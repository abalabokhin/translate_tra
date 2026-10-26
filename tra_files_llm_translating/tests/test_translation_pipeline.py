"""Synthetic regressions: no model downloads or running Ollama required."""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from translate_dialogs import DialogTranslator, TRANSLATION_RULES
from translation_common import (DIALOGUE_COLUMNS, TRANSLATION_COLUMNS, read_csv,
                                validate_text, write_csv)
from tra_format import parse_tra, replace_entry
from update_tra_from_csv import TraUpdater


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'english'
        self.target = self.root / 'russian'
        self.tra = self.root / 'tra'
        self.output = self.root / 'output'
        for path in (self.source, self.target, self.tra):
            path.mkdir()
        self.actors = self.root / 'actors.csv'
        self.actors.write_text('NPC,FEMALE\n', encoding='utf-8')
        self.dictionary = self.root / 'dict.csv'
        self.dictionary.write_text('Icewind Dale,Долина Ледяного Ветра\nIcewind,Айсвинд\n', encoding='utf-8')
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)


    def dialogue(self, rows=None, name='dialogue.csv'):
        if rows is None:
            rows = [['NPC', '1', '', 'You returned, <PLAYER1>!', '@1', 'TRA:TEST.tra:@1'],
                    ['Player1', '2', '1', 'I said "hello", then left.\nAnother line.', '@2', 'TRA:TEST.tra:@2']]
        data = [dict(zip(DIALOGUE_COLUMNS, row)) for row in rows]
        path = self.source / name
        write_csv(path, DIALOGUE_COLUMNS, data)
        return path


    def test_npc_only_also_gets_both_genders(self):
        self.dialogue([['NPC', '1', '', 'You returned!', '@1', 'TRA:test.tra:@1']])
        translator = self.translator(test_mode=True)
        self.assertTrue(translator.translate_all_dialogs())
        _, result = read_csv(self.target / 'dialogue.csv', TRANSLATION_COLUMNS)
        self.assertEqual(len(result), 1)


    def test_unused_lines_multiline_and_gendered_export(self):
        write_csv(self.source / '_unused_tra_lines.csv', ['Reference', 'Text'],
                  [{'Reference': 'test.tra:@1', 'Text': 'Hello | "friend"\n<PLAYER1>'}])
        translator = self.translator(test_mode=True)
        self.assertTrue(translator.translate_all_dialogs())
        _, rows = read_csv(self.target / '_unused_tra_lines.csv', TRANSLATION_COLUMNS)
        self.assertEqual(rows[0]['Russian_Male'], 'Hello | "friend"\n<PLAYER1>')


    def test_empty_source_female_variant_survives(self):
        path = self.source / 'dialogue.csv'
        row = dict(zip(DIALOGUE_COLUMNS, ['NPC', '1', '', 'Hello', '@1', 'TRA:test.tra:@1']))
        row.update(Source_Female_Text='', Source_Has_Female='1')
        write_csv(path, DIALOGUE_COLUMNS + ['Source_Female_Text', 'Source_Has_Female'], [row])
        self.assertTrue(self.translator(test_mode=True).translate_all_dialogs())
        (self.tra / 'test.tra').write_text('@1 = ~Hello~ ~~\n')
        updater = TraUpdater(self.tra, self.target, self.output)
        updater.load_translations_from_csvs()
        updater.update_all_tra_files()
        self.assertEqual((self.output / 'test.tra').read_text(), '@1 = ~Hello~ ~~\n')


    def test_cli_mock_from_another_working_directory(self):
        self.dialogue()
        result = subprocess.run([sys.executable, str(SCRIPTS / 'translate_dialogs.py'),
                                 str(self.source), '--target', str(self.target), '--test',
                                 '--url', 'http://localhost:11434'],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.target / 'dialogue.csv').exists())


    def test_different_source_for_same_reference_is_rejected(self):
        self.dialogue([['NPC', '1', '', 'Hello', '@1', 'TRA:test.tra:@1'],
                       ['NPC', '2', '', 'Goodbye', '@1', 'TRA:test.tra:@1']])
        translator = self.translator(test_mode=True)
        self.assertFalse(translator.translate_all_dialogs())
        self.assertFalse((self.target / 'dialogue.csv').exists())


    def test_original_female_sound_and_quote_delimiter_survive_import(self):
        (self.tra / 'test.tra').write_text('@1  =  "Old male" [M] /* keep */ "Old female" [F]\n')
        row = dict(zip(DIALOGUE_COLUMNS, ['NPC', '1', '', 'Old male', '@1', 'TRA:test.tra:@1']))
        row.update(Source_Female_Text='Old female', Russian_Male='Новый', Russian_Female='Новая')
        write_csv(self.target / 'dialogue.csv', DIALOGUE_COLUMNS + ['Source_Female_Text'] + TRANSLATION_COLUMNS, [row])
        updater = TraUpdater(self.tra, self.target, self.output)
        updater.load_translations_from_csvs()
        updater.update_all_tra_files()
        self.assertEqual((self.output / 'test.tra').read_text(),
                         '@1  =  "Новый" [M] /* keep */ "Новая" [F]\n')


    def test_grammar_keeps_reply_specific_edges(self):
        d_folder = self.root / 'd'
        d_folder.mkdir()
        (d_folder / 'test.d').write_text('BEGIN ~NPC~\n'
            'IF ~~ THEN BEGIN start\nSAY @1\n++ @2 GOTO accepted\n++ @3 EXIT\nEND\n'
            'IF ~~ THEN BEGIN accepted\nSAY @4\nIF ~~ THEN EXIT\nEND\n')
        (self.tra / 'test.tra').write_text('@1=~Question~\n@2=~Yes~\n@3=~No~\n@4=~Thanks~\n')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'parse_d_grammar.py'),
                                 str(d_folder), str(self.tra), str(self.source)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        all_rows = []
        for path in self.source.glob('*.csv'):
            all_rows.extend(read_csv(path, DIALOGUE_COLUMNS)[1])
        by_ref = {r['TRA_Reference']: r for r in all_rows}
        self.assertEqual(by_ref['@4']['Predecessors'], by_ref['@2']['Line_ID'])


    def test_malformed_d_file_stops_extraction(self):
        d_folder = self.root / 'd'
        d_folder.mkdir()
        (d_folder / 'test.d').write_text('BEGIN ~NPC~\nIF ~~ THEN BEGIN start\nSAY @99\n')
        (self.tra / 'test.tra').write_text('@1=~Unused~\n')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'parse_d_grammar.py'),
                                 str(d_folder), str(self.tra), str(self.source)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(list(self.source.glob('*.csv')))


    def test_tra_comments_delimiters_sounds_gender_pairs_and_concatenation(self):
        content = ('// @99 = ~not an entry~\r\n/* outer /* nested */ @98 = ~fake~ */\r\n'
                   '@1  =  ~Old male~ [MALE] /* keep */ ~Old female~ [FEMALE] // tail\r\n'
                   '@2 = "He said hello"\r\n@3 = ~~~~~Has ~ and " and %~~~~~\r\n'
                   '@4 = ~Part~ /* concatenate */ ^ ~ two~\r\n')
        entries = parse_tra(content)
        self.assertEqual(set(entries), {1, 2, 3, 4})
        self.assertEqual(entries[4].variants[0].text, 'Part two')
        updated = replace_entry(content, entries[1], 'Новый', 'Новая')
        self.assertIn('@1  =  ~Новый~ [MALE] /* keep */ ~Новая~ [FEMALE] // tail\r\n', updated)
        self.assertNotIn('Old female', updated)
        entry2 = parse_tra(updated)[2]
        updated = replace_entry(updated, entry2, 'Он сказал "привет"', 'Она сказала "привет"')
        self.assertEqual(parse_tra(updated)[2].variants[1].text, 'Она сказала "привет"')
        updated = replace_entry(updated, parse_tra(updated)[4], 'Часть два', 'Часть два')
        self.assertIn('/* concatenate */ ^ ~~', updated)
        self.assertEqual(parse_tra(updated)[4].variants[0].text, 'Часть два')


    def test_conflicts_rejected_before_writing_and_failed_unused_retained(self):
        updater = TraUpdater(self.tra, self.target, self.output)
        updater._register('test.tra:@1', 'Один', 'Одна', 'first')
        with self.assertRaisesRegex(ValueError, 'Conflicting translations'):
            updater._register('TEST.TRA:@1', 'Другой', 'Другая', 'second')
        (self.tra / 'test.tra').write_text('@1 = ~One~\n@2 = ~Other~\n')
        updater._register('test.tra:@2', '', '', 'invalid')
        with self.assertRaises(ValueError):
            updater.update_all_tra_files()
        self.assertFalse(self.output.exists())
        write_csv(self.target / '_unused_tra_lines.csv', ['Reference', 'English_Text', 'Russian_Text'],
                  [{'Reference': 'test.tra:@1', 'English_Text': 'One', 'Russian_Text': ''}])
        updater = TraUpdater(self.tra, self.target, self.output)
        updater.load_translations_from_csvs()
        updater.update_all_tra_files()
        self.assertEqual((self.output / 'test.tra').read_text(), '@1 = ~One~\n@2 = ~Other~\n')


    def test_legacy_gender_pairs_require_matching_ids(self):
        male = dict(zip(DIALOGUE_COLUMNS, ['NPC', '1', '', 'Один', '@1', 'TRA:test.tra:@1']))
        female = dict(male, Dialogue_Text='Одна')
        write_csv(self.target / 'dialogue_male.csv', DIALOGUE_COLUMNS, [male])
        write_csv(self.target / 'dialogue_female.csv', DIALOGUE_COLUMNS, [female])
        updater = TraUpdater(self.tra, self.target)
        updater.load_translations_from_csvs()
        self.assertEqual(updater.translations['test.tra'][1], {'male': 'Один', 'female': 'Одна'})
        write_csv(self.target / 'dialogue_female.csv', DIALOGUE_COLUMNS, [dict(female, Line_ID='2')])
        with self.assertRaises(ValueError):
            TraUpdater(self.tra, self.target).load_translations_from_csvs()


    def test_grammar_to_csv_mock_translation_to_tra(self):
        d_folder = self.root / 'd'
        d_folder.mkdir()
        (d_folder / 'test.d').write_text('BEGIN ~NPC~\nIF ~~ THEN BEGIN start\nSAY @1\n'
                                       '++ @2 EXIT\nEND\n', encoding='utf-8')
        original = '@1 = ~Hello, <PLAYER1>!~ [VOICE]\n@2 = ~I returned.~ ~I returned, sister.~\n@3 = ~Unused | text\nnext line~\n'
        (self.tra / 'TEST.TRA').write_text(original, encoding='utf-8')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'parse_d_grammar.py'),
                                 str(d_folder), str(self.tra), str(self.source)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        paths = list(self.source.glob('*.csv'))
        self.assertEqual(len(paths), 2)
        _, unused = read_csv(self.source / '_unused_tra_lines.csv', ['Reference', 'Text'])
        self.assertEqual([r['Reference'] for r in unused], ['TEST.TRA:@3'])
        self.assertTrue(self.translator(test_mode=True).translate_all_dialogs())
        updater = TraUpdater(self.tra, self.target, self.output)
        updater.load_translations_from_csvs()
        updater.update_all_tra_files()
        self.assertEqual((self.output / 'TEST.TRA').read_text(), original)


    def translator(self, **kwargs):
        return DialogTranslator(str(self.source), str(self.target),
                                str(self.actors), str(self.dictionary), **kwargs)

    @staticmethod
    def response(prompt, values=None):
        data = json.loads(prompt)
        return json.dumps({'translations': {r['id']: values[r['id']] if values else r['english']
                                           for r in data['dialogue']}}, ensure_ascii=False)

    def test_two_passes_keep_full_graph_and_original_metadata(self):
        source = self.dialogue()
        translator = self.translator()
        male = {'1': 'Ты вернулся, <PLAYER1>!',
                '2': 'Я сказал "привет", затем ушёл.\nДругая строка.'}
        female = {'1': 'Ты вернулась, <PLAYER1>!',
                  '2': 'Я сказала "привет", затем ушла.\nДругая строка.'}
        with patch.object(translator, '_call_ollama', side_effect=lambda p, s:
                          self.response(p, female if 'male_translation' in json.loads(p)['dialogue'][0] else male)) as call:
            self.assertTrue(translator.translate_all_dialogs())
        self.assertEqual(call.call_count, 2)
        first, second = [json.loads(c.args[0]) for c in call.call_args_list]
        self.assertEqual(first['dialogue'][1]['speaker_gender'], 'male')
        self.assertEqual(second['dialogue'][1]['speaker_gender'], 'female')
        self.assertEqual(second['dialogue'][0]['male_translation'], male['1'])
        self.assertEqual(second['dialogue'][0]['speaker_gender'], 'FEMALE')
        header, original = read_csv(source, DIALOGUE_COLUMNS)
        _, exported = read_csv(self.target / source.name, header + TRANSLATION_COLUMNS)
        for before, after in zip(original, exported):
            self.assertEqual(before, {k: after[k] for k in header})
        self.assertEqual(exported[1]['Russian_Female'], female['2'])

    def test_addressee_female_npc_is_fixed_in_both_prompts(self):
        row = dict(zip(DIALOGUE_COLUMNS, ['PLAYER','1','','You came here.','@1','TRA:test.tra:@1']))
        row['Addressee'] = 'NPC'
        write_csv(self.source/'dialogue.csv', DIALOGUE_COLUMNS + ['Addressee'], [row])
        translator = self.translator(test_mode=True)
        with patch.object(translator, '_call_ollama', side_effect=lambda p, s: self.response(p)) as call:
            self.assertTrue(translator.translate_all_dialogs())
        for invocation in call.call_args_list:
            line = json.loads(invocation.args[0])['dialogue'][0]
            self.assertEqual(line['addressee'], 'NPC')
            self.assertEqual(line['addressee_gender'], 'FEMALE')
        self.assertIn('every sentence', TRANSLATION_RULES)

    def test_complete_35_line_graph_is_never_partitioned(self):
        self.dialogue([['PLAYER', f'original_{i}', f'original_{i-1}' if i else '',
                        'Hello', f'@{i}', f'TRA:test.tra:@{i}'] for i in range(35)])
        translator = self.translator()
        with patch.object(translator, '_call_ollama', side_effect=lambda p, s: self.response(p)) as call:
            self.assertTrue(translator.translate_all_dialogs())
        self.assertEqual(call.call_count, 2)
        for invocation in call.call_args_list:
            data = json.loads(invocation.args[0])
            self.assertEqual(len(data['dialogue']), 35)
            self.assertEqual(data['dialogue'][1]['predecessors'], ['1'])
        _, rows = read_csv(self.target/'dialogue.csv', DIALOGUE_COLUMNS)
        self.assertEqual(rows[34]['Line_ID'], 'original_34')

    def test_invalid_ids_types_tokens_and_duplicate_json_keys_are_rejected(self):
        rows = [DIALOGUE_COLUMNS, ['NPC','x','','Hi <PLAYER1>','@1','TRA:test.tra:@1']]
        invalid = ['{"translations":{"2":"Привет <PLAYER1>"}}',
                   '{"translations":{"1":"Привет"}}',
                   '{"translations":{"1":42}}',
                   '{"translations":{"1":""}}',
                   '{"translations":{"1":"<PLAYER1>","1":"<PLAYER1>"}}',
                   '{"translations":{"1":"<PLAYER1>"},"extra":0}']
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                DialogTranslator._parse_translation(text, rows)
        with self.assertRaises(ValueError):
            validate_text('<PLAYER1> <PLAYER1>', '<PLAYER1>')
        with self.assertRaises(ValueError):
            validate_text('a\nb', 'a b')

    def test_invalid_female_response_does_not_export_or_retry(self):
        self.dialogue()
        translator = self.translator()
        def reply(prompt, schema):
            data = json.loads(prompt)
            return '{"translations":{}}' if 'male_translation' in data['dialogue'][0] else self.response(prompt)
        with patch.object(translator, '_call_ollama', side_effect=reply) as call:
            self.assertFalse(translator.translate_all_dialogs())
        self.assertEqual(call.call_count, 2)
        self.assertFalse((self.target/'dialogue.csv').exists())
        with patch.object(translator, '_call_ollama', side_effect=ValueError('offline')) as call:
            self.assertFalse(translator.translate_all_dialogs())
        self.assertEqual(call.call_count, 1)

    def test_native_context_unlimited_generation_and_no_timeout(self):
        translator = self.translator()
        show = {'model_info': {'general.architecture':'qwen35','qwen35.context_length':262144}}
        done = {'message': {'content':'{"translations":{}}'}, 'done':True, 'done_reason':'stop'}
        responses = [io.BytesIO(json.dumps(result).encode()) for result in (show, done)]
        with patch('urllib.request.urlopen', side_effect=responses) as call:
            translator._call_ollama('{}', {'type':'object'})
        payload = json.loads(call.call_args_list[1].args[0].data)
        self.assertEqual(payload['options'], {'num_ctx':262144,'num_predict':-1})
        self.assertNotIn('think', payload)
        for invocation in call.call_args_list:
            self.assertNotIn('timeout', invocation.kwargs)
        self.assertEqual(payload['messages'][0]['content'], TRANSLATION_RULES)

    def test_explicit_context_override_and_incomplete_response(self):
        translator = self.translator(num_ctx=65536, think=False, ollama_url='http://localhost:11434/api/generate')
        result = {'response':'{"translations":{}}','done':True,'done_reason':'stop'}
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(result).encode())) as call:
            translator._call_ollama('{}', {})
        payload = json.loads(call.call_args.args[0].data)
        self.assertEqual(payload['options']['num_ctx'], 65536)
        self.assertIs(payload['think'], False)
        self.assertIn(TRANSLATION_RULES, payload['prompt'])
        result['done_reason'] = 'length'
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(result).encode())):
            with self.assertRaisesRegex(ValueError, 'Incomplete generation'):
                translator._call_ollama('{}', {})

    def test_glossary_longest_match_all_occurrences(self):
        translator = self.translator(test_mode=True)
        rules = translator._build_dictionary_context('Icewind Dale and Icewind Dale')
        self.assertNotIn('"Icewind" should', rules)
        rules = translator._build_dictionary_context('Icewind Dale and Icewind')
        self.assertIn('"Icewind" should', rules)

    def test_tra_import_after_two_json_passes(self):
        self.dialogue([['NPC','1','','You returned!','@1','TRA:test.tra:@1']])
        translator = self.translator()
        with patch.object(translator, '_call_ollama', side_effect=lambda p, s: self.response(p,
                {'1':'Ты вернулась!' if 'male_translation' in json.loads(p)['dialogue'][0] else 'Ты вернулся!'})):
            self.assertTrue(translator.translate_all_dialogs())
        original = '@1 = ~You returned!~ [VOICE] // preserve\r\n@2 = ~Other~\r\n'
        (self.tra/'TEST.TRA').write_bytes(original.encode())
        (self.tra/'untouched.tra').write_text('@3 = ~Untouched~\n')
        updater = TraUpdater(self.tra, self.target, self.output)
        updater.load_translations_from_csvs()
        updater.update_all_tra_files()
        result = (self.output/'TEST.TRA').read_bytes().decode()
        self.assertIn('~Ты вернулся!~ [VOICE] ~Ты вернулась!~ [VOICE] // preserve\r\n', result)
        self.assertIn('@2 = ~Other~\r\n', result)
        self.assertEqual((self.tra/'TEST.TRA').read_bytes().decode(), original)
        self.assertTrue((self.output/'untouched.tra').exists())


if __name__ == '__main__':
    unittest.main()
