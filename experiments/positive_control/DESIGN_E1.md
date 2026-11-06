# E1: a delayed, partially observed positive control for prescribed edges

Design registered by research tooling, research engineer on positive control, on 2026-11-05, before
implementing E1 or inspecting any E1 oracle or neural result. research tooling is the
assigned project lead. This is an engineering design and pre-registration, not an
independent scientific review. Full neural runs require the PI's later decision.

## Question and scope

Can the matched graph protocol detect useful cardiovascular-to-renal and
cardiovascular-to-metabolic information when recent source history contains a
delayed driving signal that sparse, noisy target history cannot reconstruct?
This is a deliberately constructed synthetic positive control. It does not
calibrate clinical coupling strength or establish benefit on CinC-2019.

The existing generator, BASE_SIM/historical_experiment extensions, frozen arrays, H3 aggregate, and
claim C3 remain read-only. E1 is a wrapper: sample and integrate only the factual
cardiovascular jobs through the existing vectorized frozen equations, then add
the following explicitly synthetic circulatory modulation and target dynamics.
No old result or claim is replaced by the oracle check. The original C3 null
continues to describe the original regime.

## Grid, source process, and latent state

Retain the H3 six-hour grid with interval h = 5 minutes, context C = 12 samples
(minutes 0–55), and K = 24 forecast samples (minutes 60–175). Retain frozen
patient sampling, disease/treatment schedules, policy confounding c = 1, policy
noise standard deviation 0.03, dataset seed 0, RK4 step 0.5 seconds, and warm-up
180 seconds. Generate the base cardiovascular trajectories once at frozen
coupling 0; the cardiovascular equations do not depend on that coupling.
Counterfactual trajectories are not generated or scored in E1.

An upstream vasomotor process x has stationary standard deviation 1 and
correlation time 60 minutes. Its exact sampled Ornstein–Uhlenbeck update is

    a_x = exp(-h/60)
    x[0] ~ Normal(0, 1)
    x[t+1] = a_x*x[t] + sqrt(1-a_x^2)*epsilon[t], epsilon ~ Normal(0,1).

Add x times (12 mmHg, -3 beats/min, 0.6 L/min, 0.3 mmHg) to the frozen
(MAP, HR, CO, CVP) trajectories. MAP is mean arterial pressure, HR heart rate,
CO cardiac output, and CVP central venous pressure. These four channels are
densely observed. This additive stochastic stress process is a synthetic
extension; it is not asserted to preserve the frozen circulation's conservation
laws. It supplies recent, patient-specific source innovations during context,
including before the frozen disease and treatment onsets.

The dimensionless perfusion reserve r is a hidden low-pass state driven by the
cardiovascular state and prescribed vasopressor control u:

    d[t] = 0.60*(MAP[t]-85)/15 + 0.25*(CO[t]-5)/1.5
           - 0.15*(CVP[t]-8)/4 + 0.30*u[t]/0.30
    dr/ds = (d-r)/30 minutes
    r[0] ~ Normal(0, 0.25^2)
    r[t+1] = exp(-h/30)*r[t] + (1-exp(-h/30))*d[t].

The update uses the left endpoint only, so future source samples cannot affect
earlier states. Two independent, target-local Ornstein–Uhlenbeck processes z_U
and z_L have time constant 90 minutes and stationary standard deviations 0.08
mL/min and 0.15 mmol/L. Independent patient offsets b_U and b_L have standard
deviations 0.12 mL/min and 0.25 mmol/L. All these random streams are independent
of the frozen patients, source innovations, reserve initialization, and masks.

Urine output U and lactate L relax toward delayed reserve-dependent equilibria:

    U_eq[t] = 1.10 + b_U + z_U[t] + 0.45*kappa*r[t-6]
    L_eq[t] = 3.20 + b_L + z_L[t] - 1.00*kappa*r[t-9]
    dU/ds = (U_eq-U)/10 minutes
    dL/ds = (L_eq-L)/20 minutes.

Before time zero, delayed r is the initial r[0]. Initialize U and L to their
respective time-zero equilibria. Integrate each relaxation by the exact
left-endpoint exponential update on the five-minute grid. This introduces
30-minute renal and 45-minute metabolic transport delays, plus response times.
Bound the clean outputs to U in [0.05, 2.8] mL/min and L in [0.1, 10] mmol/L;
report the fraction clipped. These ranges are engineering bounds, not fitted
clinical distributions. kappa in {0, 0.5, 1} scales only the downstream reserve
effect. Source histories, independent organ dynamics, measurement noise, and
mask uniforms are paired across kappa. At kappa = 0, the target dynamics are
independent of the source and treatment by construction.

Neither r, x, offsets, disease severity, nor frozen sepsis is an input feature.
The six observed channels are exactly MAP, HR, CO, CVP, UO, Lac. Reserve affects
the targets but is not an observed renal/metabolic channel. Local inference may
still be possible probabilistically; E1 makes no claim of absolute statistical
non-identifiability. The held-out oracle tests whether source history actually
adds material prediction information under this observation model.

## Observation model and measured clinical rates

Add independent Gaussian measurement noise with standard deviations 0.08
mL/min to U and 0.15 mmol/L to L. The dense noisy array is the synthetic label
array. Context input values equal this array where observed and zero where
masked; the input mask is supplied separately. Missing values are re-masked to
zero after normalization, without forward fill or interpolation. The latent
state and dense labels are never assembled into context features.

Rates below were counted directly from data/cinc2019_cohort.npz before E1 was
implemented. The denominator is retained, non-padding hours, using each saved
length; the numerator is the corresponding mask sum. They are pooled-hour
fractions, not means of patient-specific rates. BUN is blood urea nitrogen.

| Cohort | Valid hours | Creatinine count (rate) | BUN count (rate) | Lactate count (rate) | Either renal lab rate |
|---|---:|---:|---:|---:|---:|
| A-train, 14,236 stays | 505,935 | 33,911 (0.06702640) | 41,639 (0.08230109) | 17,484 (0.03455780) | 0.08274778 |
| A-all, 20,336 stays | 722,051 | 48,320 (0.06692048) | 59,297 (0.08212301) | 25,199 (0.03489920) | 0.08253434 |
| B, 20,000 stays | 695,090 | 38,601 (0.05553382) | 38,567 (0.05548490) | 13,053 (0.01877886) | 0.05554101 |

Use A-train rates only to set E1: independent Bernoulli masks with p_U equal to
the union of creatinine/BUN masks (0.08274778) and p_L = 0.03455780. The union
is counted directly, not calculated under independence. UO is a synthetic
renal channel, not a claim about the observed clinical UO rate; the archive has
no UO feature. Lab missingness supplies a declared proxy for sparse renal
information. Cardiovascular observation probability is 1.

The primary experiment matches the *per-row* observation fractions while
retaining H3's five-minute grid. It therefore observes more frequently per
physical hour than the clinical archive. An additional, pre-specified oracle
sensitivity uses p_5min = 1-(1-p_hour)^(1/12), matching the probability of at
least one event over twelve independent five-minute bins to the hourly rate.
Neither Bernoulli model reproduces clinical clustered or informative sampling.

Dense noisy future labels and dense training-patient moments are available
only because this is a simulator. Both ridge and neural models train on these
dense labels and are evaluated against the dense labels. Input histories remain
masked. This preserves H3's full-target MSE objective and prevents differences
in available supervision from being mistaken for an edge effect. This is a
synthetic capability test, not an evaluation of learning from sparse clinical
labels. No masked input is filled from a dense label.

## Oracle check registered before neural work

For each target separately, fit a multi-output linear ridge predictor of the
entire K-step target block. The baseline receives only that target's C observed
values and masks, plus the common C context and K future treatment controls.
The augmented predictor receives the same inputs plus the four cardiovascular
channels' context values and masks. Both have an intercept and fixed ridge
penalty alpha = 10 on training-standardized features; no hyperparameter search,
validation selection, hidden states, future source values, or held-out moments.

Use 400 patients, dataset seed 0, split seed 0, and the exact H3 patient
permutation: first int(0.7*N) for fitting, remainder for testing. Use identical
patients and random streams at kappa = 0 and 1. Report raw RMSE (root mean
squared error), R² = 1-SSE/sum((y-mean_test_y)^2) pooled over patients and all
24 target times, augmented-minus-local R², and relative RMSE reduction
G = 1-RMSE_augmented/RMSE_local for U and L individually. This R² definition
uses one pooled test mean, rather than averaging separate per-horizon R².
Also report a target-macro range-normalized score with denominators from E1's
single dense kappa = 1 reference. Oracle uncertainty, when printed, resamples
held-out patients with fixed fits; it does not include refitting uncertainty.

Qualification threshold: at kappa = 1, **both** renal and metabolic G must be
at least 0.05 (5% relative RMSE reduction), and the target-macro reduction must
be at least 0.05. At kappa = 0, neither target may have G greater than 0.02.
A failed threshold is a reported failed regime; do not retune after viewing
these held-out results under this registration. The 100-patient CPU test checks
execution and prints gains; its noisy estimates are not the qualification set.
No neural smoke is started before the 400-patient oracle is recorded.

## Clinical observation lens

At kappa = 1, additionally run ridge on the same generated labels and held-out
patients for common target observation probabilities p in
{0, 0.01, 0.035, 0.05, 0.08274778, 0.10, 0.25, 0.50, 1.0}. Use nested masks
from the same uniforms. Report per-target gain and the largest tested p at
which the 5% gain threshold holds, along with the whole curve; do not assume
monotonicity or interpolate an untested transition. This is an oracle
observation threshold, not an experimentally demonstrated neural threshold.
Compare with clinical creatinine 6.70%, BUN 8.23%, either renal lab 8.27% in
A-train, and either renal lab 5.55% in B; distinguish per-row and hourly units.
The primary unequal-rate point and the hourly-rate-converted sensitivity are
reported separately from the common-p sweep.

## Neural success criterion and future run plan

The primary neural metric is H3's macro-NRMSE: pool squared errors over held-out
patients, 24 times, and channels within each organ, take the square root, divide
by that organ's fixed range, then average the three organs equally. Use one
E1 kappa = 1 reference with dataset seed 0, all 400 patients and all saved times
for the ranges, adding 1e-6 as in H3. E1 targets have changed, so the numerical
reference ranges must be generated for E1; the old target ranges are not reused.
Keep per-kappa normalization as a diagnostic, never as the primary endpoint.

Retain all six frozen edge rules: admissible {(0,1),(0,2)}, reversed, random
(the original seed-specific two-edge draws), dense, none, and misspecified-1.
Organ order is cardiovascular, renal, metabolic. Retain dense initialization
followed by edge selection and the matched coupling LayerNorm in every arm,
including none. Do not choose a different random graph after seeing a result.

For comparator c in {none, reversed, random}, define paired differences
Delta_c(kappa,seed) = macro_NRMSE_c - macro_NRMSE_admissible. Neural success
requires **all** of the following, without replacing a failed comparator:

1. At kappa = 1, each of the three mean paired differences is positive and
   its two-sided 95% paired Student-t interval excludes zero on the positive
   side: mean(Delta) ± 3.182446305 * sd(Delta,ddof=1)/sqrt(4).
2. For each comparator separately, the four-seed mean gap is non-decreasing
   over kappa = 0, 0.5, 1. No trend tolerance or endpoint substitution is allowed.
3. The oracle qualification above passes. The kappa = 0 neural cell is a
   no-coupling control, not a requirement for an impossible positive edge gain.

These are seed-paired intervals for four training/split seeds on one generated
patient set; they are not patient-population uncertainty. Success is a
conjunction of the three comparator tests; no selecting the best comparison.
Dense and misspecified arms and both monolithic controls are descriptive.

The future grid has 8 arms × 4 seeds × 3 kappa = **96 fits**: six graph arms,
Control-GRU hidden width 96, and capacity-matched Control-GRU hidden width 201.
Graph d_model = 64, d_state = 32, two layers, dropout 0.1, organ dimensions
(4,1,1); report actual parameter counts. Width 201 matches the no-edge model's
parameter count approximately as in H3, not each edge-bearing arm. The frozen
monolithic GRU consumes zero-imputed values and controls, but does not use the
explicit masks that the graph models consume; preserve and disclose this
architecture caveat. Edge comparisons themselves share identical input rules.

Each cell uses 400 patients, dataset seed 0, paired split/initialization seeds
0–3, 70/30 patient split, Adam lr 0.002, batch size 128, 60 epochs, gradient norm
cap 1, no scheduler, no early stopping or validation-based selection. Training
moments use only the training patients' dense labels over all saved times, as
in H3. Only context samples enter the encoder; predictions are free-running.
The source future is never an encoder feature. Known future control is common
to every model. No full fit is authorized in positive control.

run_host_e1.sh defaults to a dry run, prints data-generation and fit commands,
supports CPU and CUDA planning, and requires an explicit --execute for a future
host launch. Preflight all output destinations and refuse existing results.
Only CPU oracle/tests and one admissible, one-epoch, at-most-24-patient CPU smoke
are allowed now. The implemented runner must carry the real masks rather than
the frozen all-ones batch masks.

## Costs, provenance, and delivery

The frozen factual integration is vectorized over patients and cached only
inside the designated private workspace scratch. The cost is approximately
43,560 RK4 steps for a six-hour factual cohort, independently of E1 kappa;
there is no six-dose counterfactual multiplier. Oracle work consists of small
ridge systems with at most 156 features and 24 outputs, plus a fixed observation
sweep; report actual CPU wall times in the receipt. The future neural budget is
5,760 epochs (96 × 60), with three training batches per epoch for 280 training
patients. Estimate future runtime from the single smoke only, label the
extrapolation and its limitations, and do not promise a CUDA runtime.

Record input/source hashes, exact commands, split indices, versions, timings,
actual results, checks, and limitations. Required outputs are this design,
sim_positive_control.py, oracle_check.py, oracle_results.json, run_host_e1.sh,
tests/, and DISTRIBUTION_NOTE.md. No installs, network, git operations, /tmp writes, tmux
operations, or out-of-workspace edits. Stop within 120 minutes of task start.

The 2026-11-04 owner paper direction supersedes older compulsory editorial
loops. This task supplies an experiment kit rather than a paper release;
no additional editorial reader or style gate is inserted. Required scientific
audit and the project lead/PI assessment remain outstanding after engineering.
