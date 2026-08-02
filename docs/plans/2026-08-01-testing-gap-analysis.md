# Testing Gap Analysis — 2026-08-01

Survey of every test asset in the repo: what provides real signal, what is dead weight, and where the gaps are. Backend gate verified by running it (172 passed, 5s); frontend suite verified (57 suites / 388 tests, all passing, 26.15% statement coverage); last 8 GitHub Actions runs all green.

## TL;DR

CI exists and is green (`.github/workflows/ci-cd.yml`: backend DB-free gate + frontend jest + build, on push/PR to main) — the "broken CI" finding from the July strategic review is stale. But the picture has three structural problems:

1. **CI does not gate deploys.** `deploy.py` (the documented ship path) and `frontend/cloudbuild.yaml` run zero tests. A red CI does not block `python3 deploy.py`.
2. **About half the backend tests never run anywhere.** 13 of 27 backend suites (~87 tests — all auth, tickets, bowling annotations, user/attempt routes) need a real Postgres nobody starts. Three e2e harnesses (Playwright, Python prod-e2e, Puppeteer mobile) are all dead.
3. **The riskiest surfaces are the least tested**: the production signed-URL upload path, the backend↔analysis-engine report contract, golf route wiring, and the app's largest frontend pages (ChallengeDetail, VideoPlayer, GolfReview — all 0%).

---

## 1. What is useful (keep, protect)

### Backend — the DB-free gate (172 tests, 5s)
The gated pure/mocked suites are the best tests in the repo: fixture-driven, fast, assert real values.

- `test_handicap.py` (20) — WHS engine vs `whs_reference_cases.json`; every adjustment-table row, NDB cap, 12-month cap, 9-hole weighting. The contract fixture for any handicap change.
- `test_scorecard_grid.py` (11) — grid parser end-to-end against 3 real scorecard photos + human ground truth.
- `test_challenge_leaderboard.py` (22), `test_guest_round_classify.py` (7) — ranking logic incl. the −42.0 nine-hole regression.
- `test_golf_parser.py` (7 pure of 11), `test_competition_routes.py` (15 of 19), `test_magic_link.py` (16 — pins the no-enumeration guarantee), `test_analysis_notify.py` (10 — idempotency + SMTP-failure isolation), `test_achievements.py` (14), `test_og_card.py` (9), `test_lift_history.py` (7), `test_champions.py` (4), `test_lifting_processor_mapping.py` (4).

### Frontend — pure libs and challenge components
- 14 pure lib suites (~160 tests): `plankStats` (31, 99% cov), `bowlingStats` (20, 96%), `liftCoaching` (17, 100%), `setSummary`, `standing`, `uploadJourney`, etc. Fixture-driven, threshold-pinned.
- 5 hook suites (41 tests) for the annotation workspace (`useEdgeEditor`, `useAnnotation`, …).
- Challenge components are well covered (LeaderboardRow 88%, Podium 100%, AttemptHistory 98%).
- Quality is genuinely good: zero snapshot tests, only 8 weak assertions in 388, disciplined per-test API mocking. The `TZ=America/Los_Angeles` jest pin + TrophyCase date test is a proper regression guard for the UTC date bug.

### Tooling
- `run_ci_tests.sh` — the gate itself.
- `grid_debug.py` + `scorecards/` fixtures — live debug harness for the grid parser.
- `ocr_inspect3.py` — documented, works with Vision creds.

## 2. What is not useful (dead weight / negative value)

| Asset | Problem | Action |
|---|---|---|
| `frontend/e2e/` — 72 Playwright tests, 6 specs | No npm script, no CI job, default baseURL is **production**, last touched 2026-03-04. `user-workflows.spec.ts:392` still visits the deleted `/athletes` route, so the suite fails today. | Revive against a local/staging target or delete. Currently pure maintenance debt. |
| `tests/e2e/` — Python prod e2e (16 tests) + `run-production-e2e.sh` | Runs against **live production**, creating real users/competitions. Its `e2e-test-*` prefix is NOT matched by the `is_test` backfill patterns (`e2e-lift-%`, `*.local`) — running it pollutes prod leaderboards with users no filter catches. Last touched 2026-01-31, still posts `Snatch/Clean` and 2025 dates. | Do not run as-is. Either retarget + add its prefix to `is_test` patterns, or delete. |
| `tests/*.js` Puppeteer mobile suite, `run-mobile-tests.sh`, `android-test.sh` | Dead ~16 months; runner uses `md5sum` (absent on macOS). | Delete. |
| `Makefile` test targets | All three broken (`test-backend` pulls the live-DB conftest; `test-frontend` calls a nonexistent `lint` script; `test-mobile` → md5sum). | Fix to call `run_ci_tests.sh` / `npm test`, or delete. |
| `frontend/src/App.js`, `src/index.js` | Stale CRA duplicates; babel throws a full SyntaxError stack on **every** jest run (doesn't fail, just trains people to ignore stack traces). | Delete both. |
| `tools/ocr_inspect.py`, `ocr_inspect2.py`, `debug_parser.py` | Superseded by `ocr_inspect3.py` / the grid parser. | Delete or move to an attic. |
| `tools/run_golf_parser_tests.py` | Duplicates the pure half of `test_golf_parser.py` (now gated) — two copies to keep in sync. Sole user of the `golf_sagamore_ocr.json` fixture. | Fold the sagamore case into pytest, delete the runner. |
| `test_upload_routes.py::test_upload_video` | Mocks GCS **and** the DB, then asserts on the mocks — verifies the route calls its dependencies, not that upload works. (The 4 validation tests in the file are fine.) | Keep but don't trust; real coverage belongs to the signed-URL path (gap #3). |
| `lib/__tests__/api.test.ts` | Not a runtime test — compile-time type assertions with `expect(true).toBe(true)` bodies. The central HTTP layer has no behavioral tests. | Replace with real tests (gap list). |
| Untracked junk | `backend/=3.5.0` (zsh redirect artifact from an unquoted `pip install x >=3.5.0`), `backend/tools/grid_debug_out/` (~5 MB regenerable), `backend/tests/fixtures/test_video_plank_10s.mp4` (6.5 MB, referenced by zero tests). | Delete the first; gitignore the other two. ~91 MB of loose video also sits in root `tests/fixtures/`, mostly tracked. |
| Legacy stray frontend tests | `src/test-password.test.ts` ≈ duplicates `CreateProfilePassword.test.tsx`. | Consolidate into `__tests__/`. |

## 3. Gaps (ranked)

### P0 — structural

**G1. No test gate on deploy.** `deploy.py` runs nothing; `cloudbuild.yaml` is build-only. Cheapest fix: `deploy.py` shells `backend/tools/run_ci_tests.sh` and `cd frontend && npm test` before building, with a `--skip-tests` escape hatch.

**G2. `conftest.py` is dangerous and stale.**
- The autouse session fixture `init_db` executes `DROP TABLE … CASCADE` against whatever `DATABASE_URL` points to — the script's own comment says it connects to real Cloud SQL. A bare `pytest` in `backend/` with prod credentials in env would destroy production data. Add a hard guard (refuse unless the URL matches a known test host/port, or require `TOMS_GYM_TEST_DB=1`).
- The test schema applies only migrations 008 and 012. Migrations 004–007, 009–011, 013–016 never apply: no `LiftingResult`, `BowlingResult`, `ShortLink`, `MagicLinkToken`, `AnalysisNotification`, no `is_test`/`avatar` columns, and a `lift_type` enum without Plank/Pushup/Bowling. **New DB-backed tests for champions, achievements, pushups, or is_test filtering cannot be written until this is fixed.** Point it at the real migration chain instead of hand-written DDL.
- `db_session` deliberately never rolls back ("REMOVED AS REQUESTED") → order-dependent tests compensating with `DELETE FROM` preambles.
- Minor: `test_auth_user_data` defined twice (second shadows first); autouse fixture shells `docker ps` every run.

**G3. ~87 DB-bound backend tests never execute** — auth (9), tickets (16), bowling annotations (25+9+5), courses (7), user/attempt/upload-integration, sweep-stuck. `docker-compose.test.yml` exists but is referenced by nothing. Fix: a CI job with a Postgres service container running the DB suite (after G2's schema fix), or at minimum a documented `make test-db` that starts the container.

**G4. Backend↔engine report contract is unguarded.** Backend and frontend consume raw JSONB keys from engine reports — `body_line_stdev_deg`, `total_reps`, `overall_grade`, `per_second[]`, `pose_detection_rate`, `detection_rate` (`competition_routes.py:414`, `user_routes.py:128`, `services/lift_history.py:41`, plus frontend). The only cross-repo pin is the 4-test lift-type name mapping. If the engine renames a key, every consumer degrades to null/"—" silently and no test in either repo fails. Sharper because the engine's pushup config lives on the unmerged `feat/pushup-config` branch. Fix: capture one real report per lift family (plank, rep-lift, pushup, bowling) as fixtures and assert the keys both repos read exist with sane types — a poor-man's contract test.

### P1 — high-value additions

**G5. Smoke-render tests for the six large 0% pages** — `ChallengeDetail` (340 stmts), `pages/VideoPlayer` (236), `GolfReview` (205), `BowlingResult`, `Profile`, `UploadVideo`. This is the only automated defense against the scope-bug class that shipped `metric is not defined` to prod (invisible to tsc and jest today; CLAUDE.md's "verify in a browser" is the current mitigation). One render with mocked API data per page.

**G6. Production upload path untested.** The signed-URL family (`/upload/signed-url`, `/upload/resumable-url`, `/upload/finalize`, `/upload/composite/*`) — the actual post-32MiB-fix flow — has zero tests; only the legacy multipart `/upload` is tested, against mocks. Frontend mirror: `lib/resumableUpload.ts` (106 stmts) and `lib/videoCompress.ts` (13% — the iOS-OOM-implicated code) untested.

**G7. Golf route wiring untested in CI.** Pure engine coverage is excellent, but `PUT /round/<id>/scores` (differential + snapshot write), `DELETE /round/<id>`, `/golf/leaderboard` (incl. the load-bearing stale-snapshot `DISTINCT ON` inversion), and `/handicap/<id>/recompute` have no gated tests; the 4 golf-upload integration tests are deselected.

**G8. Route/wiring coverage holes elsewhere (zero tests):** `bowling_routes` core endpoints (upload/result/reanalyze), `lifting_routes` (both endpoints), `achievement_routes` (incl. the uncached per-ended-challenge championship scan), `weekly_lifts_routes`, `admin_routes` (cleanup/migrate), `integrations/email_upload.py` (37.8 KB, largest untested module), frontend `routes/index.tsx` (no routing test at all), `AuthContext` (61% only incidentally, no dedicated suite).

### P2 — cheap wins and hygiene

**G9. 18 already-passing DB-free tests missing from the gate**: `tests/unit/` (9 — the Cloud Tasks/jobs dispatch path, i.e. the *current production analysis architecture*), `test_telemetry_routes.py` (5), `test_upload_routes.py` (4). One-line-each addition to `run_ci_tests.sh`. Cheapest fix in this document.

**G10. 8 deselected assertions in the gate** (4 golf-upload, 4 competition CRUD) — silently skipped real tests; revisit after G2/G3.

**G11. No `coverageThreshold` in jest.config.js** — coverage is collected every run but can regress from 26% to 0 without failing anything. Set a floor at current levels.

**G12. Remaining bare-ISO `new Date()` sites** — the UTC day-shift bug class is fixed at 2 sites but live at 6: `AttemptHistory.tsx:40`, `LiftHistoryList.tsx:39`, `TicketList.tsx:29`, `Profile.tsx:153`, `VideoGallery.tsx:222`, `lib/utils.ts:10`. AttemptHistory/LiftHistoryList have tests, so add date-only-string cases there.

**G13. Fixture-models-the-SQL brittleness** — `_prow` / `_make_session` in `test_competition_routes.py` dispatch on SQL substrings and model result columns; adding a column broke 5 tests once (documented), and rewording a query can silently make a test pass against a query that no longer exists. Acceptable, but a captured-fixture or service-layer refactor would remove the trap.

**G14. Python version drift** — local backend venv is 3.13, CI and the Dockerfile pin 3.10 (SQLAlchemy 2.0.25 breaks on newer). Local green ≠ deployed-interpreter green.

## 4. Suggested order of attack

1. G9 (minutes) + G11 + delete App.js/index.js + `backend/=3.5.0` — same-day hygiene.
2. G1 — wire tests into `deploy.py`.
3. G2 — conftest safety guard first (it's a data-loss hazard), then the migration-chain schema fix.
4. G5 — smoke-render the six big pages (ChallengeDetail first).
5. G4 — engine report contract fixtures (before the next engine deploy, given the unmerged pushup branch).
6. G3 — Postgres service container in CI; then un-deselect G10.
7. G6/G7/G8 route coverage, then decide the fate of the three dead e2e harnesses (§2).
