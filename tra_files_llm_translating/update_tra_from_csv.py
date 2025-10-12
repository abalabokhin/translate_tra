#!/usr/bin/env python3
"""
TRA Update Script
Updates TRA files with translations from translated CSV files
Preserves original formatting, comments, and sounds
"""

import csv
import os
import re
from pathlib import Path
from typing import Dict, Optional
from collections import defaultdict
import chardet


def detect_encoding(filepath):
    """Detect file encoding using chardet."""
    with open(filepath, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result['encoding']


class TraEntry:
    """Represents a single TRA file entry."""
    def __init__(self, number, text, delimiter, sound=None, full_line=""):
        self.number = number
        self.text = text
        self.delimiter = delimiter  # '~' or '"'
        self.sound = sound  # e.g., [SOUND123]
        self.full_line = full_line  # Original full line for replacement


class TraUpdater:
    """Updates TRA files with translations from CSV files."""

    def __init__(self, tra_folder: str, csv_folder: str, output_folder: str = None):
        self.tra_folder = Path(tra_folder)
        self.csv_folder = Path(csv_folder)
        self.output_folder = Path(output_folder) if output_folder else self.tra_folder

        # Translations storage: tra_filename -> @number -> {'male': text, 'female': text, 'neutral': text}
        self.translations = defaultdict(lambda: defaultdict(dict))

        self.output_folder.mkdir(exist_ok=True)

    def load_translations_from_csvs(self):
        """Load all translations from CSV files."""
        print("Loading translations from CSV files...")

        # First, load dialogue CSV files (with male/female variants)
        csv_files = list(self.csv_folder.glob("*.csv"))

        # Separate male, female, and neutral files
        male_files = [f for f in csv_files if f.stem.endswith('_male')]
        female_files = [f for f in csv_files if f.stem.endswith('_female')]
        neutral_files = [f for f in csv_files if not f.stem.endswith('_male') and not f.stem.endswith('_female') and f.name != '_unused_tra_lines.csv']
        unused_file = self.csv_folder / '_unused_tra_lines.csv'

        # Load male/female pairs
        for male_file in male_files:
            base_name = male_file.stem[:-5]  # Remove '_male'
            female_file = self.csv_folder / f"{base_name}_female.csv"

            if female_file.exists():
                self._load_gendered_dialogue(male_file, female_file)
            else:
                print(f"Warning: {male_file.name} has no corresponding female version")

        # Load neutral files (no gender variants)
        for neutral_file in neutral_files:
            self._load_neutral_dialogue(neutral_file)

        # Load unused lines file
        if unused_file.exists():
            self._load_unused_lines(unused_file)

        print(f"Loaded translations for {len(self.translations)} TRA files")

    def _load_gendered_dialogue(self, male_file: Path, female_file: Path):
        """Load male and female dialogue translations."""
        print(f"  Loading {male_file.name} and {female_file.name}...")

        male_lines = self._read_dialogue_csv(male_file)
        female_lines = self._read_dialogue_csv(female_file)

        # Match lines by Line_ID
        for line_id, male_data in male_lines.items():
            if male_data['tra_ref'] and male_data['tra_file']:
                tra_file = male_data['tra_file']
                tra_number = male_data['tra_number']
                male_text = male_data['text']

                # Get corresponding female text
                female_text = female_lines.get(line_id, {}).get('text', male_text)

                self.translations[tra_file][tra_number]['male'] = male_text
                self.translations[tra_file][tra_number]['female'] = female_text

    def _load_neutral_dialogue(self, csv_file: Path):
        """Load neutral (non-gendered) dialogue translations."""
        print(f"  Loading {csv_file.name}...")

        lines = self._read_dialogue_csv(csv_file)

        for line_id, data in lines.items():
            if data['tra_ref'] and data['tra_file']:
                tra_file = data['tra_file']
                tra_number = data['tra_number']
                text = data['text']

                self.translations[tra_file][tra_number]['neutral'] = text

    def _read_dialogue_csv(self, csv_file: Path) -> Dict:
        """Read dialogue CSV and extract translations."""
        lines = {}

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)

            if not header:
                return lines

            for row in reader:
                if len(row) >= 6:  # Actor, Line_ID, Predecessors, Dialogue_Text, TRA_Reference, Additional_Info
                    line_id = row[1]
                    dialogue_text = row[3]
                    tra_ref = row[4]  # e.g., "@192"
                    additional_info = row[5]  # e.g., "TRA:BTCALEIG.tra:@192"

                    # Extract TRA file name and number
                    tra_file = None
                    tra_number = None

                    if tra_ref and tra_ref.startswith('@'):
                        tra_number = int(tra_ref[1:])

                        # Extract TRA filename from additional_info
                        if additional_info.startswith('TRA:'):
                            parts = additional_info.split(':')
                            if len(parts) >= 3:
                                tra_file = parts[1]  # e.g., "BTCALEIG.tra"

                    if tra_file and tra_number is not None:
                        lines[line_id] = {
                            'text': dialogue_text,
                            'tra_ref': tra_ref,
                            'tra_file': tra_file,
                            'tra_number': tra_number
                        }

        return lines

    def _load_unused_lines(self, unused_file: Path):
        """Load translations from _unused_tra_lines.csv."""
        print(f"  Loading {unused_file.name}...")

        with open(unused_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)

            if not header or len(header) < 3:
                print(f"Warning: {unused_file.name} has unexpected format")
                return

            for row in reader:
                if len(row) >= 3:
                    reference = row[0]  # e.g., "BTCSHADO.tra:@8"
                    russian_text = row[2]

                    # Parse reference
                    if ':@' in reference:
                        parts = reference.split(':@')
                        tra_file = parts[0]
                        tra_number = int(parts[1])

                        self.translations[tra_file][tra_number]['neutral'] = russian_text

    def parse_tra_file(self, tra_file: Path) -> Dict[int, TraEntry]:
        """Parse TRA file and extract entries."""
        entries = {}

        try:
            encoding = detect_encoding(tra_file)
            with open(tra_file, 'r', encoding=encoding) as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {tra_file}: {e}")
            return entries

        # Pattern for tilde format: @123 = ~text~ [SOUND] or @123 = ~text~
        pattern_tilde = r'(@(\d+)\s*=\s*~([^~]*)~(?:\s*\[([^\]]+)\])?)'
        for match in re.finditer(pattern_tilde, content, re.MULTILINE | re.DOTALL):
            full_line = match.group(1)
            tra_number = int(match.group(2))
            tra_text = match.group(3)
            sound = match.group(4)  # May be None

            entries[tra_number] = TraEntry(
                number=tra_number,
                text=tra_text,
                delimiter='~',
                sound=sound,
                full_line=full_line
            )

        # Pattern for quote format: @123 = "text" [SOUND] or @123 = "text"
        pattern_quote = r'(@(\d+)\s*=\s*"([^"]*)"(?:\s*\[([^\]]+)\])?)'
        for match in re.finditer(pattern_quote, content, re.MULTILINE | re.DOTALL):
            full_line = match.group(1)
            tra_number = int(match.group(2))
            tra_text = match.group(3)
            sound = match.group(4)  # May be None

            # Only add if not already added by tilde pattern
            if tra_number not in entries:
                entries[tra_number] = TraEntry(
                    number=tra_number,
                    text=tra_text,
                    delimiter='"',
                    sound=sound,
                    full_line=full_line
                )

        return entries

    def update_tra_file(self, tra_file: Path):
        """Update a single TRA file with translations."""
        tra_filename = tra_file.name

        if tra_filename not in self.translations:
            print(f"Skipping {tra_filename} (no translations)")
            return

        print(f"Updating {tra_filename}...")

        # Read original file
        try:
            encoding = detect_encoding(tra_file)
            with open(tra_file, 'r', encoding=encoding) as f:
                original_content = f.read()
        except Exception as e:
            print(f"Error reading {tra_file}: {e}")
            return

        # Parse original entries
        original_entries = self.parse_tra_file(tra_file)

        # Get translations for this file
        tra_translations = self.translations[tra_filename]

        # Build replacement content
        updated_content = original_content
        replaced_count = 0

        for tra_number, translation_data in tra_translations.items():
            if tra_number not in original_entries:
                print(f"  Warning: @{tra_number} not found in original file")
                continue

            original_entry = original_entries[tra_number]

            # Determine if we have gendered or neutral translation
            male_text = translation_data.get('male')
            female_text = translation_data.get('female')
            neutral_text = translation_data.get('neutral')

            # Build replacement string
            new_entry = self._build_tra_entry(
                tra_number,
                male_text,
                female_text,
                neutral_text,
                original_entry.delimiter,
                original_entry.sound
            )

            # Replace in content
            updated_content = updated_content.replace(original_entry.full_line, new_entry)
            replaced_count += 1

        # Write updated content
        output_file = self.output_folder / tra_filename
        try:
            # Always use UTF-8 for output since we're adding Russian text
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"  Updated {replaced_count} entries in {output_file}")
        except Exception as e:
            print(f"Error writing {output_file}: {e}")

    def _build_tra_entry(self, tra_number: int, male_text: Optional[str],
                        female_text: Optional[str], neutral_text: Optional[str],
                        delimiter: str, sound: Optional[str]) -> str:
        """Build TRA entry string from translation data."""

        # Use neutral if available, otherwise use gendered
        if neutral_text:
            # Single translation
            text = neutral_text
            if sound:
                return f"@{tra_number} = {delimiter}{text}{delimiter} [{sound}]"
            else:
                return f"@{tra_number} = {delimiter}{text}{delimiter}"

        elif male_text and female_text:
            # Gendered translation
            if male_text == female_text:
                # Same for both genders
                if sound:
                    return f"@{tra_number} = {delimiter}{male_text}{delimiter} [{sound}]"
                else:
                    return f"@{tra_number} = {delimiter}{male_text}{delimiter}"
            else:
                # Different for male/female
                if sound:
                    return f"@{tra_number} = {delimiter}{male_text}{delimiter} [{sound}] {delimiter}{female_text}{delimiter} [{sound}]"
                else:
                    return f"@{tra_number} = {delimiter}{male_text}{delimiter} {delimiter}{female_text}{delimiter}"

        elif male_text:
            # Only male text available
            if sound:
                return f"@{tra_number} = {delimiter}{male_text}{delimiter} [{sound}]"
            else:
                return f"@{tra_number} = {delimiter}{male_text}{delimiter}"

        else:
            # No translation available
            return f"@{tra_number} = {delimiter}[NO TRANSLATION]{delimiter}"

    def update_all_tra_files(self):
        """Update all TRA files in the folder."""
        if not self.tra_folder.exists():
            print(f"Error: TRA folder '{self.tra_folder}' does not exist")
            return

        tra_files = list(self.tra_folder.glob("*.tra"))
        if not tra_files:
            print(f"No TRA files found in '{self.tra_folder}'")
            return

        print(f"Found {len(tra_files)} TRA files to update")

        for tra_file in tra_files:
            try:
                self.update_tra_file(tra_file)
            except Exception as e:
                print(f"Error processing {tra_file.name}: {e}")

        print("\nUpdate completed!")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Update TRA files with translations from CSV files')
    parser.add_argument('tra_folder', help='Folder containing original TRA files')
    parser.add_argument('csv_folder', help='Folder containing translated CSV files')
    parser.add_argument('--output', help='Output folder for updated TRA files (default: same as tra_folder)')

    args = parser.parse_args()

    updater = TraUpdater(
        tra_folder=args.tra_folder,
        csv_folder=args.csv_folder,
        output_folder=args.output
    )

    updater.load_translations_from_csvs()
    updater.update_all_tra_files()


if __name__ == "__main__":
    main()
