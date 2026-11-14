#!/usr/bin/env bash
# Usage: run_all.sh <worktree> <out_dir> [ENV=VAL ...]  - every fixture, sequentially.
set -uo pipefail
WT="$1"; OUT="$2"; shift 2
HERE="$(cd "$(dirname "$0")" && pwd)"
FX="${FIXTURES:-/Users/toka/code/bowling-app/perf-fixtures-2026-11-13}"
mkdir -p "$OUT"
for f in "$FX"/*.mp4 "$FX"/*.mov; do
  [ -e "$f" ] || continue
  n="$(basename "${f%.*}")"
  if "$HERE/run_local.sh" "$WT" "$f" "$OUT" "$@" > "$OUT/$n.log" 2>&1; then
    echo "ok $n $(tail -1 "$OUT/$n.log" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["wall_s"],d["stages"])')"
  else
    echo "FAILED $n (see $OUT/$n.log)"
  fi
done
echo ALLDONE
