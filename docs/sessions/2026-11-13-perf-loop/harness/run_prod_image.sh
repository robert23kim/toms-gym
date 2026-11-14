#!/usr/bin/env bash
# Usage: run_prod_image.sh <fixture> <out_dir> [ENV=VAL ...]
# Runs run_local.py inside the exact prod engine image (rev 00053 digest) as linux/amd64,
# against the image's own /app code. This is the prod-parity instrument on the laptop.
set -euo pipefail
FIX="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; OUT="$2"; shift 2
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
IMG="${ENGINE_IMAGE:-gcr.io/toms-gym/bowling-service@sha256:e3acfcbdd12b8b97ebd5eec9e9c7555b988c645f178538e00d20db8095058c47}"
envargs=(-e MPLBACKEND=Agg); flags=""
for kv in "$@"; do envargs+=(-e "$kv"); flags="$flags ${kv%%=*}"; done
mounts=()
if [ -n "${WORKTREE:-}" ]; then mounts=(-v "$WORKTREE/src:/app/src:ro" -v "$WORKTREE/service:/app/service:ro"); fi
exec docker run --rm --platform linux/amd64 --cpus "${DOCKER_CPUS:-4}" \
  -v "$HERE:/harness:ro" -v "$(dirname "$FIX"):/fixtures:ro" -v "$OUT:/out" "${mounts[@]+"${mounts[@]}"}" \
  -e PERF_FLAGS="$flags" "${envargs[@]}" --entrypoint python "$IMG" \
  /harness/run_local.py --worktree /app --fixture "/fixtures/$(basename "$FIX")" --out-dir /out
