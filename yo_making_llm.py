#!/usr/bin/env python3

import argparse
import re
import os
import json
import urllib.request
import urllib.parse
from colorama import Fore, Style

def read_dict(dict_file):
    """Read dictionary file and return a dictionary mapping words without ё to words with ё"""
    dictionary = {}
    with open(dict_file, mode='r', encoding="utf8") as file:
        text = file.read()
        for a in text.split():
            b = a.replace('ё', 'е')
            dictionary[b] = a
    return dictionary

def call_ollama(prompt, model="qwen2.5:72b-instruct", ollama_url=None):
    """Call Ollama API to get LLM response"""
    if ollama_url is None:
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(ollama_url, data=data,
                                   headers={'Content-Type': 'application/json'})

        with urllib.request.urlopen(req, timeout=3600) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("response", "").strip()
    except urllib.error.URLError as e:
        if "Connection refused" in str(e):
            print(f"Error: Cannot connect to Ollama at {ollama_url}")
            print("Make sure Ollama is running: ollama serve")
            print("Or set OLLAMA_URL environment variable to the correct address")
        else:
            print(f"Error calling Ollama: {e}")
        return ""
    except TimeoutError:
        print(f"Error: Request to Ollama timed out (3600 seconds)")
        print("The model might be too large or your system too slow")
        print("Try using a smaller model like: ollama pull qwen2.5:7b-instruct")
        return ""
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        print("Make sure Ollama is running: ollama serve")
        print(f"And the model is available: ollama pull {model}")
        return ""

def validate_llm_response(original_text, llm_text):
    """
    Validate that LLM only changed е↔ё and nothing else.
    Returns (is_valid, corrected_text) tuple.
    If valid, corrected_text is the cleaned response.
    If invalid, corrected_text is None.
    """
    # Remove any markdown code blocks or extra formatting
    llm_text = llm_text.strip()
    if llm_text.startswith('```') and llm_text.endswith('```'):
        llm_text = llm_text[3:-3].strip()
    if llm_text.startswith('```text') and llm_text.endswith('```'):
        llm_text = llm_text[7:-3].strip()

    # Normalize both texts by replacing ё with е
    original_normalized = original_text.replace('ё', 'е').replace('Ё', 'Е')
    llm_normalized = llm_text.replace('ё', 'е').replace('Ё', 'Е')

    # Check if they are the same after normalization
    if original_normalized == llm_normalized:
        return True, llm_text
    else:
        return False, None

def contains_ambiguous_word(text, both_dict):
    """Check if text contains any word from the ambiguous dictionary"""
    regex = re.compile(r'\w+')
    for match in regex.finditer(text):
        word = match.group(0)
        word_lower = word.lower()
        if word_lower in both_dict:
            return True
    return False

def process_line_with_llm(line, model="qwen2.5:72b-instruct", ollama_url=None):
    """Process line with LLM to fix е→ё where appropriate
    Note: The input line should already have automatic replacements applied.
    If LLM fails, returns the input line with automatic replacements preserved.
    """
    # Extract the actual text content from TRA format
    # TRA format is @number = ~text~ or @number = "text"
    tra_match = re.match(r'(@\d+\s*=\s*[~"])(.*?)([~"])', line)
    if not tra_match:
        # Not a TRA line, process as-is
        text_to_process = line.rstrip('\n')
        prefix = ""
        suffix = "\n" if line.endswith('\n') else ""
    else:
        prefix = tra_match.group(1)
        text_to_process = tra_match.group(2)
        suffix = tra_match.group(3)
        # Preserve the rest of the line (newline, etc)
        if line.endswith('\n'):
            suffix += '\n'

    # Improved prompt with clearer instructions
    prompt = f"""You are correcting Russian text. Replace the letter "е" with "ё" ONLY where it should be pronounced as "yo" sound.

RULES:
1. Change ONLY е→ё (or Е→Ё), do not modify any other characters
2. Return ONLY the corrected text, no explanations or markdown
3. Do not add or remove any words, spaces, or punctuation

Text to correct:
{text_to_process}

Corrected text:"""

    print(f"  {Fore.YELLOW}Calling LLM for line...{Style.RESET_ALL}")
    llm_response = call_ollama(prompt, model, ollama_url)

    if not llm_response:
        print(f"  {Fore.RED}LLM returned empty response, keeping text with automatic fixes{Style.RESET_ALL}")
        return line

    # Validate response
    is_valid, corrected_text = validate_llm_response(text_to_process, llm_response)

    if not is_valid:
        print(f"  {Fore.RED}Warning: LLM changed more than just е↔ё!{Style.RESET_ALL}")
        print(f"  Expected (normalized): {text_to_process.replace('ё', 'е').replace('Ё', 'Е')}")
        print(f"  LLM returned (normalized): {llm_response.replace('ё', 'е').replace('Ё', 'Е')}")
        print(f"  {Fore.YELLOW}Keeping text with automatic fixes only{Style.RESET_ALL}")
        return line  # This already has automatic replacements applied

    # Reconstruct the line
    if tra_match:
        return prefix + corrected_text + suffix
    else:
        return corrected_text + suffix

def apply_automatic_replacements(text, main_dict, both_dict):
    """Apply automatic replacements for unambiguous words"""
    regex = re.compile(r'\w+')
    offset = 0  # Track position changes due to replacements

    for match in regex.finditer(text):
        start_p = match.start(0) + offset
        end_p = match.end(0) + offset
        w = text[start_p:end_p]
        w_lower = w.lower()

        # Determine case pattern
        upper_case = True
        all_upper_case = False
        if w == w_lower:
            upper_case = False
        if w == w.upper():
            all_upper_case = True

        # Only replace if word is in main_dict but NOT in both_dict (unambiguous)
        if w_lower in main_dict and w_lower not in both_dict:
            new_w = main_dict[w_lower]

            # Apply case pattern
            if all_upper_case:
                new_w = new_w.upper()
            elif upper_case:
                new_w = new_w[0].upper() + new_w[1:]

            # Replace in text
            text = text[:start_p] + new_w + text[end_p:]
            offset += len(new_w) - len(w)

    return text

def update_file(infile, outfile, model="qwen2.5:72b-instruct", ollama_url=None):
    """Process TRA file and apply ё replacements"""
    with open(infile, mode='r', encoding="utf8") as file:
        main_dict = read_dict("russian_yo_words.txt")
        both_dict = read_dict("russian_yo_words_both.txt")

        print(f'Processing file {infile}')
        print(f'Loaded {len(main_dict)} words from russian_yo_words.txt')
        print(f'Loaded {len(both_dict)} ambiguous words from russian_yo_words_both.txt')

        lines = file.readlines()
        processed_lines = []

        for i, line in enumerate(lines, 1):
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith('//'):
                processed_lines.append(line)
                continue

            # Check if line contains ambiguous words
            if contains_ambiguous_word(line, both_dict):
                print(f"\n{Fore.CYAN}Line {i}: Found ambiguous word(s){Style.RESET_ALL}")
                print(f"  Original: {line.strip()}")

                # First apply automatic replacements for unambiguous words
                line_auto = apply_automatic_replacements(line, main_dict, both_dict)

                # Then use LLM for the whole line (which still has ambiguous words)
                line_processed = process_line_with_llm(line_auto, model, ollama_url)
                print(f"  Result:   {line_processed.strip()}")
                processed_lines.append(line_processed)
            else:
                # No ambiguous words, just apply automatic replacements
                line_processed = apply_automatic_replacements(line, main_dict, both_dict)
                if line_processed != line:
                    print(f"{Fore.GREEN}Line {i}: Auto-fixed{Style.RESET_ALL}")
                    print(f"  Original: {line.strip()}")
                    print(f"  Fixed:    {line_processed.strip()}")
                processed_lines.append(line_processed)

        # Write output
        with open(outfile, mode='w', encoding="utf8") as outf:
            outf.writelines(processed_lines)

        print(f"\n{Fore.GREEN}Processing complete! Output written to {outfile}{Style.RESET_ALL}")


__desc__ = '''
This program automatically changes Russian letters "е" to "ё" in TRA files.
For unambiguous words (from russian_yo_words.txt), it applies changes automatically.
For ambiguous words (from russian_yo_words_both.txt), it uses local LLM (Ollama) to determine the correct spelling.
The dictionary files are russian_yo_words.txt and russian_yo_words_both.txt.
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('infile', help='Input TRA filename.')
    parser.add_argument('--out', help='Output filename.', required=False)
    parser.add_argument('--model', default='qwen2.5:72b-instruct',
                       help='Ollama model to use (default: qwen2.5:72b-instruct)')
    parser.add_argument('--url', help='Ollama API URL (default: http://localhost:11434/api/generate)')
    args = parser.parse_args()

    out = args.out
    if not out:
        out = args.infile

    update_file(args.infile, out, args.model, args.url)
