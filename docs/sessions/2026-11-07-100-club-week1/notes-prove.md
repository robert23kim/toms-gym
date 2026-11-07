# Prove round 1 (2026-11-07, ~10:50-11:00 ET, Saturday of week 1)

Targets: backend my-python-backend-00195-jbg, frontend my-frontend-00198-jsk (bundle build stamp 1794066143,
seen in the app's boot telemetry body), APK gs://.../apk/tomsgym-debug-20261107-104641.apk.
Nothing in production was written by this phase. No commits.

## A. API (python3 -I docs/sessions/2026-11-07-100-club-week1/prove-api.py; urllib; admin token read via `gcloud secrets versions access latest --secret=admin-token`, length 48, never printed)
- Public `GET /competitions/32ca7bad-.../leaderboard` -> 200, 2927 B (saved prove-live.json).
  Compared (rank, score, streak, this_week.lifts, attempt_count) per user_id against live-before.json:
  - caleb.li.larson ref (1, 150, 1, 107.5, 6) now (1, 150, 1, 107.5, 6) EQ
  - Toka ref (2, 150, 1, 100, 5) now (2, 150, 1, 100, 5) EQ
  - same 2 user_ids; week_index 1, days_left 2, leaders Plank/Pushup caleb, Situp Toka.
- Admin `?as_of=2026-11-09T12:00:00-05:00` with X-Admin-Token -> 200, 2933 B (prove-monday.json):
  - caleb (1, 200, 1, 0, 6) EQ; Toka (2, 175, 1, 0, 5) EQ; week_index 2; type_leaders {}; quotas [125, 125].
- as_of without header -> 401 `{"error":"Admin token required"}`; with a wrong token -> 401 (same body).
- Extra: `GET /lifting/result/c9dec98b-...` -> attempt_created_at "2026-11-06T13:24:09.536451+00:00" (the R2 backend
  field is live). /health 200.
- Not covered: Monday numbers are asserted only through as_of, not by a real Monday rollover. No upload happened
  during the run (attempt_count unchanged), so no new-lift scoring path was exercised.

## B. Weight guard canary: SKIPPED
Gate says cloudsql = false (the Cloud SQL proxy start was denied by the auto-mode classifier). Without SQL there is
no way to set is_test on the canary or delete it afterwards (DELETE /attempts 500s on analysed attempts, no
user-delete route), so creating it would leave a real-looking user and attempt in prod. Not attempted.
Not covered: the server-side Pushup/Situp/Plank weight->0 guard is proven only by the fixer's Flask test-client
tests (notes-fix.md QA-2, 401 backend tests), not in production.

## C. Anonymous Chrome walk (Claude in Chrome, one tab created via tabs_context_mcp createIfEmpty, closed)
Viewer state: anonymous (page shows "YOU · Not logged yet"), Chrome window viewport ~500 px wide (screenshot frame
500x723). Console errors (read_console_messages onlyErrors, tracking began on page 1 so page 1's load is not
covered; pages 2-4 loaded after tracking started): none on any page.

1. /challenges/32ca7bad-... (exact lines):
   "Ongoing · ends Sun 27 Dec"  (B5: no "51d left")
   "The 100 Club" / "WEEKLY QUOTA" / "Week 1 of 8 · 2 days left"  (B10: eyebrow no longer repeats the title)
   "Situp / Toka 40 / LEADING", "Pushup / caleb.li.larson 65 / LEADING", "Plank / caleb.li.larson 119.5 s / LEADING"
   "Type bonuses (+25 each) are added when the week ends on Sunday."  (B3)
   podium "Toka 150pts 🔥1 100/100 this week 2", "caleb.li.larson 150pts 🔥1 107.5/100 this week 1"
   "caleb.li.larson and Toka are tied on points; more lifts this week puts caleb.li.larson ahead."  (B4)
   chips "caleb.li.larson · weeks ▾", "Toka · weeks ▾"; then "— YOU Not logged yet Log this week's lifts".
   No "Everyone else" header (B8).
   Weeks toggle: clicking either chip in Chrome (by ref, by coordinate, and again in a second fresh tab after
   scroll_to) did NOT expand anything: page text and screenshot unchanged, chip still "▾". Not reproduced in
   Playwright (see D and prove-toggle-anon.txt: anonymous, 500x723 and 1280x800, both chips -> aria-expanded=true and
   the week table renders). Cause not established (could be the Chrome extension's input on this window or a real
   desktop-Chrome issue); no real-device check. The B7 / "locks Sun" text was read in Playwright instead.
2. /lift: "The 100 Club · Log this week's lifts / Open" above "Upload a lift" (B6). No "Plank challenge".
3. /profile/7844e26d-...: "My lifts (22)": "Nov 6 Situp A", "Nov 6 Pushup C", "Nov 6 Plank 1:22", "Nov 3 Situp A",
   "Nov 2 Pushup C", ... No "60kg" anywhere (B9). Weighted rows still show weight ("Bicep curl · 115kg").
4. Video page of Toka's latest attempt c9dec98b-... (attempt_id from the leaderboard row):
   "Toka's Situp / Share", "+13 lifts banked", "Toka: Quota met · 100 / 100 this week · 2 days left", "See the board →",
   "A / 13 reps detected / 91%", "Board score 13 · 13 clean of 13 · sloppy reps count half".
   No "Beat this", no "to pass" (B2). Non-owner prefix "Toka:" for an anonymous viewer (QA-1).

## D. Viewer session, Playwright (prove-viewer.mjs, playwright 1.58.2 from frontend/node_modules, headless chromium)
Fresh context per width; addInitScript sets localStorage.userId = Toka's id; page.unrouteAll(); function-matcher
route fulfils PUT/POST/DELETE/PATCH with 204. One write was attempted per width and blocked: POST /log-error with
body {"page":"app","action":"boot","error":"-","build":1794066143,"platform":"web"} (boot telemetry, not an error;
build stamp = deployed frontend). Each page text saved to prove-viewer-<page>-<width>.txt; checks in
prove-viewer-results.json. Result: 40 of 40 PASS (first run had one FAIL from my own regex assuming type order;
the breakdown is in by_type order "Plank 8 (82.8 s) · Pushup 52 · Situp 40"; check rewritten order-independent).
At both 1280x800 and 390x844 (innerWidth read back as 1280 / 390 on every page):
- challenge: ring "100 / 100"; "You lead Situp this week"; tie line as above; bonus-lock line; "Week 1 of 8 · 2 days
  left"; pill "Ongoing · ends Sun 27 Dec"; no "Everyone else"; no "Not logged yet" (viewer state took, contrast to
  the anonymous Chrome walk). Clicking "Toka · weeks" -> aria-expanded=true, table
  "1 NOW 100 100 ✓ Situp · locks Sun 150" + "Plank 8 (82.8 s) · Pushup 52 · Situp 40" (B3, B7).
- home: "The 100 Club" row with pill "100 / 100 · 2 days left" present at both widths (detail present=true; note the
  1280 check was written as always-pass, so the evidence at 1280 is the detail string, not the PASS).
- video (c9dec98b): consistency-result block "+13 lifts banked / Quota met · 100 / 100 this week · 2 days left /
  See the board →" (owner wording, no "Toka:" prefix); no "Beat this" / "to pass".
- no pageerror / console error at either width.
Anonymous toggle cross-check: prove-toggle-anon.mjs -> prove-toggle-anon.txt (both chips expand at 500 and 1280;
caleb "Pushup, Plank · locks Sun", "Plank 11 (119.5 s) · Pushup 65 · Situp 31.5").
Not covered: a real phone browser or the APK WebView; an iOS Safari render; the upload reveal (AnalysisStatus) page,
which needs a fresh upload; a viewer whose attempt is from an earlier week (no such attempt exists yet).

## E. APK
- `gsutil ls -l` -> 4679930  2026-11-07T15:46:44Z  gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-104641.apk
- `curl -sI https://my-python-backend-quyiiugyoq-ue.a.run.app/s/kwA1J7` -> HTTP/2 302, location
  https://storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-104641.apk?x-goog-signature=...
- `curl -sL` to apk-prove/tomsgym-prove.apk: 4679930 B, magic PK\x03\x04, sha256 c14dff77...7284 identical to
  frontend/tomsgym-debug.apk. `unzip -p ... assets/public/index.html` -> build-timestamp 1794066371 (> Sep 13 stamp
  1789332615). ConsistencyResult chunk present (1 entry).
- NOT covered: nobody installed this APK on Tom's phone; until it is installed, the phone keeps the Sep-13 bundle
  (B1 root cause). The short link expires 7 days after 2026-11-07.

## Cleanup
- Chrome: both tabs I created were closed (groups auto-removed). No localStorage written in Chrome, no sign-in.
  The anonymous Chrome walk could not intercept requests, so the app's own boot telemetry POST /log-error went to
  prod for those page loads (not a challenge row).
- Playwright: contexts and browser closed by the script.
- No canary created (B skipped), so nothing to delete in SQL or GCS.
- Local files added in this notes dir: prove-viewer.mjs, prove-toggle-anon.mjs, prove-*.txt/json, apk-prove/
  (downloaded APK + extracted index.html, untracked; can be deleted).
