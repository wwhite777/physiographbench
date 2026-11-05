"""One registry adapter on the frozen CinC forecasting protocol, with owned outputs."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import os
from pathlib import Path
import sys
import time

from port_utils_v3 import PROJECT, SCRATCH, owned_path, sha256, write_json

sys.dont_write_bytecode = True
os.environ['TMPDIR'] = str(SCRATCH)
sys.path.insert(0, str(PROJECT / 'src'))

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Subset

from physiograph_data_loader import make_loaders
from physiograph_training_runner import evaluate
from port_utils_v3 import query_mse
from registry_v3 import REGISTRY, build_adapter


def loaders_for_run(npz, C=12, K=12, batch_size=128, smoke=False):
    train, val, test_a, test_b, meta = make_loaders(npz, C, K, batch_size, num_workers=0)
    loaders = [train, val, test_a, test_b]
    if smoke:
        # A disjoint <=64-patient exposure in total, not 64 per split.
        loaders = [DataLoader(Subset(loader.dataset, range(min(limit, len(loader.dataset)))),
                              batch_size=batch_size, shuffle=index == 0, num_workers=0)
                   for index, (loader, limit) in enumerate(zip(loaders, (32, 8, 8, 16)))]
    if any(len(loader.dataset) == 0 for loader in loaders):
        raise ValueError('Every forecasting split must contain at least one eligible stay')
    return loaders, meta


def run(model_name, npz, out, *, seed=0, epochs=35, batch_size=128, lr=.001,
        C=12, K=12, threads=1, smoke=False):
    out = owned_path(out)
    if epochs < 1 or batch_size < 1 or threads < 1:
        raise ValueError('Require positive epochs, batch size and thread count')
    if smoke and epochs != 1:
        raise ValueError('The learned_graph_baselines adapter smoke is one epoch')
    started = time.perf_counter()
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    np.random.seed(seed)
    torch.manual_seed(seed)
    # Fail a blocked port before reading patient data or creating output artifacts.
    model = build_adapter(model_name)
    loaders, meta = loaders_for_run(npz, C, K, batch_size, smoke)
    train, val, test_a, test_b = loaders
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)
    best_val, best_state, patience = float('inf'), None, 0
    history = []
    for epoch in range(epochs):
        model.train()
        loss_sum = 0.
        for batch in train:
            optimizer.zero_grad(set_to_none=True)
            prediction = model(batch, K)
            loss = query_mse(prediction, batch['target'], batch['target_mask'])
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite forecasting loss')
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
            loss_sum += float(loss.detach())
        scheduler.step()
        validation = evaluate(model, val, 'cpu', K, meta['organ_slices'],
                              meta['organ_names'])[f'RMSE@{K}']
        if validation < best_val - 1e-4:
            best_val = validation
            best_state = {name: tensor.detach().cpu().clone()
                          for name, tensor in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
        history.append(dict(epoch=epoch, train_mse=loss_sum / len(train),
                            val_rmse=validation, best_val_rmse=best_val))
        print(f'[{model_name}] epoch={epoch} val_RMSE@{K}={validation:.6f}', flush=True)
        if patience >= 8:
            break
    if best_state is None:
        raise ValueError('No finite validation checkpoint was obtained')
    model.load_state_dict(best_state)
    checkpoint = out.with_suffix('.pt')
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, checkpoint)
    internal = evaluate(model, test_a, 'cpu', K, meta['organ_slices'], meta['organ_names'])
    external = evaluate(model, test_b, 'cpu', K, meta['organ_slices'], meta['organ_names'])
    result = dict(schema_version=1, smoke=smoke, model=model_name,
                  config=dict(seed=seed, epochs=epochs, batch_size=batch_size, lr=lr,
                              C=C, K=K, device='cpu', threads=threads),
                  architecture=model.config, n_params=sum(p.numel() for p in model.parameters()),
                  protocol=dict(optimizer='Adam', weight_decay=1e-5,
                                scheduler='CosineAnnealingLR(T_max=epochs)',
                                gradient_norm_cap=1., patience=8, min_delta=1e-4,
                                normalization='Frozen A-train means/stds, including in smoke',
                                split_counts=[len(loader.dataset) for loader in loaders],
                                query_policy='Every future time x feature; target mask only in loss',
                                loss='Mean observed query errors per nonempty example, then mean examples'),
                  val_RMSE=best_val, A_test=internal, B_external=external,
                  degradation_pct=(external[f'RMSE@{K}'] / internal[f'RMSE@{K}'] - 1) * 100,
                  training_history=history, elapsed_seconds=time.perf_counter() - started,
                  input=dict(path=str(Path(npz).resolve()), sha256=sha256(npz)),
                  checkpoint=dict(path=str(checkpoint), sha256=sha256(checkpoint)))
    write_json(out, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=REGISTRY, required=True)
    parser.add_argument('--npz', default=str(PROJECT / 'data/cinc2019_cohort.npz'))
    parser.add_argument('--out', required=True)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--epochs', type=int, default=35)
    parser.add_argument('--batch_size', type=int, default=128)
    parser.add_argument('--lr', type=float, default=.001)
    parser.add_argument('--C', type=int, default=12)
    parser.add_argument('--K', type=int, default=12)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--smoke', action='store_true')
    args = vars(parser.parse_args())
    args['model_name'] = args.pop('model')
    run(**args)


if __name__ == '__main__':
    main()
