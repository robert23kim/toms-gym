# Fix round 2 (2026-11-14, fixer): prover/refuter findings

Nothing deployed and the APK is not rebuilt, so no phone has these fixes yet. Four unique ids (DF1 appeared twice).
DF1 is fixed and proven in a browser at 390 on local vite. The APK path (Preferences cleared, still forgotten after a
force-stop) is unproven until a rebuild. UA1 is fixed (local vite, 390). CP1 is fixed in part: the "Is this a pushup?"
half is deferred as DESIGN-D5. DF2 is refuted for jest and is now proven in a browser on the production frontend.

## Commits (feat/100-club, by pathspec)
- facad38 fix(profile): phones get Forget Me (or Logout) on the owner's own profile
- f37bc6d fix(result): Upload Another on a challenge result goes back to that board's form
- 98d5166 fix(result): the queued screen says how many athletes are on the board
- dc4a066 test(result): singular "1 athlete" case; the new visitor test no longer waits on a real handle
f37bc6d and 98d5166 both touch AnalysisStatus.tsx and its test. f37bc6d was staged with the copy change backed out
(hash-object + update-index --cacheinfo), so each commit holds one unit. The intermediate tree is consistent by
construction, but no test was run on it.
Trailer: "Co-Authored-By: Claude Opus 5.5", the harness attribution line. Round 1 did the same: the task's
"Claude Fable 5.2" line is workflow script output, and the harness reminder yields only to the user's own instructions.

## Outcomes
- DF1 fixed. Profile.tsx: the owner's own profile (what the Me tab opens) shows a `md:hidden` "Forget Me" next to
  "Change avatar". It does the same as the navbar: removes last_attempt_id, awaits forget() (so the APK's Preferences
  mirror is cleared before the reload), then window.location.href = '/'. A signed-in (password) owner gets "Logout"
  instead, which calls AuthContext.logout (clears tokens + forget). The control also renders in the error and
  "no profile data" states, because a stale or deleted remembered id is exactly when it is needed (the prover's fake id
  landed there). Visitors never see it. Desktop is unchanged (navbar control only).
- UA1 fixed. AnalysisStatus.tsx: when the status URL carries ?challenge=<id> (set by UploadVideo-with-id and the Home
  PromptList), "Upload Another" and the failed state's "Upload Again" link to /challenges/<id>?upload=1, which opens that
  board's own form (club types, lbs). Without the param they keep /lift/upload. Keyed on the param, not
  result.competition_id, because generic uploads also carry a competition_id ('1'). Not covered: a club status page
  opened without ?challenge (no current link produces one; backend has no /lift/status links). The generic page's kg and
  Squat default are out of scope by the design doc and unchanged.
- CP1 fixed in part. The queued screen now reads "<leader> leads at 375 pts · 2 athletes on the board" (singular
  "athlete" for 1). Deferred: "Is this a pushup?" above "+25 lifts banked" is the design doc's wording and was already
  deferred as DESIGN-D5 in round 1. Rewording it is Tom's call.
- DF2 refuted for the jest half: emailPrefill.test.tsx "BowlingChallenge upload email" (9ef82df, mutation-killed in round
  1) passes in jest-fix2.json. The browser gap is closed now. The prover found no email input on
  /bowling/challenge/<id> because the upload form only opens on the "Upload Video" button, whatever the challenge status.
  On the PRODUCTION frontend at 390 (this round did not change BowlingChallenge), clicking it with only userEmail
  remembered pre-filled prove-placeholder@example.com and kept it editable, and typing left storage unchanged. From
  empty storage the input was empty.

## Gates
- Frontend `npx tsc --noEmit`: rc 0, empty. Jest --maxWorkers=4: 925 passed / 0 failed, 121 suites (jest-fix2.json, after dc4a066;
  round 1 had 917, +8 new tests).
- Backend `PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh`: rc 0, 483 passed, 7 skipped,
  8 deselected (backend-gate-fix2.log). No backend change this round.
- `git status --porcelain` after the last commit equals git-status.txt (start of run) when both are sorted.

## Mutation checks (10/10 killed; restored from an in-memory copy, sha1 re-read after each; script scratchpad mut2.py)
header control removed (2 failed), error-branch control removed (1), owner check dropped (1), md:hidden dropped (1),
forget() not awaited/called (1), logout branch dropped (1), upload path ignores ?challenge (4), failed-state link kept on
config.uploadPath (1), copy back to "N on the board" (1), singular ternary forced to "athletes" (1, after dc4a066).
The owner-check mutation was re-run after dc4a066 changed the visitor test's wait (still killed).
Unguarded: the mutation deleted the forget() call. Dropping only the `await` would survive jest here and in
Navbar.forget.test.tsx, and that ordering is what stops the APK restoring the identity on boot.
Note: jsdom ignores Tailwind, so the md:hidden test only asserts the class. Visibility at 390 vs 1280 is proven in the browser below.

## Browser proof (fix2-browser.json, shots-fix2/*.png)
Scripted headless Playwright. Each case got a fresh context with service workers blocked, page.unrouteAll(), one FUNCTION
matcher, every non-GET stubbed (the only one seen was the boot /log-error telemetry), 1.5 s after the first navigation.
DF1/UA1/CP1 ran on local vite dev of the committed tree (:5299, started and stopped by me), with API GETs sent to
production via route.fetch. Placeholder identity 00000000-...-d00d / prove-placeholder@example.com, whose profile GET was stubbed.
DF2 ran on the production frontend.
- df1-me-tab-390: Home, then tap the exact "Me" tab, landing on /profile/<placeholder>. One visible Forget Me at (269,268)
  84x20. Clicking it cleared userId and userEmail and landed on /. /feedback's email was empty, and still empty after a
  reload. No overflow, 0 console errors.
- df1-stale-id-390 (profile GET 404): "User not found ... Try Again / Forget Me", with Forget Me visible. The console shows
  the expected 404 lines.
- df1-profile-1280: exactly one visible Forget Me (the navbar's), so desktop is not duplicated. df1-visitor-390: 0 on
  someone else's profile.
- ua1-completed-390 / ua1-failed-390: href /challenges/<club>?upload=1. The click lands there with the board form open:
  Squat/Plank/Pushup/Situp, "Weight (lbs)", nothing submitted.
- cp1-queued-390: "<leader> leads at 375 pts · 2 athletes on the board". No overflow.
- df2-bowling-remembered-390 / df2-bowling-firstrun-390: as above.
Read by eye: df1-me-tab-390 (Forget Me sits beside Change avatar in the same muted text-sm style) and
ua1-landed-completed-390. The other shots are checked only through the logged metrics.
Not covered: the production bundle with these fixes (not deployed), the APK (needs a rebuild + publish), a real phone.

## For the lead
- Deploy: frontend only (`python3 deploy.py --frontend-only --skip-iam`), then an APK rebuild + publish so the APK gets
  Forget Me.
- Emulator check to run after the APK rebuild: remember an id, tap Me and then Forget Me, force-stop and restart, and
  confirm localStorage is empty and shared_prefs/CapacitorStorage.xml has no userId.
- Forget Me on the profile is 84x20 px, 16 px from Change avatar, with no confirm. It matches Change avatar's text-button
  style, but it is below round 1's 36 px chip height (DESIGN-D6). I left it as is, so it is a design call.
- UA1 on an ended board: ChallengeDetail renders the form only for upcoming/ongoing (line 1101), so the link lands on the
  board without a form. That is honest and does not upload elsewhere. FindProfilePage links the same way.
- Pre-existing fixture: Profile.test.tsx's profilePayload uses a real athlete handle as name/username/email (round 1 and
  earlier). My new tests use the same fixture but no longer assert on the handle.
- Pre-existing, untouched: the club board form shows "Your Email" even when the userId is known (ua1-landed shot). The
  generic /lift/upload still defaults to Squat / kg 60 for non-challenge uploads.
