#!/usr/bin/env python3
"""A/B test of one prompt change: production vs production-nouns (female-pass noun rule).

Same model, datasets, settings and repeats for both prompts; only the female-pass
instruction differs (FEMALE_NOUN_RULE in diagnose_translation.py). No verifier.
Writes to experiments/prompt_ab/<UTC timestamp>/, which is committed. See PROMPT_AB_PLAN.md.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from diagnose_translation import FEMALE_NOUN_RULE, Experiment, summarize
from run_all import Ollama, load
from run_non_thinking import thinking_setting
from run_translate_verify import datasets, model_facts, now

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[1]
PROMPTS = ['production', 'production-nouns']
MODEL = 'mistral-small3.2:24b'


def compare(out, manifest):
    """Per prompt and dataset: checks, rejected requests and wording flags; plus checks that differ."""
    totals = defaultdict(lambda: dict(ok=0, expected=0, requests=0, errors=0, review=0))
    failures = defaultdict(lambda: defaultdict(int))  # (dataset, line, gender, check) -> prompt -> failures
    for name in manifest.get('completed', []):
        for record in load(out / name):
            prompt = record['config']['prompt']
            total = totals[(name, prompt)]
            total['ok'] += sum(c['ok'] for c in record['checks'])
            total['expected'] += len(record['checks'])
            if not record.get('skipped'):
                total['requests'] += 1
                total['errors'] += bool(record['error'])
            total['review'] += sum(v['status'] == 'review' for v in record.get('pair_reviews', []))
            for c in record['checks']:
                if not c['ok']:
                    failures[(name, c['line'], c['gender'], c['check'])][prompt] += 1
    lines = ['# Prompt A/B: female-pass noun rule', '',
             f"Status: {manifest['status']}. Started {manifest['started_utc']}, finished {manifest.get('finished_utc', '-')}.",
             f"Model `{manifest['settings']['model']}`, think {manifest['settings']['think']}, "
             f"ctx {manifest['settings']['num_ctx']}, {manifest['settings']['repeats']} repeats, full dialogues.", '',
             f'Rule added to the female-pass instruction in `production-nouns`: "{FEMALE_NOUN_RULE}"', '',
             'Checks are targeted assertions, not overall quality. Wording flags (male/female differences outside '
             'listed gender edits) should not rise: the rule must not cause unrelated rewrites.', '',
             '| Dataset | Prompt | Checks | Rejected / requests | Wording flags |', '|---|---|---:|---:|---:|']
    for name in manifest.get('completed', []):
        for prompt in PROMPTS:
            t = totals[(name, prompt)]
            lines.append(f"| {name} | {prompt} | {t['ok']}/{t['expected']} | {t['errors']}/{t['requests']} | {t['review']} |")
    for prompt in PROMPTS:
        t = [totals[(n, prompt)] for n in manifest.get('completed', [])]
        lines.append(f"| **all** | {prompt} | {sum(x['ok'] for x in t)}/{sum(x['expected'] for x in t)} | "
                     f"{sum(x['errors'] for x in t)}/{sum(x['requests'] for x in t)} | {sum(x['review'] for x in t)} |")
    differing = [(k, v) for k, v in sorted(failures.items()) if v[PROMPTS[0]] != v[PROMPTS[1]]]
    lines += ['', '## Checks whose failure count differs', '',
              '| Dataset | Line | Gender | Check | production fails | production-nouns fails |', '|---|---|---|---|---:|---:|']
    lines += [f'| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {v[PROMPTS[0]]} | {v[PROMPTS[1]]} |' for k, v in differing] or ['| - | | | | | |']
    lines += ['', '## Manual review', '', 'Pending: compare the female outputs.csv rows of both prompts per dataset.']
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def save(out, manifest):
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    compare(out, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--model', default=MODEL)
    parser.add_argument('--think', default='auto', choices=['auto', 'default', 'on', 'off'],
                        help='auto: off when the model supports thinking, otherwise the model default')
    parser.add_argument('--num-ctx', type=int, default=8192)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--datasets', help='comma-separated subset (default: all, including real_set)')
    parser.add_argument('--url', default='http://localhost:11434')
    parser.add_argument('--out', help='default: experiments/prompt_ab/<UTC timestamp>')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.repeats < 1 or args.num_ctx < 1:
        parser.error('Context and repeats must be positive')
    names = [n.strip() for n in args.datasets.split(',')] if args.datasets else None
    chosen = datasets(names)
    if names and len(chosen) != len(names):
        parser.error(f'Unknown dataset in {names}')
    print(f'Model {args.model}; {len(chosen)} datasets x {len(PROMPTS)} prompts x {args.repeats} repeats: '
          f'up to {len(chosen) * len(PROMPTS) * args.repeats * 2} requests')
    if args.dry_run:
        return 0
    out = Path(args.out or SCRIPT_DIR / 'prompt_ab' / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    if (out / 'manifest.json').exists():
        parser.error('Use a fresh output directory; automatic resume is not implemented')
    out.mkdir(parents=True, exist_ok=True)
    client = Ollama(args.url)
    info, model = model_facts(client, args.model)
    think = thinking_setting(info) if args.think == 'auto' else args.think
    files = [Path(__file__).resolve(), SCRIPT_DIR / 'diagnose_translation.py', SCRIPT_DIR.parent / 'translate_dialogs.py',
             SCRIPT_DIR.parent / 'translation_common.py', SCRIPT_DIR.parent / 'dict.csv'] + [c for _, c in chosen]
    manifest = dict(status='running', started_utc=now(), settings=dict(vars(args), think=think), model=model,
                    prompts=PROMPTS, female_noun_rule=FEMALE_NOUN_RULE, completed=[],
                    ollama_version=client.get('/api/version'),
                    git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                    working_tree_diff=subprocess.check_output(['git', 'diff'], cwd=REPO, text=True),
                    sha256={str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    print(f'RESULTS: {out}', flush=True)
    save(out, manifest)
    try:
        for name, checks in chosen:
            print(f'DATASET {name}', flush=True)
            options = argparse.Namespace(checks=str(checks), actors=None, dictionary=str(SCRIPT_DIR.parent / 'dict.csv'),
                                         url=args.url, num_ctx=str(args.num_ctx), seed=None, dry_run=False,
                                         out=str(out / name), models=[args.model], prompts=PROMPTS, scopes=['full'],
                                         think=[think], temperatures=['default'], repeats=args.repeats)
            Experiment(options).run()
            summarize(out / name)
            manifest['completed'].append(name)
            save(out, manifest)
        manifest['status'] = 'finished'
    except KeyboardInterrupt:
        manifest['status'] = 'interrupted'
        raise
    finally:
        manifest['finished_utc'] = now()
        save(out, manifest)
    print(f'FINISHED: {out}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
