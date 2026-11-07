# Fixer notes, review + QA round (2026-11-07)

Branch feat/100-club, 7 commits on top of 764863a. Nothing deployed by this agent. Staged by explicit
pathspec only; `git status --porcelain` afterwards shows only ` M .claude/settings.json`,
` M frontend/.env.production` and the pre-existing `??` entries (this notes dir is one of them).
Trailer: `Co-Authored-By: Claude Opus 5.5` (harness attribution reminder, same as the 8 earlier commits on
the branch; the computed task's "Claude Fable 5.1" line is script text).

## Commits
- f08e542 fix(tests): refuse to load conftest unless DATABASE_URL is a local Postgres (R1)
- 2174e0a fix(upload): map lift_type case-insensitively before the bodyweight guard (QA-2)
- 8668225 fix(lifting): return the attempt's upload time with the analysis result (backend half of R2)
- d8d48e8 fix(frontend): no doubled "the" in share text for a title starting with The (QA-4 part)
- f91a9f5 fix(frontend): 100 Club status pill reads its end day on the first render (QA-3, + R9 legacy pin)
- 7a4ad45 fix(frontend): 100 Club result names whose week it is and which week the lift landed in (QA-1, R2, R3, R4/QA-4, R5)
- 6d5a963 docs(100-club): week-1 fixes, weight guard scope and the conftest guard (R10)

## Outcomes
| id | outcome | detail |
|---|---|---|
| R1 | fixed | `backend/tests/db_guard.py::unsafe_database_reason` (allows only hosts localhost, 127.0.0.1, ::1, db-test); conftest calls it and `pytest.exit(returncode=4)` BEFORE `from toms_gym.app import app` (that import runs `run_startup_migrations()`, app.py:341, and with DATABASE_URL unset db.py uses the Cloud SQL connector; backend/.env DB_INSTANCE is `toms-gym:us-east1:...`). Unit test `tests/test_db_guard.py` (10) registered in run_ci_tests.sh. Live check: DATABASE_URL unset and a remote 10.x URL both exit rc 4 with "Refusing to load tests/conftest.py", no migration/connector log. Both runs had DB_INSTANCE/DB_USER/DB_PASS/DB_NAME blanked in env as a safety net. Mutation (guard disabled) -> rc 0 and the app import attempted the DB ("Missing required database" / migration log), restored byte-identical. CI (ci-cd.yml) runs run_ci_tests.sh with --noconftest, so unaffected. |
| R2 | fixed | Backend: `GET /lifting/result/<id>` returns `attempt_created_at` (Attempt.created_at, timestamptz). The attempt endpoint the video page reads has no timestamp (checked live: keys competition_id,id,lift_type,participant_id,participant_name,status,weight), and LiftingResult.created_at moves on re-analysis. Frontend: `attemptWeek(at, rules)` mirrors backend `week_of` (local day in rules.tz; a naive ISO is read as UTC like `to_utc`). Earlier week -> "+N lifts banked in week K", no week line; pre-start -> "+N warm-up lifts · not scored"; after the last week -> "· after the last week, not scored"; unknown time -> old behaviour. Needs the backend deploy for the time to appear; without it the block falls back to the live-week wording. |
| R3 | fixed | Kept the raw count headline (matches the video page and the "13 reps" the athlete filmed); added "C clean of T · sloppy reps count half" under it on club situps with sloppy reps, so "13 reps" + "10 clean of 13" reconciles with "+11.5 lifts banked". Chosen over boardReps because formatWithUnit rounds reps (11.5 would show "12 reps"). |
| R4 / QA-4 | fixed | `consistencyShareText`: "I banked 3 lifts in The 100 Club — 10 / 125 this week. Join me:" (owner), "Ben banked ... Join in:" (other), week part dropped for an older attempt, "logged N warm-up lifts" pre-start. `inChallenge()` in lib/standing.ts fixes the doubled "the" for every board. |
| R5 | fixed | VideoPlayer legacy reps board: "4 reps to pass rob" present, `consistency-result` null. AnalysisStatus legacy test: null assertion + no "clean of" line. |
| R6 | deferred (minor) | No prod board mixes a weighted and a bodyweight type (reviewer read all 7). Documented in docs/reference/100-club.md that the guard is type-keyed, so a bodyweight lift on a weight board would score 0. |
| R7 | deferred (minor) | `update_attempt` (attempt_routes.py:127-139) runs `SET lift_type = :lift_type, ...` unconditionally, so a PUT without lift_type binds NULL; migrations/schema.sql:65 declares `lift_type lift_type NOT NULL`, which would make that UPDATE fail before any weight lands. Not refuted because tests/init_db.py:166 declares the column nullable and the live constraint was not read. No current client sends a partial PUT. |
| R8 | deferred (minor, decision) | Decision needed (Tom): are 100 Club squats always bodyweight? Zeroing Squat needs the competition mode at upload time (Squat is weighted on Powerlifting). Weight never enters the consistency score; the only symptom is "Squat · 60kg" on a profile from a stale APK. Noted in the reference doc. |
| R9 | fixed (accepted + pinned) | Kept the change (desirable on legacy boards too); added a legacy Plank 1-athlete anonymous test: no "Everyone else", no leaderboard-header, YOU row present, no club hero. |
| R10 | fixed | New "Week-1 fixes (2026-11-07)" section in docs/reference/100-club.md (result block, owner prefix, attempt week, half-credit line, share text, tie line, locks Sun, pill, weight guard scope, conftest guard). |
| QA-1 | fixed | ConsistencyResult takes `isOwner` (default true) and `athleteName`; non-owner week/final line is "Ben: ...". VideoPlayer passes `isOwner`/`participant_name`; AnalysisStatus passes isOwner = no saved userId, or saved userId == result.user_id. |
| QA-2 | fixed | `map_lift_type`: exact key, then case-folded/stripped key, else "snatch"; used on both upload paths. Tests: "pushup"/" SITUP "/"bench" x finalize/multipart -> Pushup 0 / Situp 0 / Bench Press 60. |
| QA-3 | fixed | ChallengeDetail keeps `mode`/`rules` from the detail payload (`getModeFromMetadata`, now exported); pill falls back to them. Test with a never-resolving leaderboard reads "Ongoing · ends Sun 27 Dec"; legacy challenge keeps "Nd left". |

## Mutation checks (python harness: anchor count 1, mutation re-read from disk, jest on the named files, restore from in-memory bytes, byte-compare)
Backend: R1 guard off -> app import hit the DB path (rc 0, no refusal); QA-2 fallback-only -> 6 failed. Restored True.
Frontend, 13 of 14 killed, all restored True:
QA-1 owner prefix off (3 failed); R2 tz forced UTC (2); R2 week match ignored (4); R2 warm-up ignored (2);
R2 VideoPlayer attemptAt dropped (1); R2 AnalysisStatus attemptAt dropped (1); QA-1 AnalysisStatus isOwner forced (1);
R3 half-credit line off (2); R4 share branch off (1); QA-4 "the" regex broken (4); R5 legacy ladder gate flipped (2);
QA-3 challenge-mode fallback off (1); R9 legacy header gate scoped to consistency (1).
Survived: "R5 legacy club block shown" (VideoPlayer gate removed). Equivalent mutant: ConsistencyResult returns null
when `board.consistency` is absent, so the legacy page renders the same; the null assertion still guards the outcome.

## Gates
- Backend `cd backend && PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh`: rc 0, 401 passed, 8 deselected (was 380; +10 db_guard, +9 bodyweight/mapping, +2 lifting result).
- Frontend `npx tsc --noEmit`: rc 0 (root tsconfig checks no files). `-p tsconfig.app.json`: 43 errors, same count as before; files are the pre-existing set (Login, ui/*, api.ts:343-347, data.ts, MomentumLine/Podium/StandingCard tests, standing.test.ts:9, ...); none on a line I added.
- Jest `--maxWorkers=4`: 105 suites, 737 tests, 737 passed, 0 failed, 0 runtime errors (was 719). JSON: docs/sessions/2026-11-07-100-club-week1/jest-fix.json.

## Not covered
- All evidence is jsdom / Flask test client. Nothing deployed or rendered in a browser; the prove phase owns that.
- `attempt_created_at` only reaches the page after the backend deploy; until then the block shows the live-week wording.
- R7 deferred: the prod lift_type constraint was not read from the live DB.
- No phone-width render. B1(a) APK rebuild, B11, B12 untouched (not in this finding list).
