"""TRA syntax regressions based on WeiDU documentation and its upstream grammar."""
import sys
import tempfile
import unittest
from itertools import product
from pathlib import Path

SCRIPTS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SCRIPTS))
from tra_format import parse_tra, read_text, replace_entry


class TraFormatTests(unittest.TestCase):
    def test_literal_gender_sound_and_line_ending_combinations(self):
        for delimiter, newline, male_sound, female_sound in product(
                ('~','"','%','~~~~~'), ('\n','\r\n','\r'), ('','[MALE]'), ('','[FEMALE]')):
            with self.subTest(delimiter=delimiter,newline=repr(newline),sounds=(male_sound,female_sound)):
                male=f'Zyxxara{newline}Qyzzorin'
                female=f'Vraxxala{newline}Thyzzorin'
                content=(f'@7 = {delimiter}{male}{delimiter} /* male */ {male_sound}'
                         f' // between variants{newline}'
                         f'{delimiter}{female}{delimiter} /* female */ {female_sound}{newline}'
                         '// final comment')
                entry=parse_tra(content)[7]
                self.assertEqual([v.text for v in entry.variants],[male,female])
                self.assertEqual([v.sound for v in entry.variants],[male_sound or None,female_sound or None])
                for v in entry.variants:
                    self.assertEqual(content[v.start:v.text_end],delimiter+v.text+delimiter)

    def test_single_literals_with_optional_sound_and_adjacent_entries(self):
        for delimiter,sound in product(('~','"','%','~~~~~'),('','[VOICE]','[]')):
            with self.subTest(delimiter=delimiter,sound=sound):
                entries=parse_tra(f'@1={delimiter}One{delimiter}{sound}@2={delimiter}Two{delimiter}')
                self.assertEqual(len(entries[1].variants),1)
                self.assertEqual(entries[1].variants[0].sound,sound or None)
                self.assertEqual(entries[2].variants[0].text,'Two')

    def test_comments_everywhere_and_fake_entries_are_not_text(self):
        content=('\ufeff/* outer @99=~Fake~ /* nested */ */\r'
                 '@1 /* before equals */ = // after equals\r'
                 '/* before text */ ~Zyxxara~ /* before sound */ [VOICE]\r'
                 '/* before female */ "Qyzzorin" /* before female sound */ [FVOICE]\r'
                 '// @98 = ~Fake~\r@2 = ~Thyzzorin~ // EOF comment')
        entries=parse_tra(content)
        self.assertEqual(list(entries),[1,2])
        self.assertEqual([v.text for v in entries[1].variants],['Zyxxara','Qyzzorin'])
        self.assertEqual([v.sound for v in entries[1].variants],['[VOICE]','[FVOICE]'])

    def test_comment_entry_sound_markers_inside_literals_are_content(self):
        text='// literal /* not a comment */ @9 = "Fake" [SOUND] %var% <PRO_SIRMAAM>'
        content='@1 = ~'+text+'~'
        self.assertEqual(parse_tra(content)[1].variants[0].text,text)
        text='Contains ~, " and %, plus ~~~~ but no closing delimiter'
        self.assertEqual(parse_tra('@1=~~~~~'+text+'~~~~~')[1].variants[0].text,text)

    def test_backslashes_are_literal_not_c_style_escapes(self):
        text=r'C:\mods\Zyxxara\file \n \t'
        self.assertEqual(parse_tra('@1 = "'+text+'"')[1].variants[0].text,text)
        with self.assertRaises(ValueError):parse_tra(r'@1="a\"b"')

    def test_concatenation_of_both_genders_preserves_comments_and_sound_spans(self):
        content=('@1 = ~Zy~ /* join male */ ^ "xxara" [MALE] '
                 '%Qyz% // join female\n ^ ~zorin~ /* sound */ [FEMALE]\n@2=~Tail~')
        entry=parse_tra(content)[1]
        self.assertEqual([v.text for v in entry.variants],['Zyxxara','Qyzzorin'])
        self.assertEqual([len(v.parts) for v in entry.variants],[2,2])
        updated=replace_entry(content,entry,'Новое','Новая')
        self.assertEqual([v.text for v in parse_tra(updated)[1].variants],['Новое','Новая'])
        for fragment in ('/* join male */','// join female','/* sound */','[MALE]','[FEMALE]','@2=~Tail~'):
            self.assertIn(fragment,updated)

    def test_empty_literals_and_empty_gender_variants(self):
        for delimiter in ('~','"','%','~~~~~'):
            with self.subTest(delimiter=delimiter):
                entry=parse_tra('@1='+delimiter*2+' [M] '+delimiter*2+' [F]')[1]
                self.assertEqual([v.text for v in entry.variants],['',''])
                self.assertEqual([v.sound for v in entry.variants],['[M]','[F]'])

    def test_bom_signed_ids_and_comments_before_equals(self):
        entries=parse_tra('\ufeff@-1 /* header */ = ~Negative~ @0=~Zero~ @007=~Seven~')
        self.assertEqual(list(entries),[-1,0,7])

    def test_duplicate_ids_default_to_error_and_last_policy_is_explicit(self):
        source='@1=~Old~ @01=~New~ [NEW]'
        with self.assertRaisesRegex(ValueError,'Duplicate'):parse_tra(source)
        self.assertEqual(parse_tra(source,duplicate_policy='last')[1].variants[0].text,'New')
        with self.assertRaisesRegex(ValueError,'duplicate_policy'):parse_tra('',duplicate_policy='unknown')

    def test_reference_inspection_never_invents_literal_text(self):
        content=('@1=#123 @2=@1 @3=( /* c */ AT "ZyxxaraVariable" ) '
                 '@4=!-5 ~Actual text~ [VOICE] @-6=!-7 !8 #42')
        for source in ('@1=#123','@2=@1','@3=(AT "var")','@4=!5 ~Text~'):
            with self.subTest(source=source),self.assertRaisesRegex(ValueError,'reference inspection'):
                parse_tra(source)
        entries=parse_tra(content,allow_references=True)
        self.assertEqual(entries[1].reference,'#123')
        self.assertEqual(entries[2].reference,'@1')
        self.assertIn('ZyxxaraVariable',entries[3].reference)
        self.assertEqual(entries[3].variants,[])
        self.assertEqual(entries[4].variants[0].text,'Actual text')
        self.assertEqual(entries[4].forced_references,(-5,))
        self.assertEqual(entries[-6].forced_references,(-7,8))
        self.assertEqual(entries[-6].variants,[])
        for entry in entries.values():
            with self.subTest(entry=entry.number),self.assertRaisesRegex(ValueError,'Cannot rewrite'):
                replace_entry(content,entry,'New','New')

    def test_empty_and_comment_only_files(self):
        for source in ('',' \t\r\n','// EOF','/* outer /* nested */ */','\ufeff// BOM\r'):
            with self.subTest(source=source):self.assertEqual(parse_tra(source),{})

    def test_malformed_inputs_fail_explicitly(self):
        sources=['@1', '@1 ~Text~', '@1 =', '@1=~Open', '@1="Open', '@1=%Open',
                 '@1=~~~~~Open', '@1=~Text~ [OPEN', '@1=~Text~ /* OPEN',
                 '/* outer /* inner */', '@1=~A~ ^', '@1=~A~ ^ [sound]',
                 '@1=~A~ [S] ^ ~B~', '@1=~A~ ~B~ ~C~', '@1=~A~ [S] [T]',
                 '@1=~A~ END', '@1=#', '@1=(AT "name"', '@1=(OTHER "name")',
                 '@1=(AT "name" ^ "suffix")']
        for source in sources:
            with self.subTest(source=source),self.assertRaises(ValueError):
                parse_tra(source,allow_references=True)

    def test_replacement_chooses_a_safe_delimiter_and_preserves_both_sounds(self):
        content='@1=~Old~ [M] "Old female" [F] // tail\r\n'
        male='Contains ~ and " and %';female='Contains ~ too'
        updated=replace_entry(content,parse_tra(content)[1],male,female)
        entry=parse_tra(updated)[1]
        self.assertEqual([v.text for v in entry.variants],[male,female])
        self.assertEqual([v.sound for v in entry.variants],['[M]','[F]'])
        self.assertTrue(updated.endswith('// tail\r\n'))

    def test_new_female_variant_copies_single_original_sound(self):
        content='@1=~Old~ /* note */ [VOICE] // tail\n'
        updated=replace_entry(content,parse_tra(content)[1],'Male','Female')
        entry=parse_tra(updated)[1]
        self.assertEqual([v.sound for v in entry.variants],['[VOICE]','[VOICE]'])
        self.assertIn('/* note */',updated)

    def test_read_text_handles_bom_and_legacy_encodings(self):
        text='@1=~Привет~\r\n'
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'test.tra'
            for encoding in ('utf-8-sig','utf-16','utf-32','cp1251'):
                with self.subTest(encoding=encoding):
                    path.write_bytes(text.encode(encoding))
                    self.assertEqual(read_text(path),text)
                    self.assertEqual(parse_tra(read_text(path))[1].variants[0].text,'Привет')

    def test_legacy_character_after_large_ascii_header_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'long.tra'
            path.write_bytes(b'// ASCII header\n' * 17000 + b'@1=~Don\x92t lose me.~')
            self.assertEqual(parse_tra(read_text(path))[1].variants[0].text,
                             'Don’t lose me.')


    def test_bare_strings_match_native_tra_lexer(self):
        entries = parse_tra('@1=Hello [M] Female-2 [F] @2=~Good luck~ EXIT2 @3=123^_suffix')
        self.assertEqual([v.text for v in entries[1].variants], ['Hello', 'Female-2'])
        self.assertEqual(entries[2].variants[1].text, 'EXIT2')
        self.assertEqual(entries[3].variants[0].text, '123_suffix')
        self.assertEqual(entries[1].variants[0].sound, '[M]')
        with self.assertRaises(ValueError):
            parse_tra('@1=Hello Female Third')
        with self.assertRaises(ValueError):
            parse_tra('@1=END')
        self.assertEqual(parse_tra('@1=end')[1].variants[0].text, 'end')


if __name__=='__main__':unittest.main()
