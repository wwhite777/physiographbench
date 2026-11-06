#!/usr/bin/env bash
# Default/dry-run: 24 commands. Each run trains on A and evaluates A-test + B.
set -euo pipefail
EXPERIMENT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$EXPERIMENT_DIR/../.." && pwd)"
script_dir="experiments/learned_graph_validation"
scratch_root="${TMPDIR:-$repo_root/.scratch}"
cd -- "$repo_root"
export TMPDIR="${TMPDIR:-$EXPERIMENT_DIR/.scratch}"
export TMP="$TMPDIR" TEMP="$TMPDIR" PYTHONDONTWRITEBYTECODE=1
EXPERIMENT_PYTHON="${PYTHON:-python3}"
if [[ "${1:-}" == '--run' ]]; then
    shift
    EXPERIMENT_COMMANDS="$("$EXPERIMENT_PYTHON" -B "$EXPERIMENT_DIR/learned_adjacency_ablation.py" --grid "$@")"
    while IFS= read -r EXPERIMENT_COMMAND; do
        bash -c "$EXPERIMENT_COMMAND"
    done <<< "$EXPERIMENT_COMMANDS"
else
    if [[ "${1:-}" == '--dry-run' ]]; then shift; fi
    exec "$EXPERIMENT_PYTHON" -B "$EXPERIMENT_DIR/learned_adjacency_ablation.py" --grid "$@"
fi
