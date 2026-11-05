#!/usr/bin/env python3
"""Regenerate simulator sets and verify every non-metadata array against frozen hashes."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_paths import ROOT
import argparse
import hashlib
import json
import shlex
import numpy as np
import sim_policy_ext as legacy
import sim_policy_ext2 as policy


def verify(path, expected):
    with np.load(path, allow_pickle=False) as data:
        actual_keys = set(data.files) - {'metadata_json'}
        if actual_keys != set(expected['arrays']):
            raise ValueError(f'{path}: array key mismatch')
        for key, ref in expected['arrays'].items():
            a = data[key]
            if str(a.dtype) != ref['dtype'] or list(a.shape) != ref['shape']:
                raise ValueError(f'{path}: dtype/shape mismatch for {key}')
            if hashlib.sha256(a.tobytes(order='C')).hexdigest() != ref['sha256']:
                raise ValueError(f'{path}: numerical payload mismatch for {key}')
    return len(actual_keys)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--group', choices=['forecast', 'policy', 'hourly', 'all'], default='all')
    ap.add_argument('--id', help='one inventory ID, e.g. forecast/h3_k1.0')
    ap.add_argument('--run', action='store_true', help='generate missing archives; default prints the plan')
    ap.add_argument('--verify-only', action='store_true')
    args = ap.parse_args()
    entries = json.loads((ROOT / 'manifests/simulator_datasets.json').read_text())['datasets']
    entries = [x for x in entries if (args.group == 'all' or x['group'] == args.group) and (not args.id or x['id'] == args.id)]
    if not entries:
        ap.error('no datasets selected')
    for record in entries:
        path = ROOT / record['path']
        if not (args.run or args.verify_only):
            print(shlex.join([sys.executable, 'tools/replay_simulators.py', '--id', record['id'], '--run']))
            continue
        if not path.exists():
            if args.verify_only:
                raise FileNotFoundError(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            settings = dict(record['generation_args'])
            if record['group'] == 'policy':
                policy.make_dataset_grid(**settings, out_path=path)
            else:
                legacy.make_dataset_grid(**settings, out_path=path)
                if record['group'] == 'hourly':
                    # The hourly index validates the generator/source fingerprints.
                    manifest = dict(settings, output_path=str(path),
                        output_sha256=legacy.sha256(path), code_sha256={
                            str(ROOT / 'sim/sim_policy_ext.py'): legacy.sha256(ROOT / 'sim/sim_policy_ext.py'),
                            str(legacy.SOURCE): legacy.sha256(legacy.SOURCE)})
                    path.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        count = verify(path, record)
        print(f'{record["id"]}: {count} array hashes PASS; archive={legacy.sha256(path)}', flush=True)

if __name__ == '__main__':
    main()
