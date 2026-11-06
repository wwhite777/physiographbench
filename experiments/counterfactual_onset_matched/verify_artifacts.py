"""Check released run inventory, numeric statuses, and dry-run plans without fitting."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def verify():
    records = sorted((ROOT / 'artifacts/host').glob('**/run.json'))
    assert len(records) == 188
    assert all(json.loads(p.read_text()).get('finite') is True and json.loads(p.read_text()).get('smoke') is False for p in records)
    plans = {}
    for group, expected in [('core', 184), ('matched-control', 4), ('lite-lambda', 120),
                            ('temporal', 160), ('legacy', 384), ('all', 304)]:
        result = subprocess.run(['bash', str(ROOT / 'run_host_e3.sh'), '--group', group, '--dry-run'],
                                capture_output=True, text=True, check=True)
        assert len(result.stdout.splitlines()) == expected
        plans[group] = expected
    print(json.dumps({'complete_run_records': len(records), 'plans': plans,
                      'scope': 'released records and command plans; no residual arrays or historical archive replay'}))


if __name__ == '__main__':
    verify()
