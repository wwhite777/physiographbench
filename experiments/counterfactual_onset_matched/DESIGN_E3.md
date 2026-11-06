# E3 counterfactual repair design

Task counterfactual experiment; implemented by research tooling as research engineer for the assigned project lead.
This is a generator/runner build with CPU acceptance evidence, not a completed
scientific experiment. No paper, claim ledger, existing generator, earlier
dataset or prior result is edited. C4/C5 retain their current qualified reading
until the project lead integrates new full-run evidence and obtains required review.

## Intervention and scoring time

The factual schedule is untreated until **4,320 seconds (minute 72)** and then
holds its assigned vasopressor dose constant. All datasets have the frozen
six-hour horizon, 180-second untreated warm-up, 0.5-second Runge–Kutta integration
step and 300-second observation interval. Dose units are micrograms/(kg minute).
Patient parameters, initial states, severity and sepsis schedules come from the
unchanged generator through historical_experiment's recording wrapper. The original policy draws
are still consumed, including the normal draw at zero noise, so changing the new
policy does not change those patient draws.

For patient i and alternative d in {0, 0.05, 0.10, 0.20, 0.40}, the main intervention is

    A_i^d(t) = 0                 for t < 4320 s,
               d                 for t >= 4320 s.

It branches from the factual simulation using historical_experiment's existing shared-state
integrator. Every recorded pre-onset outcome is bit-identical to factual, and
`counterfactual_control` records the actual alternative doses for a direct timing
check. Schedule tests also check the left limit and the exact off-grid onset,
rather than relying only on five-minute samples.

The context remains C = 12 samples at minutes 0–55. The model rolls out K = 24
samples at minutes 60–175. Its alternative control plan is zero at minutes 60,
65 and 70 and equals d from minute 75. We score the **21 samples at minutes
75–175**, strictly after onset. This preserves the original context and rollout
budget while removing the unsupported earlier intervention. NPZ `score_indices`
is 15,…,35; `counterfactual_target` contains only those scored samples, rather
than the entire rollout. The runner saves both the full rollout and scored arrays.
Training uses the factual controls and targets over the same C:C+K window.

The separately named `temporal_extrapolation` protocol switches at 3,600 seconds
(minute 60), as in historical_experiment. Its strictly post-switch scored samples are minutes
65–175 (23 times). It includes treated alternative samples at minutes 60–70,
when factual treatment is absent. It must retain that temporal-extrapolation
label and must not be pooled with the onset-matched experiment.

Numerical convention: the complete RK4 step ending at the switch uses the factual
schedule, including its endpoint evaluation. Consequently the boundary state has
the frozen integrator's endpoint contribution from factual dosing; the alternative
dose first enters the next step and direct observations at the switch. All lanes
share this state. This preserves historical_experiment/factual numerical behavior, rather than
introducing a new discontinuity integrator. No recorded outcome before the switch
or schedule value strictly before it is exposed to an alternative dose.

## Two policy families

“Support” here is the empirical 5th–95th percentile interval of assigned factual
doses **within each severity tercile**; its width and membership of the five
alternative doses are reported. It is a coarse conditional coverage diagnostic,
not a proof of causal positivity or identification. “Dependence” is global
Spearman rank correlation between latent severity S and assigned dose D. Pearson
correlation is also measured, so the two meanings of correlation remain explicit.

Let g_i be the tercile of severity S_i, using empirical severity quantiles and
`searchsorted(..., side='right')`. For each tercile g with n_g patients, fix the
sorted dose multiset

    Q_g(j) = 0.5*j/(n_g - 1),    j = 0,…,n_g - 1.

Let r_i be the centered, unit-standard-deviation rank of severity inside its
tercile, and independently draw z_i from a standard normal distribution using
NumPy `default_rng(SeedSequence([dataset_seed, 2703]))`. For a scalar a, sort the
patients within each tercile by z_i + a*r_i and assign Q_g in that order. Call
the resulting dose B_i(a). Calibrate a by 64 bisection steps on [-10^6, 10^6],
retaining the visited assignment closest to the requested global Spearman target.
Increasing a moves within-tercile pairs toward their severity ordering. Failure
to reach the target within **±0.02** raises an error; it never silently changes
the target. Assignment and verification use the stored float32 doses.

**SUPPORT-ONLY**, five points p = 0,…,4:

    rho_star = 0.30,
    w_p = {0.10, 0.25, 0.50, 0.75, 1.00},
    D_i(p) = 0.25 + w_p * (B_i(a_rho_star) - 0.25).

Positive affine scaling preserves every dose rank and the Pearson correlation
with S. No clipping or new patient noise is added. Each tercile's dose interval
has q05 = 0.25 - 0.225*w_p and q95 = 0.25 + 0.225*w_p, so its width is 0.45*w_p.
We verify Spearman against 0.30 within ±0.02, and Pearson across widths against
the width-one anchor within ±0.02 (actual errors are much smaller). The anchor
Pearson depends on the sampled severities; it is not declared equal to Spearman.
For n = 400, seed 0, it is about 0.305397; for the n = 50 smoke it is about
0.271761. This distinction avoids claiming a Pearson target that was not fitted.

**DEPENDENCE-ONLY**, five points p = 0,…,4:

    rho_p = {0.000, 0.075, 0.150, 0.225, 0.300},
    D_i(p) = B_i(a_rho_p).

Every tercile retains the **identical full dose multiset**, not merely the same
range. Its q05 and q95 remain 0.025 and 0.475; the permitted absolute discrepancy
is **10^-6 dose units**. Its 5–95% width stays 0.45, and its supported alternative
grid is {0.05, 0.10, 0.20, 0.40}, or 4/5 in each tercile. The zero dose lies outside
the central 90% interval even though zero is a multiset endpoint. Target rank
correlations are verified within ±0.02; both observed correlations must increase
across the five points in the policy verification suite.

This deliberately strong support control has a scientific cost. With identical
dose distributions in all three terciles, global severity–dose rank correlation
cannot approach one; its maximum is about one third. This family measures a
modest dependence range and does not recreate severe deterministic confounding.
The zero-correlation point is a calibrated finite-population assignment and is
**not** described as independent randomized treatment. Conditional dependence at
finer severity resolution, finite-patient assignment constraints, and changes
outside these measured statistics remain possible. The names SUPPORT-ONLY and
DEPENDENCE-ONLY describe these operational controls, not universal isolation of
all properties of an assignment law. Severity and sepsis never enter model inputs.
The common endpoint (support p4 and dependence p4) is an intentional anchor.

The original policy is retained as `family=legacy`:

    D_i = clip(c*0.5*S_i + (1-c)*U_i + epsilon_i, 0, 0.5),
    U_i ~ Uniform(0,0.5), epsilon_i ~ Normal(0,sigma).

The existing c × sigma grid is c in {0, .1, .25, .5, .75, 1}, sigma in
{0, .08, .15, .25}. `verify_policies.py` inventories and hashes all 24 old
shared-history files and prints their statistics into the JSON evidence. They
remain the old minute-60 diagnostic, without relabelling. New legacy-policy
generation can independently select the onset-matched or temporal protocol.

## Repaired CRN-lite

CRN-lite retains its 96-unit GRU encoder/decoder and treatment prediction head.
Its auxiliary label is now the **assigned eventual factual dose D_i**, supplied
explicitly in training batches as a scalar, rather than mean context dose
(identically zero). The pre-treatment representation is intended to precede
assignment. Thus the assignment whose dependence on that representation is being
penalized is D_i, even though that assignment is not yet administered during
context. This is a supervised adversarial label, never a prediction input.
Inference removes both that label and future outcome targets before rollout.

The auxiliary loss is 0.5*mean((head(GRL_lambda(h_i)) - D_i)^2). Gradient reversal
(GRL) multiplies its encoder gradient by -lambda and leaves the treatment-head
gradient unchanged. Factual outcome mean squared error, Adam learning rate
0.002, gradient norm cap 1, batch size 128, 70/30 patient split and factual
training-split observation normalization remain unchanged. Every run prints
all/train/test assigned-dose distributions: count, unique count, min/max,
mean/standard deviation, seven quantiles and ten fixed dose-bin counts.

The main grid fixes lambda = 0.5. The separate `lite-lambda` group sweeps
lambda in {0, 0.25, 1} over all ten policy points and four seeds (120 extra fits).
It keeps the same CRN-lite architecture even at zero. Gradient tests verify
opposite encoder gradients, identical head gradients, zero encoder contribution
at lambda = 0, and loss sensitivity to the assigned-dose labels.

A continuous regression head primarily penalizes predictable conditional-mean
dose signal. It does not establish full distributional independence, recover
hidden confounders, or guarantee correct counterfactual estimation. This remains
CRN-lite, not a faithful full CRN claim or an established positive control.

## Continuous-dose CRN diagnostic and host commands

The diagnostic uses the existing historical_experiment `CRNFull`/`train_crn` adaptation with
`legacy_zero=False` at every lambda, including zero. It retains ten fixed dose
classes for balancing, continuous dose for outcome heads, ordinary dropout,
teacher-forced decoder fitting, autoregressive prediction, and the unchanged
two-stage epoch split. It uses the new onset-matched legacy-policy (c,sigma) =
(0,0) data, where the eventual dose is drawn uniformly independently of severity.
The intervention now begins at the same time as factual dosing. This repairs
the diagnosed timing mismatch; random dose assignment still does not by itself
establish all state-coverage/identification assumptions or estimator adequacy.

Run plans are produced by `run_host_e3.sh`:

| group | policy/protocol | fits |
|---|---|---:|
| main | 2 families × 5 points × 4 models × 4 seeds, onset-matched, 60 epochs | 160 |
| crn-diagnostic | randomized dose × 3 lambdas × {60,120} total epochs × 4 seeds | 24 |
| core (default) | main + crn-diagnostic | 184 |
| lite-lambda | 10 points × 3 lambdas × 4 seeds, 60 epochs | 120 |
| temporal | separately labelled minute-60 version of the 160-fit main grid | 160 |
| legacy | 24 original policy settings × 4 models × 4 seeds, onset-matched | 384 |
| all | core + lite-lambda (does not include optional temporal/legacy grids) | 304 |

Models are `control_gru`, `crn_lite` (repaired), `physiograph_gru`, and
`physiograph` (SSM nodes). Main models retain their frozen dimensions and
admissible graph; parameter counts are recorded. All runs use dataset seed 0
and paired model/split seeds 0–3. Each run saves its checkpoint, predictions,
patient split, statistics, source hashes and dataset manifest. Scores report
physical-unit channel RMSE and direction accuracy; no new fixed-range NRMSE
denominator is introduced or compared to old normalized scores.

Examples, to be executed by the project lead when full runs are authorized:

```bash
bash run_host_e3.sh --dry-run
bash run_host_e3.sh --group lite-lambda --dry-run
bash run_host_e3.sh --group temporal --dry-run
bash run_host_e3.sh --group legacy --dry-run
```

Removing `--dry-run` executes that selected plan on CPU. The launcher validates
every destination and log before starting, refuses existing outputs, and confines
outputs and scratch to counterfactual experiment. Dry runs create no run directories or logs themselves.
No full run is executed by this task.

## Direction accuracy

A cell is patient × adjacent dose pair × scored post-switch time × outcome
channel. Exact accuracy uses equality of `sign(predicted adjacent difference)`
and `sign(true adjacent difference)`; zero is a third category. Report separately:

- **Post-effect:** true adjacent difference is nonzero in stored simulator truth.
- **Zero-effect:** true adjacent difference is exactly zero, including float32
  quantization ties. This is a zero-response agreement diagnostic, not a sign test.
- **All cells:** provided for compatibility, with both component denominators.

The effect-tolerance sensitivity variant maps differences with magnitude ≤ tau
to zero in both prediction and truth. In channel order MAP, HR, CO, CVP, UO,
lactate, tau is {0.1 mmHg, 0.1 beats/min, 0.01 L/min, 0.05 mmHg, 0.01 mL/min,
0.01 mmol/L}. These are declared numerical sensitivity thresholds, not clinical
minimum effects or tuned thresholds. Its nonzero-effect and zero-effect scores
are reported separately too. Both schemes include integer correct counts and
denominators, including per-channel counts. An empty subset has null accuracy
and denominator zero. Support-restricted versions require both adjacent doses
inside the patient's tercile 5–95% interval; full and selected cell totals remain
visible. Tests cover sign reversals, small effects, zeros and empty support.

## Acceptance evidence and scope

`artifacts/policy_statistics.{csv,json,md}` cover the 400-patient sweeps at four
dataset seeds and inventory the 24 legacy files. The 50-patient checks and actual
smoke outcomes are in the receipt and smoke artifacts. Policy verification
requires no physiology simulation and is not a full experiment. Tests exercise
the real six-hour onset and temporal schedules, matching-dose branches, untreated
prefix inference, auxiliary gradients, score denominators and dry-run plans.

The user’s 2026-11-04 final-kit/outside-review paper workflow supersedes
older automatic editorial gates. This task delivers engineering evidence and
does not produce a paper kit, so advisory prose metrics are not applicable.
No scientific freeze, review eligibility or required independent scientific audit
is changed. Implementation authorship prevents this worker from serving as its
own independent reviewer. Full-run scientific conclusions remain unmeasured.
