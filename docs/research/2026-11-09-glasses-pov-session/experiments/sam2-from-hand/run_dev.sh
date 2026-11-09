#!/bin/zsh
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
X=/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session/experiments/sam2-from-hand
STEMS=(20261108_104946_3b1b2308 20261108_105652_31fc9b5e 20261108_110442_d27f6c73 20261108_111631_9c1e9211 20261108_112800_0c01c7c1 20261108_113911_e5c680e6 20261108_114631_01d562c5 20261108_115157_0e03a53c)
[[ $# -gt 0 ]] && STEMS=("$@")
for s in $STEMS; do
  echo "=== $s $(date +%H:%M:%S)"
  $PY $X/run.py $s --device mps 2>&1 | grep --line-buffered -v -i warning | grep --line-buffered -v Ultralytics
done
echo "=== DONE $(date +%H:%M:%S)"
