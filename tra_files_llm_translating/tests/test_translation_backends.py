"""Production backend selection, saved requests and CSV-to-TRA round trip, offline."""
import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / 'experiments'))
from translate_dialogs import DialogTranslator, main, TRANSLATION_RULES, UNSPECIFIED_GENDER_NOTE
from translation_common import DIALOGUE_COLUMNS, TRANSLATION_COLUMNS, read_csv, write_csv
from update_tra_from_csv import TraUpdater
import run_codex_translation as runner

FAKE_CLI = '''#!/usr/bin/env python3
import json,sys
from pathlib import Path
prompt=sys.stdin.read()
data=json.loads(prompt.split('DIALOGUE DATA:\\n',1)[1])
female='now FEMALE' in data['instruction']
translations={'I returned, <CHARNAME>.':('Я вернулся, <CHARNAME>.','Я вернулась, <CHARNAME>.'),
              'The door is open.':('Дверь открыта.','Дверь открыта.'),
              'Silver key':('Серебряный ключ','Серебряный ключ'),
              'Bronze key':('Бронзовый ключ','Бронзовый ключ'),
              '':('','')}
def text(english,gender):return translations[english][gender]
values={}
for line in data['dialogue']:
 if 'english_female' in line:
  values[line['id']]={'male':text(line['english'],0),'female':text(line['english_female'],1)}
 else:values[line['id']]=text(line['english'],int(female))
reply=json.dumps({'translations':values},ensure_ascii=False)
Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text(reply,encoding='utf-8')
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':reply}}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':100,'output_tokens':20}}))
'''


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'english'
        self.source.mkdir()
        self.target = self.root / 'russian'
        self.actors = self.root / 'actors.csv'
        self.actors.write_text('NPC,female\n')
        self.dictionary = self.root / 'dict.csv'
        self.dictionary.write_text('Silver key,Серебряный ключ\n')
        self.binary = self.root / 'fake-codex'
        self.binary.write_text(FAKE_CLI)
        self.binary.chmod(0o755)
        quiet = contextlib.redirect_stdout(io.StringIO())
        quiet.__enter__()
        self.addCleanup(quiet.__exit__, None, None, None)

    def translator(self, **kwargs):
        return DialogTranslator(str(self.source), str(self.target), str(self.actors),
                                str(self.dictionary), **kwargs)

    def inputs(self):
        header = DIALOGUE_COLUMNS + ['Source_Female_Text','Source_Has_Female']
        rows = [ ['Player1','a','','I returned, <CHARNAME>.','@1','TRA:test.tra:@1','',''],
                 ['NPC','b','a','The door is open.','@2','TRA:test.tra:@2','','1'],
                 ['Player1','c','b','I returned, <CHARNAME>.','@1','TRA:test.tra:@1','',''] ]
        write_csv(self.source/'dialogue.csv',header,[dict(zip(header,r)) for r in rows])
        write_csv(self.source/'_unused_tra_lines.csv', ['Reference','Text','Source_Female_Text','Source_Has_Female'],
                  [{'Reference':'test.tra:@3','Text':'Silver key','Source_Female_Text':'Bronze key','Source_Has_Female':'1'}])

    def test_backend_defaults_overrides_and_wrong_backend_options(self):
        old=self.translator()
        self.assertEqual((old.model,old.method,old.effort),('qwen3.5:9b','two-pass',None))
        codex=self.translator(backend='codex')
        self.assertEqual((codex.model,codex.method,codex.effort),('gpt-6.1-sol','both','low'))
        custom=self.translator(backend='codex',model='other',method='two-pass',effort='high')
        self.assertEqual((custom.model,custom.method,custom.effort),('other','two-pass','high'))
        for kwargs in ({'backend':'codex','think':False},{'backend':'codex','num_ctx':4096},
                       {'backend':'codex','ollama_url':'http://localhost'}, {'effort':'low'},
                       {'backend':'other'},{'method':'other'}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.translator(**kwargs)

    def test_codex_both_and_two_pass_translate_dialogue_unused_and_export_tra(self):
        self.inputs()
        for method,expected_calls in [('both',2),('two-pass',4)]:
            with self.subTest(method=method):
                target=self.root/method
                args=[str(self.source),'--target',str(target),'--backend','codex','--method',method,
                      '--effort','medium','--model','test-sol','--codex-bin',str(self.binary),
                      '--actors',str(self.actors),'--dictionary',str(self.dictionary),
                      '--requests-dir',str(self.root/(method+'-evidence'))]
                with patch('urllib.request.urlopen',side_effect=AssertionError('must not call Ollama')):
                    self.assertEqual(main(args),0)
                _,rows=read_csv(target/'dialogue.csv',DIALOGUE_COLUMNS+TRANSLATION_COLUMNS)
                self.assertEqual([r['Line_ID'] for r in rows],['a','b','c'])
                self.assertEqual(rows[0]['Russian_Male'],rows[2]['Russian_Male'])
                self.assertEqual(rows[0]['Russian_Female'],'Я вернулась, <CHARNAME>.')
                self.assertEqual(rows[1]['Russian_Female'],'')
                _,unused=read_csv(target/'_unused_tra_lines.csv',TRANSLATION_COLUMNS)
                self.assertEqual(unused[0]['Russian_Female'],'Бронзовый ключ')
                calls=list((self.root/(method+'-evidence')).rglob('call.json'))
                self.assertEqual(len(calls),expected_calls)
                for p in calls:
                    call=json.loads(p.read_text())
                    self.assertEqual((call['model'],call['reasoning_effort']),('test-sol','medium'))
                    self.assertIn('model_reasoning_effort="medium"',call['command'])
                    for name in ('events.jsonl','prompt.txt','schema.json','response.txt'):
                        self.assertTrue(p.with_name(name).is_file())
                tra=self.root/(method+'-tra');tra.mkdir()
                (tra/'test.tra').write_text('@1 = ~I returned, <CHARNAME>.~\n@2 = ~The door is open.~ ~~\n@3 = ~Silver key~ ~Bronze key~\n')
                out=self.root/(method+'-export')
                updater=TraUpdater(tra,target,out)
                updater.load_translations_from_csvs();updater.update_all_tra_files()
                text=(out/'test.tra').read_text()
                self.assertIn('~Я вернулся, <CHARNAME>.~ ~Я вернулась, <CHARNAME>.~',text)
                self.assertIn('~Дверь открыта.~ ~~',text)
                self.assertIn('~Серебряный ключ~ ~Бронзовый ключ~',text)

    def test_both_method_is_available_for_ollama(self):
        self.inputs()
        translator=self.translator(method='both')
        def reply(prompt,schema):
            data=json.loads(prompt)
            return json.dumps({'translations':{line['id']:{'male':line['english'],'female':line['english_female']}
                                               for line in data['dialogue']}})
        with patch.object(translator,'_call_ollama',side_effect=reply) as ollama, \
             patch('translate_dialogs.run_cli',side_effect=AssertionError('must not call Codex')):
            self.assertTrue(translator.translate_all_dialogs())
        self.assertEqual(ollama.call_count,2)

    def test_cli_failure_and_structural_rejection_keep_old_export_and_evidence(self):
        self.inputs()
        (self.source/'_unused_tra_lines.csv').unlink()
        for mode in ('failure','invalid'):
            translator=self.translator(backend='codex',codex_bin=str(self.binary))
            previous=self.target/'dialogue.csv';previous.write_text('old export\n')
            if mode=='failure':
                self.binary.write_text('#!/usr/bin/env python3\nimport sys\nsys.stdin.read()\nprint(\'{"type":"turn.failed","error":{"message":"quota"}}\')\n')
            else:
                self.binary.write_text(FAKE_CLI.replace("reply=json.dumps({'translations':values},ensure_ascii=False)",
                                                       "reply='{\"translations\":{}}'"))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(translator.translate_all_dialogs())
            self.assertEqual(previous.read_text(),'old export\n')
            calls=list(translator.request_run.rglob('call.json'))
            self.assertEqual(len(calls),1)
            if mode=='invalid':
                self.assertTrue((self.target/'dialogue.both.rejected.txt').is_file())
                self.assertTrue(calls[0].with_name('response.txt').is_file())

    def test_production_graphs_and_schemas_match_saved_comparison(self):
        historical=SCRIPTS/'experiments/codex_translation/20261107-sol-low-one-repeat/results'
        for name,checks in runner.datasets():
            e=runner.experiment(checks,self.root/name)
            system,user,schema=runner.both_request(e)
            saved=historical/name/'model-1/both/1/both'
            # Archived experiment instructions stay unchanged. Production
            # instructions now also cover unspecified party slots/narration;
            # compare the source graph, metadata and schema independently.
            saved_user=(saved/'prompt.txt').read_text().split('\n\nDIALOGUE DATA:\n',1)[1]
            current_data, saved_data = json.loads(user), json.loads(saved_user)
            current_data.pop('instruction')
            saved_data.pop('instruction')
            for line in current_data['dialogue']:
                if line.get('note') == UNSPECIFIED_GENDER_NOTE:
                    self.assertNotIn(line['speaker_gender'], ('MALE', 'FEMALE', 'male', 'female'))
                    line.pop('note')
            self.assertEqual(current_data,saved_data)
            self.assertEqual(schema,json.loads((saved/'schema.json').read_text()))
            self.assertEqual(system,TRANSLATION_RULES)

    def test_codex_mock_does_not_launch_a_process(self):
        self.inputs()
        translator=self.translator(backend='codex',test_mode=True)
        with patch('codex_backend.subprocess.Popen',side_effect=AssertionError('must stay offline')):
            self.assertTrue(translator.translate_all_dialogs())
        self.assertFalse((self.target/'_requests').exists())


if __name__=='__main__':unittest.main()
