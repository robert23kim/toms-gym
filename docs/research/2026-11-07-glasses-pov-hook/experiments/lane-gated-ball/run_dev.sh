#!/bin/bash
# run_dev.sh [stem...]: run.py + score_v2 per stem sequentially (one torch process at a time), then results/dev.json.
set -e
X=/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook/experiments/lane-gated-ball
L2=/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
STEMS=${*:-"20260915_185121_23d80f05 20260915_185331_19de9ec7 20260915_185454_f240c883 20260915_185645_9fde3c16 20260915_190115_a7cf2c70"}
cd "$X"
for s in $STEMS; do
  $PY run.py "$s" --device mps 2>&1 | grep -v Warning | tail -1
  $PY "$L2/score_v2.py" "tracks/$s.json" "$L2/truth/$s.json"
done
$PY "$L2/score_all.py" tracks results/dev.json
