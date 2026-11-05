![PhysioGraphBench overview](figures/F1_overview.png)

# PhysioGraphBench: when do physiological graph priors help?

**Version 1.0.1.** This update adds the CinC-2012 training/evaluation drivers to
the published [v1.0.0 baseline](https://github.com/wwhite777/physiographbench/tree/v1.0.0),
pinned at commit [d7b5491bde5d033643611848f69f7e6eabe1e2b7](https://github.com/wwhite777/physiographbench/tree/d7b5491bde5d033643611848f69f7e6eabe1e2b7).
The frozen numerical results are unchanged. Use the versioned release archive
for this update; the cited Zenodo DOI below archives the v1.0.0 baseline.

**On hourly intensive care forecasting, tuned GRU-D outperforms the hand-specified organ graph; matched simulator controls attribute the earlier apparent graph gain to factorisation.**

This is a benchmark release: the simulator, cohort builders, baselines, protocols,
and frozen v4 results for evaluating physiological graph priors. The findings
concern the tested prediction tasks and implementations. They do not establish
clinical utility or validate recovered edges as causal physiology.

Figure 1 summarizes the two open corpora, the three-organ simulator and the v4
audit protocol. Its CinC-2012 set-b comparison is GRU-D 0.7684 versus
PhysioGraph-GRU 0.8239 under within-corpus training. The clinical models use four
organ groups; zero simulator coupling retains a shared sepsis course.

## Main findings

The task observes a 12-hour context and predicts the next 12 hours. Root mean
squared error (RMSE) is pooled over observed target entries after normalization
by training-cohort statistics; lower is better. In CinC-2019, set A is internal
and set B is external. Values are mean ± sample standard deviation over four seeds.

| Model | Internal A | External B | Frozen source |
|---|---:|---:|---|
| GRU-D | 0.7458 ± 0.0005 | 0.8059 ± 0.0009 | [selected runs](results/v4/tuning_grid.json) |
| PhysioGraph-GRU | 0.7702 ± 0.0022 | 0.8177 ± 0.0010 | [selected runs](results/v4/tuning_grid.json) |
| t-PatchGNN | 0.7492 ± 0.0016 | 0.7939 ± 0.0009 | [four runs](results/learned_graph_baselines_v1/tpatchgnn/) |
| GraFITi | 0.7483 ± 0.0003 | 0.7932 ± 0.0001 | [four runs](results/learned_graph_baselines_v1/grafiti_v3/) |

GRU-D and PhysioGraph-GRU use the same learning-rate × width grid, validation
selection, and 35-epoch cap. The selected GRU-D has 449,568 parameters and
PhysioGraph-GRU has 912,032. t-PatchGNN and GraFITi use declared paper settings
without a grid; this is a comparison of tuned recurrent models with untuned
learned variable graphs. Both learned graphs achieve lower external error than
the tuned recurrent reference. The implementations and declared adaptations
are described in [baselines/METHODS.md](baselines/METHODS.md).

On CinC-2012, transfer evaluates the CinC-2019-trained models with CinC-2019
training normalization on set-a and set-b, pooling 7,982 eligible stays.
Within-corpus training uses set-a (3,390 training / 599 validation stays),
CinC-2012 training normalization and the CinC-2019-selected configurations,
then evaluates set-b (3,993 eligible stays). The 16-variable protocol is shared.

| Model | CinC-2012 transfer, pooled | CinC-2012 within, set-b | Frozen source |
|---|---:|---:|---|
| GRU-D | 0.8273 ± 0.0018 | 0.7684 ± 0.0018 | [Result table](results/clinical_v4_v1/cinc2012/TABLE_CINC2012.md) |
| PhysioGraph-GRU | 0.8529 ± 0.0020 | 0.8239 ± 0.0152 | [Result table](results/clinical_v4_v1/cinc2012/TABLE_CINC2012.md) |
| t-PatchGNN | 0.8142 ± 0.0005 | 0.7460 ± 0.0029 | [Result table](results/clinical_v4_v1/cinc2012/TABLE_CINC2012.md) |
| GraFITi | 0.8192 ± 0.0059 | 0.7335 ± 0.0017 | [Result table](results/clinical_v4_v1/cinc2012/TABLE_CINC2012.md) |

The CinC-2012 corpus overlaps CinC-2019 set-A's hospital system, and its set-a
and set-b are not asserted to be different hospitals. Its arterial oxygen
saturation (SaO2) stands in for pulse-oximetry oxygen saturation (O2Sat).

| Question | v4 finding | Frozen evidence |
|---|---|---|
| Does the clinical gap depend on capacity? | Plain GRU (444,944 parameters; 0.7489 / 0.8059 A/B) and GRU-D beat PhysioGraph-GRU with about half its parameters. Wider GRU-med (2,586,896; 0.7475 / 0.8068) and GRU-large (6,498,320; 0.7533 / 0.8104) do not improve on GRU-D; selected GRU-med is not parameter-matched. PhysioGraph-GRU minus GRU-D paired per-stay gaps are 0.0198 ± 0.0022 on A and 0.0115 ± 0.0007 on B. | [Tuning](results/v4/tuning_grid.json), [paired statistics](results/v4/stats_v4.json) |
| Do imposed edge sets distinguish clinical performance? | No edge set is consistently better, including no edges. Across six variants, GRU-backbone mean RMSE spans 0.0024 / 0.0025 A/B; state-space-backbone spans are 0.0067 / 0.0075, with no variant best on both cohorts (seed standard deviations 0.001–0.005). These tables do not establish statistical equivalence. | [Variants](results/v4/variant_ablation_v4.json) |
| What explains the simulator gain? | At κ = 1: capacity-matched monolithic GRU 0.0389 → factorised no edges 0.0364 → physiological edges 0.0377. Admissible edges show no consistent improvement across κ ∈ {0, .1, .25, .5, .75, 1}: worse at five of six values and tied at κ = 0.75 (paired difference −0.00001). Factorisation carries the earlier gain; edges subtract. | [Matched controls](results/sim_grids_v1/h3_grid_with_controls.json) |
| When are counterfactual directions recovered? | With deterministic severity-driven dosing (σ = 0) and shared histories, all four primary models recover all three population directions at c ≤ 0.1, two at c = 0.25 and none at c ≥ 0.5. With assignment noise σ ≥ 0.15, mean arterial pressure and urine-output directions survive even at c = 1 (0.86–0.96); at σ = 0.25 all three survive to c = 0.5. Lactate fails earlier; loss of treatment support governs recovery. | [Policy grid](results/sim_grids_v1/h5_grid.json) |
| Does treatment balancing rescue direction recovery? | Neither the CRN-lite surrogate nor the continuous-dose CRN adaptation improves on the unadjusted GRU. The full adaptation fails the identifiable positive control even with different balancing weights and up to 120 epochs. | [Policy grid](results/sim_grids_v1/h5_grid.json), [CRN sweep](results/learned_graph_baselines_v1/crn_v2_lambda_sweep/) |
| How much next-hour cross-organ predictive gain is observed? | Ridge gain on A validation is +0.0033 [0.0023, 0.0043]; there is no positive gain on B. Coupled hourly simulator settings score 0.17–0.21 on the same definition; no numerical mapping onto κ is claimed. | [Clinical index](results/coupling_index_v1/coupling_index.json), [hourly simulator](results/coupling_index_v1/simulator_hourly/sim_hourly_index.json) |
| Does the external graph gap close with horizon? | With a 12-hour context on the common cohort with at least 48 hours: +0.026 at horizon 6, +0.021 at 12, +0.019 at 24. | [Horizon table](results/v4/horizon_table_v4.json) |
| Can the cohort be rebuilt? | All 40,336 public raw files are included, with zero exclusions. Rebuilding reproduces the complete CinC-2019 archive bytes. Both CinC-2012 cohort views also have expected archive and per-array hashes. | [Replay](results/cohort_replay_v1/REPLAY_RESULTS.json), [cohort hashes](manifests/cohorts.json) |
| Do the orderings reproduce on CinC-2012? | Both orderings reproduce with larger margins: transfer GRU-D 0.8273 ± 0.0018 versus PhysioGraph-GRU 0.8529 ± 0.0020; within-corpus 0.7684 ± 0.0018 versus 0.8239 ± 0.0152. Learned variable graphs have the lowest errors on both protocols (t-PatchGNN 0.8142 / 0.7460; GraFITi 0.8192 / 0.7335, transfer / within). Organ-graph models are the least seed-stable. The corpus overlaps CinC-2019 set-A's hospital system. | [Full table](results/clinical_v4_v1/cinc2012/TABLE_CINC2012.md), [numerical results](results/clinical_v4_v1/cinc2012/cinc2012_results.json), [interpretation](results/clinical_v4_v1/cinc2012/CINC2012_READING.md) |
| What is withheld as a numerical comparison? | Neural controlled differential equation (CDE) external inference on CinC-2019 is unstable and is reported as diverged. Its CinC-2012 results are finite and are retained in the full table. | [CDE diagnosis](results/v4/ncde_diagnosis.md), [CinC-2012 table](results/clinical_v4_v1/cinc2012/TABLE_CINC2012.md) |

The simulator score is a macro-average of organ errors normalized by one fixed
reference range; it is distinct from clinical pooled RMSE. κ scales the tested
coupling terms; c controls severity-dependent dosing; σ is the total standard
deviation of assignment noise. The counterfactual grid holds observed history
fixed and changes the future dose. Direction recovery means recovering the sign
of the simulated response to adjacent doses. The four primary models are the
organ state-space model, organ GRU, monolithic Control-GRU, and CRN-lite.

## Data and licences

| Resource | Access | Data licence | Reproduction |
|---|---|---|---|
| CinC-2019 sepsis challenge, version 1.0.0 | [PhysioNet](https://physionet.org/content/challenge-2019/1.0.0/), [public S3 mirror](https://physionet-open.s3.amazonaws.com/) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | `python3 tools/fetch_s3_cinc2019.py --root data` |
| CinC-2012 challenge, version 1.0.0 | [PhysioNet](https://physionet.org/content/challenge-2012/1.0.0/) | [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/) | `python3 tools/fetch_cinc2012.py --root data/cinc2012` |
| Simulator and benchmark software | This repository | [MIT](LICENSE) | `python3 tools/replay_simulators.py --group all --run` |

Data attribution: PhysioNet/Computing in Cardiology Challenge 2019, Early Prediction
of Sepsis from Clinical Data; PhysioNet/Computing in Cardiology Challenge 2012,
Predicting Mortality of ICU Patients. Preserve the original dataset attribution
and applicable data terms when obtaining or reusing the corpora. The MIT software
licence does not replace the upstream data licences. No raw patient data or model
weights are redistributed here.

## Run the artifact

Use Python and the package versions in [requirements.txt](requirements.txt).
The recorded environment is [manifests/environment.json](manifests/environment.json).
From the repository root:

```bash
make smoke
make findings
python3 tools/summarize_results.py --out-dir runs/tables --check
python3 tools/cinc2012/host_driver.py --dry-run --device cpu --threads 1
python3 tools/cinc2012/aggregate_cinc2012.py \
  --from-summary results/clinical_v4_v1/cinc2012/cinc2012_results.json \
  --out-table runs/tables/TABLE_CINC2012.md
```

The complete download, cohort rebuild, simulator generation, experiment, table,
and figure sequence is in [REPRODUCE.md](REPRODUCE.md), including expected hashes.
`PHYSIOGRAPH_ROOT` can select the repository root; `TMPDIR` selects private scratch.
The v4 experiment outputs go to `runs/`, with generated-data and probe caches
in ignored `data/` and `artifacts/` locations. `results/` holds the frozen records. `SHA256SUMS` checks the exact public distribution. Historical source and
archive fingerprints are retained separately from distribution fingerprints.

CinC-2012 table reconstruction uses the shipped per-seed records and requires
no training. Its [drivers and 88-command manifest](tools/cinc2012/README.md)
also support retraining and transfer evaluation after the cohorts and CinC-2019
source checkpoints are rebuilt. `make cinc2012-smoke` runs one 64-stay,
one-epoch CPU fit after cohort rebuilding; a clean distribution explicitly
skips transfer smoke because weights are not shipped. The full prerequisites,
CPU/GPU launch commands and aggregation are in [REPRODUCE.md section 3](REPRODUCE.md#3-reconstruct-the-cinc-2012-table-or-retrain-from-open-cohorts).

| Directory | Contents |
|---|---|
| `src/` | Original organ model, clinical baselines, loader, cohort parser, simulator, and supporting legacy entry points |
| `tools/` | Portable v4 protocol, cohort/replay utilities, statistics, coupling index, experiment plans, table/plot generation |
| `tools/cinc2012/` | CinC-2012 within-corpus training, frozen-source transfer, 88-run launcher and table/error aggregation |
| `sim/` | Matched edge controls, shared-history generation, monolithic controls, grid aggregators |
| `baselines/` | Paper-based variable-graph and continuous-dose CRN adaptations |
| `results/` | Frozen numerical evidence and machine-generated display tables |
| `manifests/` | Generation settings, original/distributed hashes, environment, cohort and simulator array checks |

## Limitations

Diagnostics: the post-hoc [renal shared-input diagnostic](diagnostics/renal_shared_input/)
compares partitioned and shared inputs at one fixed configuration over four paired seeds;
its code, saved runs, limitations and rerun commands accompany the reported results.
The post-hoc [shared-input edge ablation](diagnostics/shared_input_edges/) adds six fixed edge sets over four paired seeds, with code, archived runs and rerun commands.

The simulator findings come from one simulator family with three organ groups:
cardiovascular, renal and metabolic. This structure-matched setting does not
establish generality across physiological simulators or all organ systems.

Clinical forecasting does not observe treatments in CinC-2019. Counterfactual
claims therefore refer to the simulator. The simulator contains cardiovascular,
renal and metabolic groups, a step onset of sepsis, and a shared sepsis course
even at κ = 0. Its extended hourly trajectories can reach nonphysiological
states; the hourly index is descriptive calibration and does not validate the
simulator or locate the clinical data on a causal coupling scale.

The clinical forecasting protocol contains no real treatment variables or
interventions; treatment-direction claims are confined to simulated outcomes.
Each reported comparison uses four seeds. Seed standard deviations summarize
that limited set of runs and do not establish broad robustness. Neural CDE
diverged during external CinC-2019 re-inference and is excluded from numerical
comparisons there; finite CinC-2012 runs do not resolve that failure.

The learned variable graphs use paper hyper-parameters without a tuning grid,
whereas the recurrent and organ-graph models use equal-budget validation tuning.
Their rankings compare these implementations and settings, rather than an equal
search over every model family. Within-corpus CinC-2012 configurations were
selected on CinC-2019 and were not re-tuned on CinC-2012. The hospital-system
overlap and measurement substitutions described above limit claims of
independent clinical generalization.

Two lineage disclosures affect interpretation of the earlier results.
The earlier counterfactual targets received treatment since warm-up and did not
share the factual history. v4 branches from the factual state at the future
intervention time. Severity–dose correlations are measured per file; the policy
noise term is retained. The previously reported per-window interval came from a
checkpoint pair that was later overwritten. v4 saves seed-specific checkpoints
when rerun and distinguishes seed variation from paired patient sampling
uncertainty. Historical diagnostics and their exception remain in the frozen run
manifest; they are not silently relabelled as new evidence.

The cohort uses numerical units as distributed: inspired oxygen fraction (FiO2)
is fraction-valued; lactate is on the mmol/L numerical scale despite conflicting
upstream descriptions. The CinC-2012 report documents its hourly pressure
fallback, modality differences, missing static covariates, and evaluation-only
transfer view. These are reproducible measurement and protocol choices rather
than evidence of clinical interchangeability.

Code and data transformations for distribution preserve numerical results and
record both original and distributed file hashes in
[manifests/distribution.json](manifests/distribution.json). Simulator metadata
contains new paths and code fingerprints, so the portable archive bytes can
differ while every scientific array is checked against frozen payload hashes.

## Citation

Code and results: https://github.com/wwhite777/physiographbench — archived at Zenodo, DOI 10.5281/zenodo.23976172.

```bibtex
@software{jeong2026physiographbench,
  author    = {Jeong, Woncheol and Oh, Hayoung},
  title     = {PhysioGraphBench: code, results and diagnostics for a matched-control benchmark of physiological graph priors in multi-organ ICU trajectory forecasting},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.23976172},
  url       = {https://github.com/wwhite777/physiographbench}
}
```

Software is distributed under the [MIT licence](LICENSE).
