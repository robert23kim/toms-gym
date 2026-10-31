# 100 Club round 2: deploy notes (2026-10-31)

I deployed HEAD fa59dae on feat/100-club, which includes the round-2 fixes f5eee14 (backend: NULL auth_method on passwordless register) and d4a81bf (frontend: Consistency pill on the challenges list). I did not commit or stage anything.

## Preconditions
- git log: 9c5def1, bc8665c, fcac5d3, e127f74, f5eee14, d4a81bf and fa59dae are all on feat/100-club.
- git status --porcelain: tracked changes are only ` M .claude/settings.json` and ` M frontend/.env.production`. The 42 untracked paths are the pre-existing ones plus this run's session notes and logs.
- `PYTHON=venv/bin/python tools/run_ci_tests.sh` exited 1 before any test ran. The cause is the known broken local venv: the pytest-cov plugin fails with `ModuleNotFoundError: coverage` (see notes-gate.md and notes-deploy.md). With the documented workaround `PYTEST_ADDOPTS="-p no:cov"`: 367 passed, 8 deselected, exit 0.
- `npx tsc --noEmit` (frontend): exit 0.

## 1. Backend
- `python3 deploy.py --backend-only --skip-iam`: exit 0 in about 4.5 min (log: deploy-backend-2.log).
- Revision went from my-python-backend-00193-dd9 to **my-python-backend-00194-8wr**, with 100% of traffic. That is newer than 00192-rhl.
- `GET /health`: 200 `{"service":"toms-gym-backend","status":"healthy"}`.
- `GET /competitions`: 200, count 7. The 6 legacy challenges are still listed, plus exactly one "The 100 Club" (32ca7bad-...), so there is no duplicate.

## 2. Frontend
- `python3 deploy.py --frontend-only --skip-iam`: exit 0 (log: deploy-frontend-2.log). deploy.py rewrote only VITE_BUILD_TIMESTAMP in the pre-existing dirty frontend/.env.production (1783089945 -> 1793460922). I left it uncommitted.
- Revision went from my-frontend-00196-tt8 to **my-frontend-00197-h8f**, with 100% of traffic. That is newer than 00195-zpg.
- Bundle canary: there is no local `frontend/dist` because the build runs in Cloud Build. A local rebuild would not prove what prod serves, so I took the canary from prod:
  - `GET /`: 200. It references `/assets/index-CrsOZW6E.js`. Round 1's entry was index-B2tHBvTb.js, so the entry has changed and is not stale.
  - The entry JS is 487,698 bytes and references 71 chunks. All 71 fetched with HTTP 200 (0 failures).
  - Only `ChallengeDetail-8Yf8k2Kh.js` contains `consistency-hero`: 46,708 bytes, **1 occurrence**. The fetch canary for that chunk is 14 hits of challenge|leaderboard.
  - The round-2 fix marker: `Challenges-CZrXcHrC.js` (10,687 bytes) contains `"Consistency"` once (fetch canary: 15).
- Not covered: I did not render anything in a browser.

## 3. Production challenge
- I re-checked the existing challenge id 32ca7bad-a970-4a09-acec-02b768793063 and created nothing new.

## 4. Verification (backend 00194-8wr)
- `GET /competitions/<id>`: 200. mode "consistency"; rules have all 8 keys (base_quota 100, ramp 25, weeks 8, quota_bonus 50, type_bonus 25, plank_seconds_per_lift 10, tz America/New_York, week_start 2026-11-02); lifttypes are Situp, Pushup, Squat and Plank; status in_progress.
- `GET /competitions/<id>/leaderboard`: 200. metric "consistency"; consistency.status "upcoming"; week_index 0; weeks_total 8; week 2026-11-02..2026-11-08; type_leaders {}; rows [].
- `?as_of=2026-11-05T12:00:00-05:00` with no header returns 401 `{"error":"Admin token required"}`. A wrong token also returns 401. So ADMIN_TOKEN is set in prod, and the response is not 503. I did not exercise the path with the real token.
- Legacy situp `95b60b42-.../leaderboard`: 200, metric "reps", 1 row (rank 1, 7844e26d-..., 66.5). Compared with legacy-situp-leaderboard-before.json, the metric and rows are identical and no top-level key differs. The baseline has a non-empty row set, so this comparison could have failed.
