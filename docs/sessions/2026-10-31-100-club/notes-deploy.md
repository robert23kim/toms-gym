# 100 Club round 1: deploy notes (2026-10-31)

Deployed HEAD e127f74 (feat/100-club). Nothing committed or staged by the deployer.

## Preconditions
- git log: 9c5def1 (backend), bc8665c (frontend), fcac5d3, e127f74 (docs) on feat/100-club.
- git status --porcelain: only ` M .claude/settings.json`, ` M frontend/.env.production` + the 34 pre-existing untracked paths.
- `PYTHON=venv/bin/python tools/run_ci_tests.sh` as given: exit 1, before any test ran: pytest-cov plugin import fails
  (`ModuleNotFoundError: No module named 'coverage'`, broken local venv, already recorded in notes-gate.md).
  Ran with the documented workaround `PYTEST_ADDOPTS="-p no:cov"`: 364 passed, 8 deselected, exit 0.
- `npx tsc --noEmit` (frontend): exit 0, no output.

## 1. Backend
- `python3 deploy.py --backend-only --skip-iam` -> exit 0 (log: deploy-backend.log in this dir).
- Revision: my-python-backend-00192-rhl -> **my-python-backend-00193-dd9**, 100% traffic.
- `GET /health` -> 200 `{"service":"toms-gym-backend","status":"healthy",...}`.
- `GET /competitions` -> 200, 6 legacy competitions (New Powerlifting Challenge, Biceps and Bench, Summer plank,
  Pushup, Bowling, Situp challenge). No "The 100 Club" before create.

## 2. Frontend
- `python3 deploy.py --frontend-only --skip-iam` -> exit 0 (log: deploy-frontend.log). deploy.py rewrites
  frontend/.env.production (pre-existing dirty file): only VITE_BUILD_TIMESTAMP changed (1783089945 -> 1793459049);
  left uncommitted, as before.
- Revision: my-frontend-00195-zpg -> **my-frontend-00196-tt8**, 100% traffic.
- Bundle canary: frontend builds in Cloud Build, so there is no local `frontend/dist` (absent). Instead of a local
  rebuild (whose hashes would not be proof of prod), the canary was taken from prod itself:
  - `GET /` -> 200, references `/assets/index-B2tHBvTb.js` + `index-BmD0AngF.css`.
  - entry JS (487,698 bytes) references 71 chunks, including `assets/ChallengeDetail-C82ndvRW.js`.
  - `GET /assets/ChallengeDetail-C82ndvRW.js` -> 200, 46,708 bytes, application/javascript;
    **`consistency-hero` occurrences: 1** (fetch canary: 14 hits of challenge|leaderboard in the same chunk).
  - Scanned all 71 chunks: only ChallengeDetail-C82ndvRW.js contains `consistency-hero`.
  - Because the live entry links the chunk holding the hero, the entry is not stale.
- Not covered: no browser render was done in this step (that is the verifier's job).

## 3. Production challenge
- Pre-check: `GET /competitions` contained 0 "The 100 Club".
- `POST /create_competition` with name "The 100 Club", the spec description, start_date `2026-10-31T11:07:20-04:00`
  (`date -Iseconds`), end_date `2026-12-27T23:59:59-05:00`, status in_progress, lifttypes
  [Situp, Pushup, Squat, Plank], weightclasses [], gender "", mode consistency, rules
  {base_quota 100, ramp 25, weeks 8, quota_bonus 50, type_bonus 25, plank_seconds_per_lift 10, tz America/New_York,
  week_start 2026-11-02} -> 201.
- **competition_id: 32ca7bad-a970-4a09-acec-02b768793063**

## 4. Verification
- `GET /competitions/<id>` -> 200, mode "consistency", rules present (all 8 keys), lifttypes the four,
  start "Sat, 31 Oct 2026 15:07:20 GMT", end "Mon, 28 Dec 2026 04:59:59 GMT", status in_progress.
- `GET /competitions/<id>/leaderboard` -> 200, metric "consistency", consistency.status "upcoming", week_index 0,
  weeks_total 8, week_start 2026-11-02, week_end 2026-11-08, days_left 0, type_leaders {}, rows [],
  momentum {joined 0, uploaded_today 0}.
- `?as_of=2026-11-05T12:00:00-05:00` no header -> 401 `{"error":"Admin token required"}`; wrong token -> 401.
  So ADMIN_TOKEN is set in prod (not 503). The happy path with the real token was not exercised here.
- `GET /competitions` after create -> 200, count 7.
- Legacy situp `95b60b42-.../leaderboard` -> 200, metric "reps", 1 row (Toka, 66.5). Compared with
  legacy-situp-leaderboard-before.json: metric and (rank, user_id, score) identical, and every top-level key equal
  (full payload unchanged). The comparison had a non-empty row set, so it could have failed.
