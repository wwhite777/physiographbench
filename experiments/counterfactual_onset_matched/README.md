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
effective reading contains **188 runs: 160 main + 24 CRN + 4 matched controls**.
Release 1.2.0 retains **192 physical records**: the original 188 plus four
replacement main-grid records. The superseded originals remain as provenance.

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
training arrays. The [current-archive rerun addendum](artifacts/host/E3_READING_RERUN_ADDENDUM.md)
resolves archive identity prospectively for the effective 160-record main grid;
it does not recover or certify the unavailable historical training arrays.
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

## Release 1.2.0: effective main-grid records

The four 60-epoch CPU re-fits below replace only the effective reading of the
corresponding original records. Paths are relative to `artifacts/host/`; each
directory contains only `run.json` in this distribution.

| Replacement | Superseded original retained |
|---|---|
| `main_rerun/dependence_only/point4/crn_lite/seed3/run.json` | `main/dependence_only/point4/crn_lite/seed3/run.json` |
| `main_rerun/support_only/point1/crn_lite/seed3/run.json` | `main/support_only/point1/crn_lite/seed3/run.json` |
| `main_rerun/support_only/point1/physiograph/seed1/run.json` | `main/support_only/point1/physiograph/seed1/run.json` |
| `main_rerun/support_only/point2/physiograph_gru/seed0/run.json` | `main/support_only/point2/physiograph_gru/seed0/run.json` |

The [effective inventory](artifacts/host/E3_EFFECTIVE_INVENTORY.json) selects
156 original records and four replacements, with distributed file hashes,
archive-identity metadata and the four retained superseded originals.
Use this selection instead of recursively aggregating both `main/` and
`main_rerun/`. The [rerun summary](artifacts/host/e3_summary_rerun.json)
preserves full-precision values and original source fingerprints; those
historical fingerprints differ from the sanitized public-file hashes.

The main scientific interpretation is unchanged: broader measured support
is associated with much better direction recovery at fixed measured rank
dependence; increasing dependence over the tested modest range gives a
smaller descriptive decline with wide seed uncertainty; repaired CRN-lite
has no consistent exact-direction advantage over Control-GRU. The effective
records underlie the recomputed main aggregates, paired contrasts and family
trends in the rerun summary, including the support/dependence conclusions above.
Two narrower numerical statements change: 15/16 shared-anchor pairs retain
exact RMSE equality, and the support point-1 state-space-model-minus-Control
heart-rate RMSE interval now excludes zero on the positive side. All 16
anchor direction scores and target distributions remain identical. The
addendum gives every affected table before and after.

Original fits used one CPU thread; the replacements used two. Changes
combine archive replacement and thread-count variation, whose contributions
are not isolated. The unchanged randomized-dose matched-control results
remain in the earlier addendum. No causal-identification or independent
scientific-review pass follows from the archive reconciliation.

The unchanged `verify_artifacts.py` expects the historical 188-record view.
For an effective-view check, copy the experiment folder to scratch, omit
the four superseded originals there, and run that verifier: the 156
originals, four replacements and 28 diagnostics give its expected 188.
The release tree itself retains all 192 physical records. Policy verification
uses `--no-legacy`; protocol regeneration requires unbundled archives and
is separate from inspecting these saved replacement records.
