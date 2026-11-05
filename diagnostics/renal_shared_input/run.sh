#!/usr/bin/env bash
# Eight fixed-configuration fits, with no edges and no input-mode retuning.
set -euo pipefail
set -C
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd -- "$repo_root"
diagnostic_dir="diagnostics/renal_shared_input"
python_bin="${PYTHON:-python3}"
device="cpu"
threads=2
batch=128
output_root="runs/renal_shared_input"
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
        --dry-run|--plan) dry_run=true; shift ;;
        --help)
            echo "Usage: $0 [--device cpu|cuda] [--threads 2] [--batch 128] [--output-root PATH] [--dry-run|--plan]"
            exit 0 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
case "$device" in
    cpu|cuda) ;;
    *) echo "Device must be cpu or cuda" >&2; exit 2 ;;
esac
case "$threads:$batch" in
    *[!0-9:]*|0:*|*:0|:*|*:) echo "Threads and batch must be positive integers" >&2; exit 2 ;;
esac
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
if ! "$dry_run"; then
    # Preflight every destination before the first fit; never overwrite runs/logs.
    for input_mode in partitioned shared; do
        for seed in 0 1 2 3; do
            destination="$output_root/$input_mode/seed$seed"
            log="$log_root/${input_mode}_seed${seed}.log"
            if [[ -e "$destination" || -e "$log" ]]; then
                echo "Refusing an existing run or log: $destination ; $log" >&2
                exit 2
            fi
        done
    done
    mkdir -p -- "$TMPDIR" "$log_root"
fi
for input_mode in partitioned shared; do
    for seed in 0 1 2 3; do
        destination="$output_root/$input_mode/seed$seed"
        log="$log_root/${input_mode}_seed${seed}.log"
        command=("$python_bin" -B "$diagnostic_dir/shared_input_variant.py"
                 --input_mode "$input_mode" --seed "$seed" --epochs 35
                 --device "$device" --threads "$threads" --batch "$batch"
                 --output-dir "$destination")
        if "$dry_run"; then
            printf '%q ' "${command[@]}"
            printf '> %q 2>&1\n' "$log"
        else
            echo "Running $input_mode seed$seed on $device; log: $log"
            "${command[@]}" > "$log" 2>&1
        fi
    done
done
