# Reproduce PhysioGraphBench v1.1.2 and its v5 findings

Run commands below from the repository root. The software is a benchmark and
includes both supported findings and negative controls. No raw data, trained
weights, paper files, or upstream source checkouts are required in the
initial distribution. Downloading the open inputs and training models create
local data and checkpoints under ignored directories.

This documentation update preserves the v1.1.0 source and result records. The
primary v5 clinical comparison is the retuned shared-input series under
`experiments/shared_input_primary/`, not the historical partitioned-input v4
series reconstructed by the legacy table generator. Each experiment README
links its saved metrics, paired intervals, assumptions and rerun prerequisites.
The concept DOI is [10.5281/zenodo.23976171](https://doi.org/10.5281/zenodo.23976171);
the v1.1.0 record is [10.5281/zenodo.23992302](https://doi.org/10.5281/zenodo.23992302).
The selected per-seed checkpoints are in a separate Zenodo record,
[10.5281/zenodo.23993257](https://doi.org/10.5281/zenodo.23993257); version 1.1.2 of the code is archived as
[10.5281/zenodo.23996559](https://doi.org/10.5281/zenodo.23996559).

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
python3 tools/summarize_results.py --out-dir runs/tables
python3 -c "import json; assert json.load(open('runs/tables/findings.json')) == json.load(open('results/findings.json'))"
python3 tools/plot_results.py --out-dir runs/figures
```

The JSON assertion checks the regenerated values against frozen v4 findings.
The legacy `make findings` target invokes summarizer `--check`, which additionally
requires the historical README table verbatim; use the export-and-compare route
above for this updated README. No verifier code is changed in this update.

The legacy summary command recreates the historical v4 `findings.json`, its
partitioned-input clinical display and eight CSV tables: clinical, variants, organs, horizons, simulator forecast, simulator
policy, CRN, and coupling index. It computes clinical mean/sample standard
deviation from the four per-seed run values, computes horizon gaps from the
archived runs, and extracts the archived paired estimates and simulator/coupling
statistics. It does not re-infer checkpoints or recreate patient bootstrap
samples from aggregate means. Seed-level simulator means and uncertainty are
frozen evidence; rerunning section 5 regenerates the underlying seed results.

`results/tables/` contains the historical distributed display tables;
`results/findings.json` contains their derived v4 values. These files remain
unchanged and do not regenerate the current README's v5 primary table. The plot command draws clinical comparisons,
matched simulator controls, counterfactual direction heatmaps, horizon gaps and
the hourly coupling curve directly from frozen data. Undefined hourly means at
zero coupling are omitted and labelled. `figures/F1_overview.png` is the supplied
v5 pipeline figure, rendered from the supplied PDF at 150 dpi; this plotting
command does not generate that conceptual figure. Legacy data plots remain
historical displays; their older labels do not override the current README's
qualified interpretations.

The records in `results/v4/` are the numerical authority for the historical
partitioned-input clinical analyses. The primary v5 selection and all 35-epoch
shared-input arms are in `experiments/shared_input_primary/artifacts/host/`;
its `E2_E4_READING.md` and `e2_e4_summary.json` also hold the separate budget
control. The paired-statistics records in `analysis/paired_statistics/` retain
their stated estimands, multiplicity families and missing-array limitations.
`results/sim_grids_v1/` holds matched simulator summaries;
`results/learned_graph_baselines_v1/` holds graph-port and CRN runs;
`results/coupling_index_v1/` holds the empirical and simulator index.
The per-organ, ablation, horizon and paired-statistics records preserve
observed-entry denominators and distinguish pooled RMSE from mean stay RMSE.
The original numeric CDE external fields remain archival diagnostics and are
excluded from confirmed external rankings because checkpoint replay is
unresolved. The saved external scores are finite (3.4459 ± 3.2320); CPU replay
disagrees and there is no recorded divergence threshold. Historical generated
displays and the frozen diagnostic keep their original labels; they are not a
repaired CDE comparison.

## 3. Reconstruct the CinC-2012 table or retrain from open cohorts

### Table reconstruction from shipped records

The complete 88-run results are shipped in
`results/clinical_v4_v1/cinc2012/cinc2012_results.json`. Reconstruct their table
without data, checkpoints or training:

```bash
python3 tools/cinc2012/aggregate_cinc2012.py \
  --from-summary results/clinical_v4_v1/cinc2012/cinc2012_results.json \
  --out-table runs/tables/TABLE_CINC2012.md
```

This recomputes means and sample standard deviations from each model's four
saved seed metrics and checks them against the archived summaries. The output
reproduces the shipped `TABLE_CINC2012.md`. It does not regenerate predictions
or independently rederive the original per-stay error sums. The historical
`run_manifest.json` in the results directory retains original source, cohort,
checkpoint and error-archive fingerprints. Its locators are provenance records.

### Open data and cohort rebuilding for retraining

The data sources and licences are listed in `README.md`. No credentials are
needed for the specified open corpora. The CinC-2019 fetcher lists and downloads the
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

### CinC-2012 retraining and transfer evaluation

`tools/cinc2012/` contains the within-corpus trainer, transfer evaluator, launcher
and strict error-archive aggregator. `manifests/cinc2012_commands.json` maps all
88 historical commands to repository-relative scripts, inputs and outputs.
The frozen result JSONs remain unchanged. Enumerate the commands before fitting:

```bash
python3 tools/cinc2012/host_driver.py --dry-run
python3 tools/cinc2012/host_driver.py --dry-run --device cpu --threads 1 \
  --manifest runs/cinc2012_plan.json
make cinc2012-smoke
```

Dry-run prints exactly 88 commands and needs neither cohorts nor checkpoints.
The smoke needs the rebuilt within-2012 and reference 2019 cohorts. It performs
one GRU fit on CPU with `--max-stays 64 --epochs 1`, using 32 training,
8 validation and 24 set-b stays. Each invocation preserves outputs in a fresh
directory under `runs/cinc2012-smoke/`. No checkpoints are shipped, so the
transfer smoke is explicitly skipped in a clean distribution. If a source
CinC-2019 checkpoint is present at a documented fit path, the target also runs
one transfer evaluation with 32 stays from each 2012 set. A within-2012
checkpoint is never used as a transfer source.

For the full 88-run series, create the 44 CinC-2019 source checkpoints
using the clinical and learned-graph suites from section 5. These are substantial
training prerequisites, separate from the 44 within-2012 fits:

```bash
python3 tools/run_experiments.py --suite clinical --device cpu --threads 1 --run
python3 tools/run_experiments.py --suite learned_graphs --device cpu --threads 1 --run
python3 tools/cinc2012/host_driver.py --run --device cpu --threads 1
python3 tools/cinc2012/aggregate_cinc2012.py --root runs/cinc2012
```

The transfer evaluator reads v4 checkpoints and their run records from
`runs/clinical/selected/MODEL/seedN/`, and graph-port `.pt`/`.json` pairs from
`runs/learned_graphs/MODEL/cinc_MODEL_sN`. It verifies model/seed/configuration,
checkpoint hash and the frozen 2019 training-cohort hash. The nine within-corpus
models use the shipped 2019 selection in `results/v4/selection.json`; the two
learned graphs keep their declared paper configurations. No selection is
performed on the 2012 test sets. Full runs retain batch size 128, 35 epochs,
patience 8 and minimum improvement 0.0001, with the original optimizer,
schedule, losses and clipping. Within uses only 2012 A-train normalization and
evaluates set-b after validation selection. Transfer uses 2019 A-train
normalization, evaluates both 2012 sets and performs no fitting.

The launcher defaults to the historical CUDA lanes and four threads, or accepts
`--devices cuda:0,cuda:1` for the local machine. The explicit CPU command above
uses one sequential lane. Before GPU execution, unset the `CUDA_VISIBLE_DEVICES`
variable cleared in section 1, or select the intended visible GPUs and their
lane indices. The launcher checks every required input and destination before
launch, preserves existing outputs/logs and records child exit codes. All new
runs, errors, checkpoints, summaries and tables go under `runs/cinc2012/`;
use a fresh `--out-root runs/cinc2012_repeat` for another series. Strict
aggregation requires all 88 full-scope runs and rederives each metric from its
per-stay error archive. Pooled transfer sums squared errors and observed-entry
counts across sets before taking the square root. `--allow-partial` is for
labelled diagnostics only. The packaging check ran the CPU smoke; it did not
repeat the full training series. See `tools/cinc2012/README.md` for details.

## 4. Regenerate simulator datasets from manifests

```bash
python3 tools/replay_simulators.py --group all
python3 tools/replay_simulators.py --group all --run
python3 tools/replay_simulators.py --group all --verify-only
```

The command without `--run` prints the exact per-dataset sequence. The second regenerates
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

## 5. Rerun the distributed experiment suites

A full rerun is substantial CPU work. The staging smoke is deliberately small;
the archived results are already included for inspecting and regenerating the
published displays. Training randomness or hardware/library differences can
change fitted scores, so model-training results do not carry a byte-identity
promise. Match the recorded settings, report the new environment and compare
estimates at their stated uncertainty.

Enumerate the historical suite sequence without training:

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
| `crn` | 72 full-adaptation policy fits, 36 balancing-weight fits and four longer zero-weight randomised-dose controls. These legacy controls retain the minute-60 counterfactual / minute-72 factual onset mismatch; randomising eventual dose alone does not identify the earlier-start intervention. The zero-weight sweep keeps the full CRN architecture. |
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

### v5 primary, sensitivity and repaired-policy experiments

The historical launcher above does not include the additional v5 suites. Their
plans can be enumerated without fitting or accessing data:

```bash
bash experiments/shared_input_primary/run_host_e2.sh --dry-run
bash experiments/positive_control/run_host_e1.sh --dry-run
bash experiments/counterfactual_onset_matched/run_host_e3.sh --dry-run
bash experiments/counterfactual_onset_matched/run_host_e3.sh --dry-run --group matched-control
bash experiments/learned_graph_validation/run_host_e5.sh --dry-run
python3 -B experiments/learned_graph_validation/grafiti_p12_reproduce.py --dry-run
```

| Suite | Expected saved result and interpretation |
|---|---|
| [Shared-input primary and budgets](experiments/shared_input_primary/README.md) | 70 commands: six A-validation grid cells, 40 arm fits, 24 budget fits. At 35 epochs, shared none is 0.7559 / 0.8088 A/B; minus GRU-D +0.0101 [+0.0072, +0.0130] / +0.0029 [+0.0003, +0.0056], 95% paired t CIs over four seeds. No primary edge set is consistently better than none. At 70 epochs, none is 0.7496 / 0.8070 and its same-cap deficits are +0.0007 [−0.0030, +0.0044] / −0.0026 [−0.0088, +0.0036]. Keep this budget series separate from the 35-epoch table; the admissible model does not close its gap, and both organ models worsen at 105 epochs. |
| [Registered positive control](experiments/positive_control/README.md) | Three dataset generations and 96 fits. Registered PASS: at κ = 1, none/reversed/random minus admissible macro-NRMSE gaps are +0.0160 [+0.0142, +0.0179], +0.0167 [+0.0142, +0.0192] and +0.0117 [+0.0027, +0.0208], positive in 4/4 seeds each. One generated population, four training/split seeds, artificial drive/delays; no clinical edge benefit or superiority over a full-input monolithic GRU is established. |
| [Onset-matched policies](experiments/counterfactual_onset_matched/README.md) | 184 core commands plus four matched Control-GRU fits; 188 saved records. Alternative and factual treatment begin at minute 72; score 60,480 post-effect cells. Widening support at fixed Spearman 0.300 improves all models (+0.54 to +0.59 endpoint gains, paired CIs excluding zero); dependence-only spans only 0–0.30 at fixed tercile support. Repaired CRN-lite has no consistent gain; continuous-dose CRN trails the matched Control-GRU in all six λ/epoch arms and 4/4 seeds on the same randomised-dose archive. |
| [Learned-graph validation](experiments/learned_graph_validation/README.md) | 24 adjacency fits plus one published-protocol GraFITi attempt. Test MSE 0.3027 versus published 0.286 ± 0.001 (+0.0167, 5.8%); published precision is not reproduced. Fixed adjacency leaves GraFITi A-test RMSE nearly unchanged (0.7482–0.7483); t-PatchGNN increases by +0.0025 to +0.0046 from 0.7492. |

Use each linked README's execution flag and fresh output directory after
preparing its inputs. The primary shared-input series was selected separately
on A-validation; neither the post-hoc renal diagnostic nor the fixed-configuration
shared-input edge diagnostic is a primary-table ranking. They retain four-seed,
capacity and input-access qualifications. Table reconstruction reads saved
numbers; it is distinct from checkpoint inference and a new model fit.

Counterfactual qualifications remain material: the separate dependence family
cannot test severe deterministic dependence beyond rank correlation 0.30.
Four historical dataset-hash discrepancies affect three training archives;
matching saved predictions and test truth does not recover the unavailable
earlier training arrays or establish their identity. Legacy c × σ cells jointly
vary support and dependence, retain an onset mismatch and a pre-switch scoring
boundary, and cannot be exactly rescored without missing predicted trajectories.
The legacy CRN-lite auxiliary target is identically zero, so its agreement with
Control-GRU does not test balancing against varying dose.

## 6. Distribution lineage and limits

`SHA256SUMS` covers every current distributed file except itself.
`manifests/distribution.json` records original and distributed hashes and sizes
for the v1.1.0 distribution; it is preserved unchanged in this documentation-only
update. Its entries for edited Markdown and the overview PNG describe v1.1.0
bytes. `manifests/readme_trace.json` likewise maps the historical v4 README
claims, rather than the current primary table. Current claim sources are linked
in the README and experiment folders. [Release notes](docs/RELEASE_V1_1_1.md)
explain this scope; use `SHA256SUMS` for current distribution integrity.
`manifests/TRANSFORMATIONS.md` preserves the earlier path/import/provenance edits.
The core organ model, clinical-baseline module and base simulator are copied
byte for byte. Original scientific JSON/CSV numbers are unchanged; only descriptive
strings, private paths and JSON formatting are transformed for distribution.

The earlier artifact build verified CPU smoke tests, complete cohort bytes,
selected full-size simulator regeneration and numerical preservation of frozen
records. This documentation update checks scope, exclusions and current file
hashes without repeating those computational checks. The earlier build did not
repeat the complete training series or test remote download availability.
Historical simulator seed aggregates support table reconstruction; recomputing
patient statistics from predictions requires the locally rerun error artifacts.
The CinC-2012 table reconstruction reproduces all shipped displays, while the
new CPU smoke checks one within-corpus fit; the full 88-run series was not
repeated during packaging. The README identifies the v1.1.2 documentation
update, the v1.1.0 source commit and archive record, and the concept DOI.
The CinC-2012 results remain the recorded 88-run partitioned-input evidence.
External CinC-2019 CDE checkpoint replay remains unresolved, and its finite
saved errors remain outside confirmed rankings. No new training, repaired
checkpoint replay, historical training-array recovery or archival deposit is
claimed by this documentation update.
