"""Translate + verify runner without Ollama: fix application, planted cases and scoring."""
import argparse
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
import run_translate_verify as runner
from diagnose_translation import Experiment
from translation_common import merge_dialogue_rows, read_csv

FIXTURES = SCRIPTS / 'experiments/fixtures'
MUTATIONS = json.loads(runner.MUTATIONS.read_text(encoding='utf-8'))['fixtures']


def references(name):
    _, rows = read_csv(FIXTURES / name / 'reference.csv', ['Line_ID', 'Russian_Male', 'Russian_Female'])
    return {r['Line_ID']: r for r in rows}


class FakeClient:
    """Verifier that reports every known wrong fragment it sees, proposing the right text.
    fixes: {(column, wrong fragment): replacement}."""
    def __init__(self, fixes=None):
        self.fixes = fixes or {}
        self.requests = []

    def get(self, path, payload=None):
        if path == '/api/show':
            return {'model_info': {'general.architecture': 'x', 'x.context_length': 4096}}
        self.requests.append(payload)
        dialogue = json.loads(payload['messages'][1]['content'])['dialogue']
        issues = [dict(id=line['id'], column=column, category='other', problem=wrong, replacement=line['russian_' + column].replace(wrong, right), reason='')
                  for line in dialogue for (column, wrong), right in self.fixes.items()
                  if wrong in line['russian_' + column]]
        return {'message': {'content': json.dumps({'issues': issues}, ensure_ascii=False), 'thinking': 'x'},
                'done_reason': 'stop', 'eval_count': 7}


class TranslateVerifyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.args = argparse.Namespace(translator='t', verifier='v', verifier_think='on', verifier_num_ctx='native',
                                       verifier_num_predict=100, translator_num_ctx=8192, repeats=1,
                                       url='http://localhost:1')
        gpu = patch.object(Experiment, 'gpu_share', return_value=None)
        gpu.start()
        self.addCleanup(gpu.stop)

    def merged(self, name):
        e = runner.experiment_for(self.args, FIXTURES / name / 'checks.json', self.out / name)
        return e, *merge_dialogue_rows(e.rows)

    def test_every_planted_mutation_applies_and_stays_structurally_valid(self):
        for name, cases in MUTATIONS.items():
            e, merged, slots = self.merged(name)
            refs = references(name)
            male = runner.by_slot(merged, slots, {k: v['Russian_Male'] for k, v in refs.items()})
            female = runner.by_slot(merged, slots, {k: v['Russian_Female'] for k, v in refs.items()})
            for case in cases:
                with self.subTest(fixture=name, case=case['name']):
                    new_male, new_female = runner.mutate(merged, slots, male, female, case['mutations'])
                    changed = sum(male[i] != new_male[i] for i in male) + sum(female[i] != new_female[i] for i in female)
                    self.assertEqual(changed, len(case['mutations']))
                    self.assertIn(case['mutations'][0]['category'], runner.CATEGORIES)

    def test_complete_lines_apply_with_agreement_and_preserve_structural_checks(self):
        e, merged, slots = self.merged('original_female_variants')
        refs = references('original_female_variants')
        male = runner.by_slot(merged, slots, {k: v['Russian_Male'] for k, v in refs.items()})
        female = runner.by_slot(merged, slots, {k: v['Russian_Female'] for k, v in refs.items()})
        issue = dict(category='other', reason='')
        issues = [dict(issue, id='1', column='female', problem='Incorrect agreement',
                       replacement='Я была её ученицей.'),
                  dict(issue, id='4', column='female', problem='Missing text', replacement='Дверь открыта.'),
                  dict(issue, id='4', column='male', problem='Quotes', replacement='Дверь "открыта".'),
                  dict(issue, id='5', column='male', problem='Wording', replacement='Я подожду тут.'),
                  dict(issue, id='99', column='male', problem='Unknown', replacement='Текст.')]
        female['1'] = 'Я был её учеником.'
        new_male, new_female, decisions = runner.apply_issues(merged, male, female, issues)
        outcomes = [d['outcome'] for d in decisions]
        self.assertEqual(outcomes[0], {'female': 'applied'})
        self.assertTrue(outcomes[1]['female'].startswith('rejected: source is empty'))
        self.assertIn('quotation', outcomes[2]['male'])
        self.assertEqual(outcomes[3], {'male': 'applied'})
        self.assertIn('unknown', outcomes[4]['male'])
        self.assertEqual(new_female['1'], 'Я была её ученицей.')
        self.assertEqual(new_female['4'], '')
        self.assertEqual((new_male['5'], new_female['5']), ('Я подожду тут.', 'Я подожду здесь.'))
        self.assertEqual(new_male['4'], male['4'])

    def test_complete_line_cannot_drop_engine_tokens_and_duplicate_cells_reject(self):
        e, merged, slots = self.merged('multiple_npcs')
        refs = references('multiple_npcs')
        male = runner.by_slot(merged, slots, {k: v['Russian_Male'] for k, v in refs.items()})
        female = runner.by_slot(merged, slots, {k: v['Russian_Female'] for k, v in refs.items()})
        issue = dict(id='1', column='female', category='player_gender', problem='Gender',
                     replacement='Ты вернулась. Орин ждал внизу.', reason='')
        _, corrected, decisions = runner.apply_issues(merged, male, female, [issue])
        self.assertEqual(corrected, female)
        self.assertTrue(decisions[0]['outcome']['female'].startswith('rejected:'))
        with self.assertRaisesRegex(ValueError, 'at most one'):
            runner.parse_issues(json.dumps({'issues': [issue, issue]}))
        with self.assertRaisesRegex(ValueError, 'column'):
            runner.parse_issues(json.dumps({'issues': [dict(issue, column='both')]}))

    def test_native_translator_context_and_uncapped_generation_are_defaults(self):
        import run_prompt_ab
        for module in (runner, run_prompt_ab):
            with patch.object(sys, 'argv', ['runner', '--dry-run']), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 0)
        self.args.translator_num_ctx = 'native'
        e, _, _ = self.merged('multiple_npcs')
        with patch.object(Experiment, 'post', return_value={
                'model_info': {'general.architecture': 'x', 'x.context_length': 131072}}):
            self.assertEqual(e.context_for('t'), 131072)

    def test_verifier_request_has_both_columns_female_source_and_no_references(self):
        e, merged, slots = self.merged('original_female_variants')
        refs = references('original_female_variants')
        male = runner.by_slot(merged, slots, {k: v['Russian_Male'] for k, v in refs.items()})
        female = runner.by_slot(merged, slots, {k: v['Russian_Female'] for k, v in refs.items()})
        request = json.loads(runner.verify_request(e, merged, male, female))
        lines = request['dialogue']
        self.assertEqual(lines[1]['english_female'], 'The duchess sent you to retrieve her seal.')
        self.assertEqual(lines[3]['english_female'], '')
        self.assertNotIn('english_female', lines[4])
        self.assertEqual(lines[0]['speaker_gender'], 'male in russian_male, female in russian_female')
        self.assertEqual(lines[1]['speaker_gender'], 'female; apothecary')
        self.assertNotIn('Review_Notes', json.dumps(request))

    def test_planted_stage_measures_flags_restores_and_clean_false_alarms(self):
        name = 'multiple_npcs'
        fixes = {(m['column'], m['to']): m['from'] for case in MUTATIONS[name] for m in case['mutations']}
        client = FakeClient(fixes)
        with contextlib.redirect_stdout(io.StringIO()):
            results = runner.planted(self.args, client, self.out, name, FIXTURES / name / 'checks.json')
        self.assertEqual(len(results), 1 + len(MUTATIONS[name]))
        clean = results[0]
        self.assertEqual((clean['issues'], clean['collateral_changes'], clean['checks_failed_after']), (0, 0, 0))
        for entry in results[1:]:
            for m in entry['mutations']:
                self.assertTrue(m['flagged'] and m['restored_exact'], (entry['case'], m))
        self.assertEqual(client.requests[0]['options'], {'num_ctx': 4096, 'num_predict': 100})
        self.assertTrue(client.requests[0]['think'])
        self.assertTrue((self.out / 'planted' / name / 'verifier.jsonl').exists())

    def test_translate_verify_scores_before_and_after_and_skips_failed_translation(self):
        name = 'multiple_npcs'
        refs = references(name)
        wrong = dict(refs['105'], Russian_Female='Ты спас её, путник. Я обязан тебе жизнью.')

        def chat(config, system, user, schema):
            female = 'male_translation' in user
            values = {line['id']: (wrong if line['english'].startswith('You saved') else
                                   next(r for r in refs.values() if r['Line_ID'] == ids[line['id']]))
                      ['Russian_Female' if female else 'Russian_Male'] for line in json.loads(user)['dialogue']}
            return None, {'wall_seconds': 1, 'message': {'content': json.dumps({'translations': values})}}
        e, merged, _ = self.merged(name)
        ids = {str(i): row[1] for i, row in enumerate(merged[1:], 1)}
        client = FakeClient({('female', 'Ты спас её, путник'): 'Ты спасла её, путница'})
        with contextlib.redirect_stdout(io.StringIO()), patch.object(Experiment, 'chat', side_effect=chat):
            [result] = runner.translate_verify(self.args, client, self.out, name, FIXTURES / name / 'checks.json', 'off')
        self.assertEqual(result['checks_after'], result['expected_checks'])
        self.assertGreater(result['checks_fixed'], 0)
        self.assertEqual((result['checks_broken'], result['applied'], result['lines_changed']), (0, 1, 1))
        _, table = read_csv(self.out / 'translate-verify' / name / 'before_after.csv', ['Line_ID', 'verified'])
        self.assertEqual(len(table), 12)

        failed = self.out / 'second'
        with contextlib.redirect_stdout(io.StringIO()), patch.object(
                Experiment, 'chat', return_value=(None, {'wall_seconds': 1, 'error': 'offline'})):
            [result] = runner.translate_verify(self.args, FakeClient(), failed, name, FIXTURES / name / 'checks.json', 'off')
        self.assertIn('skipped', result)

    def test_real_fixture_skeleton_loads_scores_every_line_and_needs_a_complete_reference(self):
        import make_real_fixture
        from translation_common import write_csv
        source = FIXTURES / 'original_female_variants'
        folder = make_real_fixture.make(source / 'input.csv', FIXTURES / 'actors.csv', 'demo', 'test mod 1.0',
                                        root=self.out / 'real_set')
        with self.assertRaises(ValueError):
            make_real_fixture.make(source / 'input.csv', FIXTURES / 'actors.csv', 'demo', 'x', root=self.out / 'real_set')
        e = runner.experiment_for(self.args, folder / 'checks.json', self.out / 'run')
        self.assertEqual(e.scopes('full')[0][1], {'401', '402', '403', '404', '405'})
        _, refs = read_csv(folder / 'reference.csv', make_real_fixture.REFERENCE_COLUMNS)
        self.assertEqual(refs[1]['English_Female'], 'The duchess sent you to retrieve her seal.')
        self.assertEqual(refs[4]['English_Female'], '')
        self.assertFalse(runner.reference_complete(folder / 'checks.json'))
        filled = references('original_female_variants')
        for r in refs:
            r['Russian_Male'] = filled[r['Line_ID']]['Russian_Male']
        write_csv(folder / 'reference.csv', make_real_fixture.REFERENCE_COLUMNS, refs)
        self.assertFalse(runner.reference_complete(folder / 'checks.json'))
        for r in refs:
            r.update(Russian_Male=filled[r['Line_ID']]['Russian_Male'], Russian_Female=filled[r['Line_ID']]['Russian_Female'])
        write_csv(folder / 'reference.csv', make_real_fixture.REFERENCE_COLUMNS, refs)
        self.assertTrue(runner.reference_complete(folder / 'checks.json'))
        with patch.object(runner, 'SCRIPT_DIR', self.out):
            self.assertEqual(runner.datasets(['demo']), [('demo', folder / 'checks.json')])

    def test_report_renders_both_stages(self):
        manifest = dict(status='finished', started_utc='s', finished_utc='f',
                        settings=dict(translator='t', translator_think='default', translator_num_ctx=8192, verifier='v',
                                      verifier_think='on', verifier_num_ctx='native', verifier_num_predict=1, repeats=1),
                        translate_verify=[dict(dataset='d', repeat=1, expected_checks=10, verifier_error=None,
                                               verifier_seconds=1.0, checks_before=8, checks_after=9, checks_fixed=1,
                                               checks_broken=0, issues=2, applied=1, lines_changed=1),
                                          dict(dataset='d', repeat=2, expected_checks=10, skipped='translation failed')],
                        planted=[dict(dataset='d', case='clean reference', verifier_error=None, issues=1,
                                      collateral_changes=1, checks_failed_after=0, mutations=[]),
                                 dict(dataset='d', case='c', verifier_error=None, issues=1, collateral_changes=0,
                                      checks_failed_after=0, mutations=[dict(category='meaning', flagged=True,
                                                                             restored_exact=False, wrong_text_removed=True)])])
        runner.report(self.out, manifest)
        text = (self.out / 'REPORT.md').read_text(encoding='utf-8')
        self.assertIn('| d | 1/2 | 8/10 | 9/10 | 1 | 0 | 2 | 1 | 1 | 1.0 |', text)
        self.assertIn('| d | 1/1 | 0/1 | 1/1 | 1 | 1 | 0 | 0 | 0/2 |', text)
        self.assertIn('| meaning | 1/1 |', text)


if __name__ == '__main__':
    unittest.main()
