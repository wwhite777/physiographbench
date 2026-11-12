"""Portable family caps and public saved-record identities."""
from pathlib import Path
import os
import sys
HERE = Path(__file__).absolute().parent
sys.path.insert(0, os.environ.get('PHYSIOGRAPH_ROOT', str(HERE.parents[1])))
from release_paths import ROOT, SCRATCH
from release_records import digest, read, verify, clinical
CAPS = {'none':105, 'admissible':70, 'grud':35}
HOST = ROOT / 'experiments/shared_input_primary/artifacts/host'
RUNS = ROOT / 'experiments/shared_input_primary/runs/ten_seed'
SELECTION = HOST / 'selection_shared.json'
COHORT = ROOT / 'data/cinc2019_cohort.npz'

def location(family, seed, host=HOST):
    if family == 'grud' and seed < 4:
        return f'results/v4/tuning_grid.json#/selected_runs/grud/{seed}'
    return (host / f'budget/{family}/epochs{CAPS[family]}/seed{seed}/run.json').relative_to(ROOT).as_posix()

def chosen(family):
    if family == 'grud': return read('results/v4/selection.json')['models']['grud']
    # Recheck all six distributed grid records and rank only A-validation.
    records=[]
    for path in sorted((HOST / 'grid').glob('*/seed0/run.json')):
        verify(path)
        r=read(path.relative_to(ROOT))
        records.append((r['validation_RMSE'], path.parent.parent.name, r))
    if len(records)!=6: raise ValueError('Require six configuration-grid records')
    validation, cfg, r = min(records, key=lambda item:item[:2])
    selected=read(SELECTION.relative_to(ROOT))['selected']
    for key in ('lr','width','sizes','validation_RMSE'):
        if selected[key]!=r[key]: raise ValueError('Changed validation selection')
    if selected['cfg']!=cfg: raise ValueError('Changed configuration tie break')
    return selected

def load_shared():
    import importlib.util
    import renal_protocol
    path=ROOT / 'experiments/shared_input_primary/shared_input_primary.py'
    spec=importlib.util.spec_from_file_location('_ten_seed_shared',path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    code=path.read_text()
    old='seed not in range(4)'
    if code.count(old)!=1: raise ValueError('Changed seed validation')
    exec(compile(code.replace(old,'seed not in range(10)'),str(path),'exec'),module.__dict__)
    module.HERE=ROOT / 'experiments/shared_input_primary'
    return module
