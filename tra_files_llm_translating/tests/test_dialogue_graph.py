"""Dialogue connectivity and actor-local state labels, independent of LLMs."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from parse_d_grammar import ImprovedGrammarDialogueParser


class DialogueGraphTests(unittest.TestCase):
    def parse_mod(self, sources, translations=None, installer=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            d, tra = root / 'd', root / 'english'
            d.mkdir()
            tra.mkdir()
            for name, content in sources.items():
                path = d / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            for name, content in (translations or {}).items():
                (tra / name).write_text(content)
            tp2 = root / 'main.tp2'
            if installer:
                tp2.write_text(installer)
            parser = ImprovedGrammarDialogueParser(str(d), str(tra), str(tp2) if installer else None)
            with contextlib.redirect_stdout(io.StringIO()):
                parser.process_all_d_files()
            groups = parser.all_dialogues['combined']
            lines = [line for group in groups for line in group]
            self.assertEqual(len(lines), len({line.line_id for line in lines}))
            return parser, {line.text: line for line in lines}, groups

    def parse(self, source):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'fixture.d'
            path.write_text(source)
            parser = ImprovedGrammarDialogueParser(str(root), str(root))
            with contextlib.redirect_stdout(io.StringIO()):
                states, lines, groups = parser.parse_d_file(str(path))
        self.assertEqual(len({line.line_id for line in lines}), len(lines))
        return states, {line.text: line for line in lines}, groups

    def assert_edge(self, lines, source, target):
        self.assertIn(lines[source].line_id, lines[target].predecessors)
        self.assertIn(lines[target].line_id, lines[source].targets)

    def test_direct_extern_and_end_destination_connect_chain_states(self):
        for ending in ('EXTERN', 'END'):
            with self.subTest(ending=ending):
                _, lines, groups = self.parse(f'''CHAIN NPC first
~First.~
{ending} NPC second
CHAIN NPC second ~Second.~ EXIT
''')
                self.assertEqual(len(groups), 1)
                self.assert_edge(lines, 'First.', 'Second.')

    def test_extern_leaves_last_speaker_of_a_multi_speaker_chain(self):
        _, lines, groups = self.parse('''CHAIN FIRST first
~One.~
== SECOND ~Two.~ = ~Three.~
EXTERN THIRD next
CHAIN THIRD next ~Four.~ EXIT
''')
        self.assertEqual(len(groups), 1)
        for source, target in [('One.', 'Two.'), ('Two.', 'Three.'), ('Three.', 'Four.')]:
            self.assert_edge(lines, source, target)
        self.assertEqual(lines['Four.'].predecessors, [lines['Three.'].line_id])

    def test_replies_follow_their_own_targets_and_exit_stays_disconnected(self):
        _, lines, groups = self.parse('''CHAIN NPC first ~Question.~ END
++ ~Continue.~ EXTERN NPC next
++ ~Leave.~ EXIT
CHAIN NPC next ~Answer.~ EXIT
CHAIN NPC unrelated ~Independent.~ EXIT
''')
        self.assertEqual(len(groups), 2)
        self.assert_edge(lines, 'Question.', 'Continue.')
        self.assert_edge(lines, 'Continue.', 'Answer.')
        self.assertNotIn(lines['Leave.'].line_id, lines['Answer.'].predecessors)
        self.assertEqual(lines['Independent.'].predecessors, [])

    def test_same_chain_label_in_different_dialogues_does_not_merge(self):
        states, lines, groups = self.parse('''CHAIN FIRST same
~First start.~ == COMMENTER ~First comment.~ EXIT
CHAIN SECOND same
~Second start.~ == COMMENTER ~Second comment.~ EXIT
''')
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(states), 4)
        self.assertEqual(len({line.state_id for line in lines.values()}), 4)
        self.assert_edge(lines, 'First start.', 'First comment.')
        self.assert_edge(lines, 'Second start.', 'Second comment.')
        self.assertEqual(lines['Second comment.'].predecessors, [lines['Second start.'].line_id])

    def test_plain_state_labels_and_local_gotos_are_scoped_to_actor(self):
        _, lines, groups = self.parse('''BEGIN FIRST
IF ~~ THEN BEGIN start SAY ~First start.~ IF ~~ THEN GOTO next END
IF ~~ THEN BEGIN next SAY ~First end.~ IF ~~ THEN EXIT END
BEGIN SECOND
IF ~~ THEN BEGIN start SAY ~Second start.~ IF ~~ THEN GOTO next END
IF ~~ THEN BEGIN next SAY ~Second end.~ IF ~~ THEN EXIT END
''')
        self.assertEqual(len(groups), 2)
        self.assert_edge(lines, 'First start.', 'First end.')
        self.assert_edge(lines, 'Second start.', 'Second end.')
        self.assertEqual(lines['First end.'].predecessors, [lines['First start.'].line_id])

    def test_extern_chooses_named_actor_when_labels_are_identical(self):
        _, lines, groups = self.parse('''CHAIN FIRST start ~First start.~ EXTERN SECOND same
CHAIN FIRST same ~First isolated.~ EXIT
CHAIN SECOND same ~Second target.~ EXIT
''')
        self.assertEqual(len(groups), 2)
        self.assert_edge(lines, 'First start.', 'Second target.')
        self.assertEqual(lines['First isolated.'].predecessors, [])

    def test_plain_state_can_jump_to_chain_and_chain_back_to_plain_state(self):
        _, lines, groups = self.parse('''BEGIN NPC
IF ~~ THEN BEGIN first SAY ~First.~ IF ~~ THEN GOTO chain END
IF ~~ THEN BEGIN last SAY ~Last.~ IF ~~ THEN EXIT END
CHAIN NPC chain ~Middle.~ EXTERN NPC last
''')
        self.assertEqual(len(groups), 1)
        self.assert_edge(lines, 'First.', 'Middle.')
        self.assert_edge(lines, 'Middle.', 'Last.')

    def test_extending_existing_state_uses_same_actor_scoped_identity(self):
        _, lines, groups = self.parse('''BEGIN FIRST
IF ~~ THEN BEGIN same SAY ~First.~ IF ~~ THEN EXIT END
BEGIN SECOND
IF ~~ THEN BEGIN same SAY ~Second.~ IF ~~ THEN EXIT END
EXTEND_BOTTOM FIRST same
++ ~Reply.~ EXTERN SECOND same
END
''')
        self.assertEqual(len(groups), 1)
        self.assert_edge(lines, 'First.', 'Reply.')
        self.assert_edge(lines, 'Reply.', 'Second.')
        self.assertNotIn(lines['Second.'].line_id, lines['Reply.'].predecessors)

    def test_backward_chain_extern_and_cycle_resolve_after_all_states_are_read(self):
        _, lines, groups = self.parse('''CHAIN NPC first ~First.~ EXTERN NPC second
CHAIN NPC second ~Second.~ EXTERN NPC first
''')
        self.assertEqual(len(groups), 1)
        self.assert_edge(lines, 'First.', 'Second.')
        self.assert_edge(lines, 'Second.', 'First.')

    def test_cross_file_chain_extern_and_end_are_linked(self):
        for ending in ('EXTERN', 'END'):
            with self.subTest(ending=ending):
                parser, lines, groups = self.parse_mod({
                    'z_first.d': f'CHAIN FIRST start ~First.~ {ending} SECOND next',
                    'a_second.d': 'CHAIN SECOND next ~Second.~ EXIT'})
                self.assertEqual(len(groups), 1)
                self.assert_edge(lines, 'First.', 'Second.')
                self.assertEqual(parser.graph_report['cross_file_line_edges'], 1)
                self.assertEqual(parser.graph_report['external_targets'], [])

    def test_cross_file_plain_states_replies_and_exit_alternatives(self):
        _, lines, groups = self.parse_mod({
            'start.d': 'BEGIN FIRST IF ~~ THEN BEGIN s SAY ~Question.~ '
                       '++ ~Continue.~ EXTERN SECOND next ++ ~Leave.~ EXIT END',
            'end.d': 'BEGIN SECOND IF ~~ THEN BEGIN next SAY ~Answer.~ IF ~~ THEN EXIT END'})
        self.assertEqual(len(groups), 1)
        self.assert_edge(lines, 'Question.', 'Continue.')
        self.assert_edge(lines, 'Continue.', 'Answer.')
        self.assertNotIn(lines['Leave.'].line_id, lines['Answer.'].predecessors)

    def test_local_goto_can_target_same_dialogue_in_another_source(self):
        _, lines, groups = self.parse_mod({
            'first.d': 'BEGIN NPC IF ~~ THEN BEGIN a SAY ~First.~ IF ~~ THEN GOTO b END',
            'second.d': 'APPEND NPC IF ~~ THEN BEGIN b SAY ~Second.~ IF ~~ THEN EXIT END END'})
        self.assertEqual(len(groups), 1)
        self.assert_edge(lines, 'First.', 'Second.')

    def test_cross_file_cycle_and_multi_speaker_chain_last_line(self):
        _, lines, groups = self.parse_mod({
            'first.d': 'CHAIN FIRST start ~First.~ == COMMENTER ~Comment.~ EXTERN SECOND next',
            'second.d': 'CHAIN SECOND next ~Second.~ EXTERN FIRST start'})
        self.assertEqual(len(groups), 1)
        self.assert_edge(lines, 'First.', 'Comment.')
        self.assert_edge(lines, 'Comment.', 'Second.')
        self.assert_edge(lines, 'Second.', 'First.')

    def test_reused_actor_and_labels_remain_separate_by_file(self):
        _, lines, groups = self.parse_mod({
            'one.d': 'BEGIN NPC IF ~~ THEN BEGIN 0 SAY ~One start.~ IF ~~ THEN GOTO 1 END '
                     'IF ~~ THEN BEGIN 1 SAY ~One end.~ IF ~~ THEN EXIT END',
            'two.d': 'BEGIN NPC IF ~~ THEN BEGIN 0 SAY ~Two start.~ IF ~~ THEN GOTO 1 END '
                     'IF ~~ THEN BEGIN 1 SAY ~Two end.~ IF ~~ THEN EXIT END'})
        self.assertEqual(len(groups), 2)
        self.assert_edge(lines, 'One start.', 'One end.')
        self.assert_edge(lines, 'Two start.', 'Two end.')
        self.assertEqual(lines['Two end.'].predecessors, [lines['Two start.'].line_id])

    def test_extend_in_another_file_attaches_to_defined_state(self):
        _, lines, groups = self.parse_mod({
            'base.d': 'BEGIN NPC IF ~~ THEN BEGIN s SAY ~Question.~ ++ ~Original exit.~ EXIT END',
            'extension.d': 'EXTEND_BOTTOM NPC s ++ ~New reply.~ EXTERN OTHER answer END',
            'answer.d': 'BEGIN OTHER IF ~~ THEN BEGIN answer SAY ~Answer.~ IF ~~ THEN EXIT END'})
        self.assertEqual(len(groups), 1)
        self.assert_edge(lines, 'Question.', 'Original exit.')
        self.assert_edge(lines, 'Question.', 'New reply.')
        self.assert_edge(lines, 'New reply.', 'Answer.')
        self.assertNotIn(lines['Original exit.'].line_id, lines['Answer.'].predecessors)

    def test_automatic_extern_and_reply_alternatives_have_distinct_sources(self):
        _, lines, groups = self.parse_mod({
            'first.d': 'BEGIN NPC IF ~~ THEN BEGIN s SAY ~Question.~ '
                       'IF ~automatic~ THEN EXTERN OTHER answer ++ ~Leave.~ EXIT END',
            'second.d': 'BEGIN OTHER IF ~~ THEN BEGIN answer SAY ~Automatic answer.~ IF ~~ THEN EXIT END'})
        self.assertEqual(len(groups), 1)
        self.assert_edge(lines, 'Question.', 'Automatic answer.')
        self.assertNotIn(lines['Leave.'].line_id, lines['Automatic answer.'].predecessors)

    def test_cross_file_tra_provenance_is_not_confused_by_identical_ids(self):
        _, lines, groups = self.parse_mod({
            'first.d': 'CHAIN FIRST start @1 EXTERN SECOND next',
            'second.d': 'CHAIN SECOND next @1 EXIT'},
            {'first.tra': '@1=~First.~', 'second.tra': '@1=~Second.~'})
        self.assertEqual(len(groups), 1)
        self.assertEqual(lines['First.'].source_info, 'TRA:first.tra:@1')
        self.assertEqual(lines['Second.'].source_info, 'TRA:second.tra:@1')
        self.assert_edge(lines, 'First.', 'Second.')

    def test_missing_external_game_states_do_not_merge_unrelated_scenes(self):
        parser, _, groups = self.parse_mod({
            'one.d': 'CHAIN ONE start ~One.~ EXTERN BASEGAME 42',
            'two.d': 'CHAIN TWO start ~Two.~ EXTERN BASEGAME 42'})
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(parser.graph_report['external_targets']), 2)

    def test_ambiguous_external_symbol_is_reported_instead_of_guessed(self):
        with self.assertRaisesRegex(ValueError, 'ambiguous dialogue target TARGET:next'):
            self.parse_mod({'one.d': 'CHAIN ONE start ~One.~ EXTERN TARGET next',
                            'two.d': 'CHAIN TARGET next ~Two.~ EXIT',
                            'three.d': 'CHAIN TARGET next ~Three.~ EXIT'})

    def test_compilation_units_disambiguate_reused_external_labels(self):
        _, lines, groups = self.parse_mod({
            'one.d': 'CHAIN ONE start ~One.~ EXTERN TARGET next',
            'two.d': 'CHAIN TARGET next ~Two.~ EXIT',
            'three.d': 'CHAIN TARGET next ~Three.~ EXIT'},
            translations={'setup.tra': '@1=~Unused~'},
            installer='LANGUAGE ~English~ ~english~ ~english/setup.tra~\n'
                      'COMPILE ~d/one.d~ ~d/two.d~\nCOMPILE ~d/three.d~')
        self.assertEqual(len(groups), 2)
        self.assert_edge(lines, 'One.', 'Two.')
        self.assertEqual(lines['Three.'].predecessors, [])

    def test_nested_source_folders_are_linked(self):
        _, lines, groups = self.parse_mod({
            'soa/one.d': 'CHAIN ONE start ~One.~ EXTERN TWO next',
            'tob/two.d': 'CHAIN TWO next ~Two.~ EXIT'})
        self.assertEqual(len(groups), 1)
        self.assert_edge(lines, 'One.', 'Two.')

    def test_numeric_extern_to_complete_new_dialogue_uses_actual_state_index(self):
        _, lines, groups = self.parse_mod({
            'one.d': 'CHAIN ONE start ~One.~ EXTERN TARGET 0',
            'two.d': 'BEGIN TARGET IF ~~ THEN BEGIN entry SAY ~Two.~ IF ~~ THEN EXIT END'},
            translations={'setup.tra': '@1=~Unused~'},
            installer='LANGUAGE ~English~ ~english~ ~english/setup.tra~\n'
                      'COMPILE ~d/two.d~\nCOMPILE ~d/one.d~')
        self.assertEqual(len(groups), 1)
        self.assert_edge(lines, 'One.', 'Two.')


if __name__ == '__main__':
    unittest.main()
