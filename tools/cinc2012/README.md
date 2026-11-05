# CinC-2012 training and evaluation

Run these commands from the repository root. This directory contains the
transfer evaluator, within-corpus trainer, 88-run launcher and strict error-archive
aggregator. The shared clinical protocol is `tools/v4_protocol.py`; the two
learned-graph adapters are in `baselines/`. All new results go under `runs/`.

Reconstruct the archived table without data, weights or training:

```bash
python3 tools/cinc2012/aggregate_cinc2012.py \
  --from-summary results/clinical_v4_v1/cinc2012/cinc2012_results.json \
  --out-table runs/tables/TABLE_CINC2012.md
```

This recomputes means and sample standard deviations from the four saved seed
metrics and checks them against the archived summaries. It does not recreate
predictions or independently verify the original per-stay errors.

For retraining, first rebuild and verify both corpora using REPRODUCE.md section 3.
Within-corpus fitting needs `data/cinc2012/cinc2012_cohort.npz` and the 2019
reference archive. Transfer additionally needs the 44 CinC-2019 source fits:

```bash
python3 tools/run_experiments.py --suite clinical --device cpu --threads 1 --run
python3 tools/run_experiments.py --suite learned_graphs --device cpu --threads 1 --run
```

The clinical suite creates `runs/clinical/selected/MODEL/seedN/checkpoint.pt`
and its `run.json`. The learned-graph suite creates
`runs/learned_graphs/MODEL/cinc_MODEL_sN.pt` and its sibling JSON record. These
weights are generated locally and are excluded from the distribution.
Transfer requires a full source fit, verifies checkpoint identity and hash,
and checks that its training cohort is the frozen CinC-2019 cohort.

Print the complete 88 commands without requiring data or checkpoints:

```bash
python3 tools/cinc2012/host_driver.py --dry-run
python3 tools/cinc2012/host_driver.py --dry-run --device cpu --threads 1 \
  --manifest runs/cinc2012_plan.json
```

`manifests/cinc2012_commands.json` retains the historical order and scientific
flags with portable paths and `python3`. Defaults retain its three recorded CUDA
lanes and four threads per run. Use `--device cpu` for one sequential CPU lane,
or `--devices cuda:0,cuda:1` for locally available GPUs. Commands run in the
repository root with the launcher's Python interpreter. The historical manifest
in `results/clinical_v4_v1/cinc2012/` preserves original fingerprints separately.
For GPU execution, unset `CUDA_VISIBLE_DEVICES` if it was cleared for the CPU
checks, or set it to the intended visible GPUs before choosing lane indices.

Execute all 44 transfer evaluations and 44 within-corpus fits, then aggregate:

```bash
python3 tools/cinc2012/host_driver.py --run --device cpu --threads 1
python3 tools/cinc2012/aggregate_cinc2012.py --root runs/cinc2012
```

The launcher preflights all required inputs and destinations before starting,
keeps one sequential lane per device, records child exit codes, and aggregates
only after all runs complete successfully. Each run has a separate log and
output directory. Existing nonempty run directories and logs are preserved;
choose a fresh `--out-root runs/cinc2012_repeat` for another series. Aggregation
recomputes pooled and per-organ metrics from the new error archives and rejects
missing runs or mixed smoke/full scopes. `--allow-partial` produces a labelled
diagnostic only. New summaries and tables remain under the selected output root.

For the small CPU check after rebuilding the cohorts:

```bash
make cinc2012-smoke
```

This fits GRU seed 0 with `--max-stays 64 --epochs 1` on CPU: 32 training,
8 validation and 24 set-b stays. Outputs use a fresh directory under
`runs/cinc2012-smoke/` on every invocation. If a source checkpoint exists at a
documented CinC-2019 fit path, the smoke also evaluates transfer on 32 stays per
set. No source checkpoints are shipped, so a clean distribution reports that
transfer check as skipped and explains the prerequisite. Its newly fitted
within-2012 checkpoint cannot substitute for a CinC-2019 transfer checkpoint.

The full protocol fixes the first 12 hours as context and the following 12 as
targets, filters on length at least 24 hours, and uses four seeds (0–3). Within
training uses only set-a training statistics, the fixed 2019-selected
configuration, validation stopping and set-b evaluation; its testA is empty by
design. Transfer uses frozen 2019 normalization and evaluates both 2012 sets
without fitting. Batch size is 128; the full epoch cap is 35, patience 8 and
minimum improvement 0.0001. Adam, weight decay 0.00001, cosine schedule and
gradient clipping at 1 are unchanged. The learned-graph losses retain their
respective observed-entry and per-example definitions.

RMSE pools squared errors over observed target entries before taking the square
root. Pooled transfer combines both sets' numerators and denominators. Tables
report the arithmetic mean and sample standard deviation of seed RMSEs. Full
eligible counts are transfer 3,989 set-a and 3,993 set-b; within 3,390 training,
599 validation and 3,993 set-b. No hyperparameters are reselected on 2012.
The hospital-system overlap, SaO2 substitution and static/unit qualifications
in `results/cinc2012_cohort_v1/COHORT_REPORT.md` remain applicable. Training may
vary across environments; matching the settings does not promise identical
fitted scores or checkpoint bytes.
