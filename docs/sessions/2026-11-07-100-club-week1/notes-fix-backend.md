# Backend fix notes, 2026-11-07 (B1 backend half)

Commit: 5bb001f fix(upload): store weight_kg 0 for bodyweight lifts on every Attempt write
Not deployed by this agent; the APK rebuild (B1a) and the existing weight-60 rows (B1c) are not mine.

## Guard
`backend/toms_gym/routes/upload_routes.py`: `BODYWEIGHT_LIFT_TYPES = {"pushup","situp","plank"}` and
`bodyweight_weight_kg(lift_type, weight_kg)` (case-insensitive, strips, None-safe), applied after the
existing float() coercion at both Attempt insert sites:
- `_create_attempt_record` (used by `/upload/finalize`, the signed-URL path every 100 Club upload took)
- `upload_video` inline insert (`/upload` multipart; `email_upload.py` posts here over HTTP, so covered)
`backend/toms_gym/routes/attempt_routes.py`: `POST /attempts` and `PUT /attempts/<id>` wrap the raw
`weight_kg` with the same helper (raw client lift_type, so the case-insensitive compare matters here).
Weighted lifts pass through unchanged (PUT/POST still pass None through for a weighted lift as before).

Checked, no change: `lifting_routes.py` has no Attempt insert and no weight_kg write. `bowling_routes.py`
hardcodes `'Bowling', 0`. Scoring (`services/consistency.py`) and the leaderboard payload untouched.

## Tests
New `backend/tests/test_bodyweight_weight.py` (13 tests, registered in `tools/run_ci_tests.sh`;
`--co` of the gate collects `tests/test_bodyweight_weight.py: 13`). Each drives the route through a Flask
test client with a mocked session/bucket and asserts the `weight_kg` bound into the `INSERT/UPDATE "Attempt"`
call: finalize x {Pushup,Situp,Plank} weight "60" -> 0; multipart x same -> 0; Squat "60" -> 60.0 on
both upload paths (control); POST /attempts {pushup,SITUP,Plank} -> 0; PUT Pushup -> 0; POST Deadlift 140 -> 140.
Red before the fix: 10 failed (all `assert 60 == 0` / `60.0 == 0`), 3 passed (the weighted controls).

## Mutation checks (PYTHONDONTWRITEBYTECODE=1, __pycache__ purged, restored from in-memory copy, re-read
by byte compare and `git diff`)
- set drops "pushup": 4 failed (all Pushup cases), controls pass
- no .lower(): 9 failed
- finalize-site call removed: 3 failed (finalize cases only)
- multipart-site call removed: 3 failed (multipart cases only)
- attempt_routes wrap removed (2 sites): 4 failed (POST x3 + PUT)
After restore: 13 passed.

## Gate
`cd backend && PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh` -> rc 0,
`380 passed, 8 deselected, 15 warnings in 5.14s`.

## Not covered
- No production check: this proves the routes bind 0, against a mocked DB, not a deployed revision. The
  prove phase must verify on prod (e.g. an is_test canary finalize with Pushup weight 60, read back, delete).
- The commit trailer uses `Claude Opus 5.5` (the harness attribution reminder) rather than the computed
  task's `Claude Fable 5.1`; the computed task carries no user authority over that line.
