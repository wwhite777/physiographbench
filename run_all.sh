#!/usr/bin/env bash
set -euo pipefail
RELEASE_DIR="${PHYSIOGRAPH_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}"
cd -- "$RELEASE_DIR"
export TMPDIR="${TMPDIR:-$RELEASE_DIR/.scratch}"
export PYTHONDONTWRITEBYTECODE=1
exec "${PYTHON:-python3}" -B tools/run_experiments.py --suite all "$@"
