# Prove round 1 in production (2026-11-14, prover)

Deployed state probed: backend my-python-backend-00197-vvw (AUTO_LIFT_TYPE=0), frontend my-frontend-00206-dxd,
engine bowling-service-00053-fxm (no auto support), APK tomsgym-debug-20261114-005300.apk.
Scripts and raw outputs: scratchpad prove/ (snap.py, api.py, api.json, snap-*.json, live-prove.json).
Target attempt for read-only probes: 1dd00e0f-807b-46fb-a47d-9ec637b698d4 (owner's own latest club Pushup, from the board).
Rows created in production: NONE.

## DB snapshot (read-only session, SET default_transaction_read_only = on)
Before probes: User 158, UserCompetition 33, Attempt 77, LiftingResult 61, club attempts 28, newest Attempt
2026-11-13 16:51:35Z, newest User 2026-09-09; target Attempt sha d1520fac..., LiftingResult sha 3075de5e...,
fields lift_type Pushup / source user / confidence null / status completed / weight 0.
After the API probes: byte-identical JSON (counts, newest timestamps, both row hashes).
GCS videos/: 86 lines listed (canary: newest object is the real 2026-11-13T16:51:35Z upload), no object dated 2026-11-14.

## A. Leaderboard unchanged
GET /competitions/<club>/leaderboard (200), compared per user_id with live-before.json:
b7bb417c 1/375/147 (attempt_count 14), 7844e26d 2/350/162.5 (14): rank, score, this_week.lifts identical; week 2 (2026-11-09).
Legacy boards: see browser section.

## B. Switch state (API)
- GET /competitions/<club>: competition.auto_lift_type_enabled == false (key present).
- POST /upload multipart, lift_type Auto, user_id = nonexistent UUID ...00b0, no email, 16-byte x.mp4:
  400 {"error":"Automatic lift type is not available yet. Pick a lift type."} (the Auto guard, not a file/blob error).
- POST /attempts, lift_type Auto, nonexistent user_competition_id: 400, same message.
- /upload/finalize NOT probed: it checks the GCS blob exists before the Auto guard, so a fake object returns
  "Uploaded file not found in storage" and proves nothing; its guard is covered by route tests only.
- Nothing created: DB counts and newest timestamps unchanged, no new GCS object.

## C. Change endpoint (API, cannot write)
- GET /lifting/result/<aid>: lift_type Pushup, lift_type_source "user", lift_type_confidence null, needs_lift_type false
  (migration 020 fields are live on the payload); the participant attempt GET carries the same four.
- POST /attempts/00000000-0000-4000-8000-000000000000/lift-type -> 404 {"error":"Attempt not found"}.
- POST /attempts/<aid>/lift-type {lift_type: "Pushup" (its current type), user_id: nonexistent UUID} ->
  **400 "Changing the lift type is not available on this challenge", not 403**. By design (deviation 8): the switch gate
  runs before the owner check, so the 403 branch is unreachable in production while AUTO_LIFT_TYPE=0; 403 is covered
  by route tests only. Attempt and LiftingResult rows byte-identical afterwards (sha above).
- Not exercised in production: a real end-to-end automatic upload, a real change + re-analysis (switch off, engine has
  no auto support, and no canary rows were created).

## Browser runs (all scripted headless Playwright against the production frontend)
Fresh context per shot (serviceWorkers blocked), page.unrouteAll() first, one FUNCTION route matcher; every non-GET
fulfilled by a stub (recorded with body), GETs go to the real API unless injected; 1.5 s + networkidle after navigation.
Collected per page: console errors, pageerror, failed requests, horizontal overflow. Logs: shots-prod/render-log.jsonl,
render-results-B.json, render-results-C.json, identity-log-390.jsonl, identity-log-1280.jsonl. Scripts: scratchpad prove/bce.mjs, d.mjs.

### A. Legacy boards
/challenges list, Pushup challenge (4bd57523, reps: "35reps | 30 clean of 35") and Summer plank challenge (a0f27fa4,
time: "245.0s") load at 390 and 1280 with ranked rows, 0 console errors, no overflow.

### B. Switch off, no injection (390 and 1280)
- Club board inline form (/challenges/<club>?upload=1): select present (canary), options Squat/Plank/Pushup/Situp,
  default Squat, weight field shown with "0 for air squats." = the pre-deploy prod screen critic-prod-board-upload-390
  (Read side by side: identical). No "lift-type-automatic" anywhere in document.outerHTML, 0 "Automatic" options.
- /challenges/<club>/upload and /lift/upload: select present, Squat/Bench Press/Deadlift/Pushup/Situp, default Squat,
  weight 60 shown; identical to pre-deploy prod-challenge-upload-390. Marker absent.
- /lift (LiftHub) and / (Home): marker absent.
- Result pages with the real payload, owner identity: no lift-type line (status and video page).
- Result pages with the result payload injected as automatic but the competition left as served (switch false): still
  no line on either page -> the switch gates the line.
- Positive control (competition GET injected auto_lift_type_enabled=true, same prod bundle): Automatic is the first
  option and selected, helper "We'll work out the lift from your video. You can change it after.", weight hidden, on
  both pickers at both widths. So the "absent" result above could have failed.
- Console: 0 errors on every B page.
- Observation (pre-existing, unchanged by this run): /challenges/<club>/upload lists the generic lift set (Bench Press,
  Deadlift, no Plank) rather than the club's types; with the switch on, Automatic is offered above those options.

### C. Result line and Change (competition + result GETs injected; proves the deployed bundle, not the backend)
Attempt 1dd00e0f (owner's own Pushup). Owner = localStorage userId equal to the attempt's user (read-only; every
non-GET stubbed), stranger = placeholder UUID ...c0de, no identity = empty storage.
| state | owner | stranger | no identity |
|---|---|---|---|
| automatic (0.92) | "Counted as Pushups · Automatic" + Change | same text, no button | same text + "Yours? Find your profile to change it" |
| manual | "Counted as Pushups" + Change | text, no button | text + find-profile hint |
| confirm (0.41) | "Is this a pushup?" Yes / Change | "Counted as Pushups · Automatic", no button | same + hint |
| unknown (Auto) | status: "Pick the lift" (primary); video: "Which lift is this?" + Pick the lift | no line | no line (video: hint) |
Same on status and video page; owner states also at 1280.
- Change flow (status + video, 390 + 1280): sheet lists Situp/Pushup/Squat/Plank (board types, no Automatic), current
  Pushup checked, Re-analyze disabled until a different pick; picking Situp + Re-analyze sent exactly one
  POST /attempts/1dd00e0f.../lift-type body {"lift_type":"Situp","user_id":"7844e26d..."}; sheet closed; status page
  shows "Queued for analysis", video page "Analyzing your form..." with title "Toka's Situp" and a Pending badge.
- Yes on confirm sent {"lift_type":"Pushup","user_id":<owner>} (stub answered queued, so the page re-entered analysing;
  the real backend would answer "unchanged").
- Console: 0 errors for owner and no-identity runs. Stranger runs show 1 console 404 each:
  GET /users/<placeholder>/profile (the placeholder id does not exist). Artefact of the fake id, not new behaviour.

### D. Identity (one context per width, no init script; lookup GET stubbed to placeholder 00000000-...-d00d / prove-placeholder@example.com)
- Empty storage: /find-profile email empty, storage empty. Submitting it: "Welcome back, Prove", localStorage userId +
  userEmail set.
- With the id known: email pre-filled and editable (typed value accepted, storage unchanged while typing) on the club
  board form (shown as before), /find-profile, /signin, /feedback. Hidden by design (id known): /challenges/<club>/upload,
  /lift/upload, /golf/upload, /bowling/upload, /bowling/scoresheet/upload.
- Email remembered, id removed (page.evaluate once): pre-filled + editable on board form, /challenges/<club>/upload,
  /lift/upload, /golf/upload, /bowling/upload, /bowling/scoresheet/upload.
- /bowling/challenge/<bowling id>: no email input rendered (the only bowling challenge is completed, so no upload form):
  BowlingChallenge pre-fill NOT exercised in a browser, and per notes-impl-frontend it has no jest test either.
- Not reachable in the app (components not mounted by any route): FindProfile dialog, RegistrationForm, CreateProfile,
  PasswordResetForm; their pre-fill is jest-only and moot.
- Reload of /feedback keeps id + email and the pre-fill.
- Browsing a real athlete's profile, video page and the club board with the placeholder remembered: storage unchanged
  (never replaced silently). Upload-response overwrite paths are covered by jest only.
- Forget Me at 1280 (top nav): storage cleared, /feedback email empty, still empty after reload.
- Forget Me at 390: NOT reachable. The first scripted attempt clicked "Home" (substring match); re-run (me390.mjs) with an
  exact "Me" match: Me opens /profile/<placeholder> whose visible controls are Back, Change avatar, Lift, Upload your first
  lift, Track Weekly Lifts, footer links and tabs; no "Forget" text anywhere (D-me-tab-390.png). The navbar holding
  Forget Me is `hidden md:flex` (same at 74a2519, so pre-existing). The only other forget() call is the ChallengeDetail
  upload toast action after an adopted identity. With the APK now mirroring identity to native Preferences, a phone/APK
  user has no standing UI way to clear it. "Forget Me clears it" is proven at 1280 only.
- Console: 0 errors on every identity page; non-GETs were only the boot telemetry and a pre-existing missing bowling
  trajectory.png resource-error report (both stubbed).
- Observation (pre-existing): a public /profile/<id> at 390 shows the athlete's email and overflows horizontally.

### E. Design (shots-prod/, 129 files; B-* = production as served, inj-* = production bundle with injected GETs, D-* identity, F-* emulator)
Read and compared with shots/: B-board-upload-390 vs critic-prod-board-upload-390 and B-challenge-upload-390 vs
prod-challenge-upload-390 (pre-deploy): identical. inj-board-upload-auto-390, inj-challenge-upload-auto-390,
inj-status-automatic-owner-390, inj-video-automatic-owner-390, inj-video-sheet-390, inj-video-change-flow-390,
inj-status-change-flow-390, inj-status-unknown-owner-390, inj-status-confirm-owner-1280, inj-video-confirm-owner-1280:
inj-video-sheet-1280, inj-board-upload-auto-1280, D-known-signin-390, D-known-feedback-390, D-forget-me-390,
D-me-tab-390, F-emulator-after-restore: same chip style, YouRow-blue selected option, dark sheet, no new colours;
the prod sheet matches shots/fix-video-sheet-390 (Read side by side). 21 images Read in all (19 shots-prod, 2 shots).
D-known-feedback-390 shows the fixed header over the scrolled form (existing translucent header, not clipping).
D-browse-other-profile-*.png deleted (they showed a real athlete's email); the evidence is in identity-log-*.jsonl.
- Overflow: hOverflow false on all 66 B/C renders and all identity pages except /profile/<real athlete> at 390
  (pre-existing long email, not a changed surface).
- Fold at 390 (measured): Automatic on /challenges/<club>/upload puts Upload Video at 720-760 px, above the bottom tab
  bar (779). Board form after scrolling to it: submit 432-480 (Automatic) vs 499-547 (off). Switch off, the standalone
  upload page's submit sits at 778-818, under the tab bar: same as pre-deploy (pre-existing). Result line + Change sit
  above the fold on both result pages (status y~360, video y~530 at 390).
- Not reviewed by eye: the other ~105 images; those are checked only by the logged metrics (line text, overflow, errors).

### F. APK
- gs://.../apk/tomsgym-debug-20261114-005300.apk exists (4,819,425 bytes, 2026-11-14T05:53:02Z). Short link
  /s/qu1t84 -> 302 to the signed object; following it downloads bytes identical (cmp) to the published object.
- The DOWNLOADED published APK: capacitor.plugins.json lists @capacitor/preferences (PreferencesPlugin), class in
  classes2.dex (3 hits); lift-type-automatic in UploadVideo-CBAK2I7s.js and ChallengeDetail-C8lMhlgC.js; build stamp
  1794635557 in index.html + index chunk.
- Emulator (AVD t30g, headless), published APK installed, pm clear, WebView driven over raw CDP
  (webview_devtools_remote_<pid>, Playwright connectOverCDP is not supported by the WebView):
  1. first run: localStorage empty;
  2. placeholder identity (...e0e0 / prove-emulator@example.com) written to localStorage, 15 s for the flush, force-stop +
     start: localStorage kept AND shared_prefs/CapacitorStorage.xml now holds userId + userEmail (boot seed);
  3. localStorage.clear(), 15 s, force-stop + start: userId + email restored into localStorage from Preferences;
  4. control: Preferences file removed, clear, 15 s, restart: storage stays empty, so step 3 came from Preferences.
  Home renders (F-emulator-after-restore.png), no Uncaught in the app's logcat lines.
  Seeding was by direct localStorage writes, not through the app's remember() (no UI path to stub the lookup over raw
  CDP), so remember()'s write-through is covered by jest only. A real phone is not covered. Emulator stopped afterwards.

## Final state
DB snapshot at the end byte-identical to the first one (counts, newest rows, target Attempt/LiftingResult hashes).
Board (rank, score, this_week.lifts, attempt_count): (1,375,147,14), (2,350,162.5,14). Revisions still
my-python-backend-00197-vvw / my-frontend-00206-dxd. Cloud SQL proxy pid 13926 left running.

## Defects / follow-ups
1. (frontend, pre-existing gap made stickier) No "Forget Me" at phone width: the navbar holding it is `hidden md:flex`
   and the Me tab has none. With the new native Preferences mirror, an APK user has no UI way to clear a remembered
   identity (uninstall or clear app data only).
2. (frontend, coverage) BowlingChallenge email pre-fill has neither a browser proof nor a jest test.
3. (frontend, dead code) FindProfile dialog, RegistrationForm, CreateProfile, PasswordResetForm are not mounted by any
   route; their pre-fill counts toward "every email input" only in jest.
4. (backend, contract text vs design) wrong-user change call answers 400 (switch gate) not 403 while the switch is off
   (deviation 8, intended). The 403 path is unproven in production.
