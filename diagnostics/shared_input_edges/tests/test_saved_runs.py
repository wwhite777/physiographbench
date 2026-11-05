"""Check archived scores, curves, source locators and paired determinism."""
from pathlib import Path
import csv
import hashlib
import json
import statistics
import unittest

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
VARIANTS = ("none", "admissible", "dense", "reversed", "random", "misspecified-1")
TARGETS = ("pooled", "cardiovascular", "pulmonary", "renal", "metabolic")


def score(run, split, target):
    return (run[split]["pooled_masked_RMSE"] if target == "pooled" else
            run[split]["organs"][target]["RMSE"])


class SavedRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads((HERE / "shared_input_edges_summary.json").read_text())
        cls.runs = {(variant, seed): json.loads(
            (HERE / "runs" / variant / f"seed{seed}/run.json").read_text())
            for variant in VARIANTS for seed in range(4)}

    def test_all_24_runs_and_curves_are_complete(self):
        self.assertEqual(len(self.runs), 24)
        common_data = self.runs["none", 0]["data"]
        for (variant, seed), run in self.runs.items():
            with self.subTest(variant=variant, seed=seed):
                self.assertEqual(run["variant"], variant)
                self.assertEqual(run["seed"], seed)
                self.assertEqual(run["status"], "complete")
                self.assertEqual(run["scope"], "full")
                self.assertEqual(run["input_mode"], "shared")
                self.assertTrue(run["post_hoc"])
                self.assertFalse(run["retuned"])
                self.assertEqual(run["data"], common_data)
                self.assertEqual(run["epochs_completed"], 35)
                self.assertEqual(run["projection_input_widths"], [37] * 4)
                self.assertEqual(run["lr"], .0005)
                curve = ROOT / run["curve"]
                self.assertEqual(curve, HERE / "runs" / variant / f"seed{seed}/curve.csv")
                with curve.open() as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual([int(row["epoch"]) for row in rows], list(range(1, 36)))
                improved = [row for row in rows if row["improved"] == "True"]
                self.assertEqual(int(improved[-1]["epoch"]), run["best_epoch"])
                self.assertEqual(float(improved[-1]["val_RMSE"]), run["validation_RMSE"])
                cell = self.summary["runs"][variant][f"seed{seed}"]
                for split in ("A", "B"):
                    for target in TARGETS:
                        self.assertEqual(cell[split][target]["value"], score(run, split, target))

    def test_means_variation_and_all_paired_differences_match_saved_scores(self):
        for variant in VARIANTS:
            for split in ("A", "B"):
                pooled = [score(self.runs[variant, seed], split, "pooled") for seed in range(4)]
                cell = self.summary["pooled_summary"][variant][split]
                for field, value in (("mean", statistics.mean(pooled)),
                                     ("sd_sample", statistics.stdev(pooled)),
                                     ("minimum", min(pooled)), ("maximum", max(pooled)),
                                     ("span", max(pooled) - min(pooled))):
                    self.assertAlmostEqual(cell[field]["value"], value, places=14)
                for target in TARGETS:
                    paired = self.summary["paired_differences"][variant][split][target]
                    values = [score(self.runs[variant, seed], split, target) -
                              score(self.runs["none", seed], split, target) for seed in range(4)]
                    for seed, value in enumerate(values):
                        self.assertEqual(paired["per_seed"][f"seed{seed}"]["value"], value)
                    self.assertAlmostEqual(paired["mean"]["value"], statistics.mean(values), places=14)
                    self.assertEqual(paired["minimum"]["value"], min(values))
                    self.assertEqual(paired["maximum"]["value"], max(values))

    def test_no_edge_saved_runs_exactly_reproduce_renal_shared_arm(self):
        for seed in range(4):
            reference = json.loads((HERE.parent / "renal_shared_input/runs/shared" /
                                    f"seed{seed}/run.json").read_text())
            run = self.runs["none", seed]
            for field in ("validation_RMSE", "epochs_completed", "best_epoch", "n_params",
                          "A", "B", "data", "runtime"):
                self.assertEqual(run[field], reference[field], (seed, field))

    def test_summary_sources_resolve_with_original_distribution_fingerprints(self):
        inventory = json.loads((ROOT / "manifests/distribution.json").read_text())
        for label, source in self.summary["sources"].items():
            with self.subTest(source=label):
                relative = source["path"]
                self.assertFalse(Path(relative).is_absolute())
                self.assertTrue((ROOT / relative).is_file())
                entry = inventory[relative]
                self.assertEqual(source["sha256"], entry["original_sha256"])
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                                 entry["distributed_sha256"])
        self.assertEqual(self.summary["rendered_reading_markdown"],
                         (HERE / "SHARED_INPUT_EDGES_READING.md").read_text())


if __name__ == "__main__":
    unittest.main()
