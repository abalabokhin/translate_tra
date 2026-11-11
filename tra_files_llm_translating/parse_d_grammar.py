#!/usr/bin/env python3

import argparse
import os
import csv
import chardet
import json
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Optional, Set

from antlr4 import *
from DLexer import DLexer
from DParser import DParser
from tra_format import parse_tra, read_text
from weidu_usage import WeiduUsage
from antlr4.error.ErrorListener import ErrorListener


class RaisingErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise ValueError(f"D syntax error at {line}:{column}: {msg}")


def detect_encoding(filepath):
    """Detect file encoding using chardet."""
    with open(filepath, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result['encoding']


@dataclass
class DialogueLine:
    """Represents a single line of dialogue (SAY or REPLY)."""
    speaker: str  # NPC name or "PLAYER"
    line_id: str  # Unique identifier
    text: str     # Dialogue text
    state_id: str # State this line belongs to
    line_type: str # "SAY" or "REPLY"
    predecessors: List[str] # Lines that can lead to this line
    targets: List[str] # Lines this line can lead to
    original_ref: Optional[str] = None  # Original @NUMBER reference if any
    source_info: str = ""  # Source file and location info for translation


@dataclass 
class DialogueState:
    """Represents a complete dialogue state with all its lines."""
    state_id: str
    speaker: str
    condition: str
    lines: List[DialogueLine]
    transitions: List[str]


class ImprovedDialogueListener(ParseTreeListener):
    """Enhanced ANTLR4 listener with proper state tracking and transition resolution."""

    def __init__(self, d_filename, tra_folder, usage=None, source_path=None):
        self.d_filename = d_filename
        self.tra_folder = tra_folder
        self.tra_cache = {}
        self.usage = usage
        self.source_path = Path(source_path or d_filename).resolve()
        self.resolved_ref_files = {}
        self.resolved_ref_numbers = {}
        self.tlk_refs = {}
        self.used_tra_entries = set()  # Track which TRA entries are used

        # Enhanced state tracking
        self.all_lines = []
        self.all_states = []
        self.all_states_by_id = {}  # state_id -> DialogueState
        self.current_speaker = "UNKNOWN"
        self.current_state_id = None
        self.current_state_context = None
        self.line_counter = 0

        # Transition tracking
        self.state_transitions = {}  # state_id -> [target_states]
        
        # Chain tracking
        self.chain_roots = {}  # (speaker, label) -> root_state_id
        self.public_states = {}  # actual source labels -> entry state, including CHAIN roots
        self.automatic_transitions = defaultdict(list)
        self.created_dialogues = set()
        self.unknown_numeric_layout = set()

        # Error tracking
        self.missing_tra_refs = set()
        self.syntax_errors = []
        self.all_speakers = {}  # speaker -> {state_id -> DialogueState}

        # Source tracking for translation
        self.d_file_lines = []  # Store D file lines for line number lookup
        self.d_file_content = ""  # Store original D file content

        # Load TRA file for this D file
        base_name = os.path.splitext(d_filename)[0]
        tra_filename = base_name + '.tra'
        self.tra_filename = tra_filename
        self.tra_dict = self.load_tra_file(tra_filename)
    
    def set_d_file_content(self, content):
        """Set D file content for line number tracking."""
        self.d_file_content = content
        self.d_file_lines = content.split('\n')
    
    def find_d_file_line_number(self, search_text):
        """Find the line number where text appears in D file."""
        if not search_text or not self.d_file_lines:
            return None
        
        # Clean up the search text - remove quotes/tildes for searching
        search_clean = search_text.strip()
        if (search_clean.startswith('~') and search_clean.endswith('~')) or \
           (search_clean.startswith('"') and search_clean.endswith('"')):
            search_clean = search_clean[1:-1]
        
        # Search for the text in D file lines
        for i, line in enumerate(self.d_file_lines, 1):
            if search_clean in line and len(search_clean) > 10:  # Only for substantial text
                return i
        
        return None
    
    def create_source_info(self, text_node, tra_ref=None):
        """Create source information for translation purposes."""
        if text_node and text_node.getText().startswith('@'):
            number = int(text_node.getText()[1:])
            if number in self.tlk_refs:
                return f'TLK:{self.tlk_refs[number]}'
        if tra_ref:
            # This text comes from TRA file
            filename = self.resolved_ref_files.get(int(tra_ref[1:]), self.tra_filename)
            return f"TRA:{filename}:{tra_ref}"
        else:
            # This text comes from D file - find line number
            if text_node:
                original_text = text_node.getText()
                line_num = self.find_d_file_line_number(original_text)
                if line_num:
                    return f"D:{self.d_filename}:{line_num}"
            return f"D:{self.d_filename}:unknown"
    
    def load_tra_file(self, tra_filename):
        """Resolve one TRA filename case-insensitively, retaining its actual spelling."""
        matches = [name for name in os.listdir(self.tra_folder)
                   if name.casefold() == tra_filename.casefold()]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous TRA filename: {tra_filename}")
        if not matches:
            # D files with only direct strings need no corresponding TRA file.
            return {}
        self.tra_filename = matches[0]
        entries = parse_tra(read_text(os.path.join(self.tra_folder, self.tra_filename)),
                            allow_references=True, duplicate_policy='last')
        tra_dict = {number: entry.variants[0].text for number, entry in entries.items() if entry.variants}
        self.tra_cache[self.tra_filename] = tra_dict
        print(f"Loaded {len(tra_dict)} TRA entries from {self.tra_filename}")
        return tra_dict

    def resolve_text(self, text_node):
        """Resolve text from parse tree node to actual dialogue text."""
        if text_node is None:
            return ""

        text = text_node.getText()

        # Handle TRA references (@123)
        if text.startswith('@') and text[1:].lstrip('-').isdigit():
            tra_number = int(text[1:])
            if self.usage is not None:
                path, entry = self.usage.resolve(self.source_path, tra_number)
                if not entry.variants:
                    self.tlk_refs[tra_number] = entry.reference
                    return ''
                if path.parent != Path(self.tra_folder).resolve():
                    raise ValueError(f'{self.d_filename}: TRA source {path} is outside the supplied flat TRA folder')
                self.resolved_ref_files[tra_number] = path.name
                self.resolved_ref_files[entry.number] = path.name
                self.resolved_ref_numbers[tra_number] = entry.number
                self.used_tra_entries.add((path.name.casefold(), entry.number))
                return entry.variants[0].text
            elif tra_number in self.tra_dict:
                # Track this TRA entry as used
                self.used_tra_entries.add((self.tra_filename.casefold(), tra_number))
                self.resolved_ref_files[tra_number] = self.tra_filename
                return self.tra_dict[tra_number]
            else:
                original = self.tra_filename
                fallback = self.load_tra_file('setup.tra')
                filename = self.tra_filename
                self.tra_filename = original
                if tra_number in fallback:
                    self.resolved_ref_files[tra_number] = filename
                    self.used_tra_entries.add((filename.casefold(), tra_number))
                    return fallback[tra_number]
                raise ValueError(f"{self.d_filename}: unresolved {text} in corresponding TRA or setup.tra")

        # Clean direct text (remove quotes/tildes)
        if (text.startswith('~') and text.endswith('~')) or \
           (text.startswith('"') and text.endswith('"')):
            text = text[1:-1]

        return text.strip()
    
    def get_speaker_from_file_rule(self, file_rule):
        """Extract speaker name from fileRule."""
        if file_rule and file_rule.stringRule():
            speaker = file_rule.stringRule().getText()
            # Clean speaker name
            if (speaker.startswith('~') and speaker.endswith('~')) or \
               (speaker.startswith('"') and speaker.endswith('"')):
                speaker = speaker[1:-1]
            return speaker.upper()
        return "UNKNOWN"
    
    def get_tra_ref(self, text_node):
        """Get original TRA reference if present."""
        if text_node is None:
            return None
        text = text_node.getText()
        if text.startswith('@') and text[1:].lstrip('-').isdigit():
            number = int(text[1:])
            if number in self.tlk_refs:
                return None
            return '@' + str(self.resolved_ref_numbers.get(number, number))
        return None
    
    def enterInterjectCopyTransDAction(self, ctx: DParser.InterjectCopyTransDActionContext):
        """Handle INTERJECT_COPY_TRANS."""
        if not ctx.dlg:
            return
            
        # Target info
        target_dlg = self.get_speaker_from_file_rule(ctx.dlg)
        
        # In grammar: dlg label globalVar
        # But globalVar is actually the new label for the interjection chain
        new_label = "UNKNOWN_ICT"
        if ctx.globalVar:
            new_label = self.resolve_text(ctx.globalVar)
            
        print(f"DEBUG: Processing INTERJECT_COPY_TRANS {new_label}")

        if hasattr(ctx, 'blocks') and ctx.blocks:
            last_state_id = None
            
            for i, block in enumerate(ctx.blocks):
                block_state_id = self.state_key(target_dlg, f"{new_label}_BLOCK_{i}")
                
                entry_state, exit_state = self.process_chain_block(block, block_state_id)
                
                if last_state_id and entry_state:
                    self.add_transition(last_state_id, entry_state)
                
                if exit_state:
                    last_state_id = exit_state

    def enterInterjectDAction(self, ctx: DParser.InterjectDActionContext):
        """Handle INTERJECT."""
        if not ctx.dlg:
            return
            
        # Target info
        target_dlg = self.get_speaker_from_file_rule(ctx.dlg)
        
        new_label = "UNKNOWN_INTERJECT"
        if ctx.globalVar:
            new_label = self.resolve_text(ctx.globalVar)

        print(f"DEBUG: Processing INTERJECT {new_label}")
        
        last_state_id = None
        
        if hasattr(ctx, 'blocks') and ctx.blocks:
            for i, block in enumerate(ctx.blocks):
                block_state_id = self.state_key(target_dlg, f"{new_label}_BLOCK_{i}")
                
                entry_state, exit_state = self.process_chain_block(block, block_state_id)
                
                if last_state_id and entry_state:
                    self.add_transition(last_state_id, entry_state)
                
                if exit_state:
                    last_state_id = exit_state
        
        # Process epilog (transitions)
        if ctx.epilog and last_state_id:
            self.process_chain_epilog(ctx.epilog, last_state_id)

    def enterBeginDAction(self, ctx: DParser.BeginDActionContext):
        """Handle BEGIN dialogueName action."""
        if ctx.dlg:
            self.current_speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.created_dialogues.add(self.current_speaker.casefold())
            if self.current_speaker not in self.all_speakers:
                self.all_speakers[self.current_speaker] = {}
    
    def enterAppendDAction(self, ctx: DParser.AppendDActionContext):
        """Handle APPEND dialogueName action."""
        if ctx.dlg:
            self.current_speaker = self.get_speaker_from_file_rule(ctx.dlg)
            if self.current_speaker not in self.all_speakers:
                self.all_speakers[self.current_speaker] = {}
    
    def enterAppendEarlyDAction(self, ctx: DParser.AppendEarlyDActionContext):
        """Handle APPEND_EARLY dialogueName action."""
        if ctx.dlg:
            self.current_speaker = self.get_speaker_from_file_rule(ctx.dlg)
            self.unknown_numeric_layout.add(self.current_speaker.casefold())
            if self.current_speaker not in self.all_speakers:
                self.all_speakers[self.current_speaker] = {}
    
    def enterExtendTopBottomDAction(self, ctx: DParser.ExtendTopBottomDActionContext):
        """Handle EXTEND_TOP/BOTTOM action."""
        if not ctx.dlg:
            return

        speaker = self.get_speaker_from_file_rule(ctx.dlg)
        
        # Get states being extended
        target_states = []
        if ctx.states:
            for state_ctx in ctx.states:
                state_id = self.state_key(speaker, self.resolve_text(state_ctx))
                target_states.append(state_id)
        
        # Ensure speaker initialized
        self.ensure_speaker_initialized(speaker)

        # Process transitions (REPLYs)
        if ctx.transitions:
            for trans_ctx in ctx.transitions:
                for state_id in target_states:
                    # Create/update state if it doesn't exist
                    # This allows capturing lines for states defined externally
                    if state_id not in self.all_states_by_id:
                        state_obj = DialogueState(
                            state_id=state_id,
                            speaker=speaker,
                            condition="",
                            lines=[],
                            transitions=[]
                        )
                        self.all_states_by_id[state_id] = state_obj
                        self.all_states.append(state_obj)
                        self.all_speakers[speaker][state_id] = state_obj
                    
                    # Extract replies linking to this state
                    reply_lines = self.extract_replies_from_transition(trans_ctx, state_id)
                    
                    # Add lines
                    self.all_lines.extend(reply_lines)
                    self.all_states_by_id[state_id].lines.extend(reply_lines)
                    
                    # Extract and store transition targets
                    targets = self.extract_transition_targets(trans_ctx)
                    if targets:
                        for target in targets:
                            self.add_transition(state_id, target, automatic=not reply_lines)

    def enterChainDAction(self, ctx: DParser.ChainDActionContext):
        """Handle CHAIN dialogue action."""
        if ctx.dlg:
            self.current_speaker = self.get_speaker_from_file_rule(ctx.dlg)
            if self.current_speaker not in self.all_speakers:
                self.all_speakers[self.current_speaker] = {}

        # Process chain dialogue
        chain_label = "CHAIN_UNKNOWN"
        if ctx.label:
            chain_label = self.resolve_text(ctx.label)

        last_state_id = None
        if ctx.body:
            last_state_id = self.process_chain_dlg_rule(ctx.body, chain_label)

        # Process epilog (transitions after CHAIN...END)
        if ctx.epilog and last_state_id:
            self.process_chain_epilog(ctx.epilog, last_state_id)
        elif ctx.epilog:
            print(f"Warning: Epilog found but no last state for chain {chain_label}")
    
    def process_chain_dlg_rule(self, chain_ctx, chain_label):
        """Process chainDlgRule context."""
        if not chain_ctx:
            return None
            
        # Record chain root if not already recorded
        root_recorded = False
        last_state_id = None
            
        # Process initial speaker lines
        if hasattr(chain_ctx, 'initialSpeakerLines') and chain_ctx.initialSpeakerLines:
            for i, element in enumerate(chain_ctx.initialSpeakerLines):
                state_id = self.state_key(self.current_speaker, f"{chain_label}_INITIAL_{i}")
                if not root_recorded:
                    print(f"DEBUG: Registering chain root: ({self.current_speaker}, {chain_label}) -> {state_id}")
                    self.chain_roots[(self.current_speaker, chain_label)] = state_id
                    self.register_public_state(self.current_speaker, chain_label, state_id)
                    root_recorded = True
                
                # Connect from previous state if exists
                if last_state_id:
                     self.add_transition(last_state_id, state_id)

                self.process_chain_element(element, state_id)
                last_state_id = state_id
        
        # Process chain blocks
        if hasattr(chain_ctx, 'blocks') and chain_ctx.blocks:
            for i, block in enumerate(chain_ctx.blocks):
                block_state_id = self.state_key(self.current_speaker, f"{chain_label}_BLOCK_{i}")
                
                entry_state, exit_state = self.process_chain_block(block, block_state_id)
                
                if last_state_id and entry_state:
                    self.add_transition(last_state_id, entry_state)
                
                if exit_state:
                    last_state_id = exit_state

        return last_state_id
    
    def ensure_speaker_initialized(self, speaker):
        """Ensure speaker exists in all_speakers dictionary."""
        if speaker not in self.all_speakers:
            self.all_speakers[speaker] = {}
    
    def process_chain_element(self, element_ctx, state_id):
        """Process chainElementRule context."""
        if not element_ctx or not hasattr(element_ctx, 'line'):
            return
        
        # Ensure current speaker is initialized
        self.ensure_speaker_initialized(self.current_speaker)
            
        dialogue_text = self.resolve_text(element_ctx.line)
        
        line_id = f"{state_id}_SAY_{self.line_counter}"
        self.line_counter += 1
        
        tra_ref = self.get_tra_ref(element_ctx.line)
        source_info = self.create_source_info(element_ctx.line, tra_ref)
        
        line = DialogueLine(
            speaker=self.current_speaker,
            line_id=line_id,
            text=dialogue_text,
            state_id=state_id,
            line_type="SAY",
            predecessors=[],
            targets=[],
            original_ref=tra_ref,
            source_info=source_info
        )
        
        self.all_lines.append(line)
        
        # Create/update state
        if state_id not in self.all_states_by_id:
            state_obj = DialogueState(
                state_id=state_id,
                speaker=self.current_speaker,
                condition="",
                lines=[],
                transitions=[]
            )
            self.all_states_by_id[state_id] = state_obj
            self.all_states.append(state_obj)
            self.all_speakers[self.current_speaker][state_id] = state_obj
        
        self.all_states_by_id[state_id].lines.append(line)
    
    def process_chain_block(self, block_ctx, state_id):
        """Process chainBlockRule context."""
        entry_state = None
        exit_state = None
        last_sub_state = None

        if hasattr(block_ctx, 'elements') and block_ctx.elements:
            # Handle monolog chain block
            if hasattr(block_ctx, 'dlg') and block_ctx.dlg:
                block_speaker = self.get_speaker_from_file_rule(block_ctx.dlg)
            else:
                block_speaker = self.current_speaker

            for i, element in enumerate(block_ctx.elements):
                element_state_id = f"{state_id}_ELEMENT_{i}"
                
                if not entry_state:
                    entry_state = element_state_id
                
                if last_sub_state:
                    self.add_transition(last_sub_state, element_state_id)

                # Temporarily change speaker for this block
                original_speaker = self.current_speaker
                self.current_speaker = block_speaker
                self.ensure_speaker_initialized(self.current_speaker)
                self.process_chain_element(element, element_state_id)
                self.current_speaker = original_speaker
                
                last_sub_state = element_state_id
            
            exit_state = last_sub_state

        elif hasattr(block_ctx, 'blocks') and block_ctx.blocks:
            # Handle branch chain block
            for i, sub_block in enumerate(block_ctx.blocks):
                 sub_entry, sub_exit = self.process_chain_block(sub_block, f"{state_id}_BRANCH_{i}")
                 if not entry_state:
                     entry_state = sub_entry
                 
                 if last_sub_state and sub_entry:
                     self.add_transition(last_sub_state, sub_entry)
                 
                 if sub_exit:
                     last_sub_state = sub_exit
            
            exit_state = last_sub_state

        return entry_state, exit_state

    def process_chain_epilog(self, epilog_ctx, parent_state_id):
        """Process chainActionEpilogRule context - handles transitions after CHAIN...END."""
        if not epilog_ctx:
            return

        if isinstance(epilog_ctx, (DParser.ExternChainActionEpilogContext,
                                   DParser.EndChainActionEpilogContext)):
            speaker = self.get_speaker_from_file_rule(epilog_ctx.dlg)
            label = self.resolve_text(epilog_ctx.label)
            self.add_transition(parent_state_id, self.state_key(speaker, label))
            return

        # Check if this is an endWithTransitionsChainActionEpilog (has transitions)
        if hasattr(epilog_ctx, 'transitions') and epilog_ctx.transitions:
            # Ensure current speaker is initialized
            self.ensure_speaker_initialized(self.current_speaker)

            # Process transitions (REPLY lines)
            epilog_lines = []
            transition_targets = []

            for trans_ctx in epilog_ctx.transitions:
                # Extract REPLY lines from transitions
                reply_lines = self.extract_replies_from_transition(trans_ctx, parent_state_id)
                epilog_lines.extend(reply_lines)

                # Extract transition targets
                targets = self.extract_transition_targets(trans_ctx)
                transition_targets.extend(targets)
                if not reply_lines:
                    self.automatic_transitions[parent_state_id].extend(targets)

            # Store transitions for parent state
            if transition_targets:
                if parent_state_id in self.state_transitions:
                    self.state_transitions[parent_state_id].extend(transition_targets)
                else:
                    self.state_transitions[parent_state_id] = transition_targets

            # If there are reply lines, they are already linked to parent_state_id
            if epilog_lines:
                # Add them to all_lines
                self.all_lines.extend(epilog_lines)
                
                # Add them to the state object if we can find it
                if parent_state_id in self.all_states_by_id:
                     self.all_states_by_id[parent_state_id].lines.extend(epilog_lines)
                
                # No need to create a separate epilog state anymore unless we want to group them
                # But typically reply lines are part of the state they reply to.

    
    def enterIfThenState(self, ctx: DParser.IfThenStateContext):
        """Enhanced state handler with proper transition tracking."""
        if not ctx.label:
            return
            
        label = self.resolve_text(ctx.label)
        state_id = self.state_key(self.current_speaker, label)
        self.register_public_state(self.current_speaker, label, state_id)
        self.current_state_id = state_id
        self.current_state_context = ctx
        
        # Ensure current speaker is initialized
        self.ensure_speaker_initialized(self.current_speaker)
        
        # Process SAY lines within this state
        state_lines = []
        if ctx.lines:
            for i, line_ctx in enumerate(ctx.lines):
                dialogue_text = self.resolve_text(line_ctx)
                
                line_id = f"{state_id}_SAY_{i}"
                tra_ref = self.get_tra_ref(line_ctx)
                source_info = self.create_source_info(line_ctx, tra_ref)
                
                line = DialogueLine(
                    speaker=self.current_speaker,
                    line_id=line_id,
                    text=dialogue_text,
                    state_id=state_id,
                    line_type="SAY",
                    predecessors=[],
                    targets=[],
                    original_ref=tra_ref,
                    source_info=source_info
                )
                
                state_lines.append(line)
        
        # Process transitions and extract REPLY lines + targets
        transition_targets = []
        if ctx.transitions:
            for trans_ctx in ctx.transitions:
                # Extract REPLY lines from transitions
                reply_lines = self.extract_replies_from_transition(trans_ctx, state_id)
                state_lines.extend(reply_lines)
                
                # Extract transition targets
                targets = self.extract_transition_targets(trans_ctx)
                transition_targets.extend(targets)
                if not reply_lines:
                    self.automatic_transitions[state_id].extend(targets)
        
        # Store transitions
        self.state_transitions[state_id] = transition_targets
        
        # Create state object
        condition = ""
        if ctx.trigger:
            condition = self.resolve_text(ctx.trigger)
        
        state_obj = DialogueState(
            state_id=state_id,
            speaker=self.current_speaker,
            condition=condition,
            lines=state_lines,
            transitions=transition_targets
        )
        
        # Store state
        self.all_states_by_id[state_id] = state_obj
        self.all_states.append(state_obj)
        self.all_lines.extend(state_lines)
        
        # Add to speaker tracking
        if self.current_speaker not in self.all_speakers:
            self.all_speakers[self.current_speaker] = {}
        self.all_speakers[self.current_speaker][state_id] = state_obj
    
    def extract_replies_from_transition(self, trans_ctx, parent_state_id):
        """Extract REPLY lines from transition context."""
        replies = []
        
        if hasattr(trans_ctx, 'reply') and trans_ctx.reply:
            # This is a replyTransition (++ format)
            reply_text = self.resolve_text(trans_ctx.reply)
            
            # Get transition targets
            targets = self.extract_transition_targets(trans_ctx)
            
            line_id = f"{parent_state_id}_REPLY_{self.line_counter}"
            self.line_counter += 1
            
            tra_ref = self.get_tra_ref(trans_ctx.reply)
            source_info = self.create_source_info(trans_ctx.reply, tra_ref)
            
            reply_line = DialogueLine(
                speaker="PLAYER",
                line_id=line_id,
                text=reply_text,
                state_id=parent_state_id,  # Link to parent state
                line_type="REPLY",
                predecessors=[],  # Will be filled in flow building
                targets=targets,
                original_ref=tra_ref,
                source_info=source_info
            )
            
            replies.append(reply_line)
        
        # Check if this is an ifThenTransition with REPLY features
        elif hasattr(trans_ctx, 'features') and trans_ctx.features:
            for feature in trans_ctx.features:
                if hasattr(feature, 'line') and feature.line:
                    # This is a replyTransitionFeature (REPLY keyword in IF-THEN)
                    reply_text = self.resolve_text(feature.line)
                    
                    # Get transition targets
                    targets = self.extract_transition_targets(trans_ctx)
                    
                    line_id = f"{parent_state_id}_REPLY_{self.line_counter}"
                    self.line_counter += 1
                    
                    tra_ref = self.get_tra_ref(feature.line)
                    source_info = self.create_source_info(feature.line, tra_ref)
                    
                    reply_line = DialogueLine(
                        speaker="PLAYER",
                        line_id=line_id,
                        text=reply_text,
                        state_id=parent_state_id,  # Link to parent state
                        line_type="REPLY",
                        predecessors=[],  # Will be filled in flow building
                        targets=targets,
                        original_ref=tra_ref,
                        source_info=source_info
                    )
                    
                    replies.append(reply_line)
        
        return replies
    
    def register_public_state(self, speaker, label, state_id):
        key = (speaker.casefold(), label)
        if key in self.public_states:
            raise ValueError(f'{self.d_filename}: duplicate state label {speaker}:{label}')
        self.public_states[key] = state_id

    def add_transition(self, from_state, to_state, automatic=True):
        """Add a transition between states."""
        if from_state not in self.state_transitions:
            self.state_transitions[from_state] = []
        self.state_transitions[from_state].append(to_state)
        if automatic:
            self.automatic_transitions[from_state].append(to_state)

    def extract_transition_targets(self, trans_ctx):
        """Extract target states from transition context."""
        targets = []
        
        if hasattr(trans_ctx, 'out') and trans_ctx.out:
            for target_ctx in trans_ctx.out:
                if hasattr(target_ctx, 'dlg') and target_ctx.dlg:
                    # EXTERN format
                    speaker = self.get_speaker_from_file_rule(target_ctx.dlg)
                    if hasattr(target_ctx, 'label') and target_ctx.label:
                        state_id = self.resolve_text(target_ctx.label)
                        print(f"DEBUG: Extracted EXTERN target: {speaker}:{state_id}")
                        targets.append(f"{speaker}:{state_id}")
                elif hasattr(target_ctx, 'label') and target_ctx.label:
                    target_id = self.resolve_text(target_ctx.label)
                    print(f"DEBUG: Extracted label target: {target_id}")
                    targets.append(target_id)
                elif str(type(target_ctx)).find('ExitTransitionTargetContext') != -1:
                    targets.append('EXIT')
        
        return targets
    
    @staticmethod
    def state_key(speaker, label):
        """State labels belong to a dialogue resource; source files are qualified later."""
        return f"{speaker}:{label}"

    def build_enhanced_dialogue_flow(self):
        """Compatibility entry point for callers parsing one D source directly."""
        if not hasattr(self, '_built_groups'):
            from dialogue_graph import ModDialogueGraph
            self.all_states, self.all_lines, self._built_groups, self.graph_report = ModDialogueGraph(
                [self], self.source_path.parent).build()
            self.all_states_by_id = {state.state_id: state for state in self.all_states}

    def group_connected_dialogues(self):
        self.build_enhanced_dialogue_flow()
        return self._built_groups


class ImprovedGrammarDialogueParser:
    """Improved grammar-based D file parser with better state tracking."""

    def __init__(self, d_folder, tra_folder, tp2_file=None, source_language=None):
        self.d_folder = d_folder
        self.tra_folder = tra_folder
        self.all_dialogues = {}
        self.used_tra_entries = set()  # Global set of used TRA entries
        self.tra_cache = {}  # Global TRA cache
        self.tra_female_cache = {}
        self.tp2_file = tp2_file
        self.source_language = source_language or Path(tra_folder).name
        self.usage = None
        self.excluded_tra_entries = set()
        self.listeners = {}
        self.graph_report = None

    def parse_d_file(self, d_filepath, defer_graph=False):
        """Parse a D file using the improved ANTLR4 grammar."""
        try:
            source_path = Path(d_filepath).resolve()
            content = (self.usage.virtual_files[source_path] if self.usage and source_path in self.usage.virtual_files
                       else read_text(d_filepath))
        except Exception as e:
            print(f"Error reading {d_filepath}: {e}")
            raise ValueError(f"Cannot read D file {d_filepath}: {e}") from e
        
        d_filename = os.path.basename(d_filepath)
        
        # Create ANTLR4 input stream
        input_stream = InputStream(content)
        
        # Create lexer
        lexer = DLexer(input_stream)
        lexer.removeErrorListeners()
        lexer.addErrorListener(RaisingErrorListener())
        
        # Create token stream
        stream = CommonTokenStream(lexer)
        
        # Create parser
        parser = DParser(stream)
        parser.removeErrorListeners()
        parser.addErrorListener(RaisingErrorListener())
        
        # Parse the file
        tree = parser.dFileRule()
        
        # Create improved listener
        listener = ImprovedDialogueListener(d_filename, self.tra_folder, self.usage, d_filepath)
        listener.set_d_file_content(content)  # Set content for line number tracking
        
        # Walk the parse tree
        walker = ParseTreeWalker()
        walker.walk(listener, tree)

        # Collect used TRA entries from this file
        self.used_tra_entries.update(listener.used_tra_entries)

        self.listeners[Path(d_filepath).resolve()] = listener
        if defer_graph:
            return listener.all_states, listener.all_lines, []
        from dialogue_graph import ModDialogueGraph
        states, lines, dialogue_groups, _ = ModDialogueGraph([listener], self.d_folder).build()

        # Report any missing TRA references
        if listener.missing_tra_refs:
            print(f"  ⚠️  WARNING: {len(listener.missing_tra_refs)} missing TRA references:")
            for ref in sorted(listener.missing_tra_refs):
                print(f"    - {ref}")

        if listener.syntax_errors:
            print(f"  ⚠️  WARNING: {len(listener.syntax_errors)} syntax errors encountered:")
            for error in listener.syntax_errors[:5]:  # Show first 5
                print(f"    - {error}")

        return states, lines, dialogue_groups
    
    def sort_lines_by_flow(self, lines):
        """Iterative predecessor-first ordering; cycles and long chains are safe."""
        line_dict = {line.line_id: line for line in lines}
        result, visited = [], set()
        starts = [line for line in lines if not line.predecessors] + list(lines)
        for line in starts:
            pending = [(line.line_id, False)]
            while pending:
                line_id, expanded = pending.pop()
                if expanded:
                    result.append(line_dict[line_id])
                    continue
                if line_id in visited or line_id not in line_dict:
                    continue
                visited.add(line_id)
                pending.append((line_id, True))
                pending.extend((pred, False) for pred in reversed(line_dict[line_id].predecessors))
        return result

    def load_all_tra_files(self):
        """Read each physical TRA file once, including original female source text."""
        tra_files = sorted(f for f in os.listdir(self.tra_folder) if f.casefold().endswith('.tra'))
        if len({f.casefold() for f in tra_files}) != len(tra_files):
            raise ValueError("TRA filenames differ only by case")
        for filename in tra_files:
            entries = parse_tra(read_text(os.path.join(self.tra_folder, filename)),
                                allow_references=True, duplicate_policy='last')
            self.tra_cache[filename] = {n: e.variants[0].text for n, e in entries.items() if e.variants}
            self.tra_female_cache[filename.casefold()] = {
                n: e.variants[1].text for n, e in entries.items() if len(e.variants) == 2}
        print(f"Loaded {len(self.tra_cache)} TRA files into cache")

    def source_female_text(self, source_info):
        if not source_info.startswith('TRA:'):
            return ''
        _, filename, ref = source_info.split(':')
        return self.tra_female_cache.get(filename.casefold(), {}).get(int(ref[1:]), '')

    def source_has_female(self, source_info):
        if not source_info.startswith('TRA:'):
            return ''
        _, filename, ref = source_info.split(':')
        return '1' if int(ref[1:]) in self.tra_female_cache.get(filename.casefold(), {}) else ''

    def process_all_d_files(self):
        """Process all D files in the folder."""
        # Pre-load all TRA files so we can detect unused lines
        self.load_all_tra_files()

        if self.tp2_file:
            self.usage = WeiduUsage(self.tp2_file, self.source_language, self.tra_folder).analyze()
            self.excluded_tra_entries = {
                (path.name.casefold(), number) for path, number in self.usage.excluded
                if path.parent == Path(self.tra_folder).resolve()
            }
            print(f'Excluded {len(self.excluded_tra_entries)} proven installer-only TRA entries')
            if not self.usage.complete:
                print('Usage analysis incomplete: installer exclusions disabled; uncertain entries retained.')
                for warning in (self.usage.warnings + self.usage.unresolved)[:5]:
                    print(f'  Warning: {warning}')

        d_files = {path.resolve() for path in Path(self.d_folder).rglob('*') if path.suffix.casefold() == '.d'}
        if self.usage:
            d_files.update(path for path in self.usage.source_fallbacks if path.suffix.casefold() == '.d')
        d_files = sorted(d_files)
        print(f"Found {len(d_files)} D sources to process")

        # Process all files
        all_dialogue_groups = []
        total_lines = 0

        for d_filepath in d_files:
            print(f"Processing {d_filepath}...")

            try:
                states, all_lines, _ = self.parse_d_file(d_filepath, defer_graph=True)
                total_lines += len(all_lines)
                print(f"  Read {len(states)} states with {len(all_lines)} lines")
            except Exception as e:
                raise ValueError(f"Cannot safely extract {d_filepath}: {e}") from e

        from dialogue_graph import ModDialogueGraph
        _, _, all_dialogue_groups, self.graph_report = ModDialogueGraph(
            self.listeners.values(), self.d_folder,
            self.usage.compilation_units if self.usage else None).build()
        print(f"Linked {self.graph_report['cross_file_line_edges']} cross-file dialogue edges")

        # D parsing can discover uses outside static COMPILE paths. A dialogue
        # reference always overrides an installer-only exclusion.
        self.excluded_tra_entries.difference_update(self.used_tra_entries)
        if self.usage:
            for filename in self.tra_cache:
                for number in self.tra_cache[filename]:
                    if (filename.casefold(), number) in self.used_tra_entries:
                        key = ((Path(self.tra_folder) / filename).resolve(), number)
                        self.usage.usage[key].add('game')

        self.all_dialogues['combined'] = all_dialogue_groups
        print(f"\nTotal: {len(all_dialogue_groups)} dialogue groups with {total_lines} lines")
    
    def write_csv_files(self, output_folder):
        """Write separate CSV files for each dialogue."""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        total_csvs = 0
        
        for d_filename, dialogues in self.all_dialogues.items():
            for dialogue_idx, dialogue_lines in enumerate(dialogues, 1):
                visible = {line.line_id: line for line in dialogue_lines
                           if line.original_ref and line.source_info.startswith('TRA:')}
                if not visible:
                    continue
                all_lines = {line.line_id: line for line in dialogue_lines}
                def visible_predecessors(line):
                    result, visited = [], set()
                    pending = list(reversed(line.predecessors))
                    while pending:
                        predecessor = pending.pop()
                        if predecessor in visited:
                            continue
                        visited.add(predecessor)
                        if predecessor in visible:
                            result.append(predecessor)
                        elif predecessor in all_lines:
                            pending.extend(reversed(all_lines[predecessor].predecessors))
                    return list(dict.fromkeys(result))
                readonly = [{'actor': line.speaker, 'text': line.text,
                             'line_id': line.line_id, 'predecessors': line.predecessors}
                            for line in dialogue_lines if line.line_id not in visible and line.text.strip()
                            and not line.source_info.startswith('TLK:')]
                readonly_context = ('Read-only hardcoded dialogue; leave unchanged: ' + json.dumps(readonly, ensure_ascii=False)
                                    if readonly else '')
                # Create CSV filename
                if dialogue_lines:
                    first_speaker = dialogue_lines[0].speaker
                    csv_filename = f"{first_speaker}_dialogue_{dialogue_idx}.csv"
                else:
                    csv_filename = f"dialogue_{dialogue_idx}.csv"
                
                csv_path = os.path.join(output_folder, csv_filename)
                
                try:
                    with open(csv_path, 'w', encoding='utf-8', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        
                        # Write header
                        writer.writerow(['Actor', 'Line_ID', 'Predecessors', 'Dialogue_Text', 'TRA_Reference', 'Additional_Info', 'Source_Female_Text', 'Source_Has_Female', 'Source_Context'])
                        
                        # Sort lines logically
                        sorted_lines = self.sort_lines_by_flow(dialogue_lines)
                        
                        # Write dialogue lines
                        for line in sorted_lines:
                            if line.line_id not in visible:
                                continue
                            predecessors_str = ";".join(visible_predecessors(line))
                            tra_ref = line.original_ref or ""
                            writer.writerow([
                                line.speaker,
                                line.line_id, 
                                predecessors_str,
                                line.text,
                                tra_ref,
                                line.source_info,  # Source information for translation
                                self.source_female_text(line.source_info),
                                self.source_has_female(line.source_info),
                                readonly_context
                            ])
                    
                    total_csvs += 1
                    print(f"Created {csv_filename} with {len(dialogue_lines)} lines")
                    
                except Exception as e:
                    raise ValueError(f"Error writing {csv_filename}: {e}") from e
        
        print(f"\nTotal CSV files created: {total_csvs}")
        if self.graph_report is not None:
            (Path(output_folder) / '_dialogue_graph.json').write_text(
                json.dumps(self.graph_report, ensure_ascii=False, indent=2) + '\n')

    def write_unused_lines_csv(self, output_folder):
        """Write CSV file containing all TRA lines not used in dialogues."""
        # Collect all unused TRA entries
        unused_lines = []

        for tra_filename, tra_dict in self.tra_cache.items():
            for tra_number, tra_text in tra_dict.items():
                # Check if this entry was NOT used in dialogues
                # used_tra_entries stores lowercase filenames
                key = (tra_filename.casefold(), tra_number)
                if key not in self.used_tra_entries and key not in self.excluded_tra_entries:
                    # Create reference in format "filename.tra:@123"
                    reference = f"{tra_filename}:@{tra_number}"
                    female = self.tra_female_cache.get(tra_filename.casefold(), {}).get(tra_number, '')
                    has_female = '1' if tra_number in self.tra_female_cache.get(tra_filename.casefold(), {}) else ''
                    physical_key = ((Path(self.tra_folder) / tra_filename).resolve(), tra_number)
                    text_type = 'journal' if self.usage and physical_key in self.usage.journal_entries else ''
                    unused_lines.append((reference, tra_text, female, has_female, text_type))

        if not unused_lines:
            print("No unused TRA lines found")
            return

        # Sort by reference for consistency
        unused_lines.sort(key=lambda x: x[0])

        # Write to special CSV file
        csv_filename = "_unused_tra_lines.csv"
        csv_path = os.path.join(output_folder, csv_filename)

        try:
            with open(csv_path, 'w', encoding='utf-8', newline='') as csvfile:
                writer = csv.writer(csvfile)

                # Write header (simplified format for unused lines)
                writer.writerow(['Reference', 'Text', 'Source_Female_Text', 'Source_Has_Female', 'Text_Type'])

                # Write all unused lines
                for reference, text, female, has_female, text_type in unused_lines:
                    writer.writerow([reference, text, female, has_female, text_type])

            print(f"\nCreated {csv_filename} with {len(unused_lines)} unused TRA lines")

        except Exception as e:
            raise ValueError(f"Error writing {csv_filename}: {e}") from e


def main():
    parser = argparse.ArgumentParser(description='''
Improved Grammar-based D file parser using ANTLR4.

This enhanced parser uses a complete ANTLR4 grammar with improved state tracking:
- Better dialogue flow connections
- State-level dialogue grouping  
- Proper transition resolution
- Enhanced REPLY extraction
- Cross-reference handling

CSV format:
- Actor: NPC name or "PLAYER"
- Line_ID: Unique line identifier  
- Predecessors: Lines that lead to this line
- Dialogue_Text: Resolved text from TRA files
- TRA_Reference: Original @number reference
- Additional_Info: Source TRA filename/reference or D file location
- Source_Female_Text: Original female variant when present
''')
    
    parser.add_argument('d_folder', help='Folder containing D files')
    parser.add_argument('tra_folder', help='Folder containing TRA files') 
    parser.add_argument('output_folder', help='Output folder for CSV files')
    parser.add_argument('--tp2-file', help='Main TP2: read language fallbacks and exclude proven installer-only entries')
    parser.add_argument('--source-language', help='LANGUAGE directory/name (default: TRA folder basename)')
    parser.add_argument('--usage-report', help='Optional JSON report of fallback resolution and excluded entries')
    parser.add_argument('--unused-layout', choices=['auto', 'categorized', 'legacy'], default='auto',
                        help='auto: categorized with --tp2-file, otherwise the legacy catch-all CSV')
    parser.add_argument('--category-batch-size', type=int, default=40,
                        help='Maximum standalone rows per categorized CSV; BAF response branches stay intact')
    parser.add_argument('--actors-file', help='Optional reviewed Actor,Gender CSV for categorized extraction')
    parser.add_argument('--cre-folder', action='append', default=[],
                        help='Additional game/mod CRE folder for BAF speakers (repeatable; mod resources win)')
    
    args = parser.parse_args()
    categorized = args.unused_layout == 'categorized' or (args.unused_layout == 'auto' and args.tp2_file)
    if categorized and not args.tp2_file:
        parser.error('Categorized extraction requires --tp2-file')
    if args.category_batch_size < 1:
        parser.error('--category-batch-size must be positive')
    if categorized and Path(args.output_folder).exists() and (
            any(Path(args.output_folder).glob('*.csv')) or
            (Path(args.output_folder) / '_extraction_manifest.json').exists()):
        parser.error('Use a fresh output folder for categorized extraction')
    
    if not os.path.exists(args.d_folder):
        print(f"Error: D folder {args.d_folder} does not exist")
        return 1
        
    if not os.path.exists(args.tra_folder):
        print(f"Error: TRA folder {args.tra_folder} does not exist")
        return 1
    
    # Create parser and process files
    parser_obj = ImprovedGrammarDialogueParser(args.d_folder, args.tra_folder,
                                             args.tp2_file, args.source_language)
    try:
        parser_obj.process_all_d_files()
        parser_obj.write_csv_files(args.output_folder)
        if categorized:
            from text_categories import CategorizedTextBuilder
            CategorizedTextBuilder(parser_obj, args.category_batch_size, args.cre_folder,
                                   args.actors_file).write(args.output_folder)
        else:
            parser_obj.write_unused_lines_csv(args.output_folder)
        if args.usage_report and parser_obj.usage:
            Path(args.usage_report).write_text(json.dumps(parser_obj.usage.report(),
                                                        ensure_ascii=False, indent=2) + '\n')
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    return 0


if __name__ == '__main__':
    exit(main())
