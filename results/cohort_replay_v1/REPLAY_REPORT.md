# CinC-2019 cohort replay

Frozen replay report. Paths are mapped to public locations; the fingerprints
identify the original input files and replay, not edited source bytes.

**Verdict: PASS.** Array identity: True; complete archive byte identity: True.

The original preprocessor was executed unchanged as a separate Python process. Only its output location and worker count differ from its defaults; the full cohorts, seed 0 and validation fraction 0.15 were supplied explicitly. The regenerated archive `cohort_replay.npz` is retained in this evidence directory.

## Fingerprints and command

- Source: `src/cinc2019_cohort_preprocessor.py`; SHA-256 `ad39d19cdd3849e23f00b966404b06412ba21a4142bdcdccca6cde19171c31bb`.
- Frozen archive: `data/cinc2019_cohort.npz`; SHA-256 `d52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f`.
- Replay archive: `tools/cohort_replay.npz`; SHA-256 `d52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f`.
- Source/frozen SHA-256 and all raw file path/stat snapshots unchanged after replay: **True**.

```sh
/usr/bin/python3 -B src/cinc2019_cohort_preprocessor.py --data_root data --out tools/cohort_replay.npz --max_patients 0 --workers 8 --val_frac 0.15 --seed 0
```

## Array identity

For every key, both archives were opened with `np.load(..., allow_pickle=False)`. Identity requires the same key set, shape, dtype and `np.array_equal(frozen[key], replay[key])` with the default NaN semantics (no tolerance and no `equal_nan=True`). An additional direct comparison of each array’s C-order bytes checks payload bit identity, including signed zeros. Full-file SHA-256 checks the compressed archive as well. Key sets equal: **True**.

| Array | Shape | dtype | Shape equal | dtype equal | np.array_equal | Payload bytes equal |
|---|---|---|---|---|---|---|
| A_ever_sepsis | [20336] | float32 | True | True | True | True |
| A_length | [20336] | int32 | True | True | True | True |
| A_mask | [20336, 48, 16] | float32 | True | True | True | True |
| A_sepsis | [20336, 48] | float32 | True | True | True | True |
| A_static | [20336, 5] | float32 | True | True | True | True |
| A_values | [20336, 48, 16] | float32 | True | True | True | True |
| B_ever_sepsis | [20000] | float32 | True | True | True | True |
| B_length | [20000] | int32 | True | True | True | True |
| B_mask | [20000, 48, 16] | float32 | True | True | True | True |
| B_sepsis | [20000, 48] | float32 | True | True | True | True |
| B_static | [20000, 5] | float32 | True | True | True | True |
| B_values | [20000, 48, 16] | float32 | True | True | True | True |
| features | [16] | <U10 | True | True | True | True |
| norm_mean | [16] | float32 | True | True | True | True |
| norm_std | [16] | float32 | True | True | True | True |
| organ_names | [4] | <U14 | True | True | True | True |
| organ_slices | [4, 2] | int64 | True | True | True | True |
| test_idx | [3050] | int64 | True | True | True | True |
| train_idx | [14236] | int64 | True | True | True | True |
| val_idx | [3050] | int64 | True | True | True | True |

## Raw-file accounting

`EXCLUSION_MANIFEST.tsv` contains one row per raw file, sorted by hospital and filename, with the original parser’s inclusion verdict, nonblank data rows before the 48-hour cap, exclusion reason and quoted source line where applicable. Each included row also records its zero-based archive patient index and retained length. A per-file SHA-256 fingerprints the raw bytes. Empty exclusion fields on included rows are intentional.

| Hospital | Files found (denominator) | Included | Unreadable | Fewer than 8 rows | Other |
|---|---:|---:|---:|---:|---:|
| A | 20,336 | 20,336 | 0 | 0 | 0 |
| B | 20,000 | 20,000 | 0 | 0 | 0 |

Source rules (line numbers refer to the frozen source fingerprint above):

- Line 43: `MIN_LOS = 8`.
- Lines 54–57: `with open(path) as fh:`; the first line is the header; `rows = [ln.strip().split("|") for ln in fh if ln.strip()]`.
- **Unreadable**, lines 58–59: `except OSError:` / `return None`.
- **Fewer than 8 rows**, lines 60–61: `if len(rows) < MIN_LOS:` / `return None`.
- **Other**: there is no other silent exclusion branch. Conversion/header/index errors (for example line 62, `arr = np.array(rows, dtype=np.float32)`) propagate and fail the original build. The wrapper records an exception and its actual source line as `other`, and does not pass such a run.
- Lines 85–87 sort `*.psv` filenames; `--max_patients 0` means no file limit (line 129). Lines 90–92 append only records for which `rec is not None`.
- Lines 42 and 63–64: `T_MAX = 48`; `T = min(arr.shape[0], T_MAX)`; `arr = arr[:T]`. The minimum-row criterion is checked before this cap.

Hospital A: raw data rows range from 8 to 336; 4,442 included stays exceed 48 rows. Manifest order and retained lengths match `A_length`: **True**.

Hospital B: raw data rows range from 8 to 336; 4,128 included stays exceed 48 rows. Manifest order and retained lengths match `B_length`: **True**.

No raw file was excluded; the manifest accounts for all 40,336 input files.

## Split verification

```json
{
  "counts": {
    "train": 14236,
    "val": 3050,
    "test": 3050
  },
  "disjoint_complete_A_partition": true,
  "seed_0_exact_order": true,
  "B_external_count": 20000
}
```

The three index arrays were also compared directly to their frozen counterparts in the array table. The additional checks reconstruct the seed-0 permutation and confirm that A-train, A-validation and A-test are disjoint and exhaust hospital A. Hospital B is the complete external cohort. Normalization statistics are fitted on A-train only by source line 146 and are compared above.

## Exact inclusion sentence for the paper

> We included all 40,336 patient files from the two public CinC-2019 training sets (20,336 from hospital A and 20,000 from hospital B), each of which was readable and contained at least eight nonblank hourly data rows after the header; no files were excluded, and each stay was represented by its first 48 hourly rows or its full length if shorter.

## Environment and execution

- Start: `2026-11-04T09:50:09+00:00`; finish: `2026-11-04T09:50:34+00:00`; elapsed: 24.702 seconds.
- Preprocessor return code: `0`; full output: `PREPROCESSOR_LOG.txt`.
- Environment:

```json
{
  "python": "3.10.12 (main, Aug 15 2025, 14:32:43) [GCC 11.4.0]",
  "executable": "/usr/bin/python3",
  "numpy": "2.2.6",
  "platform": "Linux-5.15.0-171-generic-x86_64-with-glibc2.35",
  "machine": "x86_64",
  "cpu_count": 48,
  "workers": 8,
  "thread_limit": 1,
  "scratch": ".scratch",
  "cwd": "tools",
  "zlib": "1.2.11"
}
```

The original audit left source and raw data unchanged and reproduced the complete
archive bytes. The public parser has portable root defaults; its numerical
behavior was checked again by rebuilding the full cohort and comparing all array
and archive hashes. Reproduction commands and current integrity checks are in
`REPRODUCE.md`.
