#!/usr/bin/env bash
# Back-to-back native A/B of the pose pass (screen.py --pose-only), arms interleaved per fixture, N rounds.
# Usage: timing.sh <rounds> ; appends one JSON line per run to timing.jsonl
set -uo pipefail
ROUNDS="${1:-3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
MINE=/Users/toka/code/bowling-app/perf-exp-cheaper-inference
BASE=/Users/toka/code/bowling-app/perf-engine
FX=/Users/toka/code/bowling-app/perf-fixtures-2026-11-13
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
export MPLBACKEND=Agg
run() { # arm worktree fixture round [ENV=VAL]
  local arm="$1" wt="$2" f="$3" r="$4"; shift 4
  local line
  line="$(cd "$wt" && env PYTHONPATH="$wt" "$@" "$PY" "$HERE/screen.py" --worktree "$wt" --fixture "$FX/$f" --out-dir "$HERE/timing-tmp" --pose-only 2>>"$HERE/timing.err" | tail -1)"
  echo "{\"arm\":\"$arm\",\"round\":$r,\"run\":$line}" >> "$HERE/timing.jsonl"
  echo "$arm r$r $f $(echo "$line" | cut -c1-110)"
}
for r in $(seq 1 "$ROUNDS"); do
  for f in squat_f47a8848.mov pushup_e18a31d1.mp4 situp_c9dec98b.mp4; do
    run base93378b0 "$BASE" "$f" "$r"
    run flag-off "$MINE" "$f" "$r"
    run np1 "$MINE" "$f" "$r" POSE_NUM_POSES=1
    run stride2 "$MINE" "$f" "$r" POSE_FRAME_STRIDE=2
    run side640 "$MINE" "$f" "$r" POSE_MAX_SIDE=640
    if [ "$r" = 1 ]; then
      run np3 "$MINE" "$f" "$r" POSE_NUM_POSES=3
      run np2 "$MINE" "$f" "$r" POSE_NUM_POSES=2
    fi
  done
done
echo TIMINGDONE
