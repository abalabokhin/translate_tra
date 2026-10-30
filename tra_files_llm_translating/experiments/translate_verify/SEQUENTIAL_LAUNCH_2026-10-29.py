"""One-off sequential launch of the authorized verify experiment after A/B completes.
No inference retry, timeout, resume, context cap, or translator change is introduced.
"""
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO=Path('/home/paladin/source/translate_tra')
BASE=REPO/'tra_files_llm_translating/experiments'
AB=BASE/'prompt_ab/20261029-220151-recovered'
STATUS=BASE/'VERIFY_QUEUE_2026-10-29.json'
AB_PID=59881
NAMES=['inkgallery','ambiguous_addressees','multiple_npcs','original_female_variants','reused_strings',
       'inkgallery_beholder','inkgallery_moon_sisters','inkgallery_sewers']
sys.path.insert(0,str(BASE))
import run_translate_verify as runner

def now():return datetime.now(timezone.utc).isoformat()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save():STATUS.write_text(json.dumps(state,indent=2)+'\n')

code=[BASE/name for name in ['run_translate_verify.py','diagnose_translation.py','run_all.py','run_non_thinking.py']]
code += [BASE.parent/name for name in ['translate_dialogs.py','translation_common.py','tra_format.py']]
inputs={BASE.parent/'dict.csv'}
for name,checks in runner.datasets(NAMES):
    definition=json.loads(checks.read_text())
    inputs.update([checks,(checks.parent/definition['input']).resolve(),(checks.parent/definition['actors']).resolve()])
    if (checks.parent/'reference.csv').exists():inputs.add(checks.parent/'reference.csv')
hashes={str(p.relative_to(REPO)):digest(p) for p in sorted(set(code)|inputs)}
state=dict(state='waiting_for_ab',armed_utc=now(),queue_pid=os.getpid(),ab_pid=AB_PID,
           waiting_on=str(AB.relative_to(REPO)),datasets=NAMES,input_runtime_sha256=hashes,
           settings='Mistral default/no thinking; Gemma4 thinking; both native contexts; num_predict=-1; 3 repeats',
           rule='Start exactly once after A/B finishes. Exit on interruption/input drift; no automatic resume/retry.')
save()
print('QUEUED: native-context translate + verify after A/B; no model calls while waiting',flush=True)
try:
    while True:
        manifest=json.loads((AB/'manifest.json').read_text())
        if manifest['status']=='finished':break
        if manifest['status']!='running':raise RuntimeError('A/B did not finish: '+manifest['status'])
        os.kill(AB_PID,0)
        time.sleep(10)
    for path,expected in hashes.items():
        if digest(REPO/path)!=expected:raise RuntimeError('Input/runtime changed while waiting: '+path)
    frozen=json.loads((BASE/'REAL_SET_PREINFERENCE_2026-10-29.json').read_text())
    for path,expected in frozen['sha256'].items():
        if digest(BASE/path)!=expected:raise RuntimeError('Real fixture changed after freeze: '+path)
    out=BASE/'translate_verify'/datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,out/Path(__file__).name)
    paths=set(code)|inputs
    paths.update(p for folder in ['fixtures','real_set'] for p in (BASE/folder).rglob('*') if p.is_file())
    for path in sorted(paths):
        relative=path.relative_to(REPO);target=out/'snapshot'/relative
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    (out/'input_runtime_sha256.json').write_text(json.dumps({str(p.relative_to(REPO)):digest(p) for p in sorted(paths)},indent=2)+'\n')
    state.update(state='running',started_utc=now(),output=str(out.relative_to(REPO)))
    save();(out/'SEQUENCE.json').write_text(json.dumps(state,indent=2)+'\n')
    sys.argv=['run_translate_verify.py','--datasets',','.join(NAMES),'--out',str(out)]
    result=runner.main()
    final=json.loads((out/'manifest.json').read_text())
    if result or final['status']!='finished':raise RuntimeError('Verifier run did not finish successfully')
    state.update(state='finished',finished_utc=now());save()
except BaseException as exc:
    state.update(state='interrupted_or_failed',ended_utc=now(),error=repr(exc));save()
    raise
