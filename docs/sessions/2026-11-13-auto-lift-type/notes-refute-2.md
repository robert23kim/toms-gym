# Refute round 2 (2026-11-14, refuter)

Summary: 12 of 16 claims hold on my own evidence. 4 are refuted: C4 and C5 (the prover already marked both held=false), E (too broad
for its own evidence) and F2 (emulator not re-run, so unverified, not contradicted). Rows created by me: none.
Every browser non-GET was stubbed: one catch-all route fulfils every non-GET, and in r.mjs page-level seenNonGet == stubbed count on all 33 visit records (34 = 34); the identical DB snapshot is the backstop. Scripts and raw output are in scratchpad refute2/
(api.py, db.py, db2.py, r.mjs, c.mjs, e.mjs, w.mjs; api.json, db.json, db-final.json, r.json, e.json, shots/).

## Deployed state (gcloud, read)
my-python-backend-00198-8kd 100% (env AUTO_LIFT_TYPE=0), my-frontend-00207-h4l 100%, bowling-service-00053-fxm 100% on image
situp-13b49b5 (unchanged since the gate, so the engine was not deployed).

## Leaderboard (live_rows_unchanged = true)
Deep diff of GET /competitions/<club>/leaderboard against live-before.json: the only difference is consistency.days_left 3->2.
Could it fail? Yes. The same diff reports days_left, and a mutated copy (rows[0].score=-1) was detected. Rows, re-read at the end:
b7bb417c (1, 375, 147, 14) and 7844e26d (2, 350, 162.5, 14).

## DB (Cloud SQL proxy pid 13926, read-only session, SHOW default_transaction_read_only = on)
- Every public table and timestamp column since 03:40Z: only ShortLink.created_at = 2 (qu1t84 05:53Z and zFFWCs 07:03Z, the APK
  publishes, both pointing at apk/ objects) and Competition.end_date = 1 (the club's future end date, not a write). 0 new User,
  Attempt, LiftingResult or AnalysisNotification rows. 0 ghost users (ids 00000000-0000-4000-8000-*). 0 users created since 11-13.
  Could it fail? The same query with a 2026-11-01 floor returns 28 attempts.
- Baseline timing: round 1's club snapshot is from ~06:29Z, after the 03:40Z start; the bridge to the start is the gate's distribution, all sources 'user' and the unchanged leaderboard. A like-for-like type swap between two attempts before 06:29Z would be invisible.
- Attempt has no update trigger, and the lift-type UPDATE does not set updated_at, so an updated_at check alone could NOT
  detect a type change. Instead: all 28 club rows (id, lift_type, source, status, created_at, updated_at) are identical to round 1's
  snapshot. Club distribution is Pushup 11 / Situp 8 / Plank 8 / Squat 1 (= the gate). lift_type_source is 'user' on all 77 rows,
  and the overall distribution equals the gate's. 0 club LiftingResult rows are updated since start or not completed.
- Snapshot at the start and end of my run: identical.
- GCS videos/: 85 objects, 0 dated 2026-11-14. Could it fail? 6 are dated 2026-11-13, newest 16:51:35Z.

## API probes (real backend, cannot write)
- GET /competitions/<club>: key present, false.
- POST /upload multipart, Auto, ghost user, 16-byte file: 400 "Automatic lift type is not available yet. Pick a lift type."
  The control (Pushup, no file) gives 400 "No video file provided", so the first 400 is the Auto guard. POST /attempts with Auto: same 400.
- POST /attempts/0000.../lift-type: 404 "Attempt not found".
- POST /attempts/1dd00e0f.../lift-type with a ghost user_id: **400** "Changing the lift type is not available on this challenge".
  attempt_routes.py:232 (switch gate) runs before :235 (owner check, 403), so 403 is unreachable while the switch is off.

## Bundle
A live crawl from index.html found 84 files. lift-type-automatic is in 2 (UploadVideo-kIRQFP5l, ChallengeDetail-BN2_rbFb).
Fetch canary: you-row-unknown is present in ChallengeDetail. Stamp 1794639600.

## Browser (my own headless Playwright, fresh context per case, unrouteAll + FUNCTION matcher, every non-GET stubbed)
Counters for r.mjs: 1766 requests intercepted, 35 non-GETs stubbed, 41 competition and 39 result injections fired. Every
injected case has injComp>=1 and injResult>=1.
- Switch, 390: with no injection, the board form shows Squat/Plank/Pushup/Situp, default Squat. /challenges/<club>/upload and
  /lift/upload show Squat/Bench/Deadlift/Pushup/Situp. Marker absent, no Automatic. Positive control (injected true) on the board and
  /challenges/<club>/upload: Automatic first and selected, marker present. /lift/upload had injComp 0, so it is not switch-driven.
  1280: board off = 4 types with no Automatic. Injected on = Automatic first. /challenges/<club>/upload off = no Automatic.
  sw-off-board-390 has the same layout as shots/critic-prod-board-upload-390 (pre-deploy), by eye. Not checked by me: /lift and / for the marker.
- Result line at 390, status + video, each with its own injection counters:
  automatic: owner "Counted as Pushups · Automatic | Change"; stranger text only; noid text + "Yours? Find your profile to change it".
  manual: "Counted as Pushups", Change for the owner only, and the hint for noid.
  confirm (0.38): owner "Is this a pushup? | Yes | Change"; stranger/noid "Counted as Pushups · Automatic" (+ hint for noid).
  unknown: owner status "Pick the lift", video "Which lift is this? | Pick the lift"; stranger no line; noid status shows
  "Which lift was this?" + hint.
  Switch off with the payload automatic: no line.
  1280, automatic state: owner/stranger/noid match 390. The stranger's console 404 comes from the unstubbed placeholder
  /users/<id> GET: it is absent when that GET is stubbed (r.mjs, 0 errors) and present when it is not (e.mjs).
- Change flow: the video page sheet shows Situp/Pushup/Squat/Plank, Re-analyze disabled until a pick, exactly 1 POST
  {lift_type, user_id:<owner>}. With a backend-shaped stub ({attempt_id, lift_type, status:'queued'}, matching attempt_routes.py:273)
  the status page shows "Queued for analysis" (optimistic state: 0 result GETs fired in the 4 s after, so resumed polling was not observed; Yes and 1280 not re-run) and the video page shows "<name>'s Situp" + "Analyzing your form...".
  Fragility (not a prod bug): my first stub omitted lift_type, and the video page then showed "<name>'s" with no type,
  "0.00 lbs Pending" and no analysing card, because onRequeued(res.lift_type) trusts the response.
- Identity at 390, one context with no init script: /find-profile starts empty with empty storage. Submit (lookup stub fired 1x):
  "Welcome back", userId + userEmail set. Pre-filled and editable on /feedback, /signin, board form, /find-profile. Typing does not
  touch storage. Every step is a full page.goto, so storage survives reloads. Email only: pre-filled on /challenges/<club>/upload,
  /lift/upload, board form, /golf/upload, /bowling/upload. Not checked by me: bowling scoresheet, bowling challenge, 1280.
- Forget Me at 390: own profile has 2 in the DOM, 1 visible (269,268, 84x20). Click: both keys cleared, lands on /, /feedback empty,
  still empty after reload. Visitor profile: 0 visible. Not clicked by me at 1280 (the navbar shows it).
- D3: with the placeholder remembered, a real athlete's profile, video page and club board leave both keys unchanged.
- UA1: the status page href is /challenges/<club>?upload=1. Clicking lands on the board form (Squat/Plank/Pushup/Situp).
- Legacy boards: Pushup 4bd57523 and Summer plank a0f27fa4 render ranked rows at 390 and 1280, scrollWidth == innerWidth, 0 errors.
- Fold: sw-off-chup-390 shows the Upload Video button cut off under the tab bar (pre-existing, PD2-3).
- hOverflow false on every render I made (about 70, 390 and 1280). The /profile long-handle case was not reproduced (my username was short).

## APK (F1)
/s/zFFWCs returns 302 to apk/tomsgym-debug-20261114-020259.apk. gs object 4,819,418 bytes; the followed download is 4,819,418 bytes.
capacitor.plugins.json lists @capacitor/preferences; PreferencesPlugin appears 3x in classes2.dex (0 in the other dex files).
lift-type-automatic is in 2 chunks (canary you-row-unknown 1). The Profile chunk carries the md:hidden Forget Me, and the AnalysisStatus
chunk carries "athlete". Emulator (F2) not re-run.

## Phone-user issues seen in screenshots
1. (pre-existing) "Upload Another" lands on the board form defaulted to Squat whatever the athlete just uploaded. The page also
   shows two primary buttons: the form's Upload Video and a floating "Log this week's lifts" (UA-landed-390, same as pre-deploy).
2. (pre-existing) The status page says "YOUR PUSHUP" and "Back to Lift" to a stranger or no-identity viewer of someone else's result.
3. (pre-existing, prover's PD2-2, not reproduced by me) /profile overflows at 390 with a long email @handle.
4. (pre-existing, only by direct URL) /challenges/<club>/upload shows Bench/Deadlift with no Plank and Weight (kg) 60 for the club.
   Nothing in the app links there for a consistency board (ResultLadder.tsx:116 routes it to /challenges/<id>).

## Cleanup
No rows, files or objects created in production. Left as found: Cloud SQL proxy pid 13926. Local scratch only: refute2/ (shots
show public board handles, do not commit).
