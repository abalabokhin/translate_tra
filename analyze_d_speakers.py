#!/usr/bin/env python3

import argparse
import os
import re
import chardet
from collections import defaultdict


def detect_encoding(filepath):
    """Detect file encoding using chardet."""
    with open(filepath, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result['encoding']


def extract_speakers_from_file(filepath):
    """Extract all speakers from a single D file."""
    try:
        encoding = detect_encoding(filepath)
        with open(filepath, 'r', encoding=encoding) as file:
            content = file.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return set()

    speakers = set()
    
    # Remove comments (// and /* */ style)
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Pattern 1: == SPEAKERNAME (used in CHAIN, INTERJECT contexts)
    speaker_pattern1 = r'==\s+([A-Za-z_][A-Za-z0-9_#]*)'
    
    # Pattern 2: APPEND/APPEND_EARLY SPEAKERNAME (adds dialogue to existing speaker)
    speaker_pattern2 = r'APPEND(?:_EARLY)?\s+([A-Za-z_][A-Za-z0-9_#]*)'
    
    # Pattern 3: BEGIN ~SPEAKERNAME~ (begins new dialogue file)
    speaker_pattern3 = r'BEGIN\s+~([A-Za-z_][A-Za-z0-9_#]*)~'
    
    # Pattern 4: EXTEND_TOP/EXTEND_BOTTOM ~SPEAKERNAME~
    speaker_pattern4 = r'EXTEND_(?:TOP|BOTTOM)\s+~([A-Za-z_][A-Za-z0-9_#]*)~'
    
    # Pattern 5: ADD_STATE_TRIGGER SPEAKERNAME
    speaker_pattern5 = r'ADD_STATE_TRIGGER\s+([A-Za-z_][A-Za-z0-9_#]*)'
    
    # Pattern 6: ADD_TRANS_TRIGGER ~SPEAKERNAME~
    speaker_pattern6 = r'ADD_TRANS_TRIGGER\s+~([A-Za-z_][A-Za-z0-9_#]*)~'
    
    # Pattern 7: ALTER_TRANS ~SPEAKERNAME~
    speaker_pattern7 = r'ALTER_TRANS\s+~([A-Za-z_][A-Za-z0-9_#]*)~'
    
    # Pattern 8: REPLACE ~SPEAKERNAME~
    speaker_pattern8 = r'REPLACE\s+~([A-Za-z_][A-Za-z0-9_#]*)~'
    
    # Pattern 9: REPLACE_STATE_TRIGGER ~SPEAKERNAME~
    speaker_pattern9 = r'REPLACE_STATE_TRIGGER\s+~([A-Za-z_][A-Za-z0-9_#]*)~'
    
    # Pattern 10: SET_WEIGHT ~SPEAKERNAME~
    speaker_pattern10 = r'SET_WEIGHT\s+~([A-Za-z_][A-Za-z0-9_#]*)~'
    
    # Pattern 11: INTERJECT_COPY_TRANS SPEAKERNAME
    speaker_pattern11 = r'INTERJECT(?:_COPY_TRANS)?\s+([A-Za-z_][A-Za-z0-9_#]*)'
    
    all_patterns = [speaker_pattern1, speaker_pattern2, speaker_pattern3, 
                   speaker_pattern4, speaker_pattern5, speaker_pattern6,
                   speaker_pattern7, speaker_pattern8, speaker_pattern9,
                   speaker_pattern10, speaker_pattern11]
    
    for pattern in all_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        for match in matches:
            # Clean up the speaker name and add to set
            speaker = match.strip().upper()
            if speaker and len(speaker) <= 32:  # Reasonable length limit for dialogue names
                speakers.add(speaker)
    
    return speakers


def analyze_d_files(folder_path):
    """Analyze all D files in a folder and collect speakers."""
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory")
        return
    
    all_speakers = set()
    file_speakers = defaultdict(set)
    d_files_found = 0
    
    # Find all .D files in the folder
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.d'):
            filepath = os.path.join(folder_path, filename)
            d_files_found += 1
            
            speakers = extract_speakers_from_file(filepath)
            
            if speakers:
                file_speakers[filename] = speakers
                all_speakers.update(speakers)
    
    if d_files_found == 0:
        print(f"No .D files found in {folder_path}")
        return
    
    # Output only unique speakers
    for speaker in sorted(all_speakers):
        print(speaker)


__desc__ = '''
This script analyzes D files (WeiDU dialogue files) in a folder and extracts all speakers.
It looks for speaker definitions using various WeiDU commands including:
- == SPEAKERNAME (CHAIN, INTERJECT contexts)
- APPEND/APPEND_EARLY SPEAKERNAME (extending dialogues)  
- BEGIN ~SPEAKERNAME~ (new dialogue files)
- EXTEND_TOP/BOTTOM ~SPEAKERNAME~ (extending states)
- ALTER_TRANS, REPLACE, SET_WEIGHT ~SPEAKERNAME~ (dialogue modifications)
- ADD_STATE_TRIGGER, ADD_TRANS_TRIGGER SPEAKERNAME (adding conditions)
- INTERJECT/INTERJECT_COPY_TRANS SPEAKERNAME (dialogue insertions)

D files are dialogue files used in Infinity Engine game modding with WeiDU.
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('folder', help='Folder containing D files to analyze')
    args = parser.parse_args()
    
    analyze_d_files(args.folder)