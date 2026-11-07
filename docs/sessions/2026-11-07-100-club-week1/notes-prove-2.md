# Prove round 2 (2026-11-07, 16:16-16:19Z / 11:16-11:19 ET, Saturday of week 1)

Targets (confirmed live with `gcloud run services describe ... --format=value(status.latestReadyRevisionName,status.traffic[0]...)`):
backend my-python-backend-00196-mtt 100%, frontend my-frontend-00199-qfz 100%. Deployed HTML: build-timestamp 1794067886, entry
assets/index-Bp8C5fCx.js. Nothing in production was written by this phase. No commits, nothing staged (tracked status still only the
two pre-existing ` M` files).

## A. API (python3 -I prove-api-2.py = prove-api.py with outputs renamed to prove-live-2.json / prove-monday-2.json)
- Public GET /competitions/32ca7bad-.../leaderboard -> 200, 2927 B. (rank, score, streak, this_week.lifts, attempt_count):
  caleb.li.larson (1,150,1,107.5,6) EQ ref; Toka (2,150,1,100,5) EQ ref. week_index 1, days_left 2,
  leaders Plank/Pushup caleb, Situp Toka.
- Admin ?as_of=2026-11-09T12:00:00-05:00 (token from gcloud secret admin-token, len 48, never printed) -> 200, 2933 B:
  caleb (1,200,1,0,6), Toka (2,175,1,0,5), week_index 2, type_leaders {}, quotas [125,125]. EQ ref.
- Full-document equality (sort_keys dump): prove-live-2.json == live-before.json True; prove-monday-2.json == monday-before.json True.
- as_of with no header -> 401 {"error":"Admin token required"}; wrong token -> 401, same body.
- End of run (16:19Z): public board again byte-equal (sort_keys) to live-before.json, attempt_count 6 / 5. No live row changed.
- Not covered: Monday numbers are asserted only via as_of, not by a real rollover.

## B. Weight guard canary: SKIPPED (gate cloudsql=false)
No canary was registered or uploaded. Without SQL, is_test cannot be set and cleanup is impossible (DELETE /attempts 500s on analysed
attempts, there is no user-delete route), so it would leave a real-looking user in prod.
Read-only substitute: `gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="my-python-backend"
AND textPayload:"Created attempt"' --freshness=2d --limit=10` -> 4 lines, all on revision 00194-8wr (11-05 17:05Z caleb Pushup 5fce96b5;
11-06 13:21-13:24Z Toka Plank/Pushup/Situp), none on 00195 or 00196. The query could have returned lines (it found the 00194 ones), so
"no new upload since the guard deployed" is a real result. No `weight_kg=` line exists yet.
Not covered: the server-side Pushup/Situp/Plank weight->0 guard (B1b) is still unproven in production; the evidence is only the Flask
test-client tests (402 backend tests, mutation-checked in notes-fix-2.md).

## C. Anonymous Chrome walk (Claude in Chrome, one tab via tabs_context_mcp createIfEmpty, id 1652867120, closed; group auto-removed)
Console tracking was started on page 1, then page 1 was re-navigated, so its load is covered. read_console_messages onlyErrors after
get_page_text on every page: 0 errors on all four. No localStorage written, no sign-in.
1. /challenges/32ca7bad-... exact lines:
   "Ongoing · ends Sun 27 Dec" (B5; no "51d left") / "The 100 Club" / ... / "2 joined" / "WEEKLY QUOTA" (B10) / "Week 1 of 8 · 2 days left"
   "Situp / Toka 40 / LEADING", "Pushup / caleb.li.larson 65 / LEADING", "Plank / caleb.li.larson 119.5 s / LEADING"
   "Type bonuses (+25 each) are added when the week ends on Sunday." (B3)
   "Toka 150pts 🔥1 100/100 this week 2", "caleb.li.larson 150pts 🔥1 107.5/100 this week 1"
   "caleb.li.larson and Toka are tied on points; more lifts this week puts caleb.li.larson ahead." (B4)
   "caleb.li.larson · weeks ▾", "Toka · weeks ▾", "— / YOU / Not logged yet / Log this week's lifts". No "Everyone else" (B8).
   Clicked "caleb.li.larson · weeks ▾" (find ref_52, left_click by ref) -> chip "▴" and:
   "WEEK QUOTA LIFTS MET BONUSES POINTS" / "1NOW 100 107.5 ✓ Pushup, Plank · locks Sun 150" (B3) /
   "Plank 11 (119.5 s) · Pushup 65 · Situp 31.5" (B7). The toggle worked first time in Chrome this round.
2. /lift: "The 100 Club · Log this week's lifts / Open" above "Upload a lift / Squat, bench, deadlift, curl ..." (B6). No "Plank challenge".
3. /profile/7844e26d-...: "My lifts (22)": "Nov 6 Situp A", "Nov 6 Pushup C", "Nov 6 Plank 1:22", "Nov 3 Situp A", "Nov 2 Pushup C",
   "Sep 27 Situp B", ... "Aug 28 Pushup C", "Aug 1 Pushup D", ... "Mar 5 Bicep curl · 115kg D". No "60kg" anywhere (B9); weighted rows keep kg.
   First page only (20 of 22 rows, "Load more" not clicked).
4. Video page .../participants/7844e26d-.../video/c9dec98b-3c29-41fb-9324-4e545af49895 (attempt_id from Toka's leaderboard row):
   "Toka's Situp / Share", "+13 lifts banked", "Toka: Quota met · 100 / 100 this week · 2 days left", "See the board →",
   "A / 13 reps detected / 91%", "Board score 13 · 13 clean of 13 · sloppy reps count half". No "Beat this", no "to pass" (B2).
Not covered: Chrome window was desktop-ish width (not 390); no check of which bundle hash Chrome loaded (D proves the deployed stamp).

## D. Viewer session, Playwright (node prove-viewer.mjs > prove-viewer-2.log; rc 0; playwright from frontend/node_modules, headless chromium)
Same script as round 1 (fresh context per width, addInitScript localStorage.userId = Toka, page.unrouteAll(), function-matcher route that
fulfils PUT/POST/DELETE/PATCH with 204, 1500 ms wait + re-goto after the first navigation), plus one new check: the blocked boot telemetry
POST /log-error must carry "build":1794067886 (the deployed stamp). Round-1 outputs preserved in prove-round1/.
Result: FAILS 0 of 42 (prove-viewer-results.json). At 1280x800 and 390x844 (innerWidth read back 1280 / 390 on every page):
- challenge: ring "100 / 100"; "You lead Situp this week"; tie line; bonus-lock line; "Week 1 of 8 · 2 days left"; pill "Ongoing · ends Sun 27 Dec";
  no "Everyone else"; no "Not logged yet". "Toka · weeks" -> aria-expanded=true, table has "Situp · locks Sun" and
  "Plank 8 (82.8 s) · Pushup 52 · Situp 40".
- home: "The 100 Club" row and pill "100 / 100 · 2 days left" present at both widths (the 1280 check is pass-by-construction; the
  detail "present=true" is the evidence there).
- video: [data-testid=consistency-result] "+13 lifts banked / Quota met · 100 / 100 this week · 2 days left / See the board →" (owner wording,
  no "Toka:" prefix); no "Beat this" / "to pass".
- 0 pageerror / console errors. Only write attempted per width: POST /log-error boot telemetry, fulfilled locally, build 1794067886.
- Every saved text (prove-viewer-<page>-<width>.txt) differs from round 1 only in the footer "v2026-11-07 15:42 UTC" -> "v2026-11-07 16:11 UTC"
  (diff, 1 line each), i.e. the new bundle rendered with identical content (expected: round 2 changed backend only).
Not covered: a real phone browser, iOS Safari, the APK WebView, the AnalysisStatus upload reveal (needs a fresh upload).

## E. APK
- `gsutil ls -l gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-111511.apk` -> 4710160  2026-11-07T16:15:13Z.
- `curl -sI https://my-python-backend-quyiiugyoq-ue.a.run.app/s/LSOd2h` -> HTTP/2 302, location
  https://storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-111511.apk?x-goog-signature=REDACTED...&x-goog-expires=604800.
- `curl -sL` -> apk-prove-2/tomsgym-prove-2.apk: 4710160 B, magic PK\x03\x04, sha256 64f8daa7...4c80 == frontend/tomsgym-debug.apk.
  `unzip -p ... assets/public/index.html` -> build-timestamp 1794068093 (> Sep-13 stamp 1789332615). 1 ConsistencyResult entry.
- NOT covered: installing on Tom's phone. Until he installs from /s/LSOd2h (expires 2026-11-14), the phone keeps the Sep-13 bundle (B1 root cause).

## Cleanup log
- Chrome: the one tab I created (1652867120) closed; group auto-removed. Anonymous page loads sent the app's own boot telemetry to prod
  (not a challenge row; Chrome cannot intercept).
- Playwright: contexts and browser closed by the script.
- No canary created, so nothing to delete in SQL or GCS.
- Local files added (untracked): prove-api-2.py, prove-live-2.json, prove-monday-2.json, prove-viewer-2.log, prove-viewer-*-*.txt and
  prove-viewer-results.json (overwritten, round-1 copies in prove-round1/), apk-prove-2/ (downloaded APK, can be deleted).
  prove-viewer.mjs edited in place (+1 build-stamp check line).
