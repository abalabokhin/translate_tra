#!/usr/bin/env python3
"""
TRA Update Script
Updates TRA files with translations from translated CSV files
Preserves original formatting, comments, and sounds
"""

import csv
import sys
from pathlib import Path
from typing import Dict, Optional
from collections import defaultdict
from tra_format import TraEntry, parse_tra, read_text, replace_entry
from translation_common import (DIALOGUE_COLUMNS, TRANSLATION_COLUMNS, atomic_write,
                                female_source, parse_reference, read_csv, validate_text)



class TraUpdater:
    """Updates TRA files with translations from CSV files."""

    def __init__(self, tra_folder: str, csv_folder: str, output_folder: str = None):
        self.tra_folder = Path(tra_folder)
        self.csv_folder = Path(csv_folder)
        self.output_folder = Path(output_folder) if output_folder else self.tra_folder

        # Translations storage: tra_filename -> @number -> {'male': text, 'female': text, 'neutral': text}
        self.translations = defaultdict(lambda: defaultdict(dict))

        self.origins = {}  # Track conflicts instead of silently letting the last CSV win.

    def load_translations_from_csvs(self):
        """Load combined CSVs and original male/female or neutral CSVs."""
        if not self.csv_folder.is_dir():
            raise ValueError(f"CSV folder does not exist: {self.csv_folder}")
        csv_files = sorted((p for p in self.csv_folder.iterdir() if p.suffix.casefold() == '.csv'),
                           key=lambda p: p.name.casefold())
        if not csv_files:
            raise ValueError(f"No CSV files in {self.csv_folder}")
        paths = {p.name.casefold(): p for p in csv_files}
        if len(paths) != len(csv_files):
            raise ValueError('CSV filenames differ only by case')
        unused_file = paths.get('_unused_tra_lines.csv')
        combined_files = []
        for path in csv_files:
            if path == unused_file:
                continue
            header, _ = read_csv(path, DIALOGUE_COLUMNS)
            if set(TRANSLATION_COLUMNS) <= set(header):
                combined_files.append(path)
            elif set(TRANSLATION_COLUMNS).intersection(header):
                raise ValueError(f"{path}: incomplete translation columns")
        male_files = [f for f in csv_files if f not in combined_files and f.stem.casefold().endswith('_male')]
        female_files = [f for f in csv_files if f not in combined_files and f.stem.casefold().endswith('_female')]
        neutral_files = [f for f in csv_files if f not in male_files + female_files and f != unused_file]
        for female_file in female_files:
            if female_file.stem[:-7].casefold() + '_male.csv' not in paths:
                raise ValueError(f"{female_file}: missing male partner")
        for male_file in male_files:
            female_file = paths.get(male_file.stem[:-5].casefold() + '_female.csv')
            if female_file is None:
                raise ValueError(f"{male_file}: missing female partner")
            self._load_gendered_dialogue(male_file, female_file)
        for neutral_file in neutral_files:
            self._load_neutral_dialogue(neutral_file)
        if unused_file is not None:
            self._load_unused_lines(unused_file)
        print(f"Loaded translations for {len(self.translations)} TRA files")

    def _load_gendered_dialogue(self, male_file: Path, female_file: Path):
        """Load original male/female pairs without guessing missing rows."""
        male_lines = self._read_dialogue_csv(male_file)
        female_lines = self._read_dialogue_csv(female_file)
        if male_lines.keys() != female_lines.keys():
            raise ValueError(f"{male_file} and {female_file}: line IDs do not match")
        for line_id, male_data in male_lines.items():
            female_data = female_lines[line_id]
            if male_data['metadata'] != female_data['metadata']:
                raise ValueError(f"Gender files disagree on metadata for {line_id}")
            if male_data['tra_ref']:
                self._register(male_data['reference'], male_data['text'], female_data['text'], male_file)

    def _load_neutral_dialogue(self, csv_file: Path):
        """Load neutral legacy CSVs or combined Russian_Male/Russian_Female CSVs."""
        lines = self._read_dialogue_csv(csv_file)
        for data in lines.values():
            if data['tra_ref']:
                self._register(data['reference'], data['text'], data['female_text'], csv_file)

    def _read_dialogue_csv(self, csv_file: Path) -> Dict:
        """Read CSV strictly; models never supply metadata for new translations."""
        header, rows = read_csv(csv_file, DIALOGUE_COLUMNS)
        combined = set(TRANSLATION_COLUMNS) <= set(header)
        lines = {}
        for row in rows:
            line_id = row['Line_ID']
            if not line_id or line_id in lines:
                raise ValueError(f"{csv_file}: empty or duplicate Line_ID {line_id!r}")
            tra_ref = row['TRA_Reference']
            tra_file = tra_number = None
            if tra_ref:
                tra_file, tra_number = parse_reference(row['Additional_Info'])
                if tra_ref != f'@{tra_number}':
                    raise ValueError(f"{csv_file}: reference columns disagree for {line_id}")
            male = row['Russian_Male'] if combined else row['Dialogue_Text']
            female = row['Russian_Female'] if combined else male
            if combined:
                validate_text(row['Dialogue_Text'], male, f'{csv_file}:{line_id}/male')
                validate_text(female_source(row, row['Dialogue_Text']), female, f'{csv_file}:{line_id}/female')
            lines[line_id] = {'text': male, 'female_text': female, 'tra_ref': tra_ref,
                             'tra_file': tra_file, 'tra_number': tra_number,
                             'reference': row['Additional_Info'],
                             'metadata': tuple(row[name] for name in DIALOGUE_COLUMNS if name != 'Dialogue_Text')}
        return lines

    def _load_unused_lines(self, unused_file: Path):
        """Load new gendered standalone text and legacy Russian_Text files."""
        header, rows = read_csv(unused_file, ['Reference', 'English_Text'])
        combined = set(TRANSLATION_COLUMNS) <= set(header)
        if not combined and 'Russian_Text' not in header:
            raise ValueError(f"{unused_file}: missing translation columns")
        for row in rows:
            if combined:
                male, female = row['Russian_Male'], row['Russian_Female']
            else:
                male = female = row['Russian_Text']
                if row['English_Text'].strip() and not male.strip():
                    print(f"Warning: retaining untranslated {row['Reference']}", file=sys.stderr)
                    continue
            validate_text(row['English_Text'], male, f"{unused_file}:{row['Reference']}/male")
            validate_text(female_source(row, row['English_Text']), female, f"{unused_file}:{row['Reference']}/female")
            self._register(row['Reference'], male, female, unused_file)

    def parse_tra_file(self, tra_file: Path) -> Dict[int, TraEntry]:
        """Parse real literals and both gender/sound variants, ignoring comments."""
        return parse_tra(read_text(tra_file))

    def update_tra_file(self, tra_file: Path, write: bool = True):
        """Replace only literal spans, leaving original comments and sounds in place."""
        original_content = read_text(tra_file)
        original_entries = self.parse_tra_file(tra_file)
        tra_translations = self.translations.get(tra_file.name.casefold(), {})
        missing = tra_translations.keys() - original_entries.keys()
        if missing:
            raise ValueError(f"{tra_file}: missing original entries {sorted(missing)}")
        updated_content = original_content
        for number in sorted(tra_translations, key=lambda n: original_entries[n].variants[0].start, reverse=True):
            data = tra_translations[number]
            entry = original_entries[number]
            validate_text(entry.variants[0].text, data['male'], f'{tra_file}:@{number}/male')
            validate_text(entry.variants[-1].text, data['female'], f'{tra_file}:@{number}/female')
            updated_content = replace_entry(updated_content, entry, data['male'], data['female'])
        if parse_tra(updated_content).keys() != original_entries.keys():
            raise ValueError(f"{tra_file}: generated TRA entries differ from original")
        if write:
            atomic_write(self.output_folder / tra_file.name, lambda handle: handle.write(updated_content))
        return updated_content

    def _register(self, reference, male, female, origin):
        filename, number = parse_reference(reference)
        key = filename, number
        existing = self.translations[filename].get(number)
        if existing is not None and (existing['male'], existing['female']) != (male, female):
            raise ValueError(f"Conflicting translations for {filename}:@{number}: {self.origins[key]} and {origin}")
        self.translations[filename][number] = {'male': male, 'female': female}
        self.origins[key] = origin

    def update_all_tra_files(self):
        """Validate referenced files and render everything before writing any output."""
        if not self.tra_folder.is_dir():
            raise ValueError(f"TRA folder does not exist: {self.tra_folder}")
        tra_files = sorted((p for p in self.tra_folder.iterdir() if p.suffix.casefold() == '.tra'),
                           key=lambda p: p.name.casefold())
        if len({p.name.casefold() for p in tra_files}) != len(tra_files):
            raise ValueError('TRA filenames differ only by case')
        missing = self.translations.keys() - {p.name.casefold() for p in tra_files}
        if missing:
            raise ValueError(f"Referenced TRA files not found: {sorted(missing)}")
        plans = [(path.name, self.update_tra_file(path, write=False)
                  if path.name.casefold() in self.translations else read_text(path)) for path in tra_files]
        for filename, content in plans:
            atomic_write(self.output_folder / filename, lambda handle, text=content: handle.write(text))
            print(f"Wrote {self.output_folder / filename}")


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

    try:
        updater.load_translations_from_csvs()
        updater.update_all_tra_files()
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == "__main__":
    main()
