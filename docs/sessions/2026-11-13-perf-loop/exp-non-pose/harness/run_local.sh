#!/usr/bin/env bash
# Usage: run_local.sh <worktree> <fixture.mp4|mov> <out_dir> [ENV=VAL ...]
# Lift type comes from the fixture name prefix (situp_/pushup_/squat_/plank_);
# override with LIFT_TYPE=<type>. Writes <out_dir>/<name>.summary.json and .timing.json.
set -euo pipefail
WT="$1"; FIX="$2"; OUT="$3"; shift 3
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${ENGINE_PY:-/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python}"
PERF_FLAGS=""
for kv in "$@"; do export "$kv"; PERF_FLAGS="$PERF_FLAGS ${kv%%=*}"; done
export PERF_FLAGS
export MPLBACKEND=Agg
export PYTHONPATH="$WT"
cd "$WT"
exec "$PY" "$HERE/run_local.py" --worktree "$WT" --fixture "$FIX" --out-dir "$OUT" ${LIFT_TYPE:+--lift-type "$LIFT_TYPE"}
