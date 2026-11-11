"""Compare explicit-low reproduction against all three historical Sol repeats."""
import csv
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
OLD = BASE.parent / '20261031-full-comparison'

def stats(runs):
    checks = [c for r in runs for c in r['checks']]
    calls = [c for r in runs for c in r.get('calls', [])]
    return dict(pairs=len(runs), valid=sum(r['status']=='completed' for r in runs),
                checks_ok=sum(c['ok'] for c in checks), checks_total=len(checks),
                calls=len(calls), seconds=sum(c['wall_seconds'] for c in calls),
                usage={k:sum((c.get('usage') or {}).get(k,0) for c in calls)
                       for k in ('input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens')})

def main():
    new=json.loads((BASE/'results/manifest.json').read_text())
    old=json.loads((OLD/'COMPARISON.json').read_text())
    oldruns=[r for r in old['runs'] if r['model']=='gpt-6.1-sol']
    lines=['# Sol explicit-low reproduction','',f"Run status: {new['status']}",'',
           'Eight datasets, both methods, one repeat. Historical Sol used three repeats with unspecified default effort.',
           'Inputs/glossary/prompt builders/scoring match the frozen historical hashes. Only the runner adds effort selection and recording.',
           'CLI changed from 0.166.0 to '+new.get('codex_version','unknown')+'. Backend changes and normal sampling variation are uncontrolled.',
           'This is a reproduction comparison, not an isolated test of reasoning effort. Checks are diagnostics, not quality percentages.','',
           '| Method / run | Valid pairs | Checks | Calls | Seconds per pair | Input tokens per pair | Output tokens per pair | Reasoning tokens per pair |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    summary={}
    for mode in ('both','two-pass'):
        summary[mode]={}
        for label,runs in [('historical',[r for r in oldruns if r['mode']==mode]),
                           ('explicit low',[r for r in new['runs'] if r['mode']==mode])]:
            s=stats(runs); summary[mode][label]=s;n=s['pairs'] or 1
            lines.append(f"| {mode} / {label} | {s['valid']}/{s['pairs']} | {s['checks_ok']}/{s['checks_total']} | {s['calls']} | {s['seconds']/n:.2f} | {s['usage']['input_tokens']/n:.1f} | {s['usage']['output_tokens']/n:.1f} | {s['usage']['reasoning_output_tokens']/n:.1f} |")
    lines+=['','## Per-dataset checks','','| Dataset | Method | New low | Previous repeat 1 | Previous repeat 2 | Previous repeat 3 |','|---|---|---:|---:|---:|---:|']
    def score(r): return f"{sum(c['ok'] for c in r['checks'])}/{len(r['checks'])}"
    for r in new['runs']:
        previous=sorted([o for o in oldruns if (o['dataset'],o['mode'])==(r['dataset'],r['mode'])],key=lambda o:o['repeat'])
        lines.append('| '+' | '.join([r['dataset'],r['mode'],score(r)]+[score(o) for o in previous])+' |')
    lines+=['','## Failed checks','']
    for r in new['runs']:
        for c in r['checks']:
            if not c['ok']:lines.append(f"- {r['dataset']} / {r['mode']}: {json.dumps(c,ensure_ascii=False)}")
    newrows=list(csv.DictReader((BASE/'results/outputs.csv').open(encoding='utf-8-sig')))
    oldrows=list(csv.DictReader((OLD/'outputs.csv').open(encoding='utf-8-sig')))
    oldindex={ (r['dataset'],r['mode'],r['Line_ID'],r['repeat']):r for r in oldrows if r['model']=='gpt-6.1-sol'}
    fields=['dataset','mode','Line_ID','English_Male','English_Female','Russian_Male','Russian_Female']
    for repeat in ('1','2','3'):
        fields += ['Old_Male_'+repeat,'Old_Female_'+repeat]
    identical=0; unique={}
    with (BASE/'SIDE_BY_SIDE.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in newrows:
            row={k:r[k] for k in fields if k in r}
            prior=[oldindex[(r['dataset'],r['mode'],r['Line_ID'],rep)] for rep in ('1','2','3')]
            identical+=any(all(r[k]==p[k] for k in ('Russian_Male','Russian_Female')) for p in prior)
            for rep,p in zip(('1','2','3'),prior):
                row['Old_Male_'+rep]=p['Russian_Male'];row['Old_Female_'+rep]=p['Russian_Female']
            w.writerow(row)
            key=tuple(r[k] for k in ('dataset','Line_ID','Russian_Male','Russian_Female'))
            if key not in unique:unique[key]={k:r[k] for k in fields[:7]}
    with (BASE/'REVIEW_UNIQUE.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields[:7]);w.writeheader();w.writerows(unique.values())
    lines+=['','## Text comparison','',f'{identical}/{len(newrows)} source-row pairs exactly match at least one historical repeat of the same method.',
            f'{len(unique)} distinct new source-row/translation pairs are exported for review.',
            'SIDE_BY_SIDE.csv includes all three historical translations beside the new result. Linguistic assessment is recorded separately in MANUAL_REVIEW.md.']
    # Check request evidence and common prompts. Female-edit prompts depend on the generated male text.
    evidence=[]
    for r in new['runs']:
        folder=BASE/'results'/r['dataset']/'model-1'/r['mode']/'1'
        for call in r.get('calls',[]):
            assert call['reasoning_effort']=='low'
            assert 'model_reasoning_effort="low"' in call['command']
        for stage in ('both',) if r['mode']=='both' else ('male','female'):
            p=folder/stage/'prompt.txt'; previous=OLD/'results'/r['dataset']/'model-2'/r['mode']/'1'/stage/'prompt.txt'
            equal=p.read_bytes()==previous.read_bytes()
            schema_equal=p.with_name('schema.json').read_bytes()==previous.with_name('schema.json').read_bytes()
            assert schema_equal,(r['dataset'],stage,'schema')
            evidence.append({'dataset':r['dataset'],'mode':r['mode'],'stage':stage,
                             'prompt_matches_old_repeat1':equal,'schema_matches_old_repeat1':schema_equal})
            if stage!='female':assert equal,(r['dataset'],stage)
    logs=list((BASE/'results').rglob('events.jsonl'))
    for log in logs:
        events=[json.loads(line) for line in log.read_text().splitlines()]
        assert any(e.get('type')=='turn.completed' for e in events),str(log)
        assert all(e.get('item',{}).get('type') in (None,'agent_message','reasoning') for e in events),str(log)
    pre=json.loads((BASE/'PRE_RUN.json').read_text())
    repo=BASE.parents[3]
    for name,hashes in pre['comparison_to_old'].items():
        assert hashlib.sha256((repo/name).read_bytes()).hexdigest()==hashes['current'],name
    (BASE/'INTEGRITY.json').write_text(json.dumps({'explicit_low_in_all_calls':True,'successful_event_logs':len(logs),
        'no_tool_activity':True,'runtime_hashes_unchanged_during_run':True,'prompt_comparisons':evidence},indent=2)+'\n')
    (BASE/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    (BASE/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()
