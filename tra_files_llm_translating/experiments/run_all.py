#!/usr/bin/env python3
"""
One-command diagnostic: pull candidate models, run all experiment stages with
diagnose_translation.py, and write a combined REPORT.md.

  Stage 1  framing / request size / sampling noise on the baseline model
  Stage 2  thinking on vs. off for every thinking-capable model
  Stage 3  model comparison with the production prompt and stage 1's best prompt

See experiments/README.md ("One-command run").
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from diagnose_translation import Experiment, summarize  # noqa: E402

BASELINE = 'qwen3.5:9b'
# Ollama library tags, plus Russian fine-tunes pulled from Hugging Face. A tag that
# cannot be pulled is reported and skipped; it does not stop the run.
DEFAULT_MODELS = [
    'qwen3.5:9b',
    'qwen2.5:14b',
    'gemma3:12b',
    'mistral-small3.2:24b',
    'qwen3:14b',
    'gpt-oss:20b',
    'aya-expanse:8b',
    'hf.co/kri1200/T-lite-it-1.0-Q6_K-GGUF:Q6_K',
    'hf.co/VlSav/Vikhr-Nemo-12B-Instruct-R-21-09-24-Q6_K-GGUF:Q6_K',
]


class Ollama:
    def __init__(self, url):
        self.base = 'http://' + url.split('://', 1)[-1].split('/api/', 1)[0].rstrip('/')

    def request(self, path, payload=None, method=None):
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={'Content-Type': 'application/json'})
        return urllib.request.urlopen(req)

    def get(self, path, payload=None):
        with self.request(path, payload) as response:
            return json.loads(response.read().decode('utf-8'))

    def installed(self):
        names = set()
        for model in self.get('/api/tags').get('models', []):
            names.update({model.get('name'), model.get('model')})
        return names

    def pull(self, tag):
        """Stream /api/pull; print progress about every 10 seconds."""
        last = 0
        with self.request('/api/pull', {'model': tag, 'stream': True}) as response:
            for raw in response:
                event = json.loads(raw.decode('utf-8'))
                if event.get('error'):
                    raise ValueError(event['error'])
                if time.time() - last > 10 or event.get('status') == 'success':
                    last = time.time()
                    done, total = event.get('completed'), event.get('total')
                    progress = f' {100 * done / total:.0f}% of {total / 1e9:.1f} GB' if done and total else ''
                    print(f"    {event.get('status', '')}{progress}", flush=True)

    def thinking(self, tag):
        return 'thinking' in self.get('/api/show', {'model': tag}).get('capabilities', [])

    def delete(self, tag):
        self.request('/api/delete', {'model': tag}, method='DELETE').close()


def load(stage_dir):
    path = Path(stage_dir) / 'runs.jsonl'
    if not path.exists():
        return []
    with open(path, encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def rate(records, *fields):
    """Aggregate check pass rate, errors and timing by the given config fields."""
    groups = defaultdict(lambda: {'ok': 0, 'total': 0, 'errors': 0, 'seconds': 0.0, 'tokens': 0, 'requests': 0})
    for r in records:
        g = groups[tuple(r['config'][f] for f in fields)]
        g['ok'] += sum(c['ok'] for c in r['checks'])
        g['total'] += len(r['checks'])
        if r.get('derived') or r.get('skipped'):
            continue  # Derived variants and skipped passes are not additional requests.
        g['errors'] += bool(r['error'])
        g['seconds'] += r['wall_seconds']
        g['tokens'] += r['eval_count'] or 0
        g['requests'] += 1
    return groups


def table(groups, names):
    lines = ['| ' + ' | '.join(names) + ' | checks ok | failed requests | avg s/request | avg tokens |',
             '|' + '---|' * (len(names) + 4)]
    for key, g in sorted(groups.items(), key=lambda kv: -(kv[1]['ok'] / kv[1]['total'] if kv[1]['total'] else -1)):
        pct = f"{g['ok']}/{g['total']} ({100 * g['ok'] / g['total']:.0f}%)" if g['total'] else 'no output'
        lines.append(f"| {' | '.join(map(str, key))} | {pct} | {g['errors']}/{g['requests']} | "
                     f"{g['seconds'] / g['requests']:.1f} | {g['tokens'] / g['requests']:.0f} |")
    return lines


def select_settings(records):
    """Choose a tested full-dialogue configuration that needs no labelled addressees."""
    eligible = [r for r in records if r['config']['scope'] == 'full'
                and r['config']['prompt'] != 'reframed-addressee']
    groups = rate(eligible, 'prompt', 'temperature')
    scored = {k: g['ok'] / g['total'] for k, g in groups.items() if g['total']}
    # Prefer production, then model-default sampling, when scores tie.
    return max(scored, key=lambda k: (scored[k], k[0] == 'production', k[1] == 'default')) if scored else None


def experiment_args(args, out, **grid):
    return argparse.Namespace(checks=args.checks, actors=None, dictionary=args.dictionary, url=args.url,
                              num_ctx=args.num_ctx, seed=None, dry_run=args.dry_run, out=str(out), **grid)


def run_stage(args, out, title, **grid):
    print(f'\n=== {title} ===', flush=True)
    experiment = Experiment(experiment_args(args, out, **grid))
    experiment.run()
    if not args.dry_run and (Path(out) / 'runs.jsonl').exists():
        summarize(out)


def main():
    parser = argparse.ArgumentParser(description='Pull models, run all diagnostic stages, write REPORT.md.')
    parser.add_argument('--models', type=lambda v: [m.strip() for m in v.split(',') if m.strip()],
                        default=DEFAULT_MODELS, help='comma-separated tags (default: the list in this script)')
    parser.add_argument('--baseline', default=BASELINE, help='model for stage 1')
    parser.add_argument('--stages', default='1,2,3', help='which stages to run, e.g. 1 or 2,3')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--num-ctx', default='8192', help="context for every request, or 'native'")
    parser.add_argument('--checks', default=str(SCRIPT_DIR / 'inkgallery_checks.json'))
    parser.add_argument('--dictionary', default=str(SCRIPT_DIR.parent / 'dict.csv'))
    parser.add_argument('--url', default='http://localhost:11434')
    parser.add_argument('--out', help='results folder (default: experiments/results/full-<timestamp>)')
    parser.add_argument('--skip-pull', action='store_true', help='use only models that are already installed')
    parser.add_argument('--remove-pulled', action='store_true',
                        help='delete models this run downloaded once all stages finish (never pre-installed ones)')
    parser.add_argument('--dry-run', action='store_true', help='show the plan and request counts; no pulls or requests')
    args = parser.parse_args()
    stages = {s.strip() for s in args.stages.split(',')}
    out = Path(args.out or SCRIPT_DIR / 'results' / f"full-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)
    ollama = Ollama(args.url)
    models = list(dict.fromkeys([args.baseline] + args.models))

    # ---- pull ----
    status, pulled = {}, []
    if args.dry_run:
        status = {m: 'not checked (dry run)' for m in models}
    else:
        installed = ollama.installed()
        for tag in models:
            if tag in installed or f'{tag}:latest' in installed:
                status[tag] = 'already installed'
            elif args.skip_pull:
                status[tag] = 'not installed; skipped (--skip-pull)'
            else:
                print(f'Pulling {tag} ...', flush=True)
                try:
                    ollama.pull(tag)
                    status[tag] = 'pulled'
                    pulled.append(tag)
                except (urllib.error.URLError, OSError, ValueError) as exc:
                    status[tag] = f'pull failed: {exc}'
                    print(f'  {status[tag]}; skipping this model', flush=True)
    available = [m for m in models if status[m] in ('already installed', 'pulled', 'not checked (dry run)')]
    thinking = {}
    for tag in available:
        try:
            thinking[tag] = False if args.dry_run else ollama.thinking(tag)
        except (urllib.error.URLError, OSError, ValueError):
            thinking[tag] = False
    if args.dry_run:
        print('Dry run: thinking capability is detected only in a real run; stage 2 counts are omitted.')

    def think_off(tag):
        # Non-thinking models may reject an explicit think setting; leave theirs at the default.
        return ['off'] if thinking.get(tag) else ['default']

    # ---- stages ----
    best_prompt, best_temp = 'reframed', '0.2'
    stage1 = out / 'stage1-framing'
    if '1' in stages and args.baseline in available:
        run_stage(args, stage1, f'Stage 1: framing, request size and noise on {args.baseline}',
                  models=[args.baseline], prompts=['production', 'reframed', 'reframed-addressee', 'examples', 'markup'],
                  scopes=['full', 'pair'], think=think_off(args.baseline), temperatures=['default', '0.2'],
                  repeats=args.repeats)
    records = load(stage1)  # also when continuing with --stages 2,3 in the same --out folder
    if records:
        best_prompt, best_temp = select_settings(records) or (best_prompt, best_temp)
        print(f'Stage 1 best: prompt={best_prompt}, temperature={best_temp}', flush=True)
    for tag in available if '2' in stages else []:
        if thinking.get(tag):
            run_stage(args, out / 'stage2-thinking', f'Stage 2: thinking on vs. off, {tag}',
                      models=[tag], prompts=[best_prompt], scopes=['full'], think=['on', 'off'],
                      temperatures=[best_temp], repeats=args.repeats)
    for tag in available if '3' in stages else []:
        run_stage(args, out / 'stage3-models', f'Stage 3: model comparison, {tag}',
                  models=[tag], prompts=list(dict.fromkeys(['production', best_prompt])), scopes=['full'],
                  think=think_off(tag), temperatures=[best_temp], repeats=args.repeats)

    if args.dry_run:
        return 0
    if args.remove_pulled:
        for tag in pulled:
            try:
                ollama.delete(tag)
                status[tag] += '; removed after the run'
            except (urllib.error.URLError, OSError) as exc:
                status[tag] += f'; removal failed: {exc}'

    # ---- report ----
    try:
        version = ollama.get('/api/version').get('version')
    except (urllib.error.URLError, OSError, ValueError):
        version = 'unknown'
    report = ['# Translation diagnostic report', '',
              f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}, Ollama {version}, context {args.num_ctx}, "
              f'{args.repeats} repeats. Checks: `{Path(args.checks).name}`.', '',
              'Scores count expected-form checks (gender agreement, ты/вы, idiom, meaning, glossary). '
              'Failed outputs and skipped female passes fail all expected checks. '
              'They catch known error types only; read `outputs.csv` in each stage before deciding.', '',
              '## Models', '', '| model | status | thinking-capable | GPU share |', '|---|---|---|---|']
    gpu = {}
    for stage_dir in out.glob('stage*'):
        for r in load(stage_dir):
            if r.get('gpu'):
                gpu[r['config']['model']] = f"{r['gpu']['gpu_percent']}%"
    for tag in models:
        report.append(f"| {tag} | {status[tag]} | {'yes' if thinking.get(tag) else 'no'} | {gpu.get(tag, '-')} |")
    if any(v != '100.0%' for v in gpu.values()):
        report += ['', '**A model below 100% GPU was partly on the CPU: its timings are not comparable.**']

    sections = [
        ('stage1-framing', 'Stage 1: framing, request size, noise',
         [('prompt',), ('scope',), ('temperature',), ('prompt', 'scope', 'temperature')],
         'If `pair` is not better than `full`, request size is not the problem. If `examples` beats '
         '`reframed`, worked examples help. If `markup` (one request, {male|female} markup) beats `examples`, '
         'one request can work when wording cannot drift. If `reframed` beats '
         '`production`, the instructions are at fault. If the same check fails only in some repeats, it is noise. '
         f'Chosen for later stages: prompt **{best_prompt}**, temperature **{best_temp}**.'),
        ('stage2-thinking', 'Stage 2: thinking',
         [('model', 'think')], 'Compare quality gain against the extra time and tokens.'),
        ('stage3-models', 'Stage 3: models',
         [('model',), ('model', 'prompt')], 'Failures in idiom/meaning checks (@48, @100) point at model ability.'),
    ]
    for folder, title, groupings, note in sections:
        records = load(out / folder)
        if not records:
            continue
        report += ['', f'## {title}', '', note, '',
                   f'Details: [{folder}/summary.md]({folder}/summary.md), [{folder}/outputs.csv]({folder}/outputs.csv), '
                   f'[{folder}/pair_reviews.csv]({folder}/pair_reviews.csv) (wording diagnostics, excluded from scores).']
        for fields in groupings:
            report += ['', f"### By {', '.join(fields)}", ''] + table(rate(records, *fields), list(fields))
    (out / 'REPORT.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    print(f"\nReport: {out / 'REPORT.md'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
