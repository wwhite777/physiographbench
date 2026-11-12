#!/usr/bin/env python3
"""Run one family at its fixed selected cap, or one explicit CPU smoke."""
import argparse
import json
from pathlib import Path
from n2_common import *

def fit(family, seed, output_dir, device='cpu', smoke=False, threads=None):
    if seed not in range(4,10): raise ValueError('Require seed 4..9')
    output_dir=Path(output_dir).absolute()
    if not (output_dir.is_relative_to(RUNS) or output_dir.is_relative_to(SCRATCH)):
        raise ValueError('Output must be under runs/ten_seed or configured scratch')
    if output_dir.exists() or output_dir.is_symlink(): raise FileExistsError(output_dir)
    import os
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
    import torch
    threads=(2 if family=='grud' else 4) if threads is None else threads
    torch.set_num_threads(threads)
    choice=chosen(family)
    cap=CAPS[family]
    epochs, max_stays=(1,16) if smoke else (cap,None)
    if smoke and device!='cpu': raise ValueError('Smoke requires CPU')
    verify(COHORT)
    if family=='grud':
        import v4_protocol as protocol
        r=protocol.train_run('grud',choice['lr'],choice['width'],seed,output_dir,
            npz=COHORT,epochs=epochs,batch=128,device=device,max_stays=max_stays,
            variant='admissible',curve_path=output_dir/'curve.csv',evaluate_tests=True)
    else:
        protocol=load_shared()
        r=protocol.train_run('budget',family,seed,output_dir,lr=choice['lr'],
            width=choice['width'],epochs=epochs,batch=128,device=device,max_stays=max_stays,
            npz=COHORT,selection=dict(path=str(SELECTION),sha256=digest(SELECTION),scope='full'))
    r.update(batch=128,device=device,threads=threads,scheduler_T_max=epochs,
        cublas_workspace_config=':4096:8',scope='smoke' if smoke else 'full')
    (output_dir/'run.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    return r

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--family',choices=CAPS,required=True)
    ap.add_argument('--seed',type=int,choices=range(4,10),required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--device',default='cpu')
    ap.add_argument('--threads',type=int)
    ap.add_argument('--smoke',action='store_true')
    r=fit(**vars(ap.parse_args()))
    return 0 if r['status']=='complete' else 1
if __name__=='__main__': raise SystemExit(main())
