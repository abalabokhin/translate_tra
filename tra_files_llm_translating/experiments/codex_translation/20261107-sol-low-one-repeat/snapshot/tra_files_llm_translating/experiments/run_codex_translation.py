#!/usr/bin/env python3
"""Evaluate Codex CLI translations against existing fixtures; no Ollama or production edits."""

import argparse
import csv
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from diagnose_translation import Experiment
from run_translate_verify import datasets
from translate_dialogs import DialogTranslator, MIXED_SPEAKERS_NOTE
from translation_common import female_source, merge_dialogue_rows, strict_json

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CLI_INSTRUCTION = (
    'Translate using only the supplied instructions and dialogue data. '
    'Do not use tools, inspect files, browse, delegate, or change any files. '
    'Return only the JSON required by the output schema.\n\n'
)


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def experiment(checks, out):
    return Experiment(argparse.Namespace(
        checks=str(checks), actors=None, dictionary=str(HERE.parent / 'dict.csv'),
        out=str(out), url='http://localhost:11434'))


def both_request(e):
    """Use production source/glossary/graph, with two complete strings per merged ID."""
    system, user = e.build('production', e.rows[1:], 'male')
    data = json.loads(user)
    merged, _ = merge_dialogue_rows(e.rows)
    data['instruction'] = (
        'Translate every line for BOTH male and female Player1 in this one response. '
        'Return complete male and female Russian strings. All words about Player1 '
        '(including nouns, adjectives, participles, verbs and pronouns) must agree '
        'with that version. Other characters retain their fixed genders in BOTH. '
        'Use english_female for the female version, including differences in meaning. '
        'When english_female is empty, return an empty female string. '
        'Copy unaffected wording and punctuation exactly between versions; do not '
        'paraphrase one version independently. Do not use gender markup or fragments.'
    )
    properties = {}
    for line, row in zip(data['dialogue'], merged[1:]):
        line['english_female'] = female_source(dict(zip(e.header, row)), row[3])
        speakers = line['speaker'] if isinstance(line['speaker'], list) else [line['speaker']]
        genders = line['speaker_gender']
        genders = genders if isinstance(genders, list) else [genders]
        genders = ['male in male, female in female' if name == 'Player1' else gender
                   for name, gender in zip(speakers, genders)]
        line['speaker_gender'] = genders if isinstance(line['speaker'], list) else genders[0]
        if any(e.prod._mixed_speakers(row[0], gender) for gender in ('male', 'female')):
            line['note'] = MIXED_SPEAKERS_NOTE
        female = {'type': 'string'}
        if not line['english_female'].strip():
            female['enum'] = ['']
        properties[line['id']] = {
            'type': 'object', 'additionalProperties': False,
            'required': ['male', 'female'],
            'properties': {'male': {'type': 'string'}, 'female': female}}
    data['output'] = {'translations': {
        key: {'male': 'Complete Russian male line', 'female': '' if 'enum' in value['properties']['female']
              else 'Complete Russian female line'} for key, value in properties.items()}}
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['translations'],
              'properties': {'translations': {'type': 'object', 'additionalProperties': False,
                             'required': list(properties), 'properties': properties}}}
    return system, json.dumps(data, ensure_ascii=False), schema


def parse_both(e, content):
    data = strict_json(content)
    merged, slots = merge_dialogue_rows(e.rows)
    expected = {str(i) for i in range(1, len(merged))}
    if not isinstance(data, dict) or set(data) != {'translations'}:
        raise ValueError('Expected only translations')
    values = data['translations']
    if not isinstance(values, dict) or set(values) != expected:
        raise ValueError('Translation IDs do not match source rows exactly')
    empty = DialogTranslator._empty_female_ids(merged)
    for key, pair in values.items():
        if not isinstance(pair, dict) or set(pair) != {'male', 'female'}:
            raise ValueError(f'ID {key}: expected only male and female')
        if key in empty and pair['female'] != '':
            raise ValueError(f'ID {key}: explicitly empty female source must stay empty')
    result = {}
    for gender in ('male', 'female'):
        payload = {'translations': {key: pair[gender] for key, pair in values.items()
                                   if gender != 'female' or key not in empty}}
        parsed = DialogTranslator._parse_translation(json.dumps(payload), merged, female=gender == 'female')
        result[gender] = {row[1]: parsed[str(slots[row[1]])] for row in e.rows[1:]}
    return result


def run_cli(binary, model, system, user, schema, out, dry_run=False, effort=None):
    out.mkdir(parents=True)
    prompt = CLI_INSTRUCTION + system + '\n\nDIALOGUE DATA:\n' + user
    (out / 'prompt.txt').write_text(prompt, encoding='utf-8')
    save(out / 'schema.json', schema)
    record = {'status': 'prepared', 'model': model, 'reasoning_effort': effort, 'started_utc': now(),
              'wall_seconds': 0, 'usage': None, 'error': None}
    if dry_run:
        save(out / 'call.json', record)
        return record, None
    started = time.monotonic()
    try:
        # Fresh cwd outside the repository: no fixtures, references or project instructions.
        with tempfile.TemporaryDirectory(prefix='tra-codex-') as temporary:
            work = Path(temporary)
            save(work / 'schema.json', schema)
            command = [binary, 'exec', '--ignore-user-config', '--ephemeral',
                       '--skip-git-repo-check', '--sandbox', 'read-only', '--model', model,
                       '--color', 'never', '--json', '--output-schema', str(work / 'schema.json'),
                       '--output-last-message', str(work / 'response.txt'), '-']
            if effort is not None:
                command[2:2] = ['-c', f'model_reasoning_effort="{effort}"']
            record['command'] = command
            with (out / 'events.jsonl').open('w', encoding='utf-8') as events, \
                    (out / 'stderr.txt').open('w', encoding='utf-8') as stderr:
                process = subprocess.Popen(command, cwd=work, stdin=subprocess.PIPE,
                                           stdout=events, stderr=stderr, text=True,
                                           start_new_session=os.name == 'posix')
                try:
                    process.communicate(prompt)
                except KeyboardInterrupt:
                    if os.name == 'posix':
                        os.killpg(process.pid, signal.SIGTERM)
                    else:
                        process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        if os.name == 'posix':
                            os.killpg(process.pid, signal.SIGKILL)
                        else:
                            process.kill()
                        process.wait()
                    raise
            response = work / 'response.txt'
            if response.exists():
                (out / 'response.txt').write_bytes(response.read_bytes())
            record['returncode'] = process.returncode
        completed = False
        for line in (out / 'events.jsonl').read_text(encoding='utf-8').splitlines():
            event = json.loads(line)
            if event.get('type') == 'turn.completed':
                completed = True
                record['usage'] = event.get('usage')
            if event.get('type') in ('error', 'turn.failed'):
                raise ValueError(f'CLI failure: {event}')
            item = event.get('item', {})
            if item and item.get('type') not in ('agent_message', 'reasoning'):
                raise ValueError(f'Unexpected tool/activity in translation: {item.get("type")}')
        if process.returncode or not completed or not (out / 'response.txt').exists():
            raise ValueError(f'CLI did not complete successfully (exit {process.returncode}); see stderr.txt')
        record['status'] = 'completed'
        return record, (out / 'response.txt').read_text(encoding='utf-8')
    except KeyboardInterrupt:
        record.update(status='interrupted', error='Interrupted; no retry')
        raise
    except (OSError, ValueError) as exc:
        record.update(status='failed', error=str(exc))
        return record, None
    finally:
        record['wall_seconds'] = round(time.monotonic() - started, 3)
        record['finished_utc'] = now()
        save(out / 'call.json', record)


def translate(e, mode, model, binary, out, dry_run=False, effort=None):
    calls, result = [], {}
    cli_options = {'effort': effort} if effort is not None else {}
    merged, _ = merge_dialogue_rows(e.rows)
    if mode == 'both':
        system, user, schema = both_request(e)
        call, content = run_cli(binary, model, system, user, schema, out / 'both', dry_run, **cli_options)
        calls.append(call)
        if content is not None:
            result = parse_both(e, content)
    else:
        male = None
        for gender in ('male', 'female'):
            if gender == 'female' and len(DialogTranslator._empty_female_ids(merged)) == len(merged) - 1:
                result[gender] = {row[1]: '' for row in e.rows[1:]}
                break
            system, user = e.build('production', e.rows[1:], gender, male)
            schema = DialogTranslator._translation_schema(merged, female=gender == 'female')
            call, content = run_cli(binary, model, system, user, schema, out / gender, dry_run, **cli_options)
            calls.append(call)
            if content is None:
                break  # No female request without a validated male reply, no retry.
            parsed = {'translations': {}}
            e.parse(parsed, content, e.rows[1:], gender)
            if parsed.get('error'):
                raise ValueError(parsed['error'])
            result[gender] = parsed['translations']
            male = {str(i): result['male'][row[1]] for i, row in enumerate(e.rows[1:], 1)}
    return calls, result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', nargs='+', default=['gpt-6-luna'])
    parser.add_argument('--modes', nargs='+', choices=['both', 'two-pass'], default=['both'])
    parser.add_argument('--datasets', default='inkgallery', help='comma-separated fixture names, or all')
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--effort', choices=['low', 'medium', 'high', 'xhigh', 'max', 'ultra'],
                        help='explicit Codex reasoning effort; omitted uses the model default')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--codex-bin', default='codex')
    parser.add_argument('--dry-run', action='store_true', help='save prompts/schemas without calling Codex')
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    names = None if args.datasets == 'all' else [name.strip() for name in args.datasets.split(',')]
    chosen = datasets(names)
    if not chosen or (names is not None and set(names) != {name for name, _ in chosen}):
        parser.error('Unknown/empty dataset; available: ' + ', '.join(name for name, _ in datasets()))
    out = (args.out or HERE / 'codex_translation' / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')).resolve()
    out.mkdir(parents=True, exist_ok=False)  # Never overwrite or silently resume an earlier run.
    manifest = {'status': 'running', 'started_utc': now(), 'settings': dict(vars(args), out=str(out)),
                'datasets': [name for name, _ in chosen], 'runs': [], 'sha256': {},
                'manual_review': 'pending', 'provider': 'Codex CLI; existing login; no API calls from Python'}
    files = [Path(__file__), HERE / 'diagnose_translation.py', HERE / 'run_translate_verify.py',
             HERE.parent / 'translate_dialogs.py', HERE.parent / 'translation_common.py', HERE.parent / 'dict.csv']
    try:
        if not args.dry_run:
            manifest['codex_version'] = subprocess.check_output([args.codex_bin, '--version'], text=True).strip()
        with (out / 'outputs.csv').open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['dataset', 'model', 'mode', 'repeat', 'Line_ID', 'English_Male',
                             'English_Female', 'Russian_Male', 'Russian_Female'])
            for name, checks in chosen:
                e = experiment(checks, out / 'inputs' / name)
                config = json.loads(checks.read_text(encoding='utf-8'))
                files += [checks, e.input_path, (checks.parent / config['actors']).resolve()]
                for model_index, model in enumerate(args.models, 1):
                    for mode in args.modes:
                        for repeat in range(1, args.repeats + 1):
                            folder = out / name / f'model-{model_index}' / mode / str(repeat)
                            print(f'{name}: {model} {mode} repeat {repeat}', flush=True)
                            run = {'dataset': name, 'model': model, 'mode': mode, 'repeat': repeat,
                                   'status': 'prepared' if args.dry_run else 'running', 'checks': [],
                                   'evaluation_version': config.get('version', 'unversioned')}
                            manifest['runs'].append(run)
                            save(out / 'manifest.json', manifest)
                            calls, translated = translate(e, mode, model, args.codex_bin, folder, args.dry_run, args.effort)
                            run['calls'] = calls
                            if args.dry_run:
                                continue
                            if set(translated) != {'male', 'female'}:
                                raise ValueError('Translation incomplete; see saved call.json / stderr.txt')
                            targets = set(e.checks['lines'])
                            run['checks'] = [c for gender in ('male', 'female') for key in sorted(targets)
                                             for c in e.score(key, gender, translated[gender].get(key))]
                            run['pair_reviews'] = e.review_pairs(e.rows[1:], targets, translated['male'], translated['female'])
                            run['status'] = 'completed'
                            save(folder / 'validated.json', translated)
                            for row in e.rows[1:]:
                                writer.writerow([name, model, mode, repeat, row[1], row[3],
                                                 female_source(dict(zip(e.header, row)), row[3]),
                                                 translated['male'][row[1]], translated['female'][row[1]]])
                            handle.flush()
                            save(out / 'manifest.json', manifest)
        manifest['status'] = 'prepared' if args.dry_run else 'finished'
    except KeyboardInterrupt:
        manifest.update(status='interrupted', error='Interrupted; no retry/resume')
        if manifest['runs']:
            manifest['runs'][-1].update(status='interrupted', error='Interrupted; no retry/resume')
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        manifest.update(status='failed', error=str(exc))
        if manifest['runs']:
            manifest['runs'][-1].update(status='failed', error=str(exc))
    finally:
        manifest['finished_utc'] = now()
        manifest['sha256'] = {str(p.resolve().relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in files}
        save(out / 'manifest.json', manifest)
        lines = ['# Codex translation test', '', f"Status: {manifest['status']}", '',
                 'Targeted checks are not overall translation quality. Manual review is pending.', '',
                 '| Dataset | Model | Mode | Repeat | Status | Checks passed |', '|---|---|---|---:|---|---|']
        for run in manifest['runs']:
            checks = run['checks']
            score = f"{sum(c['ok'] for c in checks)}/{len(checks)}" if checks else 'not scored'
            lines.append(f"| {run['dataset']} | {run['model']} | {run['mode']} | {run['repeat']} | {run['status']} | {score} |")
        if manifest.get('error'):
            lines += ['', 'Error: ' + manifest['error']]
        (out / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f"{manifest['status'].upper()}: {out}", flush=True)
    return 0 if manifest['status'] in ('prepared', 'finished') else 1


if __name__ == '__main__':
    sys.exit(main())
