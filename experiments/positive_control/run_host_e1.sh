#!/usr/bin/env bash
# Future PI-chosen grid. Default: print the plan, run no Python commands.
set -euo pipefail
set -C
task_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$task_dir/../.." && pwd)"
script_dir="experiments/positive_control"
scratch_root="${TMPDIR:-$repo_root/.scratch}"
cd -- "$repo_root"
python_bin="${PYTHON:-python3}"
device=cpu
threads=1
output_root="$task_dir/runs/full"
execute=false
while (($#)); do
    case "$1" in
        --device|--threads|--output-root)
            if (($# < 2)); then echo "Missing value for $1" >&2; exit 2; fi
            case "$1" in
                --device) device="$2" ;;
                --threads) threads="$2" ;;
                --output-root) output_root="$2" ;;
            esac
            shift 2 ;;
        --dry-run) execute=false; shift ;;
        --execute) execute=true; shift ;;
        --help)
            echo "Usage: bash $0 [--device cpu|cuda] [--threads 1] [--output-root PATH] [--dry-run|--execute]"
            echo "Default is a dry run: 3 datasets and 96 fits; --execute is for a later PI-authorized host launch."
            exit 0 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
if [[ "$device" != cpu && "$device" != cuda ]]; then
    echo "Device must be cpu or cuda" >&2; exit 2
fi
if [[ ! "$threads" =~ ^[1-9][0-9]*$ ]]; then
    echo "Threads must be a positive integer" >&2; exit 2
fi
output_root="$(realpath -m -- "$output_root")"
case "$output_root/" in
    "$task_dir/"*|"$scratch_root/"*) ;;
    *) echo "Output root must remain inside positive control" >&2; exit 2 ;;
esac
export TMPDIR="${TMPDIR:-$task_dir/.scratch}"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
export XDG_CACHE_HOME="$TMPDIR/cache"
export PYTHONDONTWRITEBYTECODE=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS="$threads"
export MKL_NUM_THREADS="$threads"
export OPENBLAS_NUM_THREADS="$threads"
kappas=(0 0.5 1)
arms=(admissible reversed random dense none misspecified-1 control_gru control_gru_matched)
# Preflight the entire plan before any data generation, directory creation, or fit.
for kappa in "${kappas[@]}"; do
    dataset="$output_root/datasets/kappa_${kappa}.npz"
    manifest="$output_root/datasets/kappa_${kappa}.manifest.json"
    data_log="$output_root/logs/generate_kappa_${kappa}.log"
    for path in "$dataset" "$manifest" "$data_log"; do
        if [[ -e "$path" || -L "$path" ]]; then
            echo "Refusing existing output: $path" >&2; exit 2
        fi
    done
    for arm in "${arms[@]}"; do
        for seed in 0 1 2 3; do
            result="$output_root/kappa_${kappa}/$arm/seed${seed}.json"
            log="$output_root/logs/kappa_${kappa}_${arm}_seed${seed}.log"
            if [[ -e "$result" || -L "$result" || -e "$log" || -L "$log" ]]; then
                echo "Refusing existing result or log: $result ; $log" >&2; exit 2
            fi
        done
    done
done
output_root="${output_root#"$repo_root/"}"
emit_or_run() {
    local log="$1"
    shift
    if "$execute"; then
        echo "Running; log: $log"
        "$@" > "$log" 2>&1
    else
        printf '%q ' "$@"
        printf '> %q 2>&1\n' "$log"
    fi
}
if "$execute"; then
    mkdir -p -- "$TMPDIR" "$output_root/logs"
fi
for kappa in "${kappas[@]}"; do
    emit_or_run "$output_root/logs/generate_kappa_${kappa}.log" \
        "$python_bin" -B "$script_dir/sim_positive_control.py" generate \
        --kappa "$kappa" --n-patients 400 --seed 0 \
        --out "$output_root/datasets/kappa_${kappa}.npz"
done
for kappa in "${kappas[@]}"; do
    for arm in "${arms[@]}"; do
        for seed in 0 1 2 3; do
            emit_or_run "$output_root/logs/kappa_${kappa}_${arm}_seed${seed}.log" \
                "$python_bin" -B "$script_dir/sim_positive_control.py" run-cell \
                --arm "$arm" --kappa "$kappa" --seed "$seed" --epochs 60 \
                --n-patients 400 --device "$device" --threads "$threads" --full-run \
                --npz "$output_root/datasets/kappa_${kappa}.npz" \
                --reference-npz "$output_root/datasets/kappa_1.npz" \
                --out "$output_root/kappa_${kappa}/$arm/seed${seed}.json"
        done
    done
done
echo "Plan: 3 datasets; 96 fits; 60 epochs per fit; device=$device; execute=$execute"
