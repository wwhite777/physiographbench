#!/bin/bash
# run_all.sh — end-to-end reproducibility pipeline for PhysioGraph (open-data only).
# Everything below uses public, non-credentialed data: CinC-2019 (PhysioNet, CC-BY,
# via the S3 open mirror) and an in-repo CVSim mean-circulation simulator. No MIMIC/
# eICU credentialing required. Seeds are fixed; an idle GPU index is passed as $GPU.
set -euo pipefail
# Repository root: defaults to the directory holding this script.
# Override the root with PHYSIOGRAPH_ROOT, the interpreter with PYTHON, the device with GPU.
ROOT="${PHYSIOGRAPH_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
export PHYSIOGRAPH_ROOT="$ROOT"
cd "$ROOT"
PY="${PYTHON:-python3}"
GPU="${GPU:-0}"

echo "[1/7] download CinC-2019 (both hospital systems) from PhysioNet -- no credentialing"
bash data/fetch_parallel.sh || bash data/fetch_cinc2019.sh

echo "[2/7] preprocess into the 4-organ / 16-variable cohort (A=internal, B=external)"
$PY src/cinc2019_cohort_preprocessor.py --workers 24

echo "[3/7] generate the multi-organ CVSim counterfactual benchmark (open simulator)"
$PY src/cvsim_hemodynamics_simulator.py --gen data/cvsim_counterfactual.npz --n 180 --seed 0

echo "[4/7] forecasting table: PhysioGraph vs baselines, internal + external"
# Capacity controls (gru_med, gru_large) are included so the negative result cannot be
# attributed to parameter count. Neural-CDE is available in the registry but diverged on
# the external cohort and is therefore excluded from the reported table.
$PY src/physiograph_training_runner.py \
    --models physiograph,physiograph_gru,grud,odernn,graphgru,gru,gru_med,gru_large \
    --epochs 35 --gpu "$GPU" --out result/cinc_forecasting.json

echo "[5/7] counterfactual validity under hidden confounding (multi-organ)"
$PY src/cvsim_counterfactual_runner.py --C 12 --K 24 --epochs 60 --gpu "$GPU" \
    --out result/cvsim_counterfactual.json

echo "[6/7] interpretability + theory: edge stability, rollout-error bound (Thm 1)"
PYTHONPATH="$ROOT/src" $PY -c "from physiograph_result_figures import compute_edge_stability; \
        compute_edge_stability('ckpt/physiograph.pt','data/cinc2019_cohort.npz',gpu=$GPU,\
        out='result/edge_stability.json')"
$PY src/physiograph_theory_checks.py --which thm1 --gpu "$GPU"
# optional (slower): sparse-vs-dense graph ablation (Thm 3)
# $PY src/physiograph_theory_checks.py --which thm3 --gpu "$GPU" --epochs 12

echo "[7/7] render all exact-data figures"
$PY src/physiograph_result_figures.py --which all

echo "DONE. Results in result/*.json, figures in result/figure/exp{1,2,3}/"

# ---------------------------------------------------------------------------
# Optional extras that produce the remaining reported artefacts.
#
#   4 seeds + significance tests  ->  result/forecast_seed_stats.json
#     for S in 0 1 2 3; do
#       $PY src/physiograph_training_runner.py --seed "$S" --gpu "$GPU" \
#           --models physiograph,physiograph_gru,grud,odernn,graphgru,gru,gru_med,gru_large \
#           --out "result/seeds/forecast_seed$S.json"
#     done
#     $PY src/physiograph_seed_stats.py --gpu "$GPU"
#
#   Sparse-vs-dense (Thm 3) and edge falsification (H4), 2 seeds each:
#     $PY src/physiograph_theory_checks.py --which thm3 --gpu "$GPU" --epochs 12
#     $PY src/physiograph_theory_checks.py --which h4   --gpu "$GPU" --epochs 12
#
#   "When does it help?" sweeps -> result/sweeps/*.json, result/tier2_sweeps.json
#     H1 horizon:    rerun step [4] with --C/--K in {12,24}x{12,24}
#     H2 low data:   rerun step [4] with --train_frac in 0.05 0.1 0.25 0.5 1.0
#     H3 coupling:   regenerate the simulator with --kappa in 0.0 0.5 1.0, rerun step [5]
#     H5 confounding: regenerate the simulator with --conf in 0.0 0.5 1.0, rerun step [5]
#     $PY src/physiograph_sweep_analysis.py --which h1
#     $PY src/physiograph_sweep_analysis.py --which h2
# ---------------------------------------------------------------------------
