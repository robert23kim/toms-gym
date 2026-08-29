# Fairway Phase B — Correctness + Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat `GolfRound`/`GolfHoleScore`/`GolfHandicap` schema with a proper `Course`/`Tee`/`Round`/`HoleScore`/`HandicapSnapshot` model; rewrite the handicap engine against WHS reference rules (net-double-bogey, establishing, 12-month low cap, 9-hole support); wire OCR → Course/Tee matching via `pg_trgm`; add a tee-picker drawer on the review page; keep Phase A visuals untouched. Minimal JSX diffs on pages — only data plumbing changes.

**Architecture:** New backend module `backend/toms_gym/services/handicap.py` owns the WHS math as pure functions over lists of differentials, so unit tests need no DB. New module `backend/toms_gym/services/courses.py` owns fuzzy course/tee matching and creation. Migration `008_fairway_schema.sql` drops and recreates the golf tables (greenfield — user confirmed no production data to preserve). The inline `CREATE TABLE` block in `backend/toms_gym/app.py:117-194` is deleted. Existing `/golf/*` routes keep their paths; response shapes evolve to nest `course` and `tee` objects. Three new routes land: `GET /golf/courses`, `POST /golf/courses`, `GET /golf/users/:id/handicap/history`. Frontend `GolfReview.tsx` / `GolfRound.tsx` / `GolfProfile.tsx` re-plumb to the new shapes and render a tee-picker modal; Phase A CSS classes (`fw-scope`, `fw-cell`, `fw-selected`, etc.) are re-used as-is.

**Tech Stack:** Flask + SQLAlchemy Core (existing pattern — raw `sqlalchemy.text` + `get_db_connection`). PostgreSQL with `pg_trgm` extension for fuzzy match. React 18 + TypeScript + Vite, Tailwind, Playwright for e2e. Pytest for backend unit/integration tests.

**Spec reference:** `docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md` §Phase B.
**Handoff context:** `docs/superpowers/handoffs/2026-04-18-fairway-phase-a-to-b.md`.
**Style reference:** `docs/superpowers/plans/2026-04-18-fairway-phase-a.md` (same bite-sized TDD cadence — tests first, then implementation, then commit).

**Branching assumption:** Phase A (`golf/fairway-phase-a`) is merged to `main` before Phase B deploys. This plan branches from `main` post-merge.

**Phase D:** tracked separately in `docs/superpowers/plans/YYYY-MM-DD-fairway-phase-d.md` after Phase B ships.

---

## File structure

**Create (backend):**
- `backend/toms_gym/migrations/008_fairway_schema.sql` — drops `GolfRound`/`GolfHoleScore`/`GolfHandicap`; creates `Course`, `Tee`, `Round`, `HoleScore`, `HandicapSnapshot`; enables `pg_trgm` and adds GIN trigram index on `Course.name`.
- `backend/toms_gym/services/__init__.py` — package marker.
- `backend/toms_gym/services/handicap.py` — pure WHS engine (net-double-bogey, differential, index, establishing, 12-month cap, 9-hole).
- `backend/toms_gym/services/courses.py` — DB helpers for fuzzy course match + tee match/create.
- `backend/tests/test_handicap.py` — unit tests for every rule in `handicap.py` (no DB).
- `backend/tests/test_courses_service.py` — integration tests for `courses.py` against seeded `Course` / `Tee` rows.
- `backend/tests/fixtures/whs_reference_cases.json` — canonical WHS examples (rounds counts 3/4/5/6/9/15/20, establishing case, 12-month cap case, 9-hole case) used by `test_handicap.py`.

**Modify (backend):**
- `backend/toms_gym/app.py` — remove the inline `CREATE TABLE IF NOT EXISTS "GolfRound"/"GolfHoleScore"/"GolfHandicap"` blocks (lines ~117–194). Leave the `BowlingResult` annotation block and the surrounding try/except structure intact.
- `backend/toms_gym/migrations/README.md` — document 008.
- `backend/toms_gym/routes/golf_routes.py` — swap table names + response shapes; inline `_recalculate_handicap` delegates to `services.handicap`; upload handler calls `services.courses` for course/tee resolution; add `GET /golf/courses`, `POST /golf/courses`, `GET /golf/users/<user_id>/handicap/history`.
- `backend/tests/test_golf_parser.py` — add integration tests exercising course/tee matching on the upload path (Vision client stubbed).
- `backend/tests/conftest.py` — if it currently seeds `GolfRound`, update fixtures to seed the new tables; add `seed_course` / `seed_tee` helpers.

**Create (frontend):**
- `frontend/src/components/golf/TeePickerDrawer.tsx` — modal with up to 4 tee cards, editable rating/slope/yardage, difficulty meter anchored at 113, live differential preview, "Look up official values" button.
- `frontend/src/components/golf/DifficultyMeter.tsx` — the 100/113/130/145 horizontal meter used inside `TeePickerDrawer`.

**Modify (frontend):**
- `frontend/src/lib/api.ts` — new/updated types for `Course`, `Tee`, `Round`, `HoleScore`, `HandicapSnapshot`; client fns `searchCourses`, `createCourse`, `getHandicapHistory`; `fetchRound` / `fetchProfile` / `updateScores` return types updated.
- `frontend/src/pages/GolfReview.tsx` — consume nested `course` / `tee`; add "Change" link on course header that opens `TeePickerDrawer`; live differential already rendered in Phase A — re-wire its formula to draw from `round.tee.rating_18` / `round.tee.slope_18`.
- `frontend/src/pages/GolfRound.tsx` — render `round.course.name`, `round.tee.name` + color chip; Phase A visual layout kept verbatim.
- `frontend/src/pages/GolfProfile.tsx` — rounds list entries pull `course.name` instead of flat `course_name`; handicap card pulls from `HandicapSnapshot` via `/handicap/history` (latest).
- `frontend/src/pages/GolfLeaderboard.tsx` — add `monthly_delta` column render; underlying table now backed by latest `HandicapSnapshot` rather than deleted `GolfHandicap`. (Listed as "Modify" only — no `No changes` entry elsewhere in the plan should reference this page.)
- `frontend/e2e/golf-fairway-phase-a.spec.ts` — rename to `golf-fairway.spec.ts` OR keep Phase A file read-only and add `frontend/e2e/golf-fairway-phase-b.spec.ts` (chosen: new file, Phase A suite stays a regression gate).
- `frontend/e2e/golf-fairway-phase-b.spec.ts` (new) — tee-picker drawer opens, selecting a tee updates live differential, changed values persist to `PUT /golf/round/:id/scores`.

**No changes:**
- `frontend/src/styles/fairway.css` — Phase A tokens stay.
- `FairwayScope.tsx`, `StagedParseProgress.tsx`, `HighlightsGrid.tsx`, `HoleBarChart.tsx`, `ReviewBanner.tsx` — presentational only.
- `GolfUpload.tsx` — no response-shape fields rendered post-submit that change here (the upload response still carries `round_id`).
- Lifting / bowling / auth code.

---

## Parallelization map

Tasks are labelled P1…P3 by parallel-wave and annotated with the files they touch. Within a wave, tasks can run concurrently because they touch disjoint files. Across waves there are dependencies (later waves read contracts defined by earlier ones).

**Wave P1 — foundation (sequential, one agent, ~1 hr).** Everything else depends on the migration + handicap module landing first.
- Task 0: Branch setup.
- Task 1: Migration SQL `008_fairway_schema.sql` + delete inline `app.py` block.
- Task 2: `services/handicap.py` + `test_handicap.py` + WHS fixture JSON.

**Wave P2 — backend (two agents in parallel, disjoint files).**
- Task 3 (agent A): `services/courses.py` + `test_courses_service.py`.
- Task 4 (agent B): `routes/golf_routes.py` rewrite — shape swap + delegation to `services.handicap` + new endpoints.

  ⚠️ **Serialization within Task 4:** one agent only. The file is large (1075 lines) and three subtasks all edit it (shape swap in GET/PUT, new routes at bottom, upload handler course/tee resolution). Do them as sub-steps of a single task, not as parallel agents.

  Task 4 imports from `services.courses` — start Task 4 only after Task 3's module signature is stable (the test file lands first and nails the signature).

- Task 5 (agent A, after Task 3): extend `test_golf_parser.py` with course/tee matching integration tests that exercise Task 4's upload path. Waits on Task 4 to land the matching wiring.

**Wave P3 — frontend (two agents in parallel, disjoint files).**
- Task 6 (agent C): types + `lib/api.ts` + `GolfProfile.tsx` + `GolfLeaderboard.tsx` + `GolfRound.tsx` data swap (read-only pages; identical visual layout).
- Task 7 (agent D): `TeePickerDrawer.tsx` + `DifficultyMeter.tsx` + `GolfReview.tsx` wiring. Depends on Task 6's type definitions; start after agent C commits `api.ts`.
- Task 8 (single agent): Playwright `golf-fairway-phase-b.spec.ts`. Runs after Tasks 6 and 7 are both in.

**Wave P4 — verification (single agent).**
- Task 9: full backend test run, full frontend typecheck + build, full Playwright run; deploy to prod via `python3 deploy.py --skip-iam`; smoke prod.

**Shared-file hot spots (never parallelize):**
- `backend/toms_gym/routes/golf_routes.py` — Task 4 only.
- `frontend/src/lib/api.ts` — Task 6 owns; Task 7 reads.
- `frontend/src/pages/GolfReview.tsx` — Task 7 only.
- `frontend/e2e/golf-fairway-phase-b.spec.ts` — Task 8 only.

---

## Task 0: Branch setup

**Files:** none (git only).

- [ ] **Step 1: Create the phase branch from latest `main`**

```bash
git checkout main
git pull --ff-only
git checkout -b golf/fairway-phase-b
```

- [ ] **Step 2: Confirm Phase A is merged**

Run: `git log --oneline main | head -20 | grep -i fairway`
Expected: see Phase A commits on main (e.g., the 14 Phase A commits or their squash). If Phase A is **not** merged yet, STOP and wait — Phase B depends on the Phase A CSS tokens living on main.

- [ ] **Step 3: Confirm clean baseline**

Run: `git status`
Expected: `On branch golf/fairway-phase-b; nothing to commit, working tree clean`

---

## Task 1: Migration 008 — Fairway schema (drop + recreate) + remove inline block

**Files:**
- Create: `backend/toms_gym/migrations/008_fairway_schema.sql`
- Modify: `backend/toms_gym/app.py` (delete inline golf `CREATE TABLE` blocks)
- Modify: `backend/toms_gym/migrations/README.md`

- [ ] **Step 1: Write the migration SQL**

Create `backend/toms_gym/migrations/008_fairway_schema.sql`:

```sql
-- Migration 008: Fairway schema — Course/Tee/Round/HoleScore/HandicapSnapshot.
-- Greenfield migration (user confirmed no production golf data to preserve).
-- Rollback: DROP the five new tables + redeploy prior image.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Drop old flat golf tables.
DROP TABLE IF EXISTS "GolfHoleScore" CASCADE;
DROP TABLE IF EXISTS "GolfHandicap" CASCADE;
DROP TABLE IF EXISTS "GolfRound"     CASCADE;

CREATE TABLE "Course" (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    city        TEXT,
    state       TEXT,
    country     TEXT,
    latitude    DECIMAL(9,6),
    longitude   DECIMAL(9,6),
    holes       INTEGER NOT NULL DEFAULT 18 CHECK (holes IN (9, 18)),
    status      TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'verified')),
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_course_name_trgm ON "Course" USING GIN (name gin_trgm_ops);
CREATE INDEX idx_course_location  ON "Course" (latitude, longitude);

CREATE TABLE "Tee" (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id         UUID NOT NULL REFERENCES "Course"(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    color_hex         TEXT,
    rating_18         DECIMAL(4,1),
    slope_18          INTEGER CHECK (slope_18 BETWEEN 55 AND 155),
    rating_9_front    DECIMAL(4,1),
    slope_9_front     INTEGER CHECK (slope_9_front BETWEEN 55 AND 155),
    rating_9_back     DECIMAL(4,1),
    slope_9_back      INTEGER CHECK (slope_9_back BETWEEN 55 AND 155),
    yardage           INTEGER,
    par               INTEGER,
    hole_pars         INTEGER[],
    hole_yardages     INTEGER[],
    hole_handicaps    INTEGER[],  -- per-hole stroke-allocation ranks (1..18); null -> flat NDB-10 fallback
    created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tee_course_id ON "Tee" (course_id);

CREATE TABLE "Round" (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES "User"(id),
    course_id            UUID NOT NULL REFERENCES "Course"(id),
    tee_id               UUID REFERENCES "Tee"(id),
    played_on            DATE NOT NULL DEFAULT CURRENT_DATE,
    holes                INTEGER NOT NULL DEFAULT 18 CHECK (holes IN (9, 18)),
    scores               INTEGER[],
    total_score          INTEGER,
    front_nine           INTEGER,
    back_nine            INTEGER,
    score_differential   DECIMAL(5,1),
    scorecard_image_url  TEXT,
    ocr_raw              JSONB,
    ocr_confidence       DECIMAL(3,2),
    processing_status    TEXT DEFAULT 'pending',
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_round_user_id    ON "Round" (user_id);
CREATE INDEX idx_round_played_on  ON "Round" (played_on DESC);
CREATE INDEX idx_round_course_id  ON "Round" (course_id);

CREATE TABLE "HoleScore" (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id              UUID NOT NULL REFERENCES "Round"(id) ON DELETE CASCADE,
    hole_number           INTEGER NOT NULL CHECK (hole_number BETWEEN 1 AND 18),
    par                   INTEGER NOT NULL CHECK (par BETWEEN 3 AND 6),
    strokes               INTEGER CHECK (strokes >= 1),
    ocr_confidence        DECIMAL(3,2),
    manually_corrected    BOOLEAN DEFAULT false,
    UNIQUE (round_id, hole_number)
);

CREATE INDEX idx_hole_score_round_id ON "HoleScore" (round_id);

CREATE TABLE "HandicapSnapshot" (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID NOT NULL REFERENCES "User"(id),
    handicap_index         DECIMAL(4,1),
    rounds_used            INTEGER NOT NULL DEFAULT 0,
    differentials_used     JSONB,
    triggered_by_round_id  UUID REFERENCES "Round"(id) ON DELETE SET NULL,
    created_at             TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_handicap_snapshot_user_created
    ON "HandicapSnapshot" (user_id, created_at DESC);

COMMIT;
```

- [ ] **Step 2: Delete the inline golf `CREATE TABLE` block in `app.py`**

Open `backend/toms_gym/app.py`. Remove the three `try:` blocks that begin at approximately line 114 (`# Create GolfRound table if not exists`), line 148 (`# Create GolfHoleScore table if not exists`), and line 172 (`# Create GolfHandicap table if not exists`). Leave the preceding `BowlingResult` annotation migration and the surrounding outer try/except/finally intact. After deletion the golf-related sections should be gone entirely — migrations now live in `migrations/008_fairway_schema.sql` and are applied via `apply_schema.py`.

- [ ] **Step 3: Update migrations README**

Append to `backend/toms_gym/migrations/README.md`:

```markdown
## 008_fairway_schema.sql

Phase B of the Fairway migration. Drops flat `GolfRound`/`GolfHoleScore`/`GolfHandicap` and replaces them with `Course`, `Tee`, `Round`, `HoleScore`, `HandicapSnapshot`. Enables `pg_trgm` extension and adds a GIN trigram index on `Course.name`.

Greenfield — no data preservation. Rollback is `DROP TABLE` on the five new tables plus redeploy of the prior image.
```

- [ ] **Step 4: Apply migration against local Postgres**

Assumes local Postgres is running with the `toms_gym` database (see existing `apply_schema.py` pattern).

Run:
```bash
cd backend
venv/bin/python toms_gym/migrations/apply_schema.py toms_gym/migrations/008_fairway_schema.sql
```
Expected: no errors; `psql` shows the five new tables and the old three gone.

Verify:
```bash
psql toms_gym -c "\dt" | grep -E "Course|Tee|Round|HoleScore|HandicapSnapshot"
psql toms_gym -c "\dt" | grep -E "GolfRound|GolfHoleScore|GolfHandicap"
```
Expected: first command lists all five tables; second command lists nothing.

- [ ] **Step 4a: Wire 008 into the test DB bootstrap**

The pytest suite applies migrations via `backend/tests/init_db.py` (or `conftest.py`'s setup path). Update that file to apply `008_fairway_schema.sql` right after the existing migrations. Explicit sub-step so the doer does NOT leave this as a "later" TODO — Tasks 3 and 5 both hard-depend on the new tables existing in the test DB.

Edit `backend/tests/init_db.py` (or equivalent):

```python
MIGRATIONS_TO_APPLY = [
    # ...existing entries...
    "007_lifting_result.sql",
    "008_fairway_schema.sql",  # Phase B: Course/Tee/Round/HoleScore/HandicapSnapshot
]
```

Also ensure `CREATE EXTENSION IF NOT EXISTS pg_trgm;` is applied to the test DB before migration 008 runs (it's inside the migration, but the test-DB user may need superuser or the extension pre-created by the Postgres Docker image's init script).

Verify by running `cd backend && venv/bin/python -m pytest tests/test_auth_routes.py -v` — still passes (baseline untouched) AND `\dt` inside the test DB shows the 5 new tables.

- [ ] **Step 4b: Baseline the test suite BEFORE Phase B touches routes**

Before Task 4 starts the routes rewrite, capture the current green/red state of the full backend suite as a baseline. This lets Task 9 Step 2 distinguish "was already red on main" from "Phase B broke it".

```bash
cd backend && venv/bin/python -m pytest tests/ --tb=no -q 2>&1 | tee /tmp/phase-b-baseline.txt
```

Record pass/fail counts in a comment on the Task 1 commit or in the PR body. The handoff doc already names two known-flaky frontend specs; capturing a fresh backend baseline closes the loop.

- [ ] **Step 5: Commit**

```bash
git add backend/toms_gym/migrations/008_fairway_schema.sql \
        backend/toms_gym/migrations/README.md \
        backend/toms_gym/app.py
git commit -m "feat(golf): migration 008 — Fairway schema (drop + recreate)

Replaces flat GolfRound/GolfHoleScore/GolfHandicap with Course, Tee, Round,
HoleScore, HandicapSnapshot. Enables pg_trgm + trigram index on Course.name.
Removes the inline CREATE TABLE block previously in app.py.
Greenfield migration — no data preserved."
```

---

## Task 2: Handicap engine module + unit tests

**Files:**
- Create: `backend/toms_gym/services/__init__.py`
- Create: `backend/toms_gym/services/handicap.py`
- Create: `backend/tests/test_handicap.py`
- Create: `backend/tests/fixtures/whs_reference_cases.json`

- [ ] **Step 1: Write the WHS reference fixtures**

Create `backend/tests/fixtures/whs_reference_cases.json` with canonical cases derived from the spec's §8.1. Per-manager direction: top-level `"source"` key cites USGA Rules of Handicapping §5.2; parametric assertions (lowest-N + adjustment) must be bit-exact; numeric `expected_index` values are pinned-as-regression-values once the engine is implemented and can be corrected at PR review:

```json
{
  "source": "USGA Rules of Handicapping §5.2 (WHS adjustment table)",
  "establishing_zero_rounds": {
    "rounds": [],
    "expected_index": null,
    "expected_status": {"status": "establishing", "rounds_needed": 3}
  },
  "establishing_two_rounds": {
    "rounds": [
      {"adjusted_total": 92, "rating": 72.1, "slope": 128, "holes": 18},
      {"adjusted_total": 89, "rating": 72.1, "slope": 128, "holes": 18}
    ],
    "expected_index": null,
    "expected_status": {"status": "establishing", "rounds_needed": 1}
  },
  "three_rounds_lowest_minus_2": {
    "rounds": [
      {"adjusted_total": 85, "rating": 71.0, "slope": 124, "holes": 18},
      {"adjusted_total": 91, "rating": 71.0, "slope": 124, "holes": 18},
      {"adjusted_total": 88, "rating": 71.0, "slope": 124, "holes": 18}
    ],
    "expected_adjustment": -2.0
  },
  "four_rounds_lowest_minus_1": {"rounds_count": 4, "expected_adjustment": -1.0, "expected_diffs_used": 1},
  "five_rounds_lowest_zero":    {"rounds_count": 5, "expected_adjustment": 0,   "expected_diffs_used": 1},
  "six_rounds_avg_2_minus_1":   {"rounds_count": 6, "expected_adjustment": -1.0,"expected_diffs_used": 2},
  "nine_rounds_avg_3":          {"rounds_count": 9, "expected_adjustment": 0,   "expected_diffs_used": 3},
  "fifteen_rounds_avg_5":       {"rounds_count": 15,"expected_adjustment": 0,   "expected_diffs_used": 5},
  "twenty_rounds_avg_8":        {"rounds_count": 20,"expected_adjustment": 0,   "expected_diffs_used": 8},
  "twelve_month_cap": {
    "description": "Handicap cannot rise more than 5.0 above the 12-month low",
    "twelve_month_low": 8.0,
    "raw_new_index": 14.3,
    "expected_index": 13.0
  },
  "nine_hole_round_counts_as_half": {
    "description": "Nine-hole rounds use 9-hole rating/slope and count as 0.5 toward last 20",
    "rounds": [{"adjusted_total": 46, "rating": 35.2, "slope": 122, "holes": 9}]
  },
  "net_double_bogey_cap": {
    "description": "Strokes cap at par+2 (NDB, +strokes received). No handicap yet -> cap at 10.",
    "par_strokes": [[3, 9], [4, 12], [5, 11]],
    "expected_adjusted": [5, 6, 7]
  }
}
```

> Reviewer note: three_rounds case omits the full expected numeric index because it's sensitive to the adjusted-total inputs. The handicap engine test for that case should assert the adjustment and diffs-used path, then compute the index and pin it as a regression value once the module is implemented. Same approach for rounds-count-only cases.

- [ ] **Step 2: Write the failing unit tests**

Create `backend/tests/test_handicap.py`:

```python
"""Unit tests for the WHS handicap engine.

Tests operate on pure-Python helpers in `toms_gym.services.handicap`.
No DB touching — fixtures load canonical reference cases from JSON.

Reference: USGA Rules of Handicapping §5.2 (WHS adjustment table).
The parametric lowest-N + adjustment assertions must match §5.2 bit-exact;
numeric expected_index values are pinned-as-regression and cross-checked at PR review.
"""
import json
import pathlib

import pytest

from toms_gym.services.handicap import (
    net_double_bogey_cap,
    allocate_strokes,
    compute_differential,
    compute_handicap_index,
    apply_twelve_month_cap,
    HandicapResult,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "whs_reference_cases.json"


@pytest.fixture
def whs_cases():
    with open(FIXTURES) as f:
        return json.load(f)


# ---- Net-double-bogey cap ----

def test_ndb_caps_at_par_plus_two_plus_strokes_received():
    # Golfer with 9 handicap receives strokes on holes per allocation.
    # For a par-4 with 1 stroke received, NDB = par + 2 + 1 = 7.
    assert net_double_bogey_cap(par=4, strokes_received=1) == 7


def test_ndb_caps_at_10_when_no_handicap_yet():
    # Without a handicap, cap strokes at 10 (spec §B2).
    assert net_double_bogey_cap(par=3, strokes_received=None) == 10
    assert net_double_bogey_cap(par=5, strokes_received=None) == 10


def test_ndb_unchanged_when_strokes_below_cap():
    assert net_double_bogey_cap(par=4, strokes_received=0, actual=5) == 5


# ---- Stroke allocation ----

def test_allocate_strokes_none_when_no_index():
    # No handicap yet -> None -> caller must fall back to flat-10 NDB.
    assert allocate_strokes(None, [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18]) is None


def test_allocate_strokes_none_when_no_hole_handicaps():
    assert allocate_strokes(9.0, None) is None
    assert allocate_strokes(9.0, []) is None


def test_allocate_strokes_index_9_assigns_one_to_each_of_the_9_hardest():
    # Hole-handicap ranks 1..18 where hole i has rank (i+1). Hardest 9 = idx 0..8.
    ranks = list(range(1, 19))
    out = allocate_strokes(9.0, ranks)
    assert sum(out) == 9
    assert all(out[i] == 1 for i in range(9))
    assert all(out[i] == 0 for i in range(9, 18))


def test_allocate_strokes_wraps_around_past_18():
    # Index 20 -> all 18 holes get 1, plus 2 more on the two hardest.
    ranks = list(range(1, 19))
    out = allocate_strokes(20.0, ranks)
    assert sum(out) == 20
    assert out[0] == 2 and out[1] == 2
    assert all(out[i] == 1 for i in range(2, 18))


# ---- Differential ----

def test_differential_formula():
    # ((adjusted − rating − PCC) × 113) / slope ; PCC = 0 for MVP.
    diff = compute_differential(adjusted_total=85, rating=71.0, slope=124)
    assert diff == pytest.approx((85 - 71.0) * 113 / 124, rel=1e-6)


def test_nine_hole_differential_uses_nine_hole_values():
    # A nine-hole round uses the 9-hole rating/slope for differential.
    diff = compute_differential(adjusted_total=46, rating=35.2, slope=122)
    assert diff == pytest.approx((46 - 35.2) * 113 / 122, rel=1e-6)


# ---- Handicap index / WHS table ----

@pytest.mark.parametrize("n,diffs_used,adjustment", [
    # Every row of spec §B2 WHS table — one case per row, plus an extra >20 case.
    (3, 1, -2.0),  (4, 1, -1.0), (5, 1, 0),
    (6, 2, -1.0),  (7, 2, 0),    (8, 2, 0),
    (9, 3, 0),     (10, 3, 0),   (11, 3, 0),    # spec: 9–11 → lowest 3
    (12, 4, 0),    (13, 4, 0),   (14, 4, 0),    # spec: 12–14 → lowest 4
    (15, 5, 0),    (16, 5, 0),                  # spec: 15–16 → lowest 5
    (17, 6, 0),    (18, 6, 0),                  # spec: 17–18 → lowest 6
    (19, 7, 0),                                 # spec: 19   → lowest 7
    (20, 8, 0),    (25, 8, 0),                  # spec: 20+  → lowest 8
])
def test_whs_table_selects_correct_diffs_and_adjustment(n, diffs_used, adjustment):
    # Differentials [0, 1, 2, ..., n-1] — lowest `diffs_used` are picked.
    diffs = [float(i) for i in range(n)]
    result = compute_handicap_index(diffs, nine_hole_flags=[False] * n)
    assert isinstance(result, HandicapResult)
    assert result.diffs_used_count == diffs_used
    avg = sum(sorted(diffs)[:diffs_used]) / diffs_used
    # Expected raw index = (avg + adjustment) * 0.96 truncated to 1 decimal.
    import math
    expected = math.trunc((avg + adjustment) * 0.96 * 10) / 10
    assert result.handicap_index == pytest.approx(min(expected, 54.0), abs=0.05)


def test_establishing_with_zero_rounds_returns_null_index():
    result = compute_handicap_index([], nine_hole_flags=[])
    assert result.handicap_index is None
    assert result.status == "establishing"
    assert result.rounds_needed == 3


def test_establishing_with_two_rounds_returns_null_index():
    result = compute_handicap_index([12.3, 10.1], nine_hole_flags=[False, False])
    assert result.handicap_index is None
    assert result.status == "establishing"
    assert result.rounds_needed == 1


def test_handicap_index_capped_at_54():
    # Even with very high differentials, index must not exceed 54.0.
    diffs = [80.0] * 3
    result = compute_handicap_index(diffs, nine_hole_flags=[False] * 3)
    assert result.handicap_index <= 54.0


# ---- 12-month low cap ----

def test_twelve_month_cap_limits_rise_to_5_above_low():
    # 12-month low is 8.0; new raw index is 14.3 → capped at 13.0.
    capped = apply_twelve_month_cap(new_index=14.3, twelve_month_low=8.0)
    assert capped == 13.0


def test_twelve_month_cap_does_not_lower_handicap():
    # New index of 5.0 vs low of 8.0 — cap has no effect.
    assert apply_twelve_month_cap(new_index=5.0, twelve_month_low=8.0) == 5.0


def test_twelve_month_cap_noop_when_no_history():
    assert apply_twelve_month_cap(new_index=12.0, twelve_month_low=None) == 12.0


# ---- 9-hole counts as 0.5 toward last 20 ----

def test_nine_hole_counts_as_half_round():
    # 6 nine-hole diffs → equivalent to 3 full rounds → should use WHS(3) row.
    diffs = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    result = compute_handicap_index(diffs, nine_hole_flags=[True] * 6)
    # Effective round count = 3 → diffs_used = 1, adjustment = -2.0.
    assert result.diffs_used_count == 1
    assert result.adjustment == -2.0


def test_mixed_eighteen_and_nine_hole_count():
    # 2 eighteen + 2 nine = 2 + 1 = 3 effective rounds.
    diffs = [12.0, 10.0, 11.0, 9.0]
    result = compute_handicap_index(
        diffs, nine_hole_flags=[False, False, True, True]
    )
    assert result.diffs_used_count == 1
    assert result.adjustment == -2.0
```

- [ ] **Step 3: Run the tests — expect ImportError**

Run:
```bash
cd backend
venv/bin/python -m pytest tests/test_handicap.py -x 2>&1 | head -30
```
Expected: collection fails with `ImportError: cannot import name 'net_double_bogey_cap'` (module not written yet).

- [ ] **Step 4: Implement the handicap module**

Create `backend/toms_gym/services/__init__.py` (empty).

Create `backend/toms_gym/services/handicap.py`:

```python
"""WHS handicap engine — pure functions over differentials.

All functions here are side-effect free and DB-free so they can be unit-tested
in isolation. The route layer is responsible for fetching rounds, calling these
helpers, and writing HandicapSnapshot rows.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional


# rounds_available -> (differentials_to_use, adjustment)
# Matches spec §B2 WHS table exactly: 9-11 → lowest 3, 12-14 → lowest 4,
# 15-16 → lowest 5, 17-18 → lowest 6, 19 → lowest 7, 20+ → lowest 8.
WHS_TABLE = {
    3:  (1, -2.0), 4:  (1, -1.0), 5:  (1,  0),
    6:  (2, -1.0), 7:  (2,  0),   8:  (2,  0),
    9:  (3,  0),  10:  (3,  0),  11:  (3,  0),
    12: (4,  0),  13:  (4,  0),  14:  (4,  0),
    15: (5,  0),  16:  (5,  0),
    17: (6,  0),  18:  (6,  0),
    19: (7,  0),
    20: (8,  0),
}
MAX_INDEX = 54.0
PCC = 0  # MVP: Playing Conditions Calculation disabled.


@dataclass
class HandicapResult:
    handicap_index: Optional[float]
    diffs_used_count: int
    adjustment: float
    status: str  # "active" | "establishing"
    rounds_needed: int  # 0 when active


def net_double_bogey_cap(par: int, strokes_received: Optional[int] = None,
                        actual: Optional[int] = None) -> int:
    """Cap strokes at NDB (par + 2 + strokes received on that hole).

    If the user has no handicap yet, cap at a flat 10 per spec §B2.
    When `actual` is provided, returns min(actual, cap).
    """
    if strokes_received is None:
        cap = 10
    else:
        cap = par + 2 + strokes_received
    if actual is None:
        return cap
    return min(actual, cap)


def compute_differential(adjusted_total: float, rating: float, slope: int) -> float:
    """((adjusted − rating − PCC) × 113) / slope.

    Works for both 18-hole and 9-hole rounds — the caller chooses the right
    rating/slope values for the round length.
    """
    return ((adjusted_total - rating - PCC) * 113) / slope


def _effective_round_count(nine_hole_flags: List[bool]) -> int:
    """9-hole rounds count as 0.5 toward the last-20 pool. Integer floor."""
    full = sum(1 for f in nine_hole_flags if not f)
    nines = sum(1 for f in nine_hole_flags if f)
    return full + nines // 2


def compute_handicap_index(
    differentials: List[float],
    nine_hole_flags: List[bool],
) -> HandicapResult:
    """Compute WHS index from the user's last-20 differentials.

    Inputs are expected to be ordered newest-first by the caller; this function
    only cares about the values themselves (WHS picks lowest N).
    """
    assert len(differentials) == len(nine_hole_flags), "length mismatch"
    effective = _effective_round_count(nine_hole_flags)

    if effective < 3:
        return HandicapResult(
            handicap_index=None,
            diffs_used_count=0,
            adjustment=0.0,
            status="establishing",
            rounds_needed=3 - effective,
        )

    lookup_n = min(effective, 20)
    diffs_to_use, adjustment = WHS_TABLE[lookup_n]
    best = sorted(differentials)[:diffs_to_use]
    avg = sum(best) / diffs_to_use
    raw = math.trunc((avg + adjustment) * 0.96 * 10) / 10
    index = min(raw, MAX_INDEX)

    return HandicapResult(
        handicap_index=index,
        diffs_used_count=diffs_to_use,
        adjustment=adjustment,
        status="active",
        rounds_needed=0,
    )


def allocate_strokes(
    handicap_index: Optional[float],
    hole_handicaps: Optional[List[int]],
) -> Optional[List[int]]:
    """Return per-hole strokes received given an 18-slot hole-handicap array.

    `hole_handicaps` is the usual 1..18 ranking where rank 1 is hardest.
    Total strokes received = floor(handicap_index); allocated one-per-hole by
    rank. Handicap > 18 wraps around (hole rank 1 gets 2 strokes before rank 2
    gets a second stroke, etc.).

    Returns None when either input is missing — caller should fall back to
    the flat NDB-10 cap per spec §B2.
    """
    if handicap_index is None or not hole_handicaps or len(hole_handicaps) != 18:
        return None
    total = int(math.floor(handicap_index))
    out = [0] * 18
    # rank 1 is hardest; assign strokes starting from rank 1.
    order = sorted(range(18), key=lambda i: hole_handicaps[i])
    for k in range(total):
        out[order[k % 18]] += 1
    return out


def apply_twelve_month_cap(
    new_index: float, twelve_month_low: Optional[float]
) -> float:
    """Cap handicap rise at 5.0 above the user's 12-month low.

    The cap never pushes the index down; only prevents it rising too far.
    """
    if twelve_month_low is None:
        return new_index
    ceiling = twelve_month_low + 5.0
    return min(new_index, ceiling)
```

- [ ] **Step 5: Run the tests — expect green**

Run:
```bash
cd backend
venv/bin/python -m pytest tests/test_handicap.py -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/toms_gym/services/__init__.py \
        backend/toms_gym/services/handicap.py \
        backend/tests/test_handicap.py \
        backend/tests/fixtures/whs_reference_cases.json
git commit -m "feat(golf): WHS handicap engine with NDB + establishing + 12-mo cap"
```

---

## Task 3: Courses service — fuzzy match + tee match/create

**Files:**
- Create: `backend/toms_gym/services/courses.py`
- Create: `backend/tests/test_courses_service.py`

**Parallel:** Runs in Wave P2 alongside Task 4 (different files). Task 4's upload handler imports this module, so Task 3's public signatures must be stable before Task 4 starts implementation — land the test file first so the signatures are nailed down.

- [ ] **Step 1: Write the failing integration tests**

Create `backend/tests/test_courses_service.py`:

```python
"""Integration tests for the courses service.

These hit a real Postgres (via the conftest `db_session` fixture) so we can
exercise pg_trgm similarity and foreign-key behavior end-to-end.
"""
import pytest

from toms_gym.services.courses import (
    match_or_create_course,
    match_or_create_tee,
    search_courses,
    CourseMatch,
    TeeMatch,
)


@pytest.fixture
def seeded_course(db_session):
    course_id = db_session.execute(
        """INSERT INTO "Course" (name, city, state, status, latitude, longitude)
           VALUES ('Pebble Beach Golf Links', 'Pebble Beach', 'CA', 'verified',
                   36.5681, -121.9497)
           RETURNING id""").scalar()
    db_session.execute(
        """INSERT INTO "Tee" (course_id, name, color_hex, rating_18, slope_18, par)
           VALUES (:cid, 'Blue', '#185FA5', 72.7, 138, 72)""",
        {"cid": course_id}
    )
    db_session.commit()
    return course_id


def test_fuzzy_match_course_tolerates_typos(db_session, seeded_course):
    match = match_or_create_course(db_session, name="Peble Beach Golf Lnks", near=None)
    assert isinstance(match, CourseMatch)
    assert match.course_id == seeded_course
    assert match.created is False
    assert match.similarity >= 0.4


def test_course_match_creates_pending_on_miss(db_session):
    match = match_or_create_course(
        db_session, name="Totally Made Up Course XYZ", near=None
    )
    assert match.created is True
    assert match.status == "pending"


def test_geo_filter_prefers_nearby_course(db_session, seeded_course):
    # Seed a second Pebble-named course far away.
    far_id = db_session.execute(
        """INSERT INTO "Course" (name, latitude, longitude, status)
           VALUES ('Pebble Beach Club', 40.0, -100.0, 'verified') RETURNING id"""
    ).scalar()
    db_session.commit()

    match = match_or_create_course(
        db_session, name="Pebble Beach", near=(36.5681, -121.9497)
    )
    assert match.course_id == seeded_course
    assert match.course_id != far_id


def test_tee_match_by_name(db_session, seeded_course):
    tee = match_or_create_tee(
        db_session, course_id=seeded_course, name="Blue",
        rating=None, slope=None
    )
    assert isinstance(tee, TeeMatch)
    assert tee.created is False


def test_tee_creates_when_rating_slope_present(db_session, seeded_course):
    tee = match_or_create_tee(
        db_session, course_id=seeded_course, name="White",
        rating=70.2, slope=131
    )
    assert tee.created is True


def test_tee_needs_tee_when_no_match_and_no_rating(db_session, seeded_course):
    tee = match_or_create_tee(
        db_session, course_id=seeded_course, name="Unknown Tee",
        rating=None, slope=None
    )
    assert tee.created is False
    assert tee.tee_id is None
    assert tee.needs_tee is True


def test_search_courses_returns_top_matches(db_session, seeded_course):
    results = search_courses(db_session, q="Pebble", near=None, limit=5)
    assert len(results) >= 1
    assert any(r["id"] == str(seeded_course) for r in results)
```

- [ ] **Step 2: Run tests — expect ImportError**

Run:
```bash
cd backend
venv/bin/python -m pytest tests/test_courses_service.py -x 2>&1 | head -30
```
Expected: ImportError (module missing).

- [ ] **Step 3: Implement `services/courses.py`**

```python
"""Course + Tee matching service.

`match_or_create_course` fuzzy-matches on name via pg_trgm similarity and
optionally biases toward courses near a given lat/lng. On miss, inserts a new
Course with status='pending'.

`match_or_create_tee` tries an exact-name match on the given course's tees;
creates a new Tee when rating/slope are provided; otherwise signals that the
review UI must prompt the user.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict

import sqlalchemy

SIMILARITY_THRESHOLD = 0.4      # pg_trgm similarity — tuned for typos.
GEO_RADIUS_DEGREES   = 0.5      # ~55 km; rough bbox prefilter before sim.


@dataclass
class CourseMatch:
    course_id: str
    created: bool
    status: str
    similarity: float  # 1.0 when created


@dataclass
class TeeMatch:
    tee_id: Optional[str]
    created: bool
    needs_tee: bool  # True when no match and no rating/slope to create one


def match_or_create_course(
    session,
    name: str,
    near: Optional[Tuple[float, float]],
) -> CourseMatch:
    """Fuzzy-match by name, optionally bias by lat/lng. Create pending on miss."""
    params = {"name": name, "threshold": SIMILARITY_THRESHOLD}
    geo_clause = ""
    if near:
        lat, lng = near
        params.update({"lat": lat, "lng": lng, "rad": GEO_RADIUS_DEGREES})
        # Prefer nearby courses: filter to bbox first (cheap), then rank by sim.
        geo_clause = (
            " AND latitude BETWEEN :lat - :rad AND :lat + :rad"
            " AND longitude BETWEEN :lng - :rad AND :lng + :rad"
        )

    row = session.execute(sqlalchemy.text(f"""
        SELECT id, status, similarity(name, :name) AS sim
        FROM "Course"
        WHERE similarity(name, :name) > :threshold {geo_clause}
        ORDER BY sim DESC
        LIMIT 1
    """), params).fetchone()

    if row:
        return CourseMatch(
            course_id=str(row[0]), created=False,
            status=row[1], similarity=float(row[2]),
        )

    # Create pending course.
    insert_row = session.execute(sqlalchemy.text("""
        INSERT INTO "Course" (name, latitude, longitude, status)
        VALUES (:name, :lat, :lng, 'pending') RETURNING id
    """), {
        "name": name,
        "lat": near[0] if near else None,
        "lng": near[1] if near else None,
    }).fetchone()
    session.commit()
    return CourseMatch(
        course_id=str(insert_row[0]), created=True,
        status="pending", similarity=1.0,
    )


def match_or_create_tee(
    session,
    course_id: str,
    name: str,
    rating: Optional[float],
    slope: Optional[int],
) -> TeeMatch:
    """Exact-name match first; create when rating/slope present; else signal."""
    row = session.execute(sqlalchemy.text("""
        SELECT id FROM "Tee"
        WHERE course_id = :cid AND LOWER(name) = LOWER(:name)
        LIMIT 1
    """), {"cid": course_id, "name": name}).fetchone()
    if row:
        return TeeMatch(tee_id=str(row[0]), created=False, needs_tee=False)

    if rating is not None and slope is not None:
        new_row = session.execute(sqlalchemy.text("""
            INSERT INTO "Tee" (course_id, name, rating_18, slope_18)
            VALUES (:cid, :name, :rating, :slope) RETURNING id
        """), {"cid": course_id, "name": name, "rating": rating, "slope": slope}).fetchone()
        session.commit()
        return TeeMatch(tee_id=str(new_row[0]), created=True, needs_tee=False)

    return TeeMatch(tee_id=None, created=False, needs_tee=True)


def search_courses(session, q: str, near: Optional[Tuple[float, float]],
                   limit: int = 10) -> List[Dict]:
    params = {"q": q, "threshold": SIMILARITY_THRESHOLD, "limit": limit}
    geo_clause = ""
    if near:
        lat, lng = near
        params.update({"lat": lat, "lng": lng, "rad": GEO_RADIUS_DEGREES})
        geo_clause = (
            " AND latitude BETWEEN :lat - :rad AND :lat + :rad"
            " AND longitude BETWEEN :lng - :rad AND :lng + :rad"
        )
    rows = session.execute(sqlalchemy.text(f"""
        SELECT id, name, city, state, country, latitude, longitude, status,
               similarity(name, :q) AS sim
        FROM "Course"
        WHERE similarity(name, :q) > :threshold {geo_clause}
        ORDER BY sim DESC
        LIMIT :limit
    """), params).fetchall()
    return [
        {
            "id": str(r[0]), "name": r[1], "city": r[2], "state": r[3],
            "country": r[4], "latitude": float(r[5]) if r[5] else None,
            "longitude": float(r[6]) if r[6] else None,
            "status": r[7], "similarity": float(r[8]),
        }
        for r in rows
    ]
```

- [ ] **Step 4: Run tests — expect green**

Run:
```bash
cd backend
venv/bin/python -m pytest tests/test_courses_service.py -v
```
Expected: all tests pass against a local Postgres with migration 008 applied.

If `conftest.py` doesn't yet provide a `db_session` fixture with `pg_trgm` enabled, extend it in this same task (add `CREATE EXTENSION IF NOT EXISTS pg_trgm;` to the per-test setup).

- [ ] **Step 5: Commit**

```bash
git add backend/toms_gym/services/courses.py \
        backend/tests/test_courses_service.py \
        backend/tests/conftest.py
git commit -m "feat(golf): courses service — pg_trgm fuzzy match + tee match/create"
```

---

## Task 4: Rewrite `golf_routes.py` — new shapes + delegation + new endpoints

**Files:**
- Modify: `backend/toms_gym/routes/golf_routes.py`

**Single-agent task.** The file is 1075 lines and every route touches shared helpers. Do not parallelize within this task — do the sub-steps sequentially in one commit cluster.

**Depends on:** Task 2 (`services.handicap`), Task 3 (`services.courses`).

- [ ] **Step 1: Replace `_recalculate_handicap` with delegation to `services.handicap`**

Delete the local `_recalculate_handicap` (lines ~329–383) and the module-level `WHS_TABLE` constant (lines ~58–65). Add:

```python
from toms_gym.services.handicap import (
    compute_differential,
    compute_handicap_index,
    apply_twelve_month_cap,
    net_double_bogey_cap,
)
from toms_gym.services.courses import (
    match_or_create_course,
    match_or_create_tee,
    search_courses as courses_search,
)
```

Write a new `_recalculate_handicap(session, user_id, triggered_by_round_id)`. Exact query + flow:

```python
rows = session.execute(sqlalchemy.text('''
    SELECT score_differential, holes
    FROM "Round"
    WHERE user_id = :uid
      AND processing_status = 'confirmed'
      AND score_differential IS NOT NULL
    ORDER BY played_on DESC, created_at DESC
    LIMIT 20
'''), {"uid": user_id}).fetchall()

diffs           = [float(r[0]) for r in rows]
nine_hole_flags = [r[1] == 9    for r in rows]

result = compute_handicap_index(diffs, nine_hole_flags)

final_index = result.handicap_index
if result.status == "active":
    low_row = session.execute(sqlalchemy.text('''
        SELECT MIN(handicap_index) FROM "HandicapSnapshot"
        WHERE user_id = :uid
          AND handicap_index IS NOT NULL
          AND created_at >= NOW() - INTERVAL '12 months'
    '''), {"uid": user_id}).fetchone()
    twelve_month_low = float(low_row[0]) if low_row and low_row[0] is not None else None
    final_index = apply_twelve_month_cap(final_index, twelve_month_low)

# Exact differentials used in this calc (lowest-N from the pool).
diffs_used = sorted(diffs)[:result.diffs_used_count] if result.diffs_used_count else []

session.execute(sqlalchemy.text('''
    INSERT INTO "HandicapSnapshot"
      (id, user_id, handicap_index, rounds_used, differentials_used,
       triggered_by_round_id, created_at)
    VALUES
      (gen_random_uuid(), :uid, :idx, :n, :used, :trig, NOW())
'''), {
    "uid": user_id,
    "idx": final_index,
    "n":   len(diffs),
    "used": json.dumps(diffs_used),
    "trig": triggered_by_round_id,
})
session.commit()
return final_index
```

Contract requirements:
- **One INSERT per recalc**, never an UPSERT — the snapshot table is an append-only history (`GET /users/:id/handicap/history` reads the full series; current index = latest row).
- `differentials_used` column is populated with the exact list passed into the average so it is auditable per row.
- `rounds_used` = total pool size (`len(diffs)`), not `diffs_used_count` — the spec distinguishes "how many rounds we have" from "how many we picked".
- Called from `PUT /golf/round/:id/scores`, `DELETE /golf/round/:id`, and Task 4 Step 4 (after a successful tee edit that changes the differential).

- [ ] **Step 2: Update `upload_scorecard` to resolve Course/Tee**

After OCR and player selection but before creating the `Round` row:
1. Read `course_name` + optional `latitude`/`longitude` from the form (document new optional fields in the docstring).
2. Call `match_or_create_course(session, course_name, near=(lat, lng) if both present else None)`.
3. Read optional `tee_name`, `tee_rating`, `tee_slope` from the form. Call `match_or_create_tee(...)`. If `tee_match.needs_tee` is True, proceed anyway (review page will handle selection).
4. Insert a `Round` with `course_id` + `tee_id` instead of flat `course_name`/`slope_rating`/`course_rating`. `total_score`, `front_nine`, `back_nine`, `scores` remain null until the review save. **`played_on` defaults to `CURRENT_DATE` via the column default — the upload handler does NOT read an override from the form in Phase B** (document this in the route docstring so a future phase can add a date picker).
5. Response JSON:

```json
{
  "round_id": "...",
  "user_id": "...",
  "processing_status": "ocr_complete",
  "ocr_confidence": 0.87,
  "course": {"id": "...", "name": "Pebble Beach", "status": "verified"},
  "tee":    {"id": "...", "name": "Blue", "rating_18": 72.7, "slope_18": 138, "needs_tee": false},
  "holes": [...],
  "detected_players": [...],
  "scorecard_image_url": "..."
}
```

- [ ] **Step 3: Rewrite `GET /golf/round/<round_id>`**

Join `Round` + `Course` + `Tee`; return:

```json
{
  "id": "...",
  "user_id": "...",
  "played_on": "2026-04-18",
  "holes_count": 18,
  "scores": [4, 5, ...],
  "total_score": 87,
  "front_nine": 44,
  "back_nine": 43,
  "score_differential": 12.8,
  "scorecard_image_url": "...",
  "ocr_confidence": 0.87,
  "processing_status": "confirmed",
  "course": {"id": "...", "name": "...", "city": "...", "status": "verified"},
  "tee":    {"id": "...", "name": "Blue", "color_hex": "#...", "rating_18": 72.7, "slope_18": 138, "yardage": 6803},
  "holes":  [{"hole_number": 1, "par": 4, "strokes": 5, "ocr_confidence": 0.9, "manually_corrected": false}, ...],
  "detected_players": [...]
}
```

- [ ] **Step 4: Rewrite `PUT /golf/round/<round_id>/scores`**

Accept the confirmed 18 holes + optional `tee_id` (user changed the tee) + optional overrides `{tee_rating, tee_slope, tee_yardage}` (user edited the picked tee's values).

Logic — explicit per-hole NDB wiring, no hand-waving:

1. If `tee_id` changed, update `Round.tee_id`. Re-fetch tee for rating/slope/yardage/hole_handicaps.
2. If tee override values are present, update that `Tee` row (rating_18/slope_18/yardage).
3. Fetch user's current handicap index from `HandicapSnapshot` (latest; may be None).
4. **Stroke allocation + NDB per hole:**
   ```python
   strokes_received = allocate_strokes(current_index, tee.hole_handicaps)
   adjusted_per_hole = []
   for i, hole in enumerate(holes_submitted):          # 0..17, each {par, strokes}
       rec = strokes_received[i] if strokes_received else None
       adjusted_per_hole.append(
           net_double_bogey_cap(hole['par'], rec, actual=hole['strokes'])
       )
   adjusted_total = sum(adjusted_per_hole)
   ```
   - If `strokes_received` is None (no handicap yet OR tee has no `hole_handicaps` array), every hole falls back to the flat-10 cap per spec §B2 — `net_double_bogey_cap` already returns `min(actual, 10)` in that case.
5. Compute `total_score = sum(raw strokes)`, `front_nine`, `back_nine`. Compute `score_differential = compute_differential(adjusted_total, tee.rating_18, tee.slope_18)`.
6. Update `Round` row (store `total_score`, `front_nine`, `back_nine`, `score_differential`, `processing_status='confirmed'`, `scores` array). Upsert all 18 `HoleScore` rows with `manually_corrected=true` where strokes changed.
7. Call `_recalculate_handicap(session, user_id, round_id)` — this writes a new `HandicapSnapshot`.
8. Return updated round JSON + new handicap index (read back from the snapshot just written).

**Hole-handicaps availability trade-off (flagged for reviewer):** Phase B stores `hole_handicaps INTEGER[]` on `Tee` (nullable). If the user uploads a scorecard where hole handicap allocations aren't captured (the common case right now — OCR doesn't yet extract them), the column stays null and the NDB cap degrades to a flat 10. That is an accepted shortcut for Phase B; a future phase can add a handicap-allocation row to the scorecard OCR parser or let the user enter it on the tee-picker drawer.

- [ ] **Step 5: Rewrite `GET /golf/rounds?user_id=`**

Return `[{..., course: {...}, tee: {...}}, ...]`. Each round includes its 18 holes.

- [ ] **Step 6: Rewrite `GET /golf/handicap/<user_id>` + `DELETE /golf/round/<round_id>`**

`GET /handicap/:user_id` reads latest `HandicapSnapshot`. On `DELETE` of a round, also recalc handicap (inserts a new snapshot).

- [ ] **Step 7: New endpoint `GET /golf/courses?q=&near=`**

```python
@golf_bp.route('/courses', methods=['GET'])
def list_courses():
    q = request.args.get('q', '').strip()
    near = request.args.get('near')
    near_tuple = None
    if near:
        try:
            lat_s, lng_s = near.split(',')
            near_tuple = (float(lat_s), float(lng_s))
        except (ValueError, TypeError):
            return jsonify({'error': 'near must be "lat,lng"'}), 400
    if not q:
        return jsonify({'courses': []})
    session = get_db_connection()
    try:
        courses = courses_search(session, q=q, near=near_tuple, limit=10)
        return jsonify({'courses': courses})
    finally:
        session.close()
```

- [ ] **Step 8: New endpoint `POST /golf/courses`**

Accepts `{name, city, state, country, latitude, longitude, holes}`; inserts with `status='pending'`; returns `{course: {...}}`.

- [ ] **Step 9: New endpoint `GET /golf/users/<user_id>/handicap/history`**

Returns `[{handicap_index, created_at, rounds_used}, ...]` ordered by `created_at DESC` (or ASC — pick whichever the Phase D chart prefers; document the choice in the route docstring).

- [ ] **Step 10: Update `GET /golf/leaderboard`**

Pull the **latest** `HandicapSnapshot` per user and compute an explicit monthly delta.

```sql
WITH latest AS (
  SELECT DISTINCT ON (user_id) user_id, handicap_index, created_at
  FROM "HandicapSnapshot"
  WHERE handicap_index IS NOT NULL
  ORDER BY user_id, created_at DESC
),
past AS (
  -- Pick the most recent snapshot that is at least 30 days old
  -- but no older than 60 days, so the delta is over a "roughly monthly" window.
  SELECT DISTINCT ON (user_id) user_id, handicap_index
  FROM "HandicapSnapshot"
  WHERE handicap_index IS NOT NULL
    AND created_at <= NOW() - INTERVAL '30 days'
    AND created_at >= NOW() - INTERVAL '60 days'
  ORDER BY user_id, created_at DESC
)
SELECT l.user_id, u.name, l.handicap_index,
       (l.handicap_index - p.handicap_index) AS monthly_delta
FROM latest l
JOIN "User" u ON u.id = l.user_id
LEFT JOIN past p ON p.user_id = l.user_id
ORDER BY l.handicap_index ASC;
```

Rules:
- `monthly_delta` is `latest − past`. Negative delta = improvement (handicap went down). Positive = regression.
- `monthly_delta` is `NULL` when the user has no snapshot in the 30–60-day window. Don't synthesize a fake zero; the frontend renders "—" on null.
- Sort by `handicap_index ASC` (lowest = best golfer at the top) to match Phase A leaderboard ordering.

- [ ] **Step 11: Run full backend test suite**

Run:
```bash
cd backend
venv/bin/python -m pytest tests/test_handicap.py tests/test_courses_service.py tests/test_golf_parser.py tests/test_auth_routes.py tests/test_user_routes.py -v
```
Expected: all currently-green tests remain green; handicap + courses services green. `test_golf_parser.py` may need updates if it asserted against the old response shape — those get extended in Task 5.

- [ ] **Step 12: Commit**

```bash
git add backend/toms_gym/routes/golf_routes.py
git commit -m "feat(golf): re-plumb routes to Course/Tee/Round/HandicapSnapshot

- Response shapes nest course/tee instead of flat fields.
- _recalculate_handicap delegates to services.handicap (adds NDB + 12-mo cap).
- Upload resolves course/tee via services.courses (pg_trgm fuzzy match).
- New endpoints: GET /golf/courses, POST /golf/courses,
  GET /golf/users/:id/handicap/history.
- Leaderboard pulls from latest HandicapSnapshot."
```

---

## Task 5: Extend `test_golf_parser.py` with course/tee matching integration tests

**Files:**
- Modify: `backend/tests/test_golf_parser.py`

**Depends on:** Task 4 (upload handler wiring).

**Parallel:** Safe to run alongside frontend tasks 6/7 — touches only backend tests.

**Rate-limit handling (per handoff caveat):** `/golf/upload` is `@rate_limit('10/hour')`. The `rate_limit` decorator in `backend/toms_gym/security.py:118` already checks `current_app.config['TESTING']` and is a no-op when True. The existing `tests/conftest.py` already sets `TESTING=True` (line 27). Confirm that contract in Step 1 (one-liner assertion), then use the real route in the integration tests — no stubbing needed for rate-limit bypass.

If the conftest is refactored and the TESTING flag is lost, these tests will break fast (429 on the 11th case). The first step below asserts the config state to fail loudly if that regression happens.

- [ ] **Step 1: Add integration tests that exercise the upload path**

```python
def test_testing_config_disables_rate_limit(app):
    # Sanity: without this, all tests below would 429 on the 11th run.
    assert app.config['TESTING'] is True
```

Stub `toms_gym.routes.golf_routes._run_ocr` to return the fixture in `tests/fixtures/golf_scorecard_ocr.json`. Seed a Course + Tee, then post to `/golf/upload` and assert:

```python
def test_upload_resolves_existing_course_by_name(client, seeded_course, stubbed_ocr):
    resp = client.post('/golf/upload', data={
        'image': (open('tests/fixtures/golf_scorecard.jpg', 'rb'), 'scorecard.jpg'),
        'course_name': 'Peble Beach Golf Lnks',  # typo
        'slope_rating': '138',
        'course_rating': '72.7',
        'email': 'matcher@test.com',
    }, content_type='multipart/form-data')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['course']['id'] == seeded_course
    assert body['tee']['id'] is not None
    assert body['tee']['needs_tee'] is False


def test_upload_creates_pending_course_on_miss(client, stubbed_ocr):
    resp = client.post('/golf/upload', data={
        'image': (open('tests/fixtures/golf_scorecard.jpg', 'rb'), 'scorecard.jpg'),
        'course_name': 'Brand New Made Up Course',
        'slope_rating': '120', 'course_rating': '70.0',
        'email': 'new-course@test.com',
    }, content_type='multipart/form-data')
    assert resp.status_code == 200
    assert resp.get_json()['course']['status'] == 'pending'


def test_upload_marks_needs_tee_when_no_tee_on_course(...):
    # Seed a course with zero tees; upload without rating/slope → needs_tee=true.
    ...
```

- [ ] **Step 2: Run the extended suite**

```bash
cd backend
venv/bin/python -m pytest tests/test_golf_parser.py -v
```
Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_golf_parser.py
git commit -m "test(golf): course/tee matching integration tests on upload path"
```

---

## Task 6: Frontend data-shape swap — types + read-only pages

**Files:**
- Modify: `frontend/src/lib/api.ts` (or add `frontend/src/lib/golf-types.ts` alongside)
- Modify: `frontend/src/pages/GolfRound.tsx`
- Modify: `frontend/src/pages/GolfProfile.tsx`
- Modify: `frontend/src/pages/GolfLeaderboard.tsx`

**Parallel:** Runs in Wave P3 alongside Task 7. This task owns `api.ts`; Task 7 reads it. Merge this task's commit before Task 7 starts implementation.

- [ ] **Step 1: Define the new types in `api.ts`**

Add to `frontend/src/lib/api.ts`:

```ts
export interface GolfCourse {
  id: string;
  name: string;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  status: "verified" | "pending";
}

export interface GolfTee {
  id: string | null;
  name: string;
  color_hex?: string | null;
  rating_18?: number | null;
  slope_18?: number | null;
  yardage?: number | null;
  par?: number | null;
  needs_tee?: boolean;
}

export interface GolfHole {
  hole_number: number;
  par: number;
  strokes: number | null;
  ocr_confidence: number | null;
  manually_corrected: boolean;
}

export interface GolfRoundDetail {
  id: string;
  user_id: string;
  played_on: string;
  holes_count: 9 | 18;
  scores: (number | null)[];
  total_score: number | null;
  front_nine: number | null;
  back_nine: number | null;
  score_differential: number | null;
  scorecard_image_url: string | null;
  ocr_confidence: number | null;
  processing_status: string;
  course: GolfCourse;
  tee: GolfTee;
  holes: GolfHole[];
  detected_players?: Array<{ name: string; holes: GolfHole[] }>;
}

export interface HandicapHistoryPoint {
  handicap_index: number | null;
  rounds_used: number;
  created_at: string;
}

export async function searchCourses(
  q: string,
  near?: { lat: number; lng: number }
): Promise<GolfCourse[]> {
  const params = new URLSearchParams({ q });
  if (near) params.set("near", `${near.lat},${near.lng}`);
  const res = await fetch(`${API_URL}/golf/courses?${params.toString()}`);
  if (!res.ok) throw new Error(`searchCourses ${res.status}`);
  const body = await res.json();
  return body.courses as GolfCourse[];
}

export async function createCourse(
  input: Partial<GolfCourse> & { name: string }
): Promise<GolfCourse> {
  const res = await fetch(`${API_URL}/golf/courses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`createCourse ${res.status}`);
  const body = await res.json();
  return body.course as GolfCourse;
}

export async function getHandicapHistory(
  userId: string
): Promise<HandicapHistoryPoint[]> {
  const res = await fetch(`${API_URL}/golf/users/${userId}/handicap/history`);
  if (!res.ok) throw new Error(`getHandicapHistory ${res.status}`);
  return (await res.json()) as HandicapHistoryPoint[];
}
```

Update existing `fetchRound`, `fetchProfile`, `updateRoundScores` signatures to return/accept these types. **Important:** do not change Phase A presentational component prop shapes — map shapes inside the page file.

- [ ] **Step 2: Write failing tests (type-level) in `frontend/src/lib/__tests__/api.test.ts`**

```ts
import { GolfRoundDetail, GolfCourse } from "../api";

// Compile-time assertion: nested course object must be present.
const sample: GolfRoundDetail = {
  id: "x",
  user_id: "u",
  played_on: "2026-04-18",
  holes_count: 18,
  scores: [],
  total_score: null,
  front_nine: null,
  back_nine: null,
  score_differential: null,
  scorecard_image_url: null,
  ocr_confidence: null,
  processing_status: "ocr_complete",
  course: { id: "c", name: "Test", status: "pending" },
  tee: { id: null, name: "Blue", needs_tee: true },
  holes: [],
};
```

Run: `cd frontend && npx tsc --noEmit`
Expected: compiles (testing the types, not behavior).

- [ ] **Step 3: Re-plumb `GolfRound.tsx`, `GolfProfile.tsx`, `GolfLeaderboard.tsx`**

Replace references to `round.course_name` → `round.course.name`, `round.slope_rating` → `round.tee.slope_18`, `round.course_rating` → `round.tee.rating_18`. **Phase A JSX and CSS classes unchanged.**

For `GolfProfile.tsx`, the handicap card fetches `getHandicapHistory(userId)` and renders the latest value.

- [ ] **Step 4: Typecheck + build**

```bash
cd frontend && npx tsc --noEmit && npm run build
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts \
        frontend/src/lib/__tests__/api.test.ts \
        frontend/src/pages/GolfRound.tsx \
        frontend/src/pages/GolfProfile.tsx \
        frontend/src/pages/GolfLeaderboard.tsx
git commit -m "feat(golf): re-plumb read-only pages to nested Course/Tee shapes"
```

---

## Task 7: Tee-picker drawer + wire `GolfReview.tsx`

**Files:**
- Create: `frontend/src/components/golf/TeePickerDrawer.tsx`
- Create: `frontend/src/components/golf/DifficultyMeter.tsx`
- Modify: `frontend/src/pages/GolfReview.tsx`

**Depends on:** Task 6 (types in `api.ts`). **Do not start this task until Task 6 has landed its `api.ts` commit on the branch.** The manager's TaskCreate entry for Task 7 should set `blockedBy: [task-6-id]` so the team system enforces the ordering.

- [ ] **Step 1: Write the failing Playwright assertion**

In `frontend/e2e/golf-fairway-phase-b.spec.ts` (created in Task 8), include (written now to drive implementation):

```ts
test("tee-picker drawer opens from review page and updates differential", async ({ page }) => {
  // Stub GET /golf/round/:id to return a round with 2 tees on the course.
  await page.route("**/golf/round/**", route => route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ /* fixture with course + two tees */ }),
  }));

  await page.goto("/golf/review/stub-round-id");
  await page.getByRole("button", { name: /change/i }).click();

  await expect(page.getByText("Forgiving")).toBeVisible();
  await expect(page.getByText("Brutal")).toBeVisible();

  // Select the second tee — expect fw-selected class and differential change.
  const card2 = page.locator("[data-tee-card]").nth(1);
  await card2.click();
  await expect(card2).toHaveClass(/fw-selected/);

  const diff = await page.locator("[data-live-differential]").textContent();
  expect(Number(diff)).toBeGreaterThan(0);
});
```

- [ ] **Step 2: Implement `DifficultyMeter.tsx`**

Horizontal meter anchored at slope 113. Props: `slope: number`. Markers at 100, 113, 130, 145 labelled "Forgiving / Average / Above average / Brutal". Uses `--fw-info` for the current-slope caret.

- [ ] **Step 3: Implement `TeePickerDrawer.tsx`**

Props:
```ts
interface Props {
  round: GolfRoundDetail;
  tees: GolfTee[];
  open: boolean;
  onClose(): void;
  onApply(teeId: string, overrides?: { rating: number; slope: number; yardage: number }): void;
}
```

- Up to 4 tee cards. Selected card gets `className="fw-selected"` (uses Phase A's 2px info border).
- Editable rating (step 0.1), slope (step 1), yardage (step 1).
- `<DifficultyMeter slope={selectedSlope} />`.
- Live differential preview: renders `compute_differential` locally for immediate feedback.
- "Look up official values" button → calls `searchCourses(round.course.name, near)` and shows a dropdown of candidates (stubbed — pending-only results fine for Phase B).

- [ ] **Step 4: Wire drawer into `GolfReview.tsx`**

Add a "Change" link/button next to the course header in the existing Phase A markup. Clicking toggles `<TeePickerDrawer open>`. On `onApply`, PUT `/golf/round/:id/scores` with the new `tee_id` + overrides (empty holes — backend must accept tee-only change without overwriting strokes).

- [ ] **Step 5: Run typecheck + build + dev-server smoke**

```bash
cd frontend && npx tsc --noEmit && npm run build
cd frontend && npm run preview -- --port 4173 &
# manually open http://localhost:4173/golf/review/<id> or rely on Task 8's Playwright.
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/golf/TeePickerDrawer.tsx \
        frontend/src/components/golf/DifficultyMeter.tsx \
        frontend/src/pages/GolfReview.tsx
git commit -m "feat(golf): tee-picker drawer with editable rating/slope/yardage"
```

---

## Task 8: Playwright Phase B smoke tests

**Files:**
- Create: `frontend/e2e/golf-fairway-phase-b.spec.ts`

**Depends on:** Tasks 6 and 7.

- [ ] **Step 1: Write Phase B e2e assertions**

At minimum:

1. `tee-picker drawer opens and applies selected tee` (the Task 7 test, full version).
2. `editing score differential updates handicap snapshot after save` — stub `PUT /golf/round/:id/scores` to return `{ round: {...}, handicap: { handicap_index: 12.3 } }`; assert the profile handicap card updates when navigating to `/golf/profile/:user_id`.
3. `review page live differential reacts to manual score edits` (Phase A covered this for the flat shape — repeat for the new shape).
4. `handicap history endpoint feeds profile card` — stub `GET /golf/users/:id/handicap/history` with a 5-point series; assert the "Handicap" tile renders the latest value.

Use the same per-test `page.route` stub pattern Phase A established (no seeded rounds — bypass rate limit).

- [ ] **Step 2: Run against local preview**

```bash
cd frontend && npm run build && npm run preview -- --port 4173 &
FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-b.spec.ts --reporter=list
```
Expected: all green. Phase A suite (`golf-fairway-phase-a.spec.ts`) must also remain green — run it as a regression gate:
```bash
FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts --reporter=list
```

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/golf-fairway-phase-b.spec.ts
git commit -m "test(golf): Phase B Playwright — tee-picker + handicap history"
```

---

## Task 9: Deploy + prod smoke

**Files:** none (deploy script only).

- [ ] **Step 1: Rebase on latest main**

```bash
git checkout main && git pull --ff-only
git checkout golf/fairway-phase-b
git rebase main
```

- [ ] **Step 2: Full backend test run**

```bash
cd backend && venv/bin/python -m pytest tests/ -v
```
Expected: all green. Any previously-failing tests listed in the handoff doc (e.g., `user-workflows.spec.ts` flaky cases) are NOT Phase B regressions — but **new failures are blockers**.

- [ ] **Step 2a: Regression compare against Task 1 Step 4b baseline**

Compare the full suite's current state against `/tmp/phase-b-baseline.txt` captured before Phase B work started. Any test that was green on baseline and is red now is a blocker — investigate before deploy. Pay particular attention to:

- `tests/test_upload_routes.py` — lifting upload flow (did NOT have golf schema deps on baseline).
- `tests/test_attempt_routes.py` — competition attempts.
- `tests/test_auth_routes.py` — auth.
- `tests/test_user_routes.py` — user CRUD.
- `tests/test_bowling_annotations.py`, `tests/test_lane_edges_annotation.py` — bowling.

If any of these regressed, the root cause is either an `app.py` deletion that went too far or a migration that silently removed a shared table. Revert and re-scope before proceeding.

```bash
cd backend && venv/bin/python -m pytest tests/ --tb=no -q 2>&1 | diff /tmp/phase-b-baseline.txt -
```
Expected: diff shows only new-green additions from Tasks 2/3/5, zero red regressions.

- [ ] **Step 3: Full frontend typecheck + build + e2e**

```bash
cd frontend && npx tsc --noEmit && npm run build
cd frontend && npm run preview -- --port 4173 &
FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts e2e/golf-fairway-phase-b.spec.ts --reporter=list
```

- [ ] **Step 4: Deploy**

From repo root:
```bash
python3 deploy.py --skip-iam
```

Expected: Cloud Run services roll. The startup migration path in `app.py` will NOT re-create the golf tables (those blocks are deleted); the schema has to be applied via `apply_schema.py` against the Cloud SQL instance:

```bash
gcloud sql connect toms-gym --user=postgres --project=toms-gym
\i backend/toms_gym/migrations/008_fairway_schema.sql
```

or (preferred — runs the same script used locally):
```bash
cd backend && DATABASE_URL=<cloud-sql-url> venv/bin/python toms_gym/migrations/apply_schema.py toms_gym/migrations/008_fairway_schema.sql
```

- [ ] **Step 5: Prod smoke**

Against `https://toms-gym-web-quyiiugyoq-ue.a.run.app`:
1. `/golf/upload` → submit a scorecard. Confirm the response shape carries nested `course` + `tee`.
2. `/golf/review/:id` → Phase A visuals intact (color cells, amber glow, banner, live differential). "Change" button opens the tee-picker drawer.
3. `/golf/round/:id` → renders `course.name` + tee info.
4. `/golf/leaderboard` → populated with latest `HandicapSnapshot` rows.

- [ ] **Step 6: Open PR**

Use `gh pr create` (or web UI if the same EMU/Unauthorized error from Phase A returns). Title: `feat(golf): Fairway Phase B — Course/Tee schema + WHS engine`.

- [ ] **Step 7: Write Phase B → D handoff**

Create `docs/superpowers/handoffs/<YYYY-MM-DD>-fairway-phase-b-to-d.md` mirroring the Phase A → B format. Note:
- Schema now has `HandicapSnapshot` history for the Phase D trend chart.
- `GET /golf/users/:id/handicap/history` endpoint ready.
- `TeePickerDrawer` is the pattern for any future course-/tee-editing UI in Phase D.
- Known caveats carried forward from Phase A that are still relevant.

- [ ] **Step 8: Merge + cleanup**

After approval:
```bash
git checkout main && git pull
git branch -d golf/fairway-phase-b
git worktree prune
```

---

## Verification matrix

| Task | Command | Pass criterion |
|---|---|---|
| 1 | `psql toms_gym -c "\dt"` | 5 new tables, 3 old tables gone |
| 2 | `venv/bin/python -m pytest tests/test_handicap.py` | all green |
| 3 | `venv/bin/python -m pytest tests/test_courses_service.py` | all green |
| 4 | `venv/bin/python -m pytest tests/test_handicap.py tests/test_courses_service.py tests/test_golf_parser.py` | all green |
| 5 | `venv/bin/python -m pytest tests/test_golf_parser.py` | integration tests added + green |
| 6 | `cd frontend && npx tsc --noEmit && npm run build` | no errors |
| 7 | `cd frontend && npx tsc --noEmit && npm run build` | no errors |
| 8 | `npx playwright test e2e/golf-fairway-phase-a.spec.ts e2e/golf-fairway-phase-b.spec.ts` | all green |
| 9 | prod smoke on 4 URLs above | all 4 pass visually |

---

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| `pg_trgm` not enabled on Cloud SQL | Migration 008 includes `CREATE EXTENSION IF NOT EXISTS pg_trgm;`. Verify the Cloud SQL instance allows extensions (Cloud SQL Postgres does by default). |
| WHS adjustment table misinterpreted | Unit test per row in Task 2's parametrised test. Reviewer cross-checks against the spec §8.1 table before merge. |
| Response-shape change breaks frontend mid-deploy | Frontend + backend land together on one branch; no feature flag. If prod smoke fails, rollback is `gcloud run services update-traffic --to-revisions=<prev>=100`. |
| Inline `app.py` table-create block was silently creating tables on every startup | Task 1 Step 2 deletes that code. Task 9 Step 4 replaces with explicit `apply_schema.py` run against Cloud SQL. |
| Phase A's rate-limit test-friendliness (Playwright stubs) must carry into Phase B | Task 8 follows the same per-test `page.route` stub pattern. No real `/golf/upload` hits in e2e. |
| Unit tests in Task 2 lock in potentially wrong WHS values | Task 2 Step 1 flags this as reviewer-critical. Reference cases come from USGA rules of handicapping; reviewer must cross-check before merge. |

---

## Rollback plan

Phase B is a whole-branch merge. If prod smoke fails:

1. **Cloud Run:** `gcloud run services update-traffic my-python-backend --to-revisions=<prev-revision>=100 --region=us-east1` and same for `toms-gym-web`.
2. **Schema:** greenfield — run the inverse of migration 008:
   ```sql
   DROP TABLE "HandicapSnapshot", "HoleScore", "Round", "Tee", "Course" CASCADE;
   ```
   and restore the prior inline `CREATE TABLE` block from `app.py` git history.
3. **Frontend:** prior Cloud Run revision carries the old response-shape consumer.

No user data is lost because Phase B is greenfield (user confirmed).

---

## Out of scope

- Phase D dashboard (`/golf` landing page, trend chart, rank card).
- Social features (groups, feed, reactions, rematches) — deferred indefinitely.
- Course DB seeding at scale — pending courses created on demand only.
- Playing Conditions Calculation (PCC) — hardcoded to 0 for MVP.
- Push notifications, PWA install, export-as-image.



---

## Revision 1 (2026-04-18)

Changes applied after manager's first review. Each bullet references the blocker/gap number from the review so the delta is auditable.

**Blockers fixed:**

1. **WHS_TABLE rounds 10–16 corrected.** Spec §B2 rows: `9–11 → lowest 3`, `12–14 → lowest 4`, `15–16 → lowest 5`. Previous table had `11→4` and `14→5`; both are now `11→3` and `14→4`. Parametrised test in Task 2 expanded to cover **every** row of the spec table (15 cases, one per n-value plus a >20 case).
2. **`_recalculate_handicap` query spelled out.** Exact SQL and flow now embedded in Task 4 Step 1: pulls `score_differential` + `holes` from `Round`, builds `nine_hole_flags`, calls `compute_handicap_index`, applies 12-month cap against `MIN(handicap_index)` from last 12 months of `HandicapSnapshot`, INSERTs one snapshot row per recalc with the exact `differentials_used` list populated. `rounds_used` = pool size, not lowest-N count.
3. **Net-double-bogey per-hole cap wired end-to-end.**
   - Added `hole_handicaps INTEGER[]` column to `Tee` in migration 008 (nullable).
   - Added `allocate_strokes(handicap_index, hole_handicaps) -> List[int] | None` to `services/handicap.py` with 4 new unit tests covering null inputs, index=9 → 1 stroke on 9 hardest holes, and wrap-around for index>18.
   - Task 4 Step 4 (PUT /scores) now shows explicit per-hole cap application: fetch current index → `allocate_strokes(...)` → `net_double_bogey_cap(par, rec, actual=strokes)` per hole → sum adjusted. Null allocation falls back to flat-10 via the existing cap helper.
   - Accepted shortcut flagged inline: when OCR-uploaded tees have no `hole_handicaps`, every round uses flat-10 until a future phase extracts allocation ranks from scorecards.
4. **Task 5 rate-limit bypass documented.** `rate_limit` decorator already honors `app.config['TESTING']` (see `security.py:118`); conftest already sets `TESTING=True` (line 27). Added a one-liner test at the top of Task 5 Step 1 that asserts this contract, so regressions break loud instead of 429-ing silently.

**Gaps fixed:**

5. **conftest migration 008 applied.** New Task 1 Step 4a makes the test-DB bootstrap (`tests/init_db.py`) apply `008_fairway_schema.sql` explicitly. No more "extend conftest if needed" parenthetical.
6. **`monthly_delta` math spelled out.** Task 4 Step 10 now includes the full SQL (CTEs for `latest` and `past` snapshots in the 30–60-day window), delta semantics (latest − past; negative = improvement), null handling, and sort order.
7. **Frontend client-fn bodies filled in.** `searchCourses`, `createCourse`, `getHandicapHistory` now show complete `fetch` implementations so the doer doesn't reverse-engineer the existing convention.
8. **Task 7 ordering enforceable.** Task 7 header now says "do not start until Task 6's `api.ts` commit lands" and directs the manager to set `blockedBy: [task-6-id]` in TaskCreate so the team system enforces it.
9. **Regression baseline + compare added.** New Task 1 Step 4b captures a full pre-Phase-B suite baseline into `/tmp/phase-b-baseline.txt`; new Task 9 Step 2a diffs post-Phase-B state against that baseline and lists the five non-golf test files to watch.
10. **`played_on` default made explicit.** Task 4 Step 2 now documents that Phase B's upload handler does NOT accept a `played_on` override — the column defaults to `CURRENT_DATE`. Adding a date picker is noted as a future-phase concern.

**Non-blockers folded in:**

- `GolfLeaderboard.tsx` listing contradiction removed — now listed only as "Modify" with the `monthly_delta` column render called out.
- Parametrised handicap test tolerance tightened from `abs=0.1` to `abs=0.05`.

**Open-question resolutions (from manager, 2026-04-18):**

1. **USGA citation** — fixture JSON now carries a top-level `"source"` key ("USGA Rules of Handicapping §5.2 (WHS adjustment table)"); test module docstring cites the same source. Parametric lowest-N + adjustment assertions must match §5.2 bit-exact; numeric `expected_index` values are pinned-as-regression and cross-checked at PR review (not a revision blocker).
2. **Migration runner** — keep `apply_schema.py` convention. Alembic/Flyway is out of scope for Phase B; deferred to a dedicated infra task.
3. **pg_trgm on Cloud SQL** — allowed without extra privileges on Google's allowlist. No plan change; doer-schema verifies during local dev, Task 9 gets a manual `CREATE EXTENSION` step only if prod apply fails.
4. **Playwright file naming** — keep `golf-fairway-phase-a.spec.ts` as a permanent regression gate alongside new `golf-fairway-phase-b.spec.ts`. No consolidation.
