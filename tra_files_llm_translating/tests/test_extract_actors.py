"""Speaking actors, rather than bare dialogue identifiers, need gender context."""
import contextlib
import csv
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker
from DLexer import DLexer
from DParser import DParser
from extract_actors_using_grammar import (
    ActorExtractionListener, read_dialogue_table, scan_cre_files_in_folders,
)


class SpeakingActorTests(unittest.TestCase):
    def parse(self, text):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            parser = DParser(CommonTokenStream(DLexer(InputStream(text))))
            tree = parser.dFileRule()
        self.assertEqual(errors.getvalue(), '', 'Fixture must parse without recovery')
        listener = ActorExtractionListener('fixture.d')
        ParseTreeWalker().walk(listener, tree)
        return listener

    def test_empty_declarations_and_external_references_are_not_speakers(self):
        result = self.parse('''BEGIN EMPTY
BEGIN SPEAKER
IF ~~ THEN BEGIN greeting
SAY @1
++ @2 EXTERN DESTINATION next
END
''')
        self.assertEqual(result.actors, {'SPEAKER'})
        self.assertEqual(result.referenced_actors, {'EMPTY', 'SPEAKER', 'DESTINATION'})

    def test_append_replace_and_nested_appendi_attribute_say_to_owner(self):
        for action in ('APPEND', 'APPEND_EARLY', 'REPLACE'):
            with self.subTest(action=action):
                result = self.parse(f'''{action} OUTER
APPENDI INNER
IF ~~ THEN BEGIN greeting SAY @1 IF ~~ THEN EXIT END
END
END
''')
                self.assertEqual(result.actors, {'INNER'})
                self.assertIn('OUTER', result.referenced_actors)

    def test_chain_speakers_include_branches_and_exclude_reply_only_targets(self):
        result = self.parse('''CHAIN FIRST greeting
@1
== SECOND @2 = @3
BRANCH ~True()~ BEGIN
== THIRD @4
END
END
++ @5 EXTERN DESTINATION next
''')
        self.assertEqual(result.actors, {'FIRST', 'SECOND', 'THIRD'})

    def test_interjections_do_not_attribute_speech_to_the_target(self):
        for action, ending in [('INTERJECT', 'EXIT'),
                               ('INTERJECT_COPY_TRANS', 'END'),
                               ('INTERJECT_COPY_TRANS2', 'END'),
                               ('INTERJECT_COPY_TRANS3', 'END'),
                               ('INTERJECT_COPY_TRANS4', 'END')]:
            with self.subTest(action=action):
                result = self.parse(f'''{action} TARGET state global
== COMMENTER @1
{ending}
''')
                self.assertEqual(result.actors, {'COMMENTER'})
                self.assertIn('TARGET', result.referenced_actors)

    def test_chain2_does_not_count_exit_dialogue_as_a_speaker(self):
        result = self.parse('''BEGIN OUTER
CHAIN2 SPEAKER greeting @1 = @2 END DESTINATION next
''')
        self.assertEqual(result.actors, {'SPEAKER'})

    def test_replace_say_is_speech_even_without_a_local_declaration(self):
        result = self.parse('REPLACE_SAY ~speaker~ state @1')
        self.assertEqual(result.actors, {'SPEAKER'})

    def test_reply_only_extension_and_trigger_changes_have_no_npc_speech(self):
        result = self.parse('''EXTEND_TOP TARGET state
++ @1 EXTERN DESTINATION next
END
ADD_STATE_TRIGGER OTHER state ~True()~
SET_WEIGHT WEIGHTED state #1
''')
        self.assertEqual(result.actors, set())
        self.assertEqual(result.referenced_actors,
                         {'TARGET', 'DESTINATION', 'OTHER', 'WEIGHTED'})

    def test_silent_say_still_counts_as_an_explicit_text_entry(self):
        result = self.parse('BEGIN SPEAKER IF ~~ THEN BEGIN state SAY ~~ IF ~~ THEN EXIT END')
        self.assertEqual(result.actors, {'SPEAKER'})

    def test_cli_gender_csv_omits_empty_dialogues_and_reference_only_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'fixture.d').write_text('''BEGIN EMPTY
BEGIN SPEAKER
IF ~~ THEN BEGIN state SAY @1 IF ~~ THEN EXTERN TARGET next END
''')
            output = root / 'actors.csv'
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / 'extract_actors_using_grammar.py'),
                 str(root), '--csv-output', str(output)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, '')
            with output.open(newline='') as handle:
                self.assertEqual(list(csv.reader(handle)), [['SPEAKER', '']])


class ExternalCreTests(unittest.TestCase):
    def cre(self, path, dialog='', death_var='', gender=1, signature=b'CRE V1.0'):
        data = bytearray(0x2d4)
        data[:8] = signature
        data[0x275] = gender
        data[0x280:0x280 + len(death_var)] = death_var.encode('ascii')
        data[0x2cc:0x2cc + len(dialog)] = dialog.encode('ascii')
        path.write_bytes(data)

    def scan(self, folders, actors, death_vars=()):
        with contextlib.redirect_stdout(io.StringIO()):
            return scan_cre_files_in_folders(folders, actors, death_vars)

    def test_only_matching_resources_are_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.cre(root / 'speaker.CRE', dialog='speaker', gender=2)
            self.cre(root / 'companion.CRE', dialog='initial', death_var='companion')
            self.cre(root / 'unrelated.CRE', dialog='unused', death_var='unused', gender=4)
            dialogs, by_dialog, variables, by_variable, genders = self.scan(
                [root], {'SPEAKER', 'JOINED'}, {'COMPANION'})
            self.assertEqual(genders, {'speaker.CRE': 'FEMALE', 'companion.CRE': 'MALE'})
            self.assertEqual(by_dialog['SPEAKER'], {'speaker.CRE'})
            self.assertEqual(by_variable['COMPANION'], {'companion.CRE'})
            self.assertNotIn('unrelated.CRE', dialogs)
            self.assertNotIn('unused', variables.values())

    def test_first_folder_overrides_same_resource_case_insensitively(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mod, game = root / 'mod', root / 'game'
            mod.mkdir(); game.mkdir()
            self.cre(mod / 'actor.cre', dialog='SPEAKER', gender=2)
            self.cre(game / 'ACTOR.CRE', dialog='SPEAKER', gender=1)
            self.cre(game / 'OTHER.CRE', dialog='OTHER', gender=1)
            self.assertEqual(self.scan([mod, game], {'SPEAKER', 'OTHER'})[4],
                             {'actor.cre': 'FEMALE', 'OTHER.CRE': 'MALE'})
            self.assertEqual(self.scan([game, mod], {'SPEAKER'})[4], {'ACTOR.CRE': 'MALE'})

    def test_shadowed_game_resource_is_not_used_even_if_it_matches(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mod, game = root / 'mod', root / 'game'
            mod.mkdir(); game.mkdir()
            self.cre(mod / 'actor.cre', dialog='CHANGED')
            self.cre(game / 'ACTOR.CRE', dialog='OLD')
            self.assertEqual(self.scan([mod, game], {'OLD'})[4], {})

    def test_unsupported_and_truncated_cre_fail_clearly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'bad.cre'
            for data in (b'CRE V1.0', b'CRE V2.2' + bytes(0x2d4 - 8)):
                with self.subTest(length=len(data)):
                    path.write_bytes(data)
                    with self.assertRaisesRegex(ValueError, 'Unsupported or truncated CRE'):
                        self.scan([root], {'SPEAKER'})

    def test_tables_include_soa_and_tob_dialogues_but_not_scripts(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'PDIALOG.2DA'
            path.write_text('''2DA V1.0
****
POST_DIALOG_FILE JOIN_DIALOG_FILE DREAM_SCRIPT_FILE 25POST_DIALOG_FILE 25JOIN_DIALOG_FILE 25DREAM_SCRIPT_FILE 25OVERRIDE_SCRIPT_FILE
COMPANION POST JOIN DREAM POST25 JOIN25 DREAM25 OVERRIDE // comment
EMPTY **** NONE **** *** * 0 NONE
''')
            self.assertEqual(read_dialogue_table(path, 'PDIALOG'), {
                'COMPANION': {'all_dialogs': ['POST', 'JOIN', 'POST25', 'JOIN25']}})
            path.write_text('''2DA V1.0
NONE
FILE 25FILE
COMPANION BANTER BANTER25
EMPTY NONE ***
''')
            self.assertEqual(read_dialogue_table(path, 'INTERDIA'), {
                'COMPANION': {'all_dialogs': ['BANTER', 'BANTER25']}})

    def test_cli_resolves_only_mod_speakers_using_external_game_tables(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mod, game = root / 'mod', root / 'game'
            mod.mkdir(); game.mkdir()
            (mod / 'dialogue.d').write_text('''BEGIN LOCAL
IF ~~ THEN BEGIN state SAY @1 IF ~~ THEN EXIT END
APPEND JOINED
IF ~~ THEN BEGIN state SAY @2 IF ~~ THEN EXIT END
END
''')
            self.cre(mod / 'local.cre', dialog='LOCAL', gender=2)
            self.cre(game / 'COMP.CRE', dialog='INITIAL', death_var='COMPANION')
            self.cre(game / 'UNUSED.CRE', dialog='UNUSED', death_var='UNUSED')
            table = root / 'PDIALOG.2DA'
            table.write_text('''2DA V1.0
NONE
POST_DIALOG_FILE JOIN_DIALOG_FILE DREAM_SCRIPT_FILE
COMPANION POST JOINED DREAM
UNUSED UNUSED UNUSEDJ UNUSEDD
''')
            output = root / 'actors.csv'
            result = subprocess.run([
                sys.executable, str(SCRIPTS / 'extract_actors_using_grammar.py'),
                str(mod), '--cre-folder', str(mod), '--cre-folder', str(game),
                '--pdialog-file', str(table), '--csv-output', str(output)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, '')
            with output.open(newline='') as handle:
                self.assertEqual(dict(csv.reader(handle)), {'LOCAL': 'FEMALE', 'JOINED': 'MALE'})
            self.assertIn('retained 2 matching resources', result.stdout)


if __name__ == '__main__':
    unittest.main()
