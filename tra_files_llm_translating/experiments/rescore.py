#!/usr/bin/env python3
"""Rescore saved replies with the current checks, without new model requests.

Walks ROOT for runs.jsonl files whose folder is named after a dataset (inkgallery or a
fixture name, as the batch runners write them) and scores every stored translation again.
Rejected or skipped replies stay failed: rescoring never salvages them. Writes
rescored.csv in ROOT and prints old/new totals per model and dataset.
"""

import argparse
import csv
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from diagnose_translation import Experiment
from run_all import load

SCRIPT_DIR = Path(__file__).resolve().parent


def checks_for(name):
    path = SCRIPT_DIR / 'inkgallery_checks.json' if name == 'inkgallery' else SCRIPT_DIR / 'fixtures' / name / 'checks.json'
    return path if path.exists() else None


def scorer(checks):
    with tempfile.TemporaryDirectory() as unused_out:  # Experiment requires an output folder; nothing is written.
        return Experiment(argparse.Namespace(checks=str(checks), actors=None, dictionary=str(SCRIPT_DIR.parent / 'dict.csv'),
                                             url='http://localhost:11434', num_ctx='8192', seed=None, dry_run=False,
                                             out=unused_out, models=[], prompts=[], scopes=[], think=[],
                                             temperatures=[], repeats=0))


def rescore(root):
    totals = defaultdict(lambda: [0, 0, 0, 0, set()])  # old ok, old expected, new ok, new expected, versions
    for path in sorted(Path(root).rglob('runs.jsonl')):
        checks = checks_for(path.parent.name)
        if checks is None:
            print(f'skipped {path}: no checks for dataset {path.parent.name!r}', file=sys.stderr)
            continue
        e = scorer(checks)
        for record in load(path.parent):
            config = record['config']
            key = (str(path.parent.parent.relative_to(root)), config['model'], config['think'], config['prompt'],
                   path.parent.name)
            new = [c for line in record['targets']
                   for c in e.score(line, record['gender'],
                                    None if record['error'] else record['translations'].get(line))]
            total = totals[key]
            total[0] += sum(c['ok'] for c in record['checks'])
            total[1] += len(record['checks'])
            total[2] += sum(c['ok'] for c in new)
            total[3] += len(new)
            total[4].add(record.get('evaluation_version', 'legacy'))
    out = Path(root) / 'rescored.csv'
    with out.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['folder', 'model', 'think', 'prompt', 'dataset', 'old_versions', 'old_ok', 'old_expected',
                         'new_version', 'new_ok', 'new_expected'])
        for key, (old_ok, old_n, new_ok, new_n, versions) in sorted(totals.items()):
            version = json.loads(checks_for(key[4]).read_text(encoding='utf-8')).get('version')
            writer.writerow(list(key) + [';'.join(sorted(versions)), old_ok, old_n, version, new_ok, new_n])
            print(f'{key[1]:45} {key[4]:26} {old_ok:4}/{old_n:<4} -> {new_ok:4}/{new_n}')
    print(f'Wrote {out}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('root', help='a results folder, e.g. results/non-thinking-20261028-013515')
    rescore(parser.parse_args().root)
    return 0


if __name__ == '__main__':
    sys.exit(main())
