# Reproduce the v4 artifact

Run commands below from the repository root. The software is a benchmark and
includes both supported findings and negative controls. No raw data, trained
weights, paper files, or upstream source checkouts are required in the
initial distribution. Downloading the open inputs and training models create
local data and checkpoints under ignored directories.

## 1. Environment and distribution integrity

Use Python 3.10.12 and the package versions in `requirements.txt` for the recorded
configuration. The original environment used PyTorch 2.6.0+cu124; CPU execution
uses the same PyTorch release. `manifests/environment.json` records the installed
versions, including NumPy 2.2.6, SciPy 1.15.3 and zlib 1.2.11. A compatible existing
environment can be used directly. On a new machine, prepare one with:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
```

The artifact builder did not install packages or access the network. The fetch
commands in section 3 are for the reproducer and were not executed during staging.

```bash
export PHYSIOGRAPH_ROOT="$PWD"
export TMPDIR="$PWD/.scratch"
export MPLCONFIGDIR="$TMPDIR/matplotlib"
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
mkdir -p "$TMPDIR"
sha256sum --quiet -c SHA256SUMS
make smoke
```

`make smoke` runs synthetic cohort parsing, all recurrent baseline forwards, both
accepted variable-graph ports with gradients, CRN inference and gradient reversal,
a one-epoch training/checkpoint/statistics integration, shared-history branching,
the original organ-model self-test, and the simulator's pressure/flow controls.
It does not estimate scientific model rankings. All scratch uses `TMPDIR`.

## 2. Rebuild published display numbers without data or training

```bash
make findings
python3 tools/summarize_results.py --out-dir runs/tables --check
python3 tools/plot_results.py --out-dir runs/figures
```

The summary command recreates `findings.json`, the README clinical table and eight
CSV tables: clinical, variants, organs, horizons, simulator forecast, simulator
policy, CRN, and coupling index. It computes clinical mean/sample standard
deviation from the four per-seed run values, computes horizon gaps from the
archived runs, and extracts the archived paired estimates and simulator/coupling
statistics. It does not re-infer checkpoints or recreate patient bootstrap
samples from aggregate means. Seed-level simulator means and uncertainty are
frozen evidence; rerunning section 5 regenerates the underlying seed results.

`results/tables/` contains the distributed display tables; `results/findings.json`
contains the derived README values. The plot command draws clinical comparisons,
matched simulator controls, counterfactual direction heatmaps, horizon gaps and
the hourly coupling curve directly from frozen data. Undefined hourly means at
zero coupling are omitted and labelled. `figures/F1_overview.png` is the supplied
v4 overview, including the CinC-2012 comparison; this plotting command does not
generate that conceptual figure.

The records in `results/v4/` are the numerical authority for clinical analyses.
`results/sim_grids_v1/` holds matched simulator summaries;
`results/learned_graph_baselines_v1/` holds graph-port and CRN runs;
`results/coupling_index_v1/` holds the empirical and simulator index.
The per-organ, ablation, horizon and paired-statistics records preserve
observed-entry denominators and distinguish pooled RMSE from mean stay RMSE.
The original numeric CDE external fields remain archival diagnostics and are
excluded from displayed external comparisons, which label the model diverged.

## 3. Fetch open data and rebuild both cohorts

The data sources and licences are listed in `README.md`. No credentials are
needed for the specified open corpora. The first script lists and downloads the
CinC-2019 public S3 training sets, retaining its retry and nonempty-file skip
logic; do not treat its console counts alone as a content-integrity check. The
cohort archive hashes below are the end-to-end check.

```bash
python3 tools/fetch_s3_cinc2019.py --root data
python3 src/cinc2019_cohort_preprocessor.py \
  --data_root data --out data/cinc2019_cohort.npz \
  --max_patients 0 --workers 8 --val_frac 0.15 --seed 0
python3 tools/fetch_cinc2012.py --root data/cinc2012
python3 tools/cinc2012_cohort_preprocessor.py \
  --data-root data/cinc2012 --reference data/cinc2019_cohort.npz \
  --out-dir data/cinc2012
python3 tools/verify_cohorts.py
```

The CinC-2012 URLs are:

- `https://physionet.org/files/challenge-2012/1.0.0/set-a.zip`
- `https://physionet.org/files/challenge-2012/1.0.0/set-b.zip`
- `https://physionet.org/files/challenge-2012/1.0.0/Outcomes-a.txt`

The fetcher verifies SHA-256 before accepting a file. The expected input hashes
are retained in `tools/fetch_cinc2012.py` and the frozen cohort build summary.

| Rebuilt archive | Bytes | Expected SHA-256 |
|---|---:|---|
| `data/cinc2019_cohort.npz` | 18602564 | `d52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f` |
| `data/cinc2012/cinc2012_cohort.npz` | 4636151 | `f3de48a075d671a92aeae6c254063dbfe036f9d8760d0a3a1423fdb1942550b8` |
| `data/cinc2012/cinc2012_transfer.npz` | 4657179 | `9cf9e31101464f0661e0619311d9db42211582868d0e0e96581cdc82a2c3b18c` |

`manifests/cohorts.json` also records dtype, shape and payload hash for every array.
The distribution builders were executed against the existing full local raw
inputs and matched these complete archive bytes and all 99 arrays.
Archive identity is tied to the recorded NumPy/zlib implementation; if another
compression implementation changes archive bytes, compare scientific arrays
separately and disclose the difference rather than claiming archive identity.

The 2019 parser retains all 20,336 A files and 20,000 B files, caps stored timelines
at 48 hours, and fits normalization only on A-train. It requires at least eight
source rows, but no source file in the frozen collection fails that rule. Set A
splits into 14,236 training, 3,050 validation and 3,050 test stays before context/
horizon eligibility filtering. For the historical per-file replay audit after
rebuilding the local cohort, run:

```bash
python3 tools/replay_cohort.py
```

That optional audit writes its replay archive, raw-file manifest and report to
`runs/cohort_replay/`, verifies every raw file, and compares with
`data/cinc2019_cohort.npz`. It checks the distributed parser fingerprint and the
frozen cohort hash. The original full audit is in `results/cohort_replay_v1/`.

The 2012 builder reads ZIP members directly in sorted order. It bins observations
hourly, uses invasive pressure when available in each hour and the corresponding
noninvasive pressure otherwise, and retains the source timeline even for
unselected variables. The within-corpus view fits statistics on its A-train
partition. The transfer view uses the frozen 2019 statistics and is evaluation
only; its overlapping training placeholders must not be used for training.
Read `results/cinc2012_cohort_v1/COHORT_REPORT.md` for the static-variable mapping,
measurement modality/units, eligibility and missing-label qualifications.
Completed CinC-2012 transfer and within-corpus results are in
`results/clinical_v4_v1/cinc2012/TABLE_CINC2012.md` and `cinc2012_results.json`
in the same directory (88/88 runs). The numerical JSON retains all per-seed
metrics; recomputing their means and sample standard deviations reproduces the
table. `run_manifest.json` records the historical commands and original source,
cohort, checkpoint and error-archive fingerprints. Its relative historical
locators do not imply those files are bundled: the CinC-2012 training/evaluation
drivers are not included in this staged update, so full re-execution of these
88 runs is not supported by the commands in this document. No new training runs
were performed for this release update.

## 4. Regenerate simulator datasets from manifests

```bash
python3 tools/replay_simulators.py --group all
python3 tools/replay_simulators.py --group all --run
python3 tools/replay_simulators.py --group all --verify-only
```

The first command prints the exact per-dataset sequence. The second regenerates
missing files from `generation_args` and checks every scientific array. Existing
files are checked and never accepted just because their names match. The third
requires all outputs and checks them again without generation. For a selected
set, use, for example:

```bash
python3 tools/replay_simulators.py --id policy/shared_c1.0_sigma0.25 --run
```

`manifests/simulator_datasets.json` covers all 40 full-size datasets: seven forecast
sets (six coupling values and the common metric reference), 27 shared-history/
legacy policy sets, and six hourly calibration sets. It contains all generation
settings, original archive hashes, and 334 expected scientific-array hashes.
`manifests/sim_policy/` preserves the 27 original generation manifests;
`manifests/sim_hourly/` preserves the six original hourly manifests. Paths in these
historical records are mapped for distribution, while their historical code and
archive hashes retain their original meaning.

The integration step is 0.5 seconds after a 180-second warm-up. Forecast/policy
sets contain 400 patients over six hours with five-minute samples. Hourly sets
extend to 36 hours and sample hourly. Shared-history targets branch at
`C*out_dt`; the step ending at the branch uses the factual schedule. The
subsequent dose begins at the branch, including direct observation effects.
The factual schedule and random draws are preserved. Sigma is the total policy
noise standard deviation, with 0.03 reproducing the original policy.

Generated NPZ files contain `metadata_json` with current paths, timing and code
hashes. These metadata bytes differ after packaging; even the original writer
recorded elapsed time. Original archive hashes therefore remain provenance,
not promises of portable archive-byte identity. The reproducer checks dtype,
shape and the SHA-256 of every C-order payload except `metadata_json`. An array
hash failure is an error and stops the command. The simulator's scientific
arrays remain exactly reproducible in the recorded numerical environment.

## 5. Rerun every registered experiment

A full rerun is substantial CPU work. The staging smoke is deliberately small;
the archived results are already included for inspecting and regenerating the
published displays. Training randomness or hardware/library differences can
change fitted scores, so model-training results do not carry a byte-identity
promise. Match the recorded settings, report the new environment and compare
estimates at their stated uncertainty.

First enumerate the complete sequence without training:

```bash
mkdir -p runs
python3 tools/run_experiments.py --suite all --device cpu --threads 1 \
  --manifest runs/experiment_plan.json > runs/commands.txt
```

Execute the suites in this order:

```bash
python3 tools/run_experiments.py --suite clinical --device cpu --threads 1 --run
python3 tools/run_experiments.py --suite sim_forecast --device cpu --threads 1 --run
python3 tools/run_experiments.py --suite sim_policy --device cpu --threads 1 --run
python3 tools/run_experiments.py --suite learned_graphs --device cpu --threads 1 --run
python3 tools/run_experiments.py --suite crn --device cpu --threads 1 --run
python3 tools/run_experiments.py --suite coupling --device cpu --threads 1 --run
```

Each suite prints its commands and writes command logs under `runs/logs/`.
Generated-data and probe caches also use ignored `data/` and `artifacts/` paths.
Training commands retain their non-overwrite behavior. Start with empty fit/log
locations or preserve a separate previous output tree before a rerun; do not
merge partial experiments into frozen results. GPU execution is optional only
for runners that expose `--device`; the shared-history, graph-port and CRN
experiments remain CPU routes. The CPU plan uses the current interpreter.

| Suite | Experiment and relation to published evidence |
|---|---|
| `clinical` | 54 tuning fits (nine architectures × three learning rates × two widths), 36 selected-seed fits, 40 additional edge-variant fits, 180 common-cohort horizon fits; selection, pooled/paired/per-organ summaries and a newly trained CDE checkpoint diagnosis. Corresponds to `results/v4/`. |
| `sim_forecast` | 144 matched edge-set fits, 24 monolithic width-96 fits and 24 width-201 capacity-matched monolithic fits; then both control aggregations. Corresponds to the matched forecast grid. |
| `sim_policy` | 384 shared-history and 48 historical-target fits; four models, four seeds, six severity-dependence values and four assignment-noise values in the shared grid. Corresponds to the 108-cell policy summary and overlap table. |
| `learned_graphs` | Four t-PatchGNN and four GraFITi fits using their accepted ports, common loader and validation selection. No architecture tuning grid. |
| `crn` | 72 full-adaptation policy fits, 36 balancing-weight fits and four longer zero-weight positive controls. The zero-weight sweep explicitly keeps the full CRN architecture. |
| `coupling` | Frozen ridge/GRU probe definitions on the clinical and five-minute simulator data, then the separate hourly simulator ridge calibration. |

The clinical learning rates are 0.0005, 0.001 and 0.002; widths and capacity aliases
are defined in `tools/v4_protocol.py`. Selection minimizes A-validation pooled
masked RMSE, with lexical configuration tie breaking, never A-test/B performance.
The epoch cap is 35, with patience 8 and minimum improvement 0.0001. Horizon runs
use a common cohort with at least 48 hours and the five context/horizon pairs
in the frozen protocol. The simulator fits use the original 60-epoch budget,
learning rate 0.002, seeds 0–3, dataset seed 0, and the same fixed metric reference
across cells. Per-seed checkpoints and error arrays are generated locally.

The public clinical drivers replace an inaccessible historical checkpoint gate
with distribution/cohort integrity checks. The archived historical interval
exception remains in `results/v4/run_manifest_with_waiver.json`. This packaging
change does not rerun that historical pair or change validation selection,
model equations, losses, epoch budgets or scientific evidence.

## 6. Distribution lineage and limits

`SHA256SUMS` covers every distributed file except itself. `manifests/distribution.json`
records each copied source's original SHA-256, the distributed SHA-256, and file
sizes. `manifests/TRANSFORMATIONS.md` explains path/import/provenance edits;
`manifests/readme_trace.json` maps README numerical claims to result files.
The core organ model, clinical-baseline module and base simulator are copied
byte for byte. Original scientific JSON/CSV numbers are unchanged; only descriptive
strings, private paths and JSON formatting are transformed for distribution.

The build verified CPU smoke tests, complete cohort bytes, selected full-size
simulator regeneration and numerical preservation of frozen records. It did not
repeat the complete training series or test remote download availability.
Historical simulator seed aggregates support table reconstruction; recomputing
patient statistics from predictions requires the locally rerun error artifacts.
The inherited Figure 1 needs its stated release update. Public URL/DOI and final
citation remain release placeholders. These limits do not convert pending
2012 model results or unstable external CDE inference into measured comparisons.
