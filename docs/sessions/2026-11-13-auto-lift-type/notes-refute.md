# Refute round 1 (2026-11-14, refuter)

Scripts and raw output: scratchpad refute/ (db.py, sl.py, api.py, r.mjs, r2.mjs, r3.mjs; db.json, db-final.json, api.json,
lb-now.json, r.json, r2.json, shots/). Rows created by the refuter: none. Every browser non-GET was stubbed (the only one
seen was the boot /log-error telemetry, plus the stubbed lift-type POST in the change flow).

## Deployed state (gcloud, read)
my-python-backend-00197-vvw (100%, AUTO_LIFT_TYPE=0), my-frontend-00206-dxd (100%), bowling-service-00053-fxm
image situp-13b49b5 (unchanged from the gate, so the engine was not deployed).

## Leaderboard (live_rows_unchanged = true)
Full deep diff of GET /competitions/<club>/leaderboard against live-before.json: the only difference is
consistency.days_left 3 -> 2 (the calendar moved). Every row field, type_leaders, weeks and history are identical.
Rows: b7bb417c 1/375/147/14, 7844e26d 2/350/162.5/14, again at the end. Could fail: yes, the same diff reported days_left.

## DB (Cloud SQL, read-only session, SHOW default_transaction_read_only = on)
Every public table, every timestamp column, counted against 2026-11-14 03:40Z: 0 rows created or updated in User,
UserCompetition, Attempt, LiftingResult, AnalysisNotification, Ticket, etc. The only row since start is
ShortLink qu1t84 (05:53:03Z) = the APK publish, not a canary. ShortLink has no hit-counter column (closes X1's open point).
Attempt lift_type_source is 'user' on all 77 rows. 0 rows have Auto or a non-user source. All 28 club attempts have
updated_at == created_at, the newest being 2026-11-13 16:51:35Z. Users with example/prove/placeholder/canary emails
were all created in 2025-04 to 2026-07 (pre-existing). Snapshot at the end of my run: identical (tables and club rows).
GCS videos/: 86 lines, 0 objects dated 2026-11-14, canary newest 2026-11-13T16:51:35Z present.

## API probes (real backend)
- GET /competitions/<club>: key present, auto_lift_type_enabled false.
- POST /upload multipart, Auto, ghost user, 16-byte video: 400 "Automatic lift type is not available yet. Pick a lift type."
  Control, same form with Pushup and no video: 400 "No video file provided", so the 400 above is the Auto guard's message.
- POST /attempts with Auto: 400 with the same message.
- POST /attempts/0000.../lift-type: 404 "Attempt not found".
- POST /attempts/1dd00e0f.../lift-type with a ghost user_id: **400** "Changing the lift type is not available on this
  challenge", not 403 (C4 is false as written). The DB afterwards was identical.

## Bundle
Live crawl from index.html: 83 chunks. lift-type-automatic is in 2 (ChallengeDetail-Cy4MwaX4, UploadVideo-BbEAzVdN).
Fetch canary: you-row-unknown is present (ChallengeDetail). Web build stamp is 1794635342. The APK is a separate build
(stamp 1794635557, different chunk hashes).

## Browser (my own scripted headless Playwright, 390x844, fresh context per case, unrouteAll + FUNCTION matcher)
Injection counters per case are in r.json. Every "inj" case had injComp >= 1 and injResult >= 1, so the stubs fired.
- Switch off: board form (Squat/Plank/Pushup/Situp), /challenges/<club>/upload and /lift/upload (Squat/Bench/Deadlift/
  Pushup/Situp). There is no Automatic option, the marker is absent from the DOM, and the select is present (canary).
  Positive control (comp GET injected true, fired once each): Automatic is first and selected on the board and on
  /challenges/<club>/upload, with the helper shown and weight hidden. **/lift/upload never fetches the club competition
  (injComp 0)**, so its "absent" result could not have failed. It holds there only because that page is not
  switch-driven.
- Result line on the status and video pages:
  automatic: owner "Counted as Pushups · Automatic" + Change; stranger the same text with no button; no identity the same
  text + "Yours? Find your profile to change it".
  manual: "Counted as Pushups", with Change for the owner only, and the hint for no identity.
  confirm (0.40): owner "Is this a pushup?" Yes/Change; stranger "Counted as Pushups · Automatic" with no button;
  no identity the same + hint.
  Switch off with the result injected automatic (injResult 1, injComp 0): no line.
- Change flow (status page): the sheet lists Situp/Pushup/Squat/Plank and Re-analyze is disabled until another pick.
  Situp + Re-analyze sent exactly 1 POST /attempts/1dd00e0f.../lift-type {"lift_type":"Situp","user_id":<owner>}
  (stubbed). The page then shows "Queued for analysis".
- Identity, one context, no init script: /find-profile from empty storage (email empty, storage empty). Submitting a
  placeholder (lookup stubbed, fired 1) set userId + userEmail. Pre-filled and editable on /feedback, /signin and the
  board form. Typing changed the value but not storage, and a reload kept everything. After removing userId: pre-filled
  on /challenges/<club>/upload, /lift/upload and the board form.
- 1280 + legacy: the Pushup (reps) and Summer plank (seconds) boards render ranked rows at 390 and 1280 with no overflow
  and 0 console errors. At 1280, the board with Automatic and the status line with Change have no overflow.
- Forget Me at 1280 cleared both keys, and /feedback was empty after reload. At 390, "Forget Me" is in the DOM on
  /profile/<id>, /, /lift and /feedback but isVisible() is false on every one (navbar `hidden md:flex`, Navbar.tsx:137,
  AuthButton inside it). There is no other forget/sign-out control. DF1 is confirmed.
- D3: with the placeholder remembered, opening a real athlete's profile, their video page and the club board left
  userId/userEmail unchanged.
- Console: 0 app errors, apart from my own boot navigation to a nonexistent route, and the 400/500 resource errors on
  /profile/<placeholder> at 390 caused by the fake id (other per-user endpoints not stubbed).
- hOverflow false on every render I made.

## APK
The gs object is 4,819,425 bytes at 05:53:02Z. Backend /s/qu1t84 returns 302 to the signed object. The followed
download is cmp-identical to the gsutil copy. capacitor.plugins.json lists @capacitor/preferences. lift-type-automatic
is in ChallengeDetail-C8lMhlgC and UploadVideo-CBAK2I7s (canary you-row-unknown present). Stamp 1794635557.
Emulator (F2) NOT re-run by me.

## DF2 refuted
BowlingChallenge pre-fill has a jest test: commit 9ef82df (00:29, before the prove notes), emailPrefill.test.tsx
describe("BowlingChallenge upload email"), 2 cases, both passed in jest-fix.json (917 tests, 0 failed). A browser proof
is still missing.

## Screens read by eye (390)
line-confirm-owner-status, line-automatic-noid-video, change-sheet, change-flow-status, sw-off-board, sw-on-ctrl-board,
id-chup-emailonly, d2-me-390. No clipping. The Change sheet is in the existing dark style.
Phone-user issues:
1. (DF1) There is no way to forget a remembered identity on a phone or in the APK. With the Preferences mirror it now
   survives WebView clears.
2. (pre-existing, 2026-07-06) "Upload Another" on a club result (/lift/status/<id>?challenge=<club>) links to
   /lift/upload (AnalysisStatus.tsx:63/355). That page posts competition_id '1' (UploadVideo.tsx:160), defaults to
   Squat with Weight (kg) 60 and has no Plank. A club athlete who taps it uploads outside the 100 Club, and the board
   form labels weight in lbs while this page uses kg.
3. Minor copy: the queued screen reads "caleb.li.larson leads at 375 pts · 2 on the board", and "2 on the board" is
   unclear. The confirm prompt sits above "+25 lifts banked", which the design intends but which reads as already decided.
