# Fairway Phase B — Correctness + Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-plumb Phase A's review page onto a proper Course/Tee/Round/HoleScore/HandicapSnapshot data model and a correct WHS handicap engine. Phase A's visuals and CSS classes stay intact — this phase changes data, not pixels.

**Architecture:**
- **Backend:** new migration `008_fairway_schema.sql` (drop + recreate golf tables + `pg_trgm`); two new services under `backend/toms_gym/services/` (`handicap.py` pure-function WHS engine, `courses.py` pg_trgm + geo-biased matcher with tee match/create); `golf_routes.py` delegates to these services and returns nested `course` / `tee` objects; three new endpoints (`GET/POST /golf/courses`, `GET /golf/users/:id/handicap/history`).
- **Frontend:** typed wire shapes in `lib/api.ts`; `GolfReview`, `GolfRound`, `GolfProfile`, `GolfLeaderboard` read nested `course` / `tee` instead of flat fields; new `TeePickerDrawer` + `DifficultyMeter` components; `fw-selected` (2px info border from Phase A) marks the selected tee; live differential preview.
- **Testing:** `test_handicap.py` unit-tests every WHS adjustment-table row + NDB cap + 12-month cap + 9-hole weight against a JSON fixture; `test_golf_parser.py` gains course/tee matching integration cases; `golf-fairway-phase-b.spec.ts` covers the tee-picker drawer and live differential; Phase A's `golf-fairway-phase-a.spec.ts` is re-run unchanged as a regression gate.

**Tech Stack:** Python 3.12 + Flask + psycopg2 (backend); PostgreSQL with `pg_trgm` + GIN trigram index; React 18 + TypeScript + Vite; Playwright 1.58. Targets the deployed prod backend after deploy.

**Spec reference:** `docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md` §Phase B.

**Handoff reference:** `docs/superpowers/handoffs/2026-04-18-fairway-phase-a-to-b.md` (caveats: rate-limited `/golf/upload`, greenfield schema OK, inline `CREATE TABLE` block at `app.py:117-194` must be removed).

**Next phase:** after merge, write `docs/superpowers/plans/YYYY-MM-DD-fairway-phase-d.md` (dashboard landing page, handicap trend chart).

---

## Team task mapping

Plan tasks map one-to-one to tracked team tasks:

| Plan Task | Tracked Task | Wave | Owner persona |
|-----------|--------------|------|---------------|
| Task 0 + Task 1 (B1) | #10 | P1 | doer-schema |
| Task 2 (B2) | #11 | P1 | doer-handicap |
| Task 3 (B3) | #12 | P2 | doer-schema |
| Task 4 (B5) | #13 | P2 | doer-handicap |
| Task 5 | #14 | P2 | doer-schema |
| Task 6 (B6) | #15 | P3 | doer-frontend |
| Task 7 (B4) | #16 | P3 | doer-frontend |
| Task 8 (B7) | #17 | P3 | doer-frontend |
| Task 9 | #20 | P4 | doer-schema |
| QA gates | #3 baseline, #8 migration safety, #4 Phase A regression, #5 bowling/lifting untouched, #6 handicap edges, #7 OCR regression, #18 pre-deploy sweep | — | qa |
| Reviewer gate | #19 | — | reviewer |

---

## Parallelization map

**Wave P1 (sequential):** Task 0 → Task 1 (migration 008) → Task 2 (handicap engine unit tests can run against the new schema but only touch pure functions; safe to start once Task 1's SQL is committed).

**Wave P2 (parallel, two doers):** Task 3 (`courses.py`) ‖ Task 4 (`golf_routes.py` rewrite). **Sequencing within P2:** Task 4 depends on Task 3's module signature, not its body — Task 3 owner must push `services/courses.py` with **finalized function signatures + docstrings + `NotImplementedError`** and the **test file `test_courses.py` with red tests** before Task 4 starts importing it. Task 5 (extend `test_golf_parser.py`) runs after Task 4 because the integration tests exercise the rewritten upload route.

**Wave P3 (partially parallel):**
- Task 6 (types + read-only pages) must land first — it edits `lib/api.ts` types and the read-only pages.
- Task 7 (TeePickerDrawer + GolfReview wiring) and Task 8 (Playwright e2e) run in parallel **after** Task 6 merges, because Task 7 edits `GolfReview.tsx` and Task 8 creates a brand-new spec file (`golf-fairway-phase-b.spec.ts`) — no shared files.

**Wave P4 (alone):** Task 9 (deploy + smoke + PR + handoff) — no code changes, runs after all QA + reviewer gates pass.

### Shared-file hot spots (serialize)

| File | Tasks that touch it | Serialization rule |
|------|---------------------|-------------------|
| `backend/toms_gym/routes/golf_routes.py` | Task 4 (rewrite), Task 5 (integration tests read it) | Task 4 completes before Task 5 runs. |
| `backend/toms_gym/app.py` | Task 1 only (remove inline `CREATE TABLE` at 117–194) | Single owner. |
| `frontend/src/lib/api.ts` | Task 6 only | Single owner; Task 7 reads the types. |
| `frontend/src/pages/GolfReview.tsx` | Task 6 (data swap), Task 7 (drawer wiring) | Task 6 before Task 7; Task 7 owner rebases on Task 6's merge commit. |
| `frontend/e2e/golf-fairway-phase-b.spec.ts` | Task 8 only (new file) | Single owner. |
| `frontend/e2e/golf-fairway-phase-a.spec.ts` | Task 8 re-runs it unchanged | Read-only for Task 8. |

---

## File structure

**Create:**
- `backend/toms_gym/migrations/008_fairway_schema.sql` — drop old golf tables, `CREATE EXTENSION pg_trgm`, create `Course`/`Tee`/`Round`/`HoleScore`/`HandicapSnapshot`, GIN trigram index on `Course.name`. **Already present in-flight (101 lines on `golf/fairway-phase-b`); Task 1 verifies + applies, does not re-author.**
- `backend/toms_gym/services/handicap.py` — pure functions: `net_double_bogey`, `compute_differential`, `compute_handicap_index`, `twelve_month_cap`, `allocate_strokes`, `nine_hole_weighting`.
- `backend/toms_gym/services/courses.py` — `match_or_create_course`, `match_or_create_tee`, `search_courses(q, near)`.
- `backend/tests/fixtures/whs_reference_cases.json` — deterministic WHS reference cases (one per adjustment-table row + establishing + 12-month cap + 9-hole). **Already present in-flight (120 lines); Task 2 extends if gaps surface.**
- `backend/tests/test_handicap.py` — unit tests against the fixture. **Already present in-flight (216 lines, ~13 tests); Task 2 finishes the red-test set + implements green.**
- `backend/tests/test_courses.py` — unit + integration tests for `courses.py` (fuzzy match hit, miss → pending, geo-bias tie-break, tee match/create).
- `frontend/src/components/golf/TeePickerDrawer.tsx` — modal drawer with up to 4 tee cards, editable rating/slope/yardage, `fw-selected` border on active, live differential preview.
- `frontend/src/components/golf/DifficultyMeter.tsx` — horizontal meter anchored at slope 113, labels at 100/113/130/145.
- `frontend/e2e/golf-fairway-phase-b.spec.ts` — new Playwright spec for tee-picker drawer + live differential update + handicap-history endpoint.

**Modify:**
- `backend/toms_gym/app.py` — remove inline `CREATE TABLE IF NOT EXISTS` for `GolfRound` / `GolfHoleScore` / `GolfHandicap` at lines 117–194. Replace with a comment pointing at migration 008. **Already in-flight (80+ lines removed); Task 1 verifies.**
- `backend/toms_gym/routes/golf_routes.py` — rewrite `_recalculate_handicap` to call `services.handicap`, update `upload_scorecard` to call `services.courses.match_or_create_course` + `match_or_create_tee`, change response shapes to nested `course` / `tee`, add three new endpoints (`GET /golf/courses`, `POST /golf/courses`, `GET /golf/users/:id/handicap/history`). Persist `HandicapSnapshot` rows on save / edit / delete.
- `backend/tests/test_golf_parser.py` — add course/tee matching integration cases (seeded Course/Tee → upload returns matching IDs; unknown course → `status='pending'` row created).
- `backend/tests/conftest.py` / `backend/tests/init_db.py` — apply migration 008 in test DB setup. **Already in-flight; Task 1 verifies.**
- `frontend/src/lib/api.ts` — add `Course`, `Tee`, `Round` (nested), `HandicapSnapshot`, `HandicapHistoryPoint` types; update `GolfRound` / `GolfRoundWithHoles` response types; add `searchCourses`, `getHandicapHistory` client functions.
- `frontend/src/pages/GolfReview.tsx` — read `round.course.name` / `round.tee.rating_18` / `round.tee.slope_18` (flat keys become nested); wire "Change" link → `TeePickerDrawer`; surface tee-entry form when `round.needs_tee`.
- `frontend/src/pages/GolfRound.tsx` — read nested `course` / `tee` for header + differential card.
- `frontend/src/pages/GolfProfile.tsx` — read nested `course` in the round list; optionally display handicap-history sparkline fed by `GET /golf/users/:id/handicap/history`.
- `frontend/src/pages/GolfLeaderboard.tsx` — read `latest_snapshot.handicap_index` instead of `handicap.handicap_index`.

**No changes:**
- Phase A visual components (`StagedParseProgress`, `HighlightsGrid`, `HoleBarChart`, `ReviewBanner`, `FairwayScope`, `fairway.css`).
- Lifting and bowling routes, pages, tests.
- `frontend/e2e/golf-fairway-phase-a.spec.ts` (re-run unchanged).
- `frontend/e2e/bowling-lifecycle.spec.ts`, `lane-edge-editor.spec.ts`, `annotation-workspace.spec.ts`, `user-workflows.spec.ts`.

---

## Task 0: Branch setup

**Files:** none (git only).
**Tracked task:** #10 (combined with Task 1).

- [ ] **Step 1: Verify you are on the phase branch**

```bash
git checkout golf/fairway-phase-b
git status
```
Expected: branch `golf/fairway-phase-b`, modified files limited to migration 008 scaffolding from in-flight work.

- [ ] **Step 2: Rebase on `main` if Phase A has merged**

```bash
git fetch origin
git rebase origin/main
```
If Phase A has not yet merged, stay on the `golf/fairway-phase-a`-based branch — Phase A's CSS / components are dependencies. Document this in the PR description.

---

## Task 1 (B1): Migration 008 — schema drop + recreate

**Files:**
- Verify: `backend/toms_gym/migrations/008_fairway_schema.sql` (already in-flight, 101 lines).
- Modify: `backend/toms_gym/app.py` (remove inline `CREATE TABLE` block lines 117–194 — already in-flight).
- Modify: `backend/tests/conftest.py` / `backend/tests/init_db.py` (apply 008 in test setup — already in-flight).
- Modify: `backend/toms_gym/migrations/README.md` (document 008 and rollback — already in-flight).

**Tracked task:** #10.

- [ ] **Step 1 (red): prove the inline block is gone and 008 is authoritative**

```bash
grep -n 'CREATE TABLE IF NOT EXISTS "Golf' backend/toms_gym/app.py
```
Expected: no matches. Assertion: the inline block at `app.py:117-194` has been removed entirely (not commented out).

- [ ] **Step 2 (red): prove 008 creates the five new tables and installs pg_trgm**

Assertion set for `008_fairway_schema.sql`:
- Contains `CREATE EXTENSION IF NOT EXISTS pg_trgm;`.
- `DROP TABLE IF EXISTS "GolfHoleScore" CASCADE;`, `"GolfHandicap"`, `"GolfRound"` all present.
- `CREATE TABLE "Course"`, `"Tee"`, `"Round"`, `"HoleScore"`, `"HandicapSnapshot"` all present.
- `CREATE INDEX idx_course_name_trgm ON "Course" USING GIN (name gin_trgm_ops);` present.
- `CHECK (holes IN (9, 18))` on both `Course.holes` and `Round.holes`.
- `Tee.slope_18 CHECK (slope_18 BETWEEN 55 AND 155)` (WHS legal range).

- [ ] **Step 3 (green): apply migration locally and run backend tests**

```bash
cd backend
venv/bin/python toms_gym/migrations/apply_schema.py   # local test DB
venv/bin/pytest -q tests
```
Expected: all prior golf tests pass against the new schema (they may need shape updates — coordinate with Task 4). The migration applies cleanly on an empty DB and is idempotent-safe on a DB that already has Fairway tables (because of the `DROP ... CASCADE` at the top).

- [ ] **Step 4 (verification):**

```bash
cd backend && venv/bin/pytest tests/test_golf_parser.py -q
git diff --stat main -- backend/toms_gym/app.py backend/toms_gym/migrations/008_fairway_schema.sql
```
Expected: `app.py` shows ≈84 lines removed; `008_fairway_schema.sql` shows ~101 lines added.

- [ ] **Step 5: commit**

```bash
git add backend/toms_gym/migrations/008_fairway_schema.sql \
        backend/toms_gym/migrations/README.md \
        backend/toms_gym/app.py \
        backend/tests/conftest.py \
        backend/tests/init_db.py
git commit -m "feat(golf): Phase B schema — Course/Tee/Round/HoleScore/HandicapSnapshot (Task 1)"
```

---

## Task 2 (B2): WHS handicap engine + unit tests

**Files:**
- Create: `backend/toms_gym/services/handicap.py`.
- Verify + extend: `backend/tests/test_handicap.py` (216 lines in-flight, ~13 tests).
- Verify + extend: `backend/tests/fixtures/whs_reference_cases.json` (120 lines in-flight).

**Tracked task:** #11.

- [ ] **Step 1 (red): finalize the reference-case fixture**

`whs_reference_cases.json` must contain at least one case per adjustment-table row (3, 4, 5, 6, 7, 8, 9, 12, 15, 17, 19, 20+ rounds) plus:
- `establishing_1_round`, `establishing_2_rounds` → `handicap_index: null`, `status: "establishing"`.
- `twelve_month_cap` → a case where the raw index would rise >5.0 above the 12-month low and must be clamped.
- `nine_hole_weight_half` → 2 × 9-hole rounds treated as 1 × 18-hole-equivalent for the "last 20" window.
- `ndb_cap_no_handicap` → per-hole scores above 10 capped at 10 before differential.
- `ndb_cap_with_handicap` → cap at `par + 2 + course_handicap_strokes_on_hole`.

Assertion: `venv/bin/python -c "import json; d=json.load(open('backend/tests/fixtures/whs_reference_cases.json')); assert len(d['cases']) >= 17"`.

- [ ] **Step 2 (red): run the existing tests and expect import failure**

```bash
cd backend && venv/bin/pytest tests/test_handicap.py -q
```
Expected: `ModuleNotFoundError: No module named 'toms_gym.services.handicap'` (or equivalent). This confirms tests are red for the right reason.

- [ ] **Step 3 (green): implement `services/handicap.py`**

Public API (stable — Task 4 depends on these signatures):

```python
# backend/toms_gym/services/handicap.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class DifferentialInput:
    adjusted_gross_score: int
    course_rating: Decimal
    slope_rating: int
    pcc: int = 0          # playing-conditions calc; MVP = 0
    holes: int = 18       # 9 or 18

def compute_differential(d: DifferentialInput) -> Decimal: ...
    # Returns ((adjusted - rating - pcc) * 113 / slope), rounded to 0.1.

def net_double_bogey(par: int, strokes: int, course_handicap: Optional[int], hole_handicap_rank: Optional[int]) -> int: ...
    # Cap at 10 when course_handicap is None.
    # Otherwise cap at par + 2 + strokes_received_on_hole(course_handicap, hole_handicap_rank).

def allocate_strokes(course_handicap: int, hole_handicap_ranks: list[int]) -> list[int]: ...
    # Returns per-hole strokes-received array of length 18 (or 9).

def compute_handicap_index(
    differentials: list[tuple[Decimal, bool, datetime]],  # (differential, is_nine_hole, played_on)
    twelve_month_low: Optional[Decimal] = None,
) -> dict:
    # Returns {"handicap_index": Decimal|None, "rounds_used": int,
    #          "differentials_used": list[Decimal],
    #          "status": "establishing"|"active", "rounds_needed": int|None}
    # - Weights 9-hole rounds at 0.5 toward the "last 20".
    # - Applies WHS adjustment table.
    # - Enforces 12-month cap (+5.0 over twelve_month_low).
    # - Caps final index at 54.0.
```

- [ ] **Step 4 (verification):**

```bash
cd backend && venv/bin/pytest tests/test_handicap.py -q -v
```
Expected: all 13+ tests green.

- [ ] **Step 5: commit**

```bash
git add backend/toms_gym/services/handicap.py \
        backend/tests/test_handicap.py \
        backend/tests/fixtures/whs_reference_cases.json
git commit -m "feat(golf): WHS handicap engine + reference-case unit tests (Task 2)"
```

---

## Task 3 (B3): Courses service — pg_trgm fuzzy match + tee match/create

**Files:**
- Create: `backend/toms_gym/services/courses.py`.
- Create: `backend/tests/test_courses.py`.

**Tracked task:** #12.

- [ ] **Step 1 (red): write `test_courses.py` with failing tests**

Cases (all against a seeded test DB with 3 verified courses + 4 tees):
- `test_match_course_exact_name_returns_existing_course`.
- `test_match_course_fuzzy_trgm_above_threshold_returns_existing` — `"Pebbl Beach"` → `"Pebble Beach"`.
- `test_match_course_below_threshold_creates_pending` — random string yields a new `status='pending'` row.
- `test_match_course_geo_bias_tiebreaks_ambiguous_name` — two courses with similar names; user lat/lng prefers the closer one.
- `test_match_tee_by_name_returns_existing` — `"Blue"` matches on the resolved course.
- `test_match_tee_creates_when_rating_and_slope_present` — no existing tee, rating/slope supplied → inserts.
- `test_match_tee_returns_none_when_rating_slope_missing` — no rating/slope → returns `None`, caller flags `needs_tee`.
- `test_search_courses_returns_fuzzy_matches_ordered_by_similarity`.
- `test_search_courses_geo_bias_sorts_closer_first_among_equal_similarity`.

Run: `cd backend && venv/bin/pytest tests/test_courses.py -q`. Expected: 9 failures with `ModuleNotFoundError`.

- [ ] **Step 2 (red → ready): publish signature-only `courses.py` with `NotImplementedError`**

Unblocks Task 4 (which can import against these signatures):

```python
# backend/toms_gym/services/courses.py
from decimal import Decimal
from typing import Optional, TypedDict

class MatchedCourse(TypedDict):
    id: str
    name: str
    status: str  # 'verified' | 'pending'
    similarity: float
    created: bool

class MatchedTee(TypedDict):
    id: Optional[str]
    name: Optional[str]
    rating_18: Optional[Decimal]
    slope_18: Optional[int]
    needs_input: bool  # True when rating/slope missing

def match_or_create_course(
    session,
    name: str,
    *,
    city: Optional[str] = None,
    state: Optional[str] = None,
    latitude: Optional[Decimal] = None,
    longitude: Optional[Decimal] = None,
    threshold: float = 0.55,
) -> MatchedCourse: ...

def match_or_create_tee(
    session,
    course_id: str,
    name: Optional[str],
    *,
    rating_18: Optional[Decimal] = None,
    slope_18: Optional[int] = None,
    yardage: Optional[int] = None,
) -> MatchedTee: ...

def search_courses(
    session,
    q: str,
    *,
    near: Optional[tuple[Decimal, Decimal]] = None,
    limit: int = 10,
) -> list[MatchedCourse]: ...
```

Commit these signatures early so Task 4 can proceed in parallel:

```bash
git add backend/toms_gym/services/courses.py backend/tests/test_courses.py
git commit -m "chore(golf): courses service skeleton + red tests (Task 3 WIP)"
```

- [ ] **Step 3 (green): implement the service**

SQL sketch for `match_or_create_course`:

```sql
SELECT id, name, status, similarity(name, :q) AS sim,
       ST_Distance(...)  -- only if latitude/longitude supplied
  FROM "Course"
 WHERE name % :q
 ORDER BY sim DESC, distance_m ASC NULLS LAST
 LIMIT 1;
```
(If PostGIS is unavailable, compute great-circle distance in Python from returned `latitude`/`longitude`.)

Threshold default 0.55 (tune once against the fixture). On miss, `INSERT INTO "Course" (name, status, latitude, longitude) VALUES (:q, 'pending', ...) RETURNING id`.

- [ ] **Step 4 (verification):**

```bash
cd backend && venv/bin/pytest tests/test_courses.py -q -v
```
Expected: all 9 tests green.

- [ ] **Step 5: commit**

```bash
git add backend/toms_gym/services/courses.py
git commit -m "feat(golf): courses service — pg_trgm fuzzy match + tee match/create (Task 3)"
```

---

## Task 4 (B5): golf_routes.py rewrite — new shapes + delegation + new endpoints

**Files:**
- Modify: `backend/toms_gym/routes/golf_routes.py` (substantial rewrite).

**Tracked task:** #13.

- [ ] **Step 1 (red): update existing route tests to expect nested shapes**

In `backend/tests/test_golf_parser.py` (and any other route tests), change assertions:
- Upload response: `data["round"]["course"]["id"]` exists, `data["round"]["tee"]["slope_18"]` exists; flat `data["round"]["course_name"]` no longer asserted.
- `GET /round/<id>` response mirrors this shape.
- `GET /leaderboard` returns `latest_snapshot.handicap_index` (not `handicap.handicap_index`).

Run: `cd backend && venv/bin/pytest tests/test_golf_parser.py -q`. Expected: reds on `KeyError: 'course'` / `KeyError: 'tee'`.

- [ ] **Step 2 (green): rewrite handler surfaces**

Edits to `golf_routes.py`:

1. `_recalculate_handicap(session, user_id)` becomes a thin wrapper:
   ```python
   from toms_gym.services.handicap import compute_handicap_index
   # Load last-20-weighted differentials for user_id from "Round" (date-desc).
   # Load twelve_month_low from "HandicapSnapshot".
   # Call compute_handicap_index(...).
   # INSERT a new "HandicapSnapshot" row with triggered_by_round_id.
   ```
2. `upload_scorecard()` (post-parse):
   ```python
   from toms_gym.services.courses import match_or_create_course, match_or_create_tee
   course = match_or_create_course(session, detected_course_name, city=..., latitude=..., longitude=...)
   tee    = match_or_create_tee(session, course["id"], detected_tee_name, rating_18=..., slope_18=...)
   needs_tee = tee["needs_input"]
   # INSERT INTO "Round" (user_id, course_id, tee_id, holes, scorecard_image_url, ocr_raw, ocr_confidence, processing_status)
   ```
3. `get_round(round_id)` response shape:
   ```json
   {
     "round": {
       "id": "...",
       "played_on": "2026-04-18",
       "holes": 18,
       "course": {"id": "...", "name": "...", "status": "verified", "city": "...", "state": "..."},
       "tee":    {"id": "...", "name": "Blue", "rating_18": 72.1, "slope_18": 130, "yardage": 6400},
       "hole_scores": [...],
       "score_differential": 12.5,
       "needs_tee": false,
       "ocr_confidence": 0.91
     },
     "detected_players": [...]
   }
   ```
4. `confirm_scores(round_id)` — still `PUT /round/<id>/scores`, but now also emits a `HandicapSnapshot` on success.
5. `delete_round(round_id)` — also emits a `HandicapSnapshot` (recalc after deletion).
6. `get_rounds()` — nested `course` / `tee` per round.
7. `get_leaderboard()` — `SELECT DISTINCT ON (user_id) ... FROM "HandicapSnapshot" ORDER BY user_id, created_at DESC`.
8. **New endpoints:**
   - `GET /golf/courses?q=&near=lat,lng` → `search_courses(...)`. Anonymous-accessible, rate-limited.
   - `POST /golf/courses` → body `{name, city?, state?, country?, latitude?, longitude?, holes?}` → inserts `status='verified'` if the caller is authenticated, else `status='pending'`. Returns the new course row.
   - `GET /golf/users/<user_id>/handicap/history?range=6m|12m|24m|all` → `SELECT handicap_index, created_at FROM "HandicapSnapshot" WHERE user_id=... ORDER BY created_at ASC` filtered by range. Returns `[{handicap_index, created_at}, ...]`.

- [ ] **Step 3 (verification):**

```bash
cd backend && venv/bin/pytest tests/test_golf_parser.py tests/test_handicap.py tests/test_courses.py -q -v
```
Expected: all green. Plus a manual curl check of the three new endpoints against a local run.

- [ ] **Step 4: commit**

```bash
git add backend/toms_gym/routes/golf_routes.py backend/tests/test_golf_parser.py
git commit -m "feat(golf): rewire golf routes — nested course/tee, handicap snapshots, new endpoints (Task 4)"
```

---

## Task 5: Extend `test_golf_parser.py` with course/tee matching integration tests

**Files:**
- Modify: `backend/tests/test_golf_parser.py`.

**Tracked task:** #14.

- [ ] **Step 1 (red): add failing integration cases**

Cases:
- `test_upload_seeds_matching_course_when_ocr_exact_name` — seed `Course("Pebble Beach", verified)` → upload OCR fixture with `"Pebble Beach"` → response `round.course.id` matches seeded id, no new course created.
- `test_upload_seeds_matching_course_when_ocr_fuzzy_name` — seed same course → upload with `"Pebble Bch"` → response matches seeded id.
- `test_upload_creates_pending_course_on_miss` — no seed → upload with random course name → response `round.course.status == "pending"` and a new row exists.
- `test_upload_matches_tee_by_name` — seed `Tee("Blue", rating=72.1, slope=130)` on the course → upload → response `round.tee.id` matches seeded id.
- `test_upload_flags_needs_tee_when_rating_and_slope_missing` — seed no tee, upload with no rating/slope → response `round.needs_tee == true` and `round.tee.id is None`.

Run: `cd backend && venv/bin/pytest tests/test_golf_parser.py -q`. Expected: 5 failures.

- [ ] **Step 2 (green): test data only — no code changes should be required**

All behavior is implemented by Tasks 3 + 4. If tests fail for reasons beyond missing assertions, file a bug against Task 3 or Task 4 rather than patching the route.

- [ ] **Step 3 (verification):**

```bash
cd backend && venv/bin/pytest tests/test_golf_parser.py -q -v
```
Expected: all cases green.

- [ ] **Step 4: commit**

```bash
git add backend/tests/test_golf_parser.py
git commit -m "test(golf): course/tee matching integration cases (Task 5)"
```

---

## Task 6 (B6): Frontend types + read-only pages data swap

**Files:**
- Modify: `frontend/src/lib/api.ts`.
- Modify: `frontend/src/pages/GolfRound.tsx`.
- Modify: `frontend/src/pages/GolfProfile.tsx`.
- Modify: `frontend/src/pages/GolfLeaderboard.tsx`.
- Modify: `frontend/src/pages/GolfReview.tsx` (data reads only — drawer wiring happens in Task 7).

**Tracked task:** #15.

- [ ] **Step 1 (red): add types + client functions**

In `frontend/src/lib/api.ts`:

```ts
export type Course = {
  id: string;
  name: string;
  city?: string;
  state?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
  status: 'verified' | 'pending';
};

export type Tee = {
  id: string | null;
  name: string | null;
  rating_18: number | null;
  slope_18: number | null;
  yardage: number | null;
  needs_input?: boolean;
};

export type GolfRoundWithHoles = {
  id: string;
  played_on: string;
  holes: 9 | 18;
  course: Course;
  tee: Tee;
  hole_scores: HoleScore[];
  score_differential: number | null;
  needs_tee: boolean;
  ocr_confidence: number | null;
};

export type HandicapHistoryPoint = { handicap_index: number | null; created_at: string };

export async function searchCourses(q: string, near?: {lat: number; lng: number}): Promise<Course[]> { ... }
export async function getHandicapHistory(userId: string, range: '6m'|'12m'|'24m'|'all'): Promise<HandicapHistoryPoint[]> { ... }
```

- [ ] **Step 2 (green): swap reads in read-only pages**

Replace `round.course_name` → `round.course.name`; `round.slope_rating` → `round.tee.slope_18`; `round.course_rating` → `round.tee.rating_18`. In `GolfLeaderboard`: `entry.handicap_index` stays named the same but is fed from `latest_snapshot.handicap_index`.

For `GolfReview`: just swap the reads — no new UI, no drawer. That comes in Task 7.

- [ ] **Step 3 (verification):**

```bash
cd frontend && pnpm typecheck && pnpm test -- --run
```
Expected: typecheck clean; existing component tests green.

- [ ] **Step 4: commit**

```bash
git add frontend/src/lib/api.ts \
        frontend/src/pages/GolfRound.tsx \
        frontend/src/pages/GolfProfile.tsx \
        frontend/src/pages/GolfLeaderboard.tsx \
        frontend/src/pages/GolfReview.tsx
git commit -m "feat(golf): swap Phase A pages onto nested course/tee shapes (Task 6)"
```

---

## Task 7 (B4): TeePickerDrawer + DifficultyMeter + GolfReview wiring

**Files:**
- Create: `frontend/src/components/golf/TeePickerDrawer.tsx`.
- Create: `frontend/src/components/golf/DifficultyMeter.tsx`.
- Modify: `frontend/src/pages/GolfReview.tsx` (wire the drawer).

**Tracked task:** #16.

- [ ] **Step 1 (red): component unit tests**

`frontend/src/components/golf/__tests__/TeePickerDrawer.test.tsx`:
- Renders up to 4 tee cards.
- Selected card carries the `fw-selected` class (2px info border — uses Phase A's token).
- Editing rating recomputes the live differential preview.
- Difficulty meter needle sits at the correct horizontal position for slope=113 (center), slope=100 (left), slope=145 (right).

Run: `cd frontend && pnpm test -- TeePickerDrawer`. Expected: failing because the file doesn't exist.

- [ ] **Step 2 (green): implement the drawer**

```tsx
// TeePickerDrawer.tsx (sketch)
type Props = {
  courseId: string;
  tees: Tee[];
  selectedTeeId: string | null;
  adjustedGrossScore: number;
  onSelect: (teeId: string | null, overrides: Partial<Tee>) => void;
  onLookup: (q: string) => Promise<Course[]>;
};
// Renders:
//  - Tee cards grid, each with `className={cn("fw-surface", selected && "fw-selected")}`.
//  - <input type="number" step="0.1"> for rating, step="1" for slope/yardage.
//  - <DifficultyMeter slope={currentSlope} />
//  - Live differential preview:
//      diff = ((score - rating) * 113) / slope  (display rounded to 0.1)
//  - "Look up official values" → calls onLookup + populates suggestions.
```

`DifficultyMeter.tsx`:
- Horizontal bar 0–100% mapped to slope 55–155.
- Vertical anchor at slope 113.
- Labels under the bar: 100 "Forgiving", 113 "Average", 130 "Above average", 145 "Brutal".

`GolfReview.tsx` wiring: the course/tee header gets a "Change" button; on click, open the drawer. On drawer confirm, update local state and send the chosen `tee_id` (or new tee body) as part of the `PUT /round/<id>/scores` payload.

- [ ] **Step 3 (verification):**

```bash
cd frontend && pnpm typecheck && pnpm test -- --run TeePickerDrawer DifficultyMeter GolfReview
```
Expected: green.

- [ ] **Step 4: commit**

```bash
git add frontend/src/components/golf/TeePickerDrawer.tsx \
        frontend/src/components/golf/DifficultyMeter.tsx \
        frontend/src/components/golf/__tests__/TeePickerDrawer.test.tsx \
        frontend/src/components/golf/__tests__/DifficultyMeter.test.tsx \
        frontend/src/pages/GolfReview.tsx
git commit -m "feat(golf): TeePickerDrawer + DifficultyMeter on review page (Task 7)"
```

---

## Task 8 (B7): Playwright Phase B e2e + Phase A regression gate

**Files:**
- Create: `frontend/e2e/golf-fairway-phase-b.spec.ts`.
- Read-only: `frontend/e2e/golf-fairway-phase-a.spec.ts` (re-run unchanged).

**Tracked task:** #17.

- [ ] **Step 1 (red): author the spec with failing assertions**

Coverage:
- `tee_picker_opens_and_lists_up_to_four_tees` — click "Change" → drawer visible with ≤4 cards.
- `selected_tee_has_fw_selected_border` — selected card matches `.fw-selected`.
- `editing_slope_updates_live_differential` — type `130` → differential text changes.
- `handicap_history_endpoint_returns_array` — `GET /golf/users/:id/handicap/history` returns ordered points.
- `course_search_endpoint_returns_fuzzy_matches` — `GET /golf/courses?q=Pebbl` returns the seeded Pebble Beach.
- `post_course_creates_pending_course_for_anonymous` — `POST /golf/courses` returns status=`pending`.

Use deterministic UUIDs + per-test `page.route` stubs (same pattern as Phase A's spec).

- [ ] **Step 2 (red): run Phase A regression**

```bash
cd frontend && npx playwright test e2e/golf-fairway-phase-a.spec.ts
```
Expected: all 12 assertions green after Task 6's data swap. Any failure is a Phase B regression — fix before proceeding.

- [ ] **Step 3 (green): run Phase B**

```bash
cd frontend && npx playwright test e2e/golf-fairway-phase-b.spec.ts
```
Expected: all 6 assertions green.

- [ ] **Step 4 (verification):**

```bash
cd frontend && npx playwright test e2e/golf-fairway-phase-a.spec.ts e2e/golf-fairway-phase-b.spec.ts --reporter=list
```
Expected: 18 passes, 0 failures. (Unrelated failures in `user-workflows.spec.ts` — see handoff caveat #2 — are pre-existing on `main` and do not block.)

- [ ] **Step 5: commit**

```bash
git add frontend/e2e/golf-fairway-phase-b.spec.ts
git commit -m "test(golf): Phase B e2e — tee-picker, live differential, handicap history (Task 8)"
```

---

## Task 9: Deploy + prod smoke + PR + Phase B → D handoff

**Files:** none code (deploy + docs).
**Tracked task:** #20.

- [ ] **Step 1: run the full test sweep one final time**

```bash
cd backend && venv/bin/pytest -q
cd ../frontend && pnpm typecheck && pnpm lint && pnpm test -- --run
cd frontend && npx playwright test e2e/golf-fairway-phase-a.spec.ts e2e/golf-fairway-phase-b.spec.ts
```
Expected: all green. Fix any reds before continuing — do NOT deploy red code.

- [ ] **Step 2: apply migration 008 against Cloud SQL**

```bash
# from project root
gcloud sql connect toms-gym-db --user=postgres --project=toms-gym < backend/toms_gym/migrations/008_fairway_schema.sql
```
Confirm with `\dt` that the five new tables exist and the old three are gone.

- [ ] **Step 3: deploy**

```bash
python3 deploy.py --skip-iam
```

- [ ] **Step 4: prod smoke**

- Visit `https://toms-gym-web-quyiiugyoq-ue.a.run.app/golf/upload`, upload a scorecard, review, confirm, verify `GolfRound` page shows nested course/tee.
- `curl https://my-python-backend-quyiiugyoq-ue.a.run.app/golf/courses?q=pebble` → non-empty.
- `curl https://my-python-backend-quyiiugyoq-ue.a.run.app/golf/users/<test-user>/handicap/history` → array.

- [ ] **Step 5: open the PR**

```bash
gh pr create --base main --head golf/fairway-phase-b \
  --title "feat(golf): Fairway Phase B — Course/Tee/HandicapSnapshot + WHS engine" \
  --body "$(cat <<'PR'
## Summary
- Drop flat GolfRound/GolfHoleScore/GolfHandicap; add Course/Tee/Round/HoleScore/HandicapSnapshot (migration 008).
- New WHS handicap engine (NDB cap, adjustment table, 12-month cap, 9-hole weighting) with reference-case unit tests.
- New courses service with pg_trgm fuzzy match + tee match/create; three new endpoints.
- Frontend reads nested course/tee; new TeePickerDrawer + DifficultyMeter on the review page.
- Phase A visuals unchanged; Phase A e2e suite re-run as regression gate.

## Test plan
- [x] backend pytest green (handicap, courses, golf_parser, all legacy).
- [x] frontend typecheck + lint + unit tests green.
- [x] Playwright `golf-fairway-phase-a.spec.ts` (12 assertions) + `golf-fairway-phase-b.spec.ts` (6 assertions) green.
- [x] Prod smoke: upload → review → round end-to-end.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
PR
)"
```
If `gh pr create` fails due to enterprise-managed-user auth (see handoff caveat), share the branch URL manually as Phase A did.

- [ ] **Step 6: write Phase B → D handoff**

Create `docs/superpowers/handoffs/2026-MM-DD-fairway-phase-b-to-d.md` following the Phase A→B template: where we are, branch state, what Phase B delivered, caveats for Phase D, kick-off prompt. Commit and push.

- [ ] **Step 7: close out**

Mark team task #20 complete. Do not request shutdown until the manager confirms receipt of the handoff.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration 008 fails mid-apply on Cloud SQL (partial drop) | Low | High — prod down | Wrap entire migration in `BEGIN; ... COMMIT;` (already present). Test apply against a local DB clone first. On failure, `ROLLBACK` and the DB is untouched. |
| WHS reference cases disagree with the engine by 0.1 | Medium | Medium — leaderboards off | Use `Decimal` + WHS-spec rounding rules (`ROUND_HALF_EVEN` to one decimal). Unit tests enforce bit-for-bit equality to the fixture. |
| `pg_trgm` similarity threshold too tight → false pending-course spam | Medium | Medium — messy course list | Default 0.55 but make it a function-arg; tune against the seeded fixture. Add admin query to list `status='pending'` rows. |
| `/golf/upload` rate limit (10/hr) throttles integration tests | High | Low | Use `page.route` to stub the upload endpoint in e2e, as Phase A does. Backend integration tests hit the Flask test client directly, bypassing the limiter. |
| Task 4's rewrite collides with Task 3's courses service if signatures drift | Medium | Medium — merge conflicts | Task 3 commits signatures + docstrings + `NotImplementedError` stubs + red tests BEFORE Task 4 starts. Task 4 imports against the stable signatures. |
| Frontend shape change breaks an uncovered page | Low | Low | Task 6 types tightened; `tsc --noEmit` catches missed reads. (Note: `tsconfig.json` has `noUnusedLocals: false` per handoff caveat #3 — don't rely on it for cleanup.) |
| Phase A e2e regress after data swap | Medium | Low | Task 8 Step 2 re-runs the Phase A spec unchanged as an explicit gate. |
| `user-workflows.spec.ts` pre-existing reds masked as Phase B failures | Low | Low | Handoff caveat #2 enumerates them; CI report whitelists the two known reds. |

---

## Rollback plan

The schema change is the only non-trivial-to-reverse action.

1. **Before merge:** code lives on `golf/fairway-phase-b`; migration 008 only applies when the doer runs `apply_schema.py` or the gcloud command. Abandon the branch to roll back — no changes on `main`.

2. **After merge, before deploy:** revert the merge commit on `main` (`git revert -m 1 <merge-sha>`). No DB changes have landed yet.

3. **After deploy, migration applied:**
   - Re-deploy the prior Cloud Run image (`gcloud run services update-traffic my-python-backend --to-revisions=PREV_REV=100 --region=us-east1`).
   - Drop the five new tables:
     ```sql
     BEGIN;
       DROP TABLE "HandicapSnapshot" CASCADE;
       DROP TABLE "HoleScore"        CASCADE;
       DROP TABLE "Round"            CASCADE;
       DROP TABLE "Tee"              CASCADE;
       DROP TABLE "Course"           CASCADE;
     COMMIT;
     ```
   - Re-apply the inline `CREATE TABLE` block from `app.py` (commit `040c034` — pre-Phase-B `main`).
   - Greenfield data policy (handoff caveat #5) means NO user data is lost; no restore step is needed.

---

## Performance, reliability, and test implications

- **Performance:** GIN trigram index on `Course.name` keeps fuzzy search O(log N). Fetching last-20 differentials per user is indexed by `(user_id, played_on DESC)`. `HandicapSnapshot` history fetch is indexed by `(user_id, created_at DESC)`.
- **Reliability:** all handicap writes go through a single `session.begin()` transaction per route; a failed snapshot write rolls back the round save. `match_or_create_course` is idempotent on exact name match.
- **Test implications:** `test_handicap.py` is the authoritative WHS spec for this codebase — any future handicap change must re-run it. The fixture file is the contract; changes to it require a spec update.

---

## Success criteria

- Migration 008 applied in prod without data loss.
- `test_handicap.py`, `test_courses.py`, `test_golf_parser.py` all green.
- `GET /golf/round/<id>` returns nested `course` / `tee` objects.
- `GET /golf/courses?q=` and `GET /golf/users/:id/handicap/history` both live in prod.
- Phase A e2e suite (12 assertions) and Phase B e2e suite (6 assertions) both green.
- Tee-picker drawer opens from `GolfReview`, selected tee shows 2px `fw-info` border, editing slope updates the live differential.
- Phase B → D handoff doc merged to `main`.
