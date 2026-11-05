"""Synthetic CPU inference, frozen graph and protocol checks; no training."""
from pathlib import Path
import ast
import csv
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from renal_protocol import PROJECT, SCRATCH, metrics, seed_all, sha256
import shared_input_edge_variant as runner
import numpy as np
import torch

torch.set_num_threads(2)


def synthetic_batch():
    gen = torch.Generator().manual_seed(123)
    return dict(values=torch.randn(2, 12, 16, generator=gen),
                mask=(torch.rand(2, 12, 16, generator=gen) > 0.3).float(),
                static=torch.randn(2, 5, generator=gen))


class FrozenGraphTests(unittest.TestCase):
    def test_ordered_edges_match_all_six_frozen_variants_and_four_seeds(self):
        checks = json.loads((HERE / "EDGE_CHECKS.json").read_text())["checks"]
        for variant in runner.VARIANTS:
            edges = [list(e) for e in runner.edges_for(variant)]
            for seed in range(4):
                with self.subTest(variant=variant, seed=seed):
                    path = runner.frozen_edge_run(variant, seed)
                    record = next(r for r in checks if r["variant"] == variant and r["seed"] == seed)
                    self.assertEqual(record["path"], str(path.relative_to(PROJECT)))
                    self.assertTrue(record["ordered_equality"])
                    if path.exists():
                        self.assertEqual(sha256(path), record["sha256"])
                    self.assertEqual(record["variant"], variant)
                    self.assertEqual(record["seed"], seed)
                    self.assertEqual(edges, record["edges"])

    def test_resolver_disagreement_is_rejected_before_returning_edges(self):
        with patch.object(runner, "_resolve_edges", return_value=((0, 0),)):
            with self.assertRaisesRegex(ValueError, "edge-list equality failed for random"):
                runner.edges_for("random")
        with patch.dict(runner.EDGE_RUN_SHA256, random="0" * 64):
            with self.assertRaisesRegex(ValueError, "frozen edge record changed"):
                runner.edges_for("random")

    def test_random_graph_is_fixed_across_training_seeds(self):
        recorded = next(r["edges"] for r in json.loads((HERE / "EDGE_CHECKS.json").read_text())["checks"] if r["variant"] == "random")
        for seed in range(4):
            seed_all(seed)
            model = runner.build_variant("random")
            self.assertEqual([list(e) for e in model.cfg.edges], recorded)

    def test_shared_context_and_forecast_inputs_for_every_variant(self):
        batch = synthetic_batch()
        expected_context = torch.cat([
            batch["values"], batch["mask"], batch["static"][:, None].expand(-1, 12, -1)], -1)
        expected_first_step = torch.cat([
            batch["values"][:, -1], torch.ones(2, 16), batch["static"]], -1)
        for variant in runner.VARIANTS:
            with self.subTest(variant=variant):
                model = runner.build_variant(variant).eval()
                self.assertEqual(model.node_input_widths, (16,) * 4)
                for group in (model.in_proj, model.step_proj):
                    self.assertEqual([p.in_features for p in group], [37] * 4)
                self.assertEqual(model.slices, [(0, 4), (4, 8), (8, 11), (11, 16)])
                context, steps = [[] for _ in range(4)], [[] for _ in range(4)]
                hooks = []
                for projections, seen in ((model.in_proj, context), (model.step_proj, steps)):
                    for i, projection in enumerate(projections):
                        hooks.append(projection.register_forward_pre_hook(
                            lambda module, inputs, i=i, seen=seen:
                                seen[i].append(inputs[0].detach().clone())))
                try:
                    with torch.no_grad():
                        prediction = model(batch, horizon=12)
                finally:
                    for hook in hooks:
                        hook.remove()
                self.assertEqual(tuple(prediction.shape), (2, 12, 16))
                self.assertTrue(torch.isfinite(prediction).all())
                for i in range(4):
                    self.assertEqual(len(context[i]), 1)
                    torch.testing.assert_close(context[i][0], expected_context, rtol=0, atol=0)
                    self.assertEqual(len(steps[i]), 12)
                    torch.testing.assert_close(steps[i][0], expected_first_step, rtol=0, atol=0)
                    for t, actual in enumerate(steps[i]):
                        torch.testing.assert_close(actual, steps[0][t], rtol=0, atol=0)
                        torch.testing.assert_close(actual[:, 16:32], torch.ones(2, 16))
                        torch.testing.assert_close(actual[:, 32:], batch["static"])
                saved = json.loads((HERE / "runs" / variant / "seed0/run.json").read_text())
                self.assertEqual(model.n_params(), saved["n_params"])

    def test_no_edge_shared_model_exactly_matches_renal_diagnostic_for_all_paired_seeds(self):
        batch = synthetic_batch()
        for seed in range(4):
            with self.subTest(seed=seed):
                seed_all(seed)
                expected = runner._renal.build_variant("shared").eval()
                seed_all(seed)
                actual = runner.build_variant("none", input_mode="shared").eval()
                self.assertEqual(actual.n_params(), 778384)
                self.assertEqual(list(dict(actual.named_parameters())),
                                 list(dict(expected.named_parameters())))
                self.assertEqual(list(actual.state_dict()), list(expected.state_dict()))
                for name, value in expected.state_dict().items():
                    torch.testing.assert_close(actual.state_dict()[name], value, rtol=0, atol=0)
                with torch.no_grad():
                    torch.testing.assert_close(actual(batch), expected(batch), rtol=0, atol=0)


class ProtocolTests(unittest.TestCase):
    def test_local_helper_definitions_are_verbatim_renal_diagnostic(self):
        def definitions(path):
            text = path.read_text()
            return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        self.assertEqual(definitions(HERE / "renal_protocol.py"),
                         definitions(runner.RENAL_DIR / "renal_protocol.py"))
        self.assertEqual(Path(tempfile.gettempdir()), SCRATCH)
        self.assertTrue(SCRATCH.is_relative_to(PROJECT) or SCRATCH == Path(os.environ["TMPDIR"]).resolve())

    def test_training_validation_selection_loop_matches_renal_diagnostic(self):
        class RemoveProgress(ast.NodeTransformer):
            def visit_Expr(self, node):
                if (isinstance(node.value, ast.Call) and
                        isinstance(node.value.func, ast.Name) and node.value.func.id == "print"):
                    return None
                return self.generic_visit(node)

        def loop(path, function):
            tree = ast.parse(path.read_text())
            fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
            block = next(n for n in fn.body if isinstance(n, ast.With))
            return ast.dump(RemoveProgress().visit(block), include_attributes=False)
        self.assertEqual(loop(HERE / "shared_input_edge_variant.py", "train_variant"),
                         loop(runner.RENAL_DIR / "shared_input_variant.py", "train_control"))

    def test_metrics_pool_observations_and_handle_empty_denominators(self):
        # Stay-level RMSEs are 2 and 0; pooling 1+3 observations must give 1,
        # rather than sqrt(mean([4, 0])) or a stay-weighted summary.
        errors = dict(count=np.array([1, 3, 0]), sse=np.array([4., 0., 0.]),
                      sae=np.array([2., 0., 0.]), nonfinite=np.zeros(3, dtype=int),
                      organ_count=np.array([[1, 0], [3, 0], [0, 0]]),
                      organ_sse=np.array([[4., 0.], [0., 0.], [0., 0.]]))
        report = metrics(errors, ("observed", "empty"))
        self.assertEqual(report["pooled_masked_RMSE"], 1.)
        self.assertEqual(report["organs"]["observed"]["RMSE"], 1.)
        self.assertEqual(report["zero_target_stays"], 1)
        self.assertIsNone(report["organs"]["empty"]["RMSE"])

    def test_runner_refuses_existing_or_outside_destinations_and_invalid_budgets(self):
        occupied = HERE / "runs/none/seed0"
        original = sorted(occupied.iterdir())
        with self.assertRaises(FileExistsError):
            runner.train_variant("none", 0, occupied, epochs=1, max_stays=64)
        # Read-only path rejection: no mkdir or training is reached.
        with self.assertRaisesRegex(ValueError, "inside the repository"):
            runner.train_variant("none", 0, PROJECT.parent / "forbidden-output", epochs=1, max_stays=64)
        for kwargs in (dict(epochs=36), dict(max_stays=65), dict(input_mode="partitioned")):
            with self.assertRaises(ValueError):
                runner.train_variant("none", 0, occupied / "invalid", **kwargs)
        self.assertEqual(sorted(occupied.iterdir()), original)


class LauncherTests(unittest.TestCase):
    def run_launcher(self, *args):
        return subprocess.run(["bash", str(getattr(self, "launcher", HERE / "run.sh")), *args],
                              capture_output=True, text=True,
                              env={**os.environ, "PYTHON": "/bin/false"}, timeout=30)

    def test_dry_run_has_24_unique_complete_commands_and_flag_propagation(self):
        jobs = runner.variant_jobs()
        self.assertEqual(len(jobs), 24)
        self.assertEqual(len({j["run_id"] for j in jobs}), 24)
        for device in ("cpu", "cuda"):
            root = PROJECT / "runs/unused output root"
            result = self.run_launcher("--dry-run", "--device", device,
                                       "--threads", "3", "--batch", "17", "--output-root", str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.splitlines()
            self.assertEqual(len(lines), 24)
            self.assertEqual(len(set(lines)), 24)
            for job, line in zip(jobs, lines):
                tokens = shlex.split(line)
                for flag, value in (("--variant", job["variant"]), ("--input_mode", "shared"),
                                    ("--seed", str(job["seed"])), ("--epochs", "35"),
                                    ("--device", device), ("--threads", "3"), ("--batch", "17"),
                                    ("--output-dir", str((root / job["run_id"]).relative_to(PROJECT)))):
                    self.assertEqual(tokens[tokens.index(flag) + 1], value)
                self.assertNotIn("--max-stays", tokens)
            self.assertFalse(root.exists(), "dry-run must not create output directories")

    def test_launcher_preflights_last_destination_before_any_fit(self):
        fixture = tempfile.TemporaryDirectory(prefix="preflight-", dir=SCRATCH)
        self.addCleanup(fixture.cleanup)
        repo = Path(fixture.name)
        self.launcher = repo / "diagnostics/shared_input_edges/run.sh"
        self.launcher.parent.mkdir(parents=True)
        shutil.copyfile(HERE / "run.sh", self.launcher)
        root = repo / "runs/shared_input_edges"
        last = root / "misspecified-1/seed3"
        last.mkdir(parents=True)
        for dry_flag in ([], ["--dry-run"]):
            result = self.run_launcher("--output-root", str(root), *dry_flag)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("Refusing an existing run or log", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertFalse((root / "none").exists())

    def test_launcher_rejects_invalid_arguments_and_outside_output(self):
        for args in (("--device", "invalid"), ("--batch", "0"), ("--threads", "0"),
                     ("--output-root", str(PROJECT.parent)), ("--device",), ("--unknown",)):
            result = self.run_launcher(*args)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout, "")


def synthetic_cohort(path):
    rng = np.random.default_rng(19)
    payload = {}
    for cohort, n in (("A", 48), ("B", 16)):
        payload.update({f"{cohort}_{key}": value for key, value in dict(
            values=rng.normal(size=(n, 24, 16)).astype("f4"),
            mask=(rng.random((n, 24, 16)) > .6).astype("f4"),
            static=rng.normal(size=(n, 5)).astype("f4"),
            sepsis=np.zeros((n, 24), "f4"), length=np.full(n, 24, "i4")).items()})
    payload.update(train_idx=np.arange(16), val_idx=np.arange(16, 32), test_idx=np.arange(32, 48),
        norm_mean=np.zeros(16, "f4"), norm_std=np.ones(16, "f4"),
        features=np.asarray([f"feature{i}" for i in range(8)] +
                            ["Creatinine", "BUN", "Potassium"] + [f"feature{i}" for i in range(11, 16)]),
        organ_slices=np.asarray([[0, 4], [4, 8], [8, 11], [11, 16]]),
        organ_names=np.asarray(["cardiovascular", "pulmonary", "renal", "metabolic"]))
    np.savez_compressed(path, **payload)



class SyntheticInferenceTests(unittest.TestCase):
    def test_64_synthetic_stays_load_and_infer_without_fitting(self):
        with tempfile.TemporaryDirectory(prefix="edge-fixture-", dir=SCRATCH) as temp:
            fixture = Path(temp) / "cohort.npz"
            synthetic_cohort(fixture)
            loaders, meta = runner.make_data(fixture, max_stays=64, batch=16)
            self.assertEqual(meta["counts"], {"train": 16, "val": 16, "A": 16, "B": 16})
            for variant in runner.VARIANTS:
                model = runner.build_variant(variant).eval()
                errors = runner.collect_errors(model, loaders[2], organ_slices=meta["organ_slices"])
                report = metrics(errors, meta["organ_names"])
                self.assertEqual(report["n_stays"], 16)
                self.assertEqual(report["nonfinite_predictions"], 0)
                self.assertTrue(np.isfinite(report["pooled_masked_RMSE"]))


if __name__ == "__main__":
    unittest.main()
