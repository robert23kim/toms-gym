# Review: auto lift type (toms_gym 74a2519..2b397cd, auto-engine feat/situp-config..a52612e)

Verdict: 0 blockers, 4 major, 6 minor. Engine deploy_ok = true, with caveats (section 3).

## Gates I ran myself
- Backend: `PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh`: exit 0, 473 passed, 8 deselected. test_lift_type_auto.py is registered (run_ci_tests.sh:39) and has 32 test functions.
- Frontend: `npx tsc --noEmit`: exit 0, no output. That covers the untracked `src/__qa_tmp__/` (QA scaffolding, not tracked, not committed). Jest was not run (QA's job).
- Engine eval: `scripts/eval_auto_lift_type.py eval` with the doer's manifest and **macOS pose cache**, written to the scratchpad. It is byte-identical (`diff`) to the committed `docs/auto_lift_type/labelled_set_result.md`. That re-runs the classifier only, not pose extraction. The held-out rows match `engine/eval-first-holdout-run.md` (first scoring), so the later perf commit a52612e changed no held-out outcome.
- Engine before/after, explicit types: the 93378b0 tree came from `git archive` and ran against the HEAD worktree, through `analyze_lift` + `build_lift_summary`. Each tree was imported via sys.path[0] under `python -I`, and the before tree has no `_analyze_auto` (canary: grep count 0 vs 2). c28 squat d83dade21997856f, 13 reps, same. c15 pushup bb1063c58ee41617, 25 reps, same (cmp). Plank, bicep_curl, deadlift, annotated video and clips were not compared.
- Engine tests: the 4 touched files gave 47 passed and 1 failed (`test_service_app::test_metric_clips_are_reencoded_uploaded_and_rewritten`). That failure is pre-existing: the 10-name FAILED lists in the doer's before/after full-suite logs are identical (cmp). I did not re-run the full suite.
- Privacy: I grepped the added lines of both diffs for the names and long ids in live-before.json and found 0 hits (canary `LiftTypeLine` was found). Only example.com emails appear. This is limited: live-before.json yielded just 2 names and 4 ids.

## Wire agreement (read both ends)
backend -> engine: `lift_type:"auto"` (lower case) plus `candidates`, the lower-cased declared types (lifting_processor.py:200-204). The engine rejects auto with no candidates (service/app.py), and `eligible()` prevents that case.
engine -> backend: the summary is `report` with `detected_lift_type` as an engine key ("pushup") and `lift_type_confidence`. `match_declared` maps it back to the declared spelling ("Pushup"). With no detection, `report.lift_type == "auto"` and there is no annotated video.
backend -> frontend: `/lifting/result` and attempt details carry `lift_type`, `lift_type_source`, `lift_type_confidence`, `needs_lift_type`. The frontend reads the same names (lib/autoLiftType.ts pickLiftTypeFields) and checks `report.lift_type` "auto" case-insensitively. DB value "Auto"; engine value "auto". These agree.

## Findings

### M1 major frontend: the result line and Change ignore the switch
AnalysisStatus.tsx:161 and VideoPlayer.tsx:565 call `offersAutomatic(true, ...)`. The backend always returns `lift_type_source` (column default 'user'), so with AUTO_LIFT_TYPE=0 every owner viewing a 100 Club result gets "Counted as X" plus Change, and Change re-analyses. This contradicts the declared deviation F1 ("the same rule gates the result line") and check (5), which says nothing changes with the switch off.
Fix: pass the competition's `auto_lift_type_enabled`. Both pages need the competition payload, or the leaderboard payload can carry the flag. Add a test with the flag false.

### M2 major backend: the change endpoint is not behind the switch or eligibility
attempt_routes.py:204-268 is live on every competition with the switch off, weighted boards included. Combined with M1 that is a live behaviour change. The owner check is `body.user_id == owner` (line 231), and competition_routes.py:482 publishes `user_id` on the public leaderboard. So anyone can re-type and re-analyse a real athlete's club attempt, for example Plank to Pushup on the live board. The contract accepts upload-level trust, so this is cited rather than counted as a contract break, but the switch gate is cheap.
Fix: return 404/400 unless `switch_on()` and the competition is `eligible()`.

### M3 major backend: migration 020 can stall boot and every Attempt reader
app.py:101-108 runs `ALTER TABLE "Attempt" ADD COLUMN IF NOT EXISTS ...` on every boot (module import, app.py:363). Even when the columns exist, that takes ACCESS EXCLUSIVE, with no `lock_timeout`. Sessions are transactional (db.py:70, default sessionmaker).
The new `_competition_lifttypes` (lifting_processor.py:160, called at :202) reads "Attempt" on the job session before `requests.post(..., timeout=890)` (:209). That holds ACCESS SHARE on Attempt for the whole engine call, which is 52 s or more for planks and up to 890 s.
A cold start during an Auto analysis then blocks in the ALTER, and every later Attempt query queues behind the waiting ALTER: boot stalls and the board stalls. A failed or skipped migration has no fallback either: the new SELECTs of `a.lift_type_source` in /lifting/result and attempt details would 500. The migration test (test_lift_type_auto.py:630) runs against a MagicMock, so it cannot see any of this. Migration 020 has not been run against a real Postgres.
Fix: `SET LOCAL lock_timeout = '3s'` before the ALTER, or check information_schema and skip. Read the lift types in a short separate session, or commit before the engine call. Run 020 twice against a docker Postgres.

### M4 major engine (does not block deploy): silent high-confidence wrong guesses inflate a live board
c32 (plank filmed from the feet) is read as pushup at 1.00, about 162 pushups instead of about 11 plank lifts. c48 (knee pushups) is read as plank at 0.91. Also, any set that opens with a hold of 8 s or more is decided as a plank (lift_type_classifier.py:229), and pushup sets often start with a held top position. These pass the contract's rule. Recovery depends on the athlete pressing Change, and an inflated guess gives them no reason to.
Fix (doer's own follow-up): lower confidence when the pipeline's rep count and the classifier's cycle count disagree, for example 162 vs 38.

### m1 minor backend: undetected Auto attempts count in profile aggregates
Completion sets `Attempt.status='completed'` even with no detection (lifting_processor.py, auto-judge UPDATE). user_routes.py:267 (`successful_lifts` counts DISTINCT lift_type, so "Auto" counts as a type) and :303 (`best_lifts` group gains `{type: "Auto", best_weight: 0}`) are not guarded; only lift_history.py is. Profile.tsx does not render best_lifts today, so there is no visible impact yet.

### m2 minor backend: the change endpoint ignores the helper's outcome; status can stick at pending
attempt_routes.py:264 drops `queue_lifting_analysis`'s outcome and always answers `"status": "queued"`. The Attempt row lock serialises concurrent changes, so a double enqueue is unlikely, but `in_progress` is reported as queued. If the re-analysis fails, `Attempt.status` stays 'pending' because the failure path never restores it, so the board shows it as pending indefinitely.

### m3 minor frontend: identity keeps the previous user's email
`remember({userId})` without an email (MagicLink.tsx:43, tokenUtils.ts:23 setTokens) leaves the previous `userEmail`. A shared device signing in as B then pre-fills A's email on FileTicket, SignIn and the bowling and golf uploads, and `restoreIdentity` mirrors that mismatched pair to Preferences. The userId itself is never silently replaced: ChallengeDetail and UploadVideo adopt only when no id is stored, or when the user typed the email. Fix: drop `userEmail` when `remember` gets a different userId and no email.

### m4 minor frontend: UploadVideo's late fetch overrides the user's pick
UploadVideo.tsx:57 calls `setLiftType(AUTO_LIFT_TYPE)` when GET /competitions resolves, which overwrites a type the user already picked.

### m5 minor backend tests: mocked SQL only
The change-endpoint and completion tests assert SQL substrings on MagicMock sessions. There is no real-DB run of the `WHERE lift_type = 'Auto'` UPDATE, the enum value, or concurrency.

### m6 minor backend: the weight guard keeps the weight on a weighted target
`bodyweight_weight_kg(lift_type, row.weight_kg)` keeps the old weight when changing to a weighted type: Pushup (0) to Squat on a mixed weighted board gives Squat at 0 kg. This only matters while M2 leaves the endpoint open on weighted boards.

## Checks that held
- Auto never scores: consistency.py:210 counts it as pending; `_leaderboard_payload` keeps it out of the inferred lift_types; `_rank_weight`, `_rank_reps` and `_rank_time` exclude it; lift_history nulls reps and hold; the champions cache is invalidated on completion and change. The frontend hides the reveal and coaching when report.lift_type is auto.
- Upload guard: both insert paths plus POST /attempts reject Auto with the switch off or on a non-eligible board. PUT rejects Auto. `match_declared` rejects Auto and types outside the competition. 409 while queued or processing.
- Identity: Forget Me (Navbar) and logout await `forget()`, which clears both localStorage keys and Preferences. The web build skips the plugin via `isNativePlatform` in a try. `restoreIdentity` has a 1.5 s cap and never rejects. Render waits on it.
- deploy.py commits AUTO_LIFT_TYPE=0.
