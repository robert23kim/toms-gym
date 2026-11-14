#!/bin/bash
# Bench a bowling-service-perf tagged revision on the perf-bench fixtures.
# Usage: bench_cloudrun.sh <tag-url> <outdir> [runs=2] [fixture-name ...]
# Sequential calls (concurrency 1), attempt ids perf-bench-<fixture>-<tag>-r<k>.
# Writes <outdir>/<fixture>.r<k>.json (full response), <outdir>/bench.tsv and
# <outdir>/compare.txt (vs prod JSON and vs base-image summary). Refuses any URL
# that is not a bowling-service-perf URL.
set -u
URL=${1:?tag url}; OUT=${2:?outdir}; RUNS=${3:-2}; shift 3 2>/dev/null || shift $#
case "$URL" in https://*bowling-service-perf-*.run.app) ;; *) echo "REFUSED: $URL is not a bowling-service-perf URL" >&2; exit 2;; esac
H=$(cd "$(dirname "$0")" && pwd)
FX=/Users/toka/code/bowling-app/perf-fixtures-2026-11-13
BUCKET=jtr-lift-u-4ever-cool-bucket
FIXTURES=("$@")
[ ${#FIXTURES[@]} -eq 0 ] && FIXTURES=(squat_f47a8848.mov pushup_3c66c85e.mov pushup_97b4aaf2.mp4 pushup_e18a31d1.mp4 situp_16b6ca35.mov situp_667a8480.mp4 situp_c9dec98b.mp4 plank_9600f455.mp4)
HOST=${URL#https://}; TAG=latest; case "$HOST" in *---*) TAG=${HOST%%---*};; esac
mkdir -p "$OUT"
TOKEN=$(gcloud auth print-identity-token)
# canary for the instrument: health must answer 200 before any timing counts
code=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" "$URL/health")
[ "$code" = 200 ] || { echo "CANARY FAIL: $URL/health -> $code" >&2; exit 3; }
# warm-up: the first analyze on an instance pays the lazy mediapipe/model import (~5 s); discarded
curl -s -o "$OUT/warmup.json" --max-time 900 -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"video_url\":\"https://storage.googleapis.com/$BUCKET/perf-bench/squat_f47a8848.mov\",\"attempt_id\":\"perf-bench-warmup-$TAG\",\"lift_type\":\"squat\"}" "$URL/analyze-lift"
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
[ -f "$OUT/bench.tsv" ] || printf 'fixture\trun\thttp\tclient_wall_s\tprocessing_time_s\tdownload_s\tanalyze_s\treencode_s\tupload_s\tclips_s\ttotal_reps\tplank_hold_s\n' > "$OUT/bench.tsv"
for k in $(seq 1 "$RUNS"); do
  for f in "${FIXTURES[@]}"; do
    name=${f%.*}; lift=${name%%_*}
    aid="perf-bench-${name}-${TAG}-r${k}"
    body=$(printf '{"video_url":"https://storage.googleapis.com/%s/perf-bench/%s","attempt_id":"%s","lift_type":"%s"}' "$BUCKET" "$f" "$aid" "$lift")
    t0=$(python3 -c 'import time;print(time.time())')
    http=$(curl -s -o "$OUT/$name.r$k.json" -w '%{http_code}' --max-time 900 -X POST \
      -H "Authorization: Bearer $(gcloud auth print-identity-token)" -H 'Content-Type: application/json' \
      -d "$body" "$URL/analyze-lift")
    t1=$(python3 -c 'import time;print(time.time())')
    python3 - "$OUT/$name.r$k.json" "$name" "$k" "$http" "$t0" "$t1" >> "$OUT/bench.tsv" <<'PY'
import json, sys
p, name, k, http, t0, t1 = sys.argv[1:]
try:
    d = json.load(open(p))
except Exception:
    d = {}
s = d.get("stages") or {}; r = d.get("report") or {}
row = [name, k, http, f"{float(t1)-float(t0):.2f}", d.get("processing_time_s"), s.get("download"), s.get("analyze"),
       s.get("reencode"), s.get("upload"), s.get("clips"), r.get("total_reps"), r.get("total_in_plank_s")]
print("\t".join("" if v is None else str(v) for v in row))
PY
    tail -1 "$OUT/bench.tsv"
    {
      echo "== $name r$k vs prod"; python3 "$H/compare.py" "$FX/$name.prod.json" "$OUT/$name.r$k.json"; echo "exit=$?"
      echo "== $name r$k vs base-image"; python3 "$H/compare.py" "$H/../base-image/$name.summary.json" "$OUT/$name.r$k.json"; echo "exit=$?"
    } >> "$OUT/compare.txt" 2>&1
  done
done
# Join each attempt to the Cloud Run instance that served it. Results differ by host class
# (see baseline.md): compare a candidate only against base runs from the same class.
REV=$(gcloud run services describe bowling-service-perf --project toms-gym --region us-east1 --format=json | python3 -c "import json,sys;t=sys.argv[1];print(next(x['revisionName'] for x in json.load(sys.stdin)['status']['traffic'] if x.get('tag')==t))" "$TAG")
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"bowling-service-perf\" AND resource.labels.revision_name=\"$REV\" AND textPayload:\"ANALYSIS_STAGES\" AND timestamp>=\"$START\"" \
  --project toms-gym --limit 200 --format='value(timestamp,labels.instanceId,textPayload)' \
  | awk '{for(i=1;i<=NF;i++) if($i ~ /^attempt=/) print $1"\t"$2"\t"substr($i,9)}' | sort > "$OUT/instances.tsv"
echo "instances: $(cut -f2 "$OUT/instances.tsv" | sort -u | wc -l | tr -d ' ') (see instances.tsv)"
echo BENCHDONE
