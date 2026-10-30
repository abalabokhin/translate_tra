"""One-off manual daemon-restart recovery. Reuse the sole saved male reply; no inference retries.

The original interrupted run remains intact. A fresh run folder contains one
explicitly attributed replay of its successful male reply, plus new requests for
all unrecorded slots. Ordinary experiment runners gain no resume/retry behavior.
"""
import sys,json,hashlib,shutil,argparse
from pathlib import Path
REPO=Path('/home/paladin/source/translate_tra')
BASE=REPO/'tra_files_llm_translating/experiments'
sys.path.insert(0,str(BASE))
import run_prompt_ab as runner
from diagnose_translation import Experiment
from run_all import Ollama
from run_translate_verify import model_facts,now
OLD=BASE/'prompt_ab/20261029-220151'
OUT=BASE/'prompt_ab/20261029-220151-recovered'
rows=[json.loads(l) for l in (OLD/'inkgallery_beholder/runs.jsonl').read_text().splitlines()]
assert len(rows)==1 and rows[0]['gender']=='male' and not rows[0]['error']
saved=rows[0]
old_manifest=json.loads((OLD/'manifest.json').read_text())
for path,expected in json.loads((OLD/'input_runtime_sha256.json').read_text()).items():
 assert hashlib.sha256((REPO/path).read_bytes()).hexdigest()==expected,path
_,facts=model_facts(Ollama(old_manifest['settings']['url']),old_manifest['settings']['model'])
assert facts['digest']==old_manifest['model']['digest'],'Model digest changed'
OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'manifest.json').exists(),'Use only once; no automatic resume'
shutil.copyfile(__file__,OUT/Path(__file__).name)
shutil.copytree(OLD/'snapshot',OUT/'snapshot')
shutil.copyfile(OLD/'input_runtime_sha256.json',OUT/'input_runtime_sha256.json')
recovery=dict(recovery_utc=now(),reason='Codex server restart ended the experiment client process.',
 original=str(OLD.relative_to(REPO)),saved_records=1,reused_male_request=saved['config'],
 in_flight_female='No completed record survived; output unavailable and unscored. May have reached server before interruption.',
 planned_new_requests=35,completed_records_not_rerun=True,
 ordinary_runner_changed=False)
(OUT/'RECOVERY.json').write_text(json.dumps(recovery,indent=2)+'\n')
shutil.copyfile(OLD/'manifest.json',OLD/'manifest.before_recovery.json')
old_manifest.update(status='interrupted_by_daemon_restart',finished_utc=now(),recovery=recovery,
 continuation=str(OUT.relative_to(REPO)))
runner.save(OLD,old_manifest)
with (OLD/'REPORT.md').open('a') as f:f.write('\nInterrupted after one saved male reply; no full dataset completed. See RECOVERY.json in '+str(OUT.relative_to(BASE))+' for the fresh continuation.\n')
original_chat=Experiment.chat
original_record=Experiment.record
reused=[]
def chat(self,config,system,user,schema):
 if self.out.name=='inkgallery_beholder' and config==saved['config'] and not any('male_translation' in l for l in json.loads(user)['dialogue']):
  assert not reused,'Saved record reused more than once'
  assert saved['request']['messages']==[dict(role='system',content=system),dict(role='user',content=user)]
  assert saved['request']['format']==schema
  assert saved['request']['options']==dict(num_ctx=self.context_for(config['model']),num_predict=-1)
  reused.append(True)
  print('  REUSE successful male response from interrupted run; NO MODEL REQUEST',flush=True)
  result={k:saved.get(k) for k in ['error','done_reason','eval_count','prompt_eval_count','wall_seconds','gpu']}
  result['message']={'content':saved['content'],'thinking':saved.get('thinking')}
  result['recovered_from']=str((OLD/'inkgallery_beholder/runs.jsonl').relative_to(REPO))
  return saved['request'],result
 return original_chat(self,config,system,user,schema)
def record(config,gender,targets,payload,result):
 value=original_record(config,gender,targets,payload,result)
 if result.get('recovered_from'):value['recovered_from']=result['recovered_from']
 return value
Experiment.chat=chat
Experiment.record=staticmethod(record)
sys.argv=['run_prompt_ab.py','--datasets',old_manifest['settings']['datasets'],'--out',str(OUT)]
try:
 status=runner.main()
 assert reused==[True]
finally:
 if (OUT/'manifest.json').exists():
  manifest=json.loads((OUT/'manifest.json').read_text());manifest['recovery']=recovery;runner.save(OUT,manifest)
sys.exit(status)
