"""One-off continuation of sewer slots that never reached Ollama during the outage.
Wait for verification to finish so model jobs remain sequential. Keep the stalled
production repeat-1 female pass as a serving failure, as the user requested.
"""
import hashlib,json,os,shutil,sys,time
from datetime import datetime,timezone
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
REPO=BASE.parents[1]
OLD=BASE/'prompt_ab/20261029-220151-recovered'
QUEUE=BASE/'AB_TRANSPORT_CONTINUATION_QUEUE_2026-10-30.json'
sys.path.insert(0,str(BASE))
import run_prompt_ab as runner
from diagnose_translation import Experiment
from run_all import Ollama
from run_translate_verify import model_facts

def now():return datetime.now(timezone.utc).isoformat()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
records=[json.loads(l) for l in (OLD/'inkgallery_sewers/runs.jsonl').read_text().splitlines()]
prior={(r['config']['prompt'],r['config']['repeat'],r['gender']):r for r in records}
assert len(prior)==12 and not prior[('production',1,'male')]['error']
assert prior[('production',1,'female')]['error']=='Remote end closed connection without response'
selected=[(p,n) for p in runner.PROMPTS for n in range(1,4) if (p,n)!=('production',1)]
for prompt,repeat in selected:
 assert 'Connection refused' in prior[(prompt,repeat,'male')]['error']
 assert prior[(prompt,repeat,'female')].get('skipped')
frozen=json.loads((BASE/'VERIFY_QUEUE_2026-10-29.json').read_text())['input_runtime_sha256']
state=dict(state='waiting_for_verify',armed_utc=now(),queue_pid=os.getpid(),selected_configs=selected,
 planned_new_requests=10,source_outage_run=str(OLD.relative_to(REPO)),
 excluded='production repeat 1: preserve male reply and keep interrupted female as serving failure',
 method='One-off execution of unsubmitted transport-failure slots; no recorded model response is retried; same native context and uncapped generation.')
def save():QUEUE.write_text(json.dumps(state,indent=2)+'\n')
save();print('QUEUED: ten unsubmitted sewer slots after verification; no inference calls while waiting',flush=True)
try:
 while True:
  verification=json.loads((BASE/'VERIFY_QUEUE_2026-10-29.json').read_text())
  if verification['state']=='finished':break
  if verification['state']!='running':raise RuntimeError('Verification did not finish: '+verification['state'])
  os.kill(verification['queue_pid'],0);time.sleep(10)
 for path,expected in frozen.items():assert digest(REPO/path)==expected,path
 _,facts=model_facts(Ollama('http://localhost:11434'),runner.MODEL)
 assert facts['digest']==json.loads((OLD/'manifest.json').read_text())['model']['digest']
 out=BASE/'prompt_ab'/(datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-sewers-transport-continuation')
 out.mkdir(parents=True,exist_ok=False);shutil.copyfile(__file__,out/Path(__file__).name)
 shutil.copytree(OLD/'snapshot',out/'snapshot');shutil.copyfile(OLD/'input_runtime_sha256.json',out/'input_runtime_sha256.json')
 state.update(state='running',started_utc=now(),output=str(out.relative_to(REPO)));save()
 original_configs=Experiment.configs
 def configs(self):return (c for c in original_configs(self) if (c['prompt'],c['repeat']) in selected)
 Experiment.configs=configs
 original_chat=Experiment.chat
 def chat(self,config,system,user,schema):
  if not any('male_translation' in line for line in json.loads(user)['dialogue']):
   previous=prior[(config['prompt'],config['repeat'],'male')]['request']
   assert previous['messages']==[dict(role='system',content=system),dict(role='user',content=user)]
   assert previous['format']==schema
  return original_chat(self,config,system,user,schema)
 Experiment.chat=chat
 sys.argv=['run_prompt_ab.py','--datasets','inkgallery_sewers','--out',str(out)]
 try:result=runner.main()
 finally:
  if (out/'manifest.json').exists():
   manifest=json.loads((out/'manifest.json').read_text());manifest['transport_continuation']=state;runner.save(out,manifest)
 assert result==0
 state.update(state='finished',finished_utc=now());save()
except BaseException as exc:
 state.update(state='interrupted_or_failed',ended_utc=now(),error=repr(exc));save();raise
