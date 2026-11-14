# Deploy notes, round 1 (2026-11-14 ~02:20-02:45Z)

Preconditions: 10 fix commits after 5ef44cb (HEAD 50fb8cc); git status shows only .claude/settings.json,
frontend/.env.production modified plus the gate's untracked set (filtered diff of status vs gate list: empty)
plus this run dir; `npx tsc --noEmit` rc=0.

1 Backend: `git diff --stat 5ef44cb..HEAD -- backend/` empty -> NOT deployed. Rev stays my-python-backend-00196-mtt.
  /health = {"status":"healthy"}.
2 Frontend: `python3 deploy.py --frontend-only --skip-iam` rc=0 (deploy-frontend.log). Rev my-frontend-00204-rnr,
  100% traffic (was 00203-7gg). Bundle: bundle-after/ = index.html + 82 js (recursive chunk follow, same as gate).
  you-row-unknown = 1 file (was 0). Fetch canary "Not logged yet" = 1 (same canary the gate used).
  "100 Club" = 0, expected: it only appears in src fixtures/tests, not in shipped code. index build-timestamp 1794623705.
  Live render (gate-pw.mjs, fresh headless 390x844, unrouteAll, function matcher stubbing non-GET, 1500 ms):
  testid "you-row" absent; [data-testid^="you-row"] text "? / YOU / Find your profile / This device doesn't know
  who you are yet" (before: "— / YOU / Not logged yet"). after-you-row-anon.txt. Anonymous viewer only; the
  signed-in / remembered-uploader states were not rendered on prod.
3 APK: VITE_BUILD_TIMESTAMP=1794623890 npm run android:build rc=0, then android:publish rc=0.
  gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261113-213836.apk, link
  https://my-python-backend-quyiiugyoq-ue.a.run.app/s/oeg31K. APK index.html build-timestamp 1794623890;
  assets/public/assets/ChallengeDetail-DsZgsGCp.js contains you-row-unknown. Short link downloaded (200, 4815376 B),
  sha1 equal to local APK (927fbab5...). Not installed on a phone.
4 Engine: not built/deployed. bowling-service-00053-fxm.
5 Leaderboard: live-after-deploy.json vs live-before.json, (name, rank, score, this_week.lifts, attempt_count):
  caleb.li.larson 1/375/147/14, Toka 2/350/162.5/14 -> identical. No uploads during the run.
