#!/usr/bin/env bash
# HOST handoff. Worker executes --dry-run only.
# 24 shared datasets / 384 runs; 3 legacy datasets / 48 disclosure runs.
# Dataset seed=0; seeds 0..3 vary splits and training. One log per command.
# The legacy c=1,sigma=.03 file also preserves simulator_grid's fixed NRMSE reference.
set -euo pipefail

TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_ROOT="${PHYSIOGRAPH_ROOT:-$(cd -- "$TASK_ROOT/.." && pwd)}"
PY="${PYTHON:-python3}"
DRY_RUN=0
if [[ ${1:-} == --dry-run ]]; then
    DRY_RUN=1
    shift
fi
if [[ $# != 1 ]]; then
    printf 'Usage: bash run_grids_h5.sh [--dry-run] <owned-output-directory>\n' >&2
    exit 2
fi
GRID_DIR="$($PY -B -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]).resolve(); root=pathlib.Path(sys.argv[2]).resolve(); assert p.is_relative_to(root), "output outside owned directory"; print(p)' "$1" "$TASK_ROOT")"
if [[ $DRY_RUN == 0 && ! -d "$GRID_DIR" ]]; then
    printf 'The maintainer must create the output directory first: %s\n' "$GRID_DIR" >&2
    exit 2
fi
export TMPDIR="${TMPDIR:-$RELEASE_ROOT/.scratch}"
export PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="$TMPDIR/matplotlib"
EPOCHS="${EPOCHS:-60}"
THREADS="${THREADS:-1}"
CONFOUNDS=(0 0.1 0.25 0.5 0.75 1.0)
SIGMAS=(0 0.08 0.15 0.25)
MODELS=(physiograph physiograph_gru control_gru crn_lite)
SEEDS=(0 1 2 3)

run_logged() {
    local log="$1"
    shift
    if [[ $DRY_RUN == 1 ]]; then
        printf '%q ' "$@"
        printf '> %q 2>&1\n' "$log"
    else
        "$@" > "$log" 2>&1
    fi
}

if [[ $DRY_RUN == 0 ]]; then
    mkdir -p "$TMPDIR" "$GRID_DIR/data" "$GRID_DIR/runs" "$GRID_DIR/logs"
fi
REF="$GRID_DIR/data/legacy_c1.0_sigma0.03.npz"
# Generate all data before training; the 27th file serves as the common reference.
for protocol in legacy shared; do
    if [[ $protocol == legacy ]]; then
        POLICY_C=(0 0.5 1.0)
        POLICY_S=(0.03)
    else
        POLICY_C=("${CONFOUNDS[@]}")
        POLICY_S=("${SIGMAS[@]}")
    fi
    for confound in "${POLICY_C[@]}"; do
        for sigma in "${POLICY_S[@]}"; do
            ID="${protocol}_c${confound}_sigma${sigma}"
            run_logged "$GRID_DIR/logs/generate_$ID.log" "$PY" -B "$TASK_ROOT/sim_policy_ext2.py" \
                --kappa 1 --confound "$confound" --sigma "$sigma" --seed 0 --n_patients 400 \
                --cf_protocol "$protocol" --C 12 --K 24 --horizon_h 6 --out_dt 300 \
                --out "$GRID_DIR/data/$ID.npz"
        done
    done
done
for protocol in shared legacy; do
    if [[ $protocol == legacy ]]; then
        POLICY_C=(0 0.5 1.0)
        POLICY_S=(0.03)
    else
        POLICY_C=("${CONFOUNDS[@]}")
        POLICY_S=("${SIGMAS[@]}")
    fi
    for confound in "${POLICY_C[@]}"; do
        for sigma in "${POLICY_S[@]}"; do
            DATA="$GRID_DIR/data/${protocol}_c${confound}_sigma${sigma}.npz"
            for model in "${MODELS[@]}"; do
                for seed in "${SEEDS[@]}"; do
                    ID="h5_${protocol}_c${confound}_sigma${sigma}_${model}_s${seed}"
                    run_logged "$GRID_DIR/logs/$ID.log" "$PY" -B "$TASK_ROOT/sim_grid_runner2.py" \
                        --task counterfactual --kappa 1 --confound "$confound" --sigma "$sigma" \
                        --cf_protocol "$protocol" --model "$model" --variant admissible \
                        --seed "$seed" --dataset_seed 0 --n_patients 400 --epochs "$EPOCHS" \
                        --device cpu --threads "$THREADS" --C 12 --K 24 --horizon_h 6 --out_dt 300 \
                        --npz "$DATA" --reference_npz "$REF" --out "$GRID_DIR/runs/$ID.json"
                done
            done
        done
    done
done
run_logged "$GRID_DIR/logs/aggregate.log" "$PY" -B "$TASK_ROOT/aggregate_grids2.py" \
    --in "$GRID_DIR/runs" --out "$GRID_DIR/h5_grid.json" "$GRID_DIR/overlap_table.csv" \
    --require_complete
