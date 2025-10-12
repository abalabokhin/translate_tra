#!/usr/bin/env python3

import argparse
import os
import csv
import chardet
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Optional, Set

from antlr4 import *
from DLexer import DLexer
from DParser import DParser


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

    def __init__(self, d_filename, tra_folder):
        self.d_filename = d_filename
        self.tra_folder = tra_folder
        self.tra_cache = {}
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
        if tra_ref:
            # This text comes from TRA file
            base_name = os.path.splitext(self.d_filename)[0]
            return f"TRA:{base_name}.tra:{tra_ref}"
        else:
            # This text comes from D file - find line number
            if text_node:
                original_text = text_node.getText()
                line_num = self.find_d_file_line_number(original_text)
                if line_num:
                    return f"D:{self.d_filename}:{line_num}"
            return f"D:{self.d_filename}:unknown"
    
    def load_tra_file(self, tra_filename):
        """Load TRA file into cache."""
        if tra_filename in self.tra_cache:
            return self.tra_cache[tra_filename]
        
        tra_path = os.path.join(self.tra_folder, tra_filename)
        if not os.path.exists(tra_path):
            print(f"❌ ERROR: TRA file {tra_filename} not found in {self.tra_folder}")
            return {}
        
        try:
            encoding = detect_encoding(tra_path)
            with open(tra_path, 'r', encoding=encoding) as file:
                content = file.read()
        except Exception as e:
            print(f"❌ ERROR reading TRA file {tra_filename}: {e}")
            return {}
        
        # Parse TRA file: @123 = ~text~ or @123 = "text"
        tra_dict = {}
        
        import re
        # Pattern for tilde format
        pattern_tilde = r'@(\d+)\s*=\s*~([^~]*)~'
        for match in re.finditer(pattern_tilde, content, re.MULTILINE | re.DOTALL):
            tra_number = int(match.group(1))
            tra_text = match.group(2).strip()
            tra_dict[tra_number] = tra_text
        
        # Pattern for quote format
        pattern_quote = r'@(\d+)\s*=\s*"([^"]*)"'
        for match in re.finditer(pattern_quote, content, re.MULTILINE | re.DOTALL):
            tra_number = int(match.group(1))
            tra_text = match.group(2).strip()
            tra_dict[tra_number] = tra_text
        
        self.tra_cache[tra_filename] = tra_dict
        print(f"✅ Loaded {len(tra_dict)} TRA entries from {tra_filename}")
        return tra_dict
    
    def resolve_text(self, text_node):
        """Resolve text from parse tree node to actual dialogue text."""
        if text_node is None:
            return ""

        text = text_node.getText()

        # Handle TRA references (@123)
        if text.startswith('@') and text[1:].isdigit():
            tra_number = int(text[1:])
            if tra_number in self.tra_dict:
                # Track this TRA entry as used
                base_name = os.path.splitext(self.d_filename)[0]
                tra_filename = base_name + '.tra'
                self.used_tra_entries.add((tra_filename, tra_number))
                return self.tra_dict[tra_number]
            else:
                self.missing_tra_refs.add(text)
                return f"{text} (TRA not found)"

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
        if text.startswith('@') and text[1:].isdigit():
            return text
        return None
    
    def enterBeginDAction(self, ctx: DParser.BeginDActionContext):
        """Handle BEGIN dialogueName action."""
        if ctx.dlg:
            self.current_speaker = self.get_speaker_from_file_rule(ctx.dlg)
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
            if self.current_speaker not in self.all_speakers:
                self.all_speakers[self.current_speaker] = {}
    
    def enterChainDAction(self, ctx: DParser.ChainDActionContext):
        """Handle CHAIN dialogue action."""
        if ctx.dlg:
            self.current_speaker = self.get_speaker_from_file_rule(ctx.dlg)
            if self.current_speaker not in self.all_speakers:
                self.all_speakers[self.current_speaker] = {}
        
        # Process chain dialogue
        if ctx.body:
            chain_label = "CHAIN_UNKNOWN"
            if ctx.label:
                chain_label = self.resolve_text(ctx.label)
            self.process_chain_dlg_rule(ctx.body, chain_label)
    
    def process_chain_dlg_rule(self, chain_ctx, chain_label):
        """Process chainDlgRule context."""
        if not chain_ctx:
            return
            
        # Process initial speaker lines
        if hasattr(chain_ctx, 'initialSpeakerLines') and chain_ctx.initialSpeakerLines:
            for i, element in enumerate(chain_ctx.initialSpeakerLines):
                self.process_chain_element(element, f"{chain_label}_INITIAL_{i}")
        
        # Process chain blocks
        if hasattr(chain_ctx, 'blocks') and chain_ctx.blocks:
            for i, block in enumerate(chain_ctx.blocks):
                self.process_chain_block(block, f"{chain_label}_BLOCK_{i}")
    
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
        if hasattr(block_ctx, 'elements') and block_ctx.elements:
            # Handle monolog chain block
            if hasattr(block_ctx, 'dlg') and block_ctx.dlg:
                block_speaker = self.get_speaker_from_file_rule(block_ctx.dlg)
            else:
                block_speaker = self.current_speaker
                
            for i, element in enumerate(block_ctx.elements):
                element_state_id = f"{state_id}_ELEMENT_{i}"
                # Temporarily change speaker for this block
                original_speaker = self.current_speaker
                self.current_speaker = block_speaker
                self.ensure_speaker_initialized(self.current_speaker)
                self.process_chain_element(element, element_state_id)
                self.current_speaker = original_speaker
        
        elif hasattr(block_ctx, 'blocks') and block_ctx.blocks:
            # Handle branch chain block
            for i, sub_block in enumerate(block_ctx.blocks):
                self.process_chain_block(sub_block, f"{state_id}_BRANCH_{i}")
    
    def enterIfThenState(self, ctx: DParser.IfThenStateContext):
        """Enhanced state handler with proper transition tracking."""
        if not ctx.label:
            return
            
        state_id = self.resolve_text(ctx.label)
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
    
    def extract_transition_targets(self, trans_ctx):
        """Extract target states from transition context."""
        targets = []
        
        if hasattr(trans_ctx, 'out') and trans_ctx.out:
            for target_ctx in trans_ctx.out:
                if hasattr(target_ctx, 'label') and target_ctx.label:
                    target_id = self.resolve_text(target_ctx.label)
                    targets.append(target_id)
                elif hasattr(target_ctx, 'dlg') and target_ctx.dlg:
                    # EXTERN format
                    speaker = self.get_speaker_from_file_rule(target_ctx.dlg)
                    if hasattr(target_ctx, 'label') and target_ctx.label:
                        state_id = self.resolve_text(target_ctx.label)
                        targets.append(f"{speaker}:{state_id}")
                elif str(type(target_ctx)).find('ExitTransitionTargetContext') != -1:
                    targets.append('EXIT')
        
        return targets
    
    def build_enhanced_dialogue_flow(self):
        """Build dialogue connections using state transition information."""
        print(f"Building dialogue flow for {len(self.all_states)} states...")
        
        # Step 1: Connect SAY lines to REPLY lines within same state
        for state in self.all_states:
            state_lines = [line for line in self.all_lines if line.state_id == state.state_id]
            say_lines = [line for line in state_lines if line.line_type == "SAY"]
            reply_lines = [line for line in state_lines if line.line_type == "REPLY"]
            
            # SAY lines precede REPLY lines within the same state
            for reply_line in reply_lines:
                for say_line in say_lines:
                    if say_line.line_id not in reply_line.predecessors:
                        reply_line.predecessors.append(say_line.line_id)
                    if reply_line.line_id not in say_line.targets:
                        say_line.targets.append(reply_line.line_id)
        
        # Step 2: Resolve cross-references and connect states
        self.resolve_extern_references()
        
        # Step 3: Connect states using transition information
        for state_id, target_states in self.state_transitions.items():
            source_state = self.all_states_by_id.get(state_id)
            if not source_state:
                continue
                
            # Get the last lines of the source state
            source_lines = [line for line in self.all_lines if line.state_id == state_id]
            source_reply_lines = [line for line in source_lines if line.line_type == "REPLY"]
            source_last_lines = source_reply_lines if source_reply_lines else [line for line in source_lines if line.line_type == "SAY"]
            
            for target_state_id in target_states:
                if target_state_id == 'EXIT':
                    continue
                    
                target_state = self.all_states_by_id.get(target_state_id)
                if not target_state:
                    continue
                
                # Get the first lines of the target state
                target_lines = [line for line in self.all_lines if line.state_id == target_state_id]
                target_first_lines = [line for line in target_lines if line.line_type == "SAY"]
                
                # Connect last lines of source to first lines of target
                for source_line in source_last_lines:
                    for target_line in target_first_lines:
                        if target_line.line_id not in source_line.targets:
                            source_line.targets.append(target_line.line_id)
                        if source_line.line_id not in target_line.predecessors:
                            target_line.predecessors.append(source_line.line_id)
        
        print(f"Flow building completed. Connected {len([line for line in self.all_lines if line.targets or line.predecessors])} lines.")
    
    def resolve_extern_references(self):
        """Resolve EXTERN ~speaker~ state_id references."""
        for state_id, transitions in list(self.state_transitions.items()):
            resolved_transitions = []
            
            for transition in transitions:
                if ':' in transition:
                    # Format: SPEAKER:STATE_ID
                    speaker, target_state_id = transition.split(':', 1)
                    
                    # Look for target state in the specified speaker's states
                    if speaker in self.all_speakers and target_state_id in self.all_speakers[speaker]:
                        resolved_transitions.append(target_state_id)
                    else:
                        print(f"Warning: EXTERN reference {transition} not found")
                        resolved_transitions.append(transition)  # Keep unresolved
                else:
                    resolved_transitions.append(transition)
            
            self.state_transitions[state_id] = resolved_transitions
    
    def group_connected_dialogues(self):
        """Group dialogues using state-level connectivity."""
        print(f"Grouping {len(self.all_states)} states into connected dialogues...")
        
        # Build state-level connectivity graph
        state_connections = defaultdict(set)
        
        for source_state, target_states in self.state_transitions.items():
            for target_state in target_states:
                if target_state != 'EXIT':
                    state_connections[source_state].add(target_state)
                    state_connections[target_state].add(source_state)
        
        # Find connected state components
        visited_states = set()
        dialogue_groups = []
        
        def dfs_states(state_id, current_group):
            if state_id in visited_states or state_id == 'EXIT':
                return
            visited_states.add(state_id)
            current_group.add(state_id)
            
            for connected_state in state_connections.get(state_id, []):
                if connected_state not in visited_states:
                    dfs_states(connected_state, current_group)
        
        # Group states into connected components
        all_state_ids = set(self.state_transitions.keys()) | set(self.all_states_by_id.keys())
        
        for state_id in all_state_ids:
            if state_id not in visited_states:
                state_group = set()
                dfs_states(state_id, state_group)
                
                if state_group:
                    # Collect all lines from these connected states
                    dialogue_lines = [
                        line for line in self.all_lines 
                        if line.state_id in state_group
                    ]
                    if dialogue_lines:  # Only add non-empty groups
                        dialogue_groups.append(dialogue_lines)
        
        print(f"Created {len(dialogue_groups)} connected dialogue groups")
        return dialogue_groups


class ImprovedGrammarDialogueParser:
    """Improved grammar-based D file parser with better state tracking."""

    def __init__(self, d_folder, tra_folder):
        self.d_folder = d_folder
        self.tra_folder = tra_folder
        self.all_dialogues = {}
        self.used_tra_entries = set()  # Global set of used TRA entries
        self.tra_cache = {}  # Global TRA cache
        
    def parse_d_file(self, d_filepath):
        """Parse a D file using the improved ANTLR4 grammar."""
        try:
            encoding = detect_encoding(d_filepath)
            with open(d_filepath, 'r', encoding=encoding) as file:
                content = file.read()
        except Exception as e:
            print(f"Error reading {d_filepath}: {e}")
            return [], []
        
        d_filename = os.path.basename(d_filepath)
        
        # Create ANTLR4 input stream
        input_stream = InputStream(content)
        
        # Create lexer
        lexer = DLexer(input_stream)
        
        # Create token stream
        stream = CommonTokenStream(lexer)
        
        # Create parser
        parser = DParser(stream)
        
        # Parse the file
        tree = parser.dFileRule()
        
        # Create improved listener
        listener = ImprovedDialogueListener(d_filename, self.tra_folder)
        listener.set_d_file_content(content)  # Set content for line number tracking
        
        # Walk the parse tree
        walker = ParseTreeWalker()
        walker.walk(listener, tree)

        # Collect used TRA entries from this file
        self.used_tra_entries.update(listener.used_tra_entries)

        # Build enhanced dialogue flow
        listener.build_enhanced_dialogue_flow()

        # Group connected dialogues
        dialogue_groups = listener.group_connected_dialogues()

        # Report any missing TRA references
        if listener.missing_tra_refs:
            print(f"  ⚠️  WARNING: {len(listener.missing_tra_refs)} missing TRA references:")
            for ref in sorted(listener.missing_tra_refs):
                print(f"    - {ref}")

        if listener.syntax_errors:
            print(f"  ⚠️  WARNING: {len(listener.syntax_errors)} syntax errors encountered:")
            for error in listener.syntax_errors[:5]:  # Show first 5
                print(f"    - {error}")

        return listener.all_states, listener.all_lines, dialogue_groups
    
    def sort_lines_by_flow(self, lines):
        """Sort dialogue lines by logical flow."""
        line_dict = {line.line_id: line for line in lines}
        result = []
        visited = set()
        
        def visit(line_id):
            if line_id in visited or line_id not in line_dict:
                return
            
            visited.add(line_id)
            line = line_dict[line_id]
            
            # Visit predecessors first
            for pred in line.predecessors:
                if pred in line_dict:
                    visit(pred)
            
            result.append(line)
        
        # Start with lines that have no predecessors
        for line in lines:
            if not line.predecessors:
                visit(line.line_id)
        
        # Add any remaining lines
        for line in lines:
            if line.line_id not in visited:
                visit(line.line_id)
        
        return result
    
    def load_all_tra_files(self):
        """Load all TRA files from the TRA folder into cache."""
        tra_files = [f for f in os.listdir(self.tra_folder) if f.lower().endswith('.tra')]
        print(f"Pre-loading {len(tra_files)} TRA files...")

        import re
        for tra_filename in tra_files:
            tra_path = os.path.join(self.tra_folder, tra_filename)
            try:
                encoding = detect_encoding(tra_path)
                with open(tra_path, 'r', encoding=encoding) as file:
                    content = file.read()

                tra_dict = {}
                # Pattern for tilde format
                pattern_tilde = r'@(\d+)\s*=\s*~([^~]*)~'
                for match in re.finditer(pattern_tilde, content, re.MULTILINE | re.DOTALL):
                    tra_number = int(match.group(1))
                    tra_text = match.group(2).strip()
                    tra_dict[tra_number] = tra_text

                # Pattern for quote format
                pattern_quote = r'@(\d+)\s*=\s*"([^"]*)"'
                for match in re.finditer(pattern_quote, content, re.MULTILINE | re.DOTALL):
                    tra_number = int(match.group(1))
                    tra_text = match.group(2).strip()
                    tra_dict[tra_number] = tra_text

                self.tra_cache[tra_filename] = tra_dict
            except Exception as e:
                print(f"Error loading {tra_filename}: {e}")

        print(f"Loaded {len(self.tra_cache)} TRA files into cache")

    def process_all_d_files(self):
        """Process all D files in the folder."""
        # Pre-load all TRA files so we can detect unused lines
        self.load_all_tra_files()

        d_files = [f for f in os.listdir(self.d_folder) if f.lower().endswith('.d')]
        print(f"Found {len(d_files)} D files to process")

        # Process all files
        all_dialogue_groups = []
        total_lines = 0

        for d_filename in d_files:
            d_filepath = os.path.join(self.d_folder, d_filename)
            print(f"Processing {d_filename}...")

            try:
                states, all_lines, dialogue_groups = self.parse_d_file(d_filepath)
                if dialogue_groups:
                    all_dialogue_groups.extend(dialogue_groups)
                    total_lines += len(all_lines)
                    print(f"  Found {len(dialogue_groups)} dialogue groups with {len(all_lines)} lines")
            except Exception as e:
                import traceback
                print(f"Error parsing {d_filename}: {e}")
                print("Full traceback:")
                traceback.print_exc()
                continue

        self.all_dialogues['combined'] = all_dialogue_groups
        print(f"\nTotal: {len(all_dialogue_groups)} dialogue groups with {total_lines} lines")
    
    def write_csv_files(self, output_folder):
        """Write separate CSV files for each dialogue."""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        total_csvs = 0
        
        for d_filename, dialogues in self.all_dialogues.items():
            for dialogue_idx, dialogue_lines in enumerate(dialogues, 1):
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
                        writer.writerow(['Actor', 'Line_ID', 'Predecessors', 'Dialogue_Text', 'TRA_Reference', 'Additional_Info'])
                        
                        # Sort lines logically
                        sorted_lines = self.sort_lines_by_flow(dialogue_lines)
                        
                        # Write dialogue lines
                        for line in sorted_lines:
                            predecessors_str = ";".join(line.predecessors) if line.predecessors else ""
                            tra_ref = line.original_ref or ""
                            writer.writerow([
                                line.speaker,
                                line.line_id, 
                                predecessors_str,
                                line.text,
                                tra_ref,
                                line.source_info  # Source information for translation
                            ])
                    
                    total_csvs += 1
                    print(f"Created {csv_filename} with {len(dialogue_lines)} lines")
                    
                except Exception as e:
                    print(f"Error writing {csv_filename}: {e}")
        
        print(f"\nTotal CSV files created: {total_csvs}")

    def write_unused_lines_csv(self, output_folder):
        """Write CSV file containing all TRA lines not used in dialogues."""
        # Collect all unused TRA entries
        unused_lines = []

        for tra_filename, tra_dict in self.tra_cache.items():
            for tra_number, tra_text in tra_dict.items():
                # Check if this entry was NOT used in dialogues
                if (tra_filename, tra_number) not in self.used_tra_entries:
                    # Create reference in format "filename.tra:@123"
                    reference = f"{tra_filename}:@{tra_number}"
                    unused_lines.append((reference, tra_text))

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
                writer.writerow(['Reference', 'Text'])

                # Write all unused lines
                for reference, text in unused_lines:
                    writer.writerow([reference, text])

            print(f"\nCreated {csv_filename} with {len(unused_lines)} unused TRA lines")

        except Exception as e:
            print(f"Error writing {csv_filename}: {e}")


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
- Additional_Info: Empty for manual notes
''')
    
    parser.add_argument('d_folder', help='Folder containing D files')
    parser.add_argument('tra_folder', help='Folder containing TRA files') 
    parser.add_argument('output_folder', help='Output folder for CSV files')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.d_folder):
        print(f"Error: D folder {args.d_folder} does not exist")
        return 1
        
    if not os.path.exists(args.tra_folder):
        print(f"Error: TRA folder {args.tra_folder} does not exist")
        return 1
    
    # Create parser and process files
    parser_obj = ImprovedGrammarDialogueParser(args.d_folder, args.tra_folder)
    parser_obj.process_all_d_files()
    parser_obj.write_csv_files(args.output_folder)
    parser_obj.write_unused_lines_csv(args.output_folder)

    return 0


if __name__ == '__main__':
    exit(main())