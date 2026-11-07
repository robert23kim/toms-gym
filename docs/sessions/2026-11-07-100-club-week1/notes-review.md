# Review notes: 993990f..764863a (8 commits), 2026-11-07

## Gates (run by the reviewer)
- Backend: `cd backend && PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh` -> exit 0,
  `380 passed, 8 deselected, 15 warnings in 5.47s`. tests/test_bodyweight_weight.py is registered in
  run_ci_tests.sh:29. Run on its own with `--noconftest`: `13 passed in 0.79s`.
- Frontend: `npx tsc --noEmit` -> exit 0, no output.
- Jest: not run (the brief said QA runs it).
- No mutation checks: the reviewer does not edit files.

## INCIDENT during review (process hazard, not in the diff)
I ran `venv/bin/python -m pytest tests/test_bodyweight_weight.py -q` WITHOUT `--noconftest`, twice
(once plain, once with `-x`). That
loads tests/conftest.py, whose autouse session fixture `init_db` (conftest.py:59-94) runs
`DROP TABLE IF EXISTS "<t>" CASCADE` for HandicapSnapshot, HoleScore, Round, Tee, Course, TokenBlacklist,
SecurityAudit, UserSession, Attempt, UserCompetition, Competition and User through `toms_gym.db`.
toms_gym.db connects with the Cloud SQL connector (db.py:35-46, DB_INSTANCE/DB_USER/DB_PASS/DB_NAME;
backend/.env exists). The google.oauth2 traceback shows that connector was invoked for the drops. I did
not read which instance DB_INSTANCE names, so "production" is inferred, not verified. Every drop failed on `google.auth.exceptions.RefreshError: invalid_grant` (expired
ADC), and all 13 tests errored in the fixture. Afterwards `GET /competitions/32ca7bad.../leaderboard`
returned 200 with both rows intact (caleb 150, Toka 150). Data looks undamaged. Rows were not counted
and no DB audit log was read, so that is all this check shows.
The risk: once ADC is valid again, any agent that runs a single backend test file the usual way can drop
the tables of whatever instance .env names (likely prod). Every agent briefed in this workflow should use only `tools/run_ci_tests.sh`
(it passes --noconftest), and the conftest should refuse to run against anything except a local
DATABASE_URL.

## Per bug-log id
| id | verdict | evidence |
|---|---|---|
| B1(b) | done, matches the log | `bodyweight_weight_kg` upload_routes.py:37-44, applied at :121 (finalize/_create_attempt_record), :379 (multipart), attempt_routes.py:71,126. Tests cover Squat 60 (both upload paths) and Deadlift 140 keeping their weight. The weighted Squat on a legacy board is not zeroed. |
| B1(a),(c) | not in this diff | APK rebuild and the existing weight-60 rows are deploy/data steps |
| B2 | done | ConsistencyResult replaces ResultLadder only when `board.metric === 'consistency'` (VideoPlayer.tsx:561-565, AnalysisStatus.tsx:141-151). For legacy boards the code path is unchanged (`club` null -> `board?.metric ?? liftMetric`, `attemptScore`, `deriveStanding`). `deriveStanding` was not changed (the log said "can"). The share text is left over (R4). |
| B3 | done | week table bonus cell reads `"<leading> · locks Sun"` from `r.this_week.leading` (ChallengeDetail.tsx:820, ConsistencyWeekTable.tsx:48-52). The hero note reads `rules.type_bonus` (25 in the live payload). |
| B4 | done | `tieLine` tiebreak order (streak, weeks_met, this_week.lifts, name) matches backend `sort_key` consistency.py:324-333. With the live payload it gives "caleb.li.larson and Toka are tied on points; more lifts this week puts caleb.li.larson ahead." |
| B5 | done | StatusPill `endsLabel` is used only in the ongoing branch and only when consistencyBlock is set. Legacy boards keep "Nd left". `finalDayLabel` = week_start + 8*7-1 = Sun 27 Dec. |
| B6 | done | LiftHub separates the club from the plank tile; the generic upload is unchanged. |
| B7 | done | `typeBreakdown` uses `by_type` and `plank_seconds`. Live week 1 for caleb renders "Plank 11 (119.5 s) · Pushup 65 · Situp 31.5" (Squat 0 filtered). |
| B8 | done | header and column row are gated on `tableRows.length > 0`; the YOU row stays. |
| B9 | done | LiftHistoryList BODYWEIGHT set, case-insensitive. |
| B10 | done | eyebrow "Weekly quota". |
| B11, B12 | n/a | data / decision |

## Payload shape / scoring
No backend response shape changed. No scoring code changed. The only backend behaviour change is the
stored weight_kg for Pushup/Situp/Plank (R6).

## Findings
R1 major (process, pre-existing): conftest drops the configured Cloud SQL tables. See INCIDENT.
R2 minor: ConsistencyResult.tsx:42-52 always shows "+N lifts banked" and the current week's lifts/quota,
  whatever week the attempt belongs to. A warm-up attempt viewed during the live phase, or a week-1 video
  viewed in week 2, says "+13 lifts banked · 0 / 125 this week". Compare the attempt date with
  `this_week.start` / `rules.week_start`, or limit the block to the latest attempt.
R3 minor: AnalysisStatus.tsx:142-147. The club reveal headline uses raw `total_reps`, while the block below
  uses `boardReps` (half credit for sloppy situps). A 13-rep situp with 10 clean shows "13 reps" next to
  "+11.5 lifts banked". This could be intentional, but it was not the reps behaviour before (attemptScore
  used boardReps).
R4 minor: VideoPlayer.tsx:119,133. `standing` is still derived on the club, so the share text reads
  "I'm #2 of 2 in the The 100 Club — 150 pts. Beat me:". The doer acknowledged it. It is the last
  rank-ladder wording left from B2.
R5 minor (tests): no VideoPlayer test that a legacy board still renders ResultLadder and no
  consistency-result. AnalysisStatus legacy test (AnalysisStatus.test.tsx:140) asserts the ladder but not
  the absence of consistency-result. The new legacy gate in VideoPlayer.tsx:565 has no regression guard.
R6 minor: the weight guard is keyed on lift type, not on the challenge mode. On a mixed declared board,
  e.g. {Squat, Pushup}, competition_routes.py:513 picks metric "weight", so a pushup's board score is its
  weight, and that is now 0. This matches the log's literal ask. Settled for prod: I read
  /competitions/<id>/leaderboard for all 7 boards. The weight boards are Powerlifting [Squat, Bench Press,
  Deadlift], Biceps and Bench [Bench Press, Curls] and Bowling. None has a bodyweight type, so no live
  score changes. This would bite only a future mixed board.
R7 minor: update_attempt (attempt_routes.py:126) passes the weight through when a partial PUT omits
  lift_type, so `PUT {weight_kg: 60}` on a pushup attempt still stores 60.
R8 minor (out of log scope): Squat is a 100 Club type but not in BODYWEIGHT_LIFT_TYPES. A stale APK
  posting 60 on a club squat still stores 60, and the profile shows "Squat · 60kg".
R9 minor (legacy board touched): the B8 gate on `tableRows.length > 0` (ChallengeDetail.tsx:939, :950) is
  not consistency-scoped. `showTable` (:849) is true on any board for an anonymous viewer, so a legacy
  board whose podium holds everyone (e.g. Situp challenge, 1 athlete) also loses the "Everyone else"
  header and column row. That is probably what we want, but it changes a legacy board and no legacy test
  covers it.
R10 minor (docs): the diff does not touch docs/reference/100-club.md. The project rules say to add area
  notes there: the result block, the tie line, the "locks Sun" provisional bonus, and the bodyweight
  weight guard.
