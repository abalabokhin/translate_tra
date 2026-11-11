"""Export a completed real-dialogue A/B dataset for human review; never overwrite reviews."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from translation_common import female_source


def export(run, dataset, output):
    log = run / dataset / 'runs.jsonl'
    records = [json.loads(line) for line in log.read_text().splitlines()]
    by_key = {(r['config']['prompt'], r['config']['repeat'], r['gender']): r for r in records}
    prompts = ['production', 'production-nouns']
    expected = {(p, n, g) for p in prompts for n in range(1, 4) for g in ['male', 'female']}
    if len(records) != 12 or set(by_key) != expected:
        raise ValueError('Dataset is incomplete or contains duplicate records; no review export written')
    source = run / 'snapshot/tra_files_llm_translating/experiments/real_set' / dataset
    with (source / 'input.csv').open(encoding='utf-8-sig', newline='') as handle:
        inputs = list(csv.DictReader(handle))
    with (source / 'reference.csv').open(encoding='utf-8-sig', newline='') as handle:
        references = {r['Line_ID']: r for r in csv.DictReader(handle)}
    fields = ['Fixture', 'Model', 'Prompt', 'Repeat', 'Line_ID', 'Actor', 'Predecessors', 'TRA_Source',
              'English_Male', 'English_Female', 'Reference_Male', 'Reference_Female',
              'Russian_Male', 'Russian_Female', 'Male_Error', 'Female_Error',
              'Failed_Checks_Male', 'Failed_Checks_Female', 'Pair_Wording_Flag',
              'Saved_Male_Reused', 'User_Review']
    rows = []
    for line in inputs:
        key = line['Line_ID']
        reference = references[key]
        for prompt in prompts:
            for repeat in range(1, 4):
                male, female = [by_key[(prompt, repeat, gender)] for gender in ['male', 'female']]
                for record in [male, female]:
                    if not record['error']:
                        assert key in record['translations']
                pair = next((p for p in female.get('pair_reviews', []) if p['line'] == key), {})
                row = dict(Fixture=dataset, Model=male['config']['model'], Prompt=prompt, Repeat=str(repeat),
                           Line_ID=key, Actor=line['Actor'], Predecessors=line['Predecessors'],
                           TRA_Source=line['Additional_Info'], English_Male=line['Dialogue_Text'],
                           English_Female=female_source(line, line['Dialogue_Text']),
                           Reference_Male=reference['Russian_Male'], Reference_Female=reference['Russian_Female'],
                           Russian_Male=male['translations'].get(key, ''), Russian_Female=female['translations'].get(key, ''),
                           Male_Error=male['error'] or '', Female_Error=female['error'] or '',
                           Pair_Wording_Flag=(pair.get('reason', '') if pair.get('status') == 'review' else ''),
                           Saved_Male_Reused='yes' if male.get('recovered_from') else '', User_Review='')
                for gender, record in [('Male', male), ('Female', female)]:
                    row['Failed_Checks_' + gender] = '; '.join(c['check'] for c in record['checks']
                                                            if c['line'] == key and not c['ok'])
                rows.append(row)
    assert len(rows) == len(inputs) * 6
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with output.open(encoding='utf-8-sig', newline='') as handle:
        assert list(csv.DictReader(handle)) == rows
    metadata = dict(run=str(run), dataset=dataset, rows=len(rows), human_review='pending',
                    source_log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
                    source_reference_sha256=hashlib.sha256((source / 'reference.csv').read_bytes()).hexdigest(),
                    review_sha256_before_user_edits=hashlib.sha256(output.read_bytes()).hexdigest(),
                    note='Unlisted wording flags are review prompts, not automatic errors. Raw rejected replies remain in runs.jsonl.')
    output.with_suffix('.meta.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'Wrote {output}: {len(rows)} source/prompt/repeat rows, both Russian columns')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('dataset')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    export(args.run, args.dataset, args.output)
