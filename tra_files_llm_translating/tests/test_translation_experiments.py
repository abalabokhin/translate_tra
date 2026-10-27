"""Diagnostic scoring regressions; no running Ollama or model downloads."""

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS / 'experiments'))
from diagnose_translation import Experiment, summarize
from run_all import rate, select_settings


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        args = argparse.Namespace(
            checks=str(SCRIPTS / 'experiments/inkgallery_checks.json'), actors=None,
            dictionary=str(SCRIPTS / 'dict.csv'), out=str(self.out),
            url='http://localhost:11434', num_ctx='8192', seed=None, dry_run=False,
            models=['mock'], prompts=['production'], scopes=['full'],
            think=['off'], temperatures=['default'], repeats=1)
        self.experiment = Experiment(args)

    def records(self):
        return [json.loads(line) for line in (self.out / 'runs.jsonl').read_text().splitlines()]

    def run_with(self, replies):
        with contextlib.redirect_stdout(io.StringIO()), patch.object(
                self.experiment, 'chat', side_effect=replies) as call:
            self.experiment.run()
            summarize(self.out)
        return call.call_count, self.records()

    def test_scopes_score_same_lines_and_checks(self):
        full = self.experiment.scopes('full')
        pairs = self.experiment.scopes('pair')
        full_targets = full[0][1]
        self.assertEqual(full_targets, {target for _, targets in pairs for target in targets})
        self.assertEqual(len(full[0][0]), 12)  # Full context remains available.
        self.assertEqual(len(full_targets), 8)
        for gender in ('male', 'female'):
            def checks(scopes):
                return sorted((c['line'], c['gender'], c['check'])
                              for _, targets in scopes for target in targets
                              for c in self.experiment.score(target, gender, None))
            self.assertEqual(checks(full), checks(pairs))

    def test_failed_male_penalizes_both_passes_without_extra_request(self):
        count, records = self.run_with([(None, {'error': 'offline', 'wall_seconds': 1})])
        self.assertEqual(count, 1)
        self.assertEqual([r['gender'] for r in records], ['male', 'female'])
        self.assertTrue(records[1]['skipped'])
        for record in records:
            self.assertTrue(record['checks'])
            self.assertFalse(any(c['ok'] for c in record['checks']))
        totals = rate(records, 'prompt')[('production',)]
        self.assertEqual(totals['requests'], 1)
        self.assertEqual(totals['errors'], 1)

    def test_failed_female_retains_male_checks_and_fails_female_checks(self):
        values = {str(i): row[3] for i, row in enumerate(self.experiment.rows[1:], 1)}
        male = {'message': {'content': json.dumps({'translations': values})}, 'wall_seconds': 1}
        count, records = self.run_with([(None, male), (None, {'error': 'offline', 'wall_seconds': 1})])
        self.assertEqual(count, 2)
        self.assertTrue(any(c['ok'] for c in records[0]['checks']))
        self.assertFalse(any(c['ok'] for c in records[1]['checks']))
        self.assertEqual(len(records[1]['checks']), sum(
            len(self.experiment.score(target, 'female', None)) for target in records[1]['targets']))

    def test_failed_markup_penalizes_both_genders_but_counts_one_request(self):
        self.experiment.args.prompts = ['markup']
        count, records = self.run_with([(None, {'error': 'offline', 'wall_seconds': 1})])
        self.assertEqual(count, 1)
        self.assertFalse(any(c['ok'] for r in records for c in r['checks']))
        totals = rate(records, 'prompt')[('markup',)]
        self.assertEqual(totals['requests'], 1)
        self.assertEqual(totals['errors'], 1)

    def test_selection_uses_joint_full_configuration_and_penalizes_failures(self):
        def record(prompt, temp, passed, scope='full'):
            return dict(config=dict(prompt=prompt, temperature=temp, scope=scope),
                        checks=[{'ok': i < passed} for i in range(10)],
                        error=None if passed else 'offline', wall_seconds=1, eval_count=1)
        records = [record('production', 'default', 9), record('production', '0.2', 1),
                   record('examples', 'default', 0), record('examples', '0.2', 8),
                   record('reframed-addressee', '0.2', 10), record('markup', '0.2', 10, 'pair'),
                   record('markup', 'default', 10), record('markup', 'default', 0),
                   record('markup', 'default', 0)]
        self.assertEqual(select_settings(records), ('production', 'default'))
        # Tie preferences hold even when records arrive in a different order.
        tied = [record('examples', '0.2', 9), record('production', '0.2', 9), records[0]]
        self.assertEqual(select_settings(tied), ('production', 'default'))
        interacting = [record('production', 'default', 9), record('production', '0.2', 8),
                       record('examples', 'default', 0), record('examples', '0.2', 10)]
        self.assertEqual(select_settings(interacting), ('examples', '0.2'))


if __name__ == '__main__':
    unittest.main()
