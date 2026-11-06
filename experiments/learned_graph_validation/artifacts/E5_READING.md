# E5 reading: GraFITi P12 reproduction and CinC-2019 graph ablation

Prepared by the assigned research engineer/analysis author for the project lead. This is a reading of recorded results plus explicitly labelled CPU inference recovery, with author verification; it is not an independent scientific review.

**Reproduction verdict.** Differs by +0.016702 MSE (+5.839788%): our 0.302702 exceeds the published 0.286000 ± 0.001000. This single-seed adapter attempt does not match the published reported band and cannot reproduce its multi-run variability.

The absolute gap is **0.016702 MSE** and the relative gap is **5.839788%** (fraction 0.058398); the score exceeds the published mean-plus-spread endpoint by **0.015702 MSE**. The published ± term is a descriptive reported spread, not an acceptance test or a confidence interval for this one seed. The authoritative target is the protocol project lead addendum; the original run JSON retains its earlier target placeholder and false match flag.

| P12 quantity | Value | Source file / field |
| --- | ---: | --- |
| Published MSE | 0.286000 ± 0.001000 | `PROTOCOL_GRAFITI_P12.md`, project lead addendum, Table 2 Physionet12 GraFITi |
| Our test MSE | 0.302702 | `artifacts/p12_seed0.json` `/test/MSE` |
| Best validation MSE | 0.298854 | same JSON `/validation/MSE` |
| Best epoch | 84 | same JSON `/best_epoch` |
| Epochs run / limit | 114 / 200 | same JSON `len(/training_history)` / `/config/epochs`; host log epoch lines agree |
| Parameters | 44744 | same JSON `/n_params` |
| Seed / device | 0 / cuda | same JSON `/config/seed`, `/config/device` |
| Parsed / nonempty / row-empty excluded | 12000 / 11981 / 19 | same JSON `/parsed_patients`, sums of `/split_record_ids` lengths and their difference |
| Train / validation / test records | 8146 / 2037 / 1798 | same JSON `/split_record_ids/{train,val,test}` lengths |
| Observed test target cells | 35725 | same JSON `/test/n_observed_targets` |
| Corpus time maximum | 47.000000 | same JSON `/normalization/time_max` |

**Protocol differences and qualifications.** The register chooses original released-code behavior where it conflicts with the paper. Its documented candidate reasons for a score gap are the split/fold discrepancy, Adam versus AdamW, preserved hourly-reader defects, inherited adapter/scalar-width qualifications, single fixed seed/different initialization order, and per-example versus pooled loss. None is isolated as the cause by this run. The earlier missing-set-C blocker is resolved by the three actual archive records in `/source_archives`; the original build-status prose is historical. Every setting row from the protocol is retained below, with an explicit classification.

| Setting | Classification / actual-run qualification | Registered evidence | Executable choice |
| --- | --- | --- | --- |
| Corpus | **historical blocker resolved**. Host JSON supplies all three A/B/C archives and parses the full corpus; earlier missing-C build status is superseded. | P Table 1: 12,000 records, 37 channels; Q concatenates A/B/C | All three raw source sets are required for `--run`, with 12,000 unique records before removal of row-empty records. Only A/B exist locally; **full attempt is data-blocked**. |
| Existing project cohort | **project protocol difference**. The project 16-variable A/B cohort was not substituted for native P12. | H: 8,000 A/B records, 16 merged/renamed channels | Do not reuse that NPZ for this numerical comparison. Reparse native 37 variables from raw archives. |
| Features/order | **released-code alignment**. Native 37-channel order retained. | D dictionaries | `pH, PaCO2, PaO2, FiO2, MechVent, DiasABP, HR, MAP, SysABP, Temp, GCS, Urine, Weight, HCT, BUN, Creatinine, Glucose, HCO3, Mg, Platelets, K, Na, WBC, NIDiasABP, NIMAP, NISysABP, RespRate, ALP, ALT, AST, Bilirubin, SaO2, Lactate, Albumin, TroponinT, Cholesterol, TroponinI`. No pressure merging or SaO2 alias. |
| Static data/outcomes | **released-code alignment**. Admission descriptors/outcomes are excluded; later Weight remains a channel. | P §6.5 metadata limitation; D reader | Admission descriptors, RecordID and outcome labels are not model channels. Weight at 00:00 is metadata; later Weight is a time series. No outcome file is read. |
| Hourly aggregation | **released-code compatibility defect**. Preserves dropped boundary-triggering measurements and unflushed final hour. The register does not establish that the paper intended these defects. | P §6.1 hourly; D reader floors timestamps and averages | **Released-reader compatibility:** the boundary-triggering first measurement of each new hour is discarded, and the final hour is not flushed. These are visible code defects, preserved and tested for comparability, not asserted paper intentions. Times 0 through 48 are supported. |
| Raw missing values | **released-code compatibility**. No extra clinical clipping or raw -1 removal beyond the registered reader behavior. | D reader | No additional clinical clipping or raw `-1` removal beyond the released-reader behavior. Missing channels have no observation edge; normalization subsequently rejects nonfinite / out-of-range normalized entries. |
| Empty records / channels | **released-code alignment with actual exclusion**. Row-empty records are removed before splitting; the actual split counts are recorded below. | Q IDs derive from stored dataframe rows; Q drops all-NaN columns | Records without emitted rows disappear before splitting. Full run requires all 37 expected channels to have observations; it fails rather than silently changing input width. Smoke may have empty channels, represented as absent. |
| Normalization | **released-code alignment; project difference**. Full A/B/C normalization includes held-out data, unlike frozen CinC A-train normalization. | Q explicitly fits full A/B/C before splits, including test; E population standard deviation + `1e-7` | Feature means and population standard deviations over all observed hours/patients, then z-score. This is the historical code protocol; it differs from our frozen A-train normalization. No train-only normalization is silently substituted. |
| Outliers | **released-code alignment**. Strict normalized outlier exclusion retained. | Q 204–207 | After normalization retain only strict `-5 < z < 5`; rejected entries become absent, not boundary-clipped. |
| Time normalization | **released-code alignment**. The actual corpus maximum is recorded by the run JSON. | Q/E min-max time scaling | Explicit actual hour divided by maximum emitted corpus hour. Corpus minimum is 0 for the available records; the smoke maximum is 47. Grid positions without edges are padding and never observations. |
| Observation window | **paper/code boundary qualification**. The executable includes the boundary hour rather than using a half-open observation interval. | P §6.4: first 36 h; R `-ct 36`; Q `t <= observation_time` | Include emitted hours **0 through 36**, i.e. up to 37 hourly grid positions. Preserve code's inclusive boundary rather than replacing it with `[0,36)`. |
| Forecast window | **recorded-row qualification**. Targets are the next stored hourly rows, which can skip empty clock hours. | P Table 2 next 3 steps; R `-ft 0`; Q default 3 | Next three **stored hourly rows** with `t > 36`. They may skip empty clock hours; actual per-patient target times enter the model. Missing/padded target slots carry no query edges. |
| Query set | **published retrospective query; project difference**. Observed future masks request edges, without exposing their values; CinC instead requests the complete grid. | C / Q future observation masks | Only observed future labels determine the requested edge set; their **values never enter graph construction**. This is the published retrospective query protocol, distinct from the project CinC complete-grid request. |
| Paper split claim | **paper/code discrepancy**. The paper split/CV statement is retained without reconciliation with code fractions. | P §6.3: five-fold CV, 20% holdout validation, 10% unseen evaluation | Preserved as a paper claim; not silently reconciled with code fractions. |
| Executed split | **paper/code discrepancy**. Uses deterministic released-code fractions rather than the prose split statement. | Q `RANDOM_STATE=0`, test `.15`, validation `.2` of remaining `.85` | NumPy implementation of two `train_test_split(..., random_state=0)` permutations: approximately **68/17/15%**. At N=12,000: 8,160 / 2,040 / 1,800 before row-empty exclusions. Test/validation sizes use `ceil`. |
| Fold | **deviation from paper CV claim**. One fold-0 run; local code constructs identical deterministic splits, not independent folds. | R `--fold 0`; Q constructs five identical deterministic splits | One fold-0 split, not five independent folds. Repeating folds would not create independent splits in this code snapshot. Saved record IDs make the actual partition reviewable. |
| Model seed | **task choice and initialization qualification**. One fixed seed; upstream default was unset and initialization order differs. No search or sweep. | Task: one seed; original T CLI seed defaults to unset | Fix seed 0, no hyperparameter search or seed sweep. This is a task choice. Model initialization order differs from upstream; identical numeric seeds do not imply identical weights. |
| Width / heads / layers | **original released-command alignment**. Registered architecture retained; larger parameter count follows native P12 input width. | N and R original P12 command: 64 / 4 / 2; P ranges contain tuple | Reuse v3 with 37 inputs, width 64, 4 heads, 2 graph layers. This yields **44,744 parameters**, versus 43,400 for the 16-input CinC adapter. |
| Architecture completion | **inherited adapter qualification**. Retains the scalar-width completion, LeakyReLU, conventional MHA, dense masked storage and direct scalar query-edge output; no upstream-model identity claim. | F G02/G05/G10 | Retain v3's affine node/edge transition before final scalar graph layer, LeakyReLU(0.1), conventional MHA, dense masked storage and direct scalar query-edge output. These inherited qualifications remain; this is our adapter, not an upstream-model identity claim. |
| Loss | **paper/code and project differences**. Released-code pooled observed-cell MSE differs from paper per-example risk and the CinC GraFITi example-weighted loss. | P §3 per-example query risk; T executable MSE pools observed entries | Use **pooled observed-cell MSE** for released-code comparison. This differs from v3 CinC's example-weighted training loss. |
| Evaluation/selection | **released-code alignment; numerical choice**. Validation MSE selects the restored checkpoint; accumulation uses float64. | P MSE; T 233–273, 283–294 | Sum observed-target squared errors across the split / sum observed targets; select minimum validation MSE, restore best checkpoint, report test MSE in normalized units. Also record RMSE/MAE as supplementary metrics, never compare their values to MSE. Float64 evaluation accumulation is a numerical implementation choice. |
| Optimizer | **paper/code discrepancy**. AdamW in released code is used although paper prose says Adam; registered optimizer defaults retained. | P §6.3 says Adam; T imports/instantiates AdamW | Choose **AdamW**, learning rate `.001`, weight decay `.001`, betas `(.9,.999)`, epsilon `1e-8` (PyTorch default). Weight decay/betas come from T CLI/config; paper does not name weight decay. No claim that P specifies AdamW. |
| Schedule | **released-code alignment**. Registered validation-based plateau schedule and defaults retained. | P halve after 10 nonimproving epochs; T scheduler | ReduceLROnPlateau, factor `.5`, patience `10`, min learning rate `1e-5`, default relative threshold `1e-4`, cooldown 0, epsilon `1e-8`. Scheduler follows validation MSE. |
| Epoch limit / stopping | **released-code alignment**. The actual run stops after the registered nonimprovement patience, below its maximum epoch budget. | P/R: up to 200, early-stop patience 30; T | At most 200 epochs, strict validation improvement (`min_delta=0`), stop at 30 nonimproving epochs. No extra gradient clipping (T has none). |
| Batches | **original released-command alignment**. Full-run train and inference batches follow the register; smoke-only batch changes do not apply. | R original P12 batch 128; T inference batch 64 | Train 128, shuffle, drop last; validation/test 64, deterministic order, retain last. Smoke uses train batch 8 and retains last so small data are used. |
| Runtime loader | **runtime implementation difference**. Worker count zero and no pinned-memory requirement differ from the original runtime settings. | T train workers 4 / pin memory; task CPU smoke | Worker count 0, no pinned-memory requirement, configurable torch threads. Dense padding preserves incident-edge semantics for finite values but changes work/memory. |
| Device/framework | **runtime qualification**. This host run used CUDA; the current analysis/recovery uses CPU. The GPU model is not recorded in the supplied run JSON. | P RTX-3090/PyTorch; N project environment | `--device cpu` or `cuda`; worker uses CPU only. Existing Python 3.10.12, NumPy 2.2.6, PyTorch 2.6.0+cu124. No dependency installations. Deterministic algorithms enabled; CUDA availability is checked if requested on host. |
| Outputs | **record-keeping qualification**. Exact command, inputs, clocks and checkpoint are present. Original target placeholder/false match flag predate the project lead target addendum and are not silently changed. | Task scope | Owned JSON, selected state dict, source hashes, exact command, UTC clocks, all split record IDs, fit statistics and actual normalization statistics. No write outside learned-graph experiment. |

Source for every row above: `PROTOCOL_GRAFITI_P12.md`, “Complete setting decisions”, matching setting name. Exact actual-run values have JSON pointers in the P12 table and `e5_summary.json/reproduction/ours`. The smoke settings described by the register were not applied to this full run.

**Ablation definitions and provenance.** Root mean squared error (RMSE) pools observed target cells across patients and the full forecast window before taking a square root. A-test is the frozen internal test split at hospital A; B is the external cohort. Each table averages per-seed pooled RMSEs, with sample standard deviation (SD; denominator n−1) over seeds 0–3. All calculations use unrounded values; continuous report metrics use six decimals. Mean squared error (MSE) and RMSE are distinct and are not interchanged in the P12 comparison.

The 24 replacement JSONs contain physiological/random/complete runs only. Eight learned runs come from the full-precision `cinc_grafiti_s{0..3}.json` and `cinc_tpatchgnn_s{0..3}.json` beside the supplied frozen `summary.txt` files. This avoids treating rounded summary numbers as exact. Their exact files, fields and SHA-256s are in the JSON source manifest. Each replacement row uses `/A_test/RMSE` and `/B_external/RMSE`; each learned row uses `/A_test/RMSE@12` and `/B_external/RMSE@12`.

| Model | Graph | A-test pooled RMSE, mean ± SD | B pooled RMSE, mean ± SD |
| --- | --- | ---: | ---: |
| GraFITi | learned | 0.748258 ± 0.000330 | 0.793230 ± 0.000109 |
| GraFITi | physiological | 0.748343 ± 0.000370 | 0.793364 ± 0.000221 |
| GraFITi | random | 0.748335 ± 0.000851 | 0.793261 ± 0.000505 |
| GraFITi | complete | 0.748237 ± 0.000334 | 0.793172 ± 0.000192 |
| t-PatchGNN | learned | 0.749155 ± 0.001628 | 0.793921 ± 0.000937 |
| t-PatchGNN | physiological | 0.751697 ± 0.002548 | 0.794491 ± 0.001193 |
| t-PatchGNN | random | 0.753693 ± 0.002437 | 0.795359 ± 0.001567 |
| t-PatchGNN | complete | 0.753775 ± 0.001894 | 0.795150 ± 0.000939 |

**Seed-paired differences versus learned.** Each difference is replacement minus learned, so a positive value favors learned. The two-sided 95% paired Student t confidence interval (CI) is mean(d) ± t(0.975,3) × SD(d)/√4; the critical value is 3.182446. Sign counts are negative / zero / positive. These intervals describe four recorded seed differences, are unadjusted for multiple comparisons, and are not patient-level intervals. Historical learned fits used CPU and historical float32 metric reduction; replacement fits used CUDA and float64 metric accumulation. There is no contemporaneous learned CUDA control, so seed pairing does not isolate a graph-only causal effect.

**A-test.**

| Model | Replacement | Mean difference | 95% paired t CI | − / 0 / + |
| --- | --- | ---: | --- | ---: |
| GraFITi | physiological | +0.000085 | [-0.000239, +0.000409] | 1 / 0 / 3 |
| GraFITi | random | +0.000077 | [-0.001030, +0.001184] | 2 / 0 / 2 |
| GraFITi | complete | -0.000021 | [-0.000335, +0.000293] | 2 / 0 / 2 |
| t-PatchGNN | physiological | +0.002542 | [+0.000606, +0.004477] | 0 / 0 / 4 |
| t-PatchGNN | random | +0.004538 | [+0.002543, +0.006532] | 0 / 0 / 4 |
| t-PatchGNN | complete | +0.004620 | [+0.003478, +0.005761] | 0 / 0 / 4 |

**external B.**

| Model | Replacement | Mean difference | 95% paired t CI | − / 0 / + |
| --- | --- | ---: | --- | ---: |
| GraFITi | physiological | +0.000134 | [-0.000078, +0.000346] | 0 / 0 / 4 |
| GraFITi | random | +0.000031 | [-0.000635, +0.000697] | 2 / 0 / 2 |
| GraFITi | complete | -0.000058 | [-0.000319, +0.000202] | 3 / 0 / 1 |
| t-PatchGNN | physiological | +0.000571 | [-0.000661, +0.001802] | 1 / 0 / 3 |
| t-PatchGNN | random | +0.001438 | [+0.000050, +0.002826] | 0 / 0 / 4 |
| t-PatchGNN | complete | +0.001229 | [+0.000244, +0.002214] | 0 / 0 / 4 |

**All 24 replacement rows.** Paths are relative to `artifacts/e5/`; source fields are `/A_test/RMSE`, `/B_external/RMSE`, `/best_epoch`, and `len(/training_history)`. Every row and source hash is also present in `e5_summary.json/ablation/replacement_rows`.

| Model | Graph | Seed | A-test RMSE | B RMSE | Best epoch | Epochs run | Source JSON |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| GraFITi | physiological | 0 | 0.748684 | 0.793247 | 27 | 35 | `grafiti_physiological_s0.json` |
| GraFITi | physiological | 1 | 0.748630 | 0.793164 | 33 | 35 | `grafiti_physiological_s1.json` |
| GraFITi | physiological | 2 | 0.748112 | 0.793668 | 31 | 35 | `grafiti_physiological_s2.json` |
| GraFITi | physiological | 3 | 0.747945 | 0.793376 | 31 | 35 | `grafiti_physiological_s3.json` |
| GraFITi | random | 0 | 0.749201 | 0.792830 | 30 | 35 | `grafiti_random_s0.json` |
| GraFITi | random | 1 | 0.748917 | 0.792941 | 32 | 35 | `grafiti_random_s1.json` |
| GraFITi | random | 2 | 0.747474 | 0.793949 | 27 | 35 | `grafiti_random_s2.json` |
| GraFITi | random | 3 | 0.747747 | 0.793323 | 31 | 35 | `grafiti_random_s3.json` |
| GraFITi | complete | 0 | 0.748088 | 0.792923 | 31 | 35 | `grafiti_complete_s0.json` |
| GraFITi | complete | 1 | 0.748689 | 0.793271 | 29 | 35 | `grafiti_complete_s1.json` |
| GraFITi | complete | 2 | 0.748260 | 0.793363 | 29 | 35 | `grafiti_complete_s2.json` |
| GraFITi | complete | 3 | 0.747910 | 0.793129 | 31 | 35 | `grafiti_complete_s3.json` |
| t-PatchGNN | physiological | 0 | 0.755103 | 0.795825 | 28 | 35 | `tpatchgnn_physiological_s0.json` |
| t-PatchGNN | physiological | 1 | 0.749606 | 0.793161 | 34 | 35 | `tpatchgnn_physiological_s1.json` |
| t-PatchGNN | physiological | 2 | 0.749891 | 0.793890 | 33 | 35 | `tpatchgnn_physiological_s2.json` |
| t-PatchGNN | physiological | 3 | 0.752188 | 0.795090 | 31 | 35 | `tpatchgnn_physiological_s3.json` |
| t-PatchGNN | random | 0 | 0.756890 | 0.797332 | 30 | 35 | `tpatchgnn_random_s0.json` |
| t-PatchGNN | random | 1 | 0.751124 | 0.793593 | 34 | 35 | `tpatchgnn_random_s1.json` |
| t-PatchGNN | random | 2 | 0.752746 | 0.794847 | 33 | 35 | `tpatchgnn_random_s2.json` |
| t-PatchGNN | random | 3 | 0.754012 | 0.795663 | 34 | 35 | `tpatchgnn_random_s3.json` |
| t-PatchGNN | complete | 0 | 0.756246 | 0.796438 | 34 | 35 | `tpatchgnn_complete_s0.json` |
| t-PatchGNN | complete | 1 | 0.751975 | 0.794361 | 34 | 35 | `tpatchgnn_complete_s1.json` |
| t-PatchGNN | complete | 2 | 0.752670 | 0.794556 | 32 | 35 | `tpatchgnn_complete_s2.json` |
| t-PatchGNN | complete | 3 | 0.754209 | 0.795245 | 33 | 35 | `tpatchgnn_complete_s3.json` |

**Learned seed rows used for pairing.** Exact sources are the frozen baseline directories named above, with `/config/seed` and the `/RMSE@12` fields specified above.

| Model | Seed | A-test RMSE | B RMSE | Source JSON |
| --- | ---: | ---: | ---: | --- |
| GraFITi | 0 | 0.748383 | 0.793206 | `cinc_grafiti_s0.json` |
| GraFITi | 1 | 0.748560 | 0.793162 | `cinc_grafiti_s1.json` |
| GraFITi | 2 | 0.748297 | 0.793390 | `cinc_grafiti_s2.json` |
| GraFITi | 3 | 0.747791 | 0.793162 | `cinc_grafiti_s3.json` |
| t-PatchGNN | 0 | 0.750742 | 0.795018 | `cinc_tpatchgnn_s0.json` |
| t-PatchGNN | 1 | 0.747670 | 0.792812 | `cinc_tpatchgnn_s1.json` |
| t-PatchGNN | 2 | 0.747835 | 0.794245 | `cinc_tpatchgnn_s2.json` |
| t-PatchGNN | 3 | 0.750375 | 0.793607 | `cinc_tpatchgnn_s3.json` |

**Per-organ RMSE, mean ± sample SD.** Learned per-organ values are read from each frozen JSON’s `/{A_test,B_external}/RMSE_{organ}`. Replacement JSONs and host logs omit these fields, so replacement per-organ values below were recovered by CPU inference from the saved best state dictionaries, with hashes verified against `/checkpoint/sha256` and the frozen input hash verified against every run’s `/input/sha256`. This is evaluation only: no fitting, checkpoint selection or training was repeated. The recovered squared-error sums, observed-cell counts, individual seed metrics and original-versus-recovered pooled checks are embedded in `e5_summary.json/per_organ_recovery`; exact source pointers for each aggregate are under `/ablation/arms`. Historical learned values retain their original float32 reduction; recovered values use float64 accumulation.

| Model | Graph | Cohort | Cardiovascular | Pulmonary | Renal | Metabolic |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| GraFITi | learned | A-test | 0.700551 ± 0.000374 | 0.818990 ± 0.001511 | 0.695615 ± 0.001463 | 0.766782 ± 0.003002 |
| GraFITi | learned | B | 0.781953 ± 0.000199 | 0.813082 ± 0.000803 | 0.905257 ± 0.001376 | 0.771788 ± 0.001167 |
| GraFITi | physiological | A-test | 0.700565 ± 0.000348 | 0.819091 ± 0.001871 | 0.695468 ± 0.001591 | 0.767219 ± 0.003881 |
| GraFITi | physiological | B | 0.781995 ± 0.000258 | 0.813283 ± 0.000817 | 0.905944 ± 0.000978 | 0.772088 ± 0.001556 |
| GraFITi | random | A-test | 0.700574 ± 0.000384 | 0.818909 ± 0.003186 | 0.695973 ± 0.001770 | 0.767551 ± 0.003862 |
| GraFITi | random | B | 0.782043 ± 0.000651 | 0.812933 ± 0.001005 | 0.905402 ± 0.001224 | 0.771965 ± 0.001345 |
| GraFITi | complete | A-test | 0.700521 ± 0.000321 | 0.818761 ± 0.001504 | 0.695803 ± 0.001555 | 0.767441 ± 0.003641 |
| GraFITi | complete | B | 0.781817 ± 0.000318 | 0.813202 ± 0.000860 | 0.905057 ± 0.001263 | 0.771698 ± 0.000962 |
| t-PatchGNN | learned | A-test | 0.697524 ± 0.000985 | 0.822613 ± 0.005363 | 0.701802 ± 0.006398 | 0.775007 ± 0.005031 |
| t-PatchGNN | learned | B | 0.780121 ± 0.000743 | 0.816545 ± 0.001651 | 0.917936 ± 0.007989 | 0.775342 ± 0.002320 |
| t-PatchGNN | physiological | A-test | 0.697486 ± 0.000974 | 0.825731 ± 0.005143 | 0.711186 ± 0.002404 | 0.785398 ± 0.003421 |
| t-PatchGNN | physiological | B | 0.779539 ± 0.000632 | 0.819138 ± 0.000798 | 0.921609 ± 0.003102 | 0.775685 ± 0.007013 |
| t-PatchGNN | random | A-test | 0.698248 ± 0.000734 | 0.830107 ± 0.004953 | 0.713486 ± 0.006359 | 0.784970 ± 0.004803 |
| t-PatchGNN | random | B | 0.780251 ± 0.000883 | 0.820394 ± 0.001509 | 0.919097 ± 0.003880 | 0.777282 ± 0.007473 |
| t-PatchGNN | complete | A-test | 0.698272 ± 0.000607 | 0.829576 ± 0.004198 | 0.714766 ± 0.003889 | 0.787015 ± 0.002979 |
| t-PatchGNN | complete | B | 0.780148 ± 0.000440 | 0.819942 ± 0.001210 | 0.922063 ± 0.004348 | 0.776263 ± 0.007103 |

For all 48 recovered run/cohort evaluations, observed organ counts sum to the recorded pooled counts and organ squared-error sums reconstruct pooled squared error. Recovered pooled RMSE agrees with the recorded host value within half a unit in the sixth decimal place; the actual maximum discrepancy is retained at full precision in `/validation/maximum_absolute_cpu_minus_recorded_RMSE` (it rounds to 0.000000). This check supports six-decimal pooled consistency across inference devices, while it does not remove the original training-device difference.

**Reading.** On CinC-2019, learned cross-variable weighting has no clear pooled advantage for GraFITi under this declared incidence ablation: physiological minus learned RMSE is +0.000085 on A-test and +0.000134 on external B; every GraFITi replacement interval includes zero. For t-PatchGNN, all replacement graphs raise A-test RMSE: physiological +0.002542, random +0.004538, complete +0.004620, with each A-test interval above zero. External B changes are smaller: physiological +0.000571 (interval includes zero), random +0.001438 and complete +0.001229 (unadjusted intervals above zero). The physiological prior therefore retains more of the t-PatchGNN A-test performance than the other fixed alternatives by their recorded means, but it does not improve either model over its learned baseline by mean pooled RMSE. Inside t-PatchGNN it supplies fixed row-normalized receiver/source propagation weights in place of the adaptive adjacency at every block, while graph-learning embeddings, gates and dynamic projections are bypassed/frozen and the remaining network trains. Inside GraFITi it supplies fixed cross-variable messages to a separate time state for each receiving variable, retaining learned temporal attention; this changes the shared-time representation and is not a swap of a native variable-adjacency tensor. These are associations within the recorded comparison: learned controls were fit on CPU and replacements on CUDA, with differing metric accumulation; the seed-paired intervals do not isolate a device-free causal graph effect or establish equivalence.

The physiological/random supports each retain 197 directed variable pairs, including self loops, out of 256 possible; complete retains all 256. Random support matches each receiver’s physiological incoming degree. Source: both models’ `physiological_s0.json /graph/support`, random run supports, and `ABLATION_DESIGN.md` “Fixed graphs”. For t-PatchGNN the total/trainable parameter counts are 357682/355912; for GraFITi they are 43400/43400 (`/n_params`, `/n_trainable_params`). GraFITi’s learned temporal maps remain, including the inherited qualification that final node states are not read by the edge-only forecast. Thus these fixed arms do not turn either model into an untrained physiological predictor.

All numeric inputs and outputs, source fields, formulas, protocol rows, recovery evidence and hashes are in `e5_summary.json`. Commands, exit codes and UTC timing are in `DISTRIBUTION_NOTE.md`.
