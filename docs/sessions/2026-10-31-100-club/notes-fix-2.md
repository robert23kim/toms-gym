# 100 Club fixer round 2 (2026-10-31)

Scope: the two distinct problems from notes-prove.md (D1 was listed twice with the same id; treated once).
Nothing had side "data", so nothing is deferred. **Verified by local tests only. Not redeployed or re-proven in prod;
that is the next phase.**

## D1: passwordless POST /auth/register returns 500 (pre-existing, not 100 Club code) -> fixed, f5eee14
- Cause: `backend/toms_gym/routes/auth_routes.py` register wrote `auth_method = 'passwordless'` when no password was given.
  The enum is `{google, password}` (`migrations/schema.sql:15`, matches prod `enum_range`), so pg8000 raised 22P02 -> 500.
- Fix: write `None` (NULL) instead. Same as the existing bowling-sheet guest path (`bowling_sheet_routes.py:292`).
  The column is nullable (`schema.sql:27`, no NOT NULL; the bowling-sheet path already inserts NULL in prod). Chose NULL
  over `'password'` (what `upload_routes`/`golf_routes` guests write) because `/auth/magic/<token>` issues a JWT only
  for `auth_method in ('password','google')`, so NULL keeps a passwordless user on the no-JWT branch. Chose it over
  `ALTER TYPE ... ADD VALUE` because that is a schema change the codebase already avoids. The SecurityAudit detail
  string still says 'passwordless' (log label, not the column).
- Test: new DB-free `backend/tests/test_register_route.py` (3 tests, mocked session, captures the INSERT params),
  registered in `backend/tools/run_ci_tests.sh`.
  - Reproduced before the fix: `2 failed, 1 passed` (`assert ('passwordless' is None or 'passwordless' in {'google','password'})`).
    That pre-fix run is the mutation check: the guard has been observed to fail on the exact prod bug.
  - After: 3 passed.
- Not covered: no live Postgres insert was run here (the enum rejection is proven only by the prod log in notes-prove.md
  plus the schema). A prod re-run of `POST /auth/register {email, name}` should now return 201.

## F1: /challenges pill shows "Situp" for The 100 Club -> fixed, d4a81bf
- Cause: `frontend/src/pages/Challenges.tsx` rendered `pill={c.categories?.[0]}` in both "Open now" and "All challenges".
- Fix: `Challenge` type gains `mode?: string`; the list map keeps `transformCompetitionData(...).mode`; a `challengePill`
  helper returns "Consistency" when `mode === "consistency"`, else `categories[0]` (legacy challenges unchanged).
- Test: new `frontend/src/pages/__tests__/Challenges.test.tsx`, fed the prod `/competitions` description string
  (metadata parse path) plus the legacy "Biceps and Bench" row. Asserts both 100 Club rows say "Consistency" and not
  "Situp", and Biceps and Bench still shows "Bench Press".
  - Mutation: reverted the helper to `c.categories?.[0]` (re-read the file to confirm), the test failed with
    `Received: The 100 ClubSitupOpen` (the prod text), restored from an in-memory copy and re-read.
- Not covered: no browser check of the live page (not redeployed).

## Gates
- Backend: `cd backend && PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh` -> exit 0,
  `367 passed, 8 deselected` (was 364; +3 new).
- Frontend: `npx tsc --noEmit` exit 0 (checks no files: root tsconfig has `"files": []`, per notes-fix.md).
  `npx tsc --noEmit -p tsconfig.app.json` -> 43 errors, same count as notes-fix.md, none in Challenges.tsx or types.ts.
- jest `--maxWorkers=4` -> `jest-fix2.json`: 696 tests, 696 passed, 0 failed, 101 suites, 0 failed; Challenges.test.tsx present.

## Follow-ups (not acted on)
- `upload_routes.py:59,231`, `golf_routes.py:868` and `email_upload.py:469` create email-only guest users with
  `auth_method 'password'` and no password hash, so the magic-link consume route issues those guests a JWT. Unrelated to
  this fix; worth a separate look.
- Multi-category legacy challenges ("Biceps and Bench") still show only their first lift type on /challenges.
