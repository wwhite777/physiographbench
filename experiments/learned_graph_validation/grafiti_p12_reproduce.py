#!/usr/bin/env python3
"""One-seed GraFITi adapter evaluation using the original local P12 code protocol.

Default is a host command preview. --run needs all three source sets; --smoke
reads exactly 200 patients from the available A/B sets and trains two CPU epochs.
See PROTOCOL_GRAFITI_P12.md for paper/code differences and outstanding evidence.
"""
from __future__ import annotations

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import csv
import io
import math
from pathlib import Path
import shlex
import sys
import tarfile
import time
import zipfile

from e5_common import (ROOT, PROJECT, GraFITiAdapter, command_line, evaluate_mse,
                       fit, owned_path, pooled_mse, save_checkpoint, seed_runtime,
                       sha256, utc_now, write_json)
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

# Same named channels/order as the local released dataset reader; no 2019 aliases.
FEATURES = ('pH PaCO2 PaO2 FiO2 MechVent DiasABP HR MAP SysABP Temp GCS Urine '
            'Weight HCT BUN Creatinine Glucose HCO3 Mg Platelets K Na WBC '
            'NIDiasABP NIMAP NISysABP RespRate ALP ALT AST Bilirubin SaO2 '
            'Lactate Albumin TroponinT Cholesterol TroponinI').split()
DESCRIPTORS = {'Age', 'Gender', 'Height', 'ICUType', 'Weight'}
FEATURE_INDEX = {name: index for index, name in enumerate(FEATURES)}
PUBLISHED_TARGET = 'to be read from the paper by the project lead'


def parse_record(text):
    """Independently encode the local released reader's observable behavior.

    That reader drops the first reading at each hour transition and never flushes
    its last hour. These behaviors are preserved for code-protocol compatibility,
    not described as correct hourly aggregation. No upstream code is imported.
    """
    values = np.zeros((49, len(FEATURES)), np.float64)
    mask = np.zeros_like(values, dtype=bool)
    row_present = np.zeros(49, dtype=bool)
    sums = np.zeros(len(FEATURES), np.float64)
    counts = np.zeros(len(FEATURES), np.int64)
    current_hour = None
    record_id = None
    for row in csv.DictReader(io.StringIO(text)):
        name = row['Parameter']
        h, m = map(int, row['Time'].split(':'))
        if h < 0 or h > 48 or not 0 <= m < 60:
            raise ValueError(f'Unexpected P12 timestamp: {row["Time"]}')
        if name == 'RecordID':
            record_id = int(row['Value'])
            continue
        if name in DESCRIPTORS and h == m == 0:
            continue
        if current_hour is not None and current_hour != h:
            observed = counts > 0
            values[current_hour, observed] = sums[observed] / counts[observed]
            mask[current_hour] = observed
            row_present[current_hour] = True
            current_hour = h
            sums.fill(0.)
            counts.fill(0)
            continue  # compatibility: boundary-triggering observation is lost
        if name not in FEATURE_INDEX:
            continue
        current_hour = h
        j = FEATURE_INDEX[name]
        sums[j] += float(row['Value'])  # source reader does not remove raw -1
        counts[j] += 1
    if record_id is None:
        raise ValueError('Missing RecordID')
    return record_id, values, mask, row_present


def archive_members(path):
    """Yield records without extracting any archive member to disk."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for name in sorted(n for n in archive.namelist() if n.endswith('.txt')):
                yield name, archive.read(name).decode('utf-8')
    else:
        with tarfile.open(path, 'r:*') as archive:
            members = sorted((m for m in archive.getmembers()
                              if m.isfile() and m.name.endswith('.txt')), key=lambda m: m.name)
            for member in members:
                with archive.extractfile(member) as stream:
                    yield member.name, stream.read().decode('utf-8')


def load_records(archives, smoke=False):
    records = []
    for path in archives:
        # Smoke exposure is exactly 100 from A and 100 from B, no full parsing.
        for number, (name, text) in enumerate(archive_members(path)):
            if smoke and number >= 100:
                break
            record = parse_record(text)
            if str(record[0]) != Path(name).stem:
                raise ValueError('RecordID disagrees with archive filename')
            records.append(record)
    ids = np.array([r[0] for r in records], dtype=np.int64)
    if len(ids) != len(np.unique(ids)):
        raise ValueError('Duplicate patients across source archives')
    if smoke and len(ids) != 200:
        raise ValueError('Smoke must contain exactly 200 patients')
    if not smoke and (len(archives) != 3 or len(ids) != 12000):
        raise ValueError('Full P12 code protocol requires three sets / 12,000 patients')
    return ids, np.stack([r[1] for r in records]), np.stack([r[2] for r in records]), np.stack([r[3] for r in records])


def code_split(n):
    """NumPy equivalent of two sklearn ShuffleSplit calls, random_state=0."""
    permutation = np.random.RandomState(0).permutation(n)
    n_test = math.ceil(.15 * n)
    test, remaining = permutation[:n_test], permutation[n_test:]
    second = np.random.RandomState(0).permutation(len(remaining))
    n_val = math.ceil(.2 * len(remaining))
    return remaining[second[n_val:]], remaining[second[:n_val]], test


def normalize(values, mask):
    # Released task fits the full corpus, BEFORE splitting, including future/test.
    counts = mask.sum(axis=(0, 1))
    mean = np.where(mask, values, 0.).sum(axis=(0, 1)) / np.maximum(counts, 1)
    centered = np.where(mask, values - mean, 0.)
    std = np.sqrt(np.square(centered).sum(axis=(0, 1)) / np.maximum(counts, 1)) + 1e-7
    scaled = (values - mean) / std
    retained = mask & np.isfinite(scaled) & (scaled > -5) & (scaled < 5)
    return np.where(retained, scaled, 0.).astype(np.float32), retained, mean, std, counts


class P12Windows(Dataset):
    def __init__(self, values, mask, rows, ids, indices, time_max):
        self.values, self.mask, self.rows, self.ids = values, mask, rows, ids
        self.indices, self.time_max = np.asarray(indices), time_max

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, item):
        i = self.indices[item]
        # Released TaskDataset observes t <= 36; the next three stored rows may
        # skip clock hours. Padding adds no edges and no supervised targets.
        future = np.flatnonzero(self.rows[i] & (np.arange(49) > 36))[:3]
        target = np.zeros((3, len(FEATURES)), np.float32)
        target_mask = np.zeros_like(target)
        target_times = np.zeros(3, np.float32)
        target[:len(future)] = self.values[i, future]
        target_mask[:len(future)] = self.mask[i, future]
        target_times[:len(future)] = future / self.time_max
        return dict(values=torch.from_numpy(self.values[i, :37]),
                    mask=torch.from_numpy(self.mask[i, :37].astype(np.float32)),
                    context_times=torch.arange(37, dtype=torch.float32) / self.time_max,
                    target_times=torch.from_numpy(target_times),
                    target=torch.from_numpy(target), target_mask=torch.from_numpy(target_mask),
                    record_id=int(self.ids[i]))


class P12GraFITi(GraFITiAdapter):
    """Reuse v3 graph layers; accept explicit P12 times and requested query edges."""
    def __init__(self, time_max):
        super().__init__(n_feat=len(FEATURES), n_static=0, latent_dim=64,
                         attn_head=4, n_layers=2, time_scale=time_max)
        self.config.update(query_policy='Observed future labels define requested edges; no values exposed',
                           timestamp_api='Explicit context_times and target_times, normalized to corpus maximum')

    def initial_graph(self, batch, horizon):
        channels, _, _, _ = super().initial_graph(batch, horizon)
        observed = batch['mask'] > 0
        query = batch['target_mask'] > 0
        if query.shape[1] != horizon:
            raise ValueError('P12 query shape does not match horizon')
        context = torch.where(observed, batch['values'], 0.)
        raw = torch.cat([context, torch.zeros_like(batch['target_mask'])], 1)
        present = torch.cat([observed, query], 1)
        indicator = torch.cat([observed, torch.zeros_like(query)], 1)
        edges = self.edge_embedding(torch.stack([raw, indicator.to(raw.dtype)], -1))
        edges = edges * present.unsqueeze(-1)
        times = torch.cat([batch['context_times'], batch['target_times']], 1)
        time_nodes = torch.sin(self.time_embedding(times.unsqueeze(-1)))
        return channels, time_nodes, edges, present


def portable_command(command):
    return ['python3' if i == 0 else
            str(Path(arg).relative_to(PROJECT)) if Path(arg).is_absolute() and Path(arg).is_relative_to(PROJECT)
            else arg for i, arg in enumerate(command)]


def host_command(args):
    return portable_command([sys.executable, '-B', str(ROOT / 'grafiti_p12_reproduce.py'), '--run',
            '--archives', *map(str, args.archives), '--seed', str(args.seed),
            '--device', args.device, '--threads', str(args.threads), '--epochs', '200',
            '--batch-size', '128', '--out', str(args.out)])


def run(args):
    started, clock_start = time.perf_counter(), utc_now()
    owned_path(args.out)
    archives = args.archives[:2] if args.smoke else args.archives
    missing = [str(p) for p in archives if not p.is_file()]
    if missing:
        raise ValueError('Required source archive missing: ' + ', '.join(missing))
    if args.smoke and (args.device != 'cpu' or args.epochs != 2):
        raise ValueError('Smoke is exactly two CPU epochs on 200 patients')
    if not args.smoke and (args.epochs != 200 or args.batch_size != 128):
        raise ValueError('Host protocol uses at most 200 epochs and batch size 128')
    seed_runtime(args.seed, args.threads, args.device)
    ids, values, mask, rows = load_records(archives, args.smoke)
    # Empty source records have no dataframe rows and are absent from upstream IDs.
    keep = rows.any(1)
    parsed_count = len(ids)
    ids, values, mask, rows = ids[keep], values[keep], mask[keep], rows[keep]
    values, mask, mean, std, counts = normalize(values, mask)
    if not args.smoke and (counts == 0).any():
        raise ValueError('At least one expected P12 channel is entirely unobserved')
    time_max = float(np.flatnonzero(rows.any(0))[-1])
    indices = code_split(len(ids))
    datasets = [P12Windows(values, mask, rows, ids, split, time_max) for split in indices]
    loaders = [DataLoader(ds, batch_size=args.batch_size if i == 0 else 64,
                          shuffle=i == 0, drop_last=i == 0 and not args.smoke,
                          num_workers=0) for i, ds in enumerate(datasets)]
    model = P12GraFITi(time_max)
    history, best_epoch = fit(model, *loaders[:2], device=args.device, horizon=3,
                              epochs=args.epochs, lr=.001, weight_decay=.001,
                              optimizer_name='AdamW', schedule='plateau', patience=30,
                              min_delta=0., loss_fn=pooled_mse)
    result = dict(task='learned-graph experiment', started_utc=clock_start, finished_utc=utc_now(),
                  command=command_line(), smoke=args.smoke, parsed_patients=parsed_count,
                  status='smoke_only' if args.smoke else 'single_seed_adapter_reproduction_attempt',
                  published_target=PUBLISHED_TARGET, published_match_established=False,
                  config=vars(args).copy(), architecture=model.config,
                  n_params=sum(p.numel() for p in model.parameters()),
                  protocol='local released original P12 code; see PROTOCOL_GRAFITI_P12.md',
                  training_history=history, best_epoch=best_epoch,
                  validation=evaluate_mse(model, loaders[1], args.device, 3),
                  test=evaluate_mse(model, loaders[2], args.device, 3),
                  normalization=dict(scope='all available patients/all hours BEFORE split',
                                     mean=mean.tolist(), std=std.tolist(),
                                     observed_counts=counts.tolist(), time_max=time_max),
                  split_record_ids={name: ids[split].tolist()
                                    for name, split in zip(('train', 'val', 'test'), indices)},
                  source_archives=[dict(path=str(p), sha256=sha256(p)) for p in archives],
                  elapsed_seconds=time.perf_counter() - started)
    result['config']['archives'] = list(map(str, args.archives))
    result['config']['out'] = str(args.out)
    result['checkpoint'] = save_checkpoint(args.out.with_suffix('.pt'), model)
    result['finished_utc'] = utc_now()
    result['elapsed_seconds'] = time.perf_counter() - started
    write_json(args.out, result)
    print('RESULT ' + str(args.out), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run', action='store_true')
    mode.add_argument('--smoke', action='store_true')
    mode.add_argument('--dry-run', action='store_true')
    parser.add_argument('--archives', type=Path, nargs=3,
                        default=[PROJECT / f'data/cinc2012/set-{s}.zip' for s in 'abc'])
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--epochs', type=int)
    parser.add_argument('--batch-size', type=int)
    parser.add_argument('--out', type=Path, default=ROOT / 'runs/p12_seed0.json')
    args = parser.parse_args()
    args.epochs = args.epochs if args.epochs is not None else (2 if args.smoke else 200)
    args.batch_size = args.batch_size if args.batch_size is not None else (8 if args.smoke else 128)
    if args.batch_size < 1:
        parser.error('batch size must be positive')
    if args.smoke or args.run:
        print('COMMAND ' + command_line(), flush=True)
        run(args)
    else:
        print(shlex.join(host_command(args)))
        missing = [str(p) for p in args.archives if not p.is_file()]
        if missing:
            print('READINESS: missing required source archive(s): ' + ', '.join(missing), file=sys.stderr)


if __name__ == '__main__':
    main()
