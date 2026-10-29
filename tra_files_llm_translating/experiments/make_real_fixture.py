#!/usr/bin/env python3
"""Create a real-mod evaluation fixture skeleton from one parsed dialogue CSV.

Input: a dialogue CSV written by parse_d_grammar.py (one connected dialogue) and the
actors CSV used for translation. Output: real_set/<name>/ with input.csv, a checks.json
in which every line is a scored target (only global checks until you add line checks),
and reference.csv with empty Russian columns for a person to fill and review.
See real_set/README.md.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translation_common import DIALOGUE_COLUMNS, female_source, read_csv, write_csv  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCE_COLUMNS = ['Line_ID', 'Actor', 'English', 'English_Female', 'Russian_Male', 'Russian_Female', 'Review_Notes']


def make(dialogue, actors, name, source, root=SCRIPT_DIR / 'real_set'):
    folder = Path(root) / name
    if folder.exists():
        raise ValueError(f'{folder} already exists; never overwrite a reviewed fixture')
    header, rows = read_csv(dialogue, DIALOGUE_COLUMNS)
    if header[:6] != DIALOGUE_COLUMNS:
        raise ValueError('Dialogue columns must follow the parser order')
    ids = [r['Line_ID'] for r in rows]
    if not rows or len(set(ids)) != len(ids) or not all(ids):
        raise ValueError('Expected a nonempty dialogue with unique Line_IDs')
    folder.mkdir(parents=True)
    shutil.copyfile(dialogue, folder / 'input.csv')
    shutil.copyfile(actors, folder / 'actors.csv')
    checks = {
        'version': f'{name}-v1',
        'provenance': f'Real mod dialogue: {source}. Reference written/reviewed by a person; '
                      'record reviewer and date in README.md before use.',
        'input': 'input.csv', 'actors': 'actors.csv',
        'all': [{'name': 'no untranslated Latin text outside engine tokens', 'no_latin': True}],
        'allowed_latin': [],
        'pair_review': {'allowed_changes': []},
        # Every line is a target, so outputs.csv shows all of them for manual review.
        'lines': {line_id: {} for line_id in ids},
    }
    (folder / 'checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write_csv(folder / 'reference.csv', REFERENCE_COLUMNS, [
        dict(Line_ID=r['Line_ID'], Actor=r['Actor'], English=r['Dialogue_Text'],
             English_Female=female_source(r, r['Dialogue_Text']) if female_source(r, r['Dialogue_Text']) != r['Dialogue_Text']
             else '', Russian_Male='', Russian_Female='', Review_Notes='') for r in rows])
    (folder / 'README.md').write_text(
        f'# {name}\n\nSource: {source}\n\nStatus: **reference not reviewed yet.**\n\n'
        'Reviewer:\nReview date:\n\nNotes on speakers, addressees and context:\n', encoding='utf-8')
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('dialogue', help='one dialogue CSV from parse_d_grammar.py')
    parser.add_argument('actors', help='actors CSV (name,gender description)')
    parser.add_argument('name', help='fixture folder name, e.g. mymod_innkeeper')
    parser.add_argument('--source', required=True, help='mod name/version and D/TRA file, for provenance')
    args = parser.parse_args()
    try:
        print(f'Created {make(args.dialogue, args.actors, args.name, args.source)}')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
