"""Paths, source checks and output guards for shared-input CinC-2012."""
from pathlib import Path
import os
import sys
HERE=Path(__file__).absolute().parent
sys.path.insert(0,os.environ.get('PHYSIOGRAPH_ROOT',str(HERE.parents[2])))
from release_paths import ROOT as PROJECT, SCRATCH
from release_records import digest as sha256, verify as verify_input, read
import tempfile
tempfile.tempdir=str(SCRATCH)
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
TASK='cinc2012-shared-input'
BASE_RESULTS=PROJECT/'results/clinical_v4_v1/cinc2012'
SHARED_EXPERIMENT=PROJECT/'experiments/shared_input_primary'
COHORT=PROJECT/'data/cinc2012'
WITHIN_NPZ=COHORT/'cinc2012_cohort.npz'
TRANSFER_NPZ=COHORT/'cinc2012_transfer.npz'
SELECTION=SHARED_EXPERIMENT/'artifacts/host/selection_shared.json'
PYTHON=sys.executable
CAPS={'none':105,'admissible':70}
MODEL='physiograph_gru_shared'
FULL_ROOT=PROJECT/'runs/cinc2012_shared'
RECORD_ROOT=BASE_RESULTS/'shared_input'

def owned_path(path):
    p=Path(path).absolute()
    if not (p.is_relative_to(PROJECT/'runs') or p.is_relative_to(SCRATCH)):
        raise ValueError('Output must stay under runs or configured scratch')
    for ancestor in (p,*p.parents):
        if ancestor==PROJECT: break
        if ancestor.is_symlink(): raise ValueError('Output symlinks are refused')
    return p

def fresh_path(path):
    p=owned_path(path)
    if p.exists() or p.is_symlink(): raise FileExistsError(p)
    return p

def write_json(path,value):
    import json
    p=fresh_path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f: f.write(json.dumps(value,indent=2,allow_nan=False)+'\n')

def checkpoint_for(arm,seed):
    return SHARED_EXPERIMENT/f'runs/ten_seed/{arm}/seed{seed}/checkpoint.pt' if seed>=4 else SHARED_EXPERIMENT/f'runs/full/budget/{arm}/epochs{CAPS[arm]}/seed{seed}/checkpoint.pt'

def run_dir(root,protocol,arm,seed):
    return Path(root)/protocol/arm/f'seed{seed}'

def identities():
    return [(p,a,s) for p in ('within','transfer') for a in CAPS for s in range(4)]

def selected_config():
    sys.path.insert(0,str(SHARED_EXPERIMENT))
    from n2_common import chosen
    return chosen('none')
