# The 100 Club (consistency challenge)

Design contract: `docs/superpowers/specs/2026-10-31-100-club-design.md`. This file holds the operational notes.

## Rules

- Lifts that count: Situp, Pushup, Squat (one per rep; situps keep the clean-full / sloppy-half rule of
  `attempt_rep_score`) and Plank (`floor(held_s / 10)`). Any other lift type counts zero.
- Weeks run Monday to Sunday in `America/New_York`. Week 1 starts 2026-11-02 and there are 8 weeks. An
  upload belongs to the week of its `Attempt.created_at` in that zone. Uploads before week 1 are warm-up:
  they show as `warmup_lifts` and score nothing.
- Quota: 100 in week 1. After a met week the next quota is +25; after a miss it resets to 100. Nobody is
  eliminated.
- Weekly points: `min(lifts, quota)` + 50 when met + 25 per type led (plank judged on seconds). Ties at the
  top share a bonus and zero never wins. The week in progress scores lifts and the quota bonus live; its
  type leaders are provisional and lock when the week ends.
- Ranking: points, then current streak, then weeks met, then this week's lifts, then name. Zero-point rows go last.
- Open design question (QA-5, 2026-10-31): a type bonus has no minimum amount, so a 9.9 s plank with 0
  lifts still earns +25 when nobody else planked.

## Data model

There is no table. The challenge is a `Competition` row whose description metadata carries
`"mode": "consistency"` and `"rules": {base_quota, ramp, weeks, quota_bonus, type_bonus,
plank_seconds_per_lift, tz, week_start}`. `create_competition` stores `rules` as given. On read,
`services/consistency.fill_rules` replaces any missing or unusable value with its default: a non-integer
or out-of-range number, an unknown `tz`, or a `week_start` that is not `YYYY-MM-DD`. A bad row therefore
never 500s the leaderboard, `GET /champions` or achievements, which build every ended board.

## Code

- `backend/toms_gym/services/consistency.py`: pure scoring (`rank_consistency`), dispatched from
  `rank_challenge(metric="consistency", rules=, now=, lift_types=)`.
- `backend/toms_gym/routes/competition_routes.py::_leaderboard_payload`: `mode == "consistency"` selects the
  metric before the lift-type inference.
- Frontend: `components/challenge/ConsistencyHero.tsx`, `ConsistencyMeta.tsx`, `ConsistencyWeekTable.tsx`,
  `lib/prompts.ts` (home pill), `components/challenge/metric.ts` (points formatting).
- The hero caption keys off `consistency.status`, not `this_week.index`. The backend sends index 0 before
  the start and `weeks + 1` after the end.

## Admin preview: `as_of`

`GET /competitions/<id>/leaderboard?as_of=<ISO datetime>` with header `X-Admin-Token` (secret `admin-token`)
computes the board as of that instant. It returns 503 when `ADMIN_TOKEN` is unset, 401 on a wrong token and
400 on an unparseable value. Accepted forms: `2026-11-04T12:00:00-05:00`
(URL-encode the `+` of a positive offset as `%2B`; an unencoded `+` arrives as a space and is restored),
`2026-11-04T17:00:00Z`, and `2026-11-04 12:00:00`. A value without an offset is read as UTC. The frontend
never sends `as_of`.

## Fixtures

`backend/tests/consistency_scenario.py` generates `backend/tests/fixtures/consistency_leaderboard_{sample,
upcoming,ended}.json` through the real payload builder:
`cd backend && PYTHONPATH=. venv/bin/python tests/consistency_scenario.py`. The frontend copies live in
`frontend/src/__fixtures__/consistencyLeaderboard.ts`, and `consistencyFixtures.test.ts` deep-compares them
with the backend JSON (ids and clip URLs excepted). When the payload changes, regenerate the JSON and
update the TS file.

## Limitations

- Squat rep counting uses the engine as deployed (`EXERCISE_CONFIGS["squat"]`). It has never been validated
  on real footage in this app, so squat counts are unverified.
- The bare `/challenges/<id>/upload` page (`UploadVideo.tsx`) still hardcodes its lift list without Plank.
  The 100 Club never links to it: ResultLadder, ChallengeVideos and the home row all link `/challenges/<id>`,
  whose inline upload form lists exactly the four lifts. A typed URL still reaches the old page.
- No reminder emails, no admin UI for `mode`/`rules`.
