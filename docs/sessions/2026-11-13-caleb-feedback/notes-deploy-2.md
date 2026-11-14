# Deploy round 2 (2026-11-14 UTC)

Preconditions: 12 fix commits after 5ef44cba (HEAD 668529b); git status shows only the pre-existing dirty set (.claude/settings.json, frontend/.env.production + gate untracked list); frontend `npx tsc --noEmit` rc=0, no output.

1 Backend: `git diff --stat 5ef44cba..HEAD -- backend/` empty (0 bytes) -> not deployed. Revision stays my-python-backend-00196-mtt. /health: {"status":"healthy"} at 2026-11-14T03:12:34.
2 Frontend: `python3 deploy.py --frontend-only --skip-iam` rc=0 (log deploy-frontend-2.log). Revision my-frontend-00205-95c, 100% traffic (> 00203-7gg). Deployed build-timestamp 1794625712, entry index-DVWVYKuZ.js.
  Bundle canary (bundle-after-2/: index.html + 82 js, recursive chunk fetch, same count as bundle-before):
  - you-row-unknown: before 0 -> after 1 (ChallengeDetail-CL-vy90B.js)
  - fetch canary "Not logged yet": 1 (before 1). "100 Club" is 0 in both: it is API data, not bundle text, so not usable as canary.
  - HEAD 668529b wording "extra for each lift type you log that week where nobody logs more": before 0 -> after 1, so the deploy carries HEAD.
  Note: local frontend/dist is an older build (stamp 1794623890, chunk hash DsZgsGCp); Cloud Build builds its own, so chunk hashes differ from local dist.
3 APK: VITE_BUILD_TIMESTAMP=1794625920 npm run android:build rc=0 (apk-build-2.log); android:publish rc=0 (apk-publish-2.log).
  - object gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261113-221223.apk, md5 Wrz7OpSnV4b8Mr6hSdUung== equals local tomsgym-debug.apk
  - short link https://my-python-backend-quyiiugyoq-ue.a.run.app/s/oVzVrt -> 302 to that object's signed URL (7 days)
  - APK assets/public/index.html build-timestamp 1794625920; assets/public/assets/ChallengeDetail-Dr99dmtJ.js contains you-row-unknown.
  - Not installed on any phone (curl/unzip checks only; no on-device verification).
4 Engine: not built or deployed; bowling-service-00053-fxm.
5 Live board (live-after-deploy-2.json vs live-before.json), rank/score/this_week.lifts/attempt_count:
  caleb.li.larson 1/375/147/14 = equal; Toka 2/350/162.5/14 = equal. No uploads during the run.
Not covered: no browser render of the deployed page in this round (bundle-text check only).
