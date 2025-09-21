#!/usr/bin/env python3

import argparse
import os
import re
import chardet
import csv
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Optional


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


@dataclass 
class DialogueState:
    """Represents a complete dialogue state with all its lines."""
    state_id: str
    speaker: str
    condition: str
    lines: List[DialogueLine]
    transitions: List[str]


class CompleteDialogueParser:
    """Complete D file parser that includes REPLY lines."""
    
    def __init__(self, d_folder, tra_folder):
        self.d_folder = d_folder
        self.tra_folder = tra_folder
        self.tra_cache = {}
        self.all_dialogues = {}
        
    def load_tra_file(self, tra_filename):
        """Load TRA file into cache."""
        if tra_filename in self.tra_cache:
            return self.tra_cache[tra_filename]
        
        tra_path = os.path.join(self.tra_folder, tra_filename)
        if not os.path.exists(tra_path):
            print(f"Warning: TRA file {tra_filename} not found")
            return {}
        
        try:
            encoding = detect_encoding(tra_path)
            with open(tra_path, 'r', encoding=encoding) as file:
                content = file.read()
        except Exception as e:
            print(f"Error reading TRA file {tra_filename}: {e}")
            return {}
        
        # Parse TRA file: @123 = ~text~ or @123 = "text"
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
        return tra_dict
    
    def resolve_text(self, text, d_filename):
        """Resolve @number references to actual text from TRA files."""
        text = text.strip()
        
        # Check if it's a TRA reference
        tra_match = re.match(r'@(\d+)', text)
        if tra_match:
            tra_number = int(tra_match.group(1))
            base_name = os.path.splitext(d_filename)[0]
            tra_filename = base_name + '.tra'
            
            tra_dict = self.load_tra_file(tra_filename)
            if tra_number in tra_dict:
                return tra_dict[tra_number]
            else:
                return f"@{tra_number} (TRA not found)"
        
        # Clean direct text (remove quotes/tildes)
        if (text.startswith('~') and text.endswith('~')) or \
           (text.startswith('"') and text.endswith('"')):
            text = text[1:-1]
        
        return text.strip()
    
    def parse_state_content(self, state_content, state_id, speaker, d_filename):
        """Parse the content of a dialogue state to extract SAY and REPLY lines."""
        lines = []
        line_counter = 0
        
        # Find SAY statements - much more flexible pattern
        say_pattern = r'SAY\s+(@\d+|~[^~]*~|"[^"]*")'
        say_matches = list(re.finditer(say_pattern, state_content, re.IGNORECASE | re.DOTALL))
        
        for say_match in say_matches:
            raw_text = say_match.group(1)
            dialogue_text = self.resolve_text(raw_text, d_filename)
            
            line_id = f"{state_id}_SAY_{line_counter}"
            line_counter += 1
            
            lines.append(DialogueLine(
                speaker=speaker,
                line_id=line_id,
                text=dialogue_text,
                state_id=state_id,
                line_type="SAY",
                predecessors=[],
                targets=[]
            ))
        
        # Find continuation SAY statements (= lines)
        continuation_pattern = r'=\s*(@\d+|~[^~]*~|"[^"]*")'
        continuation_matches = list(re.finditer(continuation_pattern, state_content, re.IGNORECASE | re.DOTALL))
        
        for cont_match in continuation_matches:
            raw_text = cont_match.group(1)
            dialogue_text = self.resolve_text(raw_text, d_filename)
            
            line_id = f"{state_id}_SAY_{line_counter}"
            line_counter += 1
            
            lines.append(DialogueLine(
                speaker=speaker,
                line_id=line_id,
                text=dialogue_text,
                state_id=state_id,
                line_type="SAY",
                predecessors=[],
                targets=[]
            ))
        
        # Find REPLY statements - multiple formats:
        # Format 1: ++ @text DO ~actions~ GOTO target
        # Format 2: ++ @text DO ~actions~ + target  
        # Format 3: IF ~~ THEN REPLY @text DO ~actions~ GOTO target
        # Format 4: + ~condition~ + @text + target (conditional replies)
        
        # Pattern 1: ++ replies with GOTO
        reply_pattern1 = r'\+\+\s*(@\d+|~[^~]*~|"[^"]*")(?:[^+\n]*?)(?:\s+GOTO\s+([A-Za-z_][A-Za-z0-9_.]*|\d+))'
        reply_matches1 = list(re.finditer(reply_pattern1, state_content, re.IGNORECASE | re.DOTALL))
        
        # Pattern 2: ++ replies with + target
        reply_pattern2 = r'\+\+\s*(@\d+|~[^~]*~|"[^"]*")(?:[^+\n]*?)\s*\+\s*([A-Za-z_][A-Za-z0-9_.]*|\d+)'
        reply_matches2 = list(re.finditer(reply_pattern2, state_content, re.IGNORECASE | re.DOTALL))
        
        # Pattern 3: IF ~~ THEN REPLY
        reply_pattern3 = r'IF\s+~~\s+THEN\s+REPLY\s+(@\d+|~[^~]*~|"[^"]*")(?:[^G]*?)(?:GOTO\s+([A-Za-z_][A-Za-z0-9_.]*|\d+))?'
        reply_matches3 = list(re.finditer(reply_pattern3, state_content, re.IGNORECASE | re.DOTALL))
        
        # Pattern 4: Conditional replies: + ~condition~ + @text + target
        reply_pattern4 = r'\+\s+~[^~]*~\s*\+\s*(@\d+|~[^~]*~|"[^"]*")(?:[^+\n]*?)\+\s*([A-Za-z_][A-Za-z0-9_.]*|\d+)'
        reply_matches4 = list(re.finditer(reply_pattern4, state_content, re.IGNORECASE | re.DOTALL))
        
        # Also find simple ++ EXIT patterns
        reply_pattern_exit = r'\+\+\s*(@\d+|~[^~]*~|"[^"]*")(?:[^+\n]*?)(?:\s+EXIT)'
        reply_matches_exit = list(re.finditer(reply_pattern_exit, state_content, re.IGNORECASE | re.DOTALL))
        
        # Process all reply patterns
        all_reply_matches = [
            (reply_matches1, 1),    # ++ with GOTO
            (reply_matches2, 2),    # ++ with + target  
            (reply_matches3, 3),    # IF ~~ THEN REPLY
            (reply_matches4, 4),    # conditional replies
            (reply_matches_exit, 0) # ++ with EXIT
        ]
        
        for reply_list, pattern_type in all_reply_matches:
            for reply_match in reply_list:
                raw_text = reply_match.group(1)
                
                # Extract target based on pattern
                if pattern_type == 0:  # EXIT pattern
                    target = "EXIT"
                elif pattern_type == 3 and reply_match.lastindex and reply_match.lastindex >= 2:  # IF ~~ THEN REPLY
                    target = reply_match.group(2) if reply_match.group(2) else None
                elif reply_match.lastindex and reply_match.lastindex >= 2:  # Other patterns with target
                    target = reply_match.group(2)
                else:
                    target = None
                
                dialogue_text = self.resolve_text(raw_text, d_filename)
                
                line_id = f"{state_id}_REPLY_{line_counter}"
                line_counter += 1
                
                targets = [target] if target else []
                
                lines.append(DialogueLine(
                    speaker="PLAYER",
                    line_id=line_id,
                    text=dialogue_text,
                    state_id=state_id,
                    line_type="REPLY",
                    predecessors=[],
                    targets=targets
                ))
        
        return lines
    
    def parse_d_file(self, d_filepath):
        """Parse a D file and extract all dialogue states with complete line information."""
        try:
            encoding = detect_encoding(d_filepath)
            with open(d_filepath, 'r', encoding=encoding) as file:
                content = file.read()
        except Exception as e:
            print(f"Error reading {d_filepath}: {e}")
            return [], []
        
        # Remove comments
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        d_filename = os.path.basename(d_filepath)
        
        # Parse multiple APPEND/BEGIN blocks
        all_states = []
        all_lines = []
        
        # Split content by APPEND blocks
        append_blocks = self.split_by_append_blocks(content)
        
        for speaker, block_content in append_blocks:
            states, lines = self.parse_speaker_block(block_content, speaker, d_filename)
            all_states.extend(states)
            all_lines.extend(lines)
        
        return all_states, all_lines
    
    def split_by_append_blocks(self, content):
        """Split D file content by APPEND/BEGIN blocks."""
        blocks = []
        
        # Find all APPEND and BEGIN statements
        append_pattern = r'(APPEND(?:_EARLY)?\s+~?([A-Za-z_][A-Za-z0-9_#]*)~?|BEGIN\s+~([^~]+)~)'
        matches = list(re.finditer(append_pattern, content, re.IGNORECASE))
        
        if not matches:
            # No APPEND/BEGIN found, treat whole file as unknown speaker
            return [("UNKNOWN", content)]
        
        for i, match in enumerate(matches):
            # Get speaker name
            speaker = None
            if match.group(2):  # APPEND format
                speaker = match.group(2).upper().strip('~')
            elif match.group(3):  # BEGIN format
                speaker = match.group(3).upper()
            
            if not speaker:
                speaker = "UNKNOWN"
            
            # Get content for this block
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)
            
            block_content = content[start_pos:end_pos]
            blocks.append((speaker, block_content))
        
        return blocks
    
    def parse_speaker_block(self, content, speaker, d_filename):
        """Parse a single speaker block (content after APPEND/BEGIN)."""
        
        # Parse dialogue states
        states = []
        all_lines = []
        
        # Find IF blocks that define states
        if_pattern = r'IF\s+(?:~([^~]*)~\s+)?THEN\s+BEGIN\s+([A-Za-z_][A-Za-z0-9_.]*|\d+)|IF\s+~~\s+(?:THEN\s+)?BEGIN\s+([A-Za-z_][A-Za-z0-9_.]*|\d+)'
        
        matches = list(re.finditer(if_pattern, content, re.IGNORECASE | re.MULTILINE))
        
        for i, match in enumerate(matches):
            condition = match.group(1) if match.group(1) else ""
            state_id = match.group(2) or match.group(3)
            
            if not state_id:
                continue
            
            # Find content of this state
            state_start = match.end()
            if i + 1 < len(matches):
                state_end = matches[i + 1].start()
            else:
                end_match = re.search(r'\bEND\b', content[state_start:], re.IGNORECASE)
                if end_match:
                    state_end = state_start + end_match.start()
                else:
                    state_end = len(content)
            
            state_content = content[state_start:state_end]
            
            # Parse all lines in this state (SAY and REPLY)
            state_lines = self.parse_state_content(state_content, state_id, speaker, d_filename)
            
            # Find transitions from this state
            transitions = []
            
            # Find GOTO statements
            goto_matches = re.finditer(r'\b(?:GOTO|DO.*GOTO)\s+([A-Za-z_][A-Za-z0-9_.]*|\d+)', state_content, re.IGNORECASE)
            for goto_match in goto_matches:
                transitions.append(goto_match.group(1))
            
            # Find EXTERN statements: EXTERN ~SPEAKER~ state
            extern_matches = re.finditer(r'\bEXTERN\s+~([^~]+)~\s+([A-Za-z_][A-Za-z0-9_.]*|\d+)', state_content, re.IGNORECASE)
            for extern_match in extern_matches:
                speaker_name = extern_match.group(1)
                state_name = extern_match.group(2)
                # Create a cross-file reference
                transitions.append(f"{speaker_name}:{state_name}")
            
            # Find reply transitions - three formats
            # Format 1: ++ reply + target 
            reply_transition_matches1 = re.finditer(r'\+\+[^+]*\+\s*([A-Za-z_][A-Za-z0-9_.]*|\d+)', state_content, re.IGNORECASE)
            for reply_trans_match in reply_transition_matches1:
                transitions.append(reply_trans_match.group(1))
            
            # Format 2: IF ~~ THEN REPLY ... GOTO target
            reply_transition_matches2 = re.finditer(r'IF\s+~~\s+THEN\s+REPLY[^G]*GOTO\s+([A-Za-z_][A-Za-z0-9_.]*|\d+)', state_content, re.IGNORECASE)
            for reply_trans_match in reply_transition_matches2:
                transitions.append(reply_trans_match.group(1))
            
            # Format 3: Conditional replies: + ~condition~ + text + target
            reply_transition_matches3 = re.finditer(r'\+\s+~[^~]*~\s+\+[^+]*\+\s*([A-Za-z_][A-Za-z0-9_.]*|\d+)', state_content, re.IGNORECASE)
            for reply_trans_match in reply_transition_matches3:
                transitions.append(reply_trans_match.group(1))
            
            if re.search(r'\bEXIT\b', state_content, re.IGNORECASE):
                transitions.append("EXIT")
            
            state_obj = DialogueState(
                state_id=state_id,
                speaker=speaker,
                condition=condition,
                lines=state_lines,
                transitions=transitions
            )
            
            states.append(state_obj)
            all_lines.extend(state_lines)
        
        # Parse CHAIN constructs
        chain_states = self.parse_chain_constructs(content, speaker, d_filename)
        states.extend(chain_states[0])
        all_lines.extend(chain_states[1])
        
        return states, all_lines
    
    def parse_chain_constructs(self, content, default_speaker, d_filename):
        """Parse CHAIN constructs in D file content."""
        states = []
        all_lines = []
        
        # Find all CHAIN blocks
        chain_pattern = r'CHAIN(?:\s+(?:~([^~]*)~))?\s*(.*?)EXIT'
        chain_matches = re.finditer(chain_pattern, content, re.IGNORECASE | re.DOTALL)
        
        chain_counter = 0
        for chain_match in chain_matches:
            chain_counter += 1
            chain_content = chain_match.group(2)
            
            # Parse speaker lines within CHAIN: == SPEAKER text
            speaker_pattern = r'==\s+([A-Za-z_][A-Za-z0-9_#]*)\s*([@~""][^=]*?)(?=\s*==|$)'
            speaker_matches = list(re.finditer(speaker_pattern, chain_content, re.IGNORECASE | re.MULTILINE))
            
            chain_lines = []
            for i, speaker_match in enumerate(speaker_matches):
                speaker_name = speaker_match.group(1).upper()
                text_content = speaker_match.group(2).strip()
                
                # Create unique line ID for chain
                line_id = f"CHAIN{chain_counter}_PART{i+1}_SAY_0"
                state_id = f"CHAIN{chain_counter}_PART{i+1}"
                
                resolved_text = self.resolve_text(text_content, d_filename)
                
                line = DialogueLine(
                    speaker=speaker_name,
                    line_id=line_id,
                    text=resolved_text,
                    state_id=state_id,
                    line_type="SAY",
                    predecessors=[],
                    targets=[]
                )
                
                chain_lines.append(line)
                all_lines.append(line)
                
                # Create corresponding state
                state_obj = DialogueState(
                    state_id=state_id,
                    speaker=speaker_name,
                    condition="",
                    lines=[line],
                    transitions=[]
                )
                states.append(state_obj)
            
            # Connect chain lines sequentially
            for i in range(len(chain_lines) - 1):
                current_line = chain_lines[i]
                next_line = chain_lines[i + 1]
                current_line.targets.append(next_line.line_id)
                next_line.predecessors.append(current_line.line_id)
        
        return states, all_lines
    
    def build_line_flow(self, states, all_lines):
        """Build the flow connections between dialogue lines."""
        # Create lookup dictionaries
        state_dict = {s.state_id: s for s in states}
        line_dict = {line.line_id: line for line in all_lines}
        
        # Build predecessor relationships
        for state in states:
            state_lines = [line for line in all_lines if line.state_id == state.state_id]
            
            # Within a state: SAY lines come before REPLY lines
            say_lines = [line for line in state_lines if line.line_type == "SAY"]
            reply_lines = [line for line in state_lines if line.line_type == "REPLY"]
            
            # Connect SAY to REPLY within same state
            for reply_line in reply_lines:
                for say_line in say_lines:
                    reply_line.predecessors.append(say_line.line_id)
                    say_line.targets.append(reply_line.line_id)
            
            # Connect to transitions
            for transition_state_id in state.transitions:
                if transition_state_id in state_dict:
                    target_state = state_dict[transition_state_id]
                    target_lines = [line for line in all_lines if line.state_id == target_state.state_id and line.line_type == "SAY"]
                    
                    # Connect last lines of current state to first lines of target state
                    current_last_lines = reply_lines if reply_lines else say_lines
                    for current_line in current_last_lines:
                        for target_line in target_lines:
                            target_line.predecessors.append(current_line.line_id)
                            current_line.targets.append(target_line.line_id)
        
        return all_lines
    
    def build_line_flow_global(self, all_states, all_lines):
        """Build line flow connections with support for cross-file EXTERN references."""
        # Create global lookup dictionaries
        state_dict = {s.state_id: s for s in all_states}
        line_dict = {line.line_id: line for line in all_lines}
        
        # Also create speaker:state lookup for cross-file references
        speaker_state_dict = {}
        for state in all_states:
            key = f"{state.speaker}:{state.state_id}"
            speaker_state_dict[key] = state
        
        # Build predecessor relationships
        for state in all_states:
            state_lines = [line for line in all_lines if line.state_id == state.state_id]
            
            # Within a state: SAY lines come before REPLY lines
            say_lines = [line for line in state_lines if line.line_type == "SAY"]
            reply_lines = [line for line in state_lines if line.line_type == "REPLY"]
            
            # Connect SAY to REPLY within same state
            for reply_line in reply_lines:
                for say_line in say_lines:
                    reply_line.predecessors.append(say_line.line_id)
                    say_line.targets.append(reply_line.line_id)
            
            # Connect to transitions (including cross-file EXTERN)
            for transition_state_id in state.transitions:
                target_state = None
                
                # Check if it's a cross-file reference (contains ':')
                if ':' in transition_state_id:
                    if transition_state_id in speaker_state_dict:
                        target_state = speaker_state_dict[transition_state_id]
                else:
                    # Regular same-file reference
                    if transition_state_id in state_dict:
                        target_state = state_dict[transition_state_id]
                
                if target_state:
                    target_lines = [line for line in all_lines if line.state_id == target_state.state_id and line.line_type == "SAY"]
                    
                    # Connect last lines of current state to first lines of target state
                    current_last_lines = reply_lines if reply_lines else say_lines
                    for current_line in current_last_lines:
                        for target_line in target_lines:
                            target_line.predecessors.append(current_line.line_id)
                            current_line.targets.append(target_line.line_id)
        
        return all_lines
    
    def identify_dialogue_groups(self, all_lines):
        """Group lines into separate dialogues based on connectivity."""
        if not all_lines:
            return []
        
        # Build connectivity graph
        connections = defaultdict(set)
        line_dict = {line.line_id: line for line in all_lines}
        
        for line in all_lines:
            for target_id in line.targets:
                if target_id in line_dict:
                    connections[line.line_id].add(target_id)
                    connections[target_id].add(line.line_id)
            
            for pred_id in line.predecessors:
                if pred_id in line_dict:
                    connections[line.line_id].add(pred_id)
                    connections[pred_id].add(line.line_id)
        
        # Find connected components
        dialogues = []
        visited = set()
        
        def dfs(line_id, current_dialogue):
            if line_id in visited or line_id not in line_dict:
                return
            
            visited.add(line_id)
            current_dialogue.add(line_id)
            
            for connected_id in connections.get(line_id, []):
                if connected_id not in visited:
                    dfs(connected_id, current_dialogue)
        
        for line in all_lines:
            if line.line_id not in visited:
                dialogue_lines = set()
                dfs(line.line_id, dialogue_lines)
                
                if dialogue_lines:
                    dialogue_group = [line for line in all_lines if line.line_id in dialogue_lines]
                    dialogues.append(dialogue_group)
        
        print(f"  Grouped into {len(dialogues)} separate dialogues")
        return dialogues
    
    def process_all_d_files(self):
        """Process all D files in the folder."""
        d_files = [f for f in os.listdir(self.d_folder) if f.lower().endswith('.d')]
        print(f"Found {len(d_files)} D files to process")
        
        # First pass: collect all states and lines from all files
        all_states_global = []
        all_lines_global = []
        
        for d_filename in d_files:
            d_filepath = os.path.join(self.d_folder, d_filename)
            print(f"Processing {d_filename}...")
            
            states, all_lines = self.parse_d_file(d_filepath)
            if all_lines:
                all_states_global.extend(states)
                all_lines_global.extend(all_lines)
        
        # Second pass: build line flow connections with cross-file support
        if all_lines_global:
            all_lines_global = self.build_line_flow_global(all_states_global, all_lines_global)
            
            # Group into dialogues (now with cross-file connections)
            dialogues = self.identify_dialogue_groups(all_lines_global)
            
            # Store all dialogues together for now - we'll separate by file later if needed
            self.all_dialogues['combined'] = dialogues
            print(f"  Grouped into {len(dialogues)} separate dialogues")
            print(f"  Found {len(dialogues)} dialogue(s) with {len(all_lines_global)} total lines")
    
    def write_csv_files(self, output_folder):
        """Write separate CSV files for each dialogue."""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        total_csvs = 0
        
        for d_filename, dialogues in self.all_dialogues.items():
            for dialogue_idx, dialogue_lines in enumerate(dialogues, 1):
                # Create CSV filename based on structure
                if d_filename == 'combined':
                    # Handle the new combined structure
                    if dialogue_lines:
                        first_speaker = dialogue_lines[0].speaker
                        csv_filename = f"{first_speaker}_dialogue_{dialogue_idx}.csv"
                    else:
                        csv_filename = f"dialogue_{dialogue_idx}.csv"
                else:
                    # Legacy structure (for backwards compatibility)
                    base_name = os.path.splitext(d_filename)[0]
                    if len(dialogues) == 1:
                        csv_filename = f"{base_name}.csv"
                    else:
                        csv_filename = f"{base_name}_dialogue_{dialogue_idx}.csv"
                
                csv_path = os.path.join(output_folder, csv_filename)
                
                try:
                    with open(csv_path, 'w', encoding='utf-8', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        
                        # Write header
                        writer.writerow(['Actor', 'Line_ID', 'Predecessors', 'Dialogue_Text', 'Additional_Info'])
                        
                        # Sort lines logically
                        sorted_lines = self.sort_lines_by_flow(dialogue_lines)
                        
                        # Write dialogue lines
                        for line in sorted_lines:
                            predecessors_str = ";".join(line.predecessors) if line.predecessors else ""
                            writer.writerow([
                                line.speaker,
                                line.line_id, 
                                predecessors_str,
                                line.text,
                                ""  # Additional_Info column
                            ])
                    
                    total_csvs += 1
                    print(f"Created {csv_filename} with {len(dialogue_lines)} lines")
                    
                except Exception as e:
                    print(f"Error writing {csv_filename}: {e}")
        
        print(f"\nTotal CSV files created: {total_csvs}")
    
    def sort_lines_by_flow(self, lines):
        """Sort dialogue lines by logical flow."""
        # Simple topological sort
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


def main():
    parser = argparse.ArgumentParser(description='''
Complete D file parser that includes REPLY lines.

This parser extracts ALL dialogue lines from D files:
- SAY lines (NPC dialogue)  
- REPLY lines (Player responses)
- Proper dialogue flow with predecessors
- TRA file resolution for @number references
- One CSV per connected dialogue

CSV format:
- Actor: NPC name or "PLAYER"
- Line_ID: Unique line identifier  
- Predecessors: Lines that lead to this line
- Dialogue_Text: Resolved text from TRA files
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
    parser_obj = CompleteDialogueParser(args.d_folder, args.tra_folder)
    parser_obj.process_all_d_files()
    parser_obj.write_csv_files(args.output_folder)
    
    return 0


if __name__ == '__main__':
    exit(main())