"""CPU inference/protocol tests with 64 synthetic stays; no fitting or downloads."""
from pathlib import Path
import ast
import json
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from renal_protocol import PROJECT, SCRATCH, make_data, seed_all
from renal_diagnosis import aggregate, stratum_masks
from shared_input_variant import build_variant, check_sources, control_jobs, selected_config
import numpy as np
import torch
from organ_graph_ssm_model import build_model

torch.set_num_threads(2)


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


class InputScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix="renal-fixture-", dir=SCRATCH)
        cls.addClassCleanup(cls.fixture.cleanup)
        fixture = Path(cls.fixture.name) / "cohort.npz"
        synthetic_cohort(fixture)
        cls.loaders, cls.meta = make_data(fixture, max_stays=64, batch=16)
        cls.batch = next(iter(cls.loaders[0]))

    def test_actual_context_and_rollout_input_widths(self):
        self.assertEqual(sum(self.meta["counts"].values()), 64)
        for mode, widths in (("partitioned", (4, 4, 3, 5)), ("shared", (16,) * 4)):
            model = build_variant(mode).eval()
            self.assertEqual(model.node_input_widths, widths)
            full_widths = tuple(2 * d + 5 for d in widths)
            assembled = model._organ_inputs(self.batch["values"], self.batch["mask"],
                                            self.batch["static"], None)
            self.assertEqual(tuple(x.shape[-1] for x in assembled), full_widths)
            self.assertEqual(tuple(p.in_features for p in model.in_proj), full_widths)
            seen = [[] for _ in widths]
            hooks = [projection.register_forward_pre_hook(
                lambda module, inputs, i=i: seen[i].append(inputs[0].shape[-1]))
                for i, projection in enumerate(model.step_proj)]
            with torch.no_grad():
                pred = model(self.batch, horizon=12)
            for hook in hooks:
                hook.remove()
            self.assertEqual(tuple(pred.shape), (16, 12, 16))
            self.assertTrue(torch.isfinite(pred).all())
            self.assertEqual(seen, [[w] * 12 for w in full_widths])
            self.assertFalse(model.cfg.edges)
            if mode == "shared":
                for x in assembled:
                    torch.testing.assert_close(x[..., :16], self.batch["values"])
                    torch.testing.assert_close(x[..., 16:32], self.batch["mask"])

    def test_partitioned_is_frozen_no_edge_model(self):
        sizes = selected_config()["sizes"]
        seed_all(7)
        frozen = build_model("cinc", d_model=sizes["d_model"], d_state=sizes["d_state"],
                              n_layers=sizes["n_layers"], edges="none", node_type="gru").eval()
        seed_all(7)
        control = build_variant("partitioned").eval()
        self.assertEqual(set(frozen.state_dict()), set(control.state_dict()))
        for name, value in frozen.state_dict().items():
            torch.testing.assert_close(value, control.state_dict()[name], rtol=0, atol=0)
        with torch.no_grad():
            torch.testing.assert_close(frozen(self.batch), control(self.batch), rtol=0, atol=0)

    def test_shared_projection_can_embed_the_frozen_partition(self):
        # This checks feature/mask/static order in context AND every forecast
        # step, independently of the node_input_widths metadata.
        seed_all(3)
        partitioned = build_variant("partitioned").eval()
        seed_all(3)
        shared = build_variant("shared").eval()
        for name, value in partitioned.state_dict().items():
            if not name.startswith(("in_proj.", "step_proj.")):
                torch.testing.assert_close(value, shared.state_dict()[name], rtol=0, atol=0)
        with torch.no_grad():
            for group in ("in_proj", "step_proj"):
                for i, (a, b) in enumerate(partitioned.slices):
                    d = b - a
                    old, new = getattr(partitioned, group)[i], getattr(shared, group)[i]
                    new.weight.zero_()
                    new.weight[:, a:b].copy_(old.weight[:, :d])
                    new.weight[:, 16+a:16+b].copy_(old.weight[:, d:2*d])
                    new.weight[:, 32:].copy_(old.weight[:, 2*d:])
                    new.bias.copy_(old.bias)
            torch.testing.assert_close(shared(self.batch), partitioned(self.batch), atol=2e-6, rtol=2e-5)

    def test_nonrenal_context_has_access_only_in_shared_no_edge_control(self):
        changed = {**self.batch, "values": self.batch["values"].clone()}
        changed["values"][:, :, :4] += 2
        for mode in ("partitioned", "shared"):
            seed_all(5)
            model = build_variant(mode).eval()
            with torch.no_grad():
                original = model(self.batch)[:, :, 8:11]
                perturbed = model(changed)[:, :, 8:11]
            if mode == "partitioned":
                torch.testing.assert_close(original, perturbed, rtol=0, atol=0)
            else:
                self.assertGreater(float((original - perturbed).abs().max()), 1e-4)


class ProtocolTests(unittest.TestCase):
    def test_sources_and_selection_are_the_distributed_copies(self):
        check_sources()
        selection = selected_config()
        self.assertEqual(selection["lr"], .0005)
        self.assertEqual(selection["width"], "large")
        for name in ("organ_graph_ssm_model", "physiograph_data_loader",
                     "physiograph_training_runner", "clinical_timeseries_baselines"):
            self.assertEqual(Path(sys.modules[name].__file__).resolve().parent, PROJECT / "src")

    def test_helper_definitions_match_clinical_protocol(self):
        def definitions(path):
            source = path.read_text()
            return {n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        frozen = definitions(PROJECT / "tools/v4_protocol.py")
        local = definitions(HERE / "renal_protocol.py")
        for name, definition in local.items():
            self.assertEqual(definition, frozen[name], name)

    def test_training_loop_matches_clinical_protocol(self):
        # Compare the executable training/validation/checkpoint-selection loop,
        # excluding only its progress-message text and substituting fixed K=12.
        class Normalize(ast.NodeTransformer):
            def visit_Name(self, node):
                return ast.copy_location(ast.Constant(12), node) if node.id == "K" else node

            def visit_Expr(self, node):
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "print":
                    return None
                return self.generic_visit(node)

        def loop(path, function):
            tree = ast.parse(path.read_text())
            fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
            block = next(n for n in fn.body if isinstance(n, ast.With))
            return ast.dump(Normalize().visit(block), include_attributes=False)

        self.assertEqual(loop(HERE / "shared_input_variant.py", "train_control"),
                         loop(PROJECT / "tools/v4_protocol.py", "train_run"))

    def test_eight_unique_full_host_commands(self):
        jobs = control_jobs()
        self.assertEqual(len(jobs), 8)
        self.assertEqual(len({j["run_id"] for j in jobs}), 8)
        result = subprocess.run(["bash", str(HERE / "run.sh"), "--dry-run", "--device", "cuda"],
                                 check=True, capture_output=True, text=True)
        commands = result.stdout.splitlines()
        self.assertEqual(len(commands), 8)
        self.assertEqual(len(set(commands)), 8)
        for command in commands:
            self.assertIn("--epochs 35", command)
            self.assertIn("--device cuda", command)
            self.assertNotIn("--max-stays", command)
        for job, command in zip(jobs, commands):
            self.assertIn(f"--input_mode {job['input_mode']}", command)
            self.assertIn(f"--seed {job['seed']}", command)

    def test_strata_cover_stays_and_pool_by_target_entry(self):
        entries = np.array([0, 1, 3, 4, 36])
        masks = stratum_masks(entries)
        np.testing.assert_array_equal(sum(masks[k].astype(int) for k in ("0", "1–3", "≥4")), 1)
        errors = dict(context_entries=entries, renal_count=np.array([0, 1, 3, 2, 0]),
                      renal_sse=np.array([0., 4., 0., 8., 0.]),
                      feature_count=np.array([[0,0,0], [1,0,0], [1,1,1], [1,1,0], [0,0,0]]),
                      feature_sse=np.array([[0,0,0], [4,0,0], [0,0,0], [4,4,0], [0,0,0]]),
                      last_hour_entries=np.zeros(5))
        rows = aggregate(errors)
        self.assertIsNone(rows["0"]["RMSE"])
        self.assertEqual(rows["0"]["n_without_renal_targets"], 1)
        self.assertEqual(rows["all"]["renal_target_entries"], 6)
        self.assertAlmostEqual(rows["all"]["RMSE"], np.sqrt(12/6))
        self.assertAlmostEqual(rows["1–3"]["RMSE"], 1.)


if __name__ == "__main__":
    unittest.main()
