# Pushup Challenge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Users upload pushup videos to a challenge; the analyzer counts reps and scores form; the challenge leaderboard ranks athletes by best rep count (`metric: "reps"`).

**Architecture:** Config-only analyzer change (a `pushup` entry in `EXERCISE_CONFIGS` reuses the existing elbow-angle peak-detection rep pipeline), a new `Pushup` lift_type enum value + mappings in toms_gym, a third pure ranking function `_rank_reps` beside `_rank_time`/`_rank_weight`, and a `reps` case in the frontend's centralized metric helpers. Spec: `docs/superpowers/specs/2026-08-01-pushup-challenge-design.md`.

**Tech Stack:** Python (Flask backend, analysis-engine with MediaPipe/OpenCV/pytest), PostgreSQL enum migration, React + TypeScript + Jest.

## Global Constraints

- Two repos: analyzer tasks run in `~/code/bowling-app/analysis-engine`; everything else in `~/code/toms_gym`.
- Deploy order is a hard requirement: analysis engine FIRST, toms_gym second (an old engine falls back to bicep_curl analysis for unknown lift types).
- `ALTER TYPE ... ADD VALUE` is non-transactional — never wrap in BEGIN/COMMIT; use `IF NOT EXISTS` (matches migration 009 pattern).
- Backend tests registered in `tools/run_ci_tests.sh` must stay DB-free.
- Frontend label/DB enum/engine name triple is exactly: `Pushup` (frontend id) → `Pushup` (DB enum) → `pushup` (engine).
- Verify ChallengeDetail changes by rendering in a browser, not just tsc (known scope-bug class, see CLAUDE.md).
- Conventional commits: `feat(pushup): ...`, `test(pushup): ...`.

---

### Task 1: Analyzer — `pushup` exercise config

**Repo:** `~/code/bowling-app/analysis-engine`

**Files:**
- Modify: `src/lifting/config.py` (add to `EXERCISE_CONFIGS`, after the `"deadlift"` entry, before `"plank"`)
- Test: `tests/test_lifting/test_config.py`

**Interfaces:**
- Produces: `EXERCISE_CONFIGS["pushup"]` — consumed automatically by `analyze_lift()` (`pipeline.py` reads the config by `lift_type`) and `analyze_from_skeletons()` (`analysis/analyze.py:208`). No other analyzer code change is needed for routing.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lifting/test_config.py` (follow the file's existing style for asserting on configs):

```python
def test_pushup_config_exists_and_is_rep_based():
    from src.lifting.config import EXERCISE_CONFIGS

    cfg = EXERCISE_CONFIGS["pushup"]
    assert not cfg.get("static_hold")          # rep pipeline, not plank branch
    assert cfg["signal_angle_fn"] == "compute_elbow_angle"
    assert cfg["rom_extension_deg"] > cfg["rom_contraction_deg"]
    # Elbow drift is meaningless with planted hands; weights must sum to 1.
    assert cfg["form_weights"].get("elbow_drift", 0.0) == 0.0
    assert abs(sum(cfg["form_weights"].values()) - 1.0) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/code/bowling-app/analysis-engine && venv/bin/python -m pytest tests/test_lifting/test_config.py::test_pushup_config_exists_and_is_rep_based -v` (use the repo's existing test invocation if different — check `Makefile`/CI script)
Expected: FAIL with `KeyError: 'pushup'`

- [ ] **Step 3: Add the config**

In `src/lifting/config.py`, inside `EXERCISE_CONFIGS`, after the `"deadlift"` entry:

```python
    "pushup": {
        # Same elbow-angle peak cycle as bicep_curl: lockout = extension peak,
        # chest-to-floor = contraction trough. Side view recommended.
        "signal_angle_fn": "compute_elbow_angle",
        "primary_angles": ["elbow_angle"],
        "rom_extension_deg": 155.0,   # initial guess — tune on fixture (Task 2)
        "rom_contraction_deg": 90.0,
        "max_rep_duration_s": 8.0,
        "form_weights": {
            "rom": 0.50,
            "elbow_drift": 0.00,      # hands planted — drift is meaningless
            "momentum": 0.25,
            "body_sway": 0.25,
        },
    },
```

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

- [ ] **Step 5: Run the whole lifting test suite to check for regressions**

Run: `venv/bin/python -m pytest tests/test_lifting tests/test_lift_summary.py -v`
Expected: all PASS (no existing test iterates EXERCISE_CONFIGS in a way that breaks)

- [ ] **Step 6: Commit**

```bash
git add src/lifting/config.py tests/test_lifting/test_config.py
git commit -m "feat(pushup): add pushup exercise config (elbow-angle rep pipeline)"
```

---

### Task 2: Analyzer — pushup rep-counting characterization test

**Repo:** `~/code/bowling-app/analysis-engine`

**Files:**
- Test: `tests/test_lifting/test_rep_segmenter.py` (append)

**Interfaces:**
- Consumes: `EXERCISE_CONFIGS["pushup"]` from Task 1; the segmenter entry point already used by existing tests in this file (read the file first and reuse its synthetic-signal helper/pattern — it already builds angle traces and asserts rep counts).

This is a pinning test: it should pass without production changes, proving the generic segmenter counts pushup cycles. If it FAILS, stop and tune `MIN_PROMINENCE`/thresholds rather than forcing the test green — that failure is exactly the information this task exists to surface.

- [ ] **Step 1: Read the existing test file and write the pushup test in its style**

The test must build a synthetic elbow-angle trace of 5 pushup cycles at 30 fps — oscillating between ~165° (lockout, held ~0.5 s) and ~80° (bottom) with ~1 s down / ~1 s up ramps — run it through the same segmentation call the neighboring tests use, and assert exactly 5 reps are detected. Shape sketch (adapt names to the file's real helpers):

```python
def test_pushup_cycles_are_segmented():
    fps = 30
    cycle = ([165.0] * 15                       # lockout hold, 0.5 s
             + list(np.linspace(165, 80, 30))    # descent, 1 s
             + list(np.linspace(80, 165, 30)))   # press-up, 1 s
    signal = np.array(cycle * 5, dtype=float)

    reps = <segment-call-used-by-existing-tests>(signal, fps)

    assert len(reps) == 5
```

- [ ] **Step 2: Run it**

Run: `venv/bin/python -m pytest tests/test_lifting/test_rep_segmenter.py -v -k pushup`
Expected: PASS. If FAIL: the elbow-angle ROM (~85°) is well above `MIN_PROMINENCE = 20`, so investigate with the debug tooling (`scripts/debug_lift.py`) before touching thresholds; record findings in the commit message.

- [ ] **Step 3: Commit**

```bash
git add tests/test_lifting/test_rep_segmenter.py
git commit -m "test(pushup): pin rep segmentation on synthetic pushup elbow trace"
```

---

### Task 3: Analyzer — end-to-end fixture verification + deploy

**Repo:** `~/code/bowling-app/analysis-engine`

**Files:**
- Create: `tests/fixtures/` pushup clip (record ~10 s of real pushups, side view — same practice as `test_video_plank_10s.mp4`)
- No production code expected.

**Interfaces:**
- Produces: a deployed bowling-service that returns `{"lift_type": "pushup", "total_reps": N, ...}` from `POST /analyze-lift` with `lift_type: "pushup"` — the contract Tasks 4–6 build on (report JSON lands in `LiftingResult.report`, so `report->>'total_reps'` is queryable).

- [ ] **Step 1: Run the CLI analyzer on a real pushup video**

Run: `venv/bin/python scripts/analyze_lift.py <pushup video> --lift-type pushup` (check the script's actual flag names first: `head -40 scripts/analyze_lift.py`)
Expected: summary JSON with `total_reps` equal to the true count (±0) and non-empty `rep_metrics`. If the count is wrong, tune `rom_extension_deg`/`rom_contraction_deg` in the Task 1 config against this video, re-run Task 1/2 tests, and amend.

- [ ] **Step 2: Commit the fixture + any tuning**

```bash
git add tests/fixtures/ src/lifting/config.py
git commit -m "feat(pushup): tune pushup ROM thresholds against real fixture video"
```

- [ ] **Step 3: Deploy bowling-service and verify remotely**

Deploy using this repo's existing deploy path (check its README/Makefile for the Cloud Run deploy command). Then verify with a direct authenticated `POST /analyze-lift` carrying `{"video_url": <GCS pushup clip>, "attempt_id": "<uuid>", "lift_type": "pushup"}` and confirm the response/stored report contains `total_reps`.
Expected: engine deployed BEFORE any toms_gym change ships (Global Constraints).

---

### Task 4: Backend — `Pushup` enum value + label/engine mappings

**Repo:** `~/code/toms_gym`

**Files:**
- Create: `backend/toms_gym/migrations/016_add_pushup_lift_type.sql`
- Modify: `backend/toms_gym/app.py` (`run_startup_migrations`, after the Plank enum block at ~line 63–70)
- Modify: `backend/toms_gym/routes/upload_routes.py` (`LIFT_TYPE_MAPPING`, ~line 19)
- Modify: `backend/toms_gym/integrations/lifting_processor.py` (`_normalize_lift_type`, ~line 146)
- Test: `backend/tests/test_lifting_processor_mapping.py` (create; DB-free)

**Interfaces:**
- Produces: DB enum value `'Pushup'`; `LIFT_TYPE_MAPPING["Pushup"] == "Pushup"`; `_normalize_lift_type("Pushup") == "pushup"`. Tasks 5–6 assume attempts with `lift_type = 'Pushup'` exist.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_lifting_processor_mapping.py`:

```python
"""DB-free mapping tests: frontend label -> DB enum -> engine lift_type."""
from toms_gym.integrations.lifting_processor import _normalize_lift_type
from toms_gym.routes.upload_routes import LIFT_TYPE_MAPPING


def test_pushup_frontend_label_maps_to_db_enum():
    assert LIFT_TYPE_MAPPING["Pushup"] == "Pushup"


def test_pushup_db_enum_maps_to_engine_name():
    assert _normalize_lift_type("Pushup") == "pushup"


def test_unknown_still_falls_back_to_bicep_curl():
    assert _normalize_lift_type("Zumba") == "bicep_curl"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_lifting_processor_mapping.py -v --noconftest`
(If imports at module level pull in Flask app context and fail, follow the import style of an existing DB-free suite like `tests/test_lift_history.py`.)
Expected: FAIL with `KeyError: 'Pushup'`

- [ ] **Step 3: Implement**

`backend/toms_gym/migrations/016_add_pushup_lift_type.sql`:

```sql
-- Migration 016: Add 'Pushup' to the lift_type enum.
-- Enables Pushup Challenges (rep-count leaderboards).
--
-- IMPORTANT: ALTER TYPE ... ADD VALUE is non-transactional in PostgreSQL.
-- This migration must NOT be wrapped in BEGIN/COMMIT.

ALTER TYPE lift_type ADD VALUE IF NOT EXISTS 'Pushup';
```

`backend/toms_gym/app.py`, after the Plank enum block in `run_startup_migrations`:

```python
        # Add 'Pushup' to lift_type enum if not exists (migration 016)
        try:
            session.execute(sqlalchemy.text("ALTER TYPE lift_type ADD VALUE IF NOT EXISTS 'Pushup'"))
            session.commit()
            logging.info("Added 'Pushup' to lift_type enum")
        except Exception as e:
            session.rollback()
            logging.info(f"Pushup enum migration note: {e}")
```

`upload_routes.py` — add to `LIFT_TYPE_MAPPING`:

```python
    "Pushup": "Pushup",
```

`lifting_processor.py` — add to the `mapping` dict in `_normalize_lift_type`:

```python
        'Pushup': 'pushup',
```

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

- [ ] **Step 5: Register the suite in CI**

Add `tests/test_lifting_processor_mapping.py` to `backend/tools/run_ci_tests.sh` (same pattern as `test_lift_history.py`), then run the full gate: `cd backend && bash tools/run_ci_tests.sh`
Expected: all suites PASS

- [ ] **Step 6: Commit**

```bash
git add backend/toms_gym/migrations/016_add_pushup_lift_type.sql backend/toms_gym/app.py \
        backend/toms_gym/routes/upload_routes.py backend/toms_gym/integrations/lifting_processor.py \
        backend/tests/test_lifting_processor_mapping.py backend/tools/run_ci_tests.sh
git commit -m "feat(pushup): Pushup lift_type enum + frontend/engine mappings"
```

---

### Task 5: Backend — `_rank_reps` in the pure leaderboard service

**Repo:** `~/code/toms_gym`

**Files:**
- Modify: `backend/toms_gym/services/challenge_leaderboard.py`
- Test: `backend/tests/test_challenge_leaderboard.py` (append)

**Interfaces:**
- Consumes: participant dicts as built by `_leaderboard_payload` — each attempt dict will carry a new key `"reps"` (added in Task 6; `None` until analysis completes).
- Produces: `rank_challenge(participants, metric="reps")` returning rows in the exact `_rank_time` row shape (`score`, `best_by_lift`, `form_score`, `steadiness`, `attempt_id`, `clip_url`, `thumbnail_url`, `date`, `user_id`, `name`, `weight_class`, `gender`, `attempt_count`, `history`, `rank`). `score` = best single-attempt rep count.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_challenge_leaderboard.py` (reuse the file's existing participant/attempt builder helpers if present — read it first):

```python
def _pushup_attempt(attempt_id, reps, form_score=None, created_at="2026-08-01T10:00:00",
                    status="completed", lift_type="Pushup"):
    return {
        "attempt_id": attempt_id,
        "lift_type": lift_type,
        "weight_kg": None,
        "status": status,
        "created_at": created_at,
        "video_url": f"gs://v/{attempt_id}.mp4",
        "annotated_video_url": None,
        "held_s": None,
        "form_score": form_score,
        "steadiness": None,
        "reps": reps,
    }


def test_reps_board_ranks_by_best_single_attempt():
    participants = [
        {"user_id": "u1", "name": "Amy", "weight_class": None, "gender": None,
         "attempts": [_pushup_attempt("a1", 12), _pushup_attempt("a2", 30)]},
        {"user_id": "u2", "name": "Bo", "weight_class": None, "gender": None,
         "attempts": [_pushup_attempt("b1", 25)]},
    ]
    rows = rank_challenge(participants, metric="reps")
    assert [r["user_id"] for r in rows] == ["u1", "u2"]
    assert rows[0]["score"] == 30 and rows[0]["rank"] == 1
    assert rows[0]["best_by_lift"] == {"Pushup": 30}
    assert rows[0]["attempt_count"] == 2
    assert [h["score"] for h in rows[0]["history"]] == [12, 30]


def test_reps_board_tiebreak_form_then_earliest():
    participants = [
        {"user_id": "u1", "name": "Amy", "weight_class": None, "gender": None,
         "attempts": [_pushup_attempt("a1", 20, form_score=80.0,
                                      created_at="2026-08-02T10:00:00")]},
        {"user_id": "u2", "name": "Bo", "weight_class": None, "gender": None,
         "attempts": [_pushup_attempt("b1", 20, form_score=90.0,
                                      created_at="2026-08-03T10:00:00")]},
    ]
    rows = rank_challenge(participants, metric="reps")
    assert [r["user_id"] for r in rows] == ["u2", "u1"]  # higher form wins the tie


def test_reps_board_excludes_failed_pending_analysis_and_other_lifts():
    participants = [
        {"user_id": "u1", "name": "Amy", "weight_class": None, "gender": None,
         "attempts": [
             _pushup_attempt("a1", 15, status="failed"),      # failed: out
             _pushup_attempt("a2", None),                     # no analysis yet: out
             _pushup_attempt("a3", 10, lift_type="Squat"),    # wrong lift: out
         ]},
    ]
    rows = rank_challenge(participants, metric="reps")
    assert rows[0]["score"] == 0 and rows[0]["attempt_count"] == 0
    assert rows[0]["clip_url"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && venv/bin/python -m pytest tests/test_challenge_leaderboard.py -v -k reps --noconftest` (drop `--noconftest` if the existing suite runs without it — match how `run_ci_tests.sh` invokes it)
Expected: FAIL with `ValueError: unknown metric: 'reps'`

- [ ] **Step 3: Implement `_rank_reps`**

In `challenge_leaderboard.py`, add after `_compare_time_attempts` (mirrors it):

```python
def _compare_reps_attempts(a, b) -> int:
    """Best-first ordering for pushup attempts: most reps, then higher form
    score, then earliest created_at."""
    ar, br = a["reps"], b["reps"]
    if ar != br:
        return -1 if ar > br else 1
    af = a["form_score"] if a["form_score"] is not None else float("-inf")
    bf = b["form_score"] if b["form_score"] is not None else float("-inf")
    if af != bf:
        return -1 if af > bf else 1
    ak, bk = _created_key(a["created_at"]), _created_key(b["created_at"])
    if ak != bk:
        return -1 if ak < bk else 1
    return 0
```

and after `_rank_time`:

```python
def _rank_reps(participants) -> List[dict]:
    rows = []
    for p in participants:
        # A rep count only exists once analysis has produced it, so the
        # ``reps is not None`` check gates on completion (like _rank_time).
        submitted = [a for a in p.get("attempts", []) if a.get("status") != "failed"]
        qualifying = [
            a for a in submitted
            if a.get("lift_type") == "Pushup" and a.get("reps") is not None
        ]

        chrono = sorted(qualifying, key=lambda a: _created_key(a["created_at"]))
        history = [
            {"score": a["reps"], "date": _iso_date(a["created_at"])}
            for a in chrono
        ]

        if qualifying:
            best = sorted(qualifying, key=cmp_to_key(_compare_reps_attempts))[0]
            score = best["reps"]
            row = {
                "score": score,
                "best_by_lift": {"Pushup": score},
                "form_score": best["form_score"],
                "steadiness": None,
                "attempt_id": best.get("attempt_id"),
                "clip_url": _clip_url(best),
                "thumbnail_url": None,
                "date": _iso_date(best["created_at"]),
                "_best_created": _created_key(best["created_at"]),
                "_best_form": best["form_score"],
            }
        else:
            row = {
                "score": 0,
                "best_by_lift": {},
                "form_score": None,
                "steadiness": None,
                "attempt_id": None,
                "clip_url": None,
                "thumbnail_url": None,
                "date": None,
                "_best_created": _created_key(None),
                "_best_form": None,
            }

        row.update({
            "user_id": p.get("user_id"),
            "name": p.get("name"),
            "weight_class": p.get("weight_class"),
            "gender": p.get("gender"),
            "attempt_count": len(qualifying),
            "history": history,
        })
        rows.append(row)

    def sort_key(r):
        form = r["_best_form"] if r["_best_form"] is not None else float("-inf")
        return (
            0 if r["score"] > 0 else 1,   # zero-score rows last
            -r["score"],                  # most reps first
            -form,                        # higher form score first
            r["_best_created"],           # earliest created_at first
        )

    return _finalize(rows, sort_key)
```

Extend `rank_challenge`:

```python
    if metric == "reps":
        return _rank_reps(participants)
```

and update its docstring + the module docstring to list the third metric:
`"reps"` (pushup challenges) — rank by the athlete's best single-attempt rep count.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && venv/bin/python -m pytest tests/test_challenge_leaderboard.py -v`
Expected: all PASS (new + existing)

- [ ] **Step 5: Commit**

```bash
git add backend/toms_gym/services/challenge_leaderboard.py backend/tests/test_challenge_leaderboard.py
git commit -m "feat(pushup): reps metric ranking in challenge leaderboard service"
```

---

### Task 6: Backend — route wiring (metric selection + reps extraction)

**Repo:** `~/code/toms_gym`

**Files:**
- Modify: `backend/toms_gym/routes/competition_routes.py` (`_leaderboard_payload`, ~lines 405–480)

**Interfaces:**
- Consumes: `rank_challenge(..., metric="reps")` from Task 5.
- Produces: leaderboard payload with `"metric": "reps"` for pushup-only challenges; each attempt dict carries `"reps": int | None`. The frontend (Task 7–8) switches rendering on this `metric` string.

- [ ] **Step 1: Add `reps` to the leaderboard SQL**

In the SELECT (after the `steadiness` line):

```sql
                   lr.report->>'total_reps' AS reps,
```

- [ ] **Step 2: Carry it onto the attempt dict**

In the attempt-building loop (after `"steadiness": ...`), noting reps is an integer:

```python
                "reps": _to_int(row['reps']),
```

Add next to `_to_float` (same defensive shape):

```python
    def _to_int(value):
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
```

- [ ] **Step 3: Extend metric selection**

Replace the selection block (keep the comment style):

```python
    # Metric selection: declared plank-only -> time; declared pushup-only ->
    # reps; other declared -> weight; no metadata -> infer from completed
    # attempts (all-Plank -> time, all-Pushup -> reps).
    declared_set = set(declared)
    if declared_set == {"Plank"}:
        metric = "time"
    elif declared_set == {"Pushup"}:
        metric = "reps"
    elif declared_set:
        metric = "weight"
    elif completed_lift_types and completed_lift_types == {"Plank"}:
        metric = "time"
    elif completed_lift_types and completed_lift_types == {"Pushup"}:
        metric = "reps"
    else:
        metric = "weight"
```

- [ ] **Step 4: Verify**

The pure ranking is covered by Task 5; this glue needs a live check. Run the backend CI gate (`cd backend && bash tools/run_ci_tests.sh`) — expected all PASS — and start the app against a local Postgres if available (`docker run --rm -d -p 5434:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_DB=toms_gym_test postgres:15`) to confirm the leaderboard route still returns 200 for an existing challenge. Full prod verification happens in Task 9.

- [ ] **Step 5: Commit**

```bash
git add backend/toms_gym/routes/competition_routes.py
git commit -m "feat(pushup): reps metric selection + total_reps extraction in leaderboard route"
```

---

### Task 7: Frontend — `reps` metric type + helpers

**Repo:** `~/code/toms_gym`

**Files:**
- Modify: `frontend/src/lib/types.ts:397`
- Modify: `frontend/src/components/challenge/metric.ts`
- Test: `frontend/src/components/challenge/__tests__/metric.test.ts` (append)

**Interfaces:**
- Produces: `ChallengeMetric = "time" | "weight" | "reps"`; `scoreColumnLabel("reps") === "REPS"`, `scoreUnit("reps") === "reps"`, `formatScoreValue(30, "reps") === "30"`, `uploadCtaLabel("reps") === "Upload your pushups"`. All existing consumers (Podium, LeaderboardRow, StandingCard, YouRow, ChallengeDetail) compile unchanged because they switch on the metric string via these helpers.

- [ ] **Step 1: Write the failing tests**

Append to `metric.test.ts` (match its existing import/describe style):

```typescript
describe("reps metric", () => {
  it("labels the score column REPS", () => {
    expect(scoreColumnLabel("reps")).toBe("REPS");
  });
  it("uses a reps unit", () => {
    expect(scoreUnit("reps")).toBe("reps");
  });
  it("formats rep scores as integers", () => {
    expect(formatScoreValue(30.0, "reps")).toBe("30");
  });
  it("uses a pushup CTA", () => {
    expect(uploadCtaLabel("reps")).toBe("Upload your pushups");
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npx jest src/components/challenge/__tests__/metric.test.ts`
Expected: FAIL (type error on `"reps"` / wrong values)

- [ ] **Step 3: Implement**

`types.ts:397`:

```typescript
export type ChallengeMetric = "time" | "weight" | "reps";
```

`metric.ts` — convert the ternaries to explicit switches:

```typescript
export function scoreColumnLabel(metric: ChallengeMetric): string {
  if (metric === "time") return "HOLD";
  if (metric === "reps") return "REPS";
  return "TOTAL";
}

export function scoreUnit(metric: ChallengeMetric): string {
  if (metric === "time") return "s";
  if (metric === "reps") return "reps";
  return "lbs";
}

/** Number part of a score, formatted for the metric (one decimal for time). */
export function formatScoreValue(score: number, metric: ChallengeMetric): string {
  return metric === "time" ? score.toFixed(1) : String(Math.round(score));
}

export function uploadCtaLabel(metric: ChallengeMetric): string {
  if (metric === "time") return "Upload your plank";
  if (metric === "reps") return "Upload your pushups";
  return "Upload your lift";
}
```

Update the module's header comment to mention the third metric.

- [ ] **Step 4: Run tests + typecheck**

Run: `cd frontend && npx jest src/components/challenge && npx tsc --noEmit`
Expected: PASS / no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/components/challenge/metric.ts \
        frontend/src/components/challenge/__tests__/metric.test.ts
git commit -m "feat(pushup): reps challenge metric in frontend metric helpers"
```

---

### Task 8: Frontend — upload forms + attempt history for pushups

**Repo:** `~/code/toms_gym`

**Files:**
- Modify: `frontend/src/pages/ChallengeDetail.tsx` (`ALL_LIFT_OPTIONS` at ~line 941; weight-field/`liftType === 'Plank'` conditionals at ~lines 936–960 and the upload payload at ~line 194)
- Modify: `frontend/src/components/challenge/AttemptHistory.tsx`
- Modify: `frontend/src/pages/UploadVideo.tsx` (lift dropdown at ~line 285)
- Test: `frontend/src/components/challenge/__tests__/AttemptHistory.test.tsx` (append)

**Interfaces:**
- Consumes: `metric === "reps"` from the leaderboard payload (Task 6); `total_reps` on `/users/<id>/lifts` rows (already shipped by `services/lift_history.py` — field name `total_reps`).
- Produces: pushup-aware upload forms (no weight field) and attempt rows showing "N reps" + grade pill.

- [ ] **Step 1: Write the failing AttemptHistory test**

Append to `AttemptHistory.test.tsx`, following the file's existing axios-mock pattern, a case where `metric="reps"` and the mocked `/users/.../lifts` response contains two rows with `total_reps: 30` and `total_reps: 12`; assert the rendered output contains `30 reps`, `12 reps`, and that the 🏆 lands on the 30-rep row.

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npx jest AttemptHistory`
Expected: FAIL (renders the weight branch, "—")

- [ ] **Step 3: Implement AttemptHistory**

Add `total_reps: number | null;` to `AttemptRow`. Extend `metricValue`:

```typescript
const metricValue = (row: AttemptRow, metric: ChallengeMetric): number | null =>
  metric === "time" ? row.hold_s : metric === "reps" ? row.total_reps : row.weight;
```

Render branch — replace the binary `metric === "time" ? ... : ...` JSX with three branches; the reps branch mirrors the weight branch's grade pill:

```tsx
{metric === "reps" ? (
  <>
    <span className="font-medium tabular-nums">
      {row.total_reps != null ? `${row.total_reps} reps` : analyzing ? "analyzing…" : "—"}
    </span>
    {row.grade && (
      <span className={`inline-flex items-center justify-center w-5 h-5 rounded text-[11px] font-bold ${GRADE_CLASS[row.grade] ?? "bg-secondary"}`}>
        {row.grade}
      </span>
    )}
  </>
) : metric === "time" ? (
  /* existing time branch unchanged */
) : (
  /* existing weight branch unchanged */
)}
```

- [ ] **Step 4: Implement the upload forms**

`ChallengeDetail.tsx`:
- Add `{ id: 'Pushup', label: 'Pushup', dbValue: 'Pushup' }` to `ALL_LIFT_OPTIONS` (declared-category filtering then makes it appear only on pushup challenges, and the existing lock-when-only-one behavior applies).
- Everywhere the form special-cases `liftType === 'Plank'` (grid class ~line 936, weight-field visibility ~line 956, upload compression ~line 203, payload weight default), extend to a shared predicate near the top of the component:

```typescript
const isBodyweightLift = (lt: string) => lt === 'Plank' || lt === 'Pushup';
```

and replace those `=== 'Plank'` checks with `isBodyweightLift(liftType)` — EXCEPT the compression choice (`'fast-only'` is a plank-duration concern; leave pushups on `'auto'`).

`UploadVideo.tsx` — add to the standalone dropdown:

```tsx
<option value="Pushup">Pushup</option>
```

and hide/skip the weight input when `liftType === 'Pushup'` following exactly how the page handles `Plank` today (read the surrounding weight-validation at ~line 104 — weight must not block submission for Pushup). If the page has no Plank handling, submit `weight: "0"` for Pushup and keep the field hidden.

- [ ] **Step 5: Run tests, typecheck, and render in a browser**

Run: `cd frontend && npx jest && npx tsc --noEmit`
Expected: all suites PASS, no type errors.
Then start the dev server and load a challenge page (any existing one) to confirm no runtime scope errors — the `metric is not defined` class of bug tsc can't catch.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ChallengeDetail.tsx frontend/src/pages/UploadVideo.tsx \
        frontend/src/components/challenge/AttemptHistory.tsx \
        frontend/src/components/challenge/__tests__/AttemptHistory.test.tsx
git commit -m "feat(pushup): pushup upload option, weightless form, reps attempt history"
```

---

### Task 9: Deploy + production verification

**Repo:** `~/code/toms_gym`

**Files:** none (operational)

**Interfaces:**
- Consumes: everything above; engine already deployed (Task 3).

- [ ] **Step 1: Deploy toms_gym**

Run: `python3 deploy.py --skip-iam`
Expected: backend + frontend revisions live; startup log shows "Added 'Pushup' to lift_type enum".

- [ ] **Step 2: Create the pushup challenge**

Create a Competition whose description declares `lifttypes: Pushup` the same way the plank challenge does (inspect the live plank challenge's description via `GET /competitions` and copy its tag format exactly).

- [ ] **Step 3: End-to-end prod test**

Upload the real pushup fixture video to the challenge at the prod frontend URL. Verify: analysis status page → completed; VideoPlayer shows rep breakdown; challenge leaderboard shows `REPS` column with the correct count; AttemptHistory expands with "N reps"; share/OG card renders.

- [ ] **Step 4: Clean up + document**

Mark the test user via the `is_test` flow (or delete the attempt). Add a "Pushup Challenge (shipped YYYY-MM-DD)" section to `CLAUDE.md` following the existing shipped-feature sections: metric `reps`, `_rank_reps`, enum migration 016, deploy-order constraint.

```bash
git add CLAUDE.md
git commit -m "docs(pushup): record shipped pushup challenge feature"
```

---

### Task 10 (stretch, optional): Analyzer — body-line ("hip sag") form metric

**Repo:** `~/code/bowling-app/analysis-engine`. Only start after Tasks 1–9 are verified in prod.

**Files:**
- Modify: `src/lifting/analysis/form_scorer.py`, `src/lifting/config.py` (pushup `form_weights` + a `PUSHUP_METRIC_TARGETS` block + `metric_targets_key`), `src/lifting/analysis/analyze.py` (wire the metric into rep scoring the same way deadlift's `back_position` is wired — read that path first)
- Test: `tests/test_lifting/test_form_scorer.py`

Summary (details deliberately deferred — this task requires reading the deadlift metric wiring first and mirrors it): compute per-frame shoulder-hip-ankle angle (the plank analyzer's body-line math), score a rep by mean deviation from 180°, surface as a "Body Line" metric with `lower_is_better` targets (good < 10°, warn < 20°), reweight pushup to `{rom: .40, body_line: .30, momentum: .15, body_sway: .15}`, and re-verify the Task 3 fixture. Rework the Task 1 config test's weight assertions accordingly.

---

## Self-review notes

- Spec coverage: analyzer config (T1–T3), enum+mappings (T4), ranking (T5), route metric (T6), frontend metric/type (T7), forms+history (T8), rollout order + prod verify (T9), stretch body-line (T10). Spec's "no new storage" holds — no migration beyond the enum.
- Deliberate deviations from full code-inclusion: T2 Step 1 and T8 Step 1 direct the implementer to mirror an existing test file's helpers rather than pasting exact code, because those helpers' names must be read from the file to avoid drift; the required behavior and assertions are specified. T10 is explicitly a stretch outline, not a buildable task yet.
- Type consistency checked: `reps` key name is identical in SQL alias (T6), attempt dict (T6), `_rank_reps` (T5), and test builder (T5); frontend uses `total_reps` from the lifts endpoint (existing field) and `metric === "reps"` from the leaderboard payload.
