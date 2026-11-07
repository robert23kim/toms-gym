# QA notes, 2026-11-07: commits 993990f..764863a (B1 backend guard, B2-B10 frontend)

Verdict: no regression found. 7/7 of my own mutations killed, 9/10 live-payload render cases pass, the 1 failure
is a copy gap (QA-1), not a regression. All evidence is jsdom + Flask test client; nothing deployed or rendered
in a real browser by me.

## Mutation checks (harness: in-memory original, anchor count == 1, mutation re-read from disk, single test
file run, restore from bytes, byte-compare == original). Picked to not repeat the doers' 24.
| id | file | mutation | test | result |
|---|---|---|---|---|
| B1 | upload_routes.py | bodyweight_weight_kg `return 0` -> `return weight_kg` | test_bodyweight_weight.py | 10 failed / 3 passed (controls), restored True |
| B2 | upload_routes.py | drop "plank" from BODYWEIGHT_LIFT_TYPES | same | 3 failed (the Plank cases), restored True |
| F1 | ConsistencyResult.tsx | `week.met ? "Quota met · ..." : progress` -> `progress` | ConsistencyResult.test | 1 failed ("says the quota is met"), restored True |
| F2 | ConsistencyWeekTable.tsx | `t === "Plank"` -> `"Plonk"` | ConsistencyWeekTable.test | 1 failed (breakdown), restored True |
| F3 | StatusPill.tsx | `Ongoing · ends ${x}` -> `Ongoing · ${x}` | ChallengeDetail.consistency.test | 1 failed, restored True |
| F4 | AnalysisStatus.tsx | club gate `=== "consistency"` -> `"consistencyX"` | AnalysisStatus.test | 1 failed (club case), restored True |
| F5 | LiftHub.tsx | `c.mode === "consistency"` -> `"consistancy"` | LiftHub.test | 2 failed, restored True |
Note: running test_bodyweight_weight.py bare (without `--noconftest`) gives 13 ERRORS: conftest wants a DB at
db-test:5432 (unresolvable, DATABASE_URL unset; nothing reached). The gate passes --noconftest; baseline with
it = 13 passed.

## Live-payload renders (temp suite frontend/src/__qa_tmp__/qa.test.tsx, copy kept at
/private/tmp/claude-502/-Users-toka-code-toms-gym/fe49fbdc-4643-4589-9b3f-d81e9b1ac6e9/scratchpad/qa.test.tsx;
dir deleted before the gate). Fixtures: live-before.json + the prod GET /competitions list (read-only curl,
canary: 7 competitions incl. "The 100 Club"; the list item has NO `mode` key).
- ChallengeDetail, anonymous and viewer 7844e26d: PASS both.
  - bonus note "Type bonuses (+25 each) are added when the week ends on Sunday."; eyebrow "Weekly quota"
  - tie line "caleb.li.larson and Toka are tied on points; more lifts this week puts caleb.li.larson ahead."
    (the doer's inferred string, now rendered against live data)
  - status pill "Ongoing · ends Sun 27 Dec"; no "Everyone else"; no leaderboard-header
  - caleb week row: bonus "Pushup, Plank · locks Sun"; types "Plank 11 (119.5 s) · Pushup 65 · Situp 31.5"
    (order follows payload key order Plank, Pushup, Situp; 119.48552762923352 rounds to 119.5; no long floats
    anywhere in hero or table)
  - anonymous: YOU row "Not logged yet" stays as CTA. Toka viewer: ring "100 / 100", "You lead Situp this
    week", no YOU row (she is on the podium).
  - page also GETs /competitions/<id>/lifts (answered empty; not a defect).
- VideoPlayer, live club board, owner Toka, 13 clean situps: "+13 lifts banked · Quota met · 100 / 100 this
  week · 2 days left", no "to pass", no "Where ... stands". PASS.
- VideoPlayer, viewer Toka on caleb's video: "+13 lifts banked · Quota met · 107.5 / 100 this week" with no
  name -> FAIL of my assertion, QA-1.
- VideoPlayer legacy reps board: ladder renders ("4 reps to pass rob"), no club block. PASS.
- AnalysisStatus live club: situp -> heading "13 reps", "+13 lifts banked · Quota met · 100 / 100 ..."; plank
  82.79 s -> heading "82.8s", "+8 lifts banked"; no ladder. Legacy reps board keeps "4 reps to pass rob". PASS.
- LiftHistoryList with Toka's real prod rows (situp/pushup/plank weight 60.0) + a Squat 60: only "Squat ·
  60kg" shows. PASS.
- LiftHub through the REAL getCompetitions/transformCompetitionData on the prod list: transform yields
  mode "consistency" from the description fallback; tile "The 100 Club · Log this week's lifts" ->
  /challenges/32ca7bad...; "Summer plank challenge" tile absent (not ongoing). PASS. (The doer's LiftHub test
  mocks getCompetitions past the transform, so this was the unproven link.)

## Backend upload form (temp tests/test_qa_tmp_weight.py, deleted) via Flask test client, multipart /upload
7 passed: club Pushup "60" -> lift_type Pushup, weight_kg 0; legacy-id Squat "60" -> 60.0; legacy-id Pushup
"60" -> 0 (guard ignores competition_id by design); Situp "" -> 0; Squat "abc" -> 0; Plank "-5" -> 0.

## Findings
- QA-1 major by the bug log scale (a user is misled; copy, B2): ConsistencyResult has no owner awareness. Viewer 7844e26d on
  /challenges/32ca.../participants/b7bb417c.../video/v1 sees "+13 lifts banked / Quota met · 107.5 / 100 this
  week · 2 days left", caleb's numbers phrased as if they were the viewer's. ResultLadder used isOwner ("Where
  Toka stands"). Fix: pass isOwner + name, prefix "caleb.li.larson: " for non-owners.
- QA-2 minor (pre-existing, code-read only): LIFT_TYPE_MAPPING.get(lift_type, "snatch") means a lowercase or
  unknown lift_type ("pushup") is stored as "snatch" and skips the bodyweight guard (weight kept). Current
  clients post capitalised names, so B1 is covered; not a regression.
- QA-3 minor (code-read, not rendered with a delayed leaderboard): StatusPill's endsLabel comes from the
  leaderboard's consistency block, so the pill reads "Ongoing · 51d left" until the board loads, then flips
  to "ends Sun 27 Dec" (the challenge object lacks mode in ChallengeDetail). Fix: derive from challenge mode.
- QA-4 minor (code-read): VideoPlayer share text on a club board still uses standingShareText ("I'm #2 of 2
  in the The 100 Club - 150 pts"; note the doubled "the").

## Gates (after deleting __qa_tmp__)
- backend: rc 0, 380 passed, 8 deselected (matches doer).
- frontend `npx tsc --noEmit`: rc 0. `-p tsconfig.app.json`: 43 errors (same count as doer's before/after),
  none in the 24 touched paths (files are Login, ui/*, MomentumLine/Podium/StandingCard tests, ...).
- jest --maxWorkers=4: 105 suites, 719/719 passed, 0 runtime errors, no __qa_tmp__ suite in the run.
  JSON: docs/sessions/2026-11-07-100-club-week1/jest-qa.json
- git status on backend/toms_gym, backend/tests, backend/tools, frontend/src: only the two pre-existing untracked paths.

## Not covered
No browser or Playwright render, no phone width, no prod deploy check (B1 guard on a live revision, APK
rebuild B1a). Test diff: additions only, except one import line rewritten in ConsistencyHero.test.tsx (adds finalDayLabel); no assertion removed.
