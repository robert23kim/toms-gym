#!/bin/zsh
# tracks + overlays for the holdout stems (no truth, no scoring)
D=/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking/experiments/cam-diff
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
mkdir -p $D/work/holdout_logs
for s in 20260915_191253_6cf2480f 20260915_191820_0196b564 20260915_191913_907c358b 20260915_192142_eeb210f6 20260915_192636_7c7fbfb0; do
  $PY $D/run.py $s "$@" > $D/work/holdout_logs/$s.log 2>&1
  echo "RC $? $s $(tail -1 $D/work/holdout_logs/$s.log)"
done
echo ALLDONE
