#!/usr/bin/env bash
# Prod-image (emulated amd64) sweep for the non-pose experiment, strictly sequential.
# Round 1: every fixture, A (flags off) then B (flags on). Rounds 2-3: base image code, A, B on 3 fixtures.
set -uo pipefail
H="$(cd "$(dirname "$0")" && pwd)"
FX=/Users/toka/code/bowling-app/perf-fixtures-2026-11-13
WT=/Users/toka/code/bowling-app/perf-exp-non-pose
O=/Users/toka/code/bowling-app/perf-out-non-pose/img
PROD=(PLANK_POSE_WORKERS=8 NORMALIZE_BEFORE_ANALYZE=true)
ON=(LIFT_VIDEO_ENCODER=ffmpeg SKIP_METRIC_CLIPS_FOR=pushup,situp)
run() { # cfg round fixture
  local cfg=$1 r=$2 f=$3 n; n="$(basename "${f%.*}")"; local out="$O/$cfg-r$r"; mkdir -p "$out"
  case $cfg in
    base) "$H/run_prod_image.sh" "$f" "$out" "${PROD[@]}" > "$out/$n.log" 2>&1;;
    A) WORKTREE=$WT "$H/run_prod_image.sh" "$f" "$out" "${PROD[@]}" > "$out/$n.log" 2>&1;;
    B) WORKTREE=$WT "$H/run_prod_image.sh" "$f" "$out" "${PROD[@]}" "${ON[@]}" > "$out/$n.log" 2>&1;;
  esac
  echo "$(date +%H:%M:%S) $cfg r$r $n rc=$? $(tail -1 "$out/$n.log" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["wall_s"],d["stages"],d["analyze_breakdown"])' 2>&1 | tail -1)" >> "$O/sweep.progress"
}
KEY=(squat_f47a8848.mov pushup_e18a31d1.mp4 situp_667a8480.mp4)
REST=(pushup_3c66c85e.mov pushup_97b4aaf2.mp4 situp_16b6ca35.mov situp_c9dec98b.mp4 plank_9600f455.mp4)
for f in "${KEY[@]}" "${REST[@]}"; do run A 1 "$FX/$f"; run B 1 "$FX/$f"; done
echo ROUND1DONE >> "$O/sweep.progress"
for r in 2 3; do for f in "${KEY[@]}"; do run base $r "$FX/$f"; run A $r "$FX/$f"; run B $r "$FX/$f"; done; done
echo ALLDONE >> "$O/sweep.progress"
