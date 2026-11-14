#!/usr/bin/env bash
cd "$(dirname "$0")"; mkdir -p ibench-np
WT=/Users/toka/code/bowling-app/perf-exp-cheaper-inference; FX=/Users/toka/code/bowling-app/perf-fixtures-2026-11-13
export IBENCH_ARMS=off,off2,np3,np2,np1
for f in situp_667a8480.mp4 pushup_e18a31d1.mp4 squat_f47a8848.mov; do
  (cd $WT && MPLBACKEND=Agg PYTHONPATH=$WT /Users/toka/code/bowling-app/analysis-engine/.venv/bin/python "$OLDPWD/ibench.py" --worktree $WT --fixture $FX/$f --out "$OLDPWD/ibench-np/${f%.*}.json" 2>/dev/null)
done
echo IBENCHNPDONE
unset IBENCH_ARMS
./sweep.sh np3 "situp_667a8480.mp4 pushup_e18a31d1.mp4 situp_c9dec98b.mp4 squat_f47a8848.mov" POSE_NUM_POSES=3
