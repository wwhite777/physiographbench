"""Frozen evidence, validation-only selection, launcher safety, and bounded smokes."""
from pathlib import Path
import ast
import csv
import json
import math
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
from renal_protocol import PROJECT, SCRATCH, metrics, seed_all, sha256, write_json
import shared_input_primary as runner
import numpy as np
import torch
from torch import nn

torch.set_num_threads(2)


def new_root(prefix):
    return Path(tempfile.mkdtemp(prefix=prefix, dir=SCRATCH))


def synthetic_batch():
    gen = torch.Generator().manual_seed(123)
    return dict(values=torch.randn(2, 12, 16, generator=gen),
                mask=(torch.rand(2, 12, 16, generator=gen) > 0.3).float(),
                static=torch.randn(2, 5, generator=gen))


def fixture_grid(root, vals=None, *, scope="full"):
    for i, job in enumerate(runner.grid_jobs()):
        record = dict(task=runner.TASK, stage="grid", arm="none", **job,
                      scope=scope, epochs_budget=35 if scope == "full" else 1, batch=16,
                      data=dict(cohort_sha256=runner.COHORT_SHA256,
                                max_stays=None if scope == "full" else 64),
                      status="complete", validation_RMSE=1. if vals is None else vals[i],
                      A=dict(pooled_masked_RMSE=100 - i), B=dict(pooled_masked_RMSE=i))
        write_json(root / "grid" / job["cfg"] / "seed0/run.json", record)


class FrozenModelTests(unittest.TestCase):
    def test_helper_definitions_are_verbatim_and_scratch_is_private(self):
        def definitions(path):
            text = path.read_text()
            return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        self.assertEqual(definitions(HERE / "renal_protocol.py"),
                         definitions(runner.EDGE_DIR / "renal_protocol.py"))
        self.assertEqual(Path(tempfile.gettempdir()), SCRATCH)
        self.assertTrue(SCRATCH.is_dir())

    def test_frozen_sources_and_width_definitions(self):
        runner.check_sources()
        s = json.loads(runner.V4_SELECTION.read_text())
        for width in runner.WIDTHS:
            self.assertEqual(runner.sizes_for(width), s["width_definition"]["physiograph_gru"][width])
        self.assertEqual(len(runner.grid_jobs()), 6)
        self.assertEqual({j["lr"] for j in runner.grid_jobs()}, {0.0005, 0.001, 0.002})

    def test_ordered_edges_equal_frozen_records_for_all_training_seeds(self):
        checks = json.loads((runner.EDGE_DIR / 'EDGE_CHECKS.json').read_text())['checks']
        for arm in ('none', 'admissible', 'dense', 'reversed', 'misspecified-1'):
            actual = [list(e) for e in runner.edges_for(arm)]
            records = [r for r in checks if r['variant'] == arm]
            self.assertEqual(len(records), 4)
            for record in records:
                self.assertEqual(actual, record['edges'])

    def test_random_draws_are_distinct_pinned_and_independent_of_fit_seed(self):
        expected = (
            ((0, 1), (0, 3), (1, 0), (1, 2), (2, 0), (2, 3), (3, 1), (3, 2)),
            ((0, 1), (0, 2), (0, 3), (1, 0), (1, 3), (2, 1), (3, 0), (3, 2)),
            ((0, 1), (0, 2), (0, 3), (1, 0), (1, 2), (2, 3), (3, 1), (3, 2)))
        self.assertEqual(len(set(expected)), 3)
        for i, edges in enumerate(expected):
            for seed in range(4):
                seed_all(seed)
                self.assertEqual(runner.edges_for(f"random_s{i}"), edges)
            evidence = runner.edge_evidence(f"random_s{i}")
            self.assertEqual(evidence["jaccard_with_admissible"], (5/11, 6/10, 5/11)[i])
            print("RANDOM evidence:", json.dumps(evidence), flush=True)
        self.assertEqual(expected[0], runner._shared_edges.edges_for("random"))

    def test_none_exactly_reproduces_shared_edge_weights_and_forward_at_both_widths(self):
        batch = synthetic_batch()
        for width in runner.WIDTHS:
            for seed in range(4):
                with self.subTest(width=width, seed=seed):
                    sizes = runner.sizes_for(width)
                    seed_all(seed)
                    old = runner._shared_edges.build_variant("none", sizes=sizes)
                    seed_all(seed)
                    new = runner.build_arm("none", sizes)
                    self.assertEqual(list(new.state_dict()), list(old.state_dict()))
                    for name, value in old.state_dict().items():
                        torch.testing.assert_close(new.state_dict()[name], value, rtol=0, atol=0)
                    for training in (False, True):
                        old.train(training)
                        new.train(training)
                        seed_all(99)
                        expected = old(batch, horizon=2)
                        seed_all(99)
                        actual = new(batch, horizon=2)
                        torch.testing.assert_close(actual, expected, rtol=0, atol=0)

    def test_all_arms_share_full_context_and_forecast_inputs(self):
        batch = synthetic_batch()
        context = torch.cat([batch["values"], batch["mask"],
                             batch["static"][:, None].expand(-1, 12, -1)], -1)
        first_step = torch.cat([batch["values"][:, -1], torch.ones(2, 16), batch["static"]], -1)
        for arm in runner.ARMS:
            with self.subTest(arm=arm):
                model = runner.build_arm(arm, runner.sizes_for("small")).eval()
                seen_context, seen_step = [[] for _ in range(4)], [[] for _ in range(4)]
                hooks = []
                for projections, seen in ((model.in_proj, seen_context), (model.step_proj, seen_step)):
                    for i, projection in enumerate(projections):
                        self.assertEqual(projection.in_features, 37)
                        hooks.append(projection.register_forward_pre_hook(
                            lambda module, inputs, i=i, seen=seen: seen[i].append(inputs[0].detach().clone())))
                try:
                    with torch.no_grad():
                        pred = model(batch, horizon=2)
                finally:
                    for hook in hooks:
                        hook.remove()
                self.assertTrue(torch.isfinite(pred).all())
                self.assertEqual(tuple(pred.shape), (2, 2, 16))
                self.assertEqual(model.node_input_widths, (16, 16, 16, 16))
                self.assertEqual(model.slices, [(0, 4), (4, 8), (8, 11), (11, 16)])
                for i in range(4):
                    torch.testing.assert_close(seen_context[i][0], context, rtol=0, atol=0)
                    torch.testing.assert_close(seen_step[i][0], first_step, rtol=0, atol=0)
                    torch.testing.assert_close(seen_step[i][1][:, :16], pred[:, 0], rtol=0, atol=0)
                    torch.testing.assert_close(seen_step[i][1][:, 16:32], torch.ones(2, 16))

    def test_none_norm_retains_original_norm_and_has_zero_messages(self):
        for width in runner.WIDTHS:
            seed_all(7)
            base = runner.build_arm("none", runner.sizes_for(width))
            seed_all(7)
            model = runner.build_arm("none_norm", runner.sizes_for(width))
            self.assertEqual(model.n_params(), base.n_params())
            self.assertEqual(model.cfg.edges, ())
            hidden = torch.randn(2, 4, model.cfg.d_model, requires_grad=True)
            for raw, wrapped in zip(base.couplers, model.couplers):
                self.assertEqual(len(wrapped.msg), 0)
                self.assertEqual(len(wrapped.gate), 0)
                torch.testing.assert_close(wrapped.norm.weight, raw.norm.weight, rtol=0, atol=0)
                norm_inputs = []
                hook = wrapped.norm.register_forward_pre_hook(lambda m, x: norm_inputs.append(x[0]))
                out, gates = wrapped(hidden)
                hook.remove()
                torch.testing.assert_close(norm_inputs[0] - hidden, torch.zeros_like(hidden), rtol=0, atol=0)
                torch.testing.assert_close(out, wrapped.norm(hidden), rtol=0, atol=0)
                self.assertEqual(tuple(gates.shape), (2, 0))
                self.assertIs(raw(hidden)[0], hidden)
                self.assertFalse(torch.equal(out, hidden))
                out.square().sum().backward()
                self.assertIsNotNone(wrapped.norm.weight.grad)
                self.assertGreater(wrapped.norm.weight.grad.abs().max().item(), 0.)
            print("NONE_NORM evidence:", width, model.n_params(), "empty msg/gate modules; LayerNorm receives hidden + 0", flush=True)

    def test_none_norm_matches_simulator_empty_branch_source(self):
        path = PROJECT / "sim/sim_grid_runner.py"
        tree = ast.parse(path.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "_MatchedCoupling")
        forward = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "forward")
        expected = forward.body[0].body[0]
        ours = ast.parse((HERE / "shared_input_primary.py").read_text())
        cls = next(n for n in ours.body if isinstance(n, ast.ClassDef) and n.name == "NormalisationRetainingCoupling")
        forward = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "forward")
        self.assertEqual(ast.dump(forward.body[0]), ast.dump(expected))

    def test_pmatch_exact_count_and_every_added_parameter_affects_predictions(self):
        for width, count in (("small", 423712), ("large", 930464)):
            seed_all(0)
            model = runner.build_arm("none_pmatch", runner.sizes_for(width)).eval()
            admissible = runner.build_arm("admissible", runner.sizes_for(width))
            self.assertEqual(model.n_params(), admissible.n_params())
            self.assertEqual(model.n_params(), count)
            self.assertEqual(model.cfg.edges, ())
            self.assertEqual(model.pmatch["achieved_n_params"], count)
            model(synthetic_batch(), horizon=2).square().mean().backward()
            for group in (model.in_proj, model.step_proj):
                for projection in group:
                    for name, parameter in projection.named_parameters():
                        self.assertIsNotNone(parameter.grad, name)
                        self.assertTrue(torch.isfinite(parameter.grad).all(), name)
                        self.assertTrue((parameter.grad != 0).all(), name)
            print("PMATCH evidence:", width, json.dumps(model.pmatch), flush=True)


class SelectionTests(unittest.TestCase):
    def test_selection_is_blind_to_A_test_and_B_and_uses_lexical_ties(self):
        root = new_root("selection-blind-")
        fixture_grid(root)
        before = runner.select_grid(root)
        self.assertEqual(before["selected"]["cfg"], "lr0.0005_large")
        self.assertEqual(len(before["grid"]), 6)
        for p in (root / "grid").glob("*/seed0/run.json"):
            r = json.loads(p.read_text())
            r["A"] = dict(pooled_masked_RMSE=-1e20)
            r["B"] = dict(pooled_masked_RMSE=1e20 if "large" in str(p) else -1e20)
            write_json(p, r)
        self.assertEqual(runner.select_grid(root)["selected"], before["selected"] | {
            "grid_run_sha256": sha256(Path(before["selected"]["grid_run"]))})

    def test_best_validation_wins_and_failed_cells_remain_in_inventory(self):
        root = new_root("selection-failed-")
        fixture_grid(root, [0.01, .8, .7, .5, .6, .9])
        first = root / "grid/lr0.0005_small/seed0/run.json"
        record = json.loads(first.read_text())
        record["status"] = "failed"
        write_json(first, record)
        s = runner.select_grid(root)
        self.assertEqual(s["selected"]["cfg"], "lr0.001_large")
        self.assertEqual(s["grid"][0]["record"]["status"], "failed")

    def test_incomplete_grid_does_not_write_selection(self):
        root = new_root("selection-incomplete-")
        self.assertIsNone(runner.maybe_write_selection(root))
        self.assertFalse((root / "selection_shared.json").exists())
        with self.assertRaisesRegex(ValueError, "grid incomplete"):
            runner.select_grid(root)

    def test_inconsistent_grid_or_wrong_identity_is_rejected(self):
        for key, value, error in (("seed", 1, "identity"), ("batch", 32, "inconsistent"),
                                  ("epochs_budget", 34, "inconsistent")):
            root = new_root("selection-invalid-")
            fixture_grid(root)
            path = root / "grid/lr0.0005_small/seed0/run.json"
            record = json.loads(path.read_text())
            record[key] = value
            write_json(path, record)
            with self.assertRaisesRegex(ValueError, error):
                runner.select_grid(root)

    def test_all_failed_is_blocked(self):
        root = new_root("selection-blocked-")
        fixture_grid(root)
        for path in (root / "grid").glob("*/seed0/run.json"):
            record = json.loads(path.read_text())
            record.update(status="failed", validation_RMSE=None)
            write_json(path, record)
        self.assertEqual(runner.select_grid(root)["selected"]["status"], "blocked")

    def test_selection_is_written_once_and_tampering_scope_or_batch_is_rejected(self):
        root = new_root("selection-read-")
        fixture_grid(root, scope="smoke")
        runner.maybe_write_selection(root)
        path = root / "selection_shared.json"
        chosen, provenance = runner.read_shared_selection(path, max_stays=64, batch=16)
        self.assertEqual(chosen["cfg"], "lr0.0005_large")
        self.assertEqual(provenance["scope"], "smoke")
        with self.assertRaises(FileExistsError):
            runner.maybe_write_selection(root)
        for kwargs in (dict(max_stays=None, batch=16), dict(max_stays=64, batch=128)):
            with self.assertRaisesRegex(ValueError, "differs"):
                runner.read_shared_selection(path, **kwargs)
        s = json.loads(path.read_text())
        s["selected"]["lr"] = 0.002
        write_json(path, s)
        with self.assertRaisesRegex(ValueError, "changed"):
            runner.read_shared_selection(path, max_stays=64, batch=16)


class TrainingRuleTests(unittest.TestCase):
    def test_metrics_pool_observed_entries(self):
        errors = dict(count=np.array([1, 3, 0]), sse=np.array([4., 0., 0.]),
                      sae=np.array([2., 0., 0.]), nonfinite=np.zeros(3, dtype=int),
                      organ_count=np.array([[1, 0], [3, 0], [0, 0]]),
                      organ_sse=np.array([[4., 0.], [0., 0.], [0., 0.]]))
        m = metrics(errors, ("observed", "empty"))
        self.assertEqual(m["pooled_masked_RMSE"], 1.)
        self.assertEqual(m["organs"]["observed"]["RMSE"], 1.)
        self.assertIsNone(m["organs"]["empty"]["RMSE"])

    def test_destination_and_budget_guards_precede_training(self):
        occupied = new_root("occupied-")
        kw = dict(lr=.0005, width="small", epochs=1, max_stays=64)
        with self.assertRaises(FileExistsError):
            runner.train_run("arms", "none", 0, occupied, **kw)
        with self.assertRaisesRegex(ValueError, "inside shared-input experiment"):
            runner.train_run("arms", "none", 0, HERE.parent / "forbidden-shared-input experiment-output", **kw)
        for stage, arm, epochs, cap in (("arms", "none", 36, None), ("grid", "none", 1, None),
                                       ("budget", "grud", 35, None), ("budget", "grud", 106, 64),
                                       ("arms", "none", 1, 65)):
            with self.assertRaises(ValueError):
                runner.train_run(stage, arm, 0, occupied / "invalid", lr=.0005,
                                 width="small", epochs=epochs, max_stays=cap)
        self.assertEqual(list(occupied.iterdir()), [])

    @unittest.skipIf(__import__("os").environ.get("PHYSIOGRAPH_NO_TRAINING") == "1", "optimizer steps disabled for release verification")
    def test_long_budgets_keep_patience_min_delta_and_validation_only_checkpoint(self):
        # A one-parameter synthetic model tests control flow, without cohort fits.
        class Tiny(nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = nn.Parameter(torch.tensor(.1))

            def forward(self, b, horizon=12):
                return self.weight.expand_as(b["target"])

        batch = dict(target=torch.zeros(1, 12, 16), target_mask=torch.ones(1, 12, 16))
        val_loader, a_loader, b_loader = object(), object(), object()
        meta = dict(cohort_sha256=runner.COHORT_SHA256, max_stays=None,
                    organ_slices=[(0, 16)], organ_names=["all"])
        for epochs in (70, 105):
            val_calls, split_calls = [], []

            def collect(model, loader, *args):
                if loader is val_loader:
                    val_calls.append(1)
                    rmse = 1. if len(val_calls) == 1 else .99995
                else:
                    self.assertGreaterEqual(len(val_calls), 9)
                    split_calls.append(loader)
                    rmse = 99. if loader is b_loader else .01
                return dict(count=np.ones(1), sse=np.array([rmse**2]), sae=np.array([rmse]),
                            nonfinite=np.zeros(1), organ_count=np.ones((1, 1)),
                            organ_sse=np.array([[rmse**2]]))

            root = new_root("synthetic-budget-")
            with patch.object(runner, "make_data", return_value=([[batch], val_loader, a_loader, b_loader], meta)), \
                 patch.object(runner, "build_any", return_value=Tiny()), \
                 patch.object(runner, "collect_errors", side_effect=collect):
                r = runner.train_run("budget", "grud", 0, root / "run", lr=.0005,
                                     width="large", epochs=epochs, batch=16, device="cpu")
            self.assertEqual(r["status"], "complete", r["failure"])
            self.assertEqual(r["epochs_completed"], 9)
            self.assertEqual(r["best_epoch"], 1)
            self.assertEqual(r["validation_RMSE"], 1.)
            self.assertEqual(split_calls, [a_loader, b_loader])
            self.assertEqual(r["scheduler_T_max"], epochs)
            self.assertAlmostEqual(r["training_curve"][1]["lr"], .0005*(1+math.cos(math.pi/epochs))/2)


class LauncherTests(unittest.TestCase):
    def launch(self, *args):
        return subprocess.run(["bash", str(HERE / "run_host_e2.sh"), *args],
                              capture_output=True, text=True, timeout=30,
                              env={**os.environ, "PYTHON": "/bin/false"})

    def test_dry_run_has_6_40_24_unique_commands_and_propagates_flags(self):
        for device in ("cpu", "cuda"):
            root = SCRATCH / "uncreated output root"
            p = self.launch("--dry-run", "--device", device, "--threads", "3", "--batch", "17", "--output-root", str(root))
            self.assertEqual(p.returncode, 0, p.stderr)
            lines = [line for line in p.stdout.splitlines() if not line.startswith("#")]
            self.assertEqual(len(lines), 70)
            self.assertEqual(len(set(lines)), 70)
            counts, paths = dict(grid=0, arms=0, budget=0), set()
            for line in lines:
                tokens = shlex.split(line)
                value = lambda flag: tokens[tokens.index(flag) + 1]
                stage = value("--stage")
                counts[stage] += 1
                paths.add(value("--output-dir"))
                for flag, expected in (("--device", device), ("--threads", "3"),
                                       ("--batch", "17"), ("--output-root", str(root))):
                    self.assertEqual(value(flag), expected)
                self.assertNotIn("--max-stays", tokens)
                if stage == "grid":
                    self.assertEqual(value("--seed"), "0")
                    self.assertEqual(value("--epochs"), "35")
                else:
                    self.assertEqual(value("--selection"), str(root / "selection_shared.json"))
                    self.assertIn(value("--epochs"), ("70", "105") if stage == "budget" else ("35",))
            self.assertEqual(counts, dict(grid=6, arms=40, budget=24))
            self.assertEqual(len(paths), 70)
            self.assertFalse(root.exists())

    def test_preflight_checks_last_destination_and_selection_before_any_fit(self):
        for conflict in ("budget/grud/epochs105/seed3", "selection_shared.json",
                         "logs/budget_grud_selected_selected_epochs105_seed3.log"):
            root = new_root("launcher-preflight-")
            path = root / conflict
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            for dry in ([], ["--dry-run"]):
                p = self.launch("--output-root", str(root), *dry)
                self.assertEqual(p.returncode, 2, p.stderr)
                self.assertIn("Refusing an existing", p.stderr)
                self.assertEqual(p.stdout, "")
                self.assertFalse((root / "grid").exists())

    def test_dangling_symlink_destination_is_refused(self):
        root = new_root("launcher-symlink-")
        path = root / "grid/lr0.0005_small/seed0"
        path.parent.mkdir(parents=True)
        path.symlink_to(root / "uncreated")
        p = self.launch("--dry-run", "--output-root", str(root))
        self.assertEqual(p.returncode, 2)
        self.assertEqual(p.stdout, "")
        self.assertTrue(path.is_symlink())

    def test_invalid_flags_and_outside_paths_are_rejected(self):
        for args in (("--device", "invalid"), ("--threads", "0"), ("--batch", "-1"),
                     ("--device",), ("--unknown",), ("--output-root", str(HERE.parent)),
                     ("--output-root", str(HERE))):
            p = self.launch(*args)
            self.assertEqual(p.returncode, 2, p.stderr)
            self.assertEqual(p.stdout, "")


@unittest.skipIf(__import__("os").environ.get("PHYSIOGRAPH_NO_TRAINING") == "1", "training disabled for release verification")
class SmokeTests(unittest.TestCase):
    def test_CPU_grid_selection_one_arm_and_frozen_grud_budget(self):
        root = new_root("cpu-smoke-")
        common = ["--device", "cpu", "--threads", "2", "--batch", "16", "--max-stays", "64",
                  "--epochs", "1", "--output-root", str(root)]
        jobs = [("grid", ["--stage", "grid", "--lr", str(j["lr"]), "--width", j["width"]],
                 root / "grid" / j["cfg"] / "seed0") for j in runner.grid_jobs()]
        jobs.extend([
            ("arms", ["--stage", "arms", "--arm", "none_norm", "--seed", "1"], root / "arms/none_norm/seed1"),
            ("budget", ["--stage", "budget", "--model", "grud", "--seed", "2"], root / "budget/grud/epochs1/seed2")])
        summary = []
        for i, (stage, args, dest) in enumerate(jobs):
            command = [sys.executable, "-B", str(HERE / "shared_input_primary.py"), *args, *common]
            print("CPU smoke:", shlex.join(command), flush=True)
            p = subprocess.run(command, capture_output=True, text=True, timeout=180)
            log = root / f"command_{i}.log"
            log.write_text(p.stdout + p.stderr)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            r = json.loads((dest / "run.json").read_text())
            self.assertEqual(r["status"], "complete", r["failure"])
            self.assertEqual(r["scope"], "smoke")
            self.assertEqual(r["stage"], stage)
            self.assertEqual(r["epochs_completed"], 1)
            self.assertEqual(r["best_epoch"], 1)
            self.assertEqual(sum(r["data"]["counts"].values()), 64)
            self.assertEqual(r["cublas_workspace_config"], ":4096:8")
            self.assertEqual(len(r["training_curve"]), 1)
            self.assertTrue(math.isfinite(r["training_curve"][0]["train_masked_mse"]))
            self.assertTrue(math.isfinite(r["training_curve"][0]["gradient_norm_max"]))
            for split in ("A_validation", "A", "B"):
                with np.load(dest / f"errors_{split}.npz", allow_pickle=False) as data:
                    errors = {key: data[key] for key in data.files}
                self.assertEqual(metrics(errors, r["data"]["organ_names"]), r[split])
                self.assertTrue(math.isfinite(r[split]["pooled_masked_RMSE"]))
                self.assertEqual(r[split]["nonfinite_predictions"], 0)
                self.assertTrue(all(math.isfinite(v["RMSE"]) for v in r[split]["organs"].values()))
            self.assertEqual(r["A_validation"]["pooled_masked_RMSE"], r["validation_RMSE"])
            with (dest / "curve.csv").open() as curve_file:
                rows = list(csv.DictReader(curve_file))
            self.assertEqual(len(rows), 1)
            ckpt = torch.load(dest / "checkpoint.pt", map_location="cpu", weights_only=True)
            if stage == "budget":
                expected = runner.frozen_selected("grud")
                self.assertEqual(r["lr"], expected["lr"])
                self.assertEqual(r["sizes"], expected["sizes"])
                model = runner.build_any("grud", n_static=5, **ckpt["sizes"])
            else:
                self.assertEqual(r["edges"], [list(e) for e in runner.edges_for(r["arm"])])
                model = runner.build_arm(ckpt["arm"], ckpt["sizes"])
            model.load_state_dict(ckpt["state_dict"], strict=True)
            self.assertEqual(sum(p.numel() for p in model.parameters()), r["n_params"])
            summary.append(dict(stage=stage, command=command, exit_code=p.returncode,
                                run=str(dest / "run.json"), log=str(log), arm=r["arm"],
                                lr=r["lr"], width=r["width"], seed=r["seed"], n_params=r["n_params"],
                                validation_RMSE=r["validation_RMSE"], A=r["A"], B=r["B"]))
            if i < 5:
                self.assertFalse((root / "selection_shared.json").exists())
            else:
                selection = json.loads((root / "selection_shared.json").read_text())
                self.assertEqual(len(selection["grid"]), 6)
                self.assertEqual(selection["scope"], "smoke")
                self.assertEqual(selection["selected"]["status"], "selected")
            print(f"SMOKE finite: {stage} {r['arm']} A-val={r['validation_RMSE']} A={r['A']['pooled_masked_RMSE']} B={r['B']['pooled_masked_RMSE']}", flush=True)
        write_json(HERE / "SMOKE_RESULTS.json", dict(scope="smoke", root=str(root),
                   epochs_per_fit=1, max_total_stays_per_fit=64, fits=summary))


if __name__ == "__main__":
    unittest.main(verbosity=2)
