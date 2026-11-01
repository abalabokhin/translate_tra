"""Codex experiment validation and CLI failure handling, without network requests."""
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
import run_codex_translation as runner
from translation_common import merge_dialogue_rows, read_csv


class CodexTranslationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.out = Path(self.temporary.name)

    def fixture(self, name):
        checks = SCRIPTS / 'experiments/fixtures' / name / 'checks.json'
        e = runner.experiment(checks, self.out / name)
        _, refs = read_csv(checks.parent / 'reference.csv', ['Line_ID', 'Russian_Male', 'Russian_Female'])
        by_id = {row['Line_ID']: row for row in refs}
        merged, _ = merge_dialogue_rows(e.rows)
        pairs = {str(i): {'male': by_id[row[1]]['Russian_Male'],
                          'female': by_id[row[1]]['Russian_Female']}
                 for i, row in enumerate(merged[1:], 1)}
        return e, pairs

    def test_original_female_variants_and_empty_sources(self):
        e, pairs = self.fixture('original_female_variants')
        _, user, schema = runner.both_request(e)
        data = json.loads(user)
        self.assertTrue(any(line['english'] != line['english_female'] for line in data['dialogue']))
        empty = [line['id'] for line in data['dialogue'] if not line['english_female']]
        self.assertTrue(empty)
        result = runner.parse_both(e, json.dumps({'translations': pairs}))
        self.assertIn('', result['female'].values())
        self.assertEqual(schema['properties']['translations']['properties'][empty[0]]['properties']['female']['enum'], [''])
        pairs[empty[0]]['female'] = pairs[empty[0]]['male']
        with self.assertRaisesRegex(ValueError, 'empty female'):
            runner.parse_both(e, json.dumps({'translations': pairs}))

    def test_reused_strings_expand_and_prompt_has_no_evaluation_answers(self):
        e, pairs = self.fixture('reused_strings')
        result = runner.parse_both(e, json.dumps({'translations': pairs}))
        merged, slots = merge_dialogue_rows(e.rows)
        self.assertLess(len(merged), len(e.rows))
        for gender in ('male', 'female'):
            for row in e.rows[1:]:
                self.assertEqual(result[gender][row[1]], pairs[str(slots[row[1]])][gender])
        _, user, _ = runner.both_request(e)
        self.assertNotIn('reference.csv', user)
        self.assertNotIn('pair_review', user)
        self.assertEqual(set(json.loads(user)), {'instruction', 'kind', 'actors', 'glossary', 'graph_notes', 'dialogue', 'output'})

    def test_missing_ids_duplicate_keys_and_changed_tokens_reject(self):
        e, pairs = self.fixture('multiple_npcs')
        incomplete = dict(pairs)
        incomplete.pop(next(iter(incomplete)))
        with self.assertRaisesRegex(ValueError, 'IDs'):
            runner.parse_both(e, json.dumps({'translations': incomplete}))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            runner.parse_both(e, '{"translations":{},"translations":{}}')
        for pair in pairs.values():
            if '<CHARNAME>' in pair['female']:
                pair['female'] = pair['female'].replace('<CHARNAME>', '')
                break
        else:
            self.fail('fixture must contain an engine token')
        with self.assertRaisesRegex(ValueError, 'tokens'):
            runner.parse_both(e, json.dumps({'translations': pairs}))

    def test_cli_exit_zero_with_failed_turn_is_not_success(self):
        binary = self.out / 'fake-codex'
        binary.write_text('#!/usr/bin/env python3\nimport sys\nsys.stdin.read()\n'
                          'print(\'{"type":"turn.failed","error":{"message":"quota"}}\')\n')
        binary.chmod(0o755)
        call, content = runner.run_cli(str(binary), 'test', 'rules', '{}', {'type': 'object'}, self.out / 'call')
        self.assertIsNone(content)
        self.assertEqual(call['status'], 'failed')
        self.assertIn('quota', call['error'])
        self.assertEqual(call['returncode'], 0)

    def test_both_modes_with_mock_cli_and_scoring(self):
        for mode in ('both', 'two-pass'):
            e, pairs = self.fixture('ambiguous_addressees')

            def reply(binary, model, system, user, schema, out, dry_run=False):
                out.mkdir(parents=True)
                data = json.loads(user)
                if mode == 'both':
                    values = pairs
                else:
                    gender = 'female' if 'now FEMALE' in data['instruction'] else 'male'
                    values = {line['id']: pairs[line['id']][gender] for line in data['dialogue']}
                return {'status': 'completed'}, json.dumps({'translations': values})

            with patch.object(runner, 'run_cli', side_effect=reply), \
                    patch.object(runner.subprocess, 'check_output', return_value='codex-cli test'), \
                    contextlib.redirect_stdout(io.StringIO()):
                out = self.out / mode
                code = runner.main(['--datasets', 'ambiguous_addressees', '--modes', mode, '--out', str(out)])
            self.assertEqual(code, 0)
            manifest = json.loads((out / 'manifest.json').read_text())
            self.assertEqual(manifest['status'], 'finished')
            self.assertTrue(manifest['runs'][0]['checks'])
            _, rows = read_csv(out / 'outputs.csv', ['Russian_Male', 'Russian_Female'])
            self.assertEqual(len(rows), len(e.rows) - 1)

    def test_dry_run_never_launches_codex_and_refuses_existing_output(self):
        out = self.out / 'prepared'
        with patch.object(runner.subprocess, 'Popen', side_effect=AssertionError('must stay offline')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(['--dry-run', '--out', str(out)]), 0)
        manifest = json.loads((out / 'manifest.json').read_text())
        self.assertEqual(manifest['status'], 'prepared')
        self.assertEqual(manifest['runs'][0]['checks'], [])
        self.assertTrue(list(out.rglob('prompt.txt')))
        with self.assertRaises(FileExistsError):
            runner.main(['--dry-run', '--out', str(out)])


if __name__ == '__main__':
    unittest.main()
