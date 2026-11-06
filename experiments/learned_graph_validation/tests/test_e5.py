"""Author tests: fixed message oracles, data isolation, and protocol boundaries."""
import argparse
import math
from pathlib import Path
import shlex
import subprocess
import sys
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from e5_common import ROOT, GraFITiAdapter, TPatchGNNAdapter, owned_path, pooled_mse
import numpy as np
import torch
from torch.nn import functional as F

from grafiti_adapter_v3 import _GraphLayer, _IncidentAttention
from grafiti_p12_reproduce import (FEATURES, P12GraFITi, P12Windows, code_split,
                                   normalize, parse_record)
from learned_adjacency_ablation import (FixedGraFITi, FixedTPatchGNN, build_model,
                                        fixed_grafiti_layer, graph_support,
                                        normalized_adjacency)


def sample(n_feat=16, length=12, horizon=12):
    return dict(values=torch.randn(2, length, n_feat), mask=torch.ones(2, length, n_feat),
                target=torch.randn(2, horizon, n_feat), target_mask=torch.ones(2, horizon, n_feat))


class GraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def setUp(self):
        torch.manual_seed(28)

    def test_direction_self_loops_and_forbidden_edges(self):
        graph = graph_support('physiological')
        self.assertTrue(graph.diag().all())
        self.assertTrue(graph[8, 0])  # cardiovascular -> renal
        self.assertFalse(graph[8, 4])  # no pulmonary -> renal
        self.assertTrue(graph[11, 8])  # renal -> metabolic
        self.assertFalse(graph[8, 11])  # no metabolic -> renal
        self.assertTrue(graph[9, 10])  # within-organ channels
        a = normalized_adjacency(graph)
        torch.testing.assert_close(a.sum(1), torch.ones(16))
        self.assertTrue((a[~graph] == 0).all())

    def test_random_fixed_degrees_and_seeds(self):
        physiology = graph_support('physiological')
        a, b = graph_support('random', 0), graph_support('random', 1)
        self.assertTrue(torch.equal(a, graph_support('random', 0)))
        self.assertFalse(torch.equal(a, b))
        self.assertFalse(torch.equal(a, physiology))
        self.assertTrue(a.diag().all())
        self.assertTrue(torch.equal(a.sum(1), physiology.sum(1)))
        self.assertTrue(graph_support('complete').all())

    def test_fixed_grafiti_time_message_against_scalar_oracle(self):
        layer = _GraphLayer(1, 1, 1)
        with torch.no_grad():
            layer.mab.value.weight.copy_(torch.tensor([[1., 2.]]))
            layer.mab.value.bias.zero_()
            layer.mab.output.weight.fill_(1.)
            layer.mab.feedforward.weight.zero_()
            layer.mab.feedforward.bias.zero_()
        channels = torch.tensor([[[10.], [20.], [30.]]], requires_grad=True)
        edges = torch.tensor([[[[1.], [2.], [3.]]]])
        present = torch.tensor([[[True, False, True]]])
        times = torch.zeros_like(edges)
        adjacency = torch.tensor([[.5, .5, 0.], [0., 1., 0.], [1/3, 1/3, 1/3]])
        _, updated, _ = fixed_grafiti_layer(layer, channels, times, edges, present, adjacency)
        # Source messages are 12, absent, 36. Normalize on present sources only.
        torch.testing.assert_close(updated.flatten(), torch.tensor([12., 0., 24.]))
        gradient = torch.autograd.grad(updated[0, 0, 0, 0], channels)[0]
        torch.testing.assert_close(gradient.flatten(), torch.tensor([1., 0., 0.]))

    def test_complete_grafiti_equals_original_with_uniform_source_channel_weights(self):
        reference = GraFITiAdapter().eval()
        fixed = FixedGraFITi(torch.ones(16, 16, dtype=torch.bool)).eval()
        fixed.load_state_dict({**reference.state_dict(), 'fixed_adjacency': fixed.fixed_adjacency})

        def uniform(mab, nodes, incident, present):
            if nodes.shape[1] == 16:
                return _IncidentAttention.forward(mab, nodes, incident, present)
            values = mab.value(incident)
            weights = present.to(values.dtype)
            aggregate = (values * weights.unsqueeze(-1)).sum(2)
            aggregate = aggregate / weights.sum(2).clamp_min(1).unsqueeze(-1)
            hidden = F.leaky_relu(nodes + mab.output(aggregate), .1)
            return F.leaky_relu(hidden + mab.feedforward(hidden), .1)

        for layer in reference.layers:
            layer.mab.forward = types.MethodType(uniform, layer.mab)
        batch = sample()
        batch['mask'][:, :2, 3:8] = 0
        torch.testing.assert_close(fixed(batch, 12), reference(batch, 12), atol=2e-6, rtol=2e-5)

    def test_identity_graph_has_no_cross_channel_data_path(self):
        for cls in (FixedGraFITi, FixedTPatchGNN):
            with self.subTest(model=cls.__name__):
                model = cls(torch.eye(16, dtype=torch.bool)).eval()
                batch = sample()
                batch['values'].requires_grad_()
                output = model(batch, 12)[:, :, 0].sum()
                gradient = torch.autograd.grad(output, batch['values'])[0]
                self.assertTrue((gradient[:, :, 1:] == 0).all())
                self.assertGreater(gradient[:, :, 0].abs().sum().item(), 0.)

    def test_tpatch_exact_fixed_graph_and_no_dynamic_builder(self):
        model = FixedTPatchGNN(graph_support('physiological')).eval()
        for block in model.blocks:
            def forbidden(*args):
                raise AssertionError('learned adjacency called')
            block.adjacency = forbidden
        batch = sample()
        _, graphs = model.encode_context(batch)
        for graph in graphs:
            torch.testing.assert_close(graph[0, 0], model.fixed_adjacency)
            torch.testing.assert_close(graph[1, 1], model.fixed_adjacency)
        block = model.blocks[0]
        with torch.no_grad():
            for projection in block.hop_projections:
                projection.weight.copy_(torch.eye(64))
            block.graph_offset.zero_()
        states = torch.rand(2, 2, 16, 64)
        expected = torch.empty_like(states)
        for b in range(2):
            for p in range(2):
                for receiver in range(16):
                    expected[b, p, receiver] = states[b, p, receiver] + sum(
                        model.fixed_adjacency[receiver, source] * states[b, p, source]
                        for source in range(16))
        torch.testing.assert_close(block.propagate(states, model.fixed_adjacency), expected)

    @unittest.skipIf(__import__("os").environ.get("PHYSIOGRAPH_NO_TRAINING") == "1", "optimizer steps disabled for release verification")
    def test_all_six_variants_train_finitely_and_ignore_labels(self):
        for name in ('grafiti', 'tpatchgnn'):
            for graph in ('physiological', 'random', 'complete'):
                with self.subTest(model=name, graph=graph):
                    model = build_model(name, graph, 2).eval()
                    batch = sample()
                    prediction = model(batch, 12)
                    altered = {**batch, 'target': torch.full_like(batch['target'], float('nan')),
                               'target_mask': torch.zeros_like(batch['target_mask'])}
                    torch.testing.assert_close(prediction, model(altered, 12), rtol=0, atol=0)
                    optimizer = torch.optim.Adam((p for p in model.parameters() if p.requires_grad), .001)
                    for _ in range(2):
                        optimizer.zero_grad()
                        loss = pooled_mse(model(batch, 12), batch['target'], batch['target_mask'])
                        self.assertTrue(torch.isfinite(loss))
                        loss.backward()
                        for p in model.parameters():
                            if p.grad is not None:
                                self.assertTrue(torch.isfinite(p.grad).all())
                        optimizer.step()
                    torch.testing.assert_close(model.fixed_adjacency,
                                               normalized_adjacency(graph_support(graph, 2)))
                    if name == 'grafiti':
                        for layer in model.layers[:-1]:
                            self.assertIsNotNone(layer.mab.query.weight.grad)
                            self.assertIsNotNone(layer.mab.key.weight.grad)
                        # In the inherited synchronous final layer the forecast
                        # reads edges, so that layer's next-node outputs are unused.
                        self.assertIsNone(model.layers[-1].mab.query.weight.grad)
                    else:
                        self.assertTrue(all(p.grad is None for p in model.inherent_embeddings.parameters()))

    def test_architecture_lineage_counts(self):
        self.assertEqual(sum(p.numel() for p in GraFITiAdapter().parameters()), 43400)
        self.assertEqual(sum(p.numel() for p in TPatchGNNAdapter().parameters()), 357682)
        self.assertEqual(sum(p.numel() for p in P12GraFITi(48).parameters()), 44744)


class ProtocolTests(unittest.TestCase):
    def test_code_parser_boundary_and_final_hour_compatibility(self):
        text = ('Time,Parameter,Value\n00:00,RecordID,123\n00:00,Weight,70\n'
                '00:10,HR,10\n00:20,HR,20\n01:00,HR,100\n01:10,HR,40\n'
                '02:00,HR,80\n02:10,HR,90\n')
        rid, values, mask, rows = parse_record(text)
        self.assertEqual(rid, 123)
        hr = FEATURES.index('HR')
        self.assertEqual(values[0, hr], 15.)
        self.assertEqual(values[1, hr], 40.)
        self.assertFalse(mask[2].any())
        self.assertEqual(np.flatnonzero(rows).tolist(), [0, 1])
        self.assertFalse(mask[:, FEATURES.index('Weight')].any())

    def test_split_is_disjoint_and_matches_shuffle_split_semantics(self):
        train, val, test = code_split(12000)
        self.assertEqual([len(train), len(val), len(test)], [8160, 2040, 1800])
        self.assertEqual(len(set(train) | set(val) | set(test)), 12000)
        first = np.random.RandomState(0).permutation(12000)
        np.testing.assert_array_equal(test, first[:1800])
        self.assertTrue(np.array_equal(code_split(12000)[0], train))

    def test_normalization_population_std_then_five_sigma_removal(self):
        values = np.zeros((2, 3, 1)); mask = np.ones_like(values, dtype=bool)
        values[1] = 4.
        scaled, retained, mean, std, counts = normalize(values, mask)
        np.testing.assert_allclose(mean, [2.])
        np.testing.assert_allclose(std, [2.0000001])
        self.assertTrue(retained.all())
        np.testing.assert_allclose(scaled[0], -1., atol=1e-6)
        values = np.zeros((1, 100, 1)); values[0, -1, 0] = 100.
        scaled, retained, *_ = normalize(values, np.ones_like(values, dtype=bool))
        self.assertFalse(retained[0, -1, 0])
        self.assertEqual(scaled[0, -1, 0], 0.)

    def test_inclusive_context_and_next_stored_target_times(self):
        values = np.zeros((1, 49, 37), np.float32)
        mask = np.zeros_like(values, dtype=bool)
        rows = np.zeros((1, 49), dtype=bool)
        rows[0, [36, 38, 40, 41, 44]] = True
        mask[0, [36, 38, 40, 41, 44], 0] = True
        dataset = P12Windows(values, mask, rows, np.array([123]), [0], 48.)
        batch = dataset[0]
        self.assertEqual(batch['values'].shape, (37, 37))
        self.assertEqual(batch['mask'][36, 0], 1.)
        torch.testing.assert_close(batch['target_times'], torch.tensor([38., 40., 41.]) / 48)

    def test_p12_explicit_times_and_query_values_never_exposed(self):
        torch.manual_seed(3)
        model = P12GraFITi(48.).eval()
        batch = sample(37, 37, 3)
        batch['context_times'] = torch.arange(37).float()[None].expand(2, -1) / 48
        batch['target_times'] = torch.tensor([[37., 39., 41.], [38., 40., 42.]]) / 48
        batch['target_mask'][:, 0, 0] = 0
        channels, times, edges, present = model.initial_graph(batch, 3)
        self.assertFalse(present[:, 37, 0].any())
        self.assertFalse(edges[:, 37, 0].any())
        torch.testing.assert_close(times[:, 37:], torch.sin(model.time_embedding(
            batch['target_times'].unsqueeze(-1))))
        prediction = model(batch, 3)
        altered = {**batch, 'target': torch.full_like(batch['target'], float('nan'))}
        torch.testing.assert_close(prediction, model(altered, 3), rtol=0, atol=0)
        self.assertTrue(torch.isfinite(prediction).all())

    def test_masked_metric_pooling(self):
        p = torch.tensor([[[2., float('nan')]], [[1., 1.]]])
        target = torch.zeros_like(p)
        mask = torch.tensor([[[1., 0.]], [[1., 1.]]])
        self.assertEqual(pooled_mse(p, target, mask).item(), 2.)

    def test_owned_outputs(self):
        for bad in ('/tmp/historical_experiment.json', ROOT.parent / 'outside.json', ROOT / '.git/result.json'):
            with self.subTest(path=bad), self.assertRaises(ValueError):
                owned_path(bad)

    def test_host_grid_has_exactly_24_unique_executable_commands(self):
        result = subprocess.run(['bash', str(ROOT / 'run_host_e5.sh'), '--dry-run'],
                                capture_output=True, text=True, check=True)
        commands = result.stdout.splitlines()
        self.assertEqual(len(commands), 24)
        self.assertEqual(len(set(commands)), 24)
        keys, outputs = set(), set()
        for line in commands:
            argv = shlex.split(line)
            self.assertEqual(argv[0], "python3")
            keys.add(tuple(argv[argv.index(key) + 1] for key in ('--model', '--graph', '--seed')))
            outputs.add(argv[argv.index('--out') + 1])
            self.assertEqual(argv[argv.index('--epochs') + 1], '35')
            self.assertEqual(argv[argv.index('--batch-size') + 1], '128')
        self.assertEqual(len(keys), 24)
        self.assertEqual(len(outputs), 24)


if __name__ == '__main__':
    unittest.main(verbosity=2)
