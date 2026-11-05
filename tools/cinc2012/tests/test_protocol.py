"""Data-free regression checks for the portable plan and archived table route."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cinc2012_common import PROJECT, RUN_ROOT, MODELS, checkpoint_for, make_data, owned_path
from cinc2012_within_runner import run as within
from aggregate_cinc2012 import aggregate, reconstruct_table, stats
from host_driver import COMMAND_MANIFEST, main, plan


class PortableProtocolTests(unittest.TestCase):
    def test_default_plan_preserves_all_88_manifest_commands(self):
        expected = json.loads(COMMAND_MANIFEST.read_text())
        actual = plan()
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual["jobs"]), 88)
        for protocol in ("transfer", "within"):
            jobs = [job for job in actual["jobs"] if job["protocol"] == protocol]
            self.assertEqual({(job["model"], job["seed"]) for job in jobs},
                             {(model, seed) for model in MODELS for seed in range(4)})
            for job in jobs:
                command = job["command"]
                self.assertNotIn("--max-stays", command)
                self.assertTrue((PROJECT / command[3]).is_file())
                self.assertEqual(command[command.index("--batch") + 1], "128")
                if protocol == "transfer":
                    source = PROJECT / command[command.index("--checkpoint") + 1]
                    self.assertEqual(source, checkpoint_for(job["model"], job["seed"]))
                else:
                    self.assertEqual(command[command.index("--epochs") + 1], "35")

    def test_cpu_override_and_dry_run_print_exactly_88_commands(self):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(main(["--dry-run", "--device", "cpu", "--threads", "1"]), 0)
        self.assertEqual(len(output.getvalue().splitlines()), 88)
        self.assertEqual(json.loads(errors.getvalue())["total"], 88)
        for line in output.getvalue().splitlines():
            self.assertIn("--device cpu", line)
            self.assertIn("--threads 1", line)
            self.assertTrue(line.startswith("python3 -B -u tools/cinc2012/"))
        alternate = plan(PROJECT / "runs/cinc2012_repeat", ["cpu"], 1)
        for job in alternate["jobs"]:
            self.assertTrue(job["output"].startswith("runs/cinc2012_repeat/"))

    def test_invalid_devices_and_output_locations_are_rejected(self):
        for devices in (["cpu", "cpu"], ["cpu", "cuda:0"], ["unknown"], []):
            with self.assertRaises(ValueError):
                plan(devices=devices)
        with self.assertRaises(ValueError):
            plan(threads=0)
        with self.assertRaises(ValueError):
            owned_path(PROJECT / "results/new.json")
        with self.assertRaises(ValueError):
            plan(PROJECT.parent / "outside")

    def test_full_training_cannot_silently_use_smoke_budget(self):
        with self.assertRaises(ValueError):
            within("gru", 0, epochs=1)
        with self.assertRaises(ValueError):
            within("gru", 0, batch=64)
        for cap in (0, 7, 65):
            with self.assertRaises(ValueError):
                make_data(PROJECT / "data/unused.npz", "within", max_stays=cap)

    def test_archived_seed_summaries_reproduce_the_exact_shipped_table(self):
        parent = PROJECT / "runs/cinc2012-tests"
        parent.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="table-", dir=parent))
        self.addCleanup(shutil.rmtree, root)
        source = PROJECT / "results/clinical_v4_v1/cinc2012/cinc2012_results.json"
        destination = root / "TABLE.md"
        result = reconstruct_table(source, destination)
        self.assertEqual(result["completed_runs"], 88)
        self.assertEqual(destination.read_bytes(), source.with_name("TABLE_CINC2012.md").read_bytes())

    def test_strict_aggregation_rejects_an_empty_series(self):
        with self.assertRaises(ValueError):
            aggregate(RUN_ROOT / "nonexistent-empty-series")
        self.assertIsNone(stats([1.0])["sd"])
        self.assertAlmostEqual(stats([1.0, 3.0])["sd"], 2 ** 0.5)
        self.assertIsNone(stats([])["mean"])


if __name__ == "__main__":
    unittest.main()
