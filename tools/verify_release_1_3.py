#!/usr/bin/env python3
"""Check all new record bytes, identities, numerical validity and inventory."""
from pathlib import Path
import os
import sys
sys.path.insert(0, os.environ.get('PHYSIOGRAPH_ROOT',str(Path(__file__).absolute().parents[1])))
from release_records import ROOT, read, verify, finite
from collections import Counter

def verify_records(root=ROOT):
    manifest=read('manifests/release_1_3_records.json',root)
    counts=Counter()
    paths=set()
    for entry in manifest['records']:
        path=root/entry['path']
        if entry['path'] in paths: raise ValueError('Duplicate record')
        paths.add(entry['path'])
        verify(path,root)
        import hashlib
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['distributed_sha256']: raise ValueError('Record manifest mismatch')
        r=read(entry['path'],root);finite(r)
        if entry['group']=='regime':
            actual={k:r['config'][k] for k in ('kappa','arm','seed')}
        elif entry['group']=='cinc2012': actual={k:r[k] for k in ('protocol','arm','seed')}
        else: actual=dict(family=r.get('arm','grud'),seed=r['seed'],cap=r['epochs_budget'])
        if actual!=entry['identity']: raise ValueError('Record identity mismatch')
        counts[entry['group']]+=1
    if dict(counts)!=manifest['counts'] or len(paths)!=100: raise ValueError('Incomplete release inventory')
    # New-format records occur only in these experiment branches.
    physical=set()
    for branch in ('experiments/positive_control/artifacts/full','results/clinical_v4_v1/cinc2012/shared_input'):
        physical.update(p.relative_to(root).as_posix() for p in (root/branch).rglob('run.json'))
    physical.update(p.relative_to(root).as_posix() for p in (root/'experiments/shared_input_primary/artifacts/host/budget').rglob('run.json') if int(p.parent.name.removeprefix('seed'))>=4)
    if physical!=paths: raise ValueError('Unlisted or missing new run record')
    print(f'PASS: {len(paths)} new run records; {dict(counts)}')
    return len(paths)
if __name__=='__main__': verify_records()
