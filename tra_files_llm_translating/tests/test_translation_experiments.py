"""Diagnostic scoring regressions; no running Ollama or model downloads."""

import argparse
import copy
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS / 'experiments'))
from diagnose_translation import Experiment, summarize, PROMPTS
from run_all import rate, select_settings
from translation_common import merge_dialogue_rows, read_csv, validate_text


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        args = argparse.Namespace(
            checks=str(SCRIPTS / 'experiments/inkgallery_checks.json'), actors=None,
            dictionary=str(SCRIPTS / 'dict.csv'), out=str(self.out),
            url='http://localhost:11434', num_ctx='8192', seed=None, dry_run=False,
            models=['mock'], prompts=['production'], scopes=['full'],
            think=['off'], temperatures=['default'], repeats=1)
        self.experiment = Experiment(args)

    def records(self):
        return [json.loads(line) for line in (self.out / 'runs.jsonl').read_text().splitlines()]

    def run_with(self, replies):
        with contextlib.redirect_stdout(io.StringIO()), patch.object(
                self.experiment, 'chat', side_effect=replies) as call:
            self.experiment.run()
            summarize(self.out)
        return call.call_count, self.records()

    def test_scopes_score_same_lines_and_checks(self):
        full = self.experiment.scopes('full')
        pairs = self.experiment.scopes('pair')
        full_targets = full[0][1]
        self.assertEqual(full_targets, {target for _, targets in pairs for target in targets})
        self.assertEqual(len(full[0][0]), 12)  # Full context remains available.
        self.assertEqual(len(full_targets), 12)
        for gender in ('male', 'female'):
            def checks(scopes):
                return sorted((c['line'], c['gender'], c['check'])
                              for _, targets in scopes for target in targets
                              for c in self.experiment.score(target, gender, None))
            self.assertEqual(checks(full), checks(pairs))

    def test_failed_male_penalizes_both_passes_without_extra_request(self):
        count, records = self.run_with([(None, {'error': 'offline', 'wall_seconds': 1})])
        self.assertEqual(count, 1)
        self.assertEqual([r['gender'] for r in records], ['male', 'female'])
        self.assertTrue(records[1]['skipped'])
        for record in records:
            self.assertTrue(record['checks'])
            self.assertFalse(any(c['ok'] for c in record['checks']))
        totals = rate(records, 'prompt')[('production',)]
        self.assertEqual(totals['requests'], 1)
        self.assertEqual(totals['errors'], 1)

    def test_failed_female_retains_male_checks_and_fails_female_checks(self):
        values = {str(i): row[3] for i, row in enumerate(self.experiment.rows[1:], 1)}
        male = {'message': {'content': json.dumps({'translations': values})}, 'wall_seconds': 1}
        count, records = self.run_with([(None, male), (None, {'error': 'offline', 'wall_seconds': 1})])
        self.assertEqual(count, 2)
        self.assertTrue(any(c['ok'] for c in records[0]['checks']))
        self.assertFalse(any(c['ok'] for c in records[1]['checks']))
        self.assertEqual(len(records[1]['checks']), sum(
            len(self.experiment.score(target, 'female', None)) for target in records[1]['targets']))

    def test_failed_markup_penalizes_both_genders_but_counts_one_request(self):
        self.experiment.args.prompts = ['markup']
        count, records = self.run_with([(None, {'error': 'offline', 'wall_seconds': 1})])
        self.assertEqual(count, 1)
        self.assertFalse(any(c['ok'] for r in records for c in r['checks']))
        totals = rate(records, 'prompt')[('markup',)]
        self.assertEqual(totals['requests'], 1)
        self.assertEqual(totals['errors'], 1)

    def test_selection_uses_joint_full_configuration_and_penalizes_failures(self):
        def record(prompt, temp, passed, scope='full'):
            return dict(config=dict(prompt=prompt, temperature=temp, scope=scope),
                        checks=[{'ok': i < passed} for i in range(10)],
                        error=None if passed else 'offline', wall_seconds=1, eval_count=1)
        records = [record('production', 'default', 9), record('production', '0.2', 1),
                   record('examples', 'default', 0), record('examples', '0.2', 8),
                   record('reframed-addressee', '0.2', 10), record('markup', '0.2', 10, 'pair'),
                   record('markup', 'default', 10), record('markup', 'default', 0),
                   record('markup', 'default', 0)]
        self.assertEqual(select_settings(records), ('production', 'default'))
        # Tie preferences hold even when records arrive in a different order.
        tied = [record('examples', '0.2', 9), record('production', '0.2', 9), records[0]]
        self.assertEqual(select_settings(tied), ('production', 'default'))
        interacting = [record('production', 'default', 9), record('production', '0.2', 8),
                       record('examples', 'default', 0), record('examples', '0.2', 10)]
        self.assertEqual(select_settings(interacting), ('examples', '0.2'))

    def fixture(self, name):
        args = copy.copy(self.experiment.args)
        args.checks = str(SCRIPTS / 'experiments/fixtures' / name / 'checks.json')
        return Experiment(args)

    def test_latin_check_ignores_engine_tokens_and_explicit_names(self):
        def latin_ok(text):
            return next(c['ok'] for c in self.experiment.score('@48', 'male', text)
                        if c['check'] == 'no untranslated Latin text outside engine tokens')
        self.assertFalse(latin_ok('Поговорим downstairs.'))
        self.assertTrue(latin_ok('Привет, <CHARNAME>! %gate_lock% %s \\n ^R'))
        self.assertTrue(latin_ok('Жду здесь.'))
        self.experiment.checks['allowed_latin'] = ['Boo']
        self.assertTrue(latin_ok('Boo ждёт.'))
        self.assertFalse(latin_ok('Book ждёт.'))

    def test_inkgallery_names_and_idiom_accept_variants_but_reject_pilot_errors(self):
        def named(lid, text, name):
            return next(c['ok'] for c in self.experiment.score(lid, 'male', text) if c['check'] == name)
        for text in ('Галерея Чернил', 'Чернильной галереи', 'галерею туши'):
            self.assertTrue(named('@16', text, 'Ink Gallery name retains ink and gallery'))
        for text in ('Талая Галерея', 'Галерея Травы', 'Галерея Инка'):
            self.assertFalse(named('@16', text, 'Ink Gallery name retains ink and gallery'))
        for text in ('как у меня дела', 'как я поживаю', 'как я себя чувствую', 'как я справляюсь'):
            self.assertTrue(named('@48', text, 'idiom: how I\'m doing'), text)
        self.assertFalse(named('@48', 'как я делаю', 'idiom: how I\'m doing'))
        self.assertFalse(named('@48', 'Поговорим на кухне.', 'downstairs not an invented kitchen'))

    def test_pair_review_distinguishes_gender_edits_rewrites_and_missing_outputs(self):
        e = self.experiment
        row = next(r for r in e.rows[1:] if r[1] == '@100')
        male = {'@100': 'Привет! Ты видел книги и пришёл за сувенирами.'}
        female = {'@100': 'Привет! Ты видела книги и пришла за сувенирами.'}
        self.assertEqual(e.review_pairs([row], {'@100'}, male, female)[0]['status'], 'pass')
        female['@100'] = 'Здравствуй! Ты видела книги и пришла за сувенирами.'
        self.assertEqual(e.review_pairs([row], {'@100'}, male, female)[0]['status'], 'review')
        self.assertEqual(e.review_pairs([row], {'@100'}, None, female)[0]['status'], 'missing')
        # Equality is not proof of correct agreement: gender checks remain independent.
        self.assertEqual(e.review_pairs([row], {'@100'}, male, male)[0]['status'], 'pass')
        self.assertFalse(next(c['ok'] for c in e.score('@100', 'female', male['@100'])
                              if c['check'] == 'видел for female Player1'))

    def test_all_fixture_references_pass_checks_and_structural_validation(self):
        for path in sorted((SCRIPTS / 'experiments/fixtures').glob('*/checks.json')):
            with self.subTest(fixture=path.parent.name):
                e = self.fixture(path.parent.name)
                _, refs = read_csv(path.parent / 'reference.csv', ['Line_ID', 'Russian_Male', 'Russian_Female'])
                by_id = {r['Line_ID']: r for r in refs}
                self.assertEqual(set(by_id), {row[1] for row in e.rows[1:]})
                for row in e.rows[1:]:
                    self.assertTrue(set(filter(None, row[2].split(';'))) <= set(by_id))
                male, female = {}, {}
                for row in e.rows[1:]:
                    for gender, field in [('male', 'Russian_Male'), ('female', 'Russian_Female')]:
                        text = by_id[row[1]][field]
                        source = dict(zip(e.header, row))
                        english = row[3] if gender == 'male' or not source['Source_Has_Female'] else source['Source_Female_Text']
                        validate_text(english, text)
                        self.assertTrue(all(c['ok'] for c in e.score(row[1], gender, text)), (row[1], gender))
                    male[row[1]], female[row[1]] = by_id[row[1]]['Russian_Male'], by_id[row[1]]['Russian_Female']
                reviews = e.review_pairs(e.rows[1:], set(by_id), male, female)
                self.assertTrue(all(r['status'] in ('pass', 'not_applicable') for r in reviews), reviews)

    def test_v3_checks_match_observed_errors_and_accept_observed_valid_wording(self):
        """Cases taken from the manual reviews of the 2026-10-28 runs."""
        cases = [  # fixture, line, gender, text, expected all-ok
            ('multiple_npcs', '105', 'female', 'Ты спасла её, путник. Я обязан тебе жизнью.', False),
            ('multiple_npcs', '105', 'female', 'Ты спас её, путница. Я обязан тебе жизнью.', False),
            ('multiple_npcs', '102', 'female', 'Селена, ты была права. Я слишком поспешил обвинить её.', False),
            ('multiple_npcs', '103', 'female', 'Я пообещала Селене помочь ей. Орин должен перед ней извиниться.', True),
            ('multiple_npcs', '104', 'male', 'Орин, тебя не ранило? Я тревожилась за тебя.', True),
            ('multiple_npcs', '101', 'male', 'Ты вернулся, <CHARNAME>. Орин ждал этажом ниже.', True),
            ('ambiguous_addressees', '201', 'male', 'Проводник пропал. Брэм и Селена на другом берегу.', False),
            ('ambiguous_addressees', '201', 'male', 'Перевозчик пропал. Брэм и Селена на другом берегу.', True),
            ('ambiguous_addressees', '204', 'male', 'Поток слишком сильное.', False),
            ('ambiguous_addressees', '204', 'male', 'Поток слишком сильный.', True),
            ('ambiguous_addressees', '205', 'male', 'Ты должен оставаться на том берегу, пока верёвка не закреплена.', False),
            ('ambiguous_addressees', '205', 'male', 'Оставайся на том берегу, пока верёвка надёжно закреплена.', False),
            ('original_female_variants', '403', 'male', 'Я привёл серебряный ключ.', False),
            ('original_female_variants', '403', 'female', 'Я принёсла бронзовый ключ.', False),
            ('original_female_variants', '401', 'female', 'Я был её учеником.', False),
            ('reused_strings', '301_a', 'female', 'Я готова.', True),
            ('reused_strings', '301_a', 'female', 'Я готов.', False),
            ('reused_strings', '301_a', 'male', 'Я готова.', False),
        ]
        for fixture, line, gender, text, expected in cases:
            with self.subTest(fixture=fixture, line=line, text=text):
                checks = self.fixture(fixture).score(line, gender, text)
                self.assertEqual(all(c['ok'] for c in checks), expected, checks)
        ink = self.experiment.score('@16', 'female', 'Снова здравствуй, приключенец. Галерея Чернил приветствует тебя.')
        self.assertFalse(all(c['ok'] for c in ink))

    def test_noun_rule_variant_changes_only_the_female_instruction(self):
        from diagnose_translation import FEMALE_NOUN_RULE
        rows = self.experiment.rows[1:]
        male = {str(i): 'текст' for i, _ in enumerate(rows, 1)}
        for gender, previous in (('male', None), ('female', male)):
            base = json.loads(self.experiment.build('production', rows, gender, previous)[1])
            variant = json.loads(self.experiment.build('production-nouns', rows, gender, previous)[1])
            if gender == 'male':
                self.assertEqual(base, variant)
            else:
                self.assertEqual(variant['instruction'], base['instruction'] + ' ' + FEMALE_NOUN_RULE)
                self.assertEqual({k: v for k, v in variant.items() if k != 'instruction'},
                                 {k: v for k, v in base.items() if k != 'instruction'})

    def test_rescore_applies_current_checks_and_keeps_rejected_replies_failed(self):
        import rescore
        folder = self.out / 'batch' / '05' / 'multiple_npcs'
        folder.mkdir(parents=True)
        config = dict(model='m', prompt='production', scope='full', think='off', temperature='default', repeat=1)
        valid = 'Я пообещала Селене помочь ей. Орин должен перед ней извиниться.'
        records = [dict(config=config, gender='female', targets=['103'], error=None, translations={'103': valid},
                        checks=[{'ok': False}, {'ok': True}], evaluation_version='multiple_npcs-v1'),
                   dict(config=config, gender='female', targets=['103'], error='structural: x', translations={},
                        checks=[{'ok': False}, {'ok': False}], evaluation_version='multiple_npcs-v1')]
        (folder / 'runs.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records),
                                           encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            rescore.rescore(self.out / 'batch')
        _, [row] = read_csv(self.out / 'batch' / 'rescored.csv', ['new_ok'])
        expected = len(self.fixture('multiple_npcs').score('103', 'female', valid))
        self.assertEqual((row['old_ok'], row['old_expected'], row['new_version']), ('1', '4', 'multiple_npcs-v2'))
        self.assertEqual((row['new_ok'], row['new_expected']), (str(expected), str(2 * expected)))

    def test_all_prompt_variants_use_original_female_source_and_merge_references(self):
        e = self.fixture('original_female_variants')
        rows = e.rows[1:]
        male = {str(i): 'текст' for i, _ in enumerate(rows, 1)}
        for prompt in PROMPTS:
            with self.subTest(prompt=prompt):
                gender = 'both' if prompt == 'markup' else 'female'
                _, user = e.build(prompt, rows, gender, None if prompt == 'markup' else male)
                dialogue = json.loads(user)['dialogue']
                field = 'female_english' if prompt == 'markup' else 'english'
                self.assertEqual(dialogue[1][field], 'The duchess sent you to retrieve her seal.')
                if prompt == 'markup':
                    self.assertEqual(dialogue[3][field], '')
                else:  # The explicitly empty female line is left empty without a request.
                    self.assertEqual([line['id'] for line in dialogue], ['1', '2', '3', '5'])
        e = self.fixture('reused_strings')
        merged, slots = merge_dialogue_rows(e.rows)
        self.assertEqual(len(merged) - 1, 4)
        self.assertEqual(slots['301_a'], slots['301_b'])
        self.assertEqual(merged[1][e.header.index('Addressee')], '')
        for prompt in PROMPTS:
            _, user = e.build(prompt, e.rows[1:], 'male')
            dialogue = json.loads(user)['dialogue']
            self.assertEqual(len(dialogue), 4)
            self.assertEqual(dialogue[0]['speaker'], ['Selene', 'Player1'])
        record = {'translations': {}, 'error': None}
        values = {str(i): row[3] for i, row in enumerate(merged[1:], 1)}
        e.parse(record, json.dumps({'translations': values}), e.rows[1:], 'male')
        self.assertIsNone(record['error'])
        self.assertEqual(len(record['translations']), 6)
        self.assertEqual(record['translations']['301_a'], record['translations']['301_b'])

    def test_reference_replies_round_trip_all_fixtures_prompts_and_scopes(self):
        for path in sorted((SCRIPTS / 'experiments/fixtures').glob('*/checks.json')):
            with self.subTest(fixture=path.parent.name):
                e = self.fixture(path.parent.name)
                e.args.out = str(self.out / path.parent.name)
                e.out = Path(e.args.out)
                e.out.mkdir()
                e.args.prompts = list(PROMPTS)
                e.args.scopes = ['full', 'pair']
                e.prod.dictionary = {}  # References test evaluation, not glossary selection.
                _, references = read_csv(path.parent / 'reference.csv', ['Line_ID'])
                references = {r['Line_ID']: r for r in references}
                by_english = {}
                for row in e.rows[1:]:
                    by_english[row[3]] = references[row[1]]
                    source = dict(zip(e.header, row))
                    if source['Source_Has_Female']:
                        by_english[source['Source_Female_Text']] = references[row[1]]
                counts = {}
                def reply(config, system, user, schema):
                    self.assertNotIn('Review_Notes', user)
                    self.assertNotIn('allowed_changes', user)
                    key = tuple(config.values())
                    count = counts.get(key, 0)
                    counts[key] = count + 1
                    gender = 'male' if count % 2 == 0 else 'female'
                    values = {}
                    for line in json.loads(user)['dialogue']:
                        ref = by_english[line['english']]
                        m, f = ref['Russian_Male'], ref['Russian_Female']
                        if config['prompt'] == 'markup':
                            text = m if m == f else '{' + m + '|' + f + '}'
                        else:
                            text = ref['Russian_' + gender.capitalize()]
                        values[line['id']] = text
                    self.assertEqual(set(values), set(schema['properties']['translations']['properties']))
                    return None, {'wall_seconds': 1, 'message': {'content': json.dumps({'translations': values})}}
                with contextlib.redirect_stdout(io.StringIO()), patch.object(e, 'chat', side_effect=reply):
                    e.run()
                    summarize(e.out)
                records = [json.loads(line) for line in (e.out / 'runs.jsonl').read_text().splitlines()]
                self.assertTrue(all(not r['error'] for r in records))
                self.assertTrue(all(c['ok'] for r in records for c in r['checks']))
                self.assertTrue(all(v['status'] in ('pass', 'not_applicable')
                                    for r in records for v in r.get('pair_reviews', [])))
                self.assertTrue((e.out / 'pair_reviews.csv').exists())


if __name__ == '__main__':
    unittest.main()
