#!/usr/bin/env python3
"""
Dictionary Translation Finder Script
Finds translations for dictionary words using local LLM by matching English and Russian TRA files
"""

import csv
import os
import sys
import json
import re
from pathlib import Path
import urllib.request
import urllib.parse
from typing import Dict, List, Tuple, Optional


class TranslationFinder:
    def __init__(self, dictionary_file: str = "dict.csv",
                 model: str = "qwen2.5:72b-instruct",
                 ollama_url: str = None):
        self.dictionary_file = Path(dictionary_file)
        self.model = model
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API to get translation"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(self.ollama_url, data=data,
                                       headers={'Content-Type': 'application/json'})

            with urllib.request.urlopen(req, timeout=3600) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("response", "").strip()
        except urllib.error.URLError as e:
            if "Connection refused" in str(e):
                print(f"Error: Cannot connect to Ollama at {self.ollama_url}")
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
            print(f"And the model is available: ollama pull {self.model}")
            return ""

    def _load_dictionary(self) -> List[Tuple[str, str, str]]:
        """Load dictionary and return list of (word, translation, locations) tuples for untranslated words"""
        untranslated_words = []
        if not self.dictionary_file.exists():
            print(f"Error: Dictionary file '{self.dictionary_file}' not found")
            return untranslated_words

        with open(self.dictionary_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    word = row[0].strip()
                    translation = row[1].strip()
                    locations = row[2].strip()

                    # Only include words without translation (empty second column)
                    if word and not translation and locations:
                        untranslated_words.append((word, translation, locations))

        return untranslated_words

    def _find_russian_file(self, english_file: str) -> Optional[str]:
        """Find corresponding Russian TRA file by replacing 'english' with 'russian' (case insensitive)"""
        # Try direct replacement first
        russian_file = re.sub(r'english', 'russian', english_file, flags=re.IGNORECASE)
        if os.path.exists(russian_file):
            return russian_file

        # If direct replacement doesn't work, try finding by replacing the directory part
        path_parts = Path(english_file).parts
        for i, part in enumerate(path_parts):
            if 'english' in part.lower():
                # Replace the directory part
                new_parts = list(path_parts)
                new_parts[i] = re.sub(r'english', 'russian', part, flags=re.IGNORECASE)
                russian_file = str(Path(*new_parts))
                if os.path.exists(russian_file):
                    return russian_file

        print(f"Warning: Could not find Russian file corresponding to {english_file}")
        return None

    def _extract_text_from_tra_line(self, line: str) -> Optional[str]:
        """Extract text from TRA file line format (@number = ~text~)"""
        match = re.search(r'~(.*?)~', line)
        return match.group(1) if match else None

    def _get_tra_lines_at_locations(self, locations: str) -> List[Tuple[str, str]]:
        """Get English and Russian text lines from TRA files at specified locations"""
        english_lines = []
        russian_lines = []

        # Parse locations (format: filename@line_number; filename@line_number; ...)
        location_entries = locations.split(';')

        for location in location_entries:
            location = location.strip()
            if '@' not in location:
                continue

            file_path, line_number = location.rsplit('@', 1)
            try:
                line_number = int(line_number)
            except ValueError:
                print(f"Warning: Invalid line number in location: {location}")
                continue

            # Find corresponding Russian file
            russian_file = self._find_russian_file(file_path)
            if not russian_file:
                continue

            # Read English line
            english_text = self._read_tra_line(file_path, line_number)
            if english_text:
                english_lines.append(english_text)

                # Read corresponding Russian line
                russian_text = self._read_tra_line(russian_file, line_number)
                if russian_text:
                    russian_lines.append(russian_text)
                else:
                    # If Russian line not found, remove corresponding English line
                    english_lines.pop()

        return english_lines, russian_lines

    def _read_tra_line(self, file_path: str, line_number: int) -> Optional[str]:
        """Read specific TRA line by line number (@line_number format)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # Look for @number pattern
                    match = re.match(rf'^@{line_number}\s*=', line.strip())
                    if match:
                        return self._extract_text_from_tra_line(line)
        except FileNotFoundError:
            print(f"Warning: File not found: {file_path}")
        except Exception as e:
            print(f"Warning: Error reading {file_path}: {e}")

        return None

    def _create_translation_prompt(self, english_lines: List[str], russian_lines: List[str], word: str) -> str:
        """Create the prompt for finding translation"""
        prompt = f"""I have a set of lines in English with their Russian translations, I need to find a translation of a specific word/expression. Return me the result in Subjective Case in Russian (only one word or short expression, no explanations)

Here are the English lines:
"""
        for i, eng_line in enumerate(english_lines):
            prompt += f'"{eng_line}"\n'

        prompt += f"""
Here are the Russian lines (in respective order):
"""
        for i, rus_line in enumerate(russian_lines):
            prompt += f'"{rus_line}"\n'

        prompt += f"""
The expression to find a translation for is "{word}"."""

        return prompt

    def _update_dictionary_with_translation(self, word: str, translation: str):
        """Update the dictionary file with the found translation"""
        # Read all rows
        rows = []
        with open(self.dictionary_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3 and row[0].strip() == word:
                    # Update this row with translation
                    row[1] = translation.strip()
                rows.append(row)

        # Write back all rows
        with open(self.dictionary_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

    def find_translations(self):
        """Main function to find translations for all untranslated dictionary words"""
        untranslated_words = self._load_dictionary()

        if not untranslated_words:
            print("No untranslated words found in dictionary")
            return

        print(f"Found {len(untranslated_words)} untranslated words")

        for i, (word, _, locations) in enumerate(untranslated_words, 1):
            print(f"\n[{i}/{len(untranslated_words)}] Processing word: '{word}'")

            # Get English and Russian lines from TRA files
            english_lines, russian_lines = self._get_tra_lines_at_locations(locations)

            if not english_lines or not russian_lines:
                print(f"  Warning: Could not find matching English/Russian lines for '{word}'")
                continue

            if len(english_lines) != len(russian_lines):
                print(f"  Warning: Mismatch between English ({len(english_lines)}) and Russian ({len(russian_lines)}) lines for '{word}'")
                continue

            print(f"  Found {len(english_lines)} matching line pairs")

            # Limit to first 2 pairs to avoid overly long prompts
            max_pairs = 2
            if len(english_lines) > max_pairs:
                english_lines = english_lines[:max_pairs]
                russian_lines = russian_lines[:max_pairs]
                print(f"  Using first {max_pairs} line pairs to avoid long prompts")

            # Create prompt and call LLM
            prompt = self._create_translation_prompt(english_lines, russian_lines, word)

            print(f"  Calling LLM for translation...")
            translation = self._call_ollama(prompt)

            if translation:
                # Clean up the translation result
                translation = translation.strip().strip('"').strip("'").strip()

                print(f"  Found translation: '{word}' -> '{translation}'")

                # Update dictionary
                self._update_dictionary_with_translation(word, translation)
                print(f"  Updated dictionary with translation")
            else:
                print(f"  Failed to get translation from LLM")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Find translations for dictionary words using LLM and TRA files')
    parser.add_argument('--dictionary', '-d', default='dict.csv',
                       help='Dictionary CSV file (default: dict.csv)')
    parser.add_argument('--model', default='qwen2.5:72b-instruct',
                       help='Ollama model to use (default: qwen2.5:72b-instruct)')
    parser.add_argument('--url',
                       help='Ollama API URL (default: http://localhost:11434/api/generate)')

    args = parser.parse_args()

    finder = TranslationFinder(
        dictionary_file=args.dictionary,
        model=args.model,
        ollama_url=args.url
    )
    finder.find_translations()


if __name__ == "__main__":
    main()
