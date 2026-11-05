"""Check the reported diagnostic against the bundled numerical evidence."""
from pathlib import Path
import csv
import hashlib
import json
import statistics
import unittest

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]


class SavedRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads((HERE / 'shared_input_summary.json').read_text())
        cls.runs = {(mode, seed): json.loads(
            (HERE / 'runs' / mode / f'seed{seed}' / 'run.json').read_text())
            for mode in ('partitioned', 'shared') for seed in range(4)}

    def test_all_eight_runs_and_curves_are_complete(self):
        self.assertEqual(len(self.runs), 8)
        common = self.runs['partitioned', 0]['data']
        for (mode, seed), run in self.runs.items():
            with self.subTest(mode=mode, seed=seed):
                self.assertEqual(run['status'], 'complete')
                self.assertEqual(run['scope'], 'full')
                self.assertEqual(run['input_mode'], mode)
                self.assertEqual(run['seed'], seed)
                self.assertEqual(run['data'], common)
                self.assertEqual(run['variant'], 'none')
                self.assertEqual(run['edges'], [])
                self.assertEqual(run['epochs_completed'], 35)
                self.assertEqual(run['C'], 12)
                self.assertEqual(run['K'], 12)
                self.assertEqual(run['lr'], .0005)
                self.assertEqual(run['sizes']['d_model'], 96)
                self.assertEqual(run['sizes']['n_layers'], 2)
                widths = [13, 13, 11, 15] if mode == 'partitioned' else [37] * 4
                self.assertEqual(run['projection_input_widths'], widths)
                curve = ROOT / run['curve']
                self.assertEqual(curve, HERE / 'runs' / mode / f'seed{seed}' / 'curve.csv')
                with curve.open() as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual([int(row['epoch']) for row in rows], list(range(1, 36)))
                improved = [row for row in rows if row['improved'] == 'True']
                self.assertEqual(int(improved[-1]['epoch']), run['best_epoch'])
                self.assertEqual(float(improved[-1]['val_RMSE']), run['validation_RMSE'])

    def test_all_means_and_paired_differences_match_saved_scores(self):
        targets = ('cardiovascular', 'pulmonary', 'renal', 'metabolic', 'all_organ_pooled')
        for split in ('A', 'B'):
            for target in targets:
                values = {}
                for mode in ('partitioned', 'shared'):
                    values[mode] = [self.runs[mode, seed][split]['pooled_masked_RMSE']
                        if target == 'all_organ_pooled' else
                        self.runs[mode, seed][split]['organs'][target]['RMSE'] for seed in range(4)]
                    cell = self.summary['arm_summary'][mode][split][target]
                    self.assertAlmostEqual(cell['mean'], statistics.mean(values[mode]), places=14)
                    self.assertEqual(cell['min'], min(values[mode]))
                    self.assertEqual(cell['max'], max(values[mode]))
                    self.assertAlmostEqual(cell['span'], max(values[mode]) - min(values[mode]), places=14)
                differences = [b - a for a, b in zip(values['partitioned'], values['shared'])]
                paired = self.summary['paired_differences'][split][target]
                self.assertAlmostEqual(paired['mean'], statistics.mean(differences), places=14)
                if target == 'renal':
                    self.assertTrue(all(delta < 0 for delta in differences))
        for seed in range(4):
            self.assertEqual(self.runs['shared', seed]['n_params'] -
                             self.runs['partitioned', seed]['n_params'], 18432)

    def test_summary_run_locators_and_original_fingerprints(self):
        inventory = json.loads((ROOT / 'manifests/distribution.json').read_text())
        for run in self.summary['runs']:
            rel = run['run_json']
            self.assertFalse(Path(rel).is_absolute())
            path = ROOT / rel
            self.assertTrue(path.is_file())
            self.assertEqual(inventory[rel]['original_sha256'], run['run_json_sha256'])
            self.assertEqual(inventory[rel]['distributed_sha256'],
                             hashlib.sha256(path.read_bytes()).hexdigest())
        inputs = self.summary['inputs']
        for name in ('selection', 'frozen_reference', 'shared_input_variant', 'renal_protocol', 'diagnosis_reading'):
            rel = inputs[name]
            self.assertTrue((ROOT / rel).is_file(), rel)
            self.assertEqual(inputs[name + '_sha256'], inventory[rel]['original_sha256'])
        reference = json.loads((ROOT / inputs['frozen_reference']).read_text())
        for split in ('A', 'B'):
            self.assertEqual(self.summary['frozen_references']['persistence'][split]['mean'],
                             reference['selected_seed_summary']['persistence'][split]['renal']['mean'])


if __name__ == '__main__':
    unittest.main()
