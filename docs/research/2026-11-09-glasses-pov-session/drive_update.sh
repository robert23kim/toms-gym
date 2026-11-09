#!/bin/bash
# Resumable re-upload of new content into an EXISTING Drive file (same id, same link). drive_update.sh <file> <fileId>
set -euo pipefail
FILE="$1"; ID="$2"
TOK=$(gcloud auth print-access-token)
SIZE=$(stat -f %z "$FILE")
URI=$(curl -s -D - -o /dev/null -X PATCH \
  "https://www.googleapis.com/upload/drive/v3/files/$ID?uploadType=resumable" \
  -H "Authorization: Bearer $TOK" -H "Content-Type: application/json; charset=UTF-8" \
  -H "X-Upload-Content-Type: video/mp4" -H "X-Upload-Content-Length: $SIZE" \
  -d '{}' | awk 'tolower($1)=="location:" {print $2}' | tr -d '\r')
[ -n "$URI" ] || { echo "no upload session"; exit 2; }
curl -s -X PUT "$URI" -H "Content-Length: $SIZE" -H "Content-Type: video/mp4" --data-binary @"$FILE" \
  | /Users/toka/code/bowling-app/analysis-engine/.venv/bin/python -c 'import sys,json; d=json.load(sys.stdin); print(d["id"]); print("https://drive.google.com/file/d/%s/view" % d["id"])'
curl -s "https://www.googleapis.com/drive/v3/files/$ID?fields=id,name,size,md5Checksum,modifiedTime" -H "Authorization: Bearer $(gcloud auth print-access-token)"
echo; echo "local md5: $(md5 -q "$FILE") size $SIZE"
