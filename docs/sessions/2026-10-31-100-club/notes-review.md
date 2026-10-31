# 100 Club review notes (reviewer, 2026-10-31)

## Gates (run by the reviewer)
- Backend: `cd backend && PYTHON=venv/bin/python tools/run_ci_tests.sh` exits 1 as written: pytest_cov import fails
  (`ModuleNotFoundError: No module named 'coverage'`). This venv breakage predates this work. With
  `PYTEST_ADDOPTS="-p no:cov"` the gate exits 0: 339 passed, 8 deselected. tests/test_consistency.py collects 32 tests.
- Frontend: `npx tsc --noEmit` exit 0, no output.
- Not covered: jest was not run (QA owns it). Every backend probe ran on the venv's Python 3.13. CI
  (.github/workflows python-version '3.10') and the prod Dockerfile (python:3.10-slim) use 3.10, and no 3.10 is installed
  on this machine. Nobody built the image, so tzdata is unverified. I did not re-run the doer's mutation table.

## Contract (backend fixture vs frontend fixture)
- Live board: the structure matches key for key. The only differences are value-level and expected: competition_id,
  rows[0..1].attempt_id and rows[0..1].clip_url. Scenario numbers match (Ana 467, Ben 330, Cy 0, the week tables, history).
- The upcoming and ended frontend fixtures are hand-made. I generated the backend equivalents through _leaderboard_payload with
  as_of 2026-10-31 15:00 NY and 2026-12-28 09:00 NY:
  - upcoming: `$.rows[*].this_week.index` backend 0, frontend 1.
  - ended: the frontend keeps `$.consistency.type_leaders.{Situp,Plank}`, but the backend sends `{}`.
    `$.rows[*].weeks` has 8 entries in the backend and 3 in the frontend. `$.rows[*].this_week.index` is 9 in the backend and 3 in the frontend.
    `this_week` is all zeros in the backend (week 8), quota 100, leading [], while the frontend keeps the live week-3 numbers.
    In the backend, `rows[0].weeks[2]` points 67 / bonuses [Situp]; the frontend has 42 / [] (the bonuses lock at the end).
    `rows[0].score` is 492 in the backend and 467 in the frontend; `rows[1].score` is 355 and 330. `streak` is 0 in the backend and 2/1 in the frontend.

## Findings
R1 MAJOR ConsistencyHero.tsx:89 renders `Week ${week.index} quota: ${week.quota} lifts`. this_week.index equals
   week_index (spec line 109), which is 0 before the start and 9 after the end. Every entrant viewing the board right now
   (2026-10-31 to 11-01, the state Tom tests this weekend) sees "Week 0 quota: 100 lifts". After the end it shows
   "Week 9 quota: 100 lifts", or "Quota met - the bar rises next week." The tests miss this because the upcoming
   fixture uses index 1 and the ended fixture uses 3.
   Fix: drive the copy from block.status. Before the start: "Week 1 quota: 100 lifts". After the end: hide the line or show the
   final tally. Set the fixtures to 0 and 9.
R2 MAJOR create_competition (competition_routes.py:723, no auth) stores `rules` verbatim. rank_consistency does not validate
   them, and _mode_and_rules/fill_rules does not coerce them. In the probe, tz "Mars/X" raised ZoneInfoNotFoundError,
   week_start "Nov 2" raised ValueError, and base_quota "100" raised TypeError. GET /champions (competition_routes.py:641) and
   achievement_routes.py:45 build _leaderboard_payload for every ended competition, so one bad consistency row would 500
   the Hall of Champions and achievements for everyone once it ends. Today's legacy parsing tolerates garbage.
   Fix: validate and coerce in fill_rules, falling back to defaults, or reject at create time with a 400.
R3 MAJOR Spec gap (spec line 164, CLAUDE.md multi-category rule). ChallengeVideos.tsx:154 still links
   /challenges/<id>/upload. UploadVideo.tsx hardcodes its lift list there (no Plank, no per-challenge filter), so a 100 Club
   athlete can reach an upload page that cannot log a plank. ResultLadder was fixed; this link was not.
R4 MINOR The frontend upcoming/ended fixtures do not mirror the backend (paths above). "drops the leading chips once ended" passes
   only because of the status gate, with leaders present in the fixture.
R5 MINOR ChallengeDetail.tsx:110-111 initialises liftType "Squat" and weight "60". The categories effect (:505-506) only resets
   when the current type is disallowed, and Squat is allowed, so the 100 Club modal opens on Squat 60. The air-squat 0 default
   (:190-195) fires only when the dropdown changes. Bodyweight lifts also post the stale weight. Scoring ignores weight, so
   the damage is cosmetic and limited to history.
R6 MINOR prompts.ts buildPrompts: `pill = pills[c.id] ?? c.categories?.[0]`. Anonymous visitors, and saved users who have
   not joined, see "Situp" on a four-type challenge. Returning users see "Situp" flip to "42 / 150 ..." once the board fetch
   lands. The spec asks for a plain link row (no pill) for anonymous visitors.
R7 MINOR _parse_as_of (competition_routes.py:562-576) replaces every space with '+'. A space-separated datetime
   ("2026-11-03 12:00:00") becomes "2026-11-03+12:00:00". On 3.13 that parses as 12:00 UTC; on the 3.10 prod runtime
   fromisoformat is stricter and should reject it as a 400. Use the one form that works everywhere:
   `?as_of=2026-11-04T12:00:00-05:00` (or Z).
R8 MINOR Docs gap: no docs/reference/100-club.md (spec Non-goals cites "the reference doc" for the squat-counting limitation),
   and no CLAUDE.md feature-table line.
R9 MINOR a11y: aria-label on generic <span> (ConsistencyMeta StreakFlame, ConsistencyWeekTable met/missed cells). ARIA does
   not allow naming the generic role, and some screen readers ignore it. Use visually-hidden text or role="img".
   Buttons use aria-expanded and the table has th headers, which is fine.
R10 NOTE frontend/src/__qa_tmp__/ (QA scratch) sits inside src. It must not be staged, and tsc/jest pick it up.

## Checked and correct
- Metric: mode == "consistency" is checked before lift-type inference (competition_routes.py:507). With the same lifts and no mode the board stays on the legacy metric (route test).
- Legacy rank_challenge path unchanged; non-consistency payload has no `consistency` key.
- as_of: 503 when ADMIN_TOKEN is unset, 401 on a missing or wrong token, public without the param, 400 on garbage (route tests + _require_admin reuse).
- Week boundaries (probe): 2026-11-02T04:59:59Z is week 0, 05:00Z is week 1. 2026-11-09T04:59Z is week 1, 05:00Z is week 2.
  Naive datetimes are treated as UTC. The DST fall-back on 11-01 happens before the start, so it only touches warm-up.
  Attempt.created_at is timestamptz.
- days_left: Sun 23:00 gives 1 and Mon 00:30 gives 7. 2026-12-27 23:59 NY is live week 8; 12-28 00:01 is ended, week_index 9.
- Ramp 100/125/150, reset to 100 after a miss. The streak does not reset during the live week. Lift points are capped at the quota.
  The quota bonus counts live. Type bonuses count only for finished weeks. Ties share the bonus. Zero never wins. Plank is judged on
  seconds (9.9 s wins the plank bonus with 0 plank lifts, which is spec-literal). Future weeks are skipped via cap. A pending
  attempt is flagged only when status != completed. Failed attempts are excluded in SQL. LiftingResult.attempt_id is UNIQUE,
  so the join cannot double-count.
- Tiebreaks: points, streak, weeks_met, this-week lifts, name, user_id. Zero rows go last.
- Champions: the end_date (12-27 23:59:59-05:00) lines up with week 9, so the champion scan sees status ended. Every champion surface
  (ChampionCard, ChampionHero, Spotlight, TrophyCase, NextToBeCrowned) uses formatChampionScore, which now prints "N pts".
- Air squat weight 0: /upload/finalize calls _create_attempt_record (upload_routes.py:574) and does not reject weight.
  float("0") is accepted. The modal's min is 0 on consistency boards.
- ChallengeDetail scope: viewerId (:92), openUpload, resolveClipHref, rowNickname, consistencyBlock, viewerBoardRow and
  liveWeekIndex (:668-675) are component-level. isConsistency, expandable and detailPanel are used only inside the IIFE. tsc is clean.
- Bare ISO: startDayLabel uses `${iso}T00:00:00`.
- get_competition_by_id returns mode/rules (filled), or null on legacy rows. create_competition round-trips mode/rules.
