# learned-graph experiment — GraFITi PhysioNet-2012 protocol and host reproduction attempt

Prepared 2026-11-05 by research tooling, assigned research engineer/implementation author;
research tooling is the task project lead. This is an executable protocol package and
author verification, not an independent fidelity approval or a published-score
reproduction result. No full experiment was run in the worker sandbox.

## Which experiment this package implements

The original GraFITi paper's main PhysioNet-2012 experiment is **37 time-series
channels, 36 hours of observation, next three recorded hourly steps**, with MSE
on standardized values (PDF pp. 5–6, Table 1, Table 2, §§6.1, 6.3, 6.4). It is
different from the later Zhang/t-PatchGNN protocol (24/24 and 41 variables),
which the local GraFITi README explicitly labels as an extension. The task did
not authorize silently switching between their scores.

**Published number to match: to be read from the paper by the project lead.**

The supplied learned-baseline LINEAGE and `research/G1_references_v4.md` do not
record a published PhysioNet-2012 numerical target. LINEAGE records our CinC-2019
RMSEs, and G1 records bibliographic metadata. The placeholder above follows the
registered scope for this case. The local PDF's Table 2 is the
identified source for the project lead to read and record; this package does not
invent a target, matching tolerance, or success verdict. A one-seed attempt also
cannot reproduce an aggregate mean and standard deviation by itself.

The paper and the locally recorded released code disagree on some settings.
This runner chooses the **original released-code protocol** for those settings,
and names every disagreement below. It does not claim that the paper prose and
the code are identical. The task's existing records omit raw P12 parsing, exact
split fractions and normalization; the locally available code supplies those
details without network access or installing/importing its dependencies.

## Source register

All paths below are read-only inputs under ``.
Hashes of the operative inputs are in `INPUT_PROVENANCE.json`.

| ID | Source and relevant location |
| --- | --- |
| P | `collaboration/evidence/papers/grafiti_arxiv2305.12932.pdf`, arXiv v2, SHA-256 `2f4c84afcc39602fb3150116c37b14e9033b393e71c007ef9d885d6f5ec541a9`; pp. 4–7 |
| L | `results/learned_graph_baselines_v1/LINEAGE.md`, GraFITi v3 paragraph and historical_experiment verification record |
| G | `research/G1_references_v4.md`, item 1 (bibliography, no benchmark number) |
| N | `historical_sources/learned-graph-baseline-build/PORT_NOTES.md`, GraFITi decisions 1–8, original README 64/4/2 setting and upstream exposure |
| F | `baselines/FIDELITY_NOTE.md`, G01–G11 continuity and declared LeakyReLU/scalar transition |
| V | `baselines/grafiti_adapter_v3.py`, reused adapter; `port_utils_v3.py` supplies context masking/softmax |
| R | `repos/GraFITi/README.md`, original Training and Evaluation command for `physionet2012`; later extension is separate |
| T | `repos/GraFITi/train_grafiti.py`, CLI lines 22–43; optimizer config 73–77; loaders 123–143; MSE 146–148; model 172–178; optimizer/scheduler 206–211; training/selection 216–298 |
| D | `repos/GraFITi/tsdm/datasets/physionet2012.py`, 37-channel dictionaries at 178–189 and raw reader 195–281 |
| Q | `repos/GraFITi/tsdm/tasks/physionet2012.py`, `TaskDataset.__getitem__` 88–103; defaults 158–180; normalization/filter 183–208; folds 210–233 |
| E | `repos/GraFITi/tsdm/encoders/numerical.py`, `Standardizer.fit` 111–133 and `MinMaxScaler.fit` |
| C | `repos/GraFITi/grafiti/grafiti.py`, `tsdm_collate` 42–111; requested edges use observed future mask |
| H | `results/cinc2012_cohort_v1/LINEAGE.md` and `cinc2012_cohort_preprocessor.py`; 16-variable project cohort, intentionally not substituted for P12 |

The recorded GraFITi checkout identifier in N is
`698060bb0e9385d79eaf41b7981a05390725a1e5`. No git command was used to re-establish
that identifier. Exact local source bytes are pinned by this package's hashes.
The local dataset/task/train/collator files and README were read for protocol
behavior; upstream model code was not imported or executed. The inherited
adapter's earlier authorship/exposure history remains N/F, not a clean-room
claim. The parser and wrapper in this package are newly written.

## Complete setting decisions

| Setting | Paper / recorded evidence | Executable choice and status |
| --- | --- | --- |
| Corpus | P Table 1: 12,000 records, 37 channels; Q concatenates A/B/C | All three raw source sets are required for `--run`, with 12,000 unique records before removal of row-empty records. Only A/B exist locally; **full attempt is data-blocked**. |
| Existing project cohort | H: 8,000 A/B records, 16 merged/renamed channels | Do not reuse that NPZ for this numerical comparison. Reparse native 37 variables from raw archives. |
| Features/order | D dictionaries | `pH, PaCO2, PaO2, FiO2, MechVent, DiasABP, HR, MAP, SysABP, Temp, GCS, Urine, Weight, HCT, BUN, Creatinine, Glucose, HCO3, Mg, Platelets, K, Na, WBC, NIDiasABP, NIMAP, NISysABP, RespRate, ALP, ALT, AST, Bilirubin, SaO2, Lactate, Albumin, TroponinT, Cholesterol, TroponinI`. No pressure merging or SaO2 alias. |
| Static data/outcomes | P §6.5 metadata limitation; D reader | Admission descriptors, RecordID and outcome labels are not model channels. Weight at 00:00 is metadata; later Weight is a time series. No outcome file is read. |
| Hourly aggregation | P §6.1 hourly; D reader floors timestamps and averages | **Released-reader compatibility:** the boundary-triggering first measurement of each new hour is discarded, and the final hour is not flushed. These are visible code defects, preserved and tested for comparability, not asserted paper intentions. Times 0 through 48 are supported. |
| Raw missing values | D reader | No additional clinical clipping or raw `-1` removal beyond the released-reader behavior. Missing channels have no observation edge; normalization subsequently rejects nonfinite / out-of-range normalized entries. |
| Empty records / channels | Q IDs derive from stored dataframe rows; Q drops all-NaN columns | Records without emitted rows disappear before splitting. Full run requires all 37 expected channels to have observations; it fails rather than silently changing input width. Smoke may have empty channels, represented as absent. |
| Normalization | Q explicitly fits full A/B/C before splits, including test; E population standard deviation + `1e-7` | Feature means and population standard deviations over all observed hours/patients, then z-score. This is the historical code protocol; it differs from our frozen A-train normalization. No train-only normalization is silently substituted. |
| Outliers | Q 204–207 | After normalization retain only strict `-5 < z < 5`; rejected entries become absent, not boundary-clipped. |
| Time normalization | Q/E min-max time scaling | Explicit actual hour divided by maximum emitted corpus hour. Corpus minimum is 0 for the available records; the smoke maximum is 47. Grid positions without edges are padding and never observations. |
| Observation window | P §6.4: first 36 h; R `-ct 36`; Q `t <= observation_time` | Include emitted hours **0 through 36**, i.e. up to 37 hourly grid positions. Preserve code's inclusive boundary rather than replacing it with `[0,36)`. |
| Forecast window | P Table 2 next 3 steps; R `-ft 0`; Q default 3 | Next three **stored hourly rows** with `t > 36`. They may skip empty clock hours; actual per-patient target times enter the model. Missing/padded target slots carry no query edges. |
| Query set | C / Q future observation masks | Only observed future labels determine the requested edge set; their **values never enter graph construction**. This is the published retrospective query protocol, distinct from the project CinC complete-grid request. |
| Paper split claim | P §6.3: five-fold CV, 20% holdout validation, 10% unseen evaluation | Preserved as a paper claim; not silently reconciled with code fractions. |
| Executed split | Q `RANDOM_STATE=0`, test `.15`, validation `.2` of remaining `.85` | NumPy implementation of two `train_test_split(..., random_state=0)` permutations: approximately **68/17/15%**. At N=12,000: 8,160 / 2,040 / 1,800 before row-empty exclusions. Test/validation sizes use `ceil`. |
| Fold | R `--fold 0`; Q constructs five identical deterministic splits | One fold-0 split, not five independent folds. Repeating folds would not create independent splits in this code snapshot. Saved record IDs make the actual partition reviewable. |
| Model seed | Task: one seed; original T CLI seed defaults to unset | Fix seed 0, no hyperparameter search or seed sweep. This is a task choice. Model initialization order differs from upstream; identical numeric seeds do not imply identical weights. |
| Width / heads / layers | N and R original P12 command: 64 / 4 / 2; P ranges contain tuple | Reuse v3 with 37 inputs, width 64, 4 heads, 2 graph layers. This yields **44,744 parameters**, versus 43,400 for the 16-input CinC adapter. |
| Architecture completion | F G02/G05/G10 | Retain v3's affine node/edge transition before final scalar graph layer, LeakyReLU(0.1), conventional MHA, dense masked storage and direct scalar query-edge output. These inherited qualifications remain; this is our adapter, not an upstream-model identity claim. |
| Loss | P §3 per-example query risk; T executable MSE pools observed entries | Use **pooled observed-cell MSE** for released-code comparison. This differs from v3 CinC's example-weighted training loss. |
| Evaluation/selection | P MSE; T 233–273, 283–294 | Sum observed-target squared errors across the split / sum observed targets; select minimum validation MSE, restore best checkpoint, report test MSE in normalized units. Also record RMSE/MAE as supplementary metrics, never compare their values to MSE. Float64 evaluation accumulation is a numerical implementation choice. |
| Optimizer | P §6.3 says Adam; T imports/instantiates AdamW | Choose **AdamW**, learning rate `.001`, weight decay `.001`, betas `(.9,.999)`, epsilon `1e-8` (PyTorch default). Weight decay/betas come from T CLI/config; paper does not name weight decay. No claim that P specifies AdamW. |
| Schedule | P halve after 10 nonimproving epochs; T scheduler | ReduceLROnPlateau, factor `.5`, patience `10`, min learning rate `1e-5`, default relative threshold `1e-4`, cooldown 0, epsilon `1e-8`. Scheduler follows validation MSE. |
| Epoch limit / stopping | P/R: up to 200, early-stop patience 30; T | At most 200 epochs, strict validation improvement (`min_delta=0`), stop at 30 nonimproving epochs. No extra gradient clipping (T has none). |
| Batches | R original P12 batch 128; T inference batch 64 | Train 128, shuffle, drop last; validation/test 64, deterministic order, retain last. Smoke uses train batch 8 and retains last so small data are used. |
| Runtime loader | T train workers 4 / pin memory; task CPU smoke | Worker count 0, no pinned-memory requirement, configurable torch threads. Dense padding preserves incident-edge semantics for finite values but changes work/memory. |
| Device/framework | P RTX-3090/PyTorch; N project environment | `--device cpu` or `cuda`; worker uses CPU only. Existing Python 3.10.12, NumPy 2.2.6, PyTorch 2.6.0+cu124. No dependency installations. Deterministic algorithms enabled; CUDA availability is checked if requested on host. |
| Outputs | Task scope | Owned JSON, selected state dict, source hashes, exact command, UTC clocks, all split record IDs, fit statistics and actual normalization statistics. No write outside learned-graph experiment. |

## Host command and bounded smoke

Print the exact full host command and missing-input readiness (no training):

```bash
python3 -B grafiti_p12_reproduce.py --dry-run
```

The printed default command is ready to execute once the project lead supplies the
missing `data/cinc2012/set-c.zip`. `--archives A B C` also accepts local ZIP or tar
archives; no extraction or download occurs. To use CUDA, print again with
`--device cuda`. Execution requires explicit `--run` and all three sets.
`artifacts/p12_host_command.txt` contains the concrete CPU command.

The only real-data training performed for this package is:

```bash
python3 -B grafiti_p12_reproduce.py --smoke --seed 0 --device cpu --threads 2 --out artifacts/p12_smoke.json
```

This parses exactly 200 source patients: the first 100 sorted records in A and
first 100 in B. One has no emitted rows under released-reader compatibility, so
the actual nonempty train/validation/test counts are **135/34/30 (199)**. The
smoke retains the source protocol's exclusion instead of silently adding a 201st
patient. It fits normalization on those 199 records solely for a code-path
check; this is not the full benchmark normalization or score. It runs exactly
two epochs; its finite MSEs and command are in `DISTRIBUTION_NOTE.md` and the JSON/log.

## Interpretation and pending project lead work

The build is usable and the smoke is finite. A numerical reproduction claim
remains **BLOCKED** by the missing third source set and unrecorded target in
LINEAGE/G1. The paper/code split, optimizer and raw-reader discrepancies, plus
the inherited scalar-width completion, limit what a subsequent one-seed score
can establish. The project lead must record the paper's target, provide set C,
assess these scientific qualifications, and run the printed command on the
host. This worker did not obtain data, run a full fit, or independently review
its own changes.

## project lead addendum (2026-11-05T13:42:49Z) — published target read from the paper (G1)
Source: arXiv:2305.12932v2 (Yalavarthi et al., "Forecasting Irregularly Sampled Time Series using Graphs", benchmark 2024), PDF fetched 2026-11-05.
Table 2 (forecasting the next three time steps, metric MSE on normalised values; Physionet'12 column): **GraFITi 0.286 ± 0.001** (the same value
appears in Table 5 "GraFITi 0.286 ± 0.001" and Table 6 "GraFITi-MAB 0.286 ± 0.001"). The paper notes the Physionet'12 dataset "was not used by the
baseline models hence do not have published results" for the older baselines; Table 2 also lists DLinear+ 0.380 ± 0.001, NLinear+ 0.382 ± 0.001,
Informer+ 0.347 ± 0.001, FedFormer+ 0.455 ± 0.004 on Physionet'12. Longer-horizon table (observation/forecast hours): Physionet'12 24/12 0.365 ± 0.001,
24/24 0.401 ± 0.001, 36/6 0.319 ± 0.001, 36/12 0.347 ± 0.001 (GraFITi column). TARGET for the reproduction under this protocol register (36 h observation,
next three recorded steps): 0.286 ± 0.001.
