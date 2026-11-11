"""Export one completed real-dialogue translate/verify dataset; never overwrite user reviews."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from translation_common import female_source, merge_dialogue_rows, read_csv


def export(run, dataset, output):
    manifest = json.loads((run / 'manifest.json').read_text())
    repeats = manifest['settings']['repeats']
    entries = [r for r in manifest.get('translate_verify', []) if r['dataset'] == dataset]
    if len(entries) != repeats:
        raise ValueError('Dataset verification is incomplete; no review export written')
    stage = run / 'translate-verify' / dataset
    log = stage / 'translation/runs.jsonl'
    records = [json.loads(line) for line in log.read_text().splitlines()]
    translations = {(r['config']['repeat'], r['gender']): r for r in records}
    assert len(translations) == 2 * repeats == len(records)
    source = run / 'snapshot/tra_files_llm_translating/experiments/real_set' / dataset
    header, inputs = read_csv(source / 'input.csv', ['Line_ID', 'Dialogue_Text'])
    _, refs = read_csv(source / 'reference.csv', ['Line_ID', 'Russian_Male', 'Russian_Female'])
    references = {r['Line_ID']: r for r in refs}
    merged, slots = merge_dialogue_rows([header] + [[r[h] for h in header] for r in inputs])
    table = {}
    if (stage / 'before_after.csv').exists():
        with (stage / 'before_after.csv').open(encoding='utf-8-sig', newline='') as handle:
            table = {(int(r['repeat']), r['Line_ID'], r['gender']): r for r in csv.DictReader(handle)}
    verifier = {}
    if (stage / 'verifier.jsonl').exists():
        verifier = {r['repeat']: r for r in map(json.loads, (stage / 'verifier.jsonl').read_text().splitlines())}
    fields = ['Fixture', 'Repeat', 'Line_ID', 'Actor', 'Predecessors', 'TRA_Source',
              'English_Male', 'English_Female', 'Reference_Male', 'Reference_Female',
              'Translated_Male', 'Verified_Male', 'Translated_Female', 'Verified_Female',
              'Changed_Male', 'Changed_Female', 'Translator_Male_Error', 'Translator_Female_Error',
              'Verifier_Error', 'Correction_Notes', 'Failed_Checks_Before', 'Failed_Checks_After', 'User_Review']
    rows = []
    for line in inputs:
        key = line['Line_ID']
        ref = references[key]
        for repeat in range(1, repeats + 1):
            entry = next(r for r in entries if r['repeat'] == repeat)
            check = verifier.get(repeat, {})
            notes = []
            for decision in check.get('decisions', []):
                if decision['id'] == str(slots[key]):
                    outcome = ', '.join(f'{k}: {v}' for k, v in decision['outcome'].items())
                    notes.append(f"{decision['column']}/{decision['category']}: {decision['reason']} ({outcome})")
            row = dict(Fixture=dataset, Repeat=str(repeat), Line_ID=key, Actor=line['Actor'],
                       Predecessors=line['Predecessors'], TRA_Source=line['Additional_Info'],
                       English_Male=line['Dialogue_Text'], English_Female=female_source(line, line['Dialogue_Text']),
                       Reference_Male=ref['Russian_Male'], Reference_Female=ref['Russian_Female'],
                       Verifier_Error=entry.get('skipped') or check.get('error') or '',
                       Correction_Notes='\n'.join(notes), User_Review='')
            before, after = [], []
            for gender in ['male', 'female']:
                record = translations[(repeat, gender)]
                cell = table.get((repeat, key, gender), {})
                title = gender.title()
                row['Translated_' + title] = cell.get('translated', record['translations'].get(key, '') if not record['error'] else '')
                row['Verified_' + title] = cell.get('verified', '')
                row['Changed_' + title] = cell.get('changed', '')
                row['Translator_' + title + '_Error'] = record['error'] or ''
                if cell.get('failed_checks_before'):
                    before.append(gender + ': ' + cell['failed_checks_before'])
                if cell.get('failed_checks_after'):
                    after.append(gender + ': ' + cell['failed_checks_after'])
            row['Failed_Checks_Before'], row['Failed_Checks_After'] = '\n'.join(before), '\n'.join(after)
            rows.append(row)
    assert len(rows) == len(inputs) * repeats
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with output.open(encoding='utf-8-sig', newline='') as handle:
        assert list(csv.DictReader(handle)) == rows
    output.with_suffix('.meta.json').write_text(json.dumps(dict(run=str(run), dataset=dataset, rows=len(rows),
        human_review='pending', source_log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
        review_sha256_before_user_edits=hashlib.sha256(output.read_bytes()).hexdigest()), indent=2) + '\n')
    print(f'Wrote {output}: {len(rows)} source/repeat rows, both before/after Russian pairs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('dataset')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    export(args.run, args.dataset, args.output)
