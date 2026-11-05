# Historical renal checkpoint diagnosis

This report records the checkpoint replay before the shared-input fits.
The completed fits and their subsequent interpretation are in
[SHARED_INPUT_READING.md](SHARED_INPUT_READING.md). Source-line numbers
describe the original implementation before portability headers were added;
the corresponding functions remain in the same source files.


## Decision evidence

Checkpoint replay reproduces the frozen pooled renal errors within the stated CPU tolerance. No renal-specific indexing or omitted-mask defect was found in the traced path. Input restriction and forecast-boundary handling are concrete mechanistic limitations; causal attribution awaits the eight full host controls.

A: 9,581/85,248 renal context entries observed (11.24%); 2,368 eligible stays, 1,604 with renal targets, 6,336 observed renal target entries.
B: 43,978/533,664 renal context entries observed (8.24%); 14,824 eligible stays, 8,100 with renal targets, 27,206 observed renal target entries.

For hospital B, the signed excess squared-error decomposition relative to persistence assigns the following fractions to stays with zero renal context entries (a negative fraction means that group offsets excess elsewhere):
- physiograph_gru: 1.46% of total signed excess SSE (+37.121); +0.001364 in overall MSE units.
- physiograph: -4.98% of total signed excess SSE (-470.460); -0.017293 in overall MSE units.

These fractions decompose squared error, not RMSE. They describe the evaluated stays and do not identify a causal effect of missingness. The hypothesis that stays with no observed renal context principally drive the excess is therefore unsupported: nearly all excess occurs in stays with at least one observed renal entry. This does not establish whether the models underuse those observations because of input partitioning, rollout handling, or optimization.

## Estimand and denominators

One deterministic window per stay: the first 12 context hours forecast the next 12 hours. A denotes A-test; B denotes the external hospital. Renal variables are Creatinine, BUN and Potassium (columns 8–10). Observed context entries count all ones across the 12×3 renal context mask; bins are 0, 1–3 and ≥4, chosen before replay. Every eligible stay appears in one bin, including stays with no renal targets.

RMSE@12 = sqrt(sum of squared normalized errors / observed renal target entries), pooled over stays, hours and the three variables within each bin. Units are A-train standard deviations. Predictions/error arithmetic and within-stay reduction use float32 as in clinical_protocol; sums across stays use float64. The table gives the mean and sample SD of four checkpoint-specific pooled RMSEs, not mean stay RMSE. Persistence is one deterministic calculation, not four independent seeds. Denominators are shared across seeds and models and are never multiplied by four. An empty target denominator is NA, never zero error.

## Stratified renal table

| Split | Model | Context entries | Seeds | Stays | Stays with renal targets | Stays without renal targets | Renal target entries | RMSE mean ± sample SD |
|---|---|---|---:|---:|---:|---:|---:|---:|
| A | persistence | all | 1 | 2368 | 1604 | 764 | 6336 | 0.762487 |
| A | persistence | 0 | 1 | 340 | 305 | 35 | 1096 | 0.894199 |
| A | persistence | 1–3 | 1 | 937 | 546 | 391 | 1874 | 0.743554 |
| A | persistence | ≥4 | 1 | 1091 | 753 | 338 | 3366 | 0.725404 |
| A | grud | all | 4 | 2368 | 1604 | 764 | 6336 | 0.694110 ± 0.002129 |
| A | grud | 0 | 4 | 340 | 305 | 35 | 1096 | 0.843983 ± 0.007661 |
| A | grud | 1–3 | 4 | 937 | 546 | 391 | 1874 | 0.669529 ± 0.003294 |
| A | grud | ≥4 | 4 | 1091 | 753 | 338 | 3366 | 0.652203 ± 0.003759 |
| A | physiograph_gru | all | 4 | 2368 | 1604 | 764 | 6336 | 0.813376 ± 0.040099 |
| A | physiograph_gru | 0 | 4 | 340 | 305 | 35 | 1096 | 0.877738 ± 0.003595 |
| A | physiograph_gru | 1–3 | 4 | 937 | 546 | 391 | 1874 | 0.773184 ± 0.035412 |
| A | physiograph_gru | ≥4 | 4 | 1091 | 753 | 338 | 3366 | 0.813045 ± 0.055867 |
| A | physiograph | all | 4 | 2368 | 1604 | 764 | 6336 | 0.939744 ± 0.003167 |
| A | physiograph | 0 | 4 | 340 | 305 | 35 | 1096 | 0.869094 ± 0.005034 |
| A | physiograph | 1–3 | 4 | 937 | 546 | 391 | 1874 | 0.904257 ± 0.003871 |
| A | physiograph | ≥4 | 4 | 1091 | 753 | 338 | 3366 | 0.980381 ± 0.004600 |
| B | persistence | all | 1 | 14824 | 8100 | 6724 | 27206 | 0.977049 |
| B | persistence | 0 | 1 | 3820 | 2588 | 1232 | 8281 | 1.159131 |
| B | persistence | 1–3 | 1 | 6860 | 3142 | 3718 | 9986 | 0.910908 |
| B | persistence | ≥4 | 1 | 4144 | 2370 | 1774 | 8939 | 0.856620 |
| B | grud | all | 4 | 14824 | 8100 | 6724 | 27206 | 0.909741 ± 0.003806 |
| B | grud | 0 | 4 | 3820 | 2588 | 1232 | 8281 | 1.152497 ± 0.005231 |
| B | grud | 1–3 | 4 | 6860 | 3142 | 3718 | 9986 | 0.797551 ± 0.003663 |
| B | grud | ≥4 | 4 | 4144 | 2370 | 1774 | 8939 | 0.760151 ± 0.003170 |
| B | physiograph_gru | all | 4 | 14824 | 8100 | 6724 | 27206 | 1.023438 ± 0.028037 |
| B | physiograph_gru | 0 | 4 | 3820 | 2588 | 1232 | 8281 | 1.160996 ± 0.014338 |
| B | physiograph_gru | 1–3 | 4 | 6860 | 3142 | 3718 | 9986 | 0.970638 ± 0.057132 |
| B | physiograph_gru | ≥4 | 4 | 4144 | 2370 | 1774 | 8939 | 0.940302 ± 0.043576 |
| B | physiograph | all | 4 | 14824 | 8100 | 6724 | 27206 | 1.141036 ± 0.002391 |
| B | physiograph | 0 | 4 | 3820 | 2588 | 1232 | 8281 | 1.134359 ± 0.001409 |
| B | physiograph | 1–3 | 4 | 6860 | 3142 | 3718 | 9986 | 1.158960 ± 0.002932 |
| B | physiograph | ≥4 | 4 | 4144 | 2370 | 1774 | 8939 | 1.126933 ± 0.004437 |

## Renal deficit relative to frozen references

Differences below subtract the comparator's mean pooled RMSE from the model's mean pooled RMSE. References come from `selected_seed_summary` in `per_organ_v4.json`; CPU replay is verified against every individual seed.

| Split | Model | Renal RMSE | Minus persistence | Minus GRU-D |
|---|---|---:|---:|---:|
| A | physiograph_gru | 0.813376 | +0.050889 | +0.119266 |
| A | physiograph | 0.939744 | +0.177257 | +0.245634 |
| B | physiograph_gru | 1.023438 | +0.046388 | +0.113697 |
| B | physiograph | 1.141036 | +0.163987 | +0.231295 |

## Where the excess squared error occurs

SSE is the sum of squared errors. Model SSE is averaged over seeds before subtracting the comparator. The MSE contribution divides each bin's signed excess SSE by the **overall** renal target denominator; contributions add to the overall MSE difference. Fractions can be negative or exceed 100% when bins offset each other.

| Split | Model | Comparator | Context entries | Excess SSE | Contribution to overall MSE difference | Fraction of signed total excess |
|---|---|---|---|---:|---:|---:|
| A | physiograph_gru | persistence | 0 | -31.957 | -0.005044 | -6.20% |
| A | physiograph_gru | persistence | 1–3 | +85.982 | +0.013570 | +16.67% |
| A | physiograph_gru | persistence | ≥4 | +461.724 | +0.072873 | +89.52% |
| A | physiograph_gru | grud | 0 | +63.659 | +0.010047 | +5.55% |
| A | physiograph_gru | grud | 1–3 | +281.995 | +0.044507 | +24.59% |
| A | physiograph_gru | grud | ≥4 | +801.124 | +0.126440 | +69.86% |
| A | physiograph | persistence | 0 | -48.497 | -0.007654 | -2.54% |
| A | physiograph | persistence | 1–3 | +496.271 | +0.078326 | +25.96% |
| A | physiograph | persistence | ≥4 | +1464.053 | +0.231069 | +76.58% |
| A | physiograph | grud | 0 | +47.119 | +0.007437 | +1.85% |
| A | physiograph | grud | 1–3 | +692.284 | +0.109262 | +27.22% |
| A | physiograph | grud | ≥4 | +1803.452 | +0.284636 | +70.92% |
| B | physiograph_gru | persistence | 0 | +37.121 | +0.001364 | +1.46% |
| B | physiograph_gru | persistence | 1–3 | +1146.721 | +0.042150 | +45.13% |
| B | physiograph_gru | persistence | ≥4 | +1356.887 | +0.049875 | +53.41% |
| B | physiograph_gru | grud | 0 | +163.933 | +0.006026 | +2.73% |
| B | physiograph_gru | grud | 1–3 | +3080.556 | +0.113231 | +51.38% |
| B | physiograph_gru | grud | ≥4 | +2751.022 | +0.101118 | +45.88% |
| B | physiograph | persistence | 0 | -470.460 | -0.017293 | -4.98% |
| B | physiograph | persistence | 1–3 | +5127.226 | +0.188459 | +54.26% |
| B | physiograph | persistence | ≥4 | +4793.041 | +0.176176 | +50.72% |
| B | physiograph | grud | 0 | -343.648 | -0.012631 | -2.66% |
| B | physiograph | grud | 1–3 | +7061.061 | +0.259541 | +54.72% |
| B | physiograph | grud | ≥4 | +6187.176 | +0.227420 | +47.95% |

## Replay reconciliation

Maximum absolute difference from a frozen per-seed renal RMSE: 1.66e-08; required tolerance 1e-05. Checkpoint SHA256, recorded source hashes, model/seed identity, cohort SHA256 and every split's stay membership were checked. Per-stay replay errors are saved in `artifacts/diagnosis/`; full per-seed strata, feature summaries and provenance are in `renal_diagnosis.json`.

## Frozen code-path reading

All source paths are relative to the repository root. The source hashes
are checked before replay. These observations apply to the implementation being
evaluated, not to every possible organ-graph architecture.

- **Correct renal indexing and output width.** The CinC configuration is
  `(4, 4, 3, 5)` (`src/organ_graph_ssm_model.py:321–325`). Cumulative slices are
  built at `src/organ_graph_ssm_model.py:189–192`; the cohort identifies columns
  8–10 as Creatinine, BUN and Potassium. Input and output ordering agree.
- **Values and masks, with static information.** Normalization uses A-train mean
  and standard deviation and remasks missing values to zero
  (`src/physiograph_data_loader.py:25–41`). The context projection consumes
  `2*d + n_static + n_control` channels
  (`src/organ_graph_ssm_model.py:193–196`). Its renal width is 3 values + 3 masks +
  5 static features = 11; the learned projection maps this to `d_model`.
  `_organ_inputs` selects only that organ's values and masks and appends static
  features (`src/organ_graph_ssm_model.py:209–221`). Thus an empty renal context
  has zero renal values and masks, **but still has static features and learned
  projection biases**, and can receive messages. It is not an entirely zero node.
- **No explicit elapsed-time channel.** The loader returns values, masks, static
  data and targets (`src/physiograph_data_loader.py:33–44`); the organ model never
  constructs a time-since-last-observation variable. Recurrence can learn mask
  history, but this is not an explicit decay input. In contrast, GRU-D constructs
  `delta`, decays inputs/hidden states, and retains last observations inside its
  encoder (`src/clinical_timeseries_baselines.py:79–94`).
- **Cross-organ information is restricted to messages in the frozen model.**
  Separate organ encoders run before coupling
  (`src/organ_graph_ssm_model.py:223–242`). Gated source-to-target messages are
  added to each target's state (`src/organ_graph_ssm_model.py:168–182`); the
  admissible direct renal incoming edge is cardiovascular→renal
  (`src/organ_graph_ssm_model.py:31–40`). Indirect paths can act across layers or
  forecast steps. Output heads map each organ state only to its own variables
  (`src/organ_graph_ssm_model.py:203–206,274–277`), with no concatenated global
  hidden state or direct nonrenal input to the renal decoder.
- **Forecast boundary behavior is a plausible general limitation.** The initial
  feedback is the final context row, not the last observed value per variable
  (`src/organ_graph_ssm_model.py:249–251`). A missing final-hour renal value is
  consequently zero. The first forecast input marks all feedback entries as one
  (`src/organ_graph_ssm_model.py:260–265`), just as later predicted inputs are
  marked one. The encoded context still carries its true masks, but the forecast
  input does not distinguish this initial missing zero from an observed mean.
  This affects every organ and is not evidence of a renal indexing bug. Plain
  GRU and GRU-D also initialize their autoregressive decoder from the final
  remasked row (`src/clinical_timeseries_baselines.py:58–61,94`); persistence
  explicitly retains last observed values
  (`tools/v4_protocol.py:162–166`).
  Both control modes preserve
  this boundary rule rather than confounding input scope with an imputation fix.
- **Messages update outputs, not recurrent cells in place.** Stored context
  recurrent states precede coupling (`src/organ_graph_ssm_model.py:233–242`);
  rollout takes these states and re-applies messages at every future step
  (`src/organ_graph_ssm_model.py:249,266–273`). Lower-layer context messages can
  enter the next layer; the final coupled context output is not itself used as
  a recurrent state. This is shared architectural behavior, not a renal-only
  branch. It remains unchanged in the controls.

## Minimal host control and interpretation limits

`shared_input_variant.py` registers `physiograph_gru_factorised_partitioned` and
`physiograph_gru_factorised_shared`. Both have **no edges**, four organ heads and
the selected PhysioGraph-GRU configuration: learning rate 0.0005, `large`,
`d_model=96`, `d_state=48`, two layers, dropout 0.1. Context C=12, horizon K=12,
seeds 0–3. Each fit retains the clinical_protocol 35-epoch cap, patience 8, validation-selected
checkpoint, Adam/weight decay, cosine scheduler and gradient clipping. No mode is
retuned and no test score selects a configuration.

In partitioned mode the dynamic value widths are 4/4/3/5; in shared mode every
organ receives all 16 values and their 16 masks. The actual preprojection widths
including masks and static features are 13/13/11/15 versus 37/37/37/37; recurrent
cell inputs remain `d_model=96`. Both context and forecast-step inputs are widened.
There are no graph messages, but shared forecast feedback carries all organs'
previous predictions, so shared-input does not imply independent forecast
trajectories. Static inputs, output heads and all boundary/mask rules are kept.
The widened projections add parameters; this is a structural input-access
control, not a parameter-matched or elapsed-time control. Common recurrent/head
initial weights are identical for paired seeds, with fresh widened projections.

`bash diagnostics/renal_shared_input/run.sh --device cuda` enumerates the eight full fits. CPU tests are only
smoke evidence; **this report predates the eight full control fits**.
An improvement would support a role for access to cross-organ input, subject to
the changed projection capacity; it would not establish that partitioning is the
sole cause. A lack of improvement would leave optimization, rollout boundary
behavior and missingness representation as unresolved alternatives. The saved
admissible-edge runs and this no-edge control answer different comparisons.

CinC-2012's within-corpus table reports PhysioGraph-GRU 0.823867 ± 0.015241 and
SSM seeds near 0.82–0.83 and 0.89. Its renal standard deviations are much smaller
(GRU 0.001175, SSM 0.002474), while other organs vary more
(`results/clinical_v4_v1/cinc2012/TABLE_CINC2012.md`,
“Within” tables). This CinC-2019 replay does not diagnose or resolve the separate
CinC-2012 seed behavior; inferring a common renal mechanism would exceed the data.

