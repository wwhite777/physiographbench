"""Data-free coverage, provenance and corruption checks for the record index."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from leaderboard import build_leaderboard as board


class Leaderboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.source_count = board.build_records(ROOT)

    def test_complete_reported_inventory_and_exact_csv(self):
        self.assertEqual(self.source_count, 200)
        self.assertEqual(len(self.rows), 400)
        self.assertEqual(board.read_csv(ROOT / "leaderboard/LEADERBOARD.csv"), self.rows)
        self.assertEqual((ROOT / "leaderboard/LEADERBOARD.csv").read_bytes(),
                         board.csv_text(self.rows).encode("utf-8"))

    def test_all_metric_pointers_and_distributed_hashes(self):
        documents, hashes = {}, {}
        for row in self.rows:
            with self.subTest(record=row["run_record_path"]):
                metric = board.resolve(ROOT, row["run_record_path"], documents)
                key = "RMSE@12" if row["series"] == "clinical_learned_graph" else "pooled_masked_RMSE"
                self.assertEqual(row["value"], metric[key])
                counts = board.resolve(ROOT, row["denominator"]["source"], documents)
                self.assertEqual(row["denominator"]["observed_target_entries"], counts["observed_entries"])
                self.assertEqual(row["denominator"]["stays"], counts["n_stays"])
                self.assertEqual(row["denominator"]["zero_target_stays"], counts["zero_target_stays"])
                path = row["run_record_path"].partition("#")[0]
                if path not in hashes:
                    hashes[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                self.assertEqual(row["run_record_sha256"], hashes[path])

    def test_missing_seed_and_duplicate_evaluation_rejected(self):
        with self.assertRaisesRegex(ValueError, "Expected seeds"):
            board.validate_records(self.rows[1:])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            board.validate_records(self.rows + [self.rows[0]])

    def test_bad_denominator_and_nonfinite_score_rejected(self):
        for mutation in ["empty", "zero_target", "nonfinite"]:
            rows = copy.deepcopy(self.rows)
            if mutation == "empty":
                rows[0]["denominator"]["observed_target_entries"] = 0
            elif mutation == "zero_target":
                rows[0]["denominator"]["zero_target_stays"] = rows[0]["denominator"]["stays"] + 1
            else:
                rows[0]["value"] = float("nan")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                board.validate_records(rows)

    def test_unresolved_scores_and_missing_checkpoint_hashes_stay_labelled(self):
        excluded = [row for row in self.rows if row["comparison_status"] != "recorded"]
        self.assertEqual(len(excluded), 4)
        self.assertTrue(all(row["corpus"] == "CinC-2019" and row["method"] == "ncde"
                            and row["split"] == "B" for row in excluded))
        missing = [row for row in self.rows if row["checkpoint_status"] == "not_recorded_in_summary"]
        self.assertEqual(len(missing), 44)
        self.assertTrue(all(row["series"] == "cinc2012_within" and row["checkpoint_id"] is None
                            and row["checkpoint_sha256"] is None for row in missing))

    def test_transfer_pools_entries_before_square_root(self):
        groups = {}
        for row in self.rows:
            if row["series"] == "cinc2012_transfer":
                groups.setdefault((row["method"], row["seed"]), {})[row["split"]] = row
        self.assertEqual(len(groups), 44)
        for key, rows in groups.items():
            with self.subTest(model_seed=key):
                count = sum(rows[s]["denominator"]["observed_target_entries"] for s in ["testA", "testB"])
                sse = sum(rows[s]["value"] ** 2 * rows[s]["denominator"]["observed_target_entries"]
                          for s in ["testA", "testB"])
                self.assertEqual(count, rows["pooled"]["denominator"]["observed_target_entries"])
                self.assertAlmostEqual((sse / count) ** 0.5, rows["pooled"]["value"], places=12)

    def test_arm_inventory_matches_runs_degrees_and_overlap(self):
        inventory = board.load(ROOT, "experiments/shared_input_primary/E2_arm_inventory.json")
        self.assertEqual(len(inventory["arms"]), 40)
        admissible = {tuple(edge) for edge in next(a for a in inventory["arms"]
                                                  if a["arm"] == "admissible")["edges"]}
        for arm in inventory["arms"]:
            with self.subTest(arm=arm["arm"], seed=arm["seed"]):
                path = f"{board.SHARED}/arms/{arm['arm']}/seed{arm['seed']}/run.json"
                run = board.load(ROOT, path)
                for field in ["edges", "n_params", "sizes"]:
                    self.assertEqual(arm[field], run[field])
                edges = {tuple(edge) for edge in arm["edges"]}
                self.assertEqual(arm["in_degree"], [sum(v == i for u, v in edges) for i in range(4)])
                self.assertEqual(arm["out_degree"], [sum(u == i for u, v in edges) for i in range(4)])
                overlap = len(edges & admissible) / len(edges | admissible)
                self.assertAlmostEqual(arm["jaccard_with_admissible"], overlap, places=6)

    def test_json_schema_accepts_rows_and_rejects_corrupt_contract(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("optional jsonschema is unavailable; use --validate-schema where installed")
        schema = board.load(ROOT, "leaderboard/RECORD_SCHEMA.json")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        for row in self.rows:
            validator.validate(row)
        for field, value in [("seed", 4), ("metric", "mean_stay_RMSE"),
                             ("run_record_path", "../outside.json"),
                             ("run_record_sha256", "invalid"), ("value", -1)]:
            row = copy.deepcopy(self.rows[0])
            row[field] = value
            with self.subTest(field=field):
                self.assertFalse(validator.is_valid(row))


if __name__ == "__main__":
    unittest.main()
