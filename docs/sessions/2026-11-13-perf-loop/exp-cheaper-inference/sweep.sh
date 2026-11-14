#!/usr/bin/env bash
# Usage: sweep.sh <tag> "<fixture names or 'all'>" [ENV=VAL ...]; native screen, sequential.
set -uo pipefail
TAG="$1"; WHICH="$2"; shift 2
HERE="$(cd "$(dirname "$0")" && pwd)"
WT="${WT:-/Users/toka/code/bowling-app/perf-exp-cheaper-inference}"
FX=/Users/toka/code/bowling-app/perf-fixtures-2026-11-13
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
OUT="$HERE/screen/$TAG"; mkdir -p "$OUT"
for kv in "$@"; do export "$kv"; done
export MPLBACKEND=Agg PYTHONPATH="$WT"
cd "$WT"
if [ "$WHICH" = all ]; then WHICH="squat_f47a8848.mov pushup_3c66c85e.mov pushup_97b4aaf2.mp4 pushup_e18a31d1.mp4 situp_16b6ca35.mov situp_667a8480.mp4 situp_c9dec98b.mp4"; fi
for f in $WHICH; do
  n="${f%.*}"
  if "$PY" "$HERE/screen.py" --worktree "$WT" --fixture "$FX/$f" --out-dir "$OUT" > "$OUT/$n.log" 2>&1; then
    echo "ok $TAG $n $(tail -1 "$OUT/$n.log" | cut -c1-260)"
  else
    echo "FAILED $TAG $n"; tail -5 "$OUT/$n.log"
  fi
done
echo ALLDONE $TAG
