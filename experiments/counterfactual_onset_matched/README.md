# Counterfactual policies with matched intervention onset

Factual and alternative dose schedules begin at the same 72-minute onset.
The support-only family varies dose support while holding dependence fixed;
the dependence-only family varies severity/dose association while preserving
the dose multisets within severity terciles. A counterfactual recurrent network
(CRN) comparator uses the eventual assigned dose as its balancing target.

From the repository root:

```bash
bash experiments/counterfactual_onset_matched/run_host_e3.sh --dry-run
python3 -B -m pytest -p no:cacheprovider experiments/counterfactual_onset_matched/tests -q
python3 -B experiments/counterfactual_onset_matched/verify_policies.py --no-legacy --output-prefix experiments/counterfactual_onset_matched/runs/policy_statistics
```

The default core plan prints **184 commands: 160 main fits and 24 continuous-dose
CRN diagnostics**. Omit `--dry-run` to execute into a fresh `runs/host/` directory.
The additional `--group matched-control` plan prints four Control-GRU fits on
the identical randomised-dose archive used by the diagnostics. The released
records contain **188 runs: 160 main + 24 CRN + 4 matched controls**.

Each main family has five points, four models and four training/split seeds.
Models fit for 60 epochs; the CRN diagnostic sweeps λ = 0, 0.25, 1 at 60 and 120
epochs. Shared history and onset checks are independent of fitted scores.
Policy statistics for 50 and 400 patients are included under `artifacts/`.
The original legacy synthetic archives are not included; regenerate them using
the released simulator tools if the optional legacy policy inventory is needed.

Direction accuracy compares adjacent-dose effect signs. The main endpoint uses
21 post-onset samples, rather than pre-onset trivial equalities. In the matched
randomised-dose diagnostic there are **60,480 exact post-effect cells per seed**.
Control-GRU seed accuracies are **0.992063, 0.972073, 0.973644, 0.985136**;
all six CRN λ/budget arms have lower exact and tolerance post-effect accuracy
in all four seed pairs. This is a conditional synthetic benchmark result.

Read [DESIGN_E3.md](DESIGN_E3.md), [E3_READING.md](artifacts/host/E3_READING.md),
[E3_READING_ADDENDUM.md](artifacts/host/E3_READING_ADDENDUM.md) and the adjacent
summary JSON files for every run, paired interval, physical-unit error and
qualification. The historical audit records **four dataset-hash discrepancies
across three training archives**. Earlier training arrays were unavailable.
Matching saved predictions and test truth does not establish identical historical
training arrays; that provenance qualification remains unresolved.
No prediction archives or checkpoints are distributed.

## v5 policy findings and boundaries

At fixed severity–dose Spearman rank correlation **0.300**, widening within-
tercile dose support raises four-seed mean post-effect direction recovery:
Control-GRU **0.347 → 0.909**, CRN-lite **0.342 → 0.909**, PhysioGraph-GRU
**0.310 → 0.897** and PhysioGraph-SSM **0.355 → 0.890**. Endpoint paired gains
are **+0.54 to +0.59**, with 95% paired t intervals excluding zero and 4/4
positive seeds for every model.

With within-tercile dose multisets fixed, attainable rank dependence spans only
**0–0.30**. Control-GRU changes **0.991 → 0.909**, a paired difference
**−0.083 [−0.179, +0.013]**; PhysioGraph-GRU changes **0.964 → 0.897**,
**−0.067 [−0.135, +0.000]**. Both intervals include zero. Identical conditional
dose distributions cap the attainable range, so these runs do not test severe
deterministic dependence. A near-zero rank point is not independent randomised
treatment, and severity-tercile coverage does not establish conditional positivity.

Repaired CRN-lite's eventual-dose target is nonconstant in all 40 fits, but
every exact post-effect paired interval versus Control-GRU includes zero. The
continuous-dose CRN trails the matched Control-GRU on the identical onset-matched
randomised-dose set in all six λ/epoch arms and 4/4 seeds (paired accuracy
intervals below zero). This is an estimator failure
in this matched synthetic task, rather than an attribution to onset mismatch.

The legacy c × σ grid remains a historical diagnostic. Zero Gaussian assignment
noise leaves the uniform random-dose component for c < 1; only c = 1 is
deterministic given severity. Noise jointly changes support and dependence.
The older counterfactual switch is at minute 60 while factual dosing begins at
minute 72; randomising eventual dose alone does not identify that earlier-start
intervention. Its pre-switch target caps exact-sign accuracy at 0.965, missing
predicted trajectories prevent exact post-effect rescoring, and legacy CRN-lite's
context-dose balancing target is identically zero. Those qualifications do not
apply as a claim that the repaired target is constant or onset-mismatched.
