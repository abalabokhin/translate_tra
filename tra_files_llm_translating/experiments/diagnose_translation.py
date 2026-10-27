#!/usr/bin/env python3
"""
Diagnostic experiment: why does the local LLM get Russian dialogue wrong?

Runs the same small dialogue through a grid of settings and scores every output
against expected Russian forms (checks JSON). Factors:
  model, prompt framing, request size (scope), thinking, temperature, repeats.
Standalone: it does not change or call the production translator's Ollama client.
See experiments/README.md for usage.
"""

import argparse
import csv
import io
import itertools
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
from translate_dialogs import TRANSLATION_RULES, DialogTranslator  # noqa: E402

PROMPTS = ('production', 'reframed', 'reframed-addressee', 'examples', 'markup')
SCOPES = ('full', 'pair')
# Worked examples. Deliberately unrelated to the scored InkGallery lines (other names,
# no "seen", no "how I'm doing" idiom) so they teach the pattern, not the answers.
# Characters: Mirelle (female innkeeper), Garrick (male guard), a male necromancer.
EXAMPLES = [
    {'case': 'Player1 speaks to a female NPC: ты-forms are feminine for BOTH Player1 genders',
     'speaker': 'Player1', 'listener': 'Mirelle (female)',
     'english': 'You told me you used to live in Waterdeep?',
     'male': 'Ты говорила, что раньше жила в Глубоководье?',
     'female': 'Ты говорила, что раньше жила в Глубоководье?',
     'markup': 'Ты говорила, что раньше жила в Глубоководье?'},
    {'case': "A male NPC speaks to Player1: only Player1's forms change; the NPC's own я-forms stay masculine",
     'speaker': 'Garrick (male)', 'listener': 'Player1',
     'english': "You're back! I was starting to worry.",
     'male': 'Ты вернулся! Я уже начал волноваться.',
     'female': 'Ты вернулась! Я уже начал волноваться.',
     'markup': 'Ты {вернулся|вернулась}! Я уже начал волноваться.'},
    {'case': 'Nouns of address and short adjectives follow Player1 too',
     'speaker': 'Mirelle (female)', 'listener': 'Player1',
     'english': 'Welcome, traveler. Sit down, you must be tired.',
     'male': 'Добро пожаловать, путник. Садись, ты, должно быть, устал.',
     'female': 'Добро пожаловать, путница. Садись, ты, должно быть, устала.',
     'markup': 'Добро пожаловать, {путник|путница}. Садись, ты, должно быть, {устал|устала}.'},
    {'case': 'A man being talked about stays male in the female version',
     'speaker': 'Player1', 'listener': 'Garrick (male)',
     'english': 'I saw the necromancer leave the tower. He was alone.',
     'male': 'Я видел, как некромант вышел из башни. Он был один.',
     'female': 'Я видела, как некромант вышел из башни. Он был один.',
     'markup': 'Я {видел|видела}, как некромант вышел из башни. Он был один.'},
    {'case': "Player1 speaks to a female NPC: Player1's я-forms vary, her ты-forms stay feminine",
     'speaker': 'Player1', 'listener': 'Mirelle (female)',
     'english': "You were right. I'm glad I came.",
     'male': 'Ты была права. Я рад, что пришёл.',
     'female': 'Ты была права. Я рада, что пришла.',
     'markup': 'Ты была права. Я {рад|рада}, что {пришёл|пришла}.'},
    {'case': 'Nothing depends on Player1: both versions identical, no markup',
     'speaker': 'Mirelle (female)', 'listener': 'Player1',
     'english': 'The rooms upstairs are free. Take the one at the end of the hall.',
     'male': 'Комнаты наверху свободны. Займи ту, что в конце коридора.',
     'female': 'Комнаты наверху свободны. Займи ту, что в конце коридора.',
     'markup': 'Комнаты наверху свободны. Займи ту, что в конце коридора.'},
]
MARKUP_RULE = """6. Player1's gender is NOT fixed. Write each line ONCE. Wherever a word's form depends on
   Player1's gender, write both forms as {masculine|feminine}, e.g. Ты {вернулся|вернулась}!
   Mark every such word (verbs, short adjectives, nouns of address, pronouns), and nothing else:
   other characters' genders are fixed, so their forms are never marked. No nested braces."""
MARKUP = re.compile(r'\{([^{}|]*)\|([^{}|]*)\}')

REFRAMED_RULES = """You translate dialogue from an English fantasy role-playing game into Russian.
1. Translate faithfully and naturally: keep every sentence and its meaning; use idiomatic Russian, not word-for-word English.
2. Address a single person with ты/тебя/тебе/твой, never вы, even nobles. Use вы only when the English addresses a group.
3. Each line has a "grammar" note giving the gender of я (the speaker) and, when known, of ты (the listener).
   Follow it exactly for past-tense verbs, short adjectives and nouns of address (путник/путница, рад/рада).
4. Characters' genders never change between lines or passes.
5. Copy tokens such as <CHARNAME>, <PLAYER1>, %name% exactly. Use the glossary terms.
Return only the requested JSON."""


def gender_word(description):
    text = (description or '').casefold()
    if re.search(r'\bfemale\b', text):
        return 'feminine'
    if re.search(r'\bmale\b', text):
        return 'masculine'
    return 'unknown'


def is_player(name):
    return name.casefold() in ('player', 'player1')


class Experiment:
    def __init__(self, args):
        self.args = args
        self.checks_path = Path(args.checks).resolve()
        self.checks = json.loads(self.checks_path.read_text(encoding='utf-8'))
        base = self.checks_path.parent
        self.input_path = (base / self.checks['input']).resolve()
        actors_path = Path(args.actors).resolve() if args.actors else (base / self.checks['actors']).resolve()
        self.out = Path(args.out)
        self.out.mkdir(parents=True, exist_ok=True)
        # Reuse production prompt building, glossary and validation unchanged.
        self.prod = DialogTranslator(source_folder=str(self.input_path.parent), target_folder=str(self.out),
                                     actors_file=str(actors_path), dict_file=args.dictionary)
        with open(self.input_path, encoding='utf-8-sig', newline='') as f:
            self.rows = [row for row in csv.reader(f, strict=True) if row]
        self.header = self.rows[0]
        self.base = 'http://' + args.url.split('://', 1)[-1].split('/api/', 1)[0].rstrip('/')
        self.native_ctx = {}
        self.gpu_checked = set()

    # ---------- request construction ----------

    def scopes(self, scope):
        """Return (row subset, target Line_IDs scored in it)."""
        body = self.rows[1:]
        if scope == 'full':
            return [(body, {r[1] for r in body if r[1] in self.checks['lines']})]
        by_id = {r[1]: r for r in body}
        result = []
        for row in body:
            if row[1] not in self.checks['lines']:
                continue
            context = [by_id[p] for p in row[2].split(';') if p in by_id]
            result.append((context + [row], {row[1]}))
        return result

    def csv_text(self, rows):
        buffer = io.StringIO(newline='')
        csv.writer(buffer).writerows([self.header] + rows)
        return buffer.getvalue()

    def build(self, prompt, rows, gender, male=None):
        """Return (system, user) for one pass. For 'markup', gender is 'both' (single pass)."""
        text = self.csv_text(rows)
        all_text = '\n'.join(r[3] for r in rows)
        glossary = self.prod._build_dictionary_context(all_text)
        if prompt == 'production':
            actors = self.prod._build_actor_info(sorted({r[0] for r in rows}))
            previous = json.dumps({'translations': male}, ensure_ascii=False) if male else None
            return TRANSLATION_RULES, self.prod._create_translation_prompt(text, gender, actors, glossary, previous)

        use_addressee = prompt == 'reframed-addressee'
        if use_addressee and 'Addressee' not in self.header:
            raise ValueError('reframed-addressee needs an Addressee column in the input CSV')
        markup = prompt == 'markup'
        player = {'male': 'masculine', 'female': 'feminine', 'both': '{masculine|feminine} — mark variants'}[gender]
        ids = {r[1]: str(i) for i, r in enumerate(rows, 1)}
        characters = {'Player1': ('male or female: mark gender-dependent words' if markup
                                  else f'{gender} (the protagonist)')}
        dialogue = []
        for i, row in enumerate(rows, 1):
            source = dict(zip(self.header, row))
            speaker = 'Player1' if is_player(row[0]) else row[0]
            names = [speaker]
            note = f"я: {player if speaker == 'Player1' else gender_word(self.prod.actors.get(speaker.casefold()))} ({speaker})"
            if use_addressee and source.get('Addressee'):
                listener = 'Player1' if is_player(source['Addressee']) else source['Addressee']
                names.append(listener)
                note += (f"; ты: {player if listener == 'Player1' else gender_word(self.prod.actors.get(listener.casefold()))}"
                         f" ({listener})")
            for name in names:
                if name != 'Player1':
                    characters[name] = self.prod.actors.get(name.casefold(), 'unknown gender')
            line = {'id': str(i), 'speaker': speaker, 'grammar': note,
                    'predecessors': [ids[p] for p in row[2].split(';') if p in ids], 'english': row[3]}
            if male:
                line['male_translation'] = male[str(i)]
            dialogue.append(line)
        task = 'Translate every line.'
        if male:
            task = ('Player1 is now female. Each line has male_translation, written for a male Player1. '
                    'Change only the words whose form depends on Player1 being female, following the grammar notes; '
                    'copy everything else exactly. Return every line in full.')
        if markup:
            task = ('Translate every line once, marking every word whose form depends on Player1\'s gender '
                    'as {masculine|feminine}.')
        request = {'task': task, 'characters': characters, 'glossary': glossary}
        if prompt in ('examples', 'markup'):
            # Show only the fields relevant to this pass, so the examples match the requested output.
            keep = ['markup'] if markup else (['male', 'female'] if male else ['male'])
            request['worked_examples'] = [{k: e[k] for k in ('case', 'speaker', 'listener', 'english', *keep)}
                                          for e in EXAMPLES]
        request.update({'graph_notes': 'Predecessors are alternative immediately preceding lines.',
                        'dialogue': dialogue,
                        'output': {'translations': {l['id']: 'Russian text' for l in dialogue}}})
        return REFRAMED_RULES + ('\n' + MARKUP_RULE if markup else ''), json.dumps(request, ensure_ascii=False)

    @staticmethod
    def expand_markup(text):
        """Split {masculine|feminine} markup into two strings; reject malformed markup."""
        rest = MARKUP.sub('', text)
        if any(c in rest for c in '{}|'):
            raise ValueError(f'malformed markup: {text!r}')
        return MARKUP.sub(r'\1', text), MARKUP.sub(r'\2', text)

    # ---------- Ollama ----------

    def post(self, path, payload):
        req = urllib.request.Request(self.base + path, data=json.dumps(payload).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))

    def context_for(self, model):
        if self.args.num_ctx != 'native':
            return int(self.args.num_ctx)
        if model not in self.native_ctx:
            info = self.post('/api/show', {'model': model}).get('model_info', {})
            self.native_ctx[model] = info.get(f"{info.get('general.architecture')}.context_length")
            if not isinstance(self.native_ctx[model], int):
                raise ValueError(f'Cannot discover native context for {model}; pass --num-ctx')
        return self.native_ctx[model]

    def gpu_share(self, model):
        try:
            with urllib.request.urlopen(self.base + '/api/ps') as response:
                running = json.loads(response.read().decode('utf-8')).get('models', [])
        except (urllib.error.URLError, OSError, ValueError):
            return None
        for entry in running:
            if model in (entry.get('name'), entry.get('model')) and entry.get('size'):
                return {'size': entry['size'], 'size_vram': entry.get('size_vram', 0),
                        'gpu_percent': round(100 * entry.get('size_vram', 0) / entry['size'], 1)}
        return None

    def chat(self, config, system, user, schema):
        options = {'num_ctx': self.context_for(config['model']), 'num_predict': -1}
        if config['temperature'] != 'default':
            options['temperature'] = float(config['temperature'])
        if self.args.seed is not None:
            options['seed'] = self.args.seed
        payload = {'model': config['model'], 'format': schema, 'stream': False, 'options': options,
                   'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}
        if config['think'] != 'default':
            payload['think'] = config['think'] == 'on'
        start = time.time()
        try:
            result = self.post('/api/chat', payload)
        except urllib.error.HTTPError as exc:
            result = {'error': f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"}
        except (urllib.error.URLError, OSError) as exc:
            result = {'error': str(exc)}
        result['wall_seconds'] = round(time.time() - start, 2)
        key = (config['model'], options['num_ctx'])
        if key not in self.gpu_checked and 'error' not in result:
            self.gpu_checked.add(key)
            result['gpu'] = self.gpu_share(config['model'])
            share = result['gpu']
            if share and share['gpu_percent'] < 100:
                print(f"  WARNING: {config['model']} is only {share['gpu_percent']}% on GPU "
                      f"(CPU offload makes timings meaningless); consider a smaller --num-ctx", flush=True)
        return payload, result

    # ---------- scoring ----------

    def score(self, line_id, gender, text):
        line_checks = self.checks['lines'].get(line_id, {})
        results = []
        for check in self.checks.get('all', []) + line_checks.get('both', []) + line_checks.get(gender, []):
            if text is None:
                ok = False  # Missing output fails every expected check, including forbids.
            elif 'require' in check:
                ok = re.search(check['require'], text, re.IGNORECASE) is not None
            else:
                ok = re.search(check['forbid'], text, re.IGNORECASE) is None
            results.append({'line': line_id, 'gender': gender, 'check': check['name'], 'ok': ok})
        return results

    # ---------- running ----------

    def configs(self):
        a = self.args
        for model, prompt, scope, think, temp, rep in itertools.product(
                a.models, a.prompts, a.scopes, a.think, a.temperatures, range(1, a.repeats + 1)):
            yield {'model': model, 'prompt': prompt, 'scope': scope, 'think': think,
                   'temperature': temp, 'repeat': rep}

    def run(self):
        configs = list(self.configs())
        requests = sum((1 if c['prompt'] == 'markup' else 2) * len(self.scopes(c['scope'])) for c in configs)
        print(f'{len(configs)} runs, up to {requests} Ollama requests. Results: {self.out}', flush=True)
        if self.args.dry_run:
            return
        log = self.out / 'runs.jsonl'
        with open(log, 'a', encoding='utf-8') as handle:
            for n, config in enumerate(configs, 1):
                label = ' '.join(f'{k}={v}' for k, v in config.items())
                print(f'[{n}/{len(configs)}] {label}', flush=True)
                for rows, targets in self.scopes(config['scope']):
                    if config['prompt'] == 'markup':
                        self.run_markup(handle, config, rows, targets)
                        continue
                    schema = DialogTranslator._translation_schema([self.header] + rows)
                    male = None
                    for gender in ('male', 'female'):
                        system, user = self.build(config['prompt'], rows, gender, male)
                        payload, result = self.chat(config, system, user, schema)
                        record = self.record(config, gender, targets, payload, result)
                        if not record['error']:
                            self.parse(record, record['content'], rows, gender)
                        self.write(handle, record, rows, targets)
                        if record['error']:
                            if gender == 'male':
                                skipped = self.record(config, 'female', targets, None, {'wall_seconds': 0})
                                skipped.update(error='skipped: male pass failed', skipped=True,
                                               eval_count=0)
                                self.write(handle, skipped, rows, targets)
                            break  # female pass needs a valid male pass; no retry
                        male = {str(i): record['translations'][r[1]] for i, r in enumerate(rows, 1)}

    def run_markup(self, handle, config, rows, targets):
        """One request; the {masculine|feminine} reply becomes a male and a female record.
        The female record is marked 'derived' and carries no time/tokens of its own."""
        schema = DialogTranslator._translation_schema([self.header] + rows)
        system, user = self.build('markup', rows, 'both')
        payload, result = self.chat(config, system, user, schema)
        male = self.record(config, 'male', targets, payload, result)
        female = self.record(config, 'female', targets, None, result)
        female.update(derived=True, wall_seconds=0, eval_count=0, thinking=None)
        if not male['error']:
            try:
                values = json.loads(male['content'])['translations']
                split = {k: self.expand_markup(v) for k, v in values.items()}
                self.parse(male, json.dumps({'translations': {k: m for k, (m, _) in split.items()}}), rows, 'male')
                self.parse(female, json.dumps({'translations': {k: f for k, (_, f) in split.items()}}), rows, 'female')
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                male['error'] = female['error'] = f'structural: {exc}'
        for record in (male, female):
            self.write(handle, record, rows, targets)

    @staticmethod
    def record(config, gender, targets, payload, result):
        message = result.get('message', {})
        return {'config': config, 'gender': gender, 'targets': sorted(targets), 'request': payload,
                'error': result.get('error'), 'content': message.get('content'),
                'thinking': message.get('thinking'), 'done_reason': result.get('done_reason'),
                'eval_count': result.get('eval_count'), 'prompt_eval_count': result.get('prompt_eval_count'),
                'wall_seconds': result['wall_seconds'], 'gpu': result.get('gpu'), 'derived': False,
                'translations': {}, 'checks': []}

    def parse(self, record, content, rows, gender):
        try:
            values = DialogTranslator._parse_translation(content, [self.header] + rows, female=gender == 'female')
            record['translations'] = {r[1]: values[str(i)] for i, r in enumerate(rows, 1)}
        except ValueError as exc:
            record['error'] = f'structural: {exc}'

    def write(self, handle, record, rows, targets):
        for line_id in sorted(targets):
            text = None if record['error'] else record['translations'].get(line_id)
            record['checks'] += self.score(line_id, record['gender'], text)
        handle.write(json.dumps(record, ensure_ascii=False) + '\n')
        handle.flush()
        failed = [c for c in record['checks'] if not c['ok']]
        status = record['error'] or f"{len(record['checks']) - len(failed)}/{len(record['checks'])} checks ok"
        print(f"    {record['gender']:6} {','.join(sorted(targets)) if len(targets) < 3 else 'all':12} "
              f"{record['wall_seconds']:7.1f}s {record['eval_count'] or 0:6} tok  {status}", flush=True)


def summarize(out):
    out = Path(out)
    with open(out / 'runs.jsonl', encoding='utf-8') as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    groups = defaultdict(list)
    for r in records:
        c = r['config']
        groups[(c['model'], c['prompt'], c['scope'], c['think'], c['temperature'])].append(r)

    lines = ['# Diagnostic results', '',
             f'Source: `{out / "runs.jsonl"}` ({sum(not r.get("derived") and not r.get("skipped") for r in records)} requests). Checks = expected-form tests '
             'from the checks JSON, summed over repeats. Failed outputs and skipped female passes fail all expected checks. '
             'Time and tokens are per actual request.', '',
             '| model | prompt | scope | think | temp | runs | checks ok | failed requests | avg s | avg tokens |',
             '|---|---|---|---|---|---|---|---|---|---|']
    details = []
    with open(out / 'outputs.csv', 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['model', 'prompt', 'scope', 'think', 'temp', 'repeat', 'gender', 'Line_ID',
                         'failed_checks', 'russian'])
        for key, recs in sorted(groups.items()):
            checks = [c for r in recs for c in r['checks']]
            ok = sum(c['ok'] for c in checks)
            real = [r for r in recs if not r.get('derived') and not r.get('skipped')]
            errors = sum(1 for r in real if r['error'])
            runs = len({r['config']['repeat'] for r in recs})
            secs = sum(r['wall_seconds'] for r in real) / len(real)
            toks = sum(r['eval_count'] or 0 for r in real) / len(real)
            pct = f'{ok}/{len(checks)} ({100 * ok / len(checks):.0f}%)' if checks else '0/0'
            lines.append(f'| {" | ".join(str(k) for k in key)} | {runs} | {pct} | {errors} | {secs:.1f} | {toks:.0f} |')
            fails = defaultdict(int)
            totals = defaultdict(int)
            for c in checks:
                totals[(c['line'], c['gender'], c['check'])] += 1
                if not c['ok']:
                    fails[(c['line'], c['gender'], c['check'])] += 1
            if fails or errors:
                details.append(f'\n### {" / ".join(str(k) for k in key)}\n')
                for (line_id, gender, name), count in sorted(fails.items(), key=lambda x: -x[1]):
                    details.append(f'- {line_id} {gender}: {name} — failed {count}/{totals[(line_id, gender, name)]}')
                for r in recs:
                    if r['error']:
                        details.append(f"- request error (repeat {r['config']['repeat']}, {r['gender']}): {r['error'][:200]}")
            for r in recs:
                for line_id in r['targets']:
                    if line_id in r['translations']:
                        failed = '; '.join(c['check'] for c in r['checks'] if c['line'] == line_id and not c['ok'])
                        writer.writerow(list(key) + [r['config']['repeat'], r['gender'], line_id, failed,
                                                     r['translations'][line_id]])
    lines += ['', '## Failed checks by configuration'] + (details or ['', 'None.'])
    (out / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"Wrote {out / 'summary.md'} and {out / 'outputs.csv'}")


def split(value):
    return [v.strip() for v in value.split(',') if v.strip()]


def main():
    parser = argparse.ArgumentParser(description='Diagnose LLM dialogue translation errors with a settings grid.')
    parser.add_argument('--models', type=split, default=['qwen3.5:9b'], help='comma-separated Ollama model tags')
    parser.add_argument('--prompts', type=split, default=list(PROMPTS), help=f'subset of {",".join(PROMPTS)}')
    parser.add_argument('--scopes', type=split, default=list(SCOPES),
                        help='full = whole dialogue per request; pair = each checked line with its predecessors')
    parser.add_argument('--think', type=split, default=['off'],
                        help='subset of default,on,off (default: off, for a fast first stage; see README)')
    parser.add_argument('--temperatures', type=split, default=['default', '0.2'],
                        help="comma-separated; 'default' uses the model's own setting")
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--num-ctx', default='16384', help="context tokens, or 'native' like production")
    parser.add_argument('--seed', type=int, help='fixed seed (makes repeats identical at the same settings)')
    parser.add_argument('--checks', default=str(SCRIPT_DIR / 'inkgallery_checks.json'))
    parser.add_argument('--actors', help='override the actors CSV named in the checks file')
    parser.add_argument('--dictionary', default=str(SCRIPT_DIR.parent / 'dict.csv'))
    parser.add_argument('--url', default='http://localhost:11434')
    parser.add_argument('--out', help='results folder (default: experiments/results/<timestamp>)')
    parser.add_argument('--dry-run', action='store_true', help='print the number of requests and exit')
    parser.add_argument('--summarize', metavar='DIR', help='only rebuild summary.md/outputs.csv from DIR/runs.jsonl')
    args = parser.parse_args()

    if args.summarize:
        summarize(args.summarize)
        return 0
    for name, values, allowed in (('--prompts', args.prompts, PROMPTS), ('--scopes', args.scopes, SCOPES),
                                  ('--think', args.think, ('default', 'on', 'off'))):
        if not values or set(values) - set(allowed):
            parser.error(f'{name} must be a subset of {",".join(allowed)}')
    args.out = args.out or str(SCRIPT_DIR / 'results' / datetime.now().strftime('%Y%m%d-%H%M%S'))
    experiment = Experiment(args)
    try:
        experiment.run()
    except KeyboardInterrupt:
        print('Interrupted; summarizing what finished.', file=sys.stderr)
    if not args.dry_run and (Path(args.out) / 'runs.jsonl').exists():
        summarize(args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
