#!/usr/bin/env bash
cd "$(dirname "$0")"; mkdir -p ibench
WT=/Users/toka/code/bowling-app/perf-exp-cheaper-inference; FX=/Users/toka/code/bowling-app/perf-fixtures-2026-11-13
for f in squat_f47a8848.mov pushup_e18a31d1.mp4 situp_c9dec98b.mp4 situp_16b6ca35.mov; do
  (cd $WT && MPLBACKEND=Agg PYTHONPATH=$WT /Users/toka/code/bowling-app/analysis-engine/.venv/bin/python "$OLDPWD/ibench.py" --worktree $WT --fixture $FX/$f --out "$OLDPWD/ibench/${f%.*}.json" 2>>"$OLDPWD/ibench.err")
done
echo IBENCHDONE
