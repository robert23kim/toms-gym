# Deploy round 1 (2026-11-07)

## Preconditions
- `git log 993990f..HEAD`: 15 commits (5bb001f .. 6d5a963), fix/docs commits present.
- `git status --porcelain` tracked: only ` M .claude/settings.json`, ` M frontend/.env.production` (pre-existing). Build outputs (frontend/*.apk, dist/, android build/, *.log) are gitignored. Nothing staged or committed by this phase.
- Backend gate `cd backend && PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh`: rc 0, 401 passed, 8 deselected.
- `cd frontend && npx tsc --noEmit`: rc 0.

## 1. Backend
- `python3 deploy.py --backend-only --skip-iam` -> rc 0, health check HTTP 200 (log: deploy-backend.log).
- Revision: before my-python-backend-00194-8wr (2026-10-31T15:34Z); after **my-python-backend-00195-jbg**, 100% traffic.
- `curl /health` -> 200 `{"status":"healthy","timestamp":"2026-11-07T15:41:58"}`.
- live-after-backend.json vs live-before.json: same 2 user_ids; rank/score/streak/this_week.lifts/attempt_count:
  - caleb.li.larson (1, 150, 1, 107.5, 6) == (1, 150, 1, 107.5, 6)
  - Toka (2, 150, 1, 100, 5) == (2, 150, 1, 100, 5)
  - Full `json.tool` diff of the two files: empty (rc 0). No uploads during the run (attempt_count unchanged).
- monday-after.json (admin `?as_of=2026-11-09T12:00:00-05:00`, token from GCP secret admin-token, not printed) vs monday-before.json:
  - caleb.li.larson (1, 200, 1, 0, 6) == same; Toka (2, 175, 1, 0, 5) == same. ALL EQUAL.

## 2. Frontend
- `python3 deploy.py --frontend-only --skip-iam` -> rc 0 (log: deploy-frontend.log).
- Revision: before my-frontend-00197-h8f; after **my-frontend-00198-jsk**, 100% traffic.
- Bundle canary: deploy builds remotely, so there was no local `frontend/dist` to grep (the glob matched nothing). I found the chunk from the deployed site instead.
  The entry HTML references `assets/index-DnQWVIvq.js` with build-timestamp 1794066143. I fetched the entry (487,703 B, 0 hits, as expected since the route is split out) and all 71 chunks it references.
  `grep -c consistency-result` -> **ConsistencyResult-B1jCbbDB.js: 1 hit** (5,971 B, starts `import{...}from"./index-DnQWVIvq.js"`, the same hash family as the entry HTML). None of the 71 fetched files is an HTML fallback.
  New-fix strings in the deployed bundle: "banked in week" 1 (R2), "clean of" 5 and "sloppy reps count half" 3 (R3), "after the last week" 1 (R2).

## 3. APK
- `VITE_BUILD_TIMESTAMP=$(date +%s) npm run android:build` -> rc 0, frontend/tomsgym-debug.apk 4,679,930 B (log: apk-build.log). No other node job was running (pgrep empty).
- `unzip -p ... assets/public/index.html | grep build-timestamp` -> **1794066371** (> 1789332615).
  The APK has assets/public/assets/ConsistencyResult-CkCZC1Nx.js with consistency-result 1 and "banked in week" 1. Its hash differs from the web chunk because it is a separate build.
- `npm run android:publish` -> rc 0 (log: apk-publish.log).
  - Object: **gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-104641.apk**, `gsutil ls -l`: 4679930 B, 2026-11-07T15:46:44Z.
  - Short link: **https://my-python-backend-quyiiugyoq-ue.a.run.app/s/kwA1J7**. curl gives a 302 to the signed GCS URL (7d). Following it downloads 4,679,930 B starting with `PK\x03\x04`.
  - Not covered: nothing was installed on a phone, and the link was not opened on a device.

## 4. Invariants
- GET /competitions/32ca7bad-...: competition.mode = "consistency", and rules = {base_quota 100, ramp 25, weeks 8, quota_bonus 50, type_bonus 25, plank_seconds_per_lift 10, tz America/New_York, week_start 2026-11-02} (competition-after.json).
- Legacy situp board 95b60b42-...: metric reps, 1 row, top Toka 66.5 rank 1. That matches docs/sessions/2026-10-31-100-club/legacy-situp-leaderboard-before.json (legacy-situp-after.json).

## Not covered
- No browser render of the deployed pages in this phase; that belongs to the prove phase. Evidence here is HTTP, bundle grep and APK content.
- `attempt_created_at` on /lifting/result is deployed but was not curled against a real attempt here.
