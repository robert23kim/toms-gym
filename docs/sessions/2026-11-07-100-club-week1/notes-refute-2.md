# Refute round 2 (2026-11-07, 16:20-16:30Z / 11:20-11:30 ET)

Targets confirmed with `gcloud run services describe`: backend my-python-backend-00196-mtt 100%, frontend my-frontend-00199-qfz 100%.
Nothing in production was written by this phase. No commits, nothing staged. My own scripts and outputs live in the session scratchpad
(/private/tmp/claude-502/-Users-toka-code-toms-gym/fe49fbdc-4643-4589-9b3f-d81e9b1ac6e9/scratchpad/refute2/), not in the repo.

## A-live: NOT refuted
Own script (scratchpad refute2/api.py, not the prover's): public GET /competitions/32ca7bad-.../leaderboard at 16:20:43Z -> 200, 2927 B.
sort_keys dump equal to live-before.json: True; recursive field diff: [] (empty).
caleb.li.larson rank 1, 150, streak 1, 107.5 lifts, 6 attempts, quota 100; Toka 2, 150, 1, 100, 5, 100. week_index 1, days_left 2,
leaders Plank/Pushup caleb, Situp Toka. Attempt counts per user unchanged from live-before (6 / 5), so no live row was added.
Could have failed: the same diff code reports the as_of document as different from the public one (canary True).

## A-monday: NOT refuted
Admin ?as_of=2026-11-09T12:00:00-05:00 with the admin-token secret (len 48, never printed) -> 200, 2933 B, sort_keys equal to
monday-before.json True, diff []. caleb 200 / Toka 175, quota 125 each, streak 1, week_index 2, type_leaders {}.
No header -> 401 {"error":"Admin token required"}; wrong token -> 401, same body.
Not covered: a real Monday rollover.

## B-guard: REFUTED as a production claim (the prover itself marked it held=false / SKIPPED)
The guard is in the code: backend/toms_gym/routes/upload_routes.py:50 `bodyweight_weight_kg`, called at :131 (direct upload) and :389
(signed-url finalize). It is not proven in production. My own `gcloud logging read` (3 days, Created attempt OR weight_kg= OR
/upload/finalize OR /upload/signed-url, limit 20, newest first): the newest line is 2026-11-06T13:24:09Z on 00194-8wr (Toka Situp
c9dec98b). Nothing on 00195 or 00196. The query found the older lines, so an empty result for the new revisions is real: no upload has
reached the guarded revision yet. cloudsql=false, so no canary existed and no SQL cleanup check was possible. Indirect cleanup check:
attempt counts 6 / 5 and the whole public board are unchanged.

## C-chrome: NOT refuted (one correction to the prover's note)
One tab (1652867124, created by tabs_context_mcp createIfEmpty), closed; group auto-removed. No localStorage, no sign-in. Console
tracking started, then the challenge page was re-navigated: 0 errors across the challenge, video, profile and /lift loads.
- Script src assets/index-Bp8C5fCx.js, meta build-timestamp 1794067886, so Chrome loaded the deployed bundle (the prover left this open).
- Challenge page text matches the prover's lines: "Ongoing · ends Sun 27 Dec", "WEEKLY QUOTA", "Week 1 of 8 · 2 days left", the three
  LEADING chips, "Type bonuses (+25 each) are added when the week ends on Sunday.", the tie line, no "Everyone else", no "Nd left".
  The caleb "· weeks" toggle went from aria-expanded false to true and showed "1NOW 100 107.5 ✓ Pushup, Plank · locks Sun 150" and
  "Plank 11 (119.5 s) · Pushup 65 · Situp 31.5".
- Video c9dec98b: [data-testid=consistency-result] = "+13 lifts banked / Toka: Quota met · 100 / 100 this week · 2 days left / See the
  board →". No "Beat this", no "to pass", no "WHERE ... STANDS".
- Profile: clicked "Load more" (a GET), "My lifts (22)". No line matches /60\s?kg/. The kg regex did match the 7 weighted rows
  (Bicep curl 115kg, ...), so the check could have found a 60kg row. Bodyweight rows show no weight. This covers all 22 rows; the
  prover saw only 20.
- /lift: "The 100 Club · Log this week's lifts / Open" comes before the "Upload a lift / Squat, bench..." tile. No "Plank challenge".
- Correction: window.innerWidth in this Chrome window read **500**, not desktop width (below md=768, so the phone layout and
  BottomTabBar render). The prover's "desktop width only" caveat is inaccurate. Neither of us rendered real desktop width in Chrome;
  the Playwright 1280 run from round 1/2 covers that.
- Layout note (not a fix-hint contradiction): at 500 px the two "· weeks" chips sit side by side and the expanded table renders below
  both chips. The table has no name in it, so only the highlighted chip tells you whose weeks they are. This is cosmetic. I filed it
  only here.

## D-viewer: NOT refuted
Own script (scratchpad refute2/viewer.mjs): fresh headless context at 390x844, addInitScript localStorage.userId=Toka, unrouteAll,
a function matcher that fulfils every non-GET/HEAD/OPTIONS with 204, and a re-goto after the first load. Every page: innerWidth 390,
scrollWidth 390 (no horizontal overflow), build-timestamp 1794067886. 0 pageerror / console errors. Only write attempted:
POST /log-error boot telemetry, fulfilled locally.
`diff prove-viewer-{challenge,home,video}-390.txt` against mine gives rc 0 on all three: byte-identical (64 / 37 / 81 lines, including
"100 / 100", "You lead Situp this week", the tie and bonus-lock lines, the home pill "100 / 100 · 2 days left", the owner-worded block
"Quota met · 100 / 100 this week · 2 days left" with no "Toka:" prefix, no ladder).
Not covered: 1280 (prover only), a real phone, the APK WebView, and the AnalysisStatus reveal after a fresh upload.

## E-apk: NOT refuted
gsutil ls: tomsgym-debug-20261107-111511.apk 4710160 B at 2026-11-07T16:15:13Z (latest object). curl -sI /s/LSOd2h -> HTTP/2 302 to the
signed URL for that object (x-goog-date 20261107T161514Z, expires 604800 s, so 2026-11-14). The download (its own scratchpad dir) is
4710160 B, magic PK\x03\x04, sha256 64f8daa7...4c80, the same as frontend/tomsgym-debug.apk. assets/public/index.html build-timestamp is
1794068093 (> 1789332615). The bundle contains consistency-result, "locks Sun" and "tied on points" (1 file each).
Not covered: installing it on Tom's phone.

## Frontend chunk check
Fetched index.html (1430 B, stamp 1794067886) plus the entry and all 79 referenced chunks (1.3 MB, all 200 javascript).
"consistency-result" = 1 (ConsistencyResult-CdM7ZRYR.js); "locks Sun" 1 and "tied on points" 1 (ChallengeDetail chunk).
"Beat this", "to pass" and "Everyone else" still exist in the source (in the ConsistencyResult chunk, likely the bundled ResultLadder, which I did not confirm, and in ChallengeDetail's
non-consistency branch), and "Plank challenge" still exists in LiftHub for non-consistency challenges. None of them render on the
live consistency pages (C, D), so this is not a defect.

## prod_issues
None. Nothing on the live pages contradicts the bug log's fix hints.

## Cleanup
Chrome tab closed. Playwright context and browser closed. No canary, no SQL. The downloaded APK is in the scratchpad (session-reclaimed).
Leftovers carried forward from the prover: B1b unproven until the next real bodyweight upload; the APK is not installed on the phone.
