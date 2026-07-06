# Lift History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paginated, grade-annotated lift history on the profile Lift tab — per spec `docs/superpowers/specs/2026-07-06-lift-history-design.md`.

**Architecture:** New `GET /users/<id>/lifts` endpoint (SQL in route, row shaping in DB-free `services/lift_history.py`) + `LiftHistoryList` component above the existing gallery on Profile's Lift tab.

**Tech Stack:** Flask/SQLAlchemy text queries (backend), React 18 + TS + jest (frontend).

## Global Constraints

- Grade/hold extraction via JSONB `->>` in SQL — never ship `per_second` on list rows.
- All LiftingResult fields null-safe (LEFT JOIN); endpoint is public read like the profile.
- `limit` default 20 cap 50; response `{lifts, total, limit, offset}`.
- Frontend failure/empty → component renders nothing; gallery unchanged.
- Gates: backend `tools/run_ci_tests.sh` (new DB-free suite registered); frontend targeted jest + `vite build`; final full jest + `tsc --noEmit`; deploy full (`--skip-iam`, backend + frontend); prod verify endpoint + page.

---

### Task 1: `shape_lift_row` + endpoint (TDD on the pure helper)

**Files:**
- Create: `backend/toms_gym/services/lift_history.py`
- Create: `backend/tests/test_lift_history.py`
- Modify: `backend/tools/run_ci_tests.sh` (register suite)
- Modify: `backend/toms_gym/routes/user_routes.py` (endpoint)

**Interfaces:**
- Produces: `shape_lift_row(row: Mapping) -> dict` and route `GET /users/<user_id>/lifts` returning `{lifts: [{attempt_id, competition_id, competition_name, lift_type, weight, created_at, status, analysis_status, grade, total_reps, hold_s}], total, limit, offset}`.

- [ ] Failing tests for `shape_lift_row` (rep-lift row, plank row, no-analysis nulls, string numeric casts, missing keys) → red → implement → green → register in `run_ci_tests.sh` → run suite.
- [ ] Add the endpoint per spec SQL (query + COUNT), clamp limit/offset, rows through `shape_lift_row`.
- [ ] Commit — `feat(profile): paginated lift history endpoint with analysis payoffs`

---

### Task 2: LiftHistoryList component (TDD)

**Files:**
- Create: `frontend/src/components/profile/LiftHistoryList.tsx`
- Test: `frontend/src/components/profile/__tests__/LiftHistoryList.test.tsx`

**Interfaces:**
- Consumes: Task 1 endpoint; Produces `<LiftHistoryList userId />`.

- [ ] Failing tests (grade pill, plank `m:ss` hold, VideoPlayer hrefs, Load-more offset fetch + append, null on error/empty) → red → implement per spec row layout → green + `vite build`.
- [ ] Commit — `feat(profile): lift history list with grades and hold times`

---

### Task 3: Profile wiring + gate + deploy + docs

**Files:**
- Modify: `frontend/src/pages/Profile.tsx` (Lift tab, above gallery)
- Modify: `CLAUDE.md`

- [ ] Wire component into the Lift tab card stack; full gate (`jest`, `vite build`, `tsc --noEmit`, backend CI script).
- [ ] Deploy `python3 deploy.py --skip-iam`; curl the endpoint for a real user; screenshot the profile Lift tab.
- [ ] CLAUDE.md section (including the API table row), mark checkboxes, merge to main, push.
