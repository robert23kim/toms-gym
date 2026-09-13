#!/usr/bin/env bash
# Publish the built debug APK behind a backend short link for on-phone install.
# Each build goes to its own object name: GCS edge-caches a re-uploaded object
# for an hour, so reusing one name hands out the previous APK.
set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APK="${1:-$FRONTEND_DIR/tomsgym-debug.apk}"
BUCKET="${APK_BUCKET:-jtr-lift-u-4ever-cool-bucket}"
KEY="${APK_SIGN_KEY:-$FRONTEND_DIR/../backend/credentials.json}"
BACKEND="${API_URL:-https://my-python-backend-quyiiugyoq-ue.a.run.app}"

[ -f "$APK" ] || { echo "no APK at $APK (run npm run android:build)"; exit 1; }
[ -f "$KEY" ] || { echo "no signing key at $KEY"; exit 1; }

STAMP=$(date +%Y%m%d-%H%M%S)
OBJ="gs://$BUCKET/apk/tomsgym-debug-$STAMP.apk"
gcloud storage cp "$APK" "$OBJ" --content-type=application/vnd.android.package-archive --cache-control=no-store >/dev/null
SIGNED=$(gcloud storage sign-url "$OBJ" --duration=7d --private-key-file="$KEY" --format='value(signed_url)')

CODE=$(python3 - "$BACKEND" "$SIGNED" "$STAMP" <<'PY'
import json, sys, urllib.request
backend, url, stamp = sys.argv[1:]
req = urllib.request.Request(f"{backend}/short-link",
    data=json.dumps({"target_url": url, "title": f"Tom's Gym Android APK {stamp}"}).encode(),
    headers={"Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req))["short_code"])
PY
)
LINK="$BACKEND/s/$CODE"

TMP=$(mktemp)
curl -sL -o "$TMP" "$LINK"
if [ "$(md5 -q "$TMP")" != "$(md5 -q "$APK")" ]; then echo "checksum mismatch downloading $LINK"; rm -f "$TMP"; exit 1; fi
rm -f "$TMP"

echo "APK: $OBJ"
echo "Install link (7 days): $LINK"
