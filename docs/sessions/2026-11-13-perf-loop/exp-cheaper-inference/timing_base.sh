#!/usr/bin/env bash
# base worktree (93378b0) vs this branch with every flag unset: process-level ABAB, pose pass only.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MINE=/Users/toka/code/bowling-app/perf-exp-cheaper-inference; BASE=/Users/toka/code/bowling-app/perf-engine
FX=/Users/toka/code/bowling-app/perf-fixtures-2026-11-13; PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
export MPLBACKEND=Agg
run() { local arm="$1" wt="$2" f="$3" r="$4"; local line
  line="$(cd "$wt" && PYTHONPATH="$wt" "$PY" "$HERE/screen.py" --worktree "$wt" --fixture "$FX/$f" --out-dir "$HERE/timing-tmp" --pose-only 2>>"$HERE/timing.err" | tail -1)"
  echo "{\"arm\":\"$arm\",\"round\":$r,\"run\":$line}" >> "$HERE/timing-base-vs-off.jsonl"; }
for r in 1 2 3 4; do
  for f in squat_f47a8848.mov pushup_e18a31d1.mp4 situp_c9dec98b.mp4; do
    if [ $((r % 2)) = 1 ]; then run base93378b0 "$BASE" "$f" "$r"; run flag-off "$MINE" "$f" "$r"; else run flag-off "$MINE" "$f" "$r"; run base93378b0 "$BASE" "$f" "$r"; fi
  done
done
echo BASEDONE
