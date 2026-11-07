# Deploy round 2 (2026-11-07)

## Preconditions (all checked, all green)
- `git log 993990f..HEAD`: 16 commits (5bb001f .. 0916ee9), head 0916ee9 (the round-2 finalize-log fix).
- `git status --porcelain` tracked: only ` M .claude/settings.json`, ` M frontend/.env.production` (pre-existing). Nothing staged or committed by this phase, before or after.
- Backend gate `cd backend && PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh`: rc 0, 402 passed, 8 deselected.
- `cd frontend && npx tsc --noEmit`: rc 0, no output.

## 1. Backend
- `python3 deploy.py --backend-only --skip-iam` -> rc 0, health check HTTP 200 (log: deploy-backend-2.log).
- Revisions: 00194-8wr (2026-10-31) -> 00195-jbg (round 1) -> **my-python-backend-00196-mtt** (2026-11-07T16:10:17Z), 100% traffic, latestRevision.
- `curl /health` -> 200 `{"service":"toms-gym-backend","status":"healthy","timestamp":"2026-11-07T16:11:08"}`.
- live-after-backend.json vs live-before.json, per row (name, rank, score, streak, this_week.lifts, attempt_count):
  - caleb.li.larson (1, 150, 1, 107.5, 6) == (1, 150, 1, 107.5, 6)
  - Toka (2, 150, 1, 100, 5) == (2, 150, 1, 100, 5)
  - Full JSON equal. attempt_count unchanged, so no uploads during the run.
- monday-after.json (admin `?as_of=2026-11-09T12:00:00-05:00`, token read from GCP secret admin-token into a shell var, never printed) vs monday-before.json:
  - caleb.li.larson (1, 200, 1, 0, 6) == same; Toka (2, 175, 1, 0, 5) == same. Full JSON equal.

## 2. Frontend
- `python3 deploy.py --frontend-only --skip-iam` -> rc 0 (log: deploy-frontend-2.log). No jest/vite/tsc job was running.
- Revisions: 00197-h8f -> 00198-jsk (round 1) -> **my-frontend-00199-qfz** (2026-11-07T16:14:02Z), 100% traffic.
- Bundle canary: `grep -l consistency-result frontend/dist/assets/*.js` matched `ConsistencyResult-CkCZC1Nx.js`, but that local dist is the
  round-1 APK build (10:46). deploy.py builds remotely, so the deployed hash differs. I used the deployed entry to find the chunk:
  - Entry HTML (1,430 B): build-timestamp 1794067886, references `assets/index-Bp8C5fCx.js` (new hash; round 1 was index-DnQWVIvq.js).
  - Entry JS (487,703 B): consistency-result 0 hits (expected, the route is split out). It references `ConsistencyResult-CdM7ZRYR.js`.
  - `curl /assets/ConsistencyResult-CdM7ZRYR.js` -> 200 application/javascript, 5,971 B, starts `import{...}from"./index-Bp8C5fCx.js"` (same hash family as the entry),
    **consistency-result: 1 hit**, "banked in week": 1.
- Round 2 changed only backend code, so the frontend content matches round 1. This deploy rebuilt the same source.

## 3. APK
- `VITE_BUILD_TIMESTAMP=$(date +%s) npm run android:build` -> rc 0 (log: apk-build-2.log). frontend/tomsgym-debug.apk is 4,710,160 B, 11:15.
  The only JVM running was an idle gradle daemon. No node test/build was running.
- `unzip -p tomsgym-debug.apk assets/public/index.html | grep build-timestamp` -> **1794068093** (> 1789332615).
  It contains assets/public/assets/ConsistencyResult-B5YL9nQH.js with consistency-result 1 hit.
- `npm run android:publish` -> rc 0 (log: apk-publish-2.log).
  - Object: **gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-111511.apk**. `gsutil ls -l`: 4710160 B, 2026-11-07T16:15:13Z.
  - Short link: **https://my-python-backend-quyiiugyoq-ue.a.run.app/s/LSOd2h**. It gives a 302 to a signed storage.googleapis.com URL for that object (7d).
    Following it downloads 4,710,160 B, starting `PK\x03\x04`, and `cmp` shows it byte-identical to the local APK.
  - Not covered: nothing was installed on a phone, and the link was not opened on a device. The round-1 link /s/kwA1J7 still points to the older object.

## 4. Invariants
- GET /competitions/32ca7bad-...: mode "consistency", rules {base_quota 100, ramp 25, weeks 8, quota_bonus 50, type_bonus 25,
  plank_seconds_per_lift 10, tz America/New_York, week_start 2026-11-02} (competition-after-2.json).
- Legacy situp board 95b60b42-...: metric reps, 1 row, Toka rank 1 score 66.5. Equal to docs/sessions/2026-10-31-100-club/legacy-situp-leaderboard-before.json (legacy-situp-after-2.json).

## Not covered
- B-guard (server-side bodyweight weight -> 0) is still not proven in production. Commit 0916ee9 is now live on 00196-mtt, so the next real
  Pushup/Situp/Plank finalize will log `weight_kg=<w>`. Read it with the gcloud logging command in notes-fix-2.md. No upload happened during
  this run, so I have no such log line yet. I made no prod writes and created no canary.
- No browser render in this phase. The evidence is HTTP, bundle grep and APK content only.
