"""Exercise the release verifier and planted defects without model dependencies."""
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

EXPERIMENT = Path(__file__).resolve().parents[1]
RELEASE = EXPERIMENT.parents[1]
VERIFIER = 'experiments/counterfactual_onset_matched/verify_artifacts.py'
HOST = 'experiments/counterfactual_onset_matched/artifacts/host'


def run_verifier(release):
    return subprocess.run([sys.executable, '-B', VERIFIER], cwd=release,
                          capture_output=True, text=True)


@contextmanager
def copied_release():
    with tempfile.TemporaryDirectory(prefix='e3-verifier-') as scratch:
        release = Path(scratch) / 'release'
        shutil.copytree(RELEASE, release)
        yield release


def sample_records(release):
    inventory = json.loads((release / HOST / 'E3_EFFECTIVE_INVENTORY.json').read_text())
    return [inventory['effective_records'][0]['path'],
            next(r['path'] for r in inventory['effective_records'] if '/main_rerun/' in r['path']),
            inventory['superseded_records'][0]['path'],
            f'{HOST}/crn_diagnostic/control_gru/seed0/run.json',
            f'{HOST}/crn_diagnostic/lambda0/epochs60/seed0/run.json']


class VerifyArtifactsTests(unittest.TestCase):
    def test_release_tree_passes(self):
        result = run_verifier(RELEASE)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['physical_run_records'], 192)
        self.assertEqual(report['effective_run_records'], 188)
        self.assertEqual(report['superseded_run_records'], 4)
        self.assertEqual(report['plans'], {'core': 184, 'matched-control': 4, 'lite-lambda': 120,
                                          'temporal': 160, 'legacy': 384, 'all': 304})

    def test_missing_record_fails(self):
        with copied_release() as release:
            for relative in sample_records(release):
                with self.subTest(record=relative):
                    path = release / relative
                    original = path.read_bytes()
                    path.unlink()
                    try:
                        result = run_verifier(release)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(f"missing run.json: ['{relative}']", result.stderr)
                    finally:
                        path.write_bytes(original)

    def test_unlisted_record_fails(self):
        with copied_release() as release:
            for branch in ('main_rerun', 'crn_diagnostic'):
                with self.subTest(branch=branch):
                    relative = f'{HOST}/{branch}/unlisted/run.json'
                    path = release / relative
                    path.parent.mkdir(parents=True)
                    shutil.copyfile(release / sample_records(release)[0], path)
                    try:
                        result = run_verifier(release)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(f"unlisted run.json: ['{relative}']", result.stderr)
                    finally:
                        path.unlink()

    def test_hash_mismatch_fails(self):
        with copied_release() as release:
            for relative in sample_records(release):
                with self.subTest(record=relative):
                    path = release / relative
                    original = path.read_bytes()
                    # Whitespace keeps the JSON and finite/smoke fields valid.
                    path.write_bytes(original + b'\n')
                    try:
                        result = run_verifier(release)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(f'SHA-256 mismatch for {relative}:', result.stderr)
                    finally:
                        path.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
