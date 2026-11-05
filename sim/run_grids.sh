#!/usr/bin/env bash
# Host handoff only. The worker never executes the full grids.
# Usage: bash run_grids.sh <existing-owned-output-directory>
#        bash run_grids.sh --dry-run <owned-output-directory>
# Dataset seed is fixed at 0; seeds 0..3 vary the patient split and training.
# H3 preserves the frozen c=1, SD=0.03 policy. H5 uses the card's TOTAL sigma.
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
    printf 'Usage: bash run_grids.sh [--dry-run] <owned-output-directory>\n' >&2
    exit 2
fi
GRID_DIR="$1"
case "$GRID_DIR" in
    /*) ;;
    *) GRID_DIR="$PWD/$GRID_DIR" ;;
esac
# Reject traversal and require an existing directory in execution mode. The Python
# writer also resolves symlinks and enforces the owned root on every output.
GRID_DIR="$($PY -B -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]).resolve(); root=pathlib.Path(sys.argv[2]).resolve(); assert p.is_relative_to(root), "output outside owned directory"; print(p)' "$GRID_DIR" "$RELEASE_ROOT")"
if [[ $DRY_RUN == 0 && ! -d "$GRID_DIR" ]]; then
    printf 'The maintainer must create the output directory first: %s\n' "$GRID_DIR" >&2
    exit 2
fi
export TMPDIR="${TMPDIR:-$RELEASE_ROOT/.scratch}"
export PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="$TMPDIR/matplotlib"
DEVICE="${DEVICE:-cpu}"
EPOCHS="${EPOCHS:-60}"
THREADS="${THREADS:-1}"
KAPPAS=(0 0.1 0.25 0.5 0.75 1.0)
VARIANTS=(admissible reversed random dense none misspecified-1)
SIGMAS=(0 0.08 0.15)
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
REF="$GRID_DIR/data/reference_k1_c1_sigma003.npz"
run_logged "$GRID_DIR/logs/generate_reference.log" "$PY" -B "$TASK_ROOT/sim_policy_ext.py" \
    --kappa 1 --confound 1 --sigma 0.03 --seed 0 --n_patients 400 --out "$REF"
for kappa in "${KAPPAS[@]}"; do
    DATA="$GRID_DIR/data/h3_k${kappa}.npz"
    run_logged "$GRID_DIR/logs/generate_h3_k${kappa}.log" "$PY" -B "$TASK_ROOT/sim_policy_ext.py" \
        --kappa "$kappa" --confound 1 --sigma 0.03 --seed 0 --n_patients 400 --out "$DATA"
    for variant in "${VARIANTS[@]}"; do
        for seed in "${SEEDS[@]}"; do
            ID="h3_k${kappa}_${variant}_s${seed}"
            run_logged "$GRID_DIR/logs/$ID.log" "$PY" -B "$TASK_ROOT/sim_grid_runner.py" \
                --task forecast --kappa "$kappa" --variant "$variant" --model physiograph_gru \
                --confound 1 --sigma 0.03 --seed "$seed" --dataset_seed 0 --n_patients 400 \
                --epochs "$EPOCHS" --device "$DEVICE" --threads "$THREADS" \
                --npz "$DATA" --reference_npz "$REF" --out "$GRID_DIR/runs/$ID.json"
        done
    done
done
for confound in "${KAPPAS[@]}"; do
    for sigma in "${SIGMAS[@]}"; do
        DATA="$GRID_DIR/data/h5_c${confound}_sigma${sigma}.npz"
        run_logged "$GRID_DIR/logs/generate_h5_c${confound}_sigma${sigma}.log" \
            "$PY" -B "$TASK_ROOT/sim_policy_ext.py" --kappa 1 --confound "$confound" \
            --sigma "$sigma" --seed 0 --n_patients 400 --out "$DATA"
        for model in "${MODELS[@]}"; do
            for seed in "${SEEDS[@]}"; do
                ID="h5_c${confound}_sigma${sigma}_${model}_s${seed}"
                run_logged "$GRID_DIR/logs/$ID.log" "$PY" -B "$TASK_ROOT/sim_grid_runner.py" \
                    --task counterfactual --kappa 1 --confound "$confound" --sigma "$sigma" \
                    --model "$model" --variant admissible --seed "$seed" --dataset_seed 0 \
                    --n_patients 400 --epochs "$EPOCHS" --device "$DEVICE" --threads "$THREADS" \
                    --npz "$DATA" --reference_npz "$REF" --out "$GRID_DIR/runs/$ID.json"
            done
        done
    done
done
run_logged "$GRID_DIR/logs/aggregate.log" "$PY" -B "$TASK_ROOT/aggregate_grids.py" \
    --in "$GRID_DIR/runs" --out "$GRID_DIR/h3_grid.json" "$GRID_DIR/h5_grid.json" \
    "$GRID_DIR/overlap_table.csv" --require_complete
