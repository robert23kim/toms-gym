# Backend notes: The 100 Club (2026-10-31)

## What was built
- `backend/toms_gym/services/consistency.py` (new, pure, DB-free). Contains `DEFAULT_RULES`, `fill_rules`,
  `to_utc` (handles aware/naive datetime, date, and ISO strings with Z, an offset or none; naive = UTC),
  `local_date`, `week_of`, `attempt_lifts` and `rank_consistency(participants, rules, now, lift_types)`, which
  returns `(rows, consistency_block)`. Situp half-credit reuses `attempt_rep_score`.
- `challenge_leaderboard.rank_challenge(participants, *, metric, rules=None, now=None, lift_types=None)`
  dispatches `metric == "consistency"` and returns the tuple. The three legacy metrics are unchanged.
- `competition_routes.py`:
  - `_parse_metadata` added; `_parse_lifttypes` now uses it. `_mode_and_rules` fills the rule defaults
    when mode is consistency.
  - `_leaderboard_payload(session, id, now=None)` checks `mode == "consistency"` before the lift-type
    inference, defaults `now` to `datetime.now(timezone.utc)` and adds `payload["consistency"]`. No SQL
    change, so `_prow` is unchanged.
  - `GET /competitions/<id>/leaderboard?as_of=` goes through `ticket_routes._require_admin` (503 when
    unset, 401 on mismatch) and returns 400 when the ISO is unparseable. A naive as_of is read as UTC. An
    unencoded `+hh:mm` (decoded to a space) is repaired. Without the param the route is public as before.
  - `get_competition_by_id` returns `mode` and `rules` (defaults filled for consistency; both null on
    legacy rows). `create_competition` passes `mode`/`rules` into the metadata blob.
- `requirements.txt` gains `tzdata>=2024.1`. In the Dockerfile the production stage copies the build
  stage's site-packages wholesale and strips nothing, so the pip tzdata ships.
- `tools/run_ci_tests.sh` gains `tests/test_consistency.py`.
- Tests:
  - `tests/test_consistency.py`: 32 tests (rules plus scenario fixture plus upload weight 0).
  - `tests/test_competition_routes.py`: 12 new tests (mode, legacy, as_of gate, create/get round-trip).
  - `tests/test_champions.py`: 1 new test (consistency champion through the real ranker).
- `tests/consistency_scenario.py` holds the shared scenario as DB-shaped rows (string reps/held_s and aware
  created_at, like pg8000) behind a fake session. Its `__main__` regenerates
  `tests/fixtures/consistency_leaderboard_sample.json` through the real `_leaderboard_payload(..., now=AS_OF)`.
  `test_shared_scenario_fixture_matches_the_payload_builder` asserts fixture == regenerated payload, plus
  the headline numbers. Regenerate with: `cd backend && PYTHONPATH=. venv/bin/python tests/consistency_scenario.py`.

## Files
backend/toms_gym/services/consistency.py (new)
backend/toms_gym/services/challenge_leaderboard.py
backend/toms_gym/routes/competition_routes.py
backend/requirements.txt
backend/tools/run_ci_tests.sh
backend/tests/test_consistency.py (new)
backend/tests/consistency_scenario.py (new)
backend/tests/fixtures/consistency_leaderboard_sample.json (new, generated)
backend/tests/test_competition_routes.py
backend/tests/test_champions.py

## Decisions where the spec was silent (frontend and integrator: read these)
- **weeks before week_start:** `[]`. `this_week` is week 1 with zeros and quota = base_quota.
- **this_week.index:** literally `week_index` per the contract, so 0 before the start and weeks+1 (9)
  after the end. After the end, the other this_week fields are the last week's, with `leading: []`.
- **type_leaders:** only while status is live. It is `{}` when upcoming or ended. Leaders inside a type are
  sorted by name. The Plank amount is in seconds.
- **pending:** an attempt in a counted lift type whose result field (reps / held_s) is null and whose status
  is not `completed`. A completed attempt with no result counts zero, is not pending, and is not in
  history.
- **Lift types outside the challenge's counted set** (anything other than Situp/Pushup/Squat/Plank, or not
  declared) are left out of history, attempt_count, pending and warm-up. They still appear in `by_type` at
  0 if declared.
- **Streak:** consecutive met weeks. The week in progress adds 1 once met and never breaks the streak while
  unmet. Quota = base + ramp x (met weeks in a row before this week).
- **Numbers:** integral floats are emitted as ints (45, not 45.0). A half-credit situp total stays x.5.
- **Dates:** history and row `date` are the local date in the challenge tz, not the UTC date.
- **as_of** keys only the week logic, as the spec says. An attempt created after as_of but inside the week in
  progress is still counted. Only later weeks are ignored.
- **Name tiebreak** is case-insensitive, then user_id.
- **Zero-points-last** is enforced by the first sort key. It is equivalent to `-score` (scores are never
  negative), so that key's mutation would always survive; it was not counted as a guard.

## Shared scenario, derived by hand (as_of Thu 2026-11-19 15:00 America/New_York)
The code output matched every number in the brief. Neither side was wrong.
- Block: live, week_index (2026-11-19 - 2026-11-02) = 17 days, //7 = 2, +1 = 3. Week 3 runs 11-16..11-22.
  days_left = (11-22 - 11-19) + 1 = 4. Situp leader Ana 42 (Ben 0). Plank leader Ben 100 s (Ana 0 this week).
  Pushup and Squat are all zero, so no key. momentum joined 3, uploaded_today 0 (mocked COUNT).
- **Ana 467.**
  - Warm-up 2026-10-31 is week 0: pushup 20 goes to warmup_lifts.
  - W1 (quota 100): plank 240/10 = 24; situp 40 clean + 10 x 0.5 = 45; pushup 43; total 112, met.
    Bonuses: Situp (45 vs Ben 0) and Plank (240 s vs 0). Pushup goes to Ben (60 > 43).
    Points 100 + 50 + 25 + 25 = 200.
  - W2 (quota 125): pushup 70 + situp 60 = 130, met. Situp and Pushup bonuses (Ben 0 for both). Squat goes
    to Ben. Nobody planked. Points 125 + 50 + 50 = 225.
  - W3 (quota 150): situp 42, not met, live 42. Situp leading is provisional and not scored.
  - Total 467. streak 2, best 2, weeks_met 2, attempt_count 6, history 24, 45, 43, 70, 60, 42.
    Latest counted attempt is the 11-17 situp.
- **Ben 330.**
  - W1 (quota 100): pushup 60 + squat 35 = 95, missed. Pushup and Squat bonuses. Points 95 + 50 = 145.
  - W2 (quota reset to 100): squat 100, met. Squat bonus. Points 100 + 50 + 25 = 175.
  - W3 (quota 125): plank 100 s = 10 lifts, plus 1 pending pushup. Live 10, leading Plank.
  - Total 330. streak 1, best 1, weeks_met 1, attempt_count 4 (pending excluded). Latest is the 11-18 plank.
- **Cy 0.** Three empty weeks, quota 100 each. Rank 3 (zero points last).

## tzdata proof (the check that could fail)
- `PYTHONTZPATH= venv/bin/python -c "from zoneinfo import ZoneInfo; ZoneInfo('America/New_York')"` raises
  ZoneInfoNotFoundError (no system zoneinfo, no tzdata package).
- The same command with `PYTHONPATH=<scratch>/tzpkg` (the tzdata wheel installed there via
  `python3 -m pip install --target`) prints `America/New_York 2026f`.
- The venv's own pip is broken (`No module named pip._internal.operations.build`), so tzdata is NOT
  installed in backend/venv. The local tests pass on macOS system zoneinfo.
- Not covered: I did not build the image (Docker daemon not running), so tzdata presence in the prod image
  is inferred from requirements.txt plus the Dockerfile's site-packages copy. Verify after deploy by calling
  the consistency leaderboard and checking for a 200.

## Squat weight 0
Verified by reading `upload_routes._create_attempt_record` (`float(weight)`, no positivity check) and by
`test_upload_accepts_squat_with_weight_zero`, which calls it with "0" and asserts weight_kg 0.0 in the
Attempt INSERT. The multipart `/upload` path has the same `float(weight)` at line ~363 and was checked by
reading only. Not covered: the frontend form's own validation.

## Mutation table (harness: scratchpad/backend-doer/mutate_backend.py)
Each row: break the anchor (asserted unique), re-read the file to confirm it changed, run the named test
with -k, restore from the in-memory original, re-read to confirm equality. A final `diff -q` against the
saved copies printed RESTORED_IDENTICAL.

| guard | mutation real | failed when broken | restored | pytest tail |
|---|---|---|---|---|
| ramp | True | True | True | 1 failed, 31 deselected in 0.02s |
| reset | True | True | True | 1 failed, 31 deselected in 0.02s |
| cap | True | True | True | 1 failed, 31 deselected in 0.02s |
| quota bonus | True | True | True | 1 failed, 31 deselected in 0.02s |
| type-bonus tie | True | True | True | 1 failed, 31 deselected in 0.02s |
| zero never wins | True | True | True | 1 failed, 31 deselected in 0.03s |
| plank exchange | True | True | True | 1 failed, 31 deselected in 0.02s |
| plank bonus on seconds | True | True | True | 1 failed, 31 deselected in 0.02s |
| situp half credit | True | True | True | 1 failed, 31 deselected in 0.02s |
| warm-up exclusion | True | True | True | 1 failed, 31 deselected in 0.02s |
| week boundary (local tz) | True | True | True | 1 failed, 31 deselected in 0.02s |
| naive created_at is UTC | True | True | True | 1 failed, 31 deselected in 0.02s |
| provisional current-week bonus | True | True | True | 1 failed, 31 deselected in 0.02s |
| future week cannot score | True | True | True | 1 failed, 31 deselected in 0.02s |
| pending count | True | True | True | 1 failed, 31 deselected in 0.02s |
| days_left Sunday counts 1 | True | True | True | 1 failed, 31 deselected in 0.02s |
| tiebreak streak | True | True | True | 1 failed, 31 deselected in 0.02s |
| tiebreak weeks_met | True | True | True | 1 failed, 31 deselected in 0.02s |
| tiebreak this-week lifts | True | True | True | 1 failed, 31 deselected in 0.02s |
| tiebreak name case-insensitive | True | True | True | 1 failed, 31 deselected in 0.02s |
| as_of auth gate | True | True | True | 2 failed, 31 deselected, 3 warnings in 5.18s |
| as_of plumbed into payload | True | True | True | 1 failed, 32 deselected, 3 warnings in 5.08s |
| as_of '+' restore | True | True | True | 1 failed, 32 deselected, 3 warnings in 4.94s |
| as_of garbage -> 400 | True | True | True | 1 failed, 32 deselected, 3 warnings in 4.86s |
| mode beats lift-type inference | True | True | True | 1 failed, 32 deselected, 3 warnings in 4.90s |
| create passes mode/rules | True | True | True | 1 failed, 32 deselected, 3 warnings in 4.81s |
| get-by-id returns mode | True | True | True | 1 failed, 32 deselected, 3 warnings in 4.71s |
| get-by-id fills rule defaults | True | True | True | 1 failed, 32 deselected, 3 warnings in 4.78s |
| fixture drift | True | True | True | 1 failed, 31 deselected, 3 warnings in 0.75s |

The first harness run had 3 survivors: the streak, weeks_met and this-week-lifts tiebreaks. Each test's
lower-priority keys (this-week lifts, name, user_id) agreed with the expected order. The tests were
rewritten so the winner loses on every lower key, and all three now fail when broken.

Also caught: pytest `--deselect` matches node-id prefixes. CI's
`--deselect ...::test_create_competition` and `...::test_get_competition_by_id` silently dropped 4 new
tests (deselected 8 -> 12). They were renamed (`test_creating_a_...`, `test_competition_by_id_...`) and
the count is back to 8.

## Gate
`cd backend && PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh` returned exit 0.
The `-p no:cov` workaround from notes-gate.md is needed because the venv has pytest-cov without coverage.
    339 passed, 8 deselected, 11 warnings in 7.22s
Baseline was 294 passed / 8 deselected. Now 339 passed / 8 deselected / 0 failed (+45 new tests).

## Open issues / handoffs
- **Shared scratchpad collision.** The frontend doer and I share the session scratchpad. Their
  `scratchpad/mutate.py` overwrote mine at 10:17, and two of my invocations ran their script with a path
  argument. Their script reads argv as an index filter, so every mutation was skipped (no frontend file was
  touched), but it wrote `[]` over their `scratchpad/mutations.json`. Their run rewrites that file when it
  completes. If it had already completed, re-run it. My harness now lives in `scratchpad/backend-doer/`.
- The venv's pip and coverage are broken (pre-existing). Repairing the venv is out of scope.
- The prod check after deploy should include one `?as_of=` call with the admin token, which exercises
  zoneinfo in the container.

## Other payload consumers (checked)
I grepped `_leaderboard_payload|rank_challenge|metric ==` across `toms_gym`. There are three callers:
- the leaderboard route
- `get_champions`
- `achievement_routes._championship_count`

The last two only pass the payload to `shape_champions`, which reads `rank`, `score`, `attempt_count` and
`date`. `test_consistency_board_champion_is_rank_one_on_points` covers that path. No other code branches on
metric.

`create_competition` is public and does not validate `rules`. A bad `tz` or `week_start` would 500 that one
board. The row is created by Tom, so this does not block.
