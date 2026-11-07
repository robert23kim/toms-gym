#!/bin/bash
# run_dev.sh <tag> <run.py args...>   -> runs the 5 dev stems sequentially into work/<tag>/ and scores them (dev only)
set -u
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
HERE=$(cd "$(dirname "$0")" && pwd)
L2=$(cd "$HERE/../.." && pwd)
tag=$1; shift
for st in 20260915_185121_23d80f05 20260915_185331_19de9ec7 20260915_185454_f240c883 20260915_185645_9fde3c16 20260915_190115_a7cf2c70; do
  $PY "$HERE/run.py" "$st" "$@" --out-dir "$HERE/work/$tag" 2>&1 | tail -1 | sed 's#wrote .*json: ##'
done
$PY "$L2/score_all.py" "$HERE/work/$tag/tracks" "$HERE/work/$tag/dev.json" 2>&1 | grep -v '^wrote'
