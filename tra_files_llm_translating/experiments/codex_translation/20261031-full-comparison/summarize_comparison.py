"""Combine completed/rejected cases, preserving raw data and separate manual review."""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
sys.path.insert(0, str(REPO / 'tra_files_llm_translating/experiments'))
import run_codex_translation as runner
from translation_common import female_source


def summarize():
    state=json.loads((BASE/'COMPARISON.json').read_text())
    groups=defaultdict(list)
    calls=[]
    for r in state['runs']:
        if r['status']=='running':continue
        groups[r['model'],r['mode']].append(r)
        calls.extend(r.get('calls',[]))
    lines=['# Full Codex translation comparison','',f"Status: {state['status']}", '',
           'Two models × two methods × eight datasets × three repeats = 96 planned dialogue pairs.',
           'Initial pilot is separate. No rejected reply was retried. Invalid/missing passes fail all expected checks.',
           'Targeted checks are diagnostics, not translation-quality percentages. Human review is pending.','',
           '| Model | Method | Pairs completed / attempted | Rejected | All checks | Accepted pairs only | CLI calls | Total seconds |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    stats=[]
    for (model,mode),runs in sorted(groups.items()):
        checks=[c for r in runs for c in r['checks']]
        valid=[r for r in runs if r['status']=='completed']
        good=[c for r in valid for c in r['checks']]
        real=[c for r in runs for c in r.get('calls',[])]
        sec=sum(c['wall_seconds'] for c in real)
        summary=dict(model=model,mode=mode,attempted=len(runs),completed=len(valid),rejected=sum(r['status']=='rejected' for r in runs),
                     checks_ok=sum(c['ok'] for c in checks),checks_total=len(checks),accepted_checks_ok=sum(c['ok'] for c in good),
                     accepted_checks_total=len(good),cli_calls=len(real),wall_seconds=round(sec,3),
                     usage={k:sum((c.get('usage') or {}).get(k,0) for c in real) for k in ['input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens']})
        stats.append(summary)
        lines.append(f"| {model} | {mode} | {len(valid)}/{len(runs)} | {summary['rejected']} | {summary['checks_ok']}/{len(checks)} | {summary['accepted_checks_ok']}/{len(good)} | {len(real)} | {sec:.1f} |")
    lines+=['','## Rejections','']
    for r in state['runs']:
        if r['status']=='rejected':lines.append(f"- {r['dataset']} / {r['model']} / {r['mode']} / repeat {r['repeat']}: {r['error']}")
    lines+=['','## Dataset checks','', '| Dataset | Model | Method | Completed / attempted | Checks |', '|---|---|---|---:|---:|']
    by_dataset=defaultdict(list)
    for r in state['runs']:
        if r['status']!='running':by_dataset[r['dataset'],r['model'],r['mode']].append(r)
    for key,runs in by_dataset.items():
        checks=[c for r in runs for c in r['checks']]
        lines.append('| '+' | '.join(key)+f" | {sum(r['status']=='completed' for r in runs)}/{len(runs)} | {sum(c['ok'] for c in checks)}/{len(checks)} |")
    lines+=['','## Interpretation','',
            'Compare both completion/validation reliability and accepted-pair checks. Entire rejected replies',
            'can dominate all-attempted scores even when their raw Russian has useful content; see the review export.',
            'Token counts include Codex scaffolding and are not directly comparable with Ollama prompt counts.',
            'The CLI uses model-default reasoning effort; this is not an isolated architecture or reasoning-effort benchmark.',
            'A simultaneous pair makes one CLI request; two-pass makes up to two. Compare complete-pair cost/time.',
            'See REVIEW_UNIQUE.csv and ASSISTANT_REVIEW.csv for raw texts and separate editorial annotations.',
            'Raw replies, reference translations, prompts and production code were not edited.']
    (BASE/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    runner.save(BASE/'SUMMARY.json',dict(status=state['status'],groups=stats,total_calls=len(calls),
                                      total_seconds=round(sum(c['wall_seconds'] for c in calls),3)))
    e_by_name={name:runner.experiment(checks,BASE/'results/inputs'/name) for name,checks in runner.datasets()}
    with (BASE/'outputs.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['dataset','model','mode','repeat','status','Line_ID','English_Male','English_Female','Russian_Male','Russian_Female','male_validated','female_validated'])
        for r in state['runs']:
            if r['status']=='running':continue
            folder=BASE/'results'/r['dataset']/f"model-{state['settings']['models'].index(r['model'])+1}"/r['mode']/str(r['repeat'])
            valid=folder/'validated.json'
            values=json.loads(valid.read_text()) if valid.exists() else {}
            if not values and r['mode']=='two-pass':
                for gender in r.get('validated_genders',[]):
                    p=folder/gender/'response.txt'
                    if not p.exists():continue
                    temp={'translations':{}}
                    e=e_by_name[r['dataset']];e.parse(temp,p.read_text(),e.rows[1:],gender)
                    if not temp.get('error'):values[gender]=temp['translations']
            e=e_by_name[r['dataset']]
            for row in e.rows[1:]:
                w.writerow([r['dataset'],r['model'],r['mode'],r['repeat'],r['status'],row[1],row[3],
                            female_source(dict(zip(e.header,row)),row[3]),values.get('male',{}).get(row[1],''),values.get('female',{}).get(row[1],''),
                            'male' in values,'female' in values])
    review=BASE/'REVIEW_UNIQUE.csv';annotations=BASE/'ASSISTANT_ANNOTATIONS.json'
    if review.exists() and annotations.exists():
        notes=json.loads(annotations.read_text());rows=list(csv.DictReader(review.open(encoding='utf-8-sig')))
        with (BASE/'ASSISTANT_REVIEW.csv').open('w',encoding='utf-8-sig',newline='') as f:
            fields=list(rows[0])+['assistant_status','assistant_note'] if rows else []
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
            for row in rows:
                a=notes.get(row['review_id'],dict(status='pending',note='Not reviewed yet'))
                w.writerow(dict(row,assistant_status=a['status'],assistant_note=a['note']))
        print('Review coverage',sum(row['review_id'] in notes for row in rows),'/',len(rows))
    print('Pairs',len(state['runs']),'calls',len(calls),'status',state['status'])


if __name__=='__main__':summarize()
