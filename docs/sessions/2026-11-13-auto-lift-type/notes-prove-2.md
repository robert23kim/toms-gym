# Prove round 2 in production (2026-11-14, prover)

Summary: A, B, D, E, F held; C held except the wrong-user call answers 400, not 403 (switch gate first, deviation 8).
Rows created in production: none. Not exercised in production: a real automatic upload and a real change + re-analysis.

Deployed state probed 07:05Z (gcloud): backend my-python-backend-00198-8kd 100% (env AUTO_LIFT_TYPE=0), frontend
my-frontend-00207-h4l 100% (footer stamp "v2026-11-14 07:00 UTC" seen in the 1280 shots = round-2 bundle), engine
bowling-service-00053-fxm image situp-13b49b5 (unchanged, no auto support).
Rows created in production: NONE. Target for read-only probes: club attempt 1dd00e0f-807b-46fb-a47d-9ec637b698d4
(owner 7844e26d..., a completed Pushup from the board).
Scripts and raw output: scratchpad prove2/ (snap.py, db.py, api.py, bce.mjs, d2.mjs, ovf.mjs, ua.mjs, *.out, *.json).
Shots and logs: shots-prod/r2/ (round 1's shots-prod/*.png left as they were).

## DB (Cloud SQL via proxy pid 13926, read-only session, SHOW default_transaction_read_only = on)
snap-before (07:05Z): User 158, UserCompetition 33, Attempt 77, LiftingResult 61, club attempts 28, newest Attempt
2026-11-13 16:51:35Z, newest User 2026-09-09; target Attempt sha d1520fac..., LiftingResult sha 3075de5e..., fields
Pushup / source user / confidence null / completed / weight 0 (same hashes as round 1).
db.py, every public table and timestamp column vs run start 03:40Z: 0 rows created/updated in any table except
ShortLink (2 rows since start, = the two APK publishes qu1t84 05:53Z and zFFWCs 07:03Z; not canaries, not mine). Competition shows 1 row with end_date >= start: the club's future end date
(2026-12-28), not a write (updated_at unchanged).
After the API probes: snap byte-identical (cmp).

## A. Leaderboard unchanged
GET /competitions/<club>/leaderboard 200. Per user_id (rank, score, this_week.lifts, attempt_count) vs live-before.json:
b7bb417c (1, 375, 147, 14), 7844e26d (2, 350, 162.5, 14), identical. Full deep diff: the only difference is
consistency.days_left 3 -> 2 (calendar). The diff could fail: it did report days_left.
Legacy boards (Playwright, 390 + 1280, from the real API): Pushup challenge 4bd57523 (reps: "35reps | 30 clean of 35")
and Summer plank challenge a0f27fa4 (time: "245.0s") render ranked rows; /challenges list loads; 0 console errors, no overflow.

## B. Switch state
- API: GET /competitions/<club> -> competition.auto_lift_type_enabled == false (key present).
- API: POST /upload multipart, lift_type Auto, user_id = nonexistent UUID ...00b0, no email, 16-byte file ->
  400 "Automatic lift type is not available yet. Pick a lift type." POST /attempts with Auto and a nonexistent
  user_competition_id -> 400, same message. Nothing created (snap identical, db.py 0 rows since start).
  /upload/finalize not probed (it checks the blob exists before the Auto guard; route tests only).
- Browser, production as served (no injection), 390 + 1280: board inline form (/challenges/<club>?upload=1) options
  Squat/Plank/Pushup/Situp, default Squat, Weight (lbs) "0 for air squats." shown; /challenges/<club>/upload and
  /lift/upload Squat/Bench Press/Deadlift/Pushup/Situp default Squat, weight shown. "lift-type-automatic" absent from
  document.outerHTML and 0 "Automatic" options on those three plus /lift and /. Status and video pages with the real
  payload, and with the result payload injected as automatic but the switch left false: no lift-type line.
- Positive control (same prod bundle, competition GET injected auto_lift_type_enabled=true): Automatic first and
  selected, helper "We'll work out the lift from your video. You can change it after.", weight hidden, on the board
  form and /challenges/<club>/upload at both widths. So the "absent" result could have failed. (/lift/upload never
  fetches the club competition, so its absence holds because it is not switch-driven.)
- Read side by side: B-board-upload-390 vs shots/critic-prod-board-upload-390 (pre-deploy prod): identical layout,
  options and helper by eye (submit measured 499-547 this round; the pre-deploy value was not measured). Also
  B-challenge-upload-390 vs shots/prod-challenge-upload-390: identical by eye.

## C. Result line and Change flow (prod bundle; competition + result GETs injected per state; every non-GET stubbed)
| state | owner (localStorage userId = attempt user) | stranger (placeholder ...c0de) | no identity |
|---|---|---|---|
| automatic 0.92 | "Counted as Pushups · Automatic" + Change | same text, no button | same + "Yours? Find your profile to change it" |
| manual | "Counted as Pushups" + Change | text only | text + hint |
| confirm 0.41 | "Is this a pushup?" Yes / Change | "Counted as Pushups · Automatic", no button | same + hint |
| unknown (Auto) | status "Pick the lift"; video "Which lift is this?" + Pick the lift | no line | no line |
Identical on the status page and the video page at 390; at 1280 only the owner column was run (stranger and
no-identity at 1280 not covered).
- Change flow (status + video, 390 + 1280): sheet lists Situp/Pushup/Squat/Plank (board types, no Automatic), Pushup
  checked, Re-analyze disabled until another pick; Situp + Re-analyze sent exactly 1
  POST /attempts/1dd00e0f.../lift-type {"lift_type":"Situp","user_id":"7844e26d..."} (stubbed queued); sheet closed;
  status page "Queued for analysis", video page "Analyzing your form...".
- Round-2 copy (CP1) on the queued status page, 390 + 1280: "<leader> leads at 375 pts · 2 athletes on the board".
- Yes on confirm sent {"lift_type":"Pushup","user_id":<owner>} (stub; the real backend would answer unchanged).
- Real API, calls that cannot write: POST /attempts/00000000-0000-4000-8000-000000000000/lift-type -> 404
  "Attempt not found". POST /attempts/1dd00e0f.../lift-type {lift_type Pushup, user_id nonexistent UUID} -> **400
  "Changing the lift type is not available on this challenge", NOT 403**: the switch gate runs before the owner check
  (contract deviation 8), so 403 is unreachable while AUTO_LIFT_TYPE=0 and is covered by route tests only. Attempt and
  LiftingResult rows byte-identical afterwards (sha above).
- NOT exercised in production: a real end-to-end automatic upload and a real change + re-analysis (switch off,
  engine without auto support, no canary rows).
- Console: 0 errors for owner and no-identity runs; stranger runs show 1 console 404 each (same as round 1, the
  placeholder user's profile GET; URL not captured this round, so that attribution is assumed).

## Round-2 fixes, Upload Another (UA1), prod bundle
- Completed club status page /lift/status/<aid>?challenge=<club>: "Upload Another" href /challenges/<club>?upload=1 at
  390 and 1280. Without ?challenge: /lift/upload (unchanged path). Clicking it (ua.mjs) lands on the board form:
  Squat/Plank/Pushup/Situp, "Weight (lbs)", no overflow, 0 errors, nothing submitted. Failed-state "Upload Again" not
  rendered in prod (no failed attempt to point at); jest only.

## D. Identity (d2.mjs, one context per width, no init script; lookup GET stubbed to placeholder ...d00d / prove-placeholder@example.com)
- Empty storage: /find-profile email empty, storage empty. Submit: "Welcome back, Prove", userId + userEmail set
  (lookup stub fired 1x).
- Id known: email pre-filled AND editable (typed value accepted, storage unchanged while typing) on the board form,
  /find-profile, /signin, /feedback. Hidden by design while the id is known: /challenges/<club>/upload, /lift/upload,
  /golf/upload, /bowling/upload, /bowling/scoresheet/upload, /bowling/challenge/<id> (after clicking Upload Video).
- Email remembered, id removed: pre-filled + editable on the board form, /challenges/<club>/upload, /lift/upload,
  /golf/upload, /bowling/upload, /bowling/scoresheet/upload and /bowling/challenge/<id> (form opened via Upload Video;
  closes round 1's browser gap for BowlingChallenge).
- Reload of /feedback keeps id + email and the pre-fill.
- Never replaced silently: with the placeholder remembered, opening a real athlete's profile, their video page and the
  club board left userId/userEmail unchanged (no screenshots of the athlete pages kept).
- Forget Me (DF1 fix, prod bundle): at 390 Home -> exact "Me" tab -> /profile/<placeholder>: 2 "Forget Me" in the DOM,
  exactly 1 visible (at 269,304, 84x20, beside Change avatar); click -> storage cleared, lands on /, /feedback email
  empty and still empty after reload. Visitor profile at 390: 0 visible. At 1280 own profile: 1 visible (the navbar's;
  the profile one is md:hidden), click clears the same way. Logout variant (password user) not exercised.
- Not reachable in the app (not mounted by any route): FindProfile dialog, RegistrationForm, CreateProfile,
  PasswordResetForm: jest only. Upload-response identity overwrite paths: jest only.
- Console: 0 errors on every identity page. Non-GETs: boot /log-error telemetry and a pre-existing bowling
  trajectory.png resource-error report (both stubbed).
- hOverflow true on /profile/<id> at 390 (own and visitor alike). ovf.mjs: the only element past 390 px is the
  "@<username>" span (scrollWidth 407 with prove-placeholder@example.com; 390 with p@x.io), not Forget Me (right edge
  353). Pre-existing long-handle overflow, noted in round 1 for a real athlete's profile.

## E. Design (shots-prod/r2/, both widths)
Read by eye: D-own-profile-390 (Forget Me beside Change avatar, same muted text style), D-own-profile-1280 (navbar
control only), inj-status-change-flow-390 (queued copy), B-status-real-owner-390 (Upload Another), inj-video-sheet-390
(dark sheet, YouRow-blue selected chip, Re-analyze CTA), inj-board-upload-auto-390 vs B-board-upload-390 vs
shots/critic-prod-board-upload-390, inj-status-confirm-owner-1280, inj-status-automatic-owner-390 and
inj-video-automatic-owner-390 (line + Change at y~358 / ~530, above the fold), UA-landed-390 (board form, lbs),
B-challenge-upload-390 vs shots/prod-challenge-upload-390, F-emulator-profile-before-forget, F-emulator-after-forget-restart.
Overflow: false on all 68 B/C renders (render-log.jsonl) and every identity page except /profile at 390 (above, pre-existing).
Fold at 390: board form submit 499-547 (off) / 431-479 (Automatic) after scrolling to the form; /challenges/<club>/upload
submit 720-760 with Automatic (above the tab bar at 779); switch off it sits at 778-818 under the tab bar, same as
pre-deploy (pre-existing). Result line + Change above the fold on both result pages. Forget Me at y 304 on the Me page.
Not read by eye: the remaining shots, checked only by logged metrics.

## F. APK (published tomsgym-debug-20261114-020259.apk)
- gs object exists: 4,819,418 bytes, 2026-11-14T07:03:01Z. Short link /s/zFFWCs -> 302 to the signed object; the
  followed download (fresh dir scratchpad apk-r2/dl) is cmp-identical to a gsutil copy.
- Unzipped download: capacitor.plugins.json lists @capacitor/preferences (PreferencesPlugin), class in classes2.dex
  (2 hits; AppPlugin canary 8 in the same file); lift-type-automatic in ChallengeDetail-BNJQ7Ren.js and
  UploadVideo-CXuVIMFk.js; stamp 1794639762 in index.html + index chunk (app footer reads v2026-11-14 07:02 UTC);
  round-2 fixes present: Profile chunk carries the md:hidden Forget Me control, AnalysisStatus chunk the athlete copy.
- Emulator (AVD t30g, headless, published APK installed, pm clear; WebView driven over raw CDP via
  webview_devtools_remote; scripts emu-ctl.mjs + emu2.mjs, log prove2/emu-steps.log; WebView width 412 css px):
  1. first run: localStorage empty, no CapacitorStorage.xml;
  2. placeholder identity (...e0e0 / prove-emulator@example.com) written to localStorage, force-stop + start:
     localStorage kept AND shared_prefs/CapacitorStorage.xml holds userId + userEmail (so the next step can fail);
  3. localStorage.clear(), 15 s, force-stop + start: userId + email restored into localStorage from Preferences;
  4. Forget Me (DF1 on the APK): navigated in-app to /profile/<placeholder>; the profile GET 404s (placeholder, real
     API, read-only) and the error state shows "Try Again" + one visible "Forget Me" (F-emulator-profile-before-forget.png);
     clicking it cleared localStorage and left CapacitorStorage.xml as an empty <map />;
  5. 15 s, force-stop + start: localStorage still empty, prefs still empty -> the forgotten identity is not restored
     (F-emulator-after-forget-restart.png). Step 5 is also the control for step 3.
  Seeding was by direct localStorage writes, not through remember() (no UI path to stub the lookup over raw CDP), so
  remember()'s write-through is covered by jest only. The emulator app ran UNSTUBBED against production: its boot
  /log-error telemetry POSTs (platform=capacitor log lines in Cloud Run) and the GET /users/<placeholder>/profile (404)
  reached the real backend. No DB row resulted (db-final identical; /log-error writes logs, not rows). logcat tail had only chromium tile-memory warnings and system
  JavaBinder lines, no app Uncaught. Emulator stopped (adb emu kill). A real phone is not covered.

## Final state (07:30Z)
snap-final byte-identical to snap-before (counts, newest rows, target Attempt/LiftingResult hashes); db.py tables and
club rows identical to the start of this run, 0 Auto / non-user rows; ShortLink rows since 03:40Z = qu1t84, zFFWCs
(APK publishes by the deploy agents). GCS videos/: 85 objects, 0 dated 2026-11-14, canary newest 2026-11-13T16:51:35Z
present. Board (rank, score, this_week.lifts, attempt_count): (1,375,147,14), (2,350,162.5,14). Revisions re-probed 07:33Z: 00198-8kd / 00207-h4l / 00053-fxm, 100% each.
Cloud SQL proxy pid 13926 left running.

## Defects / follow-ups
1. (backend, contract vs design) POST /attempts/<real id>/lift-type with a wrong user_id answers 400 "Changing the
   lift type is not available on this challenge", not 403, while AUTO_LIFT_TYPE=0 (switch gate before owner check,
   deviation 8). 403 is unproven in production; route tests only.
2. (frontend, pre-existing) /profile/<id> overflows horizontally at 390 when the @username is a long email
   (scrollWidth 407 with a 29-char email), own profile and visitor alike; Forget Me itself sits inside the viewport.
2b. (frontend, pre-existing) with the switch off, /challenges/<club>/upload puts Upload Video at 778-818 px at 390,
   under the bottom tab bar (779): primary action not above the fold; same as the pre-deploy screen.
3. (design call, from fix-2) the phone Forget Me is an 84x20 text button with no confirm; matches Change avatar's style.
4. Not covered anywhere in production: Logout variant on the phone profile, upload-response identity overwrite,
   /upload/finalize Auto guard, failed-state "Upload Again" link, a real end-to-end automatic upload, a real
   re-analysis, a real phone.
