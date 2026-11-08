"""Name extraction from complete TRA literals and dictionary output, offline."""
import contextlib
import csv
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import collect_english_names as collector


class CollectNamesTests(unittest.TestCase):
    def test_cli_collects_both_variants_and_deduplicates_locations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'english.tra'
            source.write_text('@1 = ~Zyxxara\nQyzzorin~ [male] "Zyxxara\nVraxxala" [female]\n'
                              '@2 = ~Zyxxara~ ~~\n@3 = ~Qyzzorin~ ~Qyzzorin~\n')
            dictionary=root/'dict.csv'
            dictionary.write_text('Existing,Существующий,context,oldmod\n')
            result=subprocess.run([sys.executable,str(SCRIPTS/'collect_english_names.py'),
                                   str(source),'--dictionary',str(dictionary),'--comment','Fixture'],
                                  capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            with dictionary.open(encoding='utf-8', newline='') as handle:
                rows=list(csv.reader(handle))
            by_word={r[0]:r for r in rows}
            self.assertEqual(set(by_word),{'Existing','Zyxxara','Qyzzorin','Vraxxala'})
            self.assertEqual(by_word['Existing'],['Existing','Существующий','context','oldmod'])
            self.assertEqual(by_word['Zyxxara'][2],f'{source.resolve()}@1; {source.resolve()}@2')
            self.assertEqual(by_word['Qyzzorin'][2],f'{source.resolve()}@1; {source.resolve()}@3')
            self.assertEqual(by_word['Vraxxala'][1:],['',f'{source.resolve()}@1','Fixture'])

    def test_complete_literals_are_read_and_gender_tags_are_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'english.tra'
            path.write_text('''// @99 = ~Fake~ ~Pair~
@1 = ~Zyxxara
Qyzzorin~
@2 = "Vraxxala"
@3 = %Xyzziria%
@4 = ~Kryzzara~ ^ ~ Thyzzorin~
@5 = ~~~~~Vlyzzara~~~~~
@6 = ~Zyxxara <PRO_SIRMAAM>~
''')
            with patch.object(collector,'is_common_word',return_value=False), \
                 contextlib.redirect_stdout(io.StringIO()):
                words=collector.collect_fantasy_names_from_tra_files(str(path))
            self.assertEqual(set(words),{'Zyxxara','Qyzzorin','Vraxxala','Xyzziria',
                                         'Kryzzara','Thyzzorin','Vlyzzara'})

    def test_malformed_late_file_leaves_dictionary_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'english';source.mkdir()
            (source/'a.tra').write_text('@1 = ~Zyxxara~')
            (source/'b.tra').write_text('@1 = ~Unterminated')
            dictionary=root/'dict.csv'
            original=b'Existing,translation,context,mod\n'
            dictionary.write_bytes(original)
            with contextlib.redirect_stdout(io.StringIO()),self.assertRaises(ValueError):
                collector.collect_fantasy_names_from_tra_files(str(source),str(dictionary))
            self.assertEqual(dictionary.read_bytes(),original)

    def test_common_words_and_blacklisted_names_are_excluded_in_both_variants(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'english.tra'
            source.write_text('@1 = ~Hello Zyxxara~ ~Hello Qyzzorin~')
            blacklist=root/'blacklist.txt';blacklist.write_text('zyxxara\n')
            with contextlib.redirect_stdout(io.StringIO()):
                words=collector.collect_fantasy_names_from_tra_files(str(source),blacklist_file=str(blacklist))
            self.assertEqual(words,['Qyzzorin'])

    def test_comments_and_sound_names_never_become_dictionary_candidates(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'english.tra'
            source.write_text('''/* Vraxxala @99=~Fake~ /* Qyzzorin */ */
@1 /* Thyzzorin */ = ~Zyxxara~ /* Vlyzzara */ [Xyzziria]
// Qyzzorin @98=~Fake~
~Kryzzara~ /* Vlyzzara */ [Thyzzorin] // Xyzziria
@2 = ~~ [Vraxxala]
''')
            with patch.object(collector,'is_common_word',return_value=False), \
                 contextlib.redirect_stdout(io.StringIO()):
                words=collector.collect_fantasy_names_from_tra_files(str(source))
            self.assertEqual(words,['Zyxxara','Kryzzara'])

    def test_only_literal_text_is_collected_from_reference_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'english.tra'
            source.write_text('@1=~Zyxxara~ @2=#123 @3=@1 '
                              '@4=(AT "Vraxxala") @5=!12 ~Qyzzorin~ @-1=~Thyzzorin~')
            with patch.object(collector,'is_common_word',return_value=False), \
                 contextlib.redirect_stdout(io.StringIO()):
                words=collector.collect_fantasy_names_from_tra_files(str(source))
            self.assertEqual(words,['Zyxxara','Qyzzorin','Thyzzorin'])

    def test_duplicate_entry_uses_last_definition(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'english.tra'
            source.write_text('@1=~Zyxxara~ @1=~Qyzzorin~ [VOICE]')
            with patch.object(collector,'is_common_word',return_value=False), \
                 contextlib.redirect_stdout(io.StringIO()):
                words=collector.collect_fantasy_names_from_tra_files(str(source))
            self.assertEqual(words,['Qyzzorin'])

    def test_directory_scan_accepts_mixed_case_extensions_and_ignores_nonfiles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'a.TrA').write_text('@1=~Zyxxara~')
            (root/'b.TRA').write_text('@1=~Qyzzorin~')
            (root/'not-tra.txt').write_text('@1=~Thyzzorin~')
            (root/'folder.tra').mkdir()
            with patch.object(collector,'is_common_word',return_value=False), \
                 contextlib.redirect_stdout(io.StringIO()):
                words=collector.collect_fantasy_names_from_tra_files(str(root))
            self.assertEqual(set(words),{'Zyxxara','Qyzzorin'})


if __name__=='__main__':unittest.main()
