"""Ordered candidate lifecycle without downloads or inference."""
import argparse
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import run_non_thinking as runner


class NonThinkingRunnerTests(unittest.TestCase):
    def test_only_disabled_thinking_is_eligible(self):
        self.assertEqual(runner.thinking_setting({'thinking': {'values': [False, True]}}), 'off')
        self.assertEqual(runner.thinking_setting({'thinking': {'values': [False]}}), 'default')
        self.assertEqual(runner.thinking_setting({'capabilities': ['thinking']}), 'off')
        self.assertEqual(runner.thinking_setting({}), 'default')
        for values in ([True], ['low', 'medium', 'high']):
            with self.assertRaisesRegex(ValueError, 'No non-thinking mode'):
                runner.thinking_setting({'thinking': {'values': values}})

    def test_probed_tlite_overrides_metadata_only_for_verified_digest(self):
        info = {'thinking': {'values': [True], 'default': True}}
        tag, digest = runner.TLITE_NATIVE
        self.assertEqual(runner.thinking_setting(info, tag, digest), 'off')
        for unverified_tag, unverified_digest in [(tag, 'different artifact'), ('other-model', digest)]:
            with self.assertRaises(ValueError):
                runner.thinking_setting(info, unverified_tag, unverified_digest)

    def lifecycle(self, failed_pull=False, failed_stage=False, orders=None):
        events = []
        class Client:
            def installed(self):
                return set()
            def pull(self, tag):
                events.append(('pull', tag))
                if failed_pull and tag == 'a':
                    raise OSError('unavailable')
            def get(self, path, payload=None):
                return {}
        manifest = dict(status='running', started_utc='test', models=[
            dict(order=i, tag=tag, status='pending') for i, tag in enumerate(['a', 'b'], 1)])
        def evaluate(args, out, tag, think, checks):
            events.append(('test', tag, checks.name))
            if failed_stage and tag == 'a':
                raise ValueError('Unexpected nonempty thinking output')
        cases = [('one', runner.SCRIPT_DIR / 'one.json'), ('two', runner.SCRIPT_DIR / 'two.json')]
        with tempfile.TemporaryDirectory() as temp, patch.object(runner, 'datasets', return_value=cases), \
                patch.object(runner, 'evaluate', side_effect=evaluate), contextlib.redirect_stdout(io.StringIO()):
            runner.run_models(argparse.Namespace(repeats=3, num_ctx=8192), Path(temp), manifest, Client(), orders=orders)
            self.assertTrue((Path(temp) / 'REPORT.md').exists())
        return events, manifest

    def test_download_test_then_next_download(self):
        events, manifest = self.lifecycle()
        self.assertEqual(events, [('pull', 'a'), ('test', 'a', 'one.json'), ('test', 'a', 'two.json'),
                                  ('pull', 'b'), ('test', 'b', 'one.json'), ('test', 'b', 'two.json')])
        self.assertTrue(all(m['status'] == 'completed' for m in manifest['models']))

    def test_pull_failure_is_recorded_and_next_candidate_runs(self):
        events, manifest = self.lifecycle(failed_pull=True)
        self.assertEqual(events, [('pull', 'a'), ('pull', 'b'), ('test', 'b', 'one.json'), ('test', 'b', 'two.json')])
        self.assertEqual(manifest['models'][0]['status'], 'failed/skipped')
        self.assertEqual(manifest['models'][1]['status'], 'completed')

    def test_stage_failure_stops_candidate_without_retry_or_thinking_fallback(self):
        events, manifest = self.lifecycle(failed_stage=True)
        self.assertEqual(events, [('pull', 'a'), ('test', 'a', 'one.json'),
                                  ('pull', 'b'), ('test', 'b', 'one.json'), ('test', 'b', 'two.json')])
        self.assertIn('Unexpected nonempty thinking', manifest['models'][0]['error'])
        self.assertEqual(manifest['models'][1]['status'], 'completed')

    def test_explicit_continuation_does_not_repeat_earlier_candidate(self):
        events, manifest = self.lifecycle(orders={2})
        self.assertEqual(events, [('pull', 'b'), ('test', 'b', 'one.json'), ('test', 'b', 'two.json')])
        self.assertEqual(manifest['models'][0]['status'], 'pending')


if __name__ == '__main__':
    unittest.main()
