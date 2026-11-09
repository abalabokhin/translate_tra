"""TP2-derived fallbacks, conservative exclusions and English-preserving export."""
import contextlib
import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from weidu_usage import WeiduUsage, tokenize
from parse_d_grammar import ImprovedGrammarDialogueParser
from update_tra_from_csv import TraUpdater


class WeiduUsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mod = self.root / 'mod'
        self.tra = self.mod / 'languages/english'
        self.dialogue = self.mod / 'dialogue'
        self.tra.mkdir(parents=True)
        self.dialogue.mkdir()
        self.tp2 = self.mod / 'main.tp2'
        self.common = self.tra / 'common.tra'
        self.common.write_text('@0=~Install~ @1=~Shared~ @2=~Game~ @3=~Unreferenced~')
        self.npc = self.dialogue / 'NPC.d'

    def script(self, body='', fallbacks='~mod/languages/english/common.tra~'):
        self.tp2.write_text(f'''BACKUP ~mod/backup~ AUTHOR ~author@example.com~
LANGUAGE ~English~ ~english~ {fallbacks}
{body}
''')

    def analyze(self):
        return WeiduUsage(self.tp2, 'english', self.tra).analyze()

    def test_lexer_ignores_nested_comments_and_preserves_literal_strings(self):
        tokens = tokenize('/* @99 /* @98 */ */ PRINT @1 // @97\r\n'
                          'PRINT ~@2 PRINT @3~ PRINT "text" PRINT %more% PRINT ~~~~~long~~~~~')
        self.assertEqual([t.value for t in tokens if t.kind == 'ref'], ['@1'])
        self.assertEqual([t.value for t in tokens if t.kind == 'string'],
                         ['@2 PRINT @3', 'text', 'more', 'long'])

    def test_language_declared_non_setup_filename_is_used(self):
        self.script('COMPILE ~mod/dialogue/NPC.d~')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN state SAY @2 IF ~~ THEN EXIT END')
        usage = self.analyze()
        path, entry = usage.resolve(self.npc, 2)
        self.assertEqual(path, self.common)
        self.assertEqual(entry.variants[0].text, 'Game')
        self.assertTrue(usage.complete)

    def test_corresponding_file_wins_case_insensitively_and_falls_back_per_entry(self):
        corresponding = self.tra / 'npc.TRA'
        corresponding.write_text('@2=~Local~')
        self.script('COMPILE ~MOD/DIALOGUE/npc.D~')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN state SAY @2 IF ~~ THEN EXIT END')
        usage = self.analyze()
        self.assertEqual(usage.resolve(self.npc, 2)[0], corresponding)
        self.assertEqual(usage.resolve(self.npc, 1)[0], self.common)

    def test_multiple_language_files_follow_load_order(self):
        other = self.tra / 'other.tra'
        other.write_text('@2=~Override~')
        self.script(fallbacks='~mod/languages/english/common.tra~ ~mod/languages/english/other.tra~')
        usage = self.analyze()
        self.assertEqual(usage.resolve(self.npc, 2)[0], other)
        self.assertEqual(usage.resolve(self.npc, 1)[0], self.common)

    def test_other_languages_are_not_mixed_into_english_fallbacks(self):
        self.script()
        self.tp2.write_text(self.tp2.read_text() +
                           'LANGUAGE ~Russian~ ~russian~ ~missing/russian.tra~\n')
        self.assertTrue(self.analyze().complete)

    def test_include_reinclude_and_load_tra_at_compile_site(self):
        library = self.mod / 'lib'
        library.mkdir()
        (library / 'one.tph').write_text('INCLUDE ~%MOD_FOLDER%/lib/two.tpa~')
        (library / 'two.tpa').write_text('PRINT @0\n')
        alternate = self.tra / 'alternate.tra'
        alternate.write_text('@2=~Later context~')
        self.script('''INCLUDE ~%MOD_FOLDER%/lib/one.tph~
LOAD_TRA ~mod/languages/english/alternate.tra~
COMPILE ~mod/dialogue/NPC.d~
REINCLUDE ~mod/lib/two.tpa~
''')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN state SAY @2 IF ~~ THEN EXIT END')
        usage = self.analyze()
        self.assertEqual(usage.resolve(self.npc, 2)[0], alternate)
        self.assertIn((self.common, 0), usage.excluded)
        self.assertEqual(len(usage.sources), 3)

    def test_compile_using_adds_an_explicit_fallback(self):
        alternate = self.tra / 'alternate.tra'
        alternate.write_text('@2=~Using context~')
        self.script('COMPILE ~mod/dialogue/NPC.d~ USING ~mod/languages/english/alternate.tra~')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN state SAY @2 IF ~~ THEN EXIT END')
        self.assertEqual(self.analyze().resolve(self.npc, 2)[0], alternate)

    def test_installer_only_is_excluded_but_shared_game_and_unused_entries_are_kept(self):
        self.script('''BEGIN @0
PRINT @1
COMPILE ~mod/dialogue/NPC.d~
''')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN state SAY @1 IF ~~ THEN EXIT END')
        usage = self.analyze()
        self.assertEqual(usage.excluded, {(self.common, 0)})
        self.assertNotIn((self.common, 3), usage.excluded)

    def test_say_item_name_and_unknown_macro_parameter_are_retained(self):
        self.script('''PRINT @1
SAY NAME1 @1
PRINT @2
LPF custom STR_VAR message = @2 END
''')
        self.assertEqual(self.analyze().excluded, set())

    def test_baf_usage_protects_shared_entry_without_building_baf_dialogue_csvs(self):
        baf = self.mod / 'scene.baf'
        baf.write_text('IF True() THEN RESPONSE #100 DisplayStringHead(Myself,@1) END')
        self.script('PRINT @1\nCOMPILE ~mod/scene.baf~')
        self.assertEqual(self.analyze().excluded, set())

    def test_missing_or_dynamic_include_disables_exclusions(self):
        for statement in ('INCLUDE ~mod/missing.tph~', 'INCLUDE ~%unknown%/file.tph~'):
            with self.subTest(statement=statement):
                self.script('PRINT @0\n' + statement)
                usage = self.analyze()
                self.assertFalse(usage.complete)
                self.assertEqual(usage.excluded, set())
                self.assertTrue(usage.warnings)

    def test_missing_reference_is_reported_and_disables_exclusions(self):
        self.script('PRINT @0\nSAY NAME1 @999')
        usage = self.analyze()
        self.assertFalse(usage.complete)
        self.assertIn('@999', usage.unresolved[0])
        self.assertEqual(usage.excluded, set())

    def test_embedded_references_are_uncertain_and_retained(self):
        self.script('PRINT @1\nOUTER_SPRINT code ~SAY NAME1 @1~')
        self.assertEqual(self.analyze().excluded, set())

    def test_component_and_installation_error_messages_can_be_excluded(self):
        self.script('BEGIN @0\nREQUIRE_PREDICATE (GAME_IS ~bg2ee~) @1\nFAIL @2')
        self.assertEqual(self.analyze().excluded,
                         {(self.common, 0), (self.common, 1), (self.common, 2)})

    def test_variable_paths_and_windows_separators(self):
        self.script('''OUTER_SPRINT lib ~mod/lib~
INCLUDE ~%lib%\\test.tph~
''')
        (self.mod / 'lib').mkdir()
        (self.mod / 'lib/test.tph').write_text('PRINT @0')
        self.assertTrue(self.analyze().complete)

    def test_include_cycle_does_not_recurse_or_exclude(self):
        self.script('PRINT @0\nINCLUDE ~mod/cycle.tph~')
        (self.mod / 'cycle.tph').write_text('INCLUDE ~mod/cycle.tph~')
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertEqual(len(usage.sources), 2)

    def test_conditional_load_tra_is_reported_instead_of_guessing_a_context(self):
        other = self.tra / 'other.tra'
        other.write_text('@2=~Conditional override~')
        self.script('''PRINT @0
ACTION_IF unknown BEGIN
LOAD_TRA ~mod/languages/english/other.tra~
END
COMPILE ~mod/dialogue/NPC.d~
''')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN state SAY @2 IF ~~ THEN EXIT END')
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertEqual(usage.usage[(self.common, 2)], {'game'})
        self.assertEqual(usage.usage[(other, 2)], {'game'})
        with self.assertRaisesRegex(ValueError, 'conflicting fallback definitions'):
            usage.resolve(self.npc, 2)

    def test_builder_uses_real_fallback_origin_and_preserves_female_source(self):
        self.common.write_text('@0=~Installer~ @1=~Fallback male~ ~Fallback female~ @2=~Unused~')
        self.script('PRINT @0\nCOMPILE ~mod/dialogue/NPC.d~')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN state SAY @1 IF ~~ THEN EXIT END')
        builder = ImprovedGrammarDialogueParser(str(self.dialogue), str(self.tra), str(self.tp2))
        output = self.root / 'csv'
        with contextlib.redirect_stdout(io.StringIO()):
            builder.process_all_d_files()
            builder.write_csv_files(str(output))
            builder.write_unused_lines_csv(str(output))
        dialogue = next(p for p in output.glob('*.csv') if not p.name.startswith('_'))
        with dialogue.open() as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]['Additional_Info'], 'TRA:common.tra:@1')
        self.assertEqual(rows[0]['Source_Female_Text'], 'Fallback female')
        with (output / '_unused_tra_lines.csv').open() as handle:
            unused = list(csv.DictReader(handle))
        self.assertEqual([row['Reference'] for row in unused], ['common.tra:@2'])

    def test_without_tp2_legacy_setup_fallback_still_works(self):
        (self.tra / 'SETUP.TRA').write_text('@2=~Fallback~')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN state SAY @2 IF ~~ THEN EXIT END')
        builder = ImprovedGrammarDialogueParser(str(self.dialogue), str(self.tra))
        with contextlib.redirect_stdout(io.StringIO()):
            _, lines, _ = builder.parse_d_file(str(self.npc))
        self.assertEqual(lines[0].source_info, 'TRA:SETUP.TRA:@2')

    def test_csv_to_tra_roundtrip_keeps_excluded_entries_in_english(self):
        self.script('PRINT @0')
        usage = self.analyze()
        self.assertEqual(usage.excluded, {(self.common, 0)})
        folder = self.root / 'translated'
        folder.mkdir()
        with (folder / '_unused_tra_lines.csv').open('w', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['Reference', 'English_Text', 'Russian_Male', 'Russian_Female'])
            writer.writerow(['common.tra:@2', 'Game', 'Игра', 'Игра'])
        updater = TraUpdater(str(self.tra), str(folder), str(self.root / 'russian'))
        with contextlib.redirect_stdout(io.StringIO()):
            updater.load_translations_from_csvs()
            updater.update_all_tra_files()
        result = (self.root / 'russian/common.tra').read_text()
        self.assertIn('@0=~Install~', result)
        self.assertIn('Игра', result)

    def test_unquoted_language_directory_is_supported(self):
        self.tp2.write_text('LANGUAGE "English" ENGLISH ~mod/languages/english/common.tra~\nPRINT @0')
        self.assertTrue(self.analyze().complete)

    def test_english_name_wins_when_another_language_reuses_english_directory(self):
        self.script('PRINT @0')
        self.tp2.write_text(self.tp2.read_text() +
                           'LANGUAGE ~Russian~ ~english~ ~missing/russian.tra~')
        self.assertEqual(self.analyze().default_fallbacks, [self.common])

    def test_english_revision_is_selected_in_declaration_order(self):
        self.tp2.write_text('''LANGUAGE ~English revised~ ~english_revision~ ~mod/languages/english/common.tra~
LANGUAGE ~English original~ ~english_original~ ~missing/original.tra~
PRINT @0
''')
        self.assertEqual(self.analyze().language, 'english_revision')

    def test_unused_function_body_is_not_executed(self):
        self.script('''DEFINE_ACTION_FUNCTION never_called BEGIN
INCLUDE ~missing.tph~
LOAD_TRA ~missing.tra~
COMPILE ~missing.d~
END
PRINT @0
''')
        self.assertTrue(self.analyze().complete)

    def test_called_function_resolves_string_parameters(self):
        helper = self.mod / 'helper.tph'
        helper.write_text('PRINT @0')
        self.script('''DEFINE_ACTION_FUNCTION load_helper STR_VAR file=~~ BEGIN
INCLUDE ~%file%~
END
LAF load_helper STR_VAR file=~mod/helper.tph~ END
''')
        self.assertIn((self.common, 0), self.analyze().excluded)

    def test_known_parameter_condition_does_not_overwrite_explicit_path(self):
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN state SAY @2 IF ~~ THEN EXIT END')
        self.script('''DEFINE_ACTION_FUNCTION compile_one STR_VAR root=~~ BEGIN
ACTION_IF ~%root%~ STRING_EQUAL_CASE ~~ BEGIN
OUTER_SPRINT root ~missing~
END
COMPILE ~%root%/NPC.d~
END
LAF compile_one STR_VAR root=~mod/dialogue~ END
''')
        self.assertTrue(self.analyze().complete)

    def test_evaluate_buffer_after_filename_and_language_placeholder(self):
        alternate = self.tra / 'other.tra'
        alternate.write_text('@2=~Override~')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN state SAY @2 IF ~~ THEN EXIT END')
        self.script('COMPILE ~mod/dialogue/NPC.d~ EVALUATE_BUFFER USING ~mod/languages/%s/other.tra~')
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertEqual(usage.resolve(self.npc, 2)[0], alternate)

    def test_statement_local_using_resolves_journal_and_tlk_patch_references(self):
        other = self.tra / 'journal.tra'
        other.write_text('@8=~Journal~ @9=~Title~')
        self.script('''ADD_JOURNAL @8 USING ~mod/languages/%s/journal.tra~
STRING_SET 123 @9 USING ~mod/languages/english/journal.tra~
''')
        usage = self.analyze()
        self.assertTrue(usage.complete, usage.unresolved)
        self.assertEqual(usage.usage[(other, 8)], {'unknown'})
        self.assertEqual(usage.usage[(other, 9)], {'unknown'})

    def test_inline_baf_and_bare_extend_destination(self):
        self.script('''<<<<<<<< .../scene.baf
IF True() THEN RESPONSE #100 DisplayStringHead(Myself,@1) END
>>>>>>>>
PRINT @1
EXTEND_TOP NPC.bcs ~.../scene.baf~
''')
        usage = self.analyze()
        self.assertTrue(usage.complete, usage.warnings)
        self.assertNotIn((self.common, 1), usage.excluded)

    def test_generated_inline_copy_evaluates_forwarded_string_parameter(self):
        self.script('''DEFINE_ACTION_FUNCTION emit STR_VAR input=~~ BEGIN
<<<<<<<< temp_file
%input%
>>>>>>>>
COPY - temp_file ~mod/generated.baf~ EVALUATE_BUFFER
COMPILE ~mod/generated.baf~
END
OUTER_SPRINT input ~IF True() THEN RESPONSE #100 DisplayStringHead(Myself,@1) END~
LAF emit STR_VAR input END
PRINT @1
''')
        usage = self.analyze()
        self.assertTrue(usage.complete, usage.warnings)
        self.assertEqual(usage.usage[(self.common, 1)], {'game', 'unknown', 'installer'})

    def test_copied_language_workspace_maps_to_original_sources(self):
        self.script('''COPY ~mod/languages/english~ ~generated/english~
LOAD_TRA ~generated/english/common.tra~
PRINT @0
''')
        self.assertTrue(self.analyze().complete)

    def test_charset_out_path_maps_to_original_sources(self):
        self.script('''LAF HANDLE_CHARSETS STR_VAR
tra_path=~mod/languages~ out_path=~generated~ END
LOAD_TRA ~generated/english/common.tra~
PRINT @0
''')
        self.assertTrue(self.analyze().complete)

    def test_macro_definition_uses_caller_variables_without_end_at_callsite(self):
        (self.mod / 'helper.tph').write_text('PRINT @0')
        self.script('''DEFINE_ACTION_MACRO load_one BEGIN INCLUDE ~%file%~ END
OUTER_SPRINT file ~mod/helper.tph~
LAM load_one
''')
        self.assertTrue(self.analyze().complete)

    def test_function_name_with_hash_and_numeric_at_reference(self):
        self.script('''DEFINE_ACTION_FUNCTION f#text INT_VAR number=0 BEGIN
OUTER_SPRINT value (AT number)
END
LAF f#text INT_VAR number=2 END
PRINT @2
''')
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertNotIn((self.common, 2), usage.excluded)

    def test_readonly_analysis_accepts_duplicate_and_reference_valued_tra(self):
        self.common.write_text('@0=~Old~ @0=~New~ @1=#123 @2=@0')
        self.script('PRINT @0\nSAY NAME1 @1')
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertEqual(usage.table(self.common)[0].variants[0].text, 'New')

    def test_finite_include_filename_domain_is_scanned(self):
        (self.mod / 'lib').mkdir()
        (self.mod / 'lib/one.tph').write_text('PRINT @0')
        (self.mod / 'lib/two.tph').write_text('SAY NAME1 @1')
        self.script('INCLUDE ~mod/lib/%file%.tph~')
        self.assertTrue(self.analyze().complete)

    def test_unevaluated_game_conditions_do_not_hide_possible_game_use(self):
        self.script('''PRINT @1
ACTION_IF GAME_IS ~bg2ee~ BEGIN SAY NAME1 @1 END
''')
        self.assertNotIn((self.common, 1), self.analyze().excluded)


    def test_function_named_include_does_not_become_native_command(self):
        self.script("""DEFINE_ACTION_FUNCTION include STR_VAR file=~~ BEGIN
PRINT @0
END
LAF include STR_VAR file=~not-an-include.tph~ END
""")
        self.assertTrue(self.analyze().complete)

    def test_function_arguments_preserve_game_reference(self):
        self.script('PRINT @2\nLAF unknown_helper INT_VAR text=@2 END')
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertNotIn((self.common, 2), usage.excluded)

    def test_inline_filename_binds_after_variable_assignment(self):
        self.script("""<<<<<<<< .../inlined/%script%.baf
IF True() THEN RESPONSE #100 DisplayStringHead(Myself,@2) END
>>>>>>>>
OUTER_SPRINT script ~late_name~
COMPILE ~.../inlined/%script%.baf~ EVAL
""")
        usage = self.analyze()
        self.assertTrue(usage.complete, usage.warnings)
        self.assertIn((self.common, 2), usage.usage)

    def test_absolute_virtual_source_can_be_included(self):
        virtual = self.mod / 'generated.d'
        self.script(f"""<<<<<<<< generated.d
BEGIN NPC IF ~~ THEN BEGIN s SAY @2 IF ~~ THEN EXIT END
>>>>>>>>
INCLUDE ~{virtual}~
""")
        self.assertTrue(self.analyze().complete)

    def test_with_tra_has_local_scope_and_compile_does_not_clobber_using_map(self):
        other = self.tra / 'other.tra'
        other.write_text('@8=~Other~')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN s SAY @2 IF ~~ THEN EXIT END')
        self.script("""COMPILE ~mod/dialogue/NPC.d~ USING ~mod/languages/english/common.tra~
WITH_TRA ~mod/languages/english/other.tra~ BEGIN SAY NAME1 @8 END
STRING_SET 123 @8 USING ~mod/languages/english/other.tra~
SAY NAME1 @2
""")
        usage = self.analyze()
        self.assertTrue(usage.complete, usage.unresolved)
        self.assertIn((other, 8), usage.usage)
        self.assertIn((self.common, 2), usage.usage)

    def test_missing_optional_tra_matches_weidu_skip_semantics(self):
        self.script('LOAD_TRA ~mod/languages/english/absent.tra~\nSAY NAME1 @2')
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertTrue(usage.notes)

    def test_optional_compile_does_not_require_absent_source(self):
        self.script('COMPILE IF_EXISTS ~mod/dialogue/absent.d~')
        self.assertTrue(self.analyze().complete)

    def test_recursive_variable_expansion_terminates(self):
        self.script()
        usage = self.analyze()
        usage.variables.update(a='%b%', b='%a%')
        self.assertIn('%', usage.expand('%a%'))

    def test_numeric_function_guard_skips_default_negative_reference(self):
        self.script("""DEFINE_DIMORPHIC_FUNCTION text INT_VAR number=-1 BEGIN
ACTION_IF number > 0 BEGIN OUTER_SPRINT value (AT number) END
END
LAF text END
""")
        self.assertTrue(self.analyze().complete)

    def test_export_preserves_native_tlk_and_alias_entries(self):
        self.common.write_text('@0=#123\n@1=@2\n@2=~Game~\n')
        folder = self.root / 'translated'
        folder.mkdir()
        with (folder / '_unused_tra_lines.csv').open('w', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['Reference', 'English_Text', 'Russian_Male', 'Russian_Female'])
            writer.writerow(['common.tra:@2', 'Game', 'Игра', 'Игра'])
        updater = TraUpdater(str(self.tra), str(folder), str(self.root / 'russian'))
        with contextlib.redirect_stdout(io.StringIO()):
            updater.load_translations_from_csvs()
            updater.update_all_tra_files()
        text = (self.root / 'russian/common.tra').read_text()
        self.assertIn('@0=#123', text)
        self.assertIn('@1=@2', text)
        self.assertIn('Игра', text)


    def test_end_variable_does_not_terminate_function_definition(self):
        self.script("""DEFINE_ACTION_FUNCTION buffer_edit BEGIN
SET end=INDEX_BUFFER (~text~)
READ_ASCII 0 data (end - 0)
INSERT_BYTES end 4
WRITE_ASCIIE end ~text~
SAY NAME1 @2
END
PRINT @2
""")
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertIn((self.common, 2), usage.excluded)

    def test_quoted_plus_before_end_is_not_an_offset_expression(self):
        self.script('DEFINE_ACTION_FUNCTION f BEGIN SPRINT plus ~+~ END\nLAF f END')
        self.assertTrue(self.analyze().complete)

    def test_charset_reload_array_loads_additional_fallback(self):
        journal = self.tra / 'Journal.tra'
        journal.write_text('@8=~Journal~')
        self.script("""ACTION_DEFINE_ARRAY reload BEGIN common Journal END
LAF HANDLE_CHARSETS STR_VAR tra_path=~mod/languages~ reload_array=reload END
ADD_JOURNAL @8
""")
        usage = self.analyze()
        self.assertTrue(usage.complete, usage.unresolved)
        self.assertIn((journal, 8), usage.usage)

    def test_known_false_file_test_short_circuits_unknown_game_condition(self):
        self.script("""ACTION_IF GAME_IS ~bg2ee~ AND FILE_EXISTS ~mod/absent.tph~ BEGIN
INCLUDE ~mod/absent.tph~
END
""")
        self.assertTrue(self.analyze().complete)

    def test_local_variable_named_load_is_not_an_include(self):
        self.script('LOCAL_SPRINT load ~~')
        self.assertTrue(self.analyze().complete)


    def test_inline_terminator_can_follow_content_on_same_line(self):
        self.script("""<<<<<<<< generated.tph
SAY NAME1 @2 >>>>>>>>
INCLUDE ~generated.tph~
""")
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertIn((self.common, 2), usage.usage)

    def test_false_component_prerequisite_skips_body_but_not_next_component(self):
        self.script("""BEGIN @0
REQUIRE_PREDICATE (GAME_IS ~bg2ee~ AND FILE_EXISTS ~mod/absent.tph~) @1
INCLUDE ~mod/absent.tph~
BEGIN @1
SAY NAME1 @2
""")
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertIn((self.common, 2), usage.usage)


    def test_native_tlk_state_is_omitted_and_alias_uses_literal_target(self):
        self.common.write_text('@0=#123\n@1=@2\n@2=~Game~\n')
        self.script('COMPILE ~mod/dialogue/NPC.d~')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN s SAY @1 IF ~~ THEN GOTO t END '
                            'IF ~~ THEN BEGIN t SAY @0 IF ~~ THEN GOTO u END '
                            'IF ~~ THEN BEGIN u SAY @2 IF ~~ THEN EXIT END')
        output = self.root / 'csv'
        builder = ImprovedGrammarDialogueParser(str(self.dialogue), str(self.tra),
                                                tp2_file=str(self.tp2))
        with contextlib.redirect_stdout(io.StringIO()):
            builder.process_all_d_files()
            builder.write_csv_files(str(output))
        rows = []
        for file in output.glob('*.csv'):
            if not file.name.startswith('_'):
                with file.open() as handle:
                    rows.extend(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['Additional_Info'] for r in rows}, {'TRA:common.tra:@2'})
        self.assertTrue(rows[1]['Predecessors'])
        self.assertTrue(all(r['Dialogue_Text'] == 'Game' for r in rows))


    def test_action_and_patch_functions_have_separate_namespaces(self):
        self.script("""DEFINE_PATCH_FUNCTION helper RET table BEGIN
SPRINT table ~mod/languages/english/common.tra~
END
DEFINE_ACTION_FUNCTION helper RET table BEGIN
LPF helper RET table END
END
LAF helper RET selected=table END
LOAD_TRA ~%selected%~
SAY NAME1 @2
""")
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertEqual(usage.variables['selected'], 'mod/languages/english/common.tra')

    def test_ret_alias_is_not_passed_as_input_parameter(self):
        self.script("""DEFINE_ACTION_FUNCTION helper STR_VAR value=~correct~ RET value BEGIN END
OUTER_SPRINT selected ~wrong~
LAF helper RET selected=value END
""")
        self.assertEqual(self.analyze().variables['selected'], 'correct')

    def test_copy_follows_every_source_destination_pair(self):
        (self.mod / 'one.tph').write_text('PRINT @0')
        (self.mod / 'two.tph').write_text('SAY NAME1 @2')
        self.script("""COPY - ~mod/one.tph~ ~generated/one.tph~
~mod/two.tph~ ~generated/two.tph~
INCLUDE ~generated/two.tph~
""")
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertIn((self.common, 2), usage.usage)

    def test_static_foreach_and_indirect_variable_paths(self):
        (self.mod / 'one.tph').write_text('PRINT @0')
        (self.mod / 'two.tph').write_text('SAY NAME1 @2')
        self.script("""OUTER_SPRINT first ~mod/one.tph~
OUTER_SPRINT second ~mod/two.tph~
ACTION_FOR_EACH key IN first second BEGIN
INCLUDE ~%%key%%~
END
""")
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertIn((self.common, 2), usage.usage)
        self.assertIn((self.common, 0), usage.excluded)

    def test_known_match_selects_only_applicable_branch(self):
        self.script("""ACTION_MATCH ~english~ WITH
english BEGIN PRINT @0 END
russian BEGIN INCLUDE ~missing.tph~ END
DEFAULT INCLUDE ~also-missing.tph~
END
""")
        self.assertTrue(self.analyze().complete)

    def test_single_statement_else_does_not_consume_next_component(self):
        self.script("""ACTION_IF GAME_IS ~bg2ee~ BEGIN OUTER_SET value=1 END ELSE OUTER_SET value=0
BEGIN @0
PRINT @1
""")
        self.assertTrue(self.analyze().complete)


    def test_function_locals_do_not_leak_into_later_compilation_paths(self):
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN s SAY @2 IF ~~ THEN EXIT END')
        self.script("""OUTER_SPRINT root ~mod/dialogue~
DEFINE_ACTION_FUNCTION helper BEGIN OUTER_SPRINT root ~missing~ END
LAF helper END
COMPILE ~%root%/NPC.d~
""")
        self.assertTrue(self.analyze().complete)

    def test_compiled_baf_is_available_to_later_extend_as_native_tlk(self):
        source = self.mod / 'source.baf'
        source.write_text('IF True() THEN RESPONSE #100 DisplayStringHead(Myself,@2) END')
        self.script('COMPILE ~mod/source.baf~\nEXTEND_BOTTOM NPC.bcs ~override/source.bcs~')
        usage = self.analyze()
        self.assertTrue(usage.complete, usage.warnings)
        self.assertIn((self.common, 2), usage.usage)

    def test_literal_index_prevents_appending_second_extension(self):
        self.script("""OUTER_SPRINT file ~mod/helper.tph~
ACTION_IF INDEX (~\\.~ ~%file%~)<0 BEGIN OUTER_SPRINT file ~%file%.tph~ END
INCLUDE ~%file%~
""")
        (self.mod / 'helper.tph').write_text('PRINT @0')
        self.assertTrue(self.analyze().complete)


    def test_explicit_string_argument_is_literal_even_if_same_named_variable_exists(self):
        self.script("""OUTER_SPRINT english ~wrong~
DEFINE_ACTION_FUNCTION helper STR_VAR name=~~ RET name BEGIN END
LAF helper STR_VAR name=english RET selected=name END
""")
        self.assertEqual(self.analyze().variables['selected'], 'english')

    def test_arguments_use_caller_values_before_defaults_are_applied(self):
        self.script("""OUTER_SPRINT file ~correct~
DEFINE_ACTION_FUNCTION helper STR_VAR file=~~ RET file BEGIN END
LAF helper STR_VAR file=~%file%~ RET selected=file END
""")
        self.assertEqual(self.analyze().variables['selected'], 'correct')


    def test_numeric_prefixed_identifier_is_one_token_in_file_loop(self):
        (self.mod / 'bg2_2DA.tph').write_text('PRINT @0')
        self.script('ACTION_FOR_EACH kind IN 2DA BEGIN INCLUDE ~mod/bg2_%kind%.tph~ END')
        self.assertTrue(self.analyze().complete)

    def test_static_associative_array_drives_source_include_loop(self):
        (self.mod / 'one.tph').write_text('PRINT @0')
        (self.mod / 'two.tph').write_text('SAY NAME1 @2')
        self.script("""ACTION_DEFINE_ASSOCIATIVE_ARRAY files BEGIN one=>first two=>second END
ACTION_PHP_EACH files AS name=>value BEGIN INCLUDE ~mod/%name%.tph~ END
""")
        usage = self.analyze()
        self.assertTrue(usage.complete)
        self.assertIn((self.common, 2), usage.usage)


    def test_string_comparison_case_flag_matches_native_weidu(self):
        self.script()
        usage = self.analyze()
        self.assertFalse(usage.condition(tokenize('~English~ STR_EQ ~english~'), self.tp2))
        self.assertTrue(usage.condition(tokenize('~English~ STR_EQ_CASE ~english~'), self.tp2))


    def test_journal_references_are_marked_by_their_consumers(self):
        self.common.write_text('@1=~I spoke.~ @2=~We spoke.~ @3=~Reward~ @4=~Title~')
        self.npc.write_text('BEGIN NPC IF ~~ THEN BEGIN s SAY @3 IF ~~ THEN JOURNAL @1 EXIT END')
        baf = self.mod / 'journal.baf'
        baf.write_text('IF True() THEN RESPONSE #100 AddJournalEntry(@2,QUEST) '
                       'EraseJournalEntry(@1) DisplayStringHead(Player1,@3) END')
        self.script('COMPILE ~mod/journal.baf~ ~mod/dialogue/NPC.d~\nADD_JOURNAL TITLE (@4) @1 @2')
        usage = self.analyze()
        self.assertTrue(usage.complete, usage.unresolved)
        self.assertEqual(usage.journal_entries, {(self.common, n) for n in (1, 2, 4)})

    def test_catchall_exports_journal_role_without_changing_reference(self):
        self.script('ADD_JOURNAL @2')
        builder = ImprovedGrammarDialogueParser(str(self.dialogue), str(self.tra), tp2_file=str(self.tp2))
        output = self.root / 'csv'
        output.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            builder.process_all_d_files()
            builder.write_unused_lines_csv(str(output))
        with (output / '_unused_tra_lines.csv').open() as handle:
            rows = {r['Reference']: r for r in csv.DictReader(handle)}
        self.assertEqual(rows['common.tra:@2']['Text_Type'], 'journal')
        self.assertEqual(rows['common.tra:@3']['Text_Type'], '')


if __name__ == '__main__':
    unittest.main()
