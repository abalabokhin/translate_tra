"""Item retrieval, statistics-only prompting and guarded TRA export, without an LLM."""
import contextlib
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from find_closest_item import (DEFAULT_ENGLISH, DEFAULT_RUSSIAN, ItemTemplateIndex,
                               statistics_section, statistics_labels)
from translate_dialogs import DialogTranslator
from translation_common import DIALOGUE_COLUMNS, read_csv, validate_text, write_csv
from update_tra_from_csv import TraUpdater
from tra_format import parse_tra, read_text


class ItemTemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.en, self.ru = self.root / 'en.tra', self.root / 'ru.tra'
        self.en.write_text('''@1=~Weapon lore must never enter the prompt.
STATISTICS:
THAC0: +1
Damage: 1d6+1
Speed Factor: 3
Requires:
 5 Strength
Weight: 2~
@2=~Armor lore.
STATISTICS:
Armor Class: 4
Weight: 8~
@3=~Ring lore.
STATISTICS:
Charge abilities:
- Spell
  Range: 40 ft.
  Duration: 2 hours
Weight: 0~
@4=~Big item.
STATISTICS:
Damage: 1d6
Speed Factor: 3
Armor Class: 4
Charge abilities:
Range: 40 ft.
Duration: 2 hours
Equipped abilities:
Weight: 2~
@5=~Missing pair.
STATISTICS:
Weight: 1~
''')
        self.ru.write_text('''@1=~Чужая история.
ПАРАМЕТРЫ:
THAC0: +1
Урон: 1d6+1
Фактор скорости: 3
Требования:
 Сила 5
Вес: 2~
@2=~Доспех.
ПАРАМЕТРЫ:
Класс защиты: 4
Вес: 8~
@3=~Кольцо.
ПАРАМЕТРЫ:
Свойства зарядов:
- Заклинание
  Дистанция: 40 футов
  Длительность: 2 часа
Вес: 0~
@4=~Длинная история.
ПАРАМЕТРЫ:
Урон: 1d6
Вес: 2~
''')
        self.index = ItemTemplateIndex(self.en, self.ru)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.actors, self.dictionary = self.root / 'actors.csv', self.root / 'dict.csv'
        self.actors.write_text('NPC,FEMALE\n')
        self.dictionary.write_text('Moonblade,Лунный клинок,item name\n')

    def translator(self, **options):
        return DialogTranslator(self.source, self.root / 'target', self.actors, self.dictionary,
                                item_reference_english=self.en, item_reference_russian=self.ru, **options)

    def csv_text(self, texts, extra=None):
        header = DIALOGUE_COLUMNS + list(extra or {})
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(header)
        for i, text in enumerate(texts, 1):
            writer.writerow(['NARRATOR', str(i), '', text, f'@{i}', f'TRA:items.tra:@{i}']
                            + list((extra or {}).values()))
        return stream.getvalue()

    def test_marker_is_a_heading_case_insensitive_and_lore_is_excluded(self):
        self.assertIsNone(statistics_section('Someone said STATISTICS: aloud.'))
        self.assertEqual(statistics_section('Lore\r\n\r\n statistics: \r\nWeight: 2'),
                         'statistics: \nWeight: 2')
        self.assertNotIn('lore', self.index.closest('Lore\nSTATISTICS:\nWeight: 1')['english_statistics'])

    def test_all_labels_include_digits_nested_fields_and_ignore_values(self):
        labels = statistics_labels('STATISTICS:\nTHAC0: +3\nCharge abilities:\n  Range: 40 ft.\nDamage type (melee): slashing\n- Save vs. Death: +2')
        self.assertEqual(set(labels), {'thac0', 'charge abilities', 'range', 'damage type', 'save', 'save vs. death'})

    def test_specific_sentences_become_short_concepts(self):
        labels = statistics_labels('Chance to score a critical hit: 10%\n'
                                   'Creates a globe of anti-magic around the user: once per day\n'
                                   'Damage done to user: 2\nSave vs. Death: +1\nSaving Throws: +2')
        self.assertEqual(set(labels), {'chance', 'critical hit', 'anti-magic', 'damage', 'save',
                                       'save vs. death', 'saving throws'})

    def test_specific_saves_and_saving_throws_remain_distinct_without_double_counting(self):
        index = ItemTemplateIndex(DEFAULT_ENGLISH, DEFAULT_RUSSIAN)
        for label in ('Save vs. Breath', 'Save vs. Death', 'Save vs. Petrification/Polymorph',
                      'Save vs. Polymorph', 'Save vs. Spell', 'Save vs. Wand', 'Saving Throws'):
            with self.subTest(label=label):
                self.assertIn(label.casefold(), index.english_labels)
                self.assertEqual(index.keywords('STATISTICS:\n' + label + ': +2'), {label.casefold()})
        self.assertEqual(index.keywords('STATISTICS:\nA save negates the effect.'), {'save'})

    def test_longest_concepts_win_and_repetition_is_not_counted_twice(self):
        with self.en.open('a') as f:
            f.write('@6=~STATISTICS:\nResistance: 10%\nMagic Resistance: 20%\n'
                    'Chance to score a critical hit: 5%\nDamage done to user: 2\n'
                    'Damage type: crushing\nSave vs. Death: +1~')
        with self.ru.open('a') as f:
            f.write('@6=~ПАРАМЕТРЫ:\nСопротивление: 10%~')
        index = ItemTemplateIndex(self.en, self.ru)
        self.assertEqual(index.keywords('STATISTICS:\nMagic Resistance: 20%\nMagic Resistance: 30%'),
                         {'magic resistance'})
        keys = index.keywords('STATISTICS:\n- A 10% chance to score a critical hit.\n'
                              '- Inflicts damage. Additional damage. Save vs. spell negates.')
        self.assertEqual(keys, {'chance', 'critical hit', 'damage', 'save'})
        self.assertNotIn('damage', index.keywords('STATISTICS:\nDamage type: crushing'))
        self.assertNotIn('resistance', index.keywords('STATISTICS:\nMagic Resistance: 20%'))

    def test_keyword_matching_uses_word_boundaries_and_statistics_only(self):
        index = self.index
        self.assertNotIn('damage', index.keywords('STATISTICS:\nUndamaged: yes'))
        a = index.closest('Damage: 1d8\nSTATISTICS:\nWeight: 2')
        self.assertNotIn('damage', a['matched_keywords'])

    def test_weapon_armor_and_charge_templates(self):
        for text, reference in [('Damage: 1d8\nSpeed Factor: 4\nWeight: 5', '@1'),
                                ('Armor Class: 2\nWeight: 10', '@2'),
                                ('Charge abilities:\nRange: 50 ft.\nDuration: 3 hours\nWeight: 1', '@3')]:
            with self.subTest(reference=reference):
                self.assertEqual(self.index.closest('STATISTICS:\n' + text)['reference'], reference)

    def test_lore_and_numeric_values_do_not_change_selection(self):
        a = self.index.closest('Armor lore!\nSTATISTICS:\nDamage: 1d8\nSpeed Factor: 3')
        b = self.index.closest('Weapon lore!\nSTATISTICS:\nDamage: 2d4+8\nSpeed Factor: 1')
        self.assertEqual(a['reference'], b['reference'])

    def test_unknown_fields_are_reported_and_do_not_disappear(self):
        selected = self.index.closest('STATISTICS:\nDamage: 1d8\nMoonlight strength: 4')
        self.assertIn('moonlight strength', selected['unmatched_keywords'])
        self.assertIn('damage', selected['matched_keywords'])
        self.assertIsNotNone(self.index.closest('STATISTICS:\nTotally new field: 4'))

    def test_no_statistics_has_no_template(self):
        self.assertIsNone(self.index.closest('Ordinary dialogue.'))

    def test_target_receives_resistances_are_generic_matching_labels(self):
        for element in ('Acid', 'Cold', 'Electrical', 'Fire'):
            with self.subTest(element=element):
                generic = f'{element} Resistance'
                specific = f'Target receives {generic}'
                self.assertEqual(statistics_labels(specific + ': +20%'),
                                 statistics_labels(generic + ': +10%'))
                self.assertEqual(len(statistics_labels(specific + ': +20%\n' + generic + ': +10%')), 1)

    def test_normalized_label_matches_without_rewriting_reference_example(self):
        with self.en.open('a') as f:
            f.write('@6=~STATISTICS:\nTarget receives Acid Resistance: 20%\nWeight: 0~')
        with self.ru.open('a') as f:
            f.write('@6=~ПАРАМЕТРЫ:\nЦель получает добавку к сопротивлению кислоте: 20%\nВес: 0~')
        index = ItemTemplateIndex(self.en, self.ru)
        match = index.closest('STATISTICS:\nAcid Resistance: 50%\nWeight: 0')
        self.assertEqual(match['reference'], '@6')
        self.assertIn('acid resistance', match['matched_keywords'])
        self.assertIn('Target receives Acid Resistance', match['english_statistics'])
        self.assertNotIn('target receives acid resistance', index.frequencies)

    def test_inventory_contains_both_languages_and_missing_pair_is_skipped(self):
        data = self.index.keyword_inventory()
        self.assertEqual(data['paired_items'], 4)
        self.assertEqual(data['skipped_unpaired'], [5])
        self.assertIn('thac0', {r['normalized'] for r in data['english']})
        self.assertIn('фактор скорости', {r['normalized'] for r in data['russian']})

    def test_ties_are_deterministic_by_reference(self):
        self.en.write_text('@8=~STATISTICS:\nWeight: 1~\n@7=~STATISTICS:\nWeight: 1~')
        self.ru.write_text('@7=~ПАРАМЕТРЫ:\nВес: 1~\n@8=~ПАРАМЕТРЫ:\nВес: 1~')
        self.assertEqual(ItemTemplateIndex(self.en, self.ru).closest('STATISTICS:\nWeight: 5')['reference'], '@7')

    def test_bad_or_missing_reference_files_fail_clearly(self):
        self.ru.write_text('@1=~No statistics translation~')
        with self.assertRaisesRegex(ValueError, 'no paired'):
            ItemTemplateIndex(self.en, self.ru)
        with self.assertRaises(OSError):
            ItemTemplateIndex(self.root / 'missing.tra', self.ru)

    def test_prompt_is_per_description_and_keeps_glossary(self):
        text = self.csv_text(['Moonblade\n\nSTATISTICS:\nDamage: 1d8\nSpeed Factor: 3',
                              'Armor\n\nSTATISTICS:\nArmor Class: 2\nWeight: 5', 'Plain name'])
        translator = self.translator()
        data = json.loads(translator._create_translation_prompt(text, 'male', '', 'Moonblade = Лунный клинок'))
        self.assertIn('Лунный клинок', data['glossary'])
        a, b, plain = data['dialogue']
        self.assertEqual(a['item_statistics_template']['reference'], '@1')
        self.assertEqual(b['item_statistics_template']['reference'], '@2')
        self.assertNotIn('item_statistics_template', plain)
        self.assertNotIn('Weapon lore', json.dumps(data))
        self.assertNotIn('Чужая история', json.dumps(data, ensure_ascii=False))
        self.assertIn('ONLY', a['item_statistics_instruction'])
        self.assertIn('narrative', a['item_statistics_instruction'])

    def test_single_and_both_gender_prompts_handle_original_female_statistics(self):
        female = 'Other\n\nSTATISTICS:\nArmor Class: 3\nWeight: 4'
        content = self.csv_text(['Moonblade\n\nSTATISTICS:\nDamage: 1d8\nSpeed Factor: 3'],
                                {'Source_Female_Text': female, 'Source_Has_Female': '1'})
        translator = self.translator()
        single = json.loads(translator._create_translation_prompt(content, 'female', '', ''))
        self.assertEqual(single['dialogue'][0]['item_statistics_template']['reference'], '@2')
        both, _ = translator._both_request(content, list(csv.reader(io.StringIO(content))), '', '')
        row = json.loads(both)['dialogue'][0]
        self.assertEqual(row['item_statistics_template']['reference'], '@1')
        self.assertEqual(row['item_statistics_template_female']['reference'], '@2')

    def test_templates_can_be_disabled_and_nonitems_never_load_references(self):
        translator = self.translator(item_templates=False)
        text = self.csv_text(['STATISTICS:\nWeight: 5'])
        with patch('translate_dialogs.ItemTemplateIndex', side_effect=AssertionError('must not load')):
            self.assertNotIn('item_statistics_template', json.loads(translator._create_translation_prompt(text, 'male', '', ''))['dialogue'][0])
            self.translator()._create_translation_prompt(self.csv_text(['Hello.']), 'male', '', '')

    def test_validation_allows_statistics_layout_quotes_and_reordered_requirements(self):
        source = 'Story.\n\nSTATISTICS:\nDamage: 1d6+2\nRequires: 5 Strength\nWeight: 4'
        target = 'История.\n\nПАРАМЕТРЫ:\n\nУрон: 1d6+2\nТребования:\n Сила 5\n\nВес: 4'
        validate_text(source, target)
        validate_text('STATISTICS:\nCharge abilities:\n- Spell (2/day)',
                      'ПАРАМЕТРЫ:\n\nСвойства зарядов:\n- "Заклинание" (2/день)')
        validate_text('STATISTICS:\nChance: 2.5%', 'ПАРАМЕТРЫ:\nШанс: 2,5%')

    def test_validation_rejects_changed_values_dice_signs_percent_and_missing_heading(self):
        source = 'STATISTICS:\nDamage: 1d6+2\nTHAC0: +1\nChance: 50%\nWeight: 4'
        for replacement in ('1d8+2', '1d6+3', '1d6', '2d6+2'):
            with self.subTest(dice=replacement), self.assertRaisesRegex(ValueError, 'statistics'):
                validate_text(source, source.replace('1d6+2', replacement))
        for before, after in [('+1', '-1'), ('50%', '50'), ('Weight: 4', 'Weight: 5'), ('STATISTICS:', 'No heading')]:
            with self.subTest(change=(before, after)), self.assertRaisesRegex(ValueError, 'statistics'):
                validate_text(source, source.replace(before, after))

    def test_statistics_exception_keeps_narrative_and_token_checks(self):
        source = 'Story <CHARNAME>.\n\nSTATISTICS:\nWeight: 4'
        for target in ['Story <PLAYER1>.\n\nПАРАМЕТРЫ:\nВес: 4',
                       'Story <CHARNAME>.\nПАРАМЕТРЫ:\nВес: 4',
                       '"Story" <CHARNAME>.\n\nПАРАМЕТРЫ:\nВес: 4']:
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_text(source, target)
        with self.assertRaises(ValueError):
            validate_text('Dialogue.\nNext.', 'Диалог. Далее.')

    def test_translation_export_round_trip_uses_template_and_preserves_sound(self):
        english = 'Moonblade\n\nSTATISTICS:\nDamage: 1d8+2\nRequires: 5 Strength\nWeight: 4'
        russian = 'Лунный клинок\n\nПАРАМЕТРЫ:\n\nУрон: 1d8+2\nТребования:\n Сила 5\n\nВес: 4'
        (self.source / 'item.csv').write_text(self.csv_text([english]))
        tra = self.root / 'tra'; tra.mkdir()
        (tra / 'items.tra').write_text('@1=~' + english + '~ [voice]')
        translator = self.translator(backend='codex', method='both')
        def reply(prompt, *args):
            data = json.loads(prompt)
            self.assertIn('Лунный клинок', data['glossary'])
            self.assertEqual(data['dialogue'][0]['item_statistics_template']['reference'], '@1')
            return json.dumps({'translations': {'1': {'male': russian, 'female': russian}}})
        with contextlib.redirect_stdout(io.StringIO()), patch.object(translator, '_call_model', side_effect=reply):
            self.assertTrue(translator.translate_all_dialogs())
            updater = TraUpdater(tra, self.root / 'target', self.root / 'output')
            updater.load_translations_from_csvs(); updater.update_all_tra_files()
        entry = parse_tra(read_text(self.root / 'output/items.tra'))[1]
        self.assertEqual(entry.variants[0].text, russian)
        self.assertEqual(entry.variants[0].sound, '[voice]')

    def test_cli_reads_csv_and_collects_keywords(self):
        path = self.source / 'item.csv'
        path.write_text(self.csv_text(['STATISTICS:\nArmor Class: 2\nWeight: 3']))
        command = [sys.executable, str(SCRIPTS / 'find_closest_item.py'),
                   '--reference-english', str(self.en), '--reference-russian', str(self.ru)]
        result = subprocess.run(command + [str(path)], capture_output=True, text=True, check=True, cwd=self.root)
        self.assertEqual(json.loads(result.stdout)[0]['reference'], '@2')
        result = subprocess.run(command + ['--list-keywords'], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)['paired_items'], 4)

    def test_legacy_unused_csv_gets_item_prompt(self):
        path = self.source / '_unused_tra_lines.csv'
        write_csv(path, ['Reference', 'Text'], [{'Reference': 'items.tra:@1', 'Text': 'STATISTICS:\nWeight: 4'}])
        translator = self.translator(test_mode=True)
        original = translator._call_model
        prompts = []
        def capture(prompt, *args):
            prompts.append(json.loads(prompt))
            return original(prompt, *args)
        with contextlib.redirect_stdout(io.StringIO()), patch.object(translator, '_call_model', side_effect=capture):
            self.assertTrue(translator.translate_all_dialogs())
        self.assertTrue(all('item_statistics_template' in p['dialogue'][0] for p in prompts))

    def test_translator_cli_accepts_custom_references_and_disable_switch(self):
        (self.source / 'item.csv').write_text(self.csv_text(['STATISTICS:\nWeight: 4']))
        command = [sys.executable, str(SCRIPTS / 'translate_dialogs.py'), str(self.source),
                   '--backend', 'codex', '--test', '--actors', str(self.actors),
                   '--dictionary', str(self.dictionary)]
        result = subprocess.run(command + ['--target', str(self.root / 'cli-target'),
                                '--item-reference-english', str(self.en),
                                '--item-reference-russian', str(self.ru)],
                                capture_output=True, text=True, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run(command + ['--target', str(self.root / 'disabled-target'),
                                '--item-reference-english', str(self.root / 'missing.tra'),
                                '--no-item-templates'], capture_output=True, text=True, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shipped_reference_catalog_and_keyword_snapshot(self):
        index = ItemTemplateIndex(DEFAULT_ENGLISH, DEFAULT_RUSSIAN)
        snapshot = json.loads((SCRIPTS / 'reference/item_statistics_keywords.json').read_text())
        self.assertEqual(index.keyword_inventory(), snapshot)
        self.assertEqual(len(index.templates), 615)
        self.assertFalse(index.skipped)
        for item in index.templates:
            match = index.closest(item.english)
            self.assertFalse(match['unmatched_keywords'])
            self.assertTrue(match['english_statistics'].startswith('STATISTICS:'))
            self.assertTrue(match['russian_statistics'].startswith('ПАРАМЕТРЫ:'))


if __name__ == '__main__':
    unittest.main()
