# Measured compute accounting for PhysioGraphBench

Snapshot: E2/E4 refreshed 2026-11-06T00:03:17.202224+00:00 to 2026-11-06T00:03:17.581103+00:00; all other rows and hardware observations retain the v1 snapshot 2026-11-05T14:47:31.977205+00:00 to 2026-11-05T14:47:33.909724+00:00. Timings are wall-clock seconds from saved records. A fit means one independently trained model/configuration/seed; an evaluation job scores an existing checkpoint without fitting. GPU and CPU hours below are sums of job wall times assigned to those devices.

**Requested benchmark families: 113.1120 GPU job-hours and 16.1712 CPU job-hours, covering 1509 fits and 45 evaluation jobs with saved timers. These are recorded-cost subtotals, not a complete lifetime compute claim.**

The v1 accounting-host snapshot reports NVIDIA L40S GPUs and driver 550.163.01 through `/proc/driver/nvidia`; its CPU is INTEL(R) XEON(R) SILVER 4510. The one `nvidia-smi` query failed to communicate with the driver and was not retried. These are v1 host observations inherited without a new hardware query; historical run records identify CUDA/CPU devices but do not attest historical hardware model/driver. Clinical run records report PyTorch `2.6.0+cu124` in `/runtime/torch`.

| Experiment / paper use | Fits / expected fits | Timed jobs / observed jobs | Assigned device(s) | Seconds per recorded fit/job: mean (min–max) | Total job-device hours | Runtime field |
|---|---:|---:|---|---:|---:|---|
| Table 1 clinical tuning grid | 54/54 | 54/54 | cuda:1, cuda:2, cuda:3 | 882.97 (52.15–4165.27) | 13.2446 GPU | `/seconds` |
| Table 1 clinical selected fits | 36/36 | 36/36 | cuda:1, cuda:2, cuda:3 | 900.45 (89.08–3395.91) | 9.0045 GPU | `/seconds` |
| Clinical variant ablation: additional fits | 40/40 | 40/40 | cuda:1, cuda:2, cuda:3 | 1870.91 (1026.99–2607.42) | 20.7879 GPU | `/seconds` |
| Horizon C12_K12 | 36/36 | 36/36 | cuda:1, cuda:2, cuda:3 | 246.05 (22.67–747.44) | 2.4605 GPU | `/seconds` |
| Horizon C12_K24 | 36/36 | 36/36 | cuda:1, cuda:2, cuda:3 | 346.87 (42.53–1296.30) | 3.4687 GPU | `/seconds` |
| Horizon C12_K6 | 36/36 | 36/36 | cuda:1, cuda:2, cuda:3 | 196.49 (23.08–806.12) | 1.9649 GPU | `/seconds` |
| Horizon C24_K12 | 36/36 | 36/36 | cuda:1, cuda:2, cuda:3 | 497.07 (32.23–2826.33) | 4.9707 GPU | `/seconds` |
| Horizon C24_K24 | 36/36 | 36/36 | cuda:1, cuda:2, cuda:3 | 586.80 (41.31–3193.85) | 5.8680 GPU | `/seconds` |
| Learned clinical graph: t-PatchGNN | 4/4 | 4/4 | cpu | 1889.61 (1815.82–1968.90) | 2.0996 CPU | `/elapsed_seconds` |
| Learned clinical graph: GraFITi v3 | 4/4 | 4/4 | cpu | 421.03 (347.91–448.49) | 0.4678 CPU | `/elapsed_seconds` |
| Continuous-dose CRN: frozen shared-history grid | 72/72 | 72/72 | cpu | 129.97 (94.06–295.33) | 2.5994 CPU | `/timing/elapsed_seconds` |
| Continuous-dose CRN: frozen λ/budget diagnostics | 40/40 | 40/40 | cpu | 117.70 (96.04–221.39) | 1.3078 CPU | `/timing/elapsed_seconds` |
| CinC-2012 within | 44/44 | 44/44 | cuda:1, cuda:2, cuda:3 | 198.51 (27.45–730.72) | 2.4262 GPU | `/seconds` |
| CinC-2012 transfer | 0 (evaluation only) | 44/44 | cuda:1, cuda:2, cuda:3 | 5.21 (1.02–18.68) | 0.0637 GPU | `/seconds` |
| Simulator κ grid: six edge variants | 144/144 | 144/144 | cuda:1, cuda:2, cuda:3 | 137.05 (74.35–247.60) | 5.4818 GPU | `/elapsed_seconds` |
| Simulator κ grid: monolithic GRU | 24/24 | 24/24 | cuda:1, cuda:2, cuda:3 | 8.27 (7.78–8.69) | 0.0551 GPU | `/elapsed_seconds` |
| Simulator κ grid: capacity-matched GRU | 24/24 | 24/24 | cuda:1, cuda:2, cuda:3 | 10.88 (10.19–11.70) | 0.0725 GPU | `/elapsed_seconds` |
| Counterfactual frozen grid: shared | 384/384 | 384/384 | cpu | 44.00 (4.03–112.87) | 4.6928 CPU | `/elapsed_seconds` |
| Counterfactual frozen grid: legacy | 48/48 | 48/48 | cpu | 50.45 (6.41–106.42) | 0.6727 CPU | `/elapsed_seconds` |
| Renal diagnostic: partitioned/shared input fits | 8/8 | 8/8 | cuda:1, cuda:2, cuda:3 | 989.59 (957.76–1030.74) | 2.1991 GPU | `/seconds` |
| Renal diagnostic: fixed-checkpoint replay | 0 (evaluation only) | 1/1 | cpu | 103.70 (103.70–103.70) | 0.0288 CPU | `/seconds` |
| Shared-input edge ablation (shared-edge diagnostic) | 24/24 | 24/24 | cuda | 1478.22 (989.34–1938.63) | 9.8548 GPU | `/seconds` |
| E1 positive-control regime | 96/96 | 96/96 | cuda | 82.18 (10.48–157.59) | 2.1914 GPU | `/timing/total_seconds` |
| E2 shared-input tuning grid | 6/6 | 6/6 | cuda | 1145.03 (1075.96–1295.15) | 1.9084 GPU | `/seconds` |
| E2 shared-input primary arms | 40/40 | 40/40 | cuda | 1479.30 (1004.89–2074.61) | 16.4367 GPU | `/seconds` |
| E4 extended-budget fits | 24/24 | 24/24 | cuda | 1462.28 (135.55–2696.84) | 9.7485 GPU | `/seconds` |
| E3 support-only sweep | 80/80 | 80/80 | cpu | 71.09 (4.03–137.14) | 1.5798 CPU | `/timing/total_seconds` |
| E3 dependence-only sweep | 80/80 | 80/80 | cpu | 65.49 (4.44–141.96) | 1.4554 CPU | `/timing/total_seconds` |
| E3 onset-matched continuous-dose CRN | 24/24 | 24/24 | cpu | 189.48 (102.37–283.66) | 1.2632 CPU | `/timing/total_seconds` |
| E3 CRN diagnostic: matched Control-GRU | 4/4 | 4/4 | cpu | 3.61 (3.14–4.94) | 0.0040 CPU | `/timing/total_seconds` |
| E5 adjacency ablation: grafiti | 12/12 | 12/12 | cuda | 114.48 (100.95–125.99) | 0.3816 GPU | `/elapsed_seconds` |
| E5 adjacency ablation: tpatchgnn | 12/12 | 12/12 | cuda | 111.48 (108.11–114.52) | 0.3716 GPU | `/elapsed_seconds` |
| E5 P12 reproduction attempt | 1/1 | 1/1 | cuda | 543.09 (543.09–543.09) | 0.1509 GPU | `/elapsed_seconds` |

For evaluation-only rows, the runtime distribution is per evaluation job. E2/E4 now includes all 70 completed fits: 6 tuning-grid fits, 40 primary-arm fits and 24 extended-budget fits. The 3 tuning-grid fits already included in v1 are counted once; this revision adds 67 fits. Unrecorded timing components remain unknown.

Clinical Table 1 training is the 54-fit grid plus 36 newly fitted selected runs. Persistence adds no training fit. The variant table contains 48 result entries but reuses 8 admissible selected fits, leaving 40 additional fits. The five common-long-stay horizon designs contribute 180 separate fits, including a separately fitted C12/K12 design. Copied tuning summaries, material exports and repeated paper references do not create additional fits. renal diagnostic and shared-edge diagnostic none-arm reruns remain separate executions even when their scores agree.

Timing boundaries and inference cost:

| Family | Recorded timer includes | Separately measured final evaluation |
|---|---|---|
| Table 1 clinical tuning grid | Training and epoch validation; starts after data/model setup and ends before checkpoint save and final A/B scoring. | not recorded |
| Table 1 clinical selected fits | Training and epoch validation; starts after data/model setup and ends before checkpoint save and final A/B scoring. | not recorded |
| Clinical variant ablation: additional fits | Training and epoch validation; starts after data/model setup and ends before checkpoint save and final A/B scoring. | not recorded |
| Horizon C12_K12 | Training and epoch validation; starts after data/model setup and ends before checkpoint save and final A/B scoring. | not recorded |
| Horizon C12_K24 | Training and epoch validation; starts after data/model setup and ends before checkpoint save and final A/B scoring. | not recorded |
| Horizon C12_K6 | Training and epoch validation; starts after data/model setup and ends before checkpoint save and final A/B scoring. | not recorded |
| Horizon C24_K12 | Training and epoch validation; starts after data/model setup and ends before checkpoint save and final A/B scoring. | not recorded |
| Horizon C24_K24 | Training and epoch validation; starts after data/model setup and ends before checkpoint save and final A/B scoring. | not recorded |
| Learned clinical graph: t-PatchGNN | Whole adapter run including setup, validation-selected training and A/B evaluation. | not recorded |
| Learned clinical graph: GraFITi v3 | Whole adapter run including setup, validation-selected training and A/B evaluation. | not recorded |
| Continuous-dose CRN: frozen shared-history grid | Whole CRN run; data and training are separately timed, final prediction/scoring is included but not separately timed. | not recorded |
| Continuous-dose CRN: frozen λ/budget diagnostics | Whole CRN run; data and training are separately timed, final prediction/scoring is included but not separately timed. | not recorded |
| CinC-2012 within | Whole job including loading/setup and held-out scoring; fitting included. | not recorded |
| CinC-2012 transfer | Whole job including loading/setup and held-out scoring; no training. | 5.21 (1.02–18.68) s; 0.063711 job-hours; `/seconds` |
| Simulator κ grid: six edge variants | Whole simulator fit job; data, training and final evaluation separately timed. | 1.41 (0.70–2.77) s; 0.056214 job-hours; `/timing/evaluation_seconds` |
| Simulator κ grid: monolithic GRU | Whole simulator fit job; data, training and final evaluation separately timed. | 0.09 (0.06–0.10) s; 0.000576 job-hours; `/timing/evaluation_seconds` |
| Simulator κ grid: capacity-matched GRU | Whole simulator fit job; data, training and final evaluation separately timed. | 0.11 (0.09–0.13) s; 0.000737 job-hours; `/timing/evaluation_seconds` |
| Counterfactual frozen grid: shared | Whole simulator fit job; data, training and final evaluation separately timed. | 0.41 (0.08–1.25) s; 0.043263 job-hours; `/timing/evaluation_seconds` |
| Counterfactual frozen grid: legacy | Whole simulator fit job; data, training and final evaluation separately timed. | 0.45 (0.10–0.91) s; 0.005961 job-hours; `/timing/evaluation_seconds` |
| Renal diagnostic: partitioned/shared input fits | Training and epoch validation; starts after data/model setup and ends before checkpoint save and final A/B scoring. | not recorded |
| Renal diagnostic: fixed-checkpoint replay | One CPU diagnostic job, including 12 checkpoint loads, A/B renal scoring, persistence, consistency checks and output archives. | 103.70 (103.70–103.70) s; 0.028804 job-hours; `/seconds` |
| Shared-input edge ablation (shared-edge diagnostic) | Training and epoch validation; starts after data/model setup and ends before checkpoint save and final A/B scoring. | not recorded |
| E1 positive-control regime | Whole fit job including data loading/setup, training and final prediction/scoring; training has its own timer. | not recorded |
| E2 shared-input tuning grid | Whole job including data/model/optimizer setup, training, validation and final held-out evaluation. | not recorded |
| E2 shared-input primary arms | Whole job including data/model/optimizer setup, training, validation and final held-out evaluation. | not recorded |
| E4 extended-budget fits | Whole job including data/model/optimizer setup, training, validation and final held-out evaluation. | not recorded |
| E3 support-only sweep | Whole fit job including data generation/loading, training and final scoring; data and training separately timed. | not recorded |
| E3 dependence-only sweep | Whole fit job including data generation/loading, training and final scoring; data and training separately timed. | not recorded |
| E3 onset-matched continuous-dose CRN | Whole fit job including data generation/loading, training and final scoring; data and training separately timed. | not recorded |
| E3 CRN diagnostic: matched Control-GRU | Whole fit job including data generation/loading, training and final scoring; data and training separately timed. | not recorded |
| E5 adjacency ablation: grafiti | Whole adapter job including setup, validation-selected fitting, final scoring and checkpoint save. | not recorded |
| E5 adjacency ablation: tpatchgnn | Whole adapter job including setup, validation-selected fitting, final scoring and checkpoint save. | not recorded |
| E5 P12 reproduction attempt | Whole adapter job including parsing/preprocessing, fitting, final scoring and checkpoint save. | not recorded |

shared-input experiment snapshot: 6/6 grid records; 40/40 arm records; 24/24 budget records. All 70/70 planned E2/E4 fits have complete run records, CUDA device labels and measured `/seconds`. The remaining accounting rows retain their v1 source snapshot.

The simulator κ and frozen counterfactual records expose `/timing/evaluation_seconds`; these costs are already inside `/elapsed_seconds`. CinC-2012 transfer exposes whole evaluation-job `/seconds`, including loading and setup. CinC-2012 within `/seconds` includes fitting and scoring, without a final-inference split. E1 and E3 expose training and total time; subtracting them would mix data/setup/serialization with inference, so no inference estimate is made. Clinical v4, renal diagnostic input fits and shared-edge diagnostic stop `/seconds` before final A/B scoring: their unrecorded final inference is absent from totals, not free. E2/E4 and E5 timers include final scoring without a separate inference timer.

Additional fixed-checkpoint audit executions are shown separately so the project lead can report either experiment-only or experiment-plus-audit costs. They add no training fits.

| Fixed-checkpoint evaluation | Fits | Timed jobs | Device | Seconds/job: mean (min–max) | CPU job-hours | Source |
|---|---:|---:|---|---:|---:|---|
| Clinical fixed-checkpoint audit replay | 0 | 45/45 | cpu | 7.94 (0.60–27.47) | 0.099310 | `historical_sources/final-gate-verify/inference_results.json`; per-entry `seconds` |
| Neural CDE CPU audit probes | 0 | 4/4 | cpu | 45.41 (22.19–68.61) | 0.050453 | `historical_sources/final-gate-verify/ncde_cpu_probe.json`; per-entry `seconds` |
| CinC-2012 fixed-checkpoint audit replay | 0 | 88/88 | cpu | 3.22 (0.24–16.81) | 0.078793 | `historical_sources/cinc2012-verify/recomputed.json`; per-entry `seconds` |

The renal fixed-checkpoint job additionally covers 12 checkpoint models and persistence, each on A and B, in 103.695 CPU seconds. The clinical audit replay has 44 checkpoint jobs plus persistence. Neural CDE audit probes are actual separate CPU executions despite their numerical replay discrepancies; compute accounting does not certify scientific reproduction. CinC-2012 audit replay scores the 44 within and 44 transfer checkpoints without refitting.

**Including the three additional audit rows: 113.1120 GPU job-hours and 16.3997 CPU job-hours; 1509 fits and 182 evaluation jobs.** The added audit cost is 0.228556 CPU job-hours. Every evaluation component is counted once.

One further historical Neural CDE diagnosis job has no record timer. Adjacent launcher timestamps (2026-11-04T22:39:43Z to 2026-11-04T22:39:50Z) give an explicitly labelled **log-timestamp estimate of 7 CPU seconds (0.001944 CPU job-hours)** for the whole diagnostic. It is excluded from measured totals. No per-checkpoint duration is inferred from that aggregate.

Scope and interpretation:

- Device hours are summed assigned-device job wall times, including CPU preparation inside a GPU-labelled job where the timer includes it. They are not GPU-kernel active time, energy, unique hardware occupancy, or CPU core-hours. Clinical fits ran in six lanes on three CUDA devices, so concurrent jobs can share a GPU. No hardware count or thread count multiplies recorded durations.
- Totals cover the task-card experiment records available in this snapshot, the renal checkpoint diagnostic, and the explicitly separated audit records. Untimed final scoring, environment setup, data acquisition/cohort construction, coupling-probe fitting, simulator archive generation outside fit timers, smoke/debug/development runs, superseded/collapsed ports, other audit passes and older pre-v4 experiments are not included. Total benchmark lifetime cost is not recoverable from these records.
- The frozen counterfactual export has 432 fits: 384 shared-history fits and 48 legacy-protocol disclosure fits. The separate continuous-dose CRN grid and λ/budget diagnostics add 72 and 40 fits. E3 contains the new onset-matched sweeps/diagnostics and is counted separately.
- Arithmetic uses unrounded record values. Display rounding occurs only here. `compute_accounting_v2.json` retains individual source paths, fields, source SHA-256 digests, timing components, device provenance and aggregate formulas.

Suggested compute statement:

> Across the available records for the reported experiment families, we recorded 113.11 GPU job-hours and 16.17 CPU job-hours for 1509 fits and 45 fixed-checkpoint evaluation jobs. Additional recorded checkpoint audit replays used 0.23 CPU job-hours. GPU jobs used CUDA devices on the accounting host, which reports NVIDIA L40S GPUs; the host CPU is an Intel Xeon Silver 4510. These totals sum measured job wall times and exclude unrecorded inference and development/data-preparation work. All 70 planned E2/E4 fits are included; the other experiment families retain their original source snapshot.

## Release 1.2.0: four additional E3 re-fits

The 1,509-fit snapshot and its totals above are preserved. The four
current-archive E3 replacements are additional executions outside that
snapshot: **100.6 CPU job-seconds** (0.027953510 CPU job-hours),
summed from each replacement record’s `/timing/total_seconds`. They add
four fits, giving 1,513 recorded fit executions when combined with the
snapshot; the effective main E3 grid still has 160 records. Superseded
fits remain counted in the historical snapshot and are not subtracted.

| Replacement record under `experiments/counterfactual_onset_matched/artifacts/host/main_rerun/` | `/timing/total_seconds` |
|---|---:|
| `dependence_only/point4/crn_lite/seed3/run.json` | 3.957248413003981 |
| `support_only/point1/crn_lite/seed3/run.json` | 4.325057482346892 |
| `support_only/point1/physiograph/seed1/run.json` | 47.15915957465768 |
| `support_only/point2/physiograph_gru/seed0/run.json` | 45.19117112737149 |
| **Sum** | **100.63263659738004** |

Each timer includes data loading/setup, training and final scoring without
a separate inference timer. The re-fits used CPU and two threads; job
wall time is not multiplied by thread count. Packaging performed no fits.
These additions do not make the measured snapshot a lifetime-compute total.
