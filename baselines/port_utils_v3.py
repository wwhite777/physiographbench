"""Owned I/O and tensor utilities for grafiti_baseline; no upstream code imports."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import hashlib
import json
from pathlib import Path

import torch

ROOT = RELEASE_ROOT
PROJECT = RELEASE_ROOT
SCRATCH = RELEASE_SCRATCH


def owned_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f'grafiti_baseline outputs must be inside {ROOT}: {path}')
    return path


def write_json(path, value):
    path = owned_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def context(batch, n_feat):
    """Discard absent placeholders before embedding, including NaN placeholders."""
    values, mask = batch['values'], batch['mask']
    if values.ndim != 3 or values.shape != mask.shape or values.shape[-1] != n_feat:
        raise ValueError('Expected matching (batch, context, n_feat) values and mask')
    if values.shape[1] < 1:
        raise ValueError('An empty context is not supported')
    present = mask > 0
    return torch.where(present, values, torch.zeros_like(values)), present


def masked_softmax(scores, present, dim):
    scores = scores.masked_fill(~present, torch.finfo(scores.dtype).min)
    weights = torch.softmax(scores, dim=dim) * present
    return weights / weights.sum(dim=dim, keepdim=True).clamp_min(
        torch.finfo(weights.dtype).tiny)


def query_mse(prediction, target, target_mask):
    """GraFITi §3: mean answers per example, then mean nonempty examples.

    The graph requests the complete future grid. Only its observed labels can
    supervise: K_i = sum(target_mask[i]). Empty examples have no defined query
    loss and are omitted. An entirely empty batch returns differentiable zero.
    """
    present = target_mask > 0
    difference = torch.where(present, prediction - target, torch.zeros_like(prediction))
    counts = present.flatten(1).sum(1)
    per_example = difference.square().flatten(1).sum(1) / counts.clamp_min(1)
    nonempty = counts > 0
    return per_example[nonempty].sum() / nonempty.sum().clamp_min(1)
