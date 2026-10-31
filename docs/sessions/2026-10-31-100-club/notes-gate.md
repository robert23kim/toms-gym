# Gate notes 2026-10-31 (pre-flight, 100 Club)

## 1 gcloud: writable
`gcloud config get-value project` -> toms-gym; `gcloud auth print-access-token >/dev/null` exit 0.

## 2 cloudrun: writable (read only; describe succeeded)
backend latestReadyRevision: my-python-backend-00192-rhl
frontend latestReadyRevision: my-frontend-00195-zpg

## 3 gcs: writable
Bucket jtr-lift-u-4ever-cool-bucket (deploy-config.json GCS_BUCKET_NAME). `gsutil cp /tmp/gate-x gs://.../gate/2026-10-31-x` then `gsutil rm` both "Operation completed".

## 4 admin_token: writable
`gcloud secrets versions access latest --secret=admin-token --project=toms-gym | wc -c` -> 48 bytes (value not printed).

## 5 cloudsql: writable
Recipe: `~/Downloads/google-cloud-sdk/bin/cloud_sql_proxy -instances=toms-gym:us-east1:my-db=tcp:5433` (run in background; log says "Ready for new connections").
pg8000.native.Connection(user="postgres", password=<subprocess gcloud secrets versions access latest --secret=db-password --project=toms-gym>, host="127.0.0.1", port=5433, database="postgres"). Run with backend/venv/bin/python.
Ran: SELECT 1 -> [[1]]; SELECT COUNT(*) FROM "Competition" -> [[6]]; BEGIN; DELETE FROM "User" WHERE id='0000...' ; ROLLBACK -> ok. Working script: $S/dbcheck.py. Proxy killed with pkill -f cloud_sql_proxy afterwards.

## 6 chrome: NOT confirmed
mcp__claude-in-chrome__tabs_context_mcp (no args) returned: "This session has no tab group of its own. Any tabs opened earlier ... may still be open in Chrome, in a group this session cannot see". No tab context returned. Tool is reachable; createIfEmpty:true would open a new window, which the gate forbade. Later stages likely work with createIfEmpty:true (unverified).

## 7 backend_gate
`cd backend && PYTHON=venv/bin/python tools/run_ci_tests.sh` as given FAILS: venv is broken, pytest-cov plugin cannot import (ModuleNotFoundError: No module named 'coverage'; dist-info exists, package dir missing).
Workaround (no venv change): `PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh` -> 294 passed, 8 deselected, 0 failed, exit 0.

## 8 frontend_gate
frontend/node_modules was missing; ran `npm ci` (exit 0, gitignored, no tracked changes).
`npx tsc --noEmit` exit 0. jest --maxWorkers=4: 634 tests, 0 failed, 92 suites, 0 failed suites (jest-baseline.json).

## 9 git
Branch feat/100-club. Pre-existing dirty set (git status --porcelain, 30 entries):
 M .claude/settings.json
 M frontend/.env.production
?? .claude/workflows/
?? .superpowers/
?? backend/=3.5.0
?? backend/tests/fixtures/test_video_plank_10s.mp4
?? backend/tools/grid_debug_out/
?? docs/delight/2026-09-19-iteration-07/
?? docs/delight/persona-walk.config.json
?? docs/plans/2026-03-04-bowling-pages-implementation.md
?? docs/plans/2026-03-04-bowling-pages-redesign.md
?? docs/plans/2026-03-04-challenge-video-redesign.md
?? docs/plans/2026-03-05-robust-elbow-swing-filter.md
?? docs/plans/labeler-port-progress.md
?? docs/research/2026-09-14-alley-face/results/e6_eval_class_lovo_20260112_121117.json
?? docs/research/2026-09-14-alley-face/results/e6_eval_class_lovo_sample_input.json
?? docs/research/2026-09-14-alley-face/results/e6_eval_landmark_lovo_20260112_121117.json
?? docs/research/2026-09-14-alley-face/results/e6_eval_landmark_lovo_sample_input.json
?? docs/research/2026-09-19-new-alley-videos/
?? docs/sessions/2026-08-28-bug-ticket-loop-admin-gate.md
?? docs/sessions/2026-08-28-site-map-walk-and-home-challenges-fixes.md
?? docs/sessions/2026-08-29-bowling-scoresheet-photos-feature.md
?? docs/sessions/2026-08-29-hall-of-champions-replaces-lift-leaderboard.md
?? docs/sessions/2026-08-29-home-activity-streak-card.md
?? docs/sessions/2026-08-29-upload-analysis-perf-loop.md
?? docs/sessions/2026-08-31-delight-loop-six-iterations.md
?? docs/sessions/2026-09-08-bowling-night-four-photos-loop.md
?? docs/sessions/2026-10-05-manhattan-mile-reel-video.md
?? fairway_spec_bundle/
?? frontend/scripts/persona-walk.mjs

## 10 legacy_snapshot: writable
HTTP 200, 732 bytes saved to docs/sessions/2026-10-31-100-club/legacy-situp-leaderboard-before.json
