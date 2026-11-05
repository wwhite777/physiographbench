#!/usr/bin/env python3
"""cohort_replay: replay the unchanged CinC-2019 preprocessor and audit every raw file.

Run with system Python 3 + NumPy. All writes stay beside this script; temporary
files and bytecode are confined to the task's private scratch or disabled.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone

HERE = RELEASE_ROOT / 'runs/cohort_replay'
PROJECT = Path(str(RELEASE_ROOT / '.'))
SOURCE = PROJECT / 'src/cinc2019_cohort_preprocessor.py'
DATA = PROJECT / 'data'
FROZEN = DATA / 'cinc2019_cohort.npz'
SCRATCH = RELEASE_SCRATCH
REPLAY = HERE / 'cohort_replay.npz'
EXPECTED_SOURCE = json.loads((RELEASE_ROOT / 'manifests/distribution.json').read_text())['src/cinc2019_cohort_preprocessor.py']['distributed_sha256']
EXPECTED_FROZEN = 'd52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f'
WORKERS = 8


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def signature(path):
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def audit_file(path, hospital, parser, source_lines):
    """Call the original parser; separately count its nonblank input rows."""
    row = dict(file_name=path.name, hospital_set=hospital, rows_read=0,
               included='no', reason='', code_line='', cohort_index='',
               retained_rows='', raw_sha256='', error='')
    try:
        with path.open() as stream:
            stream.readline()  # The original parser treats the first line as header.
            for line in stream:
                if line.strip():
                    row['rows_read'] += 1
    except OSError as exc:
        row.update(reason='unreadable',
                   code_line='L58-59: except OSError: / return None',
                   error=f'{type(exc).__name__}: {exc}')
        return row
    try:
        record = parser.parse_patient(str(path))
    except Exception as exc:
        frames = [frame for frame in traceback.extract_tb(exc.__traceback__)
                  if Path(frame.filename) == SOURCE]
        frame = frames[-1] if frames else None
        row.update(reason='other', error=f'{type(exc).__name__}: {exc}',
                   code_line=(f'L{frame.lineno}: {source_lines[frame.lineno - 1].strip()}'
                              if frame else 'no preprocessor source frame'))
    else:
        if record is not None:
            row.update(included='yes', retained_rows=int(record['length']))
        elif row['rows_read'] < parser.MIN_LOS:
            row.update(reason='fewer than 8 rows',
                       code_line='L60-61: if len(rows) < MIN_LOS: / return None (L43: MIN_LOS = 8)')
        else:
            row.update(reason='unreadable',
                       code_line='L58-59: except OSError: / return None',
                       error='Original parser returned None on its separate read despite >=8 counted rows.')
    row['raw_sha256'] = sha256(path)
    return row


def main():
    start = utc_now()
    clock_start = time.monotonic()
    HERE.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for key in ('TMPDIR', 'TMP', 'TEMP'):
        os.environ[key] = str(SCRATCH)
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[key] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['PYTHONUNBUFFERED'] = '1'
    sys.dont_write_bytecode = True
    import numpy as np

    source_before, frozen_before = sha256(SOURCE), sha256(FROZEN)
    if source_before != EXPECTED_SOURCE or frozen_before != EXPECTED_FROZEN:
        raise RuntimeError('Input fingerprint differs from the recorded cohort specification; replay not started.')
    files = {hospital: sorted((DATA / f'training_set{hospital}').glob('*.psv'))
             for hospital in ('A', 'B')}
    snapshots = {path: signature(path) for paths in files.values() for path in paths}
    source_lines = SOURCE.read_text().splitlines()
    spec = importlib.util.spec_from_file_location('frozen_cinc2019_preprocessor', SOURCE)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)

    command = [sys.executable, '-B', str(SOURCE), '--data_root', str(DATA),
               '--out', str(REPLAY), '--max_patients', '0', '--workers', str(WORKERS),
               '--val_frac', '0.15', '--seed', '0']
    print(f'[{utc_now()}] Running unchanged source: {shlex.join(command)}', flush=True)
    with (HERE / 'PREPROCESSOR_LOG.txt').open('w') as log:
        result = subprocess.run(command, cwd=HERE, env=os.environ.copy(),
                                stdout=log, stderr=subprocess.STDOUT, check=False)
    print(f'[{utc_now()}] Preprocessor exit status: {result.returncode}', flush=True)
    print((HERE / 'PREPROCESSOR_LOG.txt').read_text(), flush=True)

    manifest = []
    for hospital, paths in files.items():
        cohort_index = 0
        for index, path in enumerate(paths, 1):
            if time.monotonic() - clock_start > 90 * 60:
                raise RuntimeError('90-minute task limit reached; no further work started.')
            row = audit_file(path, hospital, parser, source_lines)
            if row['included'] == 'yes':
                row['cohort_index'] = cohort_index
                cohort_index += 1
            manifest.append(row)
            if index % 5000 == 0 or index == len(paths):
                print(f'[{utc_now()}] Manifest {hospital}: {index}/{len(paths)}', flush=True)
    manifest_path = HERE / 'EXCLUSION_MANIFEST.tsv'
    with manifest_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest[0]), delimiter='\t',
                                lineterminator='\n')
        writer.writeheader()
        writer.writerows(manifest)

    counts = {}
    for hospital in files:
        rows = [row for row in manifest if row['hospital_set'] == hospital]
        counts[hospital] = dict(found=len(rows), included=sum(row['included'] == 'yes' for row in rows),
                                reasons=dict(Counter(row['reason'] for row in rows
                                                     if row['included'] == 'no')),
                                min_rows=min(row['rows_read'] for row in rows),
                                max_rows=max(row['rows_read'] for row in rows),
                                truncated=sum(row['included'] == 'yes' and row['rows_read'] > parser.T_MAX
                                              for row in rows))

    comparisons, split_checks, mapping_checks = [], {}, {}
    keys_equal = False
    if result.returncode == 0:
        with np.load(FROZEN, allow_pickle=False) as frozen, np.load(REPLAY, allow_pickle=False) as replay:
            keys_equal = set(frozen.files) == set(replay.files)
            for name in sorted(set(frozen.files) | set(replay.files)):
                if name not in frozen.files or name not in replay.files:
                    comparisons.append(dict(name=name, shape='missing', dtype='missing',
                                            shape_equal=False, dtype_equal=False,
                                            array_equal=False, payload_bytes_equal=False))
                    continue
                left, right = frozen[name], replay[name]
                comparisons.append(dict(name=name, shape=list(right.shape), dtype=str(right.dtype),
                                        shape_equal=left.shape == right.shape,
                                        dtype_equal=left.dtype == right.dtype,
                                        array_equal=bool(np.array_equal(left, right)),
                                        payload_bytes_equal=left.tobytes(order='C') == right.tobytes(order='C')))
            for hospital in files:
                included = [row for row in manifest
                            if row['hospital_set'] == hospital and row['included'] == 'yes']
                lengths = np.array([row['retained_rows'] for row in included], dtype=np.int32)
                mapping_checks[hospital] = bool(np.array_equal(lengths, replay[f'{hospital}_length']))
            n_a = len(replay['A_length'])
            indices = [replay[f'{split}_idx'] for split in ('train', 'val', 'test')]
            joined = np.concatenate(indices)
            perm = np.random.default_rng(0).permutation(n_a)
            n_test = int(0.15 * n_a)
            n_val = int(0.15 * n_a)
            expected = [perm[n_test + n_val:], perm[n_test:n_test + n_val], perm[:n_test]]
            split_checks = dict(counts={split: len(arr) for split, arr in zip(('train', 'val', 'test'), indices)},
                                disjoint_complete_A_partition=bool(np.array_equal(np.sort(joined), np.arange(n_a))),
                                seed_0_exact_order=all(np.array_equal(arr, target)
                                                       for arr, target in zip(indices, expected)),
                                B_external_count=len(replay['B_length']))
    input_unchanged = (sha256(SOURCE) == source_before and sha256(FROZEN) == frozen_before
                       and all(signature(path) == snapshot for path, snapshot in snapshots.items())
                       and all(sorted((DATA / f'training_set{hospital}').glob('*.psv')) == paths
                               for hospital, paths in files.items()))
    replay_sha = sha256(REPLAY) if result.returncode == 0 else None
    identity = (result.returncode == 0 and keys_equal and bool(comparisons)
                and all(row['shape_equal'] and row['dtype_equal'] and row['array_equal'] for row in comparisons))
    passed = (identity and input_unchanged and all(mapping_checks.values())
              and split_checks.get('disjoint_complete_A_partition', False)
              and split_checks.get('seed_0_exact_order', False)
              and not any(row['reason'] == 'other' for row in manifest))
    evidence = dict(task='cohort_replay-cohort-replay-build', started_utc=start, finished_utc=utc_now(),
                    elapsed_seconds=round(time.monotonic() - clock_start, 3),
                    command=command, preprocessor_returncode=result.returncode,
                    source_sha256=source_before, frozen_sha256=frozen_before, replay_sha256=replay_sha,
                    identity=identity, archive_bytes_equal=replay_sha == frozen_before,
                    keys_equal=keys_equal, comparisons=comparisons, counts=counts,
                    manifest_length_mapping=mapping_checks, split_checks=split_checks,
                    input_unchanged=input_unchanged, passed=passed,
                    environment=dict(python=sys.version, executable=sys.executable, numpy=np.__version__,
                                     platform=platform.platform(), machine=platform.machine(),
                                     cpu_count=os.cpu_count(), workers=WORKERS,
                                     thread_limit=1, scratch=str(SCRATCH), cwd=str(HERE),
                                     zlib=__import__('zlib').ZLIB_RUNTIME_VERSION))
    (HERE / 'REPLAY_RESULTS.json').write_text(json.dumps(evidence, indent=2) + '\n')
    write_report(evidence, manifest)
    print(f'[{utc_now()}] Overall {"PASS" if passed else "FAIL"}; array identity={identity}; '
          f'archive bytes equal={evidence["archive_bytes_equal"]}', flush=True)
    return 0 if passed else 1


def write_report(evidence, manifest):
    e = evidence
    lines = ['# cohort_replay — CinC-2019 cohort replay', '',
             f'**Verdict: {"PASS" if e["passed"] else "FAIL"}.** '
             f'Array identity: {e["identity"]}; complete archive byte identity: {e["archive_bytes_equal"]}.', '',
             'The original preprocessor was executed unchanged as a separate Python process. '
             'Only its output location and worker count differ from its defaults; the full cohorts, '
             'seed 0 and validation fraction 0.15 were supplied explicitly. The regenerated archive '
             '`cohort_replay.npz` is retained in this evidence directory.', '',
             '## Fingerprints and command', '',
             f'- Source: `{SOURCE}`; SHA-256 `{e["source_sha256"]}`.',
             f'- Frozen archive: `{FROZEN}`; SHA-256 `{e["frozen_sha256"]}`.',
             f'- Replay archive: `{REPLAY}`; SHA-256 `{e["replay_sha256"]}`.',
             f'- Source/frozen SHA-256 and all raw file path/stat snapshots unchanged after replay: '
             f'**{e["input_unchanged"]}**.', '',
             '```sh', shlex.join(e['command']), '```', '',
             '## Array identity', '',
             'For every key, both archives were opened with `np.load(..., allow_pickle=False)`. '
             'Identity requires the same key set, shape, dtype and `np.array_equal(frozen[key], replay[key])` '
             'with the default NaN semantics (no tolerance and no `equal_nan=True`). '
             'An additional direct comparison of each array’s C-order bytes checks payload bit identity, '
             'including signed zeros. Full-file SHA-256 checks the compressed archive as well. '
             f'Key sets equal: **{e["keys_equal"]}**.', '',
             '| Array | Shape | dtype | Shape equal | dtype equal | np.array_equal | Payload bytes equal |',
             '|---|---|---|---|---|---|---|']
    for row in e['comparisons']:
        lines.append(f'| {row["name"]} | {row["shape"]} | {row["dtype"]} | {row["shape_equal"]} | '
                     f'{row["dtype_equal"]} | {row["array_equal"]} | {row["payload_bytes_equal"]} |')
    lines += ['', '## Raw-file accounting', '',
              '`EXCLUSION_MANIFEST.tsv` contains one row per raw file, sorted by hospital and filename, '
              'with the original parser’s inclusion verdict, nonblank data rows before the 48-hour cap, '
              'exclusion reason and quoted source line where applicable. Each included row also records '
              'its zero-based archive patient index and retained length. A per-file SHA-256 fingerprints '
              'the raw bytes. Empty exclusion fields on included rows are intentional.', '',
              '| Hospital | Files found (denominator) | Included | Unreadable | Fewer than 8 rows | Other |',
              '|---|---:|---:|---:|---:|---:|']
    for hospital, count in e['counts'].items():
        reasons = count['reasons']
        lines.append(f'| {hospital} | {count["found"]:,} | {count["included"]:,} | '
                     f'{reasons.get("unreadable", 0):,} | {reasons.get("fewer than 8 rows", 0):,} | '
                     f'{reasons.get("other", 0):,} |')
    lines += ['', 'Source rules (line numbers refer to the frozen source fingerprint above):', '',
              '- Line 43: `MIN_LOS = 8`.',
              '- Lines 54–57: `with open(path) as fh:`; the first line is the header; '
              '`rows = [ln.strip().split("|") for ln in fh if ln.strip()]`.',
              '- **Unreadable**, lines 58–59: `except OSError:` / `return None`.',
              '- **Fewer than 8 rows**, lines 60–61: `if len(rows) < MIN_LOS:` / `return None`.',
              '- **Other**: there is no other silent exclusion branch. Conversion/header/index errors '
              '(for example line 62, `arr = np.array(rows, dtype=np.float32)`) propagate and fail the '
              'original build. The wrapper records an exception and its actual source line as `other`, '
              'and does not pass such a run.',
              '- Lines 85–87 sort `*.psv` filenames; `--max_patients 0` means no file limit '
              '(line 129). Lines 90–92 append only records for which `rec is not None`.',
              '- Lines 42 and 63–64: `T_MAX = 48`; `T = min(arr.shape[0], T_MAX)`; `arr = arr[:T]`. '
              'The minimum-row criterion is checked before this cap.', '']
    for hospital, count in e['counts'].items():
        lines.append(f'Hospital {hospital}: raw data rows range from {count["min_rows"]} to '
                     f'{count["max_rows"]}; {count["truncated"]:,} included stays exceed 48 rows. '
                     f'Manifest order and retained lengths match `{hospital}_length`: '
                     f'**{e["manifest_length_mapping"].get(hospital, False)}**.')
        lines.append('')
    excluded = [row for row in manifest if row['included'] == 'no']
    if excluded:
        lines += ['Every difference from the raw counts is listed row by row in the manifest; '
                  f'there are {len(excluded):,} excluded files.', '']
    else:
        lines += ['No raw file was excluded; the manifest accounts for all 40,336 input files.', '']
    lines += ['## Split verification', '', '```json', json.dumps(e['split_checks'], indent=2), '```', '',
              'The three index arrays were also compared directly to their frozen counterparts in '
              'the array table. The additional checks reconstruct the seed-0 permutation and confirm '
              'that A-train, A-validation and A-test are disjoint and exhaust hospital A. '
              'Hospital B is the complete external cohort. Normalization statistics are fitted on '
              'A-train only by source line 146 and are compared above.', '',
              '## Exact inclusion sentence for the paper', '']
    if e['passed'] and all(e['counts'][h]['included'] == n for h, n in [('A', 20336), ('B', 20000)]):
        lines += ['> We included all 40,336 patient files from the two public CinC-2019 training sets '
                  '(20,336 from hospital A and 20,000 from hospital B), each of which was readable and '
                  'contained at least eight nonblank hourly data rows after the header; no files were '
                  'excluded, and each stay was represented by its first 48 hourly rows or its full '
                  'length if shorter.', '']
    else:
        lines += ['No inclusion sentence is certified because the expected complete replay did not pass.', '']
    lines += ['## Environment and execution', '',
              f'- Start: `{e["started_utc"]}`; finish: `{e["finished_utc"]}`; '
              f'elapsed: {e["elapsed_seconds"]} seconds.',
              f'- Preprocessor return code: `{e["preprocessor_returncode"]}`; full output: `PREPROCESSOR_LOG.txt`.',
              '- Environment:', '', '```json', json.dumps(e['environment'], indent=2), '```', '',
              'No source or data file was edited. No installation, network or git operation was used. '
              'The process pool was capped at eight workers and numerical-library threads at one. '
              'Scratch environment variables point to the owned private workspace directory; bytecode '
              'writes were disabled. No tmux or socket operation was performed. This is an engineering '
              'replay by the assigned research engineer, not an independent scientific review.', '']
    (HERE / 'REPLAY_REPORT.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    raise SystemExit(main())
