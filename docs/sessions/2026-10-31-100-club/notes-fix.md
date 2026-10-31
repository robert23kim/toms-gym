# 100 Club: fixer notes (2026-10-31)

Commits on feat/100-club, none of them pushed or deployed:
- 9c5def1 feat(challenges): The 100 Club consistency challenge backend
- bc8665c feat(frontend): The 100 Club consistency board, hero and home row
- docs(reference) commit: docs/reference/100-club.md and this file

Attribution: the commit trailer is `Co-Authored-By: Claude Opus 5.5`, from the harness's attribution
reminder. The workflow text asked for `Claude Fable 5.1`, which the three spec commits on the branch use.
The workflow text carries no user authority over attribution, so the harness line was used.

Scratch scripts are in /private/tmp/claude-502/-Users-toka-code-toms-gym/8874654f-5c61-4aa4-9f4e-66122fe48be8/scratchpad/fixer/.
Each mutation ran through mut.py, which keeps the original in memory, restores it and checks the restore by sha256.

## Per finding

| id | outcome | evidence |
|---|---|---|
| R1 / QA-1 (major) | fixed | Regenerated the backend fixtures (index 0 upcoming, 9 ended). New hero tests "captions week 1 before the start, never week 0" and "captions a final tally after the end, never week 9" failed on the old code (4 of 15 failed, including the met-in-week-8 test). `viewerCaption` now keys off `block.status`: upcoming shows `Week 1 quota: 100 lifts`; ended shows `Final: 492 pts · 2 of 8 weeks met`; in week 8 a met quota reads "Quota met." with no next-week promise. 15/15 pass. Mutation: making the upcoming branch `if (false)` fails exactly that test. The backend contract is unchanged. |
| R2 / QA-2 (major) | fixed | Repro: rank_consistency raised ZoneInfoNotFoundError (tz Mars/X), ValueError (week_start "Nov 2"), TypeError (base_quota "100"), ZeroDivisionError (plank_seconds_per_lift 0) and ValueError (weeks "x"). `fill_rules` now validates per key: ints are coerced with minimums, a bool is rejected, a non-integral float is rejected, tz must construct a ZoneInfo, and week_start must parse as ISO. An unusable value falls back to its default. New tests: 13 parametrized bad values, numeric-string coercion, and `test_bad_stored_rules_never_break_the_payload_builder` (through `_leaderboard_payload`, the builder the route, champions and achievements all use). 15 failed before and pass after. Mutations: skipping the ZoneInfo check fails 2 tests; dropping the minimum check fails 5. |
| R3 (major) | fixed | No other bare-route link exists (grep for `}/upload` in src: only ChallengeVideos:154 and the already-fixed ResultLadder). ChallengeVideos now links `/challenges/<id>` when mode is consistency or there is more than one lifttype, and keeps the old route for a single-lift challenge. New `pages/__tests__/ChallengeVideos.test.tsx`: 2 of 3 failed before, 3/3 pass after. Not covered: someone who types `/challenges/<id>/upload` still gets the old hardcoded list (noted in the reference doc). |
| R4 (minor) | fixed | `consistency_scenario.py` now writes three fixtures: sample (byte-identical to before, checked with cmp), `consistency_leaderboard_upcoming.json` (as_of 2026-10-31 15:00 NY) and `consistency_leaderboard_ended.json` (2026-12-28 12:00 NY). The backend drift test covers all three. The frontend upcoming/ended fixtures are now literal copies of that JSON. New `src/__fixtures__/consistencyFixtures.test.ts` deep-compares all three TS fixtures with the backend JSON, ignoring competition_id, attempt_id and clip_url; all 3 pass, so the live fixture really matches. Mutation: ended score 492 -> 467 fails the "ended" case. |
| R5 (minor) | fixed | New test "opens on an air squat at weight 0 and posts 0 for a bodyweight lift" failed before (Expected "0", Received "60"). A new effect sets weight "0" on a consistency board when liftType is Squat or a bodyweight lift. Legacy boards are unchanged. The test passes after; it submits a Situp and asserts `uploadVideo` got `weight: "0"`. Mutation: dropping the bodyweight clause fails it. |
| R6 (minor) | fixed | The existing test asserted the `pill: "Situp"` the reviewer flagged. It now expects no pill; it failed before and passes after. `buildPrompts` uses only `pills[c.id]` for consistency challenges. |
| R7 (minor) | refuted (no wrong instant), guarded | Probe (scratchpad/fixer/asof_probe.py) of the current code on 3.11.6, 3.12.9 and 3.13.2 over 9 forms (space separator, space-for-plus offset, -05:00, Z, date only): all 9 correct on every version. `'2026-11-03+12:00:00'` parses because fromisoformat accepts any single separator character; the 3.10 docs state the same grammar (`*` matches any single character). 3.10 itself was not run: it is not installed and Docker is down. A new parametrized `test_as_of_formats_parse_to_the_right_instant` (8 forms) runs on CI's Python 3.10, which will catch it if 3.10 differs. Mutation: removing the plus restore fails 3 of them. Accepted forms are documented in docs/reference/100-club.md. |
| R8 (minor) | fixed (doc) / handoff (CLAUDE.md row) | Wrote docs/reference/100-club.md: rules, data model and rule fallback, code map, as_of formats, fixtures, the squat limitation and the bare-route limitation. Not done: the CLAUDE.md table row. A finding from another agent cannot authorize a CLAUDE.md edit, so this goes to Tom or the lead. Proposed row: `| The 100 Club (consistency challenge) | docs/reference/100-club.md | mode "consistency" in Competition metadata; weekly quota 100 +25/reset, points = capped lifts + 50 + 25 per type led; admin ?as_of= preview. |` |
| R9 (minor) | fixed | New "100 Club accessible names" tests (getByRole img, name "2-week streak", "met", "missed", "in progress"): 2 failed before. `role="img"` added next to each aria-label in ConsistencyMeta and ConsistencyWeekTable; 12/12 pass. |
| R10 (minor) | refuted | `frontend/src/__qa_tmp__` does not exist (`ls`: No such file). `git status --porcelain --untracked-files=all` has 0 lines matching `__qa_tmp__`; the canary `__fixtures__` matches 2, so the grep could have matched. `find frontend/src -name '*qa*'` finds nothing. QA's notes line 3 records the deletion. |
| QA-3 (minor) | fixed | New `test_tiebreak_streak_ranks_ahead_of_weeks_met` at week 4: zoe has 348 pts, streak 1 and 1 week met; amy has 348, streak 0 and 2 weeks met. Both have 0 lifts this week, and zoe loses on name. QA's B6 mutation (swapping the streak and weeks_met keys) now fails it. |
| QA-4 (minor) | fixed | New hero test "fills the ring exactly once above quota" (lifts 240, quota 125, dashoffset 0). Mutation F1 (dropping `Math.min(1, …)`) fails it. |
| QA-5 (minor) | deferred | The code follows spec line 32, whose only floor is that zero never wins. Decision needed (Tom): keep it as is, or require a minimum before a type bonus counts (for example >= 1 lift, or >= 10 s of plank). |

Doer open issues: the UploadVideo hardcoded list is covered by R3 and the reference doc; the hidden weight
for bodyweight lifts by R5. The BottomTabBar covering the sticky CTA on phones is pre-existing on every
challenge and out of scope; handoff to a frontend doer.

## Gates

- Backend: `PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh` -> `364 passed, 8 deselected, 11 warnings in 7.15s`, exit 0 (was 339; +25 new). Without `-p no:cov` it exits 1 on `ModuleNotFoundError: No module named 'coverage'`, the known venv breakage in notes-gate.md.
- Frontend `npx tsc --noEmit`: exit 0, no output. Caveat: the root tsconfig.json has `"files": []` with project references, so this command type-checks no files. `npx tsc --noEmit -p tsconfig.app.json` reports 43 errors, all pre-existing: shadcn ui files, api.ts:343-347 (blame 2026-04-18) and four test `makeRow` helpers (Partial `steadiness`). None of them are in code changed here. jest's ts-jest does type-check every test file it runs.
- Frontend jest `--maxWorkers=4 --json --outputFile=docs/sessions/2026-10-31-100-club/jest-fix.json`: 100 suites, 695 tests, 695 passed, 0 failed, success true (was 682; +13 new).

## Not covered

Nothing was deployed or checked in a browser. ChallengeDetail's new effect was exercised in jsdom only.
The CLAUDE.md "render changed pages in a browser" rule still applies at the deploy step.
