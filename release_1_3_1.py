"""Integrity and locations for the population and device-matched saved records."""
from pathlib import Path
import hashlib
import json
import math
import os

ROOT = Path(os.environ.get('PHYSIOGRAPH_ROOT', Path(__file__).absolute().parent))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path, root=ROOT):
    relative = Path(path)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Expected a repository-relative path')
    return json.loads((root / relative).read_text())

def checked(path, expected, root=ROOT):
    if Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError('Expected a repository-relative path')
    path = root / path
    if sha(path) != expected:
        raise ValueError(f'Changed distributed input: {path.relative_to(root)}')
    return path

def finite(obj):
    if isinstance(obj, dict):
        for v in obj.values(): finite(v)
    elif isinstance(obj, list):
        for v in obj: finite(v)
    elif isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError('Nonfinite record')

def records(group, root=ROOT):
    manifest = read('manifests/release_1_3_1_inputs.json', root)
    rows = [r for r in manifest['records'] if r['group'] == group]
    required = ({(p,c,s) for p in range(5) for c in
                 ('none','admissible','shared_none','shared_admissible','control_gru') for s in range(4)}
                if group == 's1' else
                {(role,m,g,s) for role in ('fixed','cpu','cuda') for m in ('grafiti','tpatchgnn')
                 for g in (('physiological','random','complete') if role == 'fixed' else ('learned',))
                 for s in range(4)})
    result = {}
    for row in rows:
        key = ((row['population'],row['cell'],row['seed']) if group == 's1' else
               (row['role'],row['model'],row['graph'],row['seed']))
        if key in result or key not in required:
            raise ValueError(f'Duplicate or unexpected {group} identity: {key}')
        path = checked(row['path'], row['sha256'], root)
        record = json.loads(path.read_text()); finite(record)
        config = record['config']
        if type(config['seed']) is not int or config['seed'] != row['seed'] or record.get('smoke') is not False:
            raise ValueError('Wrong seed or smoke record')
        if group == 's1':
            if (config['arm'],config['dataset_seed'],config['epochs'],config['kappa'],config['n_patients']) != (row['cell'],row['population'],60,1,400):
                raise ValueError('Wrong population protocol')
            if row['population'] and (record['status'] != 'complete' or record['population'] != row['population'] or record['cell'] != row['cell']):
                raise ValueError('Incomplete population record')
            m=record['metrics'];ranges=record['reference_ranges']
            for organ in ('cardiovascular','renal','metabolic'):
                if not math.isclose(m['organ_rmse'][organ]/ranges[organ],m['organ_nrmse_fixed'][organ],abs_tol=1e-13,rel_tol=0):
                    raise ValueError('Organ normalization mismatch')
            if not math.isclose(sum(m['organ_nrmse_fixed'].values())/3,m['macro_nrmse_fixed'],abs_tol=1e-13,rel_tol=0):
                raise ValueError('Macro normalization mismatch')
        else:
            model = record['model'] if row['role'] == 'cpu' else config['model']
            if model != row['model']:
                raise ValueError('Wrong graph model')
            if row['role'] != 'cpu' and (record['graph']['kind'] != row['graph'] or config['graph'] != row['graph']):
                raise ValueError('Wrong adjacency')
            if row['role'] == 'cuda':
                runtime=record['runtime']
                if (config['device'],runtime['device'],runtime['parameter_dtype'],runtime['metric_reduction_dtype'],runtime['deterministic_algorithms']) != ('cuda','cuda','torch.float32','torch.float64',True):
                    raise ValueError('Wrong device or precision protocol')
        result[key] = (record,row)
    if set(result) != required:
        raise ValueError(f'Incomplete {group} records: {sorted(required-set(result))}')
    branch = ('experiments/positive_control/artifacts/population_replication/records' if group=='s1'
              else 'experiments/learned_graph_validation/artifacts/learned_cuda')
    expected_paths={r['path'] for r in rows if (r.get('population',0)>0 if group=='s1' else r['role']=='cuda')}
    physical={p.relative_to(root).as_posix() for p in (root/branch).rglob('*.json')}
    if physical != expected_paths:
        raise ValueError('Unlisted or missing record in added branch')
    if group == 's1':
        import numpy as np
        if len(manifest['populations']) != 4 or {p['population'] for p in manifest['populations']} != {1,2,3,4}:
            raise ValueError('Incomplete population inventory')
        for pop in manifest['populations']:
            path=checked(pop['path'],pop['sha256'],root)
            with np.load(path,allow_pickle=False) as arrays:
                for name,desc in pop['arrays'].items():
                    array=arrays[name]
                    if (list(array.shape),str(array.dtype),hashlib.sha256(array.tobytes()).hexdigest()) != (desc['shape'],desc['dtype'],desc['sha256']):
                        raise ValueError('Changed synthetic array')
    return result
