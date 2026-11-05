#!/usr/bin/env bash
# 24 post-hoc full fits, shared inputs, frozen edges/configuration.
set -euo pipefail
set -C
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd -- "$repo_root"
diagnostic_dir="diagnostics/shared_input_edges"
python_bin="${PYTHON:-python3}"
device="cpu"
threads=2
batch=128
output_root="runs/shared_input_edges"
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
absolute_output="$(realpath -m -- "$output_root")"
case "$absolute_output/" in
    "$repo_root/"*) output_root="${absolute_output#"$repo_root/"}" ;;
    *) echo "Output root must stay inside the repository" >&2; exit 2 ;;
esac
export TMPDIR="${TMPDIR:-$repo_root/.scratch}"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
export PYTHONDONTWRITEBYTECODE=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
log_root="$output_root/logs"
variants=(none admissible dense reversed random misspecified-1)
# Preflight ALL destinations before even creating logs/scratch or starting a fit.
# Check dry runs too so a reviewed plan cannot silently include an existing run.
for variant in "${variants[@]}"; do
    for seed in 0 1 2 3; do
        destination="$output_root/$variant/seed$seed"
        log="$log_root/${variant}_seed${seed}.log"
        if [[ -e "$destination" || -L "$destination" || -e "$log" || -L "$log" ]]; then
            echo "Refusing an existing run or log: $destination ; $log" >&2
            exit 2
        fi
    done
done
if ! "$dry_run"; then
    mkdir -p -- "$TMPDIR" "$log_root"
fi
for variant in "${variants[@]}"; do
    for seed in 0 1 2 3; do
        destination="$output_root/$variant/seed$seed"
        log="$log_root/${variant}_seed${seed}.log"
        command=("$python_bin" -B "$diagnostic_dir/shared_input_edge_variant.py"
                 --variant "$variant" --input_mode shared --seed "$seed" --epochs 35
                 --device "$device" --threads "$threads" --batch "$batch"
                 --output-dir "$destination")
        if "$dry_run"; then
            printf '%q ' "${command[@]}"
            printf '> %q 2>&1\n' "$log"
        else
            echo "Running $variant shared seed$seed on $device; log: $log"
            "${command[@]}" > "$log" 2>&1
        fi
    done
done
