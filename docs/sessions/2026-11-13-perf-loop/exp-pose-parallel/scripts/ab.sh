#!/usr/bin/env bash
# Usage: ab.sh <outdir> <reps> <arms: comma list of base,off,w2,w3,w4> <fixture ...>
# Back-to-back arms per fixture per rep, sequential. Timing from the harness timing.json.
set -uo pipefail
OUT="$1"; REPS="$2"; ARMS="$3"; shift 3
H=/Users/toka/code/toms_gym-perf/docs/sessions/2026-11-13-perf-loop/harness
WT=/Users/toka/code/bowling-app/perf-exp-pose-parallel
BASE=/Users/toka/code/bowling-app/perf-engine
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$OUT"
for rep in $(seq 1 "$REPS"); do
  for f in "$@"; do
    n="$(basename "${f%.*}")"
    for arm in ${ARMS//,/ }; do
      d="$OUT/$arm-r$rep"; mkdir -p "$d"
      case "$arm" in
        base) cmd=("$H/run_local.sh" "$BASE" "$f" "$d") ;;
        off)  cmd=("$H/run_local.sh" "$WT" "$f" "$d") ;;
        w*)   cmd=("$H/run_local.sh" "$WT" "$f" "$d" "LIFT_POSE_WORKERS=${arm#w}") ;;
      esac
      if /usr/bin/time -l "${cmd[@]}" > "$d/$n.log" 2>&1; then
        echo "ok rep=$rep $n $arm $(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print("pose",d["analyze_breakdown"].get("pose"),"analyze",d["stages"].get("analyze"),"wall",d["wall_s"],"reps",d["total_reps"])' "$d/$n.timing.json") parallel=$(grep -c 'LIFT_POSE_PARALLEL' "$d/$n.log")"
      else
        echo "FAILED rep=$rep $n $arm (see $d/$n.log)"
      fi
    done
  done
done
echo ABDONE
