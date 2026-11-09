#!/bin/bash
# Resumable upload of one file to the root of My Drive. Needs a gcloud login with the Drive scope.
set -euo pipefail
FILE="$1"; NAME="$2"
TOK=$(gcloud auth print-access-token)
SIZE=$(stat -f %z "$FILE")
URI=$(curl -s -D - -o /dev/null -X POST \
  "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable" \
  -H "Authorization: Bearer $TOK" -H "Content-Type: application/json; charset=UTF-8" \
  -H "X-Upload-Content-Type: video/mp4" -H "X-Upload-Content-Length: $SIZE" \
  -d "{\"name\": \"$NAME\", \"mimeType\": \"video/mp4\"}" | awk 'tolower($1)=="location:" {print $2}' | tr -d '\r')
[ -n "$URI" ] || { echo "no upload session (scope missing?)"; exit 2; }
curl -s -X PUT "$URI" -H "Content-Length: $SIZE" -H "Content-Type: video/mp4" --data-binary @"$FILE" \
  | /Users/toka/code/bowling-app/analysis-engine/.venv/bin/python -c 'import sys,json; d=json.load(sys.stdin); print(d["id"]); print("https://drive.google.com/file/d/%s/view" % d["id"])'
