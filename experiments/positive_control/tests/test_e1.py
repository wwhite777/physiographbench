"""CPU checks for E1 observation integrity, causal lag, oracle, and host plan."""
import copy
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import sim_positive_control as e1
import oracle_check as oracle


class RegimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        e1.configure_scratch()
        cls.data = e1.generate(100, 1., seed=0)

    def test_reproducibility_and_kappa_pairing(self):
        repeat = e1.generate(100, 1., seed=0)
        for name in self.data:
            if name != 'metadata_json':
                np.testing.assert_array_equal(self.data[name], repeat[name])
        null = e1.generate(100, 0., seed=0)
        for name in ('mask', 'controls', 'audit_source', 'audit_reserve', 'audit_mask_uniforms'):
            np.testing.assert_array_equal(self.data[name], null[name])
        np.testing.assert_array_equal(self.data['truth'][..., :4], null['truth'][..., :4])
        self.assertGreater(np.mean(abs(self.data['truth'][..., 4:] - null['truth'][..., 4:])), .01)

    def test_latent_absent_and_masks_applied_in_actual_batches(self):
        self.assertEqual(self.data['channels'].tolist(), list(e1.CHANNELS))
        self.assertEqual(self.data['values'].shape[-1], 6)
        self.assertTrue(self.data['mask'][..., :4].all())
        self.assertTrue((self.data['values'][~self.data['mask']] == 0).all())
        np.testing.assert_array_equal(self.data['values'][self.data['mask']],
                                      self.data['truth'][self.data['mask']])
        prepared = e1.prepare_data(self.data)
        self.assertFalse(any(name.startswith('audit_') for name in prepared))
        batch = next(e1.batches(prepared, prepared['te'], 'cpu'))
        self.assertFalse(batch['mask'][..., 4:].all())
        self.assertTrue((batch['values'][batch['mask'] == 0] == 0).all())
        self.assertEqual(batch['values'].shape[1:], (12, 6))
        self.assertEqual(batch['target'].shape[1:], (24, 6))
        allowed = {'values', 'mask', 'control_ctx', 'control_future', 'static', 'target'}
        self.assertEqual(set(batch), allowed)
        changed = dict(self.data, audit_reserve=self.data['audit_reserve'] + 1000.)
        alternate = next(e1.batches(e1.prepare_data(changed), prepared['te'], 'cpu'))
        np.testing.assert_array_equal(batch['values'].numpy(), alternate['values'].numpy())

    def test_empirical_rates_and_observation_sensitivities(self):
        counts = e1.clinical_rates()['cohorts']['A_train']
        self.assertEqual(counts['valid_hours'], 505935)
        self.assertEqual(counts['counts'], dict(Creatinine=33911, BUN=41639, Lactate=17484))
        self.assertEqual(counts['renal_union_count'], 41865)
        observed = self.data['mask'][..., 4:].mean(axis=(0, 1))
        np.testing.assert_allclose(observed, e1.target_probabilities(), atol=.015)
        low = e1.remask(self.data, [.01, .01])
        high = e1.remask(self.data, [.5, .5])
        self.assertTrue((low['mask'] <= high['mask']).all())
        self.assertFalse(e1.remask(self.data, [0., 0.])['mask'][..., 4:].any())
        self.assertTrue(e1.remask(self.data, [1., 1.])['mask'].all())
        np.testing.assert_array_equal(low['truth'], high['truth'])
        hourly = e1.target_probabilities(hourly_matched=True)
        np.testing.assert_allclose(1. - (1. - hourly) ** 12, e1.target_probabilities())

    def test_oracle_has_no_hidden_or_future_observation_features(self):
        changed = dict(self.data)
        changed['values'] = self.data['values'].copy()
        changed['values'][:, e1.C:] += 1e6
        changed['audit_reserve'] = self.data['audit_reserve'] + 1e6
        changed['truth'] = self.data['truth'] + 1e6
        for channel in (4, 5):
            for augmented in (False, True):
                np.testing.assert_array_equal(oracle.features(self.data, channel, augmented),
                                              oracle.features(changed, channel, augmented))
        train, test = e1.patient_split(100, 0)
        np.testing.assert_array_equal(np.r_[train, test], np.random.default_rng(0).permutation(100))
        self.assertEqual((len(train), len(test)), (70, 30))
        self.assertFalse(set(train) & set(test))

    def test_cardiovascular_perturbation_has_delayed_target_effect(self):
        base = e1.base_cardiovascular(100, 0)
        perturbed = copy.deepcopy(base)
        source_time = e1.C - 1
        perturbed['cardiovascular'][:, source_time, 0] += 15.
        with patch.object(e1, 'base_cardiovascular', return_value=perturbed):
            altered = e1.generate(100, 1., seed=0)
        np.testing.assert_array_equal(altered['truth'][:, :source_time, :],
                                      self.data['truth'][:, :source_time, :])
        for channel, lag in ((4, 6), (5, 9)):
            # Source -> reserve update -> delayed target equilibrium -> target update.
            earliest = source_time + lag + 2
            np.testing.assert_array_equal(altered['truth'][:, :earliest, channel],
                                          self.data['truth'][:, :earliest, channel])
            self.assertGreater(np.max(abs(altered['truth'][:, earliest:, channel]
                                           - self.data['truth'][:, earliest:, channel])), .001)
        with patch.object(e1, 'base_cardiovascular', return_value=perturbed):
            altered_null = e1.generate(100, 0., seed=0)
        null = e1.generate(100, 0., seed=0)
        np.testing.assert_array_equal(altered_null['truth'][..., 4:], null['truth'][..., 4:])

    def test_100_patient_cpu_oracle_runs_and_prints_gain(self):
        result = oracle.check(100, kappas=(0., 1.), lens=False)
        self.assertEqual(len(result['cells']), 2)
        self.assertFalse(result['qualification']['qualification_set'])
        self.assertFalse(result['qualification']['passed'])
        for cell in result['cells']:
            self.assertEqual((cell['n_train'], cell['n_test']), (70, 30))
            for organ, metrics in cell['per_organ'].items():
                gain = metrics['rmse_relative_reduction']
                self.assertTrue(np.isfinite(gain))
                self.assertGreater(metrics['local']['rmse'], 0)
                print(f"100-patient oracle kappa={cell['kappa']} {organ} RMSE gain={gain:.6f}",
                      flush=True)

    def test_dataset_roundtrip_and_manifest_validation(self):
        private = Path(tempfile.mkdtemp(prefix='roundtrip_', dir=e1.SCRATCH))
        path = private / 'data.npz'
        original = e1.generate(100, 1., out=path)
        loaded = e1.load_dataset(path, 100, 1.)
        for name in original:
            np.testing.assert_array_equal(original[name], loaded[name])
        with self.assertRaises(ValueError):
            e1.load_dataset(path, 100, 0.)
        with self.assertRaises(FileExistsError):
            e1.generate(100, 1., out=path)
        manifest_path = path.with_suffix('.manifest.json')
        manifest = json.loads(manifest_path.read_text())
        manifest['output_sha256'] = 'deliberately incorrect test checksum'
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            e1.load_dataset(path, 100, 1.)

    def test_frozen_graph_rules_and_capacity_counts(self):
        sys.path.insert(0, str(e1.MATCHED_SIM))
        from sim_grid_runner_mono2 import build_model, graph_edges
        none = build_model('physiograph_gru', 'none', 0)
        admissible = build_model('physiograph_gru', 'admissible', 0)
        # Shared initialization is preserved despite selecting different messages.
        for name, parameter in none.named_parameters():
            if not name.startswith('couplers.'):
                np.testing.assert_array_equal(parameter.detach().numpy(),
                                              dict(admissible.named_parameters())[name].detach().numpy())
        count = lambda model: sum(parameter.numel() for parameter in model.parameters())
        self.assertEqual(count(none), 254086)
        self.assertEqual(count(admissible), 271242)
        self.assertEqual(count(build_model('control_gru', control_gru_hidden=96)), 61062)
        matched = count(build_model('control_gru', control_gru_hidden=201))
        self.assertEqual(matched, 254472)
        self.assertLess(abs(matched / count(none) - 1.), .01)
        dense = graph_edges('dense', 0)
        for seed in range(4):
            selected = np.random.default_rng(seed).choice(len(dense), 2, replace=False)
            self.assertEqual(graph_edges('random', seed), tuple(dense[i] for i in sorted(selected)))


class HostPlanTests(unittest.TestCase):
    def test_dry_run_lists_registered_cpu_and_cuda_grids_without_creating_output(self):
        output_root = e1.SCRATCH / 'test_dry_run_never_created'
        self.assertFalse(output_root.exists())
        for device in ('cpu', 'cuda'):
            result = subprocess.run(
                ['bash', str(ROOT / 'run_host_e1.sh'), '--dry-run', '--device', device,
                 '--output-root', str(output_root)], text=True, capture_output=True, check=True)
            lines = result.stdout.splitlines()
            generate = [line for line in lines if ' generate ' in line]
            fits = [shlex.split(line) for line in lines if ' run-cell ' in line]
            self.assertEqual((len(generate), len(fits)), (3, 96))
            cells = set()
            for command in fits:
                flags = {flag: command[command.index(flag) + 1]
                         for flag in ('--arm', '--kappa', '--seed', '--epochs',
                                      '--n-patients', '--device', '--reference-npz')}
                self.assertEqual(flags['--epochs'], '60')
                self.assertEqual(flags['--n-patients'], '400')
                self.assertEqual(flags['--device'], device)
                self.assertTrue(flags['--reference-npz'].endswith('kappa_1.npz'))
                cells.add((flags['--arm'], flags['--kappa'], flags['--seed']))
            self.assertEqual(len(cells), 96)
        self.assertFalse(output_root.exists())

    def test_output_escape_and_existing_destination_are_rejected(self):
        with self.assertRaises(ValueError):
            e1.owned_path(ROOT.parent / 'outside_e1.json')
        result = subprocess.run(['bash', str(ROOT / 'run_host_e1.sh'), '--dry-run',
                                 '--output-root', str(ROOT.parent)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        path = e1.SCRATCH / 'plan_existing/kappa_1/none/seed3.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{}\n')
        result = subprocess.run(['bash', str(ROOT / 'run_host_e1.sh'), '--dry-run',
                                 '--output-root', str(e1.SCRATCH / 'plan_existing')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Refusing existing', result.stderr)

    def test_full_neural_run_requires_explicit_mode(self):
        with self.assertRaisesRegex(ValueError, 'Choose exactly one'):
            e1.run_cell(arm='admissible', kappa=1., seed=0, epochs=60,
                        n_patients=400, device='cpu', threads=1,
                        out=e1.SCRATCH / 'unexecuted.json')
        with self.assertRaisesRegex(ValueError, 'exactly one CPU epoch'):
            e1.run_cell(arm='admissible', kappa=1., seed=0, epochs=2,
                        n_patients=24, device='cpu', threads=1,
                        out=e1.SCRATCH / 'unexecuted.json', smoke=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
