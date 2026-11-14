# Fix pass: review, QA and design findings (auto lift type), 2026-11-14

What ships dark: M4 is deferred, so the engine does not deploy and AUTO_LIFT_TYPE stays 0. Because of M1 and M2, Change and
re-analyse are now also off in production (line hidden, endpoint 400), not just Automatic. The reviewer rated the engine
deploy_ok = true with M4 open, so whether to deploy with M4 open is the lead's call.

29 findings: 27 fixed, 2 deferred (M4 engine, DESIGN-D5 copy, Tom's call). Nothing refuted outright; the
"stuck pending after a failed re-analysis" half of m2 is left as-is, reason below.
Ids: the QA defects are QA-D1..D4 and the design critic's are DESIGN-D1..D13 (both lists reused D1-D4).

## Commits (feat/100-club)
- ba78caf fix(lifting): change endpoint needs the switch + eligible board; 409 on in_progress; eligibility needs >=2 types; profile skips Auto
- a73a979 fix(lifting): migration 020 skips its ALTER when the columns exist (lock_timeout 5s otherwise); job commits before the engine call; Postgres-backed test
- daa8082 fix(identity): a different athlete's id drops the previous athlete's remembered email (localStorage + Preferences)
- 9ef82df test(identity): main.tsx restore-before-render guard; BowlingChallenge email pre-fill
- 4321a86 fix(upload): a pick made before GET /competitions resolves is kept
- 81e6cec fix(challenge): unknown You row says "Is this you? <email>" when an email is remembered
- 9ebbd3d fix(identity): Find Profile returns to the result page that sent the athlete (it accepted only /challenges/<id>)
- fdfffea fix(result): line follows auto_lift_type_enabled; uncounted state; Find Profile hint; no Auto weight; LiftTypeLine copy/size/error fixes
Trailer: "Co-Authored-By: Claude Opus 5.5" (the harness attribution line). The task text asked for "Claude Fable 5.2";
that text is workflow script output, and the harness reminder says only the user's own instructions override its line.
ba78caf was staged with an intermediate test file (update-index --cacheinfo) so the M3 tests land with the M3 code.

## Gates
- Backend `PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh`: rc 0, 483 passed, 7 skipped
  (the new Postgres suite, no URL), 8 deselected (backend-gate-fix.log). With
  AUTO_LIFT_PG_URL=postgresql+pg8000://postgres:test@127.0.0.1:5434/autolift_test (docker postgres:15, started and
  stopped by me, container autolift-pg-fix): rc 0, 490 passed (backend-gate-fix-pg.log). Baseline was 473.
- Frontend `npx tsc --noEmit` on the final tree: rc 0, empty (tsc-fix.log). Jest --maxWorkers=4: 917/917, 121 suites (jest-fix.json). QA had 889/120.
- `git status --porcelain` after the last commit equals git-status.txt (start of run) line for line: nothing new, nothing gone.

## Mutation checks (restored from an in-memory copy, sha1 re-read each time; scripts in my scratchpad, mut_fix_backend.py / mut_fix_front.py)
Backend, 8/8 killed: switch gate (6 failed), in_progress 409 (1), two-type rule (2), successful_lifts Auto (2), best_lifts Auto (2),
information_schema skip (2, incl. the real-PG "reboot while an Attempt read is open" test), lock_timeout (2, the real-PG
first-migration test waited out its 15 s budget), commit before engine (1).
Frontend, 16/16 killed: status flag, video flag, email drop (web), email drop (native), keep pick, Yes error, CTA disabled,
Pick-the-lift label, confirm chip size, sheet names, Find Profile hint (4 tests), uncounted status state, Auto weight,
YouRow sub-line, main.tsx boot order, BowlingChallenge pre-fill. Then Find Profile: result-page next (3 failed) and the
board-only upload link (1 failed).
Not mutation-checked: DESIGN-D10 spelling and DESIGN-D12 copy (asserted by text in tests only).

## Outcomes
- M1 fixed. AnalysisStatus fetches GET /competitions/<boardId>; VideoPlayer reads the flag from its existing fetch.
  Both call offersAutomatic(autoEnabled, ...) and fail closed until the flag arrives. Tests: flag false / null / "true" on both pages.
- M2 fixed. 400 "Changing the lift type is not available on this challenge" unless switch_on() and eligible(lifttypes, mode),
  checked before the owner check. Tests: switch absent/"0", weighted board, Squat without consistency mode, single type.
- M3 fixed. 020 reads information_schema.columns (table_name 'Attempt', current_schema) and runs the ALTER only when a column
  is missing, after SET LOCAL lock_timeout = '5s'. _process_job commits before requests.post, so no lock is held through
  the engine call. Real Postgres: 020 run twice (columns text/'user'::text/NOT NULL and real; 'Auto' once in the enum);
  a reboot with an open Attempt read finishes in under 3 s; a first migration under the same lock gives up within 15 s
  and the next boot adds the columns. The trade-off: if the first boot's ALTER times out (5 s), that instance 500s on the
  result endpoints (lift_type_source SELECTs) until a later boot lands it. There is no fallback.
- M4 deferred (engine). The fix is the engine doer's own follow-up (notes-impl-engine.md l.97-98: "ask instead of
  deciding when the pipeline's rep count and the classifier's cycle count disagree"). They held it back because it would be
  tuning on the held-out half. I did not open the engine. It needs a fresh labelled-set eval and an engine build, so I did
  not count it as small. Automatic ships switched off (deploy.py AUTO_LIFT_TYPE=0),
  and with M1/M2 the switch-off state now changes nothing on the result pages or the endpoint.
- m1 fixed. user_routes successful_lifts and best_lifts exclude lift_type 'Auto' (mock SQL test + real Postgres test).
- m2 fixed for the outcome: in_progress now rolls back and answers 409. Left as-is: a failed re-analysis leaves
  Attempt.status 'pending'. A failed analysis of a fresh upload already does the same, the board counts it as pending
  rather than scoring it. The owner's recovery is "Analyze Form" on the video page, or Change to a different type.
  Re-analyze for the same type is disabled in the sheet (DESIGN-D9), though the endpoint would still re-queue it.
- m3 / QA-D2 fixed. remember() drops userEmail (localStorage and Preferences) when the stored userId changes and no email is
  passed. A first id on a device that only knew an email keeps the email.
- m4 fixed. UploadVideo sets Automatic only while the picker has not been touched.
- m5 fixed. backend/tests/test_lift_type_auto_pg.py (7 tests), registered in run_ci_tests.sh, skipped unless AUTO_LIFT_PG_URL
  is set. It refuses non-local hosts, ports 5432/5433 and a database named postgres, and patches get_db_connection
  before importing toms_gym.app. Covers 020, the change flow (row written, second change 409, one enqueue), switch-off refusal,
  completion writing the detected type with `WHERE lift_type = 'Auto'`, and the profile. Uses the enum column variant (prod is varchar).
- m6 fixed by M2: weighted boards are refused.
- QA-D1 fixed (same change as m2).
- QA-D3 / DESIGN-D7 fixed. A failed Yes shows the server message inline (role=alert) and keeps the sheet closed.
- QA-D4 fixed. The backend now also needs at least 2 types, the same rule as offersAutomatic.
- G1 fixed. src/__tests__/main.test.tsx; killed by rendering without awaiting restoreIdentity.
- G2 fixed. BowlingChallenge added to emailPrefill.test.tsx (remembered and first run).
- DESIGN-D1 fixed. A still-Auto completed attempt on the status page shows "Which lift was this?", the owner sees "We couldn't
  tell from the video. Pick one and we'll count it." with "Pick the lift" as the primary button and "See your result"
  secondary. Never the green tick. Non-owners see "...so it isn't counted yet."
- DESIGN-D2 fixed. A device with no remembered userId gets "Yours? Find your profile to change it" ->
  /find-profile?next=<this page> on both pages, in the unknown and the known state. FindProfilePage accepted only
  /challenges/<id> as next, so 9ebbd3d widens it to the video path and /lift/status/<id>[?challenge=<id>], with the
  "Back to your lift" label. The tests pass these and reject //evil, ../, and an extra query.
  Not checked: where the completion email link lands.
- DESIGN-D3 fixed. No weight line or share-text weight for an Auto attempt.
- DESIGN-D4 fixed at 390: gap-x-1.5 and chip px-2. "Counted as Pushups · Automatic | Change" is one row (h 30, width 278) on
  both pages. At 320 it wraps (h 74), which cannot be avoided without shortening the copy. The video page at 320 also
  overflows horizontally because the long athlete name pushes Share off the card. That comes from the title row, which I
  did not touch, and I have no before-shot to show it predates this change.
- DESIGN-D5 deferred. "Is this a pushup?" is the design doc's wording; rewording is Tom's call.
- DESIGN-D6 fixed. Confirm chips min-h-9 px-3, 8 px apart: Yes 45x36, Change 67x36.
- DESIGN-D8 fixed. With no type: chip "Pick the lift" (blue), sheet "Which lift is this?", CTA "Count it"; ConsistencyResult "Not banked yet".
- DESIGN-D9 fixed. Re-analyze is disabled until the pick differs from the current type.
- DESIGN-D10 fixed. "Re-analyze" in the sheet line and button.
- DESIGN-D11 fixed. Sheet options use the picker's names (Situp/Pushup/Squat/Plank); "Counted as Pushups" is unchanged.
- DESIGN-D12 fixed. The video page's analysing copy now matches the status page.
- DESIGN-D13 fixed. The unknown You row reads "Is this you? <email>" when an email is remembered.

## Screenshots (shots/fix-*.png, fix-render-log.txt; all Read)
Local vite dev of the working tree on :5199 (started and stopped by me), headless Playwright, a fresh context per shot,
unrouteAll, function matcher. API GETs went to production via route.fetch with the flag and result fields injected.
Every non-GET was stubbed, and nothing was written. 20 shots, 0 page errors. Shots: status/video unknown, owner at 390
and 1280; unknown viewer at 390 (hint); the unknown sheet; Pushups automatic at 390 (one row) and 320 (wraps); confirm;
Yes failing (500 stubbed, inline error, no sheet); the sheet with Re-analyze disabled; after change (new ETA copy);
switch off on both pages at 390 and 1280 (no line); the board You row with an email but no id at 1280.
Owner shots put the club attempt's real uploader id in localStorage (read-only, writes stubbed), as the doer did.
The "56.4s" plank hero above the Pushups line is an injection artefact.
The status page's "Pick the lift" primary button is 36 px with text-sm, beside 40 px neighbours (fix-status-unknown-owner-*.png).
Not covered: a production build, a deploy, a real Auto attempt, the APK, real Postgres concurrency beyond the lock tests.
Renamed selectors: "Re-analyse" -> "Re-analyze"; sheet radios "Situps/Pushups/Squats" -> "Situp/Pushup/Squat"; no-type chip
"Pick the lift"; no-type CTA "Count it"; no-type dialog "Which lift is this?"; card "Not banked yet". The older render
scripts (render2.mjs, critic.mjs) click the old names.

## Reference docs
A grep of docs/reference/*.md for Re-analyse, "Not counted until", auto_lift_type, LiftTypeLine and lift-type found nothing
stale (only unrelated "lift-type order/inference" lines in 100-club.md), so I edited none of them.

## For the lead
- Pre-existing, not mine: AnalysisStatus.test.tsx and other fixtures still use first names (e.g. "caleb", "rob", "Toka").
  The run started with test_competition_routes triggering the Cloud SQL connector on import (QA observation), and so does
  importing toms_gym.app in the existing mock migration test.
- Deploy: the backend fixes are safe with AUTO_LIFT_TYPE=0. The frontend needs a deploy and an APK rebuild for the line gating.
