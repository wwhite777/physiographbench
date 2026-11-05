#!/usr/bin/env python3
"""Verify the complete cohort archives and all frozen array payloads."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_paths import ROOT
import argparse
import hashlib
import json
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT, help='root holding data/')
    args = ap.parse_args()
    entries = json.loads((ROOT / 'manifests/cohorts.json').read_text())
    for relative, record in entries.items():
        path = args.root / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != record['sha256']:
            raise ValueError(f'{relative}: complete archive hash mismatch ({actual})')
        with np.load(path, allow_pickle=False) as data:
            assert set(data.files) == set(record['arrays']), relative
            for key, ref in record['arrays'].items():
                a = data[key]
                assert str(a.dtype) == ref['dtype'] and list(a.shape) == ref['shape'], (relative, key)
                assert hashlib.sha256(a.tobytes(order='C')).hexdigest() == ref['sha256'], (relative, key)
        print(f'{actual}  {relative}: all {len(record["arrays"])} arrays PASS')

if __name__ == '__main__':
    main()
