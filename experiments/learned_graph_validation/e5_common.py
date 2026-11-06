"""Shared learned-graph experiment runtime, owned artifacts, and observed-cell metrics."""
from __future__ import annotations

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import hashlib
import json
import os
from pathlib import Path
import random
import shlex
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
PROJECT = RELEASE_ROOT
SCRATCH = RELEASE_SCRATCH
SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ['TMPDIR'] = str(SCRATCH)
os.environ['TMP'] = str(SCRATCH)
os.environ['TEMP'] = str(SCRATCH)
os.environ['XDG_CACHE_HOME'] = str(SCRATCH / 'cache')
os.environ['TORCH_HOME'] = str(SCRATCH / 'torch')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

import numpy as np
import torch

GRAFITI_SOURCE = PROJECT / 'baselines'
TPATCH_SOURCE = PROJECT / 'baselines'
for directory in (GRAFITI_SOURCE, TPATCH_SOURCE, PROJECT / 'src'):
    sys.path.insert(0, str(directory))

from grafiti_adapter_v3 import GraFITiAdapter
from tpatchgnn_adapter import TPatchGNNAdapter


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def owned_path(path):
    path = Path(path).resolve()
    if not (path.is_relative_to(ROOT) or path.is_relative_to(RELEASE_SCRATCH)) or path == ROOT:
        raise ValueError(f'Outputs must be files inside {ROOT}: {path}')
    if path.relative_to(ROOT).parts[0] in ('.git', '.agents', '.research tooling', '.aws'):
        raise ValueError('Protected workspace metadata is read-only')
    return path


def write_json(path, data):
    path = owned_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def command_line():
    return shlex.join([sys.executable, '-B', *sys.argv])


def seed_runtime(seed, threads, device):
    if threads < 1:
        raise ValueError('threads must be positive')
    torch.set_num_threads(threads)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device == 'cuda':
        if not torch.cuda.is_available():
            raise ValueError('CUDA requested but unavailable')
        os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)


def to_device(batch, device):
    return {key: value.to(device) if torch.is_tensor(value) else value
            for key, value in batch.items()}


def pooled_mse(prediction, target, mask):
    present = mask > 0
    errors = torch.where(present, prediction - target, 0.)
    return errors.square().sum() / present.sum().clamp_min(1)


@torch.no_grad()
def evaluate_mse(model, loader, device, horizon):
    """Pool squared errors and denominators, never average batch means."""
    model.eval()
    squared_error, absolute_error, count = 0., 0., 0
    for batch in loader:
        batch = to_device(batch, device)
        prediction = model(batch, horizon)
        present = batch['target_mask'] > 0
        if not torch.isfinite(prediction[present]).all():
            raise ValueError('Nonfinite prediction on an observed target')
        error = (prediction - batch['target'])[present].double()
        squared_error += error.square().sum().item()
        absolute_error += error.abs().sum().item()
        count += error.numel()
    if not count:
        raise ValueError('Evaluation split has no observed targets')
    mse = squared_error / count
    return dict(MSE=mse, RMSE=mse ** .5, MAE=absolute_error / count,
                n_observed_targets=count)


def fit(model, train, val, *, device, horizon, epochs, lr, weight_decay,
        optimizer_name, schedule, patience, min_delta, loss_fn, clip=None):
    if epochs < 1:
        raise ValueError('epochs must be positive')
    model.to(device)
    optimizer_type = {'Adam': torch.optim.Adam, 'AdamW': torch.optim.AdamW}[optimizer_name]
    optimizer = optimizer_type((p for p in model.parameters() if p.requires_grad),
                               lr=lr, weight_decay=weight_decay)
    if schedule == 'plateau':
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', patience=10, factor=.5, min_lr=1e-5)
    else:
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)
    best, state, stale, best_epoch = float('inf'), None, 0, None
    history = []
    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for batch in train:
            batch = to_device(batch, device)
            if not (batch['target_mask'] > 0).any():
                continue
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(batch, horizon), batch['target'], batch['target_mask'])
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite training loss')
            loss.backward()
            if any(p.grad is not None and not torch.isfinite(p.grad).all()
                   for p in model.parameters()):
                raise ValueError('Nonfinite parameter gradient')
            if clip is not None:
                torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
            optimizer.step()
            losses.append(loss.item())
        if not losses:
            raise ValueError('No nonempty training batches; check batch size/drop_last')
        validation = evaluate_mse(model, val, device, horizon)
        score = validation['MSE'] if schedule == 'plateau' else validation['RMSE']
        if score < best - min_delta:
            best, stale, best_epoch = score, 0, epoch
            state = {key: value.detach().cpu().clone()
                     for key, value in model.state_dict().items()}
        else:
            stale += 1
        history.append(dict(epoch=epoch, train_mse=float(np.mean(losses)),
                            val=validation, learning_rate=optimizer.param_groups[0]['lr']))
        print(f'epoch={epoch} train_MSE={np.mean(losses):.8f} '
              f'val_MSE={validation["MSE"]:.8f}', flush=True)
        if schedule == 'plateau':
            scheduler.step(score)
        else:
            scheduler.step()
        if stale >= patience:
            break
    model.load_state_dict(state)
    return history, best_epoch


def save_checkpoint(path, model):
    path = owned_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({key: value.detach().cpu() for key, value in model.state_dict().items()}, path)
    return dict(path=str(path), sha256=sha256(path))
