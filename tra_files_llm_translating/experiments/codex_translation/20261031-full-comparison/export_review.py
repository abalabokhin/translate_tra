"""Export accepted and rejected raw translations for review; never changes scores."""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
sys.path.insert(0, str(REPO / 'tra_files_llm_translating/experiments'))
import run_codex_translation as runner
from translation_common import female_source, merge_dialogue_rows


def export():
    state = json.loads((BASE / 'COMPARISON.json').read_text())
    groups = {}
    for name, checks in runner.datasets():
        e = runner.experiment(checks, BASE / 'results/inputs' / name)
        merged, slots = merge_dialogue_rows(e.rows)
        for run in state['runs']:
            if run['dataset'] != name or run['status'] == 'running':
                continue
            folder = BASE / 'results' / name / f"model-{state['settings']['models'].index(run['model'])+1}" / run['mode'] / str(run['repeat'])
            raw = {}
            if run['mode'] == 'both':
                path = folder / 'both/response.txt'
                if path.exists():
                    try:
                        pairs = json.loads(path.read_text())['translations']
                        for gender in ('male', 'female'):
                            raw[gender] = {k: v.get(gender) for k, v in pairs.items() if isinstance(v, dict)}
                    except (ValueError, TypeError, KeyError, AttributeError):
                        pass
            else:
                for gender in ('male', 'female'):
                    path = folder / gender / 'response.txt'
                    if path.exists():
                        try:
                            raw[gender] = json.loads(path.read_text())['translations']
                        except (ValueError, TypeError, KeyError):
                            pass
                if 'female' in raw:
                    for key in runner.DialogTranslator._empty_female_ids(merged):
                        raw['female'][key] = ''
            for row in e.rows[1:]:
                slot = str(slots[row[1]])
                male = raw.get('male', {}).get(slot)
                female = raw.get('female', {}).get(slot)
                if not isinstance(male, str) and not isinstance(female, str):
                    continue
                identity = (name, row[1], male, female)
                if identity not in groups:
                    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()[:16]
                    groups[identity] = dict(review_id=digest, dataset=name, Line_ID=row[1],
                        English_Male=row[3], English_Female=female_source(dict(zip(e.header,row)),row[3]),
                        Russian_Male=male, Russian_Female=female, configurations=[])
                groups[identity]['configurations'].append(f"{run['model']} {run['mode']} r{run['repeat']} ({run['status']})")
    fields = ['review_id','dataset','Line_ID','English_Male','English_Female','Russian_Male','Russian_Female','configurations']
    with (BASE/'REVIEW_UNIQUE.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in groups.values():
            writer.writerow(dict(row,configurations='; '.join(row['configurations'])))
    print('Unique raw line pairs for review:',len(groups),'from',len(state['runs']),'attempted pairs')


if __name__ == '__main__':
    export()
