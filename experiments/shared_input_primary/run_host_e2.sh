#!/usr/bin/env bash
# D-014: six grid cells, then 40 arms and 24 longer-budget fits. No retuning on B.
set -euo pipefail
set -C
task_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$task_dir/../.." && pwd)"
script_dir="experiments/shared_input_primary"
scratch_root="${TMPDIR:-$repo_root/.scratch}"
cd -- "$repo_root"
python_bin="${PYTHON:-python3}"
device=cpu
threads=2
batch=128
output_root="$task_dir/runs/host"
dry_run=false
while (($#)); do
    case "$1" in
        --device|--threads|--batch|--output-root)
            if (($# < 2)); then
                echo "Missing value for $1" >&2; exit 2
            fi
            case "$1" in
                --device) device="$2" ;;
                --threads) threads="$2" ;;
                --batch) batch="$2" ;;
                --output-root) output_root="$2" ;;
            esac
            shift 2 ;;
        --dry-run) dry_run=true; shift ;;
        --help)
            echo "Usage: $0 [--device cpu|cuda] [--threads 2] [--batch 128] [--output-root PATH] [--dry-run]"
            exit 0 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
if [[ "$device" != cpu && "$device" != cuda ]]; then
    echo "Device must be cpu or cuda" >&2; exit 2
fi
if [[ ! "$threads" =~ ^[1-9][0-9]*$ || ! "$batch" =~ ^[1-9][0-9]*$ ]]; then
    echo "Threads and batch must be positive integers" >&2; exit 2
fi
output_root="$(realpath -m -- "$output_root")"
case "$output_root/" in
    "$task_dir/"?*|"$scratch_root/"?*) ;;
    *) echo "Output root must stay inside shared-input experiment workspace, below its root" >&2; exit 2 ;;
esac
export TMPDIR="${TMPDIR:-$task_dir/.scratch}"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
export PYTHONDONTWRITEBYTECODE=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
stages=() arms=() lrs=() widths=() seeds=() budgets=() destinations=() logs=()
add_job() {
    stages+=("$1"); arms+=("$2"); lrs+=("$3"); widths+=("$4")
    seeds+=("$5"); budgets+=("$6"); destinations+=("$output_root/$7")
    logs+=("$output_root/logs/${1}_${2}_${3}_${4}_epochs${6}_seed${5}.log")
}
for lr in 0.0005 0.001 0.002; do
    for width in small large; do
        add_job grid none "$lr" "$width" 0 35 "grid/lr${lr}_${width}/seed0"
    done
done
for arm in none none_norm none_pmatch admissible dense reversed random_s0 random_s1 random_s2 misspecified-1; do
    for seed in 0 1 2 3; do
        add_job arms "$arm" selected selected "$seed" 35 "arms/$arm/seed$seed"
    done
done
for model in none admissible grud; do
    for epochs in 70 105; do
        for seed in 0 1 2 3; do
            add_job budget "$model" selected selected "$seed" "$epochs" "budget/$model/epochs$epochs/seed$seed"
        done
    done
done
# Preflight all 70 destinations, logs and the selection BEFORE any fit or mkdir.
for path in "$output_root/selection_shared.json" "${destinations[@]}" "${logs[@]}"; do
    if [[ -e "$path" || -L "$path" ]]; then
        echo "Refusing an existing run, selection or log: $path" >&2; exit 2
    fi
done
if ! "$dry_run"; then
    mkdir -p -- "$TMPDIR" "$output_root/logs"
fi
output_root="${output_root#"$repo_root/"}"
for i in "${!destinations[@]}"; do
    destinations[$i]="${destinations[$i]#"$repo_root/"}"
    logs[$i]="${logs[$i]#"$repo_root/"}"
done
for i in "${!stages[@]}"; do
    case "$i" in
        0) echo '# GRID (6 commands; the last recorded cell writes selection_shared.json)' ;;
        6) echo '# ARMS (40 commands; read selection_shared.json)' ;;
        46) echo '# BUDGET (24 commands; shared selection / frozen GRU-D selection)' ;;
    esac
    command=("$python_bin" -B "$script_dir/shared_input_primary.py" --stage "${stages[$i]}")
    case "${stages[$i]}" in
        grid) command+=(--lr "${lrs[$i]}" --width "${widths[$i]}") ;;
        arms) command+=(--arm "${arms[$i]}" --selection "$output_root/selection_shared.json") ;;
        budget) command+=(--model "${arms[$i]}" --selection "$output_root/selection_shared.json") ;;
    esac
    command+=(--seed "${seeds[$i]}" --epochs "${budgets[$i]}" --device "$device"
              --threads "$threads" --batch "$batch" --output-root "$output_root"
              --output-dir "${destinations[$i]}")
    if "$dry_run"; then
        printf '%q ' "${command[@]}"
        printf '> %q 2>&1\n' "${logs[$i]}"
    else
        echo "Running ${stages[$i]} ${arms[$i]} seed${seeds[$i]} on $device; log: ${logs[$i]}"
        "${command[@]}" > "${logs[$i]}" 2>&1
    fi
done
