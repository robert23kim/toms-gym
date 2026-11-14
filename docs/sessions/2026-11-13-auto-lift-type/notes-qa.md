# QA: auto lift type, change-and-re-analyse, remembered identity (74a2519..2b397cd, 13 commits)

Verdict: no regressions. Gates are identical before and after (backend 473/473, jest 889/889 in 120 suites, tsc clean).
I found 4 minor defects and 2 test gaps. None is a blocker. All 13 guards I mutated failed when broken
(6 backend, 7 frontend). The engine was not assessed by QA.
Not covered: production, a browser, the APK/emulator, a real Postgres. All backend checks used the route test client
with a MagicMock session, as the committed suite does.

## Gates
| gate | before (HEAD, no QA files) | after (QA files deleted) |
|---|---|---|
| backend `tools/run_ci_tests.sh` | 473 passed, 8 deselected, exit 0 (qa-backend-gate-before.log) | 473 passed, exit 0 (qa-backend-gate-after.log) |
| frontend `tsc --noEmit` | exit 0 (qa-tsc-before.log) | exit 0, empty output (qa-tsc-after.log) |
| frontend jest --maxWorkers=4 | 889/889, 120 suites (qa-jest-before.json) | 889/889, 120 suites, no `__qa_tmp__` suite (jest-qa.json) |

No test was deleted or weakened. Every test file in the diff only adds lines. The only exception is `__fixtures__/liveClubBoard.ts` (8/8),
where a real athlete's name and id were swapped for placeholders and no assertion changed.
A privacy grep of the added lines for real names, emails and ids returned nothing. The removed lines contain the
old id, so the pattern does match this diff.

## Mutation checks (each source restored from an in-memory copy; sha1 matched on re-read)
Scripts: qa-tmp-tests/mut_backend.py, qa-tmp-tests/mut_front.py.
| # | mutation | test(s) | result |
|---|---|---|---|
| B1 | consistency.py: drop the `Auto -> pending, continue` block | test_auto_attempt_scores_nothing_and_is_pending | 2 failed (killed) |
| B2 | attempt_routes: drop the 409 queued/processing check | test_change_409_while_analysis_runs | 2 failed |
| B3 | upload_routes.auto_lift_type_error: `if not switch_on()` -> `if False` | test_auto_upload_is_400_when_switch_off | 3 failed |
| B4 | _leaderboard_payload: Auto feeds completed_lift_types again | test_auto_attempt_never_drives_metric_inference | 1 failed |
| B5 | change endpoint: 403 check only `not user_id` (no owner compare) | test_change_403_unless_owner | 1 failed |
| B6 | processor: detection ignores the candidate set | test_completion_without_a_usable_detection_leaves_auto + QA outside-candidates | 4 failed |
| F1 | offersAutomatic returns true for any types | QA picker-vs-baseline (weighted, flag true) + autoLiftType.test | 2+2 failed |
| F2 | VideoPlayer isOwner ignores viewer id | QA no-identity + liftTypeLine.pages "Change is owner-only" | killed |
| F3 | AnalysisStatus viewerOwns ignores viewer id | QA no-identity + liftTypeLine.pages "visitor with no stored id" | killed |
| F4 | identity.read without catch | QA throwing storage + identity.test "storage that throws" | killed |
| F5 | main.tsx renders without awaiting restoreIdentity | QA main.qa.test only | killed (no committed test guards this, see G1) |
| F6 | restoreIdentity runs on web | QA web-skip + identity.test "never touches the native plugin on the web" | killed |
| F7 | ChallengeDetail posts `weight` instead of "0" for Auto | committed ChallengeDetail.autoLiftType "still posts weight 0 after a manual pick" | killed by the committed test; my QA payload test survived it (weight state is already "0") |

## Backend exercises (qa-tmp-tests/test_qa_tmp_auto.py.txt; 27 pass, 1 fails = D1)
Committed tests already cover: an Auto upload accepted on the club with the switch on (finalize, multipart, POST /attempts), 400 with the switch off,
400 on a weighted board, 400 on Squat without consistency mode, and 200/400/403/404/409, unchanged, and re-queue exactly once. I re-ran them in the gate.
I added:
- An Auto upload naming an unknown competition (no Competition row) gets 400 on all 3 paths, with no insert. PASS
- AUTO_LIFT_TYPE "0", "", "yes" and "2" all mean off (400). PASS. "AUTO" is stored as `Auto`, and a sent weight of 140 is stored as 0. PASS
- Completion when the engine says `squat` on a Pushup/Plank board: candidates sent `["pushup","plank"]` and the attempt stays Auto (no type update). PASS
- Completion with `detected_lift_type: null` (the engine's exact no-detection shape) leaves the attempt Auto and marks the LiftingResult completed. PASS
- Normalisation: PUSHUP/1.7 -> Pushup/1.0, situp/-3 -> Situp/0.0, plank/"nan" -> None, squat/None -> None, plank/True -> None. PASS
- Club board through `GET /leaderboard?as_of=` with one Auto attempt (completed, pending or failed). Score, rank order, by_type, weeks and type_leaders
  match the same data without it. pending +1 for completed and pending; failed adds nothing. An Auto-only athlete scores 0 with pending 1. PASS
- Legacy reps board (Pushup/Situp) and weight board (Squat/Deadlift) with an Auto attempt carrying reps 99 / weight 300: metric and scores unchanged. PASS
- Change endpoint: repeating the same type twice gives `unchanged` both times with no enqueue. A change gives `queued`, then a repeat while queued gives 409; enqueued stays at exactly 1
  and the LiftingResult UPDATE runs exactly once. Auto is rejected even on an Auto attempt. A non-JSON body gets 403. PASS
- Leaderboard after a change: not cached. A grep of all of backend/toms_gym for `lru_cache|_cache|TTL` finds only the champions cache
  (competition_routes.py:620) and the video-blob list. The before/after check ran through the `?as_of=` admin preview path. The board right after the change shows the
  new type (by_type Situp 0 -> 50, pending -1). The champions cache is dropped by the change endpoint. PASS. Caveat: the champions cache is per
  instance, so other Cloud Run instances stay stale for up to 600 s (documented as accepted).
- Observation for the lead: running the committed tests/test_competition_routes.py alone with `-s` prints 39 `RefreshError` lines.
  These come from the Cloud SQL connector trying to refresh `toms-gym:us-east1:my-db` and failing with invalid_grant, so it never connected.
  I did not check whether this predates the diff. Either way, the "DB-free" gate tries to reach production credentials.

## Frontend exercises (qa-tmp-tests/*.txt; 48 tests, 46 pass, 2 fail = D2, D3)
- Switch off: I copied the pickers from 74a2519 (`git show` into `__qa_tmp__/ChallengeDetailBase.tsx` and `UploadVideoBase.tsx`) and rendered them beside HEAD.
  Option list (value:label), selected value, weight field and helper are identical in: club with the flag absent, false or "true" (a string);
  weighted board with the flag true or absent; UploadVideo club page with the flag absent or false; weighted board with the flag true; the generic /lift/upload page. PASS (9 cases).
  This check can fail: mutation F1 failed it.
- Switch on: ChallengeDetail (club, and a Pushup/Situp duo) shows `Auto:Automatic` first and selected, no weight field and the helper line. The upload posts
  lift_type "Auto", weight "0" and the pre-filled email after only picking a file. On UploadVideo the club page offers Automatic and /lift/upload never does. PASS
- LiftTypeLine states: automatic ("Counted as Pushups · Automatic" + Change), manual ("Counted as Pushups" + Change),
  confirm at confidence 0.4 and 0.599 ("Is this a pushup?" Yes Change), 0.6 -> automatic, Auto + needs_lift_type -> "Which lift is this?",
  and a user source at confidence 0.1 -> manual. PASS
- Change hidden: for a non-owner at component level, and at page level on VideoPlayer and AnalysisStatus for viewer "someone-else", null and "undefined". The owner sees it. PASS
- Change flow on both pages: the sheet lists the board's types, the current one is pre-checked, picking Situps calls changeLiftType("v1","Situp",owner) once, and the page goes back to
  its analysing state with no old reps. The page matched no analysing text before the change, so the check can fail. PASS. A 409 keeps the sheet open with the server message. PASS
- Identity: localStorage throwing on get/set/remove (web and native) reads null and never throws. remember, forget and restore all resolve, and native still writes through
  to Preferences. Empty storage and the junk values "", "undefined", "null" read as null. Email is trimmed, and an email without "@" is not stored.
  For a different user, restore keeps localStorage A and re-seeds Preferences, empty localStorage brings back B, and remember({email}) keeps A. PASS. Failing cases: D2.
- Preferences restore: main.tsx calls restoreIdentity once, and createRoot/render do not run until it resolves (QA main test). On web the plugin is
  never called. On native a hanging plugin resolves after the 1.5 s timeout. PASS
- Email pre-fill. A grep for `type="email"` finds 13 inputs: RegistrationForm, CreateProfile, PasswordResetForm, FindProfile, FindProfilePage, SignIn,
  FileTicket, GolfUpload, BowlingUpload, BowlingSheetUpload (all 10 in the committed emailPrefill.test), ChallengeDetail and UploadVideo
  (committed autoLiftType tests + QA), and BowlingChallenge (QA only, PASS; no committed test, see G2). Login.tsx takes a "Username" text input
  (it is remembered as an email only when it contains "@") and is not pre-filled. It is not an email input, so I am not counting it as a defect.

## Defects
D1 (minor, backend, attempt_routes.change_lift_type): the endpoint ignores the "in_progress" result of `queue_lifting_analysis`.
   This is a mocked interleaving (the two reads return different statuses), not a reproduced concurrent race. Input: the joined lookup sees `processing_status='completed'`, then the shared helper sees 'processing' (two Change requests at once, or a re-analyse
   started between the two reads). Output: 200 `{"lift_type":"Situp","status":"queued"}` with enqueue calls `[]`. The Attempt row is already
   switched to Situp/pending, and the job already running finishes and writes a report for the old type. Fix: on "in_progress", roll back and return 409,
   or lock the row (`SELECT ... FOR UPDATE`).
D2 (minor, frontend, lib/identity.ts remember): a new userId without an email keeps the previous user's email.
   Input: localStorage {userId: B, userEmail: b@x.co}, then `remember({userId:"A"})`. Output: getEmail() is "b@x.co". expected null.
   On native, restore with localStorage {userId: A} and Preferences {userId: B, userEmail: b@x.co} gives Preferences ["A","b@x.co"].
   Callers that remember an id with no email: tokenUtils.setTokens (sign-in), MagicLink (passwordless), and Login when the username has no "@".
   Effect: forms that still show an email (FileTicket, SignIn, FindProfile) pre-fill the previous user's address until A opens their own Profile.
   Fix: when the id changes and no email is given, drop the stored email in localStorage and in Preferences.
D3 (minor, frontend, LiftTypeLine.confirmYes): a failed "Yes" is silent. Input: changeLiftType rejects
   `{response:{status:500,data:{error:"boom"}}}`. Output: the sheet opens with no error text ("boom" is never shown). The Change path does show it.
   Fix: `setError(errorText(err))` in the confirmYes catch.
D4 (minor, frontend/backend contract). Run: `AUTO_LIFT_TYPE=1`, `eligible(["Pushup"], None)` -> True and `enabled_for` -> True. The committed
   frontend test "switch off, one type, or a weighted type never qualify" pins the opposite. the backend `eligible()` accepts a single bodyweight type, so
   auto_lift_type_enabled is true on a one-type Pushup board. The frontend `offersAutomatic` requires at least 2 types and re-derives eligibility, although contract-deviations
   D2 says the frontend should rely on the flag alone. It fails safe (Automatic is hidden), but the two rules disagree.
## Test gaps
G1 (minor, frontend): no committed test imports main.tsx (grep), and jest coverage excludes it. Mutation F5 (render before restore) was caught
   only by the temporary QA test, so the "restore before first render" guarantee has no committed guard.
G2 (minor, frontend): the BowlingChallenge email pre-fill has no committed test. It passes in QA, both remembered and empty.

## Cleanup
Deleted `frontend/src/__qa_tmp__/` and `backend/tests/test_qa_tmp_auto.py`. Copies are in qa-tmp-tests/ as .txt.
`git status` on backend/, frontend/ and deploy.py shows only the paths that were already present. frontend/scripts/persona-walk.mjs
is listed in git-status.txt from the start of the run. Every gate ran on HEAD 2b397cded3ff9064ee00a1640a55d59d3e77807d.
