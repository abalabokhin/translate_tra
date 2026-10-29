#!/usr/bin/env python3
"""Translate with one model, then verify both gender columns with a second (thinking) model.

Two stages, both scored with the frozen checks:
  translate-verify  translator (production prompt, two passes) -> verifier -> fragment fixes
                    applied by code; compares checks before and after verification.
  planted           verifier only, on the synthetic reference translations: once unmodified
                    (false alarms) and once per case of known planted errors (recall).
The verifier reports issues; it never rewrites the table. A fix is applied only when its
fragment occurs exactly once and the line still passes structural validation.
See TRANSLATE_VERIFY_PLAN.md.
"""

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from diagnose_translation import Experiment, is_player, summarize
from run_all import Ollama, load
from run_non_thinking import thinking_setting
from translation_common import female_source, merge_dialogue_rows, read_csv, strict_json, validate_text

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[1]
TRANSLATOR = 'mistral-small3.2:24b'
VERIFIER = 'gemma4:12b'
MUTATIONS = SCRIPT_DIR / 'verify_mutations.json'
CATEGORIES = ['player_gender', 'npc_gender', 'third_person', 'female_source', 'meaning', 'omission',
              'addition', 'address_form', 'grammar', 'glossary', 'shared_string', 'other']
VERIFY_RULES = """You review a Russian translation of English Infinity Engine game dialogue.
Each line has two Russian versions: russian_male is shown when the protagonist (Player1) is male,
russian_female when Player1 is female. Report real errors only, not style preferences or acceptable
alternative wordings. Check every line for:
1. player_gender: every word referring to Player1 (past-tense verbs, short adjectives, participles,
   nouns of address such as путник/путница, искатель приключений/искательница приключений) is
   masculine in russian_male and feminine in russian_female.
2. npc_gender, third_person: words about anyone else follow that character's fixed gender in BOTH
   versions. A man being talked about stays male in russian_female.
3. The two versions may differ only in words about Player1, and in meaning where english_female
   differs from english. Any other difference is an error in one of them.
4. female_source: when english_female is given, russian_female translates english_female.
5. meaning, omission, addition: every fact, name, condition, negation, number and tense is kept and
   nothing is invented. Seeing a book is not reading it.
6. address_form: ты/тебя/твой for one addressee, including nobles; вы only for a group.
7. grammar: agreement, case, spelling, punctuation.
8. glossary: glossary terms are used and inflected consistently.
9. shared_string: a line with several speakers is one game string; its single wording must suit the
   gender of every speaker.
Speaker and gender facts are given; the addressee follows from the speakers and predecessors.
For each error give the line id, the column to change (male, female or both), the exact wrong
fragment copied from that column (problem: short, but unique within the line) and its replacement.
Keep engine tokens such as <CHARNAME> and %var%, line breaks, quotes, asterisks and brackets.
Do not rewrite correct text. Report nothing for a correct line. Return only the requested JSON."""


def now():
    return datetime.now(timezone.utc).isoformat()


def datasets(names=None):
    """InkGallery, the synthetic fixtures and the person-reviewed real-mod set (real_set/)."""
    found = [('inkgallery', SCRIPT_DIR / 'inkgallery_checks.json')] + [
        (p.parent.name, p) for folder in ('fixtures', 'real_set') for p in sorted((SCRIPT_DIR / folder).glob('*/checks.json'))]
    return [d for d in found if names is None or d[0] in names]


def reference_complete(checks):
    """A reference can stand in for correct text only when every nonempty source has a translation."""
    path = checks.parent / 'reference.csv'
    if not path.exists():
        return False
    _, refs = read_csv(path, ['Line_ID', 'Russian_Male', 'Russian_Female'])
    e = json.loads(checks.read_text(encoding='utf-8'))
    _, rows = read_csv(checks.parent / e['input'], ['Line_ID', 'Dialogue_Text'])
    by_id = {r['Line_ID']: r for r in refs}
    return all(r['Line_ID'] in by_id and (by_id[r['Line_ID']]['Russian_Male'] or not r['Dialogue_Text'].strip())
               for r in rows)


def experiment_for(args, checks, out, model=None, think='off'):
    options = argparse.Namespace(checks=str(checks), actors=None, dictionary=str(SCRIPT_DIR.parent / 'dict.csv'),
                                 url=args.url, num_ctx=str(args.translator_num_ctx), seed=None, dry_run=False,
                                 out=str(out), models=[model or args.translator], prompts=['production'],
                                 scopes=['full'], think=[think], temperatures=['default'], repeats=args.repeats)
    return Experiment(options)


# ---------- verifier request and fixes ----------

def verify_request(e, merged, male, female):
    """User message for one dialogue; merged are prompt rows (header first), male/female id -> text."""
    header, rows = merged[0], merged[1:]
    ids = {row[1]: str(i) for i, row in enumerate(rows, 1)}
    actors = sorted({a for row in rows for a in row[0].split(';') if not is_player(a)})
    dialogue = []
    for i, row in enumerate(rows, 1):
        source = dict(zip(header, row))
        speakers = ['Player1' if is_player(a) else a for a in row[0].split(';')]
        genders = ['male in russian_male, female in russian_female' if a == 'Player1'
                   else e.prod.actors.get(a.casefold(), 'unknown') for a in speakers]
        line = {'id': str(i), 'speaker': speakers[0] if len(speakers) == 1 else speakers,
                'speaker_gender': genders[0] if len(genders) == 1 else genders,
                'predecessors': [ids[p] for p in row[2].split(';') if p in ids],
                'english': row[3]}
        female_english = female_source(source, row[3])
        if female_english != row[3]:
            line['english_female'] = female_english
        line.update(russian_male=male[str(i)], russian_female=female[str(i)])
        dialogue.append(line)
    glossary = e.prod._build_dictionary_context('\n'.join(
        row[3] + '\n' + female_source(dict(zip(header, row)), row[3]) for row in rows))
    return json.dumps({'task': 'List every error in russian_male and russian_female.',
                       'actors': e.prod._build_actor_info(actors), 'glossary': glossary,
                       'graph_notes': 'Predecessors are alternative immediately preceding lines.',
                       'dialogue': dialogue}, ensure_ascii=False)


def verify_schema(merged):
    item = {'type': 'object', 'additionalProperties': False,
            'required': ['id', 'column', 'category', 'problem', 'replacement', 'reason'],
            'properties': {'id': {'type': 'string', 'enum': [str(i) for i in range(1, len(merged))]},
                           'column': {'type': 'string', 'enum': ['male', 'female', 'both']},
                           'category': {'type': 'string', 'enum': CATEGORIES},
                           'problem': {'type': 'string'}, 'replacement': {'type': 'string'},
                           'reason': {'type': 'string'}}}
    return {'type': 'object', 'additionalProperties': False, 'required': ['issues'],
            'properties': {'issues': {'type': 'array', 'items': item}}}


def parse_issues(content):
    result = strict_json(content)
    if not isinstance(result, dict) or set(result) != {'issues'} or not isinstance(result['issues'], list):
        raise ValueError('Expected one JSON object containing only issues')
    keys = {'id', 'column', 'category', 'problem', 'replacement', 'reason'}
    for issue in result['issues']:
        if not isinstance(issue, dict) or set(issue) != keys or not all(isinstance(v, str) for v in issue.values()):
            raise ValueError(f'Malformed issue: {issue!r}')
    return result['issues']


def apply_issues(merged, male, female, issues):
    """Return (male, female, decisions). Each fragment fix applies only if unambiguous and valid."""
    header, rows = merged[0], merged[1:]
    sources = {str(i): {'male': row[3], 'female': female_source(dict(zip(header, row)), row[3])}
               for i, row in enumerate(rows, 1)}
    texts = {'male': dict(male), 'female': dict(female)}
    decisions = []
    for issue in issues:
        outcome = {}
        for column in (('male', 'female') if issue['column'] == 'both' else (issue['column'],)):
            line = issue['id']
            text = texts.get(column, {}).get(line)
            count = text.count(issue['problem']) if text is not None and issue['problem'] else 0
            if text is None:
                outcome[column] = 'rejected: unknown line or column'
            elif not sources[line][column].strip():
                outcome[column] = 'rejected: source is empty, so the translation stays empty'
            elif issue['problem'] == issue['replacement']:
                outcome[column] = 'rejected: replacement equals problem'
            elif count != 1:
                outcome[column] = f'rejected: fragment found {count} times'
            else:
                fixed = text.replace(issue['problem'], issue['replacement'])
                try:
                    validate_text(sources[line][column], fixed, f'line {line} {column}')
                except ValueError as exc:
                    outcome[column] = f'rejected: {exc}'
                else:
                    texts[column][line] = fixed
                    outcome[column] = 'applied'
        decisions.append(dict(issue, outcome=outcome))
    return texts['male'], texts['female'], decisions


def call_verifier(args, client, e, merged, male, female):
    """One verifier request; returns (record, issues or None). No retry, repair or fallback."""
    model = args.verifier
    if args.verifier_num_ctx == 'native':
        info = client.get('/api/show', {'model': model}).get('model_info', {})
        num_ctx = info.get(f"{info.get('general.architecture')}.context_length")
        if not isinstance(num_ctx, int):
            raise ValueError(f'Cannot discover native context for {model}; pass --verifier-num-ctx')
    else:
        num_ctx = int(args.verifier_num_ctx)
    payload = {'model': model, 'format': verify_schema(merged), 'stream': False,
               'options': {'num_ctx': num_ctx, 'num_predict': args.verifier_num_predict},
               'messages': [{'role': 'system', 'content': VERIFY_RULES},
                            {'role': 'user', 'content': verify_request(e, merged, male, female)}]}
    if args.verifier_think != 'default':
        payload['think'] = args.verifier_think == 'on'
    start = time.time()
    try:
        result = client.get('/api/chat', payload)
    except urllib.error.HTTPError as exc:
        result = {'error': f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        result = {'error': str(exc)}
    message = result.get('message', {})
    record = {'request': payload, 'error': result.get('error'), 'content': message.get('content'),
              'thinking': message.get('thinking'), 'done_reason': result.get('done_reason'),
              'eval_count': result.get('eval_count'), 'prompt_eval_count': result.get('prompt_eval_count'),
              'wall_seconds': round(time.time() - start, 2), 'gpu': e.gpu_share(model)}
    issues = None
    if not record['error'] and record['done_reason'] != 'stop':
        record['error'] = f"incomplete generation: {record['done_reason']}"
    if not record['error']:
        try:
            issues = parse_issues(record['content'] or '')
        except ValueError as exc:
            record['error'] = f'structural: {exc}'
    return record, issues


# ---------- scoring helpers ----------

def by_slot(merged, slots, values):
    """Line_ID -> text  to  prompt id -> text (first row of each reused string)."""
    first = {}
    for line_id, slot in slots.items():
        first.setdefault(str(slot), line_id)
    return {i: values[first[i]] for i in (str(n) for n in range(1, len(merged)))}


def failed_checks(e, slots, male, female):
    """Prompt-id texts -> {(Line_ID, gender): [failed check names]} over all checked lines."""
    result = {}
    for line_id in e.checks['lines']:
        for gender, texts in (('male', male), ('female', female)):
            checks = e.score(line_id, gender, texts[str(slots[line_id])])
            result[(line_id, gender)] = [c['check'] for c in checks if not c['ok']]
    return result


def count_checks(e):
    return sum(len(e.score(line_id, gender, '')) for line_id in e.checks['lines'] for gender in ('male', 'female'))


def write_jsonl(path, record):
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + '\n')


# ---------- stages ----------

def translate_verify(args, client, out, name, checks, translator_think):
    folder = out / 'translate-verify' / name
    e = experiment_for(args, checks, folder / 'translation', think=translator_think)
    e.run()
    summarize(folder / 'translation')
    merged, slots = merge_dialogue_rows(e.rows)
    records = load(folder / 'translation')
    expected = count_checks(e)
    results = []
    for repeat in range(1, args.repeats + 1):
        passes = {r['gender']: r for r in records if r['config']['repeat'] == repeat}
        entry = dict(dataset=name, repeat=repeat, expected_checks=expected)
        if any(passes.get(g, {}).get('error') or g not in passes for g in ('male', 'female')):
            entry['skipped'] = 'translation failed validation; nothing to verify'
            results.append(entry)
            continue
        male = by_slot(merged, slots, passes['male']['translations'])
        female = by_slot(merged, slots, passes['female']['translations'])
        print(f'  VERIFY {name} repeat {repeat}', flush=True)
        record, issues = call_verifier(args, client, e, merged, male, female)
        new_male, new_female, decisions = apply_issues(merged, male, female, issues or [])
        before, after = failed_checks(e, slots, male, female), failed_checks(e, slots, new_male, new_female)
        write_jsonl(folder / 'verifier.jsonl', dict(record, repeat=repeat, issues=issues, decisions=decisions))
        entry.update(verifier_error=record['error'], verifier_seconds=record['wall_seconds'],
                     verifier_tokens=record['eval_count'], gpu=record['gpu'], issues=len(issues or []),
                     applied=sum('applied' in d['outcome'].values() for d in decisions),
                     checks_before=expected - sum(map(len, before.values())),
                     checks_after=expected - sum(map(len, after.values())),
                     checks_fixed=sum(len(set(before[k]) - set(after[k])) for k in before),
                     checks_broken=sum(len(set(after[k]) - set(before[k])) for k in before),
                     lines_changed=sum(male[i] != new_male[i] for i in male) + sum(female[i] != new_female[i] for i in female))
        results.append(entry)
        table = folder / 'before_after.csv'
        new_table = not table.exists()
        with table.open('a', encoding='utf-8-sig' if new_table else 'utf-8', newline='') as handle:
            writer = csv.writer(handle)
            if new_table:
                writer.writerow(['repeat', 'Line_ID', 'gender', 'translated', 'verified', 'changed',
                                 'failed_checks_before', 'failed_checks_after'])
            for i, row in enumerate(merged[1:], 1):
                for gender, old, new in (('male', male, new_male), ('female', female, new_female)):
                    key = (row[1], gender)
                    writer.writerow([repeat, row[1], gender, old[str(i)], new[str(i)], old[str(i)] != new[str(i)],
                                     '; '.join(before.get(key, [])), '; '.join(after.get(key, []))])
        print(f"    {entry['issues']} issues, {entry['applied']} applied; checks {entry['checks_before']} -> "
              f"{entry['checks_after']}/{expected}; {record['wall_seconds']}s {record['error'] or ''}", flush=True)
    return results


def mutate(merged, slots, male, female, mutations):
    texts = {'male': dict(male), 'female': dict(female)}
    for m in mutations:
        line, column = str(slots[m['line']]), m['column']
        source = female_source(dict(zip(merged[0], merged[int(line)])), merged[int(line)][3]) \
            if column == 'female' else merged[int(line)][3]
        if texts[column][line].count(m['from']) != 1:
            raise ValueError(f"Mutation fragment must occur once: {m}")
        texts[column][line] = texts[column][line].replace(m['from'], m['to'])
        validate_text(source, texts[column][line], f"mutation {m['line']} {column}")
    return texts['male'], texts['female']


def planted(args, client, out, name, checks):
    folder = out / 'planted' / name
    folder.mkdir(parents=True, exist_ok=True)
    e = experiment_for(args, checks, folder, model=args.verifier)
    merged, slots = merge_dialogue_rows(e.rows)
    _, refs = read_csv(checks.parent / 'reference.csv', ['Line_ID', 'Russian_Male', 'Russian_Female'])
    refs = {r['Line_ID']: r for r in refs}
    ref_male = by_slot(merged, slots, {k: v['Russian_Male'] for k, v in refs.items()})
    ref_female = by_slot(merged, slots, {k: v['Russian_Female'] for k, v in refs.items()})
    cases = [{'name': 'clean reference', 'mutations': []}]
    cases += json.loads(MUTATIONS.read_text(encoding='utf-8'))['fixtures'].get(name, [])
    results = []
    for repeat in range(1, args.repeats + 1):
        for case in cases:
            male, female = mutate(merged, slots, ref_male, ref_female, case['mutations'])
            print(f"  PLANTED {name} / {case['name']} repeat {repeat}", flush=True)
            record, issues = call_verifier(args, client, e, merged, male, female)
            new_male, new_female, decisions = apply_issues(merged, male, female, issues or [])
            write_jsonl(folder / 'verifier.jsonl', dict(record, repeat=repeat, case=case['name'],
                                                        mutations=case['mutations'], issues=issues, decisions=decisions))
            planted_cells = {(str(slots[m['line']]), m['column']) for m in case['mutations']}
            after = {'male': new_male, 'female': new_female}
            reference = {'male': ref_male, 'female': ref_female}
            entry = dict(dataset=name, case=case['name'], repeat=repeat, verifier_error=record['error'],
                         verifier_seconds=record['wall_seconds'], verifier_tokens=record['eval_count'],
                         issues=len(issues or []), applied=sum('applied' in d['outcome'].values() for d in decisions),
                         collateral_changes=sum(after[c][i] != reference[c][i] for c in after for i in after[c]
                                                if (i, c) not in planted_cells),
                         checks_failed_after=sum(map(len, failed_checks(e, slots, new_male, new_female).values())),
                         mutations=[])
            for m in case['mutations']:
                line, column = str(slots[m['line']]), m['column']
                flagged = any(i['id'] == line and i['column'] in (column, 'both') for i in issues or [])
                entry['mutations'].append(dict(m, flagged=flagged,
                                               restored_exact=after[column][line] == reference[column][line],
                                               wrong_text_removed=m['to'] not in after[column][line]))
            results.append(entry)
            found = sum(m['flagged'] for m in entry['mutations'])
            print(f"    {entry['issues']} issues, {entry['applied']} applied; planted flagged {found}/"
                  f"{len(case['mutations'])}; collateral {entry['collateral_changes']} {record['error'] or ''}", flush=True)
    return results


# ---------- report ----------

def report(out, manifest):
    tv, pl = manifest.get('translate_verify', []), manifest.get('planted', [])
    lines = ['# Translate + verify experiment', '',
             f"Status: {manifest['status']}. Started {manifest['started_utc']}, finished {manifest.get('finished_utc', '-')}.",
             f"Translator `{manifest['settings']['translator']}` (think {manifest['settings']['translator_think']}, "
             f"ctx {manifest['settings']['translator_num_ctx']}); verifier `{manifest['settings']['verifier']}` "
             f"(think {manifest['settings']['verifier_think']}, ctx {manifest['settings']['verifier_num_ctx']}, "
             f"num_predict {manifest['settings']['verifier_num_predict']}); {manifest['settings']['repeats']} repeats.", '',
             'Checks are the frozen targeted assertions, not overall quality. Fixes are applied by code only when the '
             'fragment is unique and the line stays structurally valid. Manual review of before_after.csv and '
             'verifier.jsonl is required before drawing conclusions.']
    if tv:
        lines += ['', '## Stage 1: translate, then verify', '',
                  '| Dataset | Verified repeats | Checks before | Checks after | Fixed | Broken | Issues | Applied | Lines changed | Verifier s |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for name in dict.fromkeys(r['dataset'] for r in tv):
            rows = [r for r in tv if r['dataset'] == name and 'skipped' not in r and not r.get('verifier_error')]
            total = sum(r['expected_checks'] for r in rows)
            s = lambda k: sum(r[k] for r in rows)  # noqa: E731
            lines.append(f"| {name} | {len(rows)}/{sum(r['dataset'] == name for r in tv)} | {s('checks_before')}/{total} | "
                         f"{s('checks_after')}/{total} | {s('checks_fixed')} | {s('checks_broken')} | {s('issues')} | "
                         f"{s('applied')} | {s('lines_changed')} | {sum(r['verifier_seconds'] for r in rows):.1f} |")
        failures = [r for r in tv if 'skipped' in r or r.get('verifier_error')]
        for r in failures:
            lines.append(f"\n- {r['dataset']} repeat {r['repeat']}: {r.get('skipped') or r['verifier_error']}")
    if pl:
        lines += ['', '## Stage 2: planted errors in the reference translations', '',
                  '| Dataset | Planted flagged | Restored exactly | Wrong text removed | Clean-run issues | Clean-run changes | Collateral changes | Checks failed after | Verifier errors |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for name in dict.fromkeys(r['dataset'] for r in pl):
            rows = [r for r in pl if r['dataset'] == name]
            ok = [r for r in rows if not r['verifier_error']]
            muts = [m for r in ok for m in r['mutations']]
            clean = [r for r in ok if not r['mutations']]
            lines.append(f"| {name} | {sum(m['flagged'] for m in muts)}/{len(muts)} | "
                         f"{sum(m['restored_exact'] for m in muts)}/{len(muts)} | {sum(m['wrong_text_removed'] for m in muts)}/{len(muts)} | "
                         f"{sum(r['issues'] for r in clean)} | {sum(r['collateral_changes'] for r in clean)} | "
                         f"{sum(r['collateral_changes'] for r in ok if r['mutations'])} | "
                         f"{sum(r['checks_failed_after'] for r in ok)} | {len(rows) - len(ok)}/{len(rows)} |")
        by_category = {}
        for m in (m for r in pl if not r['verifier_error'] for m in r['mutations']):
            by_category.setdefault(m['category'], []).append(m['flagged'])
        lines += ['', '| Planted category | Flagged |', '|---|---:|']
        lines += [f'| {k} | {sum(v)}/{len(v)} |' for k, v in sorted(by_category.items())]
    lines += ['', '## Manual review', '', 'Pending.']
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def save(out, manifest):
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report(out, manifest)


def model_facts(client, tag):
    info = client.get('/api/show', {'model': tag})
    digest = next((m.get('digest') for m in client.get('/api/tags').get('models', [])
                   if tag in (m.get('name'), m.get('model'))), None)
    return info, dict(tag=tag, digest=digest, capabilities=info.get('capabilities'), details=info.get('details'))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--translator', default=TRANSLATOR)
    parser.add_argument('--translator-think', default='auto', choices=['auto', 'default', 'on', 'off'],
                        help="auto: off when the model supports thinking, otherwise the model default")
    parser.add_argument('--translator-num-ctx', type=int, default=8192)
    parser.add_argument('--verifier', default=VERIFIER)
    parser.add_argument('--verifier-think', default='on', choices=['default', 'on', 'off'])
    parser.add_argument('--verifier-num-ctx', default='native', help="tokens, or 'native'")
    parser.add_argument('--verifier-num-predict', type=int, default=32768,
                        help='generation cap per verifier request (-1 = uncapped); a capped reply is a failure')
    parser.add_argument('--stages', default='translate-verify,planted')
    parser.add_argument('--datasets', help='comma-separated subset (default: all five)')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--url', default='http://localhost:11434')
    parser.add_argument('--out', help='default: experiments/translate_verify/<UTC timestamp>')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    stages = [s.strip() for s in args.stages.split(',') if s.strip()]
    if not stages or set(stages) - {'translate-verify', 'planted'}:
        parser.error('--stages must be a subset of translate-verify,planted')
    if args.repeats < 1 or args.translator_num_ctx < 1:
        parser.error('Context and repeats must be positive')
    names = [n.strip() for n in args.datasets.split(',')] if args.datasets else None
    chosen = datasets(names)
    if names and len(chosen) != len(names):
        parser.error(f'Unknown dataset in {names}')
    with_reference = [(n, c) for n, c in chosen if reference_complete(c)]
    for n, c in chosen:
        if (c.parent / 'reference.csv').exists() and (n, c) not in with_reference:
            print(f'planted: skipping {n}; its reference.csv is incomplete')
    mutations = json.loads(MUTATIONS.read_text(encoding='utf-8'))['fixtures']
    planned = {'translate-verify': len(chosen) * args.repeats * 3,
               'planted': sum(1 + len(mutations.get(n, [])) for n, _ in with_reference) * args.repeats}
    print(f'Translator {args.translator}; verifier {args.verifier} (think {args.verifier_think}).')
    for stage in stages:
        print(f'{stage}: up to {planned[stage]} requests')
    if args.dry_run:
        return 0

    out = Path(args.out or SCRIPT_DIR / 'translate_verify' / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    if (out / 'manifest.json').exists():
        parser.error('Use a fresh output directory; automatic resume is not implemented')
    out.mkdir(parents=True, exist_ok=True)
    client = Ollama(args.url)
    translator_info, translator = model_facts(client, args.translator)
    _, verifier = model_facts(client, args.verifier)
    translator_think = thinking_setting(translator_info) if args.translator_think == 'auto' else args.translator_think
    files = [Path(__file__).resolve(), MUTATIONS, SCRIPT_DIR / 'diagnose_translation.py',
             SCRIPT_DIR.parent / 'translate_dialogs.py', SCRIPT_DIR.parent / 'translation_common.py',
             SCRIPT_DIR.parent / 'dict.csv'] + [c for _, c in chosen]
    files += [p for p in (SCRIPT_DIR / 'fixtures').rglob('*') if p.is_file()]
    manifest = dict(status='running', started_utc=now(), stages=stages,
                    settings=dict(vars(args), translator_think=translator_think),
                    models=dict(translator=translator, verifier=verifier),
                    ollama_version=client.get('/api/version'),
                    git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                    working_tree_diff=subprocess.check_output(['git', 'diff'], cwd=REPO, text=True),
                    sha256={str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    print(f'RESULTS: {out}', flush=True)
    save(out, manifest)
    try:
        if 'translate-verify' in stages:
            manifest['translate_verify'] = []
            for name, checks in chosen:
                print(f'DATASET {name}', flush=True)
                manifest['translate_verify'] += translate_verify(args, client, out, name, checks, translator_think)
                save(out, manifest)
        if 'planted' in stages:
            manifest['planted'] = []
            for name, checks in with_reference:
                manifest['planted'] += planted(args, client, out, name, checks)
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
