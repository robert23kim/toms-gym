# QA notes: The 100 Club (2026-10-31)

QA ran against the uncommitted working tree on feat/100-club. Nothing was staged and no source file was left changed: every mutation was restored from an in-memory copy, and a sha256 check confirmed each restore. The temporary QA test dir frontend/src/__qa_tmp__ was deleted after its runs.
QA scripts (outside the repo): /private/tmp/claude-502/-Users-toka-code-toms-gym/8874654f-5c61-4aa4-9f4e-66122fe48be8/scratchpad/qa/
(test_qa_edges.py, qa.consistency.test.tsx, mut.py, mut-*.json, mut-*-out.json).

## Gates (after QA, final tree)
- Backend: `PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh` -> **339 passed, 8 deselected, exit 0**.
  As documented (no PYTEST_ADDOPTS), it exits 1 because the venv's pytest-cov cannot import `coverage`. This was already broken before the change (see notes-gate.md section 7) and is not a regression.
- Frontend: `npx tsc --noEmit` exit 0, no output.
- Frontend: jest --maxWorkers=4 -> **682/682 passed, 98 suites, 0 failed, exit 0** (jest-qa.json). Baseline was 634/634 in 92 suites. Every baseline test name is still present (0 missing).
- Test files in the diff: 8 files, 345 insertions, **0 deleted lines**. No existing test was removed or weakened.

## Mutation checks (QA's own, doers' tests)
Harness: replace one anchor that occurs exactly once, re-read the file to confirm the mutation is in place, run the named test, restore from memory, check sha256.
**Trap found and fixed:** the first backend pass ran two same-size mutations in the same second. Python validates .pyc files by mtime+size, so a stale bytecode file from the previous mutant ran instead of the new one: B7 "survived" falsely, and so did B6 on that pass. The re-run used PYTHONDONTWRITEBYTECODE=1 and purged the module's __pycache__ before and after each mutation. Doers' mutation claims made the same way may be unreliable.

| id | mutation | test | result |
|---|---|---|---|
| B1 | `top > 0` -> `>= 0` (zero never wins) | test_zero_never_wins_a_type_bonus | KILLED |
| B2 | bonuses also in the live week | test_current_week_is_live_with_provisional_leaders_not_in_score | KILLED |
| B3 | no streak reset after a missed week | test_quota_resets_to_base_after_a_missed_week | KILLED |
| B4 | plank leader judged on lifts, not seconds | test_plank_bonus_judged_on_seconds_not_lifts | KILLED |
| B5 | warm-up `w < 1` -> `w < 0` | test_warmup_attempts_score_nothing_and_are_counted_apart | KILLED |
| B6 | swap streak / weeks_met sort keys | test_tiebreak_streak_beats_weeks_met (and all of test_consistency.py, 32 tests) | **SURVIVED** |
| B6b | drop the streak key | test_tiebreak_streak_beats_weeks_met | KILLED |
| B7 | pending `+= 1` -> `+= 0` | test_pending_attempt_counts_zero_and_is_flagged | KILLED (after the pyc fix) |
| B8 | mode check never matches | test_leaderboard_consistency_mode_beats_lift_type_inference | KILLED |
| B9 | as_of admin gate bypassed | test_as_of_is_401_on_missing_or_wrong_token | KILLED |
| B10 | plank floor -> round | test_plank_exchange_rate_is_ten_seconds_per_lift_floored | KILLED |
| F1 | ring fraction not clamped at 1 | ConsistencyHero.test.tsx (11 tests) | **SURVIVED** (QA test kills it) |
| F2 | pill always "days" | prompts.test.ts | KILLED |
| F3 | scoreUnit "pts" removed | metric.test.ts | KILLED |
| F4 | leader chips shown when status is ended | ConsistencyHero.test.tsx | KILLED |
| F5 | formatWithUnit consistency branch removed | champion tests: survived (correct, because they do not use it); standing.test.ts + challenge tests: KILLED | guarded |
| F6 | hero never mounted in ChallengeDetail | ChallengeDetail.consistency.test.tsx | KILLED (4/4 fail) |
| F7 | home row links to /upload | prompts.test.ts + Index.consistency.test.tsx | KILLED |
| F8 | air squat default "60" | ChallengeDetail.consistency.test.tsx | KILLED |

## Edge cases run (scratchpad/qa/test_qa_edges.py: 30/31 pass; qa.consistency.test.tsx: 16/16 pass)
Pass, with the exact inputs:
- 2026-11-08T23:59:59-05:00 -> week 1; 2026-11-09T00:00:00-05:00 -> week 2; 2026-11-01T23:59:59-05:00 -> 0, 2026-11-02T00:00-05:00 -> 1.
- 2026-11-01T23:30-04:00 (= 22:30 EST) -> week 0. As a 20-rep squat: warmup_lifts 20, score 0, attempt_count 0, history [].
- Naive datetime(2026,11,2,4,59) -> week 0, 05:00 -> week 1 (naive is read as UTC). The strings "2026-11-02T05:00:00" and "2026-11-02 05:00:00" give week 1. Garbage or None created_at is dropped without a crash. The DB column is timestamptz (schema.sql:69), so prod rows arrive aware.
- Rules None, {}, {"base_quota": None}, "not a dict" and partial rules all fall back to the defaults. {"base_quota": 50} is honoured (60 lifts -> met, 100 pts).
- An attempt in week 9 (2026-12-28) after the end: status ended, week_index 9, days_left 0, score 0, 8 weeks, attempt_count 0.
- 2026-12-27T23:59:59-05:00 -> live week 8 with days_left 1. 2026-12-28T00:00-05:00 -> ended, type_leaders {}, the week-8 bonus locks (10 + 25), this_week.index 9.
- Pending situp + processing plank + a 10-rep squat -> pending 2, lifts 10, attempt_count 1. A pending warm-up attempt is not flagged.
- Plank 9.9 s -> 0 lifts; 10.0 -> 1; 19.99 -> 1.
- Situp with 11 reps, all form scores < 70 -> 5.5 lifts; score 5.5.
- Two athletes tied on 30 pushups: both get the Pushup bonus (55 each). While live, both are listed in type_leaders in name order and the score stays 30.
- Everyone at zero for a type: no bonus, no leader.
- A user with zero attempts: rank last, score 0, quota 100, streak 0, attempt_id/date None, history [].
- Met w1 (100), met w2 (125), w3 in progress at 0: streak 2, quota 150, score 350. After w3 is missed: streak 0, quota 100, best_streak 2.
- days_left: Monday 7, Sunday 1, upcoming 0. The upcoming shape: weeks [], this_week.index 0, quota 100, week 2026-11-02..08.
- Route: as_of without the header -> 401; with a wrong token -> 401; with a valid token -> 200, live, plank 95 s -> 9 pts. as_of "" -> 400. "2026-11-04 17:00:00" and "2026-11-04" -> 200. ADMIN_TOKEN unset -> 503. Without as_of the board is public, even with a bad token. as_of on a legacy board -> 200, metric time.
- Legacy Plank board -> metric time, score 95, no consistency block. Legacy Pushup -> reps 22. Legacy Situp -> reps.
- Frontend: weekLine "Starts Monday 2 Nov" / "Week 1 of 8 · 7 days left" / "Week 8 of 8 · 1 day left" / "Ended". Ring at 0 -> dashoffset = C; at quota -> 0 plus "Quota met"; above quota (240/125) -> clamped to 0 with text "240 / 125"; half credit "42.5 / 150". An anonymous visitor sees no ring.
- Pill: "42 / 150 · 1 day left", "… · 3 days left", upcoming "Starts Mon", anonymous null, non-entrant null, "42.5 / 150 · 2 days left". The anonymous home row is a link to /challenges/c1 (not /upload). The saved-user pill override works.
- formatWithUnit(325,"consistency") = "325 pts", 42.5 -> "42.5 pts". POINTS/pts/"Log this week's lifts". Legacy formatting is unchanged.
- Python 3.9 (stand-in for prod 3.10; no 3.10 on this machine): the pure module computes the boundaries and the live block correctly. fromisoformat on 3.9/3.10 rejects 1-digit fractions ("...:00.5+00:00"), so such an as_of gets a 400. Acceptable.

Failing case (1):
- rules {"tz": "Mars/Base"} -> GET /leaderboard **500** (ZoneInfoNotFoundError: 'No time zone found with key Mars/Base'). The doer already listed this. Tom creates the row, so the risk is low.

## Items
1. minor: invalid rules.tz (or week_start) makes that board 500. Repro: description metadata with "rules": {"week_start": "2026-11-02", "tz": "Mars/Base"} -> GET /competitions/<id>/leaderboard -> 500.
2. minor: the streak-over-weeks_met tiebreak order is unguarded. Swapping the two sort keys passes all 32 tests in test_consistency.py. test_tiebreak_streak_beats_weeks_met has weeks_met equal (2 == 2), so it never tests the precedence.
3. minor: the ring clamp above quota is unguarded by the doer tests (F1 survives ConsistencyHero.test.tsx). The behaviour is correct today.
4. minor (design, follows the spec): the type bonus has no minimum amount. Repro: two athletes, week 1 finished; p uploads a 9.9 s plank, q 3 squats. Result: q 28 pts (3 + 25), p **25 pts from 0 lifts** (Plank bonus). With few entrants, one tiny clip of each type earns +100/week, against 175 for someone who does 100 situps. Tom should confirm this is intended.

## Not covered
- No prod deploy or browser check by QA (that is a later stage). tzdata in the prod image (python:3.10-slim + requirements tzdata>=2024.1) is still unverified. Tests ran on 3.13 locally, plus a 3.9 smoke of the pure module.
- QA did not mutation-check type_leaders sorting, days_left arithmetic beyond Mon/Sun, or the Podium/YouRow rendering.

## Added after the advisor review: hero caption with backend-shaped payloads (MAJOR)
5. **major**: the ConsistencyHero caption shows "Week 0 quota" before the start and "Week 9 quota" after the end.
   Cause: ConsistencyHero.tsx renders `Week ${week.index} quota: ${week.quota} lifts` from viewerRow.this_week.index. The backend sends that as week_index, which is 0 before week_start and weeks+1 after the end (consistency.py line 231: `this_week = {"index": week_index, ...}`). The frontend fixture `upcomingConsistencyLeaderboard` uses `this_week.index: 1` (fixture line 264), so the doer tests pass against a shape the backend never sends.
   Repro: build the payload with rank_consistency for one joined athlete at now=2026-10-31T12:00-04:00 and at now=2026-12-28T12:00-05:00, then render <ConsistencyHero block=... viewerRow=row/>. Rendered text:
   - upcoming: "The 100 ClubStarts Monday 2 Nov0 / 100liftsWeek 0 quota: 100 lifts"
   - ended:    "The 100 ClubEnded20 / 100liftsWeek 9 quota: 100 lifts"
   This is the first thing a joined athlete sees in prod this weekend.
   Fix hint: on the frontend, key the caption off block.status (upcoming -> "Week 1 quota", ended -> "Final week", or hide the caption), or clamp the index to [1, weeks_total]. Then change the fixture to the real backend shape (index 0 / 9). The alternative is a backend change to the contract, which also means updating the spec text that says this_week.index is week_index.
   Scripts: scratchpad/qa/be-shapes.json, scratchpad/qa/qa.caption.test.tsx (2/2 fail as shown). The temp test dir was removed afterwards.
   Note on B6: the two "KILLED" results from the B6 full-suite run and the B6 QA-edges run are false kills. The first failed on deselected live-DB tests, the second on the always-failing bad-tz test. B6 (reordering the keys) is killed by nothing. Only removing the streak key is killed.
