"""Categorized extraction through translation/export; no game or model required."""
import contextlib
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from parse_d_grammar import ImprovedGrammarDialogueParser
from text_categories import CategorizedTextBuilder, ActorIndex, Actor, baf_responses
from weidu_usage import tokenize
from translate_dialogs import DialogTranslator
from translation_common import read_csv, DIALOGUE_COLUMNS, TRANSLATION_COLUMNS, merge_dialogue_rows, write_csv
from tra_format import parse_tra
from update_tra_from_csv import TraUpdater


class CategoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mod = self.root / 'mod'
        self.d = self.mod / 'dialogue'
        self.tra = self.mod / 'english'
        self.output = self.root / 'csv'
        for directory in (self.d, self.tra, self.output):
            directory.mkdir(parents=True)
        self.tp2 = self.mod / 'setup.tp2'
        self.actors = self.root / 'actors.csv'
        self.actors.write_text('')
        self.dictionary = self.root / 'dict.csv'
        self.dictionary.write_text('')

    def script(self, body, tra='@1=~First~ @2=~Second~ @3=~Unreferenced~'):
        (self.tra / 'setup.tra').write_text(tra)
        self.tp2.write_text('LANGUAGE ~English~ ~english~ ~mod/english/setup.tra~\n' + body)

    def cre(self, name, actor, gender, script):
        data = bytearray(0x2d4)
        data[:8] = b'CRE V1.0'
        data[0x275] = gender
        data[0x280:0x280 + len(actor)] = actor.encode()
        data[0x248:0x248 + len(script)] = script.encode()
        (self.mod / (name + '.cre')).write_bytes(data)

    def build(self, **kwargs):
        parser = ImprovedGrammarDialogueParser(str(self.d), str(self.tra), str(self.tp2))
        with contextlib.redirect_stdout(io.StringIO()):
            parser.process_all_d_files()
            parser.write_csv_files(str(self.output))
            manifest = CategorizedTextBuilder(parser, **kwargs).write(self.output)
        self.parser = parser
        self.rows = []
        for path in self.output.glob('*.csv'):
            _, rows = read_csv(path, DIALOGUE_COLUMNS)
            self.rows.extend(dict(row, csv=path.name) for row in rows)
        return manifest

    def test_blocks_alternatives_comments_and_two_line_cutscene(self):
        (self.mod / 'scene.baf').write_text('''/* IF THEN RESPONSE #100 DisplayString(Myself,@999) END */
IF True() THEN
RESPONSE #50 CutSceneId(Player1) DisplayStringHead(Myself,@1) Wait(4) DisplayStringHead(Myself,@2)
RESPONSE #50 DisplayStringHead(Player2,@2)
END
''')
        self.script('COMPILE ~mod/scene.baf~')
        self.build(batch_size=1)
        by_file = {}
        for row in self.rows:
            if row['Text_Type'] == 'baf_dialogue':
                by_file.setdefault(row['csv'], []).append(row)
        self.assertEqual(sorted(map(len, by_file.values())), [1, 2])
        sequence = next(rows for rows in by_file.values() if len(rows) == 2)
        self.assertEqual([r['Actor'] for r in sequence], ['Player1', 'Player1'])
        self.assertEqual(sequence[1]['Predecessors'], sequence[0]['Line_ID'])
        other = next(rows[0] for rows in by_file.values() if len(rows) == 1)
        self.assertEqual(other['Actor'], 'Player2')
        self.assertEqual(other['Speaker_Gender'], 'unknown')
        self.assertEqual(other['Predecessors'], '')

    def test_nested_action_override_and_cre_script_owner(self):
        self.cre('voice', 'SPEAKER', 2, 'speech')
        (self.mod / 'speech.baf').write_text('''IF True() THEN RESPONSE #100
DisplayStringHead(Myself,@1)
ActionOverride("SPEAKER",ActionOverride(Myself,DisplayStringHead(Myself,@2))) END''')
        self.script('COMPILE ~mod/speech.baf~')
        self.build()
        rows = [r for r in self.rows if r['Text_Type'] == 'baf_dialogue']
        self.assertEqual([r['Actor'] for r in rows], ['SPEAKER', 'SPEAKER'])
        self.assertEqual([r['Speaker_Gender'] for r in rows], ['FEMALE', 'FEMALE'])

    def test_region_owner_and_unknown_script_are_not_given_cre_gender(self):
        data = bytearray(0x11c + 0xc4)
        data[:8] = b'AREAV1.0'
        struct.pack_into('<H', data, 0x5a, 1)
        struct.pack_into('<I', data, 0x5c, 0x11c)
        data[0x11c:0x11c + 4] = b'Book'
        data[0x11c + 0x7c:0x11c + 0x7c + 4] = b'book'
        (self.mod / 'room.are').write_bytes(data)
        (self.mod / 'book.baf').write_text('IF True() THEN RESPONSE #100 DisplayString(Myself,@1) END')
        (self.mod / 'other.baf').write_text('IF True() THEN RESPONSE #100 DisplayString(Myself,@2) END')
        self.script('COMPILE ~mod/book.baf~ ~mod/other.baf~')
        self.build()
        rows = {r['TRA_Reference']: r for r in self.rows if r['Text_Type'] == 'baf_dialogue'}
        self.assertEqual(rows['@1']['Actor'], 'REGION:Book')
        self.assertTrue(rows['@2']['Actor'].startswith('UNKNOWN:'))
        self.assertEqual(rows['@1']['Speaker_Gender'], 'unknown')

    def test_notifications_use_narrator_even_over_player1(self):
        (self.mod / 'scene.baf').write_text('IF True() THEN RESPONSE #100 DisplayStringHead(Player1,@1) END')
        self.script('COMPILE ~mod/scene.baf~', '@1=~(Gained +5% Fire Resistance.)~')
        self.build()
        row = self.rows[0]
        self.assertEqual(row['Actor'], 'NARRATOR')
        self.assertEqual(row['Display_Target'], 'Player1')
        self.assertEqual(row['Text_Type'], 'notification')

    def test_journals_from_d_baf_and_installer_and_map_labels(self):
        (self.d / 'talk.d').write_text('BEGIN NPC IF ~~ THEN BEGIN s SAY @1 IF ~~ THEN JOURNAL @2 EXIT END')
        (self.mod / 'scene.baf').write_text('IF True() THEN RESPONSE #100 '
                                          'AddJournalEntry(@3,QUEST) EraseJournalEntry(@2) AddMapNote([1.2],@4) END')
        self.script('COMPILE ~mod/dialogue/talk.d~ ~mod/scene.baf~\nADD_JOURNAL @5',
                    '@1=~Speech~ @2=~I spoke.~ @3=~We spoke.~ @4=~Map~ @5=~I left.~')
        self.build()
        journal = [r for r in self.rows if r['Text_Type'] == 'journal']
        self.assertEqual({r['TRA_Reference'] for r in journal}, {'@2', '@3', '@5'})
        self.assertEqual({r['Actor'] for r in journal}, {'Player1'})
        self.assertEqual(len([r for r in self.rows if r['Text_Type'] == 'map_label']), 1)

    def test_all_three_d_journal_transition_clauses_are_separate_journal_rows(self):
        (self.d / 'talk.d').write_text('''BEGIN NPC
IF ~~ THEN BEGIN start
SAY @1
++ @2 JOURNAL /* ordinary journal */ @5 EXIT
++ @3 SOLVED_JOURNAL
/* completed quest */ @6 EXIT
++ @4 UNSOLVED_JOURNAL /* ongoing quest */ @7 EXIT
END
''')
        self.script('COMPILE ~mod/dialogue/talk.d~',
                    '@1=~Speech~ @2=~Reply one~ @3=~Reply two~ @4=~Reply three~ '
                    '@5=~I saw a vampire.~ @6=~I defeated the vampire.~ @7=~I accepted the task.~')
        manifest = self.build()
        journal = [row for row in self.rows if row['Text_Type'] == 'journal']
        dialogue = [row for row in self.rows if row['Text_Type'] == 'dialogue']
        self.assertEqual({row['TRA_Reference'] for row in journal}, {'@5', '@6', '@7'})
        self.assertEqual({row['TRA_Reference'] for row in dialogue}, {'@1', '@2', '@3', '@4'})
        self.assertEqual({row['Actor'] for row in journal}, {'Player1'})
        self.assertEqual(manifest['distinct_entries_by_category']['journal'], 3)
        self.assertEqual(manifest['exported_distinct_entries'], 7)

    def test_item_spell_and_soundset_context_and_gender(self):
        self.cre('voice', 'VOICE', 2, 'voice')
        self.script('''COPY ~mod/sword.itm~ ~override~ SAY NAME1 @1 SAY DESC @2
COPY ~mod/spell.spl~ ~override~ SAY NAME1 @3 SAY DESC @4
COPY ~mod/voice.cre~ ~override~ SAY NAME1 @5 SAY BATTLE_CRY1 @6 SAY 0xa4 @7
''', ' '.join(f'@{i}=~Text {i}~' for i in range(1, 8)))
        self.build(batch_size=1)
        by_ref = {r['TRA_Reference']: r for r in self.rows}
        self.assertEqual(by_ref['@1']['csv'], by_ref['@2']['csv'])
        self.assertEqual(by_ref['@3']['csv'], by_ref['@4']['csv'])
        self.assertEqual(by_ref['@6']['csv'], by_ref['@7']['csv'])
        self.assertEqual(by_ref['@6']['Actor'], 'VOICE')
        self.assertEqual(by_ref['@6']['Speaker_Gender'], 'FEMALE')
        self.assertEqual(by_ref['@7']['Text_Type'], 'character_sound')
        self.assertEqual(by_ref['@5']['Text_Type'], 'creature_name')

    def test_shared_item_names_are_in_each_items_description_file(self):
        self.script('''COPY ~mod/a.itm~ ~override~ SAY NAME1 @1 SAY DESC @2
COPY ~mod/b.itm~ ~override~ SAY NAME1 @1 SAY DESC @3''')
        self.build()
        name_rows = [r for r in self.rows if r['TRA_Reference'] == '@1']
        self.assertEqual(len(name_rows), 2)
        self.assertEqual({r['csv'] for r in name_rows}, {r['csv'] for r in self.rows})
        self.assertTrue(all('Same physical TRA' in r['Usage_Context'] for r in name_rows))

    def test_sound_and_item_helpers_inherit_each_callers_resource_context(self):
        self.cre('female', 'WOMAN', 2, 'female')
        self.cre('male', 'MAN', 1, 'male')
        (self.mod / 'description.tph').write_text('SAY DESC @2')
        self.script('''DEFINE_PATCH_FUNCTION voice BEGIN SAY BATTLE_CRY1 @1 END
COPY ~mod/female.cre~ ~override~ LPF voice END
COPY ~mod/male.cre~ ~override~ LPF voice END
COPY ~mod/item.itm~ ~override~ INCLUDE ~mod/description.tph~
''')
        self.build()
        sound = next(r for r in self.rows if r['TRA_Reference'] == '@1')
        self.assertEqual(sound['Text_Type'], 'character_sound')
        self.assertEqual(set(sound['Actor'].split(';')), {'WOMAN', 'MAN'})
        self.assertEqual(set(sound['Speaker_Gender'].split(';')), {'FEMALE', 'MALE'})
        description = next(r for r in self.rows if r['TRA_Reference'] == '@2')
        self.assertEqual(description['Text_Type'], 'item_description')

    def test_display_and_journal_actions_embedded_in_d_do_strings(self):
        (self.d / 'talk.d').write_text('BEGIN NPC IF ~~ THEN BEGIN s SAY @1 '
                                       'IF ~~ THEN DO ~DisplayStringHead(Player2,@2) AddJournalEntry(@3,QUEST)~ EXIT END')
        self.script('COMPILE ~mod/dialogue/talk.d~')
        self.build()
        display = next(r for r in self.rows if r.get('Text_Type') == 'baf_dialogue')
        self.assertEqual(display['Actor'], 'Player2')
        self.assertEqual(display['Speaker_Gender'], 'unknown')
        journal = next(r for r in self.rows if r.get('Text_Type') == 'journal')
        self.assertEqual(journal['TRA_Reference'], '@3')
        self.assertEqual(journal['Actor'], 'Player1')

    def test_unclassified_and_excluded_inventory_is_complete(self):
        self.script('PRINT @1\nCOPY ~mod/sword.itm~ ~override~ SAY NAME1 @2')
        manifest = self.build()
        self.assertEqual(manifest['inventory'], 3)
        self.assertEqual(manifest['excluded_entries'], 1)
        self.assertEqual(manifest['categorized_entries'], 2)
        self.assertEqual(manifest['unclassified'], ['TRA:setup.tra:@3'])

    def test_map_label_from_installer_function_parameter(self):
        self.script('COPY_EXISTING ~room.are~ ~override~\nLPF fj_are_structure INT_VAR '
                    'fj_info_point_strref=RESOLVE_STR_REF(@1) END')
        self.build()
        row = next(r for r in self.rows if r['TRA_Reference'] == '@1')
        self.assertEqual(row['Text_Type'], 'area_text')
        self.assertEqual(row['Field'], 'FJ_INFO_POINT_STRREF')

    def test_hardcoded_text_is_readonly_and_native_tlk_is_accounted_for(self):
        scene = self.mod / 'scene.baf'
        scene.write_text('IF True() THEN RESPONSE #100 DisplayStringHead(Myself,"Hardcoded") '
                         'DisplayStringHead(Myself,@1) END')
        self.script('COMPILE ~mod/scene.baf~')
        manifest = self.build()
        self.assertEqual(len(manifest['hardcoded_context']), 1)
        self.assertTrue(all(row['Dialogue_Text'] != 'Hardcoded' for row in self.rows))
        row = next(row for row in self.rows if row['TRA_Reference'] == '@1')
        self.assertIn('read-only hardcoded context', row['Source_Context'])
        self.assertIn('Hardcoded', row['Source_Context'])
        scene.write_text('IF True() THEN RESPONSE #100 DisplayStringHead(Myself,12345) END')
        self.output = self.root / 'native'
        self.output.mkdir()
        manifest = self.build()
        self.assertEqual(len(manifest['native_tlk_uses']), 1)

    def test_cross_file_extern_through_hardcoded_dialogue_exports_only_tra_rows(self):
        first = 'CHAIN FIRST start @1 EXTERN SECOND middle'
        middle = 'CHAIN SECOND middle ~Read-only original speech.~ EXTERN THIRD last'
        last = 'CHAIN THIRD last @2 EXIT'
        for name, text in [('first.d', first), ('middle.d', middle), ('last.d', last)]:
            (self.d / name).write_text(text)
        self.script('COMPILE ~mod/dialogue~')
        self.build()
        dialogue = [r for r in self.rows if r['Text_Type'] == 'dialogue']
        self.assertEqual(len(dialogue), 2)
        self.assertEqual(len({r['csv'] for r in dialogue}), 1)
        start = next(r for r in dialogue if r['TRA_Reference'] == '@1')
        end = next(r for r in dialogue if r['TRA_Reference'] == '@2')
        self.assertEqual(end['Predecessors'], start['Line_ID'])
        self.assertIn('Read-only original speech.', start['Source_Context'])
        self.assertEqual((self.d / 'middle.d').read_text(), middle)

    def test_prompt_uses_resource_gender_and_all_category_context(self):
        self.cre('voice', 'VOICE', 2, 'voice')
        self.script('COPY ~mod/voice.cre~ ~override~ SAY BATTLE_CRY1 @1')
        self.build()
        path = next(self.output.glob('character_sound__*.csv'))
        translator = DialogTranslator(str(self.output), str(self.root / 'ru'), str(self.actors), str(self.dictionary), test_mode=True)
        data = json.loads(translator._create_translation_prompt(path.read_text(), 'male', '', ''))
        line = data['dialogue'][0]
        self.assertEqual(line['speaker_gender'], 'FEMALE')
        self.assertEqual(line['text_type'], 'character_sound')
        self.assertEqual(line['field'], 'BATTLE_CRY1')
        self.assertIn('voice.cre', line['resource'])
        self.assertNotIn('note', line)

    def test_dialogue_gender_uses_cre_dialogue_identity(self):
        self.cre('voice', 'SPEAKER', 2, 'voice')
        path = self.mod / 'voice.cre'
        data = bytearray(path.read_bytes())
        data[0x2cc:0x2cc + 6] = b'TALKER'
        path.write_bytes(data)
        (self.d / 'talk.d').write_text('BEGIN TALKER IF ~~ THEN BEGIN s SAY @1 IF ~~ THEN EXIT END')
        self.script('COMPILE ~mod/dialogue/talk.d~')
        self.build()
        row = next(r for r in self.rows if r['TRA_Reference'] == '@1')
        self.assertEqual(row['Actor'], 'TALKER')
        self.assertEqual(row['Speaker_Gender'], 'FEMALE')

    def test_gender_metadata_cannot_fix_party_slots_and_survives_shared_merge(self):
        self.script('')
        translator = DialogTranslator(str(self.output), str(self.root / 'ru'), str(self.actors), str(self.dictionary), test_mode=True)
        self.assertEqual(translator._speaker_genders(['Player1', 'Player2', 'NPC'], 'male', 'FEMALE;MALE;FEMALE'),
                         ['male', 'unknown', 'FEMALE'])
        header = DIALOGUE_COLUMNS + ['Speaker_Gender', 'Source_Context']
        rows = [header, ['ONE', '1', '', 'Ready.', '@1', 'TRA:setup.tra:@1', 'MALE', 'one'],
                ['TWO', '2', '', 'Ready.', '@1', 'TRA:setup.tra:@1', 'FEMALE', 'two']]
        merged, _ = merge_dialogue_rows(rows)
        buffer = io.StringIO()
        csv.writer(buffer).writerows(merged)
        payload, _ = translator._both_request(buffer.getvalue(), merged, '', '')
        line = json.loads(payload)['dialogue'][0]
        self.assertEqual(line['speaker_gender'], ['MALE', 'FEMALE'])
        self.assertIn('no gendered form', line['note'])
        self.assertEqual(line['source_context'], 'one | two')

    def test_categorized_translation_and_export_roundtrip_skips_duplicate_requests(self):
        (self.mod / 'one.baf').write_text('IF True() THEN RESPONSE #100 DisplayStringHead(Player1,@2) END')
        (self.mod / 'two.baf').write_text('IF True() THEN RESPONSE #100 DisplayStringHead(Player2,@2) END')
        self.script('PRINT @1\nCOMPILE ~mod/one.baf~ ~mod/two.baf~\nADD_JOURNAL @3',
                    '@1=~Installer~\n@2=~(Gained resistance.)~ [SOUND]\n@3=~I spoke.~\n')
        manifest = self.build()
        target = self.root / 'ru'
        translator = DialogTranslator(str(self.output), str(target), str(self.actors), str(self.dictionary), method='both')
        def reply(prompt, schema):
            data = json.loads(prompt)
            return json.dumps({'translations': {line['id']: {'male': line['english'], 'female': line['english_female']}
                                                for line in data['dialogue']}})
        with contextlib.redirect_stdout(io.StringIO()), patch.object(translator, '_call_ollama', side_effect=reply) as model:
            self.assertTrue(translator.translate_all_dialogs())
            self.assertEqual(model.call_count, 2)  # shared display + journal
            updater = TraUpdater(str(self.tra), str(target), str(self.root / 'russian'))
            updater.load_translations_from_csvs()
            updater.update_all_tra_files()
        self.assertEqual((self.tra / 'setup.tra').read_text(), (self.root / 'russian/setup.tra').read_text())
        self.assertEqual(manifest['categorized_entries'], 2)

    def test_cli_default_and_legacy_option(self):
        self.script('ADD_JOURNAL @1')
        command = [sys.executable, str(SCRIPTS / 'parse_d_grammar.py'), str(self.d), str(self.tra),
                   str(self.output), '--tp2-file', str(self.tp2)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.output / '_unused_tra_lines.csv').exists())
        self.assertTrue((self.output / '_extraction_manifest.json').exists())
        repeat = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(repeat.returncode, 0)
        legacy = self.root / 'legacy'
        command[4] = str(legacy)
        result = subprocess.run(command + ['--unused-layout', 'legacy'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((legacy / '_unused_tra_lines.csv').exists())


if __name__ == '__main__':
    unittest.main()
