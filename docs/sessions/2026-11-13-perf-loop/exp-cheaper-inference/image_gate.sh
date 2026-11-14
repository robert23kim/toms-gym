#!/usr/bin/env bash
# Prod-image acceptance gate (emulated amd64, prod deps, class-A reference): variant worktree mounted
# over /app, compared against ../base-image. Usage: image_gate.sh <tag> "<fixtures|all>" [ENV=VAL ...]
set -uo pipefail
TAG="$1"; WHICH="$2"; shift 2
HERE="$(cd "$(dirname "$0")" && pwd)"; H="$HERE/../harness"
FX=/Users/toka/code/bowling-app/perf-fixtures-2026-11-13
export WORKTREE=/Users/toka/code/bowling-app/perf-exp-cheaper-inference
OUT="$HERE/image/$TAG"; mkdir -p "$OUT"
if [ "$WHICH" = all ]; then WHICH="squat_f47a8848.mov pushup_3c66c85e.mov pushup_97b4aaf2.mp4 pushup_e18a31d1.mp4 situp_16b6ca35.mov situp_667a8480.mp4 situp_c9dec98b.mp4 plank_9600f455.mp4"; fi
for f in $WHICH; do
  n="${f%.*}"
  if "$H/run_prod_image.sh" "$FX/$f" "$OUT" PLANK_POSE_WORKERS=8 NORMALIZE_BEFORE_ANALYZE=true "$@" > "$OUT/$n.log" 2>&1; then
    v="$(python3 "$H/compare.py" "$H/../base-image/$n.summary.json" "$OUT/$n.summary.json" | tail -1 | sed "s#$HERE/##g;s#$H/../##g")"
    echo "ok $TAG $n :: $v :: $(tail -1 "$OUT/$n.log" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["wall_s"],d["analyze_breakdown"],d["total_reps"],d["code_hash"])')"
  else
    echo "FAILED $TAG $n"; tail -3 "$OUT/$n.log"
  fi
done
echo GATEDONE $TAG
