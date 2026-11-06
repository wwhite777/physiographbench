# Leaderboard and record contract

[LEADERBOARD.csv](LEADERBOARD.csv) indexes the released clinical forecasting
results. It has one row per method, training seed, configuration, protocol and
evaluation split. [RECORD_SCHEMA.json](RECORD_SCHEMA.json) is the JSON Schema
(Draft 2020-12) for a decoded row. This is a record index: comparisons must retain
the protocol and exclusion labels.

From the repository root, rebuild or check without clinical data, weights or fitting:

```bash
python3 -B leaderboard/build_leaderboard.py
python3 -B leaderboard/build_leaderboard.py --check
```

The builder uses the Python standard library, sorts rows and JSON object keys,
writes UTF-8 with LF line endings, and prints row counts and denominators.
`--check` compares the complete expected CSV bytes and performs a typed CSV
round trip. When `jsonschema` is already available, full schema validation is:

```bash
python3 -B leaderboard/build_leaderboard.py --check --validate-schema
```

The CSV stores `configuration` and `denominator` as JSON objects. Parse those
cells with `json.loads`; parse `schema_version` and `seed` as integers and
`value` as a number. Empty checkpoint/original-record cells mean JSON `null`.
`read_csv` in the builder implements this decoding. All other cells are strings.
The schema applies to the resulting objects, rather than untyped CSV strings.

## Included series and exact coverage

| Series | Source run identities | Seed/split records = CSV rows |
|---|---:|---:|
| Selected clinical models, including partitioned-input ablations | 36 | 72 |
| Persistence, recorded under each canonical seed | 4 | 8 |
| Learned graphs: t-PatchGNN and GraFITi | 8 | 16 |
| Shared-input primary: all ten arms | 40 | 80 |
| Longer budget: none, admissible and GRU-D at 70/105 epochs | 24 | 48 |
| CinC-2012 transfer: set-a, set-b and their pooled union | 44 | 132 |
| CinC-2012 within-corpus: set-b | 44 | 44 |
| Total | 200 | 400 |

There are **400 shipped seed/split metric records and 400 CSV data rows**.
The 200 source run identities include four copies of deterministic persistence;
those copies do not represent four fitted models. Multiple splits from a fit are
separate evaluation records. Embedded seed records are counted individually,
not as one record per JSON container file. The six shared-input tuning runs
select a configuration and do not enter the leaderboard. Simulator outcomes,
other horizons, tuning cells and post-hoc diagnostic series remain in their
respective result directories and are outside this clinical RMSE@12 index.

Sources are the selected seed records in
[the tuning archive](../results/v4/tuning_grid.json), the persistence records in
[the per-organ archive](../results/v4/per_organ_v4.json), the individual learned
adapter JSONs under `results/learned_graph_baselines_v1/`, the 64 primary-arm and
budget run files under `experiments/shared_input_primary/artifacts/host/`, and
[the CinC-2012 archive](../results/clinical_v4_v1/cinc2012/cinc2012_results.json).
A `run_record_path` points to the exact public metric block with a JSON Pointer
fragment (`file.json#/object/key`). Its `run_record_sha256` hashes the complete
shipped container file. Historical original-record identifiers and digests,
where preserved, have separate columns and may name unbundled records.

Neural CDE's four CinC-2019 B records retain their saved finite scores with
`comparison_status=excluded_unresolved_replay`. **Exclude those rows from
confirmed rankings and paired comparisons.** Their archival values do not resolve
the checkpoint replay problem described in the top-level documentation. Other
`recorded` rows mean that metrics were saved; the label does not claim a fresh
checkpoint replay or independent verification of predictions.

Checkpoint files are excluded from this repository; the selected fits are in the
separate Zenodo checkpoints record [10.5281/zenodo.23993257](https://doi.org/10.5281/zenodo.23993257). A recorded checkpoint identifier/digest refers
to the original weights, not the run JSON. Transfer rows identify the recorded
2019 source checkpoint and explicitly label that provenance. The bundled
CinC-2012 summary does not preserve the within-corpus checkpoint identities or
hashes: its 44 within rows therefore contain nulls and
`checkpoint_status=not_recorded_in_summary`. Original run-file hashes cannot
substitute for those missing weight-file hashes. Persistence has no checkpoint.

## Metric and fixed splits

Pooled root mean squared error at 12 hours (RMSE@12) is
`sqrt(sum(mask * (prediction - target)^2) / sum(mask))`, summing over all stays,
the 12 forecast hours and all 16 variables before the square root. Targets use
the corpus protocol's training-based normalization. Missing target entries
contribute neither squared error nor denominator. A stay with no observed
targets contributes no error term. This metric differs from averaging per-stay
RMSE or organ RMSE. The `stays` field includes eligible zero-target stays;
subtract `zero_target_stays` for the number contributing an observed target.

| Corpus/split | Observed target entries | Eligible stays | Zero-target stays |
|---|---:|---:|---:|
| CinC-2019 A-test (`A`) | 174879 | 2368 | 1 |
| CinC-2019 external hospital (`B`) | 1074461 | 14824 | 4 |
| CinC-2012 set-a (`testA`, transfer only) | 242346 | 3989 | 16 |
| CinC-2012 set-b (`testB`) | 242155 | 3993 | 22 |
| CinC-2012 transfer union (`pooled`) | 484501 | 7982 | 38 |

These counts come from the saved metric blocks. Learned-adapter records omit
entry denominators; their rows explicitly point to the persistence metric on
the identical fixed clinical cohort. The builder reports counts per split;
repeated models/seeds do not create additional patients or independent targets.
For transfer, combine the two sets' squared-error sums and entry counts before
the square root; do not average the set RMSEs.

CinC-2019 fixes the first 12 hours as context and the following 12 as targets,
using 11102 eligible A-training stays, 2367 A-validation stays, 2368 A-test
stays and 14824 B stays. Use the archived indices in the tuning records and
[the preprocessing fingerprints](../manifests/cohorts.json), with
[the common protocol](../tools/v4_protocol.py). Select configuration and stopping
only on A validation; A test and B never choose a model. The separately retuned
shared-input series uses its own A-validation selection and shares that
configuration across edge arms. Longer caps also change the cosine schedule;
keep them separate from the 35-epoch comparison.

CinC-2012 transfer uses the frozen CinC-2019 models and normalization with no
fitting. Within-corpus fitting uses 3390 eligible set-a training stays and
599 validation stays, the transferred configurations, set-a training
normalization and the 3993 eligible set-b test stays. Its A-test set is empty.
Use the frozen indices and cohort hashes in the archive and follow
[the full CinC-2012 protocol](../tools/cinc2012/README.md). Do not reselect
hyperparameters on set-b or pool the within and transfer protocols.

## Adding and comparing a method

1. Implement the common values/masks/static/target interface. Register the model
   in `tools/v4_protocol.py` and, for CinC-2012, its common runner registry.
   Follow [REPRODUCE.md](../REPRODUCE.md) for cohort construction and local runs.
2. Use canonical training seeds **0, 1, 2, 3**, the same fixed splits, target
   masks and normalization. Declare input access, architecture, parameter count,
   configuration-selection rule, epoch cap, schedule, stopping and loss. Apply
   the appropriate equal-count validation grid or explicitly label a fixed
   published configuration. Retain the source checkpoint identity and SHA-256
   in the saved run record. Keep restricted data, predictions and weights out
   of a public contribution.
3. Save a full-scope run JSON for every seed, including pooled RMSE and both
   observed-entry and stay counts for each required evaluation split. Preserve
   the original record bytes. Extend the builder's explicit source inventory
   and model inventory checks for the new method; use public paths and JSON
   Pointers, and regenerate the CSV. A method in an existing series uses the
   same schema; a new protocol/series requires an explicit schema update.
4. Run `--check`, full schema validation when available, the leaderboard tests
   and `make smoke`. Confirm complete seed/split coverage and matching
   denominators. A missing checkpoint hash is a disclosed record limitation,
   not a verified checkpoint identity.
5. Compare only rows with the same corpus, split, metric, protocol, input-access
   conditions and training budget. Report the arithmetic mean and sample
   standard deviation (`ddof=1`) of the four seed RMSEs, and seed-paired
   differences when making a matched contrast. Preserve exclusion flags.
   A lower mean alone does not establish significance, and four training seeds
   do not represent four independent patient populations.
