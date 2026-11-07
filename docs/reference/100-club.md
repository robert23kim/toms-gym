# The 100 Club (consistency challenge, shipped 2026-10-31)

Live challenge: `32ca7bad-a970-4a09-acec-02b768793063` (start 2026-10-31, end 2026-12-27T23:59:59-05:00, week 1 starts Mon 2026-11-02). Branch `feat/100-club`, backend `my-python-backend-00196-mtt`, frontend `my-frontend-00199-qfz` (week-1 fixes, 2026-11-07; shipped at 2026-10-31 as 00194-8wr / 00197-h8f).

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

## API contract

`GET /competitions/<id>/leaderboard` keeps its shape; `metric` is `"consistency"` and the payload gains a `consistency` block (`rules`, `status` upcoming|live|ended, `week_index` 0 before the start and weeks+1 after the end, `weeks_total`, `week_start`, `week_end`, `days_left`, `type_leaders`) and per-row `streak`, `best_streak`, `weeks_met`, `this_week`, `weeks`, `warmup_lifts`. Full field list: the design doc. `GET /competitions/<id>` returns `mode` and `rules`.

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

## Tests and suite counts at ship

- Backend gate `cd backend && PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh`: 367 passed, 8 deselected. The `-p no:cov` is needed because the local venv lacks the `coverage` package (the plain command exits 1 before any test runs). New suites: `tests/test_consistency.py`, `tests/test_register_route.py`, route and champion cases in `test_competition_routes.py` / `test_champions.py`.
- Frontend jest (`--maxWorkers=4`): 101 suites, 696 tests, 0 failed. `npx tsc --noEmit` checks no files (root tsconfig has `"files": []`); `npx tsc --noEmit -p tsconfig.app.json` reports 43 errors, all pre-existing and none in changed files.
- Guards were mutation-checked (see the fixer notes in `docs/sessions/2026-10-31-100-club/`).

## Production verification and cleanup recipe

- Round 2 (backend 00194 / frontend 00197), canary user `hundredclub-canary-2026-10-31@example.com`: `POST /auth/register` without a password returned 201 (round 1 returned 500, fixed in f5eee14); a real upload of `backend/tests/fixtures/test_video_plank_10s.mp4` (Plank, weight 0) analysed to `hold_s` 6.0; four attempts were seeded by SQL (two in week 1, one in week 2, one warm-up) and the board read with `?as_of=2026-11-12T12:00:00-05:00` passed 37 of 37 checks (week 1 = 110 lifts, 200 pts; week 2 live quota 125, 95 lifts; score 295, streak 1, `days_left` 4, `warmup_lifts` 3). A separate read-only refuter hand-checked those numbers against the design.
- Browser (Claude in Chrome, desktop and a 390 px iframe): hero pre-start state, rules line, CTA, `/challenges` "Consistency" pill and the anonymous home row render with 0 console errors.
- Cleanup order, one transaction, `DELETE ... RETURNING id`: AnalysisNotification, ShortLink, LiftingResult, Attempt, UserCompetition, User; then `gsutil rm` the video and the two `lifting/<attempt>/` objects. Connect with `cloud_sql_proxy -instances=toms-gym:us-east1:my-db=tcp:5433` and pg8000 using the `db-password` secret. Round 2 cleanup left 0 rows and 0 objects (re-listed with positive controls).

## Week-1 fixes (2026-11-07)

Bug log: `docs/sessions/2026-11-07-100-club-week1/bugs.md`; run notes in the same folder; session doc `docs/sessions/2026-11-07-100-club-week1.md`.

- B1 fixed (backend half, 5bb001f): Pushup/Situp/Plank store `weight_kg 0` on `/upload`, `/upload/finalize`, `POST`/`PUT /attempts`. Not proven in prod (no upload since deploy). The five existing weight-60 rows stay.
- B2 fixed (7db3ed9): `ConsistencyResult` replaces the rank ladder on the video and status pages.
- B3 fixed (b7b3c68): live-week type leads show as "Situp · locks Sun", hero note says +25 bonuses land Sunday.
- B4 fixed (e5b1c8e): podium tie line names the deciding tiebreak.
- B5 fixed (6710a4b): status pill reads "Ongoing · ends Sun 27 Dec".
- B6 fixed (fb6aafb): `/lift` hub leads with "The 100 Club · Log this week's lifts".
- B7 fixed (b7b3c68): week rows list per-type totals (plank seconds included).
- B8 fixed (855bdcb): no "Everyone else" header on an empty board (all boards).
- B9 fixed (764863a): lift history hides weight for plank, pushup, situp.
- B10 fixed (b7b3c68): hero eyebrow reads "Weekly quota".
- B11, B12 open, see Open follow-ups.

Details:

- Result block (`ConsistencyResult`) replaces the rank ladder on the video and status pages: "+N lifts banked" plus this week's `lifts / quota` and days left. It places the attempt in its own week from `attempt_created_at` (new on `GET /lifting/result/<id>`, read in `rules.tz` like backend `week_of`): an earlier week reads "banked in week K" with no week line, a pre-start upload reads "warm-up lifts · not scored". On someone else's video the week line is prefixed with the athlete's first name.
- Status page headline keeps the raw rep count; a situp with sloppy reps adds "C clean of T · sloppy reps count half" so it reconciles with the half-credit lifts in the block.
- Share text on a club video: "I banked N lifts in The 100 Club — L / Q this week. Join me:" (no rank). `inChallenge` drops the extra "the" for any title starting with "The".
- Podium tie line names the tiebreak (streak, weeks met, this week's lifts, name, as backend `sort_key`). Live-week type leads show as "Situp · locks Sun" in the week table, with a hero note that +25 bonuses land on Sunday.
- Status pill reads "Ongoing · ends Sun 27 Dec" from the challenge's own `mode`/`rules` on first render, not only after the leaderboard loads.
- Bodyweight weight guard: Pushup, Situp and Plank attempts store `weight_kg 0` on every write path (stale APKs posted 60). It is keyed on lift type, not challenge mode, so a bodyweight lift on a weight board would score 0 (no prod board mixes them); Squat is not zeroed. `lift_type` is mapped case-insensitively before the guard.
- `tests/conftest.py` refuses to load unless `DATABASE_URL` is a local Postgres (its `init_db` drops tables and importing the app runs migrations; with `DATABASE_URL` unset that is the Cloud SQL instance in `backend/.env`). Use `tools/run_ci_tests.sh`.

APK: `gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-111511.apk`, short link `https://my-python-backend-quyiiugyoq-ue.a.run.app/s/LSOd2h` (signed URL expires 2026-11-14). Checked by curl and sha256 only; **it still has to be installed on Tom's phone**, which runs the Sep-13 bundle until then (B1 root cause).

## Limitations

- Not covered by the proof: the ring, flame, leader chips, week table and ranked rows were never rendered in a browser against live data (the board was empty during every browser check); the saved-`userId` home pill; the upload page lift list and Squat weight 0 in a browser; behaviour after Mon 2 Nov (live state); ties, a second athlete, tiebreaks and the reset after a miss in prod (unit tests only); Pushup and Squat lifts; situp half-credit used seeded `rep_metrics`, not an engine report. The `as_of` call with the real token ran in round 2 only.
- Cleanup was confirmed in the DB by SQL in the prover's run; the round 2 refuter could not start the SQL proxy (blocked) and confirmed through API 404s and GCS listings only.
- An analysis-ready email was sent to the example.com canary address in both rounds (round 1 bounced).

- Squat rep counting uses the engine as deployed (`EXERCISE_CONFIGS["squat"]`). It has never been validated
  on real footage in this app, so squat counts are unverified.
- The bare `/challenges/<id>/upload` page (`UploadVideo.tsx`) still hardcodes its lift list without Plank.
  The 100 Club never links to it: ResultLadder, ChallengeVideos and the home row all link `/challenges/<id>`,
  whose inline upload form lists exactly the four lifts. A typed URL still reaches the old page.
- No reminder emails, no admin UI for `mode`/`rules`.

## Open follow-ups

- B1b unproven in prod: after the next real bodyweight upload read the `weight_kg=` log line (gcloud logging command in `docs/sessions/2026-11-07-100-club-week1/notes-fix-2.md`).
- B1 data: five existing weight-60 rows left alone on purpose.
- B11: two unexplained 404s on `GET /lifting/result/5a0d00a7-...` (4 Nov), not chased.
- B12 / QA-5 (Tom): type bonus has no minimum (see above).
- R6: weight guard keys on lift type; a bodyweight lift on a weight board would score 0 (no such board).
- R7: partial `PUT /attempts` may fail on `lift_type` NOT NULL; live constraint not read, no client sends one.
- R8 (Tom): are club squats always bodyweight? Only symptom is the profile label.
- Decision needed (Tom): type bonus has no minimum amount (QA-5), so a 9.9 s plank earns +25 when nobody else planks (B12).
- Pre-existing: `upload_routes.py`, `golf_routes.py` and `email_upload.py` create guest users with `auth_method 'password'` and no hash, so the magic-link route issues them a JWT.
- Pre-existing: `GET /attempts/<id>` returns 500 for an existing attempt.
- Multi-category legacy challenges still show only their first lift on `/challenges`; the BottomTabBar covers the sticky CTA on phones.
- Local backend venv is missing `coverage`; `deploy.py` leaves `frontend/.env.production` dirty (build timestamp).
