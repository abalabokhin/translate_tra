"""One-off full comparison coordinator. Preserve attempted pairs; never retry replies."""
import csv
import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
sys.path.insert(0, str(REPO / 'tra_files_llm_translating/experiments'))
import run_codex_translation as runner

OUT = BASE / 'results'
STATE = BASE / 'COMPARISON.json'
PRE = json.loads((BASE / 'PRE_RUN.json').read_text())
MODELS = PRE['models']
MODES = PRE['modes']


def key(record):
    return tuple(record[k] for k in ('dataset', 'model', 'mode', 'repeat'))


def check_frozen():
    for name, digest in PRE['sha256'].items():
        if hashlib.sha256((REPO / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen input/runtime changed: ' + name)


def folder_for(name, model, mode, repeat):
    return OUT / name / f'model-{MODELS.index(model) + 1}' / mode / str(repeat)


def collect(e, record, folder):
    calls = [json.loads(p.read_text()) for p in sorted(folder.glob('*/call.json'))]
    record['calls'] = calls
    translated = {}
    valid = folder / 'validated.json'
    if valid.exists():
        translated = json.loads(valid.read_text())
    elif record['mode'] == 'two-pass':
        # Preserve a valid male pass even if the female reply was rejected.
        for gender in ('male', 'female'):
            response = folder / gender / 'response.txt'
            call = next((c for p, c in [(p, json.loads(p.read_text())) for p in folder.glob('*/call.json')]
                         if p.parent.name == gender), None)
            if response.exists() and call and call['status'] == 'completed':
                parsed = {'translations': {}}
                e.parse(parsed, response.read_text(), e.rows[1:], gender)
                if not parsed.get('error'):
                    translated[gender] = parsed['translations']
    targets = set(e.checks['lines'])
    record['checks'] = [c for gender in ('male', 'female') for line in sorted(targets)
                        for c in e.score(line, gender, translated.get(gender, {}).get(line))]
    record['pair_reviews'] = e.review_pairs(e.rows[1:], targets, translated.get('male'), translated.get('female', {}))
    record['validated_genders'] = list(translated)
    return translated


def save(state):
    runner.save(STATE, state)
    lines = ['# Full Codex comparison', '', f"Status: {state['status']}", '',
             'Invalid replies are retained and not retried. Missing/invalid gender passes fail all expected checks.',
             'Targeted checks are not overall quality; assistant/human review pending.', '',
             '| Dataset | Model | Mode | Repeat | Status | Checks |', '|---|---|---|---:|---|---|']
    for r in state['runs']:
        checks = r.get('checks', [])
        lines.append(f"| {r['dataset']} | {r['model']} | {r['mode']} | {r['repeat']} | {r['status']} | {sum(c['ok'] for c in checks)}/{len(checks)} |")
    if state.get('error'):
        lines += ['', 'Error: ' + state['error']]
    (BASE / 'REPORT.md').write_text('\n'.join(lines) + '\n')


def main():
    if STATE.exists():
        raise ValueError('Coordinator already launched; inspect saved state, do not auto-resume')
    check_frozen()
    original = json.loads((OUT / 'manifest.json').read_text())
    state = {'status': 'running', 'started_utc': runner.now(), 'settings': PRE,
             'reason': 'Original runner stopped on second reply structural rejection; continue unattempted cases only.',
             'runs': original['runs'], 'manual_review': 'pending'}
    for r in state['runs']:
        if r['status'] == 'failed':
            r['status'] = 'rejected'
            r['failure_kind'] = 'structural'
    attempted = {key(r) for r in state['runs']}
    try:
        for name, checks in runner.datasets():
            e = runner.experiment(checks, OUT / 'inputs' / name)
            for r in state['runs']:
                if r['dataset'] == name:
                    collect(e, r, folder_for(*key(r)))
            for model in MODELS:
                for mode in MODES:
                    for repeat in range(1, PRE['repeats'] + 1):
                        if (name, model, mode, repeat) in attempted:
                            continue
                        check_frozen()
                        folder = folder_for(name, model, mode, repeat)
                        if folder.exists():
                            raise ValueError('Unrecorded attempted directory exists: ' + str(folder))
                        r = {'dataset': name, 'model': model, 'mode': mode, 'repeat': repeat,
                             'status': 'running', 'evaluation_version': e.checks.get('version', 'unversioned')}
                        state['runs'].append(r)
                        save(state)
                        print(f"[{len(state['runs'])}/96] {name} {model} {mode} repeat {repeat}", flush=True)
                        try:
                            calls, translated = runner.translate(e, mode, model, 'codex', folder)
                            if any(c['status'] != 'completed' for c in calls):
                                raise RuntimeError('CLI failure; inspect call.json. Stopping without retry.')
                            if set(translated) != {'male', 'female'}:
                                raise RuntimeError('Incomplete CLI result; stopping without retry.')
                            runner.save(folder / 'validated.json', translated)
                            r['status'] = 'completed'
                        except ValueError as exc:
                            r.update(status='rejected', failure_kind='structural', error=str(exc))
                            print('  REJECTED (retained, no retry): ' + str(exc), flush=True)
                        collect(e, r, folder)
                        save(state)
        state['status'] = 'finished'
    except KeyboardInterrupt:
        state.update(status='interrupted', error='Interrupted; no automatic resume')
        if state['runs'][-1]['status'] == 'running':
            state['runs'][-1]['status'] = 'interrupted'
    except Exception as exc:
        state.update(status='failed', error=str(exc))
        print('STOPPED: ' + str(exc), flush=True)
    finally:
        state['finished_utc'] = runner.now()
        save(state)
    return 0 if state['status'] == 'finished' else 1


if __name__ == '__main__':
    sys.exit(main())
