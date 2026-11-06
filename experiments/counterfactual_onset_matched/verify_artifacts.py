"""Check released run inventory, numeric statuses, and dry-run plans without fitting."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
RELEASE_ROOT = ROOT.parents[1]


def verify():
    inventory = json.loads((ROOT / 'artifacts/host/E3_EFFECTIVE_INVENTORY.json').read_text())
    effective = {r['path']: r['sha256'] for r in inventory['effective_records']}
    superseded = {r['path']: r['sha256'] for r in inventory['superseded_records']}
    # The inventory covers the main grid. The 28 unchanged diagnostic/control
    # records use distributed-file hashes from the root checksum manifest.
    checksums = {path: digest for digest, path in
                 (line.split('  ', 1) for line in (RELEASE_ROOT / 'SHA256SUMS').read_text().splitlines())}
    diagnostic_root = f'{ROOT.relative_to(RELEASE_ROOT).as_posix()}/artifacts/host/crn_diagnostic'
    arms = ['control_gru'] + [f'lambda{lamb}/epochs{epochs}'
                             for lamb in ('0', '0.25', '1') for epochs in (60, 120)]
    for arm in arms:
        for seed in range(4):
            path = f'{diagnostic_root}/{arm}/seed{seed}/run.json'
            effective[path] = checksums[path]
    if len(effective) != 188 or len(superseded) != 4 or effective.keys() & superseded.keys():
        raise ValueError('Expected 188 effective and 4 distinct superseded run.json records')
    expected = {**effective, **superseded}
    records = sorted((ROOT / 'artifacts/host').glob('**/run.json'))
    physical = {p.relative_to(RELEASE_ROOT).as_posix() for p in records}
    missing = sorted(expected.keys() - physical)
    unlisted = sorted(physical - expected.keys())
    if missing or unlisted:
        raise ValueError(f'Run inventory mismatch; missing run.json: {missing}; unlisted run.json: {unlisted}')
    for p in records:
        path = p.relative_to(RELEASE_ROOT).as_posix()
        contents = p.read_bytes()
        digest = hashlib.sha256(contents).hexdigest()
        if digest != expected[path]:
            raise ValueError(f'SHA-256 mismatch for {path}: expected {expected[path]}, got {digest}')
        record = json.loads(contents)
        assert record.get('finite') is True and record.get('smoke') is False, path
    plans = {}
    for group, expected in [('core', 184), ('matched-control', 4), ('lite-lambda', 120),
                            ('temporal', 160), ('legacy', 384), ('all', 304)]:
        result = subprocess.run(['bash', str(ROOT / 'run_host_e3.sh'), '--group', group, '--dry-run'],
                                capture_output=True, text=True, check=True)
        assert len(result.stdout.splitlines()) == expected
        plans[group] = expected
    print(json.dumps({'physical_run_records': len(records), 'effective_run_records': len(effective),
                      'superseded_run_records': len(superseded), 'plans': plans,
                      'scope': 'released records and command plans; no residual arrays or historical archive replay'}))


if __name__ == '__main__':
    verify()
