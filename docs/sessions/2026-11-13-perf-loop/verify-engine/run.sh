#!/bin/bash
# Verifier's own cand/base run: one fixture per lift type, alternating, fresh perf-bench-*-verify ids.
set -u
OUT=/Users/toka/code/toms_gym-perf/docs/sessions/2026-11-13-perf-loop/verify-engine/run
BUCKET=jtr-lift-u-4ever-cool-bucket
C=https://perf-cand---bowling-service-perf-quyiiugyoq-ue.a.run.app
B=https://perf-base---bowling-service-perf-quyiiugyoq-ue.a.run.app
for u in "$C" "$B"; do case "$u" in https://*---bowling-service-perf-*.run.app) ;; *) echo REFUSED; exit 2;; esac
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$u/health"); echo "health $u $code"; [ "$code" = 200 ] || exit 3; done
one() { local u=$1 f=$2 t=$3 name=${2%.*}; local lift=${name%%_*}; local aid="perf-bench-${name}-${t}-verify-r1"
  local http=$(curl -s -o "$OUT/$t.$name.json" -w '%{http_code}' --max-time 900 -X POST -H "Authorization: Bearer $(gcloud auth print-identity-token)" -H 'Content-Type: application/json' \
    -d "{\"video_url\":\"https://storage.googleapis.com/$BUCKET/perf-bench/$f\",\"attempt_id\":\"$aid\",\"lift_type\":\"$lift\"}" "$u/analyze-lift")
  echo "$(date -u +%H:%M:%S) $t $name http=$http $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d.get('processing_time_s'),d.get('stages'))" "$OUT/$t.$name.json" 2>&1)"; }
date -u +START=%Y-%m-%dT%H:%M:%SZ
one "$C" squat_f47a8848.mov cand  # warm
for f in squat_f47a8848.mov pushup_e18a31d1.mp4 situp_667a8480.mp4 plank_9600f455.mp4; do one "$C" $f cand; one "$B" $f base; done
echo RUNDONE
