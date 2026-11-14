# Frontend impl notes: auto lift type, change + re-analyse, remembered identity (2026-11-14)

Gate (final, after round 2 fixes): tsc --noEmit rc 0; tsc -p tsconfig.app.json 43 errors (= baseline 43, none from this work;
Login.tsx(44), BowlingResult.tsx(40), api.ts(343-347) pre-exist); jest 120 suites, 889 tests, 889 passed, 0 failed (baseline 811)
-> jest-impl-frontend.json. One intermediate full run failed once on a pre-existing timer (ChallengeDetail upload form
scrollIntoView in jsdom); stubbed in that test file.

## Commits (feat/100-club, frontend/ only, staged by pathspec)
- 09a4a5a feat(identity): lib/identity.ts + Preferences mirror + email pre-fill
- adbc39b feat(upload): Automatic first/selected on bodyweight challenge uploads
- 35e68fb feat(result): lift type line, Change sheet, confirm prompt, re-analyse
- c89936d test(challenge): liveClubBoard fixture placeholders (+ guard test)
- 64d9e7f feat(android): cap sync registered @capacitor/preferences (capacitor.build.gradle, capacitor.settings.gradle)
- 9566019 test(identity): Navbar Forget Me native clear; Auto weight 0 off the club
- 7b4fc02 fix(result): attempt shows Pending while a changed type re-analyses
- da4b223 fix(identity): boot seeds Preferences for an athlete the WebView already knows; logout redirects after the
  native clear; Registration, CreateProfile, PasswordResetForm pre-fill too
- 1664f6c fix(result): line only on all-bodyweight boards (same rule as Automatic); Auto completion toast reads
  "Tell us which lift it was to count it." instead of an undefined grade
- (last) test(challenge): scrollIntoView stub + CreateProfile test typing
Trailer: "Co-Authored-By: Claude Opus 5.5" (the harness attribution reminder, as in the earlier run), not the task's "Claude Fable 5.2".

## Design items (frontend side)
1 Automatic
- Pickers a club upload can reach: ChallengeDetail inline form (board CTA "Log this week's lifts") and UploadVideo at
  /challenges/:id/upload. Checked, no picker: Home PromptList (club is a link row; buildPrompts turns consistency challenges
  into links), LiftHub (links only), camera-first capture (VideoCaptureInput is only the file input inside ChallengeDetail).
  /lift/upload keeps its manual picker and never fetches the competition (test).
- <option data-testid="lift-type-automatic" value="Auto">Automatic</option> first and selected every time (also after an
  upload with a manual pick), helper "We'll work out the lift from your video. You can change it after.", weight hidden,
  posts lift_type "Auto" + weight "0"; compression fast-only (the clip may be a plank). No added tap: email pre-filled,
  pick video, submit.
- Offered only when auto_lift_type_enabled === true (nested or top level) AND offersAutomatic (>= 2 types, all bodyweight;
  club squats count). Switch off: options, default and weight field exactly as before (tests for both).
2 Result line + Change
- components/challenge/LiftTypeLine.tsx on the status page (under the big number, or under "Analysis complete!" when there
  is nothing to reveal) and the challenge video page (under the h1). States: automatic "Counted as Pushups · Automatic",
  manual "Counted as Pushups", confirm "Is this a pushup?" Yes/Change (confidence < 0.6) or "Which lift is this?" Change
  (needs_lift_type / still Auto). Rendered only when the payload carries lift_type_source and the board passes the
  all-bodyweight rule (offersAutomatic with the switch treated as on), so weighted boards keep today's pages (test).
  Placement choice: the line lives on the two host pages, not inside ConsistencyResult.tsx (one line per page).
- Owner-only Change (status page: strict viewer id == result.user_id, unlike the old ConsistencyResult isOwner which treats
  a visitor with no id as owner). Sheet lists board.lift_types only (never Automatic), blue YouRow highlight for the pick,
  "Re-analyse" calls POST /attempts/<id>/lift-type; status "queued" drops the page into its existing analysing state
  (video page: result -> queued + poll, title shows new type, badge Pending; status page: Queued for analysis + polling
  restarted); "unchanged" (Yes) settles to manual; 4xx stays in the sheet with the server's error text.
- ConsistencyResult: an Auto report banks nothing ("Not counted until the lift type is set"); attemptLifts returns null
  for auto (hero upload list shows it as pending). VideoPlayer never renders the rep breakdown for an auto report (the
  engine's no-detection report has no insights -> would have crashed on report.insights.filter).
3 Identity
- lib/identity.ts getUserId/getEmail/remember/forget/restoreIdentity. Every direct localStorage userId read/write moved
  (grep outside identity.ts and tests: 0; canary: 14 test files still reference the key). Per-site overwrite rules kept
  (ChallengeDetail keeps a different stored id and does not remember that typed email; UploadVideo overwrites as before).
  tokenUtils setTokens/clearTokens go through remember/forget; Navbar Forget Me awaits forget() before reloading.
- remember at: upload responses (UploadVideo, ChallengeDetail, GolfUpload; bowling uploads remember the typed email), Find
  Profile dialog + page, Login (username if it is an email), MagicLink, CreateProfile, RegistrationForm, own profile fetch
  (Profile page, profile.user.email).
- Pre-filled, still editable: ChallengeDetail, UploadVideo, FindProfile, FindProfilePage, SignIn, FileTicket, GolfUpload,
  BowlingUpload, BowlingSheetUpload, BowlingChallenge. RegistrationForm, CreateProfile and PasswordResetForm also pre-fill (round 2). BowlingChallenge pre-fills but has no test.
- @capacitor/preferences 7.0.4 (core 7.6.9). Native-only via Capacitor.isNativePlatform(); every plugin call caught;
  restore races a 1.5 s timeout; main.tsx renders after restoreIdentity() (web resolves at once). android/ is tracked
  (53 files) so npx cap sync android was run (used the existing stale dist; assets are gitignored).
4 Design fit: existing select + "0 for air squats" helper style, weeks-chip style for Change/Yes, YouRow blue for the
  selected sheet option, dark card sheet, CTA blue for Re-analyse. No new colours, fonts or icons.

## Browser (local vite dev of the working tree, headless Playwright, fresh context per shot, unrouteAll, function matcher)
API GETs -> production via route.fetch; every non-GET stubbed (the lift-type POST returned queued; only other POST was the
boot telemetry). auto_lift_type_enabled and the result/attempt fields injected per state. 40 shots at 390x844 and 1280x800
in shots/ (render-log.txt): 0 page errors, no horizontal overflow, states as expected. Neighbours for comparison:
board-upload-off-*, challenge-upload-off-*, video-unchanged-*, status-unchanged-*, findprofile-firstrun-*, and prod-*-390.
Owner shots set localStorage userId to the club attempt's real uploader (read-only render, writes stubbed).
Not covered: production (not deployed), the APK and the native restore on a device/emulator (plugin only mocked in jest),
a real upload/re-analyse against the backend, Yes in a browser, a production vite build (renders used the dev
server). video-after-change-* and *-unknown-* were re-shot after 1664f6c (Pending badge visible). The unknown state on the
status page reads "Analysis complete! Your results are ready to view." above "Which lift is this?"; left as is.

## Mutation checks: 31 guards, all killed (mutation-frontend.txt, -2.txt, -3.txt)
Round 3 added: boot seed, remember write-through, both weighted-board gates, the present gate, UploadVideo switch-off,
CreateProfile pre-fill. Not mutation-checked: main.tsx restore-before-render ordering (main.tsx is outside jest), logout
awaiting the native clear in AuthContext, BowlingChallenge pre-fill, the Auto completion toast.
Restored from an in-memory copy, sha re-read after each. One first-round survivor was an ineffective mutation (a redundant
inner restore guard; re-run with both guards removed: killed); one survived because the test board was a club board
(weight already 0) and was fixed with a non-club board before re-running: killed.

## Handoffs / notes
- APK rebuild + publish needed for the Preferences mirror to ship (deploy step).
- Backend deviation 2 says the flag already folds eligibility; the frontend re-checks with the same rule (harmless).
- The old real athlete id in liveClubBoard.ts is still in git history (c89936d only fixes HEAD).
- Other test files still use the owner's first name "Toka" (ResultLadder, StandingCard, standing, share, HallOfChampions,
  AnalysisStatus, VideoPlayer.consistency, useIsOwner, owner tests): out of scope here.
