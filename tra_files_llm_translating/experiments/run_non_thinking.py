#!/usr/bin/env python3
"""Download one candidate, test the frozen suite, then advance in the agreed order."""

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from diagnose_translation import Experiment, summarize
from run_all import Ollama, load

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[1]
PLAN = SCRIPT_DIR / 'NON_THINKING_PLAN_2026-10-27.md'
MODELS = [
    'gemma3:12b',
    'hf.co/t-tech/T-lite-it-2.1-GGUF:Q4_K_M',
    'aya-expanse:8b',
    'hf.co/VlSav/Vikhr-Nemo-12B-Instruct-R-21-09-24-Q6_K-GGUF:Q6_K',
    'mistral-small3.2:24b',
    'gemma4:12b',
    'qwen3:14b',
]
BASELINE = SCRIPT_DIR / 'results/comparison-20261027-221323/manifest.json'
# Publisher says non-thinking; default mode sometimes routes answer JSON into the
# thinking field. Actual production-schema/non-streaming probes verified explicit
# off gives clean content without reasoning. Pin this compatibility exception.
TLITE_NATIVE = ('hf.co/t-tech/T-lite-it-2.1-GGUF:Q4_K_M',
                '24727915b419e9949ba993e59353f72b84650693c73af70d4a0886e0b5416cf9')


def now():
    return datetime.now(timezone.utc).isoformat()


def datasets():
    return [('inkgallery', SCRIPT_DIR / 'inkgallery_checks.json')] + [
        (p.parent.name, p) for p in sorted((SCRIPT_DIR / 'fixtures').glob('*/checks.json'))]


def thinking_setting(info, tag=None, digest=None):
    """Use no reasoning; never substitute a low reasoning effort for disabled thinking."""
    if (tag, digest) == TLITE_NATIVE:
        return 'off'
    values = (info.get('thinking') or {}).get('values')
    if values is not None:
        if not any(v is False for v in values):
            raise ValueError(f'No non-thinking mode in reported thinking values: {values}')
        return 'off' if any(v is not False for v in values) else 'default'
    return 'off' if 'thinking' in info.get('capabilities', []) else 'default'


def metrics(records):
    real = [r for r in records if not r.get('skipped') and not r.get('derived')]
    checks = [c for r in records for c in r['checks']]
    pairs = {}
    for r in records:
        pairs.setdefault(r['config']['repeat'], set())
        if not r['error']:
            pairs[r['config']['repeat']].add(r['gender'])
    return dict(ok=sum(c['ok'] for c in checks), expected=len(checks),
                requests=len(real), errors=sum(bool(r['error']) for r in real),
                complete_pairs=sum(v == {'male', 'female'} for v in pairs.values()),
                seconds=round(sum(r['wall_seconds'] for r in real), 2),
                gpu=[r['gpu']['gpu_percent'] for r in real if r.get('gpu')],
                wording_review=sum(v['status'] == 'review' for r in records for v in r.get('pair_reviews', [])))


def save(out, manifest):
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# Ordered non-thinking comparison', '', f"Status: {manifest['status']}. Started: {manifest['started_utc']}.",
             '', 'Scores are diagnostic expected-form tests, not translation accuracy. Partial models are labelled; '
             'wording flags are excluded from scores. Consult the plan and raw outputs before choosing a winner.', '',
             '| order | model | status | checks | complete pairs | errors/requests | request seconds | macro % |',
             '|---|---|---|---|---|---|---|---|']
    with (out / 'scores.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['order', 'model', 'dataset', 'ok', 'expected', 'requests', 'errors', 'complete_pairs', 'seconds', 'gpu', 'wording_review'])
        for entry in manifest['models']:
            stats = []
            for stage in entry.get('datasets', []):
                s = metrics(load(out / stage['out']))
                stats.append(s)
                writer.writerow([entry['order'], entry['tag'], stage['name']] + [s[k] for k in
                                 ('ok', 'expected', 'requests', 'errors', 'complete_pairs', 'seconds', 'gpu', 'wording_review')])
            sums = {k: sum(s[k] for s in stats) for k in ('ok', 'expected', 'requests', 'errors', 'complete_pairs', 'seconds')}
            rates = [100 * s['ok'] / s['expected'] for s in stats if s['expected']]
            macro = f'{sum(rates) / len(rates):.2f}' if rates else '-'
            lines.append(f"| {entry['order']} | {entry['tag']} | {entry['status']} | {sums['ok']}/{sums['expected']} | "
                         f"{sums['complete_pairs']} | {sums['errors']}/{sums['requests']} | {sums['seconds']:.2f} | {macro} |")
    for entry in manifest['models']:
        lines += ['', f"## {entry['order']}. {entry['tag']}", '', f"Status: {entry['status']}."]
        if entry.get('error'):
            lines += ['', entry['error']]
        for stage in entry.get('datasets', []):
            folder = stage['out']
            lines += ['', f"- {stage['name']}: [summary]({folder}/summary.md), [outputs]({folder}/outputs.csv), "
                       f"[wording review]({folder}/pair_reviews.csv), [raw requests/replies]({folder}/runs.jsonl)."]
            if stage.get('error'):
                lines.append(f"  Stage error: {stage['error']}")
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def evaluate(args, out, tag, think, checks):
    options = argparse.Namespace(checks=str(checks), actors=None, dictionary=str(SCRIPT_DIR.parent / 'dict.csv'),
                                 url=args.url, num_ctx=str(args.num_ctx), seed=None, dry_run=False, out=str(out),
                                 models=[tag], prompts=['production'], scopes=['full'], think=[think],
                                 temperatures=['default'], repeats=args.repeats)
    experiment = Experiment(options)
    original_chat = experiment.chat
    def non_thinking_chat(*call_args):
        payload, result = original_chat(*call_args)
        if (result.get('message', {}).get('thinking') or '').strip():
            (out / 'unexpected_thinking.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            raise ValueError('Unexpected nonempty thinking output; stopping this non-thinking candidate')
        return payload, result
    experiment.chat = non_thinking_chat
    try:
        experiment.run()
    finally:
        if (out / 'runs.jsonl').exists():
            summarize(out)


def run_models(args, out, manifest, client, orders=None):
    installed = client.installed()
    for entry in manifest['models']:
        if orders is not None and entry['order'] not in orders:
            continue  # Explicit manual continuation; never repeat completed candidates.
        tag = entry['tag']
        print(f"\nMODEL {entry['order']}/{len(manifest['models'])}: {tag}", flush=True)
        entry.update(status='checking', started_utc=now(), datasets=[])
        save(out, manifest)
        try:
            if tag in installed or f'{tag}:latest' in installed:
                entry['download'] = 'already installed'
            else:
                entry['status'] = 'pulling'
                save(out, manifest)
                client.pull(tag)
                entry['download'] = 'pulled; retained'
            info = client.get('/api/show', {'model': tag})
            entry['show'] = info
            entry['inventory_after_pull'] = client.get('/api/tags')
            digest = next((m.get('digest') for m in entry['inventory_after_pull'].get('models', [])
                           if tag in (m.get('name'), m.get('model'))), None)
            think = thinking_setting(info, tag, digest)
            if (tag, digest) == TLITE_NATIVE:
                entry['thinking_policy'] = ('Publisher non-thinking model; explicit off validated with the production '
                                            'JSON schema and non-streaming API. Default mode sometimes misroutes '
                                            'answer JSON into thinking. Metadata-only skip superseded by actual probes; '
                                            'unexpected-thinking guard remains active.')
            entry.update(think=think, status='testing')
            save(out, manifest)
            for name, checks in datasets():
                folder = Path(f"{entry['order']:02d}") / name
                stage = dict(name=name, checks=str(checks.relative_to(REPO)), out=str(folder), started_utc=now())
                entry['datasets'].append(stage)
                stage['configuration'] = dict(model=tag, prompt='production', scope='full', think=think,
                                               temperature='default', repeats=args.repeats, num_ctx=args.num_ctx,
                                               num_predict=-1, seed=None)
                save(out, manifest)
                print(f'  DATASET {name}', flush=True)
                try:
                    evaluate(args, out / folder, tag, think, checks)
                except (ValueError, OSError) as exc:
                    stage['error'] = str(exc)
                    raise
                finally:
                    stage['finished_utc'] = now()
                    save(out, manifest)
            entry['status'] = 'completed'
        except (ValueError, OSError) as exc:
            entry.update(status='failed/skipped', error=str(exc))
            print(f"  Candidate failed/skipped: {exc}", flush=True)
        finally:
            entry['finished_utc'] = now()
            save(out, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://localhost:11434')
    parser.add_argument('--num-ctx', type=int, default=8192)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--out')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.repeats < 1 or args.num_ctx < 1:
        parser.error('Context and repeats must be positive')
    if args.dry_run:
        for i, tag in enumerate(MODELS, 1):
            print(f'{i}. pull if absent -> test {len(datasets())} datasets -> retain: {tag}')
        print(f'Up to {len(MODELS) * len(datasets()) * args.repeats * 2} requests; no thinking, no inference cap or retries.')
        return 0
    out = Path(args.out or SCRIPT_DIR / 'results' / ('non-thinking-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')))
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'manifest.json').exists():
        parser.error('Use a fresh results directory; automatic resume is not implemented')
    print(f'RESULTS: {out}', flush=True)
    manifest = dict(status='preparing', started_utc=now(), models=[dict(order=i, tag=tag, status='pending') for i, tag in enumerate(MODELS, 1)])
    save(out, manifest)
    files = [Path(__file__).resolve(), SCRIPT_DIR / 'run_all.py', SCRIPT_DIR / 'diagnose_translation.py', PLAN,
             SCRIPT_DIR / 'inkgallery_checks.json', SCRIPT_DIR.parent / 'translate_dialogs.py',
             SCRIPT_DIR.parent / 'translation_common.py', SCRIPT_DIR.parent / 'dict.csv']
    files += [p for p in (SCRIPT_DIR / 'fixtures').rglob('*') if p.is_file()]
    files += list((SCRIPT_DIR.parent / 'examples/inkgallery-json-two-pass').glob('*.csv'))
    hashes = {}
    for source in files:
        rel = source.relative_to(REPO)
        target = out / 'snapshot' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        hashes[str(rel)] = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest['sha256'] = hashes
    if BASELINE.exists():
        previous = json.loads(BASELINE.read_text(encoding='utf-8'))
        for name, digest in previous['sha256'].items():
            if not name.endswith('.md') and hashes.get(name) != digest:
                raise ValueError(f'Frozen runtime/input changed since baseline: {name}')
        manifest['baseline_manifest'] = str(BASELINE.relative_to(REPO))
    manifest['git_head'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    manifest['working_tree_diff'] = subprocess.check_output(['git', 'diff'], cwd=REPO, text=True)
    client = Ollama(args.url)
    manifest['ollama_version'] = client.get('/api/version')
    manifest['initial_inventory'] = client.get('/api/tags')
    manifest['status'] = 'running'
    save(out, manifest)
    try:
        run_models(args, out, manifest, client)
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
