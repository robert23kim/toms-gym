#!/bin/bash
# Alternating A/B bench of two bowling-service-perf tags in one sitting.
# Usage: bench_ab.sh <base-url> <cand-url> <outdir> [runs=2] [fixture ...]
# Per round k, per fixture: base then cand (odd k) or cand then base (even k), sequential.
# Attempt ids perf-bench-<fixture>-<tag>-ab-r<k>. Writes <outdir>/<tag>/<fixture>.r<k>.json,
# <outdir>/<tag>/bench.tsv and <outdir>/<tag>/instances.tsv (attempt -> Cloud Run instance).
set -u
B=${1:?base url}; C=${2:?cand url}; OUT=${3:?outdir}; RUNS=${4:-2}; shift 4 2>/dev/null || shift $#
for u in "$B" "$C"; do case "$u" in https://*---bowling-service-perf-*.run.app) ;; *) echo "REFUSED: $u" >&2; exit 2;; esac; done
BUCKET=jtr-lift-u-4ever-cool-bucket
FIXTURES=("$@")
[ ${#FIXTURES[@]} -eq 0 ] && FIXTURES=(squat_f47a8848.mov pushup_3c66c85e.mov pushup_97b4aaf2.mp4 pushup_e18a31d1.mp4 situp_16b6ca35.mov situp_667a8480.mp4 situp_c9dec98b.mp4 plank_9600f455.mp4)
tag() { local h=${1#https://}; echo "${h%%---*}"; }
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
for u in "$B" "$C"; do
  t=$(tag "$u"); mkdir -p "$OUT/$t"
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$u/health")
  [ "$code" = 200 ] || { echo "CANARY FAIL: $u/health -> $code" >&2; exit 3; }
  w=$(curl -s -o "$OUT/$t/warmup.json" -w '%{http_code}' --max-time 900 -X POST -H "Authorization: Bearer $(gcloud auth print-identity-token)" -H 'Content-Type: application/json' \
    -d "{\"video_url\":\"https://storage.googleapis.com/$BUCKET/perf-bench/squat_f47a8848.mov\",\"attempt_id\":\"perf-bench-warmup-$t-ab\",\"lift_type\":\"squat\"}" "$u/analyze-lift")
  echo "warmup $t http=$w"
  [ -f "$OUT/$t/bench.tsv" ] || printf 'fixture\trun\thttp\tclient_wall_s\tprocessing_time_s\tdownload_s\tanalyze_s\treencode_s\tupload_s\tclips_s\ttotal_reps\tplank_hold_s\n' > "$OUT/$t/bench.tsv"
done
one() { # url fixture k
  local u=$1 f=$2 k=$3 t name lift aid body t0 t1 http
  t=$(tag "$u"); name=${f%.*}; lift=${name%%_*}; aid="perf-bench-${name}-${t}-ab-r${k}"
  body=$(printf '{"video_url":"https://storage.googleapis.com/%s/perf-bench/%s","attempt_id":"%s","lift_type":"%s"}' "$BUCKET" "$f" "$aid" "$lift")
  t0=$(python3 -c 'import time;print(time.time())')
  http=$(curl -s -o "$OUT/$t/$name.r$k.json" -w '%{http_code}' --max-time 900 -X POST \
    -H "Authorization: Bearer $(gcloud auth print-identity-token)" -H 'Content-Type: application/json' -d "$body" "$u/analyze-lift")
  t1=$(python3 -c 'import time;print(time.time())')
  python3 - "$OUT/$t/$name.r$k.json" "$name" "$k" "$http" "$t0" "$t1" >> "$OUT/$t/bench.tsv" <<'PY'
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
  echo "$(date +%H:%M:%S) $t $(tail -1 "$OUT/$t/bench.tsv")"
}
for k in $(seq 1 "$RUNS"); do
  for f in "${FIXTURES[@]}"; do
    if [ $((k % 2)) -eq 1 ]; then one "$B" "$f" "$k"; one "$C" "$f" "$k"; else one "$C" "$f" "$k"; one "$B" "$f" "$k"; fi
  done
done
for u in "$B" "$C"; do
  t=$(tag "$u")
  REV=$(gcloud run services describe bowling-service-perf --project toms-gym --region us-east1 --format=json | python3 -c "import json,sys;t=sys.argv[1];print(next(x['revisionName'] for x in json.load(sys.stdin)['status']['traffic'] if x.get('tag')==t))" "$t")
  gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"bowling-service-perf\" AND resource.labels.revision_name=\"$REV\" AND textPayload:\"ANALYSIS_STAGES\" AND timestamp>=\"$START\"" \
    --project toms-gym --limit 200 --format='value(timestamp,labels.instanceId,textPayload)' \
    | awk '{for(i=1;i<=NF;i++) if($i ~ /^attempt=/) print $1"\t"$2"\t"substr($i,9)}' | sort > "$OUT/$t/instances.tsv"
  echo "$t rev=$REV instances: $(cut -f2 "$OUT/$t/instances.tsv" | sort -u | wc -l | tr -d ' ')"
done
echo "START=$START"
echo BENCHDONE
