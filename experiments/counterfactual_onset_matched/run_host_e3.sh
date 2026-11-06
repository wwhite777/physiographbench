#!/usr/bin/env bash
# E3 host plan. This worker only executes --dry-run, tests and small CPU smoke.
set -euo pipefail
set -C
task_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$task_dir/../.." && pwd)"
script_dir="experiments/counterfactual_onset_matched"
scratch_root="${TMPDIR:-$repo_root/.scratch}"
cd -- "$repo_root"
python_bin="${PYTHON:-python3}"
output_root="$task_dir/runs/host"
group=core
threads=1
dry_run=false
while (($#)); do
    case "$1" in
        --output-root|--group|--threads)
            if (($# < 2)); then echo "Missing value for $1" >&2; exit 2; fi
            case "$1" in
                --output-root) output_root="$2" ;;
                --group) group="$2" ;;
                --threads) threads="$2" ;;
            esac
            shift 2 ;;
        --dry-run) dry_run=true; shift ;;
        --help)
            echo "Usage: $0 [--group core|main|crn-diagnostic|matched-control|lite-lambda|temporal|legacy|all] [--threads 1] [--output-root PATH] [--dry-run]"
            exit 0 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
case "$group" in
    core|main|crn-diagnostic|matched-control|lite-lambda|temporal|legacy|all) ;;
    *) echo "Unknown group: $group" >&2; exit 2 ;;
esac
if [[ ! "$threads" =~ ^[1-9][0-9]*$ ]]; then echo "Threads must be positive" >&2; exit 2; fi
output_root="$(realpath -m -- "$output_root")"
case "$output_root/" in
    "$task_dir/"*|"$scratch_root/"*) ;;
    *) echo "Output root must stay inside counterfactual experiment workspace" >&2; exit 2 ;;
esac
export TMPDIR="${TMPDIR:-$task_dir/.scratch}"
export TMP="$TMPDIR" TEMP="$TMPDIR" PYTHONDONTWRITEBYTECODE=1

# Build and preflight the whole plan before starting any fit or creating outputs.
commands=()
destinations=()
logs=()
add_run() {
    local relative="$1"
    shift
    local destination
    destination="$(realpath -m -- "$output_root/$relative")"
    case "$destination/" in
        "$task_dir/"*|"$scratch_root/"*) ;;
        *) echo "Run path escapes counterfactual experiment workspace: $destination" >&2; exit 2 ;;
    esac
    destination="${destination#"$repo_root/"}"
    local log="$destination.log"
    if [[ -e "$destination" || -L "$destination" || -e "$log" || -L "$log" ]]; then
        echo "Refusing existing run or log: $destination ; $log" >&2; exit 2
    fi
    local command
    printf -v command '%q ' "$python_bin" -B "$script_dir/sim_grid_runner3.py" \
        --output-dir "$destination" --threads "$threads" --n_patients 400 \
        --dataset_seed 0 --C 12 --K 24 "$@"
    commands+=("$command")
    destinations+=("$destination")
    logs+=("$log")
}
if [[ "$group" == core || "$group" == main || "$group" == all || "$group" == temporal ]]; then
    protocol=onset_matched
    label=main
    if [[ "$group" == temporal ]]; then protocol=temporal_extrapolation; label=temporal; fi
    for family in support_only dependence_only; do
        for point in 0 1 2 3 4; do
            for model in control_gru crn_lite physiograph_gru physiograph; do
                for seed in 0 1 2 3; do
                    add_run "$label/$family/point$point/$model/seed$seed" \
                        --family "$family" --point "$point" --model "$model" --seed "$seed" \
                        --epochs 60 --lamb 0.5 --cf_protocol "$protocol"
                done
            done
        done
    done
fi
if [[ "$group" == core || "$group" == crn-diagnostic || "$group" == all ]]; then
    for lamb in 0 0.25 1; do
        for epochs in 60 120; do
            for seed in 0 1 2 3; do
                add_run "crn_diagnostic/lambda$lamb/epochs$epochs/seed$seed" \
                    --family legacy --confound 0 --sigma 0 --model crn_continuous \
                    --seed "$seed" --epochs "$epochs" --lamb "$lamb" --cf_protocol onset_matched
            done
        done
    done
fi
if [[ "$group" == matched-control ]]; then
    for seed in 0 1 2 3; do
        add_run "crn_diagnostic/control_gru/seed$seed" \
            --family legacy --confound 0 --sigma 0 --model control_gru \
            --seed "$seed" --epochs 60 --lamb 0.5 --cf_protocol onset_matched
    done
fi
if [[ "$group" == lite-lambda || "$group" == all ]]; then
    for family in support_only dependence_only; do
        for point in 0 1 2 3 4; do
            for lamb in 0 0.25 1; do
                for seed in 0 1 2 3; do
                    add_run "lite_lambda/$family/point$point/lambda$lamb/seed$seed" \
                        --family "$family" --point "$point" --model crn_lite --seed "$seed" \
                        --epochs 60 --lamb "$lamb" --cf_protocol onset_matched
                done
            done
        done
    done
fi
if [[ "$group" == legacy ]]; then
    for confound in 0 0.1 0.25 0.5 0.75 1; do
        for sigma in 0 0.08 0.15 0.25; do
            for model in control_gru crn_lite physiograph_gru physiograph; do
                for seed in 0 1 2 3; do
                    add_run "legacy_policy/c$confound/sigma$sigma/$model/seed$seed" \
                        --family legacy --confound "$confound" --sigma "$sigma" --model "$model" \
                        --seed "$seed" --epochs 60 --lamb 0.5 --cf_protocol onset_matched
                done
            done
        done
    done
fi
echo "# E3 group=$group fits=${#commands[@]} device=cpu" >&2
for i in "${!commands[@]}"; do
    if "$dry_run"; then
        printf '%s> %q 2>&1\n' "${commands[$i]}" "${logs[$i]}"
    else
        mkdir -p -- "$TMPDIR" "$(dirname -- "${destinations[$i]}")"
        echo "Running ${destinations[$i]}; log ${logs[$i]}" >&2
        # Each argument was shell-quoted by printf %q above; no unquoted user text.
        eval "${commands[$i]}" > "${logs[$i]}" 2>&1
    fi
done
