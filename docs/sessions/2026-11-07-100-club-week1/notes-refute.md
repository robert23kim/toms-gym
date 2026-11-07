# Refute round 1 (2026-11-07, ~10:57-11:10 ET)

Scratch outputs (not committed): /private/tmp/claude-502/-Users-toka-code-toms-gym/fe49fbdc-4643-4589-9b3f-d81e9b1ac6e9/scratchpad/refute/
(api.py, bundle.py, viewer.mjs, viewer1280.mjs, viewer-*-390.txt, viewer-*-1280.txt, viewer-*.png, live-now.json, monday-now.json).
Nothing in production was written. No commits, nothing staged.

## A. API (own script api.py, urllib; admin token from gcloud secret, len 48, not printed)
- Public leaderboard: 200, 2927 B. The whole JSON document (sort_keys dump) is byte-equal to live-before.json, which is
  stricter than the prover's 5-field compare. Per-user: caleb (1,150,1,107.5,6), Toka (2,150,1,100,5). week_index 1,
  days_left 2, leaders Plank/Pushup caleb, Situp Toka. attempt_count is unchanged for both users, so no live-challenge
  row changed during the run as far as the API shows.
- as_of=2026-11-09T12:00:00-05:00 with the admin token: 200, 2933 B, whole document equal to monday-before.json.
  caleb (1,200,1,0,6), Toka (2,175,1,0,5), week_index 2, type_leaders {}, quotas [125,125].
- as_of with no header: 401 "Admin token required". With a wrong 48-char token: 401, same body.
- /lifting/result: attempt_created_at is present on both leaderboard attempts. c9dec98b gives 2026-11-06T13:24:09.536451+00:00
  and caleb's 5fce96b5 gives 2026-11-05T17:05:31.731053+00:00. That is 2 attempts, one more than the prover checked.
- Could these checks have failed? Yes. The comparison is a full-document equality, and the same script prints DIFF
  per field when values differ.

## Bundle (own bundle.py)
- The page HTML has build-timestamp 1794066143 and entry /assets/index-DnQWVIvq.js (487,698 B; the prover reported 487,703).
  It references 71 chunks, and none of them is an HTML fallback.
- consistency-result appears only in ConsistencyResult-B1jCbbDB.js (1 hit, 5971 B).
- That chunk also contains a "Beat this →" literal. It renders only for `!isOwner && <flag>` and links to /challenges/<id>
  on a consistency board. It is not rendered on the live video page for either viewer (see C and D).

## B. Weight guard
cloudsql is false in the gate, so there was no SQL check and no canary. The guard is still unproven in production.
The API shows attempt counts unchanged (6 and 5), which matches live-before.json.

## C. Chrome (one tab created via tabs_context createIfEmpty, closed at the end, no localStorage, no sign-in)
- Challenge page, anonymous, about 500 px wide. Console tracking started, then the page was reloaded, so its load is
  covered: 0 errors. The text matches the prover line for line: "Ongoing · ends Sun 27 Dec", "WEEKLY QUOTA",
  "Week 1 of 8 · 2 days left", the bonus-lock line, the tie line, and no "Everyone else".
- **The weeks-toggle anomaly does not reproduce.** I clicked "Toka · weeks" once (find ref, then left_click by ref).
  The chip turned to ▴ and the table rendered "WEEK QUOTA LIFTS MET BONUSES POINTS / 1NOW 100 100 ✓ Situp · locks Sun 150 /
  Plank 8 (82.8 s) · Pushup 52 · Situp 40". The screenshot shows it expanded. The prover's leftover was a tooling
  artefact of that session, not a product defect. It was still not checked on a real phone.
- Video page c9dec98b, anonymous: "+13 lifts banked", "Toka: Quota met · 100 / 100 this week · 2 days left",
  "See the board →". No "Beat this" and no "to pass". Clean reload: 0 console errors. One "Error fetching video data"
  came from my own first navigation to a mistyped attempt id (c9dec98b-0000-...). It was cleared, the real URL was
  reloaded, and the error did not recur.
- /lift: "The 100 Club · Log this week's lifts / Open" sits above "Upload a lift". No "Plank challenge".
- /profile/Toka: no "60kg". The rows read "Nov 6 Situp A, Nov 6 Pushup C, Nov 6 Plank 1:22, Nov 3 Situp A, Nov 2 Pushup C".
  Bicep rows still carry kg. 0 console errors. Only the first page (20 of 22) was checked.

## D. Playwright viewer (own script: fresh context, addInitScript userId=Toka, unrouteAll, every non-GET/HEAD/OPTIONS fulfilled 204)
- 390x844 (isMobile, hasTouch, DSF 3; the toggle was opened by tap). The challenge, home and video pages all read back
  innerWidth 390 and scrollWidth 390, so there is no horizontal overflow; profile and lift do the same.
  The only write attempted was POST /log-error (boot telemetry), and it was fulfilled locally. No pageerror and no console error.
  Diff against prove-viewer-*-390.txt: home and video are identical. The challenge pre-toggle text is identical. The
  post-toggle parts differ only because my script captures the whole body and the prover's captures the table. Both
  contain "Situp · locks Sun" and "Plank 8 (82.8 s) · Pushup 52 · Situp 40". The ring reads "100 / 100 LIFTS", and the
  page shows "You lead Situp this week", the tie line and the bonus line. Home: "The 100 Club / 100 / 100 · 2 days left".
  Video: owner wording "Quota met · 100 / 100 this week · 2 days left", with no prefix.
  Screenshot viewer-challenge-390.png: the layout holds at phone width. The week table fits, and the bonuses cell wraps
  to "Situp · / locks Sun". The mid-page "Tom's Gym" bar is the fullPage capture of the sticky header, not a layout bug.
- 1280x800: the home and video texts are identical to prove-viewer-*-1280.txt, and so is the challenge pre-toggle text.
  The table row reads "1NOW 100 100 ✓ Situp · locks Sun 150" with the per-type line. innerWidth = scrollWidth = 1280.
- Scanned all 5 viewer pages at 390 for "Beat this", "to pass", "Everyone else", "Plank challenge" and "60kg": 0 hits each.
- Not covered: a real phone, the APK WebView and iOS Safari. The AnalysisStatus reveal was not checked.

## E. APK
- curl -sI /s/kwA1J7 returns a 302 to the signed .../apk/tomsgym-debug-20261107-104641.apk. gsutil shows 4679930 B at
  2026-11-07T15:46:44Z.
- Downloaded through the short link with curl -sL: sha256 c14dff77...7284. That equals frontend/tomsgym-debug.apk and
  the prover's copy. index.html build-timestamp is 1794066371, and there is 1 ConsistencyResult entry.
- Side note: the bucket still holds a non-versioned gs://.../apk/tomsgym-debug.apk (4742008 B, 2026-09-13T19:50:40Z).
  Any older link to that object still serves the Sep-13 bundle. It is not a defect of this run, but Tom must install
  from the new short link.
- Not covered: installing on the phone.

## Prod issues
None. Nothing on the live pages contradicts the bug-log fix hints: no ladder, no 60kg, the copy matches, and the
phone width does not overflow.

## Cleanup
The Chrome tab is closed (the group was auto-removed). The Playwright contexts are closed. No canary. Scratch files are
in the session scratchpad only.
