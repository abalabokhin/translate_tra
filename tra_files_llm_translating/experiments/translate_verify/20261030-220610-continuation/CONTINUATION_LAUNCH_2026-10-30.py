"""Explicitly authorized continuation; fresh datasets, then pending Sewers A/B.
No automatic retries or resume. Preserve the completed InkGallery results.
"""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[1]
QUEUE = BASE / 'VERIFY_QUEUE_2026-10-29.json'
OLD = BASE / 'translate_verify/20261030-095325'
NAMES = ['ambiguous_addressees', 'multiple_npcs', 'original_female_variants',
         'reused_strings', 'inkgallery_beholder', 'inkgallery_moon_sisters', 'inkgallery_sewers']
sys.path.insert(0, str(BASE))
import run_translate_verify as runner
from run_all import Ollama


def now():
    return datetime.now(timezone.utc).isoformat()


def save():
    QUEUE.write_text(json.dumps(state, indent=2) + '\n')


def main():
    global state
    state = json.loads(QUEUE.read_text())
    if state['state'] not in ('stopped', 'interrupted_or_failed'):
        raise RuntimeError('Continuation already running or finished: ' + state['state'])
    frozen = json.loads((OLD / 'manifest.json').read_text())
    hashes = dict(state['input_runtime_sha256'], **frozen['sha256'])
    for path, expected in hashes.items():
        if hashlib.sha256((REPO / path).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Frozen input drift: ' + path)
    client = Ollama('http://localhost:11434')
    if client.get('/api/ps').get('models'):
        raise RuntimeError('Ollama is no longer idle; inspect before launching')
    for facts in frozen['models'].values():
        _, installed = runner.model_facts(client, facts['tag'])
        if installed['digest'] != facts['digest']:
            raise RuntimeError('Model digest drift: ' + facts['tag'])
    out = BASE / 'translate_verify' / (datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-continuation')
    out.mkdir(exist_ok=False)
    shutil.copyfile(__file__, out / Path(__file__).name)
    shutil.copytree(OLD / 'snapshot', out / 'snapshot')
    (out / 'input_runtime_sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
    (out / 'CONTINUATION.json').write_text(json.dumps(dict(
        source_run=str(OLD.relative_to(REPO)), datasets=NAMES,
        completed_inkgallery_reused=True,
        ambiguous_addressees='Fresh run as requested; prior verifier failed transport, no successful correction.',
        offline_tests='59 passed', started_utc=now()), indent=2) + '\n')
    state['previous_run'] = {k: state[k] for k in
                             ('state', 'queue_pid', 'output', 'ended_utc', 'error', 'stopped_note') if k in state}
    state.update(state='running', queue_pid=os.getpid(), continuation_started_utc=now(),
                 continuation_output=str(out.relative_to(REPO)))
    save()
    print('CONTINUATION:', out, flush=True)
    try:
        sys.argv = ['run_translate_verify.py', '--datasets', ','.join(NAMES), '--out', str(out)]
        result = runner.main()
        final = json.loads((out / 'manifest.json').read_text())
        if result or final['status'] != 'finished':
            raise RuntimeError('Continuation did not finish successfully')
        state.update(state='finished', continuation_finished_utc=now())
        save()
    except BaseException as exc:
        state.update(state='interrupted_or_failed', continuation_ended_utc=now(), continuation_error=repr(exc))
        save()
        raise
    print('Starting ten pending Sewers A/B requests', flush=True)
    runpy.run_path(str(BASE / 'prompt_ab/TRANSPORT_CONTINUATION_LAUNCH_2026-10-30.py'), run_name='__main__')


if __name__ == '__main__':
    main()
