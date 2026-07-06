# Achievement Milestone Path + Avatar Unlocks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A plank-first milestone ladder that awards badges (retroactively too), unlocks tiered DiceBear avatar packs, shows a badge strip on Index and the full path + avatar picker on Profile, and renders chosen avatars across challenge surfaces.

**Architecture:** Pure ladder/catalog logic in `services/achievements.py`; an append-only `Achievement` ledger + `User.avatar` key column (startup migration 015 with self-healing SQL backfill); best-effort award pass at lifting-analysis completion and on achievements read; two routes (GET achievements, PUT avatar); frontend BadgeStrip/MilestonePath/AvatarPicker components plus `avatar_url` preference in existing avatar call sites.

**Tech Stack:** Python/Flask + SQLAlchemy raw SQL (backend), TypeScript/React + Jest (frontend), DiceBear URL avatars.

## Global Constraints

- Ladder keys/titles/emoji/thresholds exactly as the spec table: `first_steps` 🌱 First Steps (any video attempt) / `half_minute` ⏱️ Half Minute (hold ≥30s) / `iron_minute` 💪 Iron Minute (≥60s) / `two_minute_club` 🔥 Two-Minute Club (≥120s) / `statue_tier` 🗿 Statue Tier (≥180s) / `plank_royalty` 👑 Plank Royalty (≥5 plank attempts AND ≥120s hold).
- Avatar packs per tier (6 each): avataaars / bottts / adventurer / lorelei / fun-emoji / legendary avataaars seeds. Keys are `<style>-<n>` (e.g. `bottts-3`).
- `User.avatar` stores a catalog **key**, never a URL. NULL → existing deterministic fallback (`getGolfAvatar`/`getGhibliAvatar`) — behavior for non-choosers is unchanged.
- Ledger is append-only; awards are never revoked. All award inserts use `ON CONFLICT DO NOTHING`.
- Award passes are best-effort: wrapped so failure never blocks analysis completion or the GET response.
- Public endpoints, consistent with the app's optional-auth model.
- Follow repo patterns: pure services + SQL-in-routes, startup-migration block in `app.py` (like 013/014), `_to_float`-style null safety, mock-session route tests like `tests/test_competition_routes.py`.

---

### Task 1: Pure achievements service (ladder, catalog, evaluate, progress)

**Files:**
- Create: `backend/toms_gym/services/achievements.py`
- Test: `backend/tests/test_achievements.py`
- Modify: `backend/tools/run_ci_tests.sh` (add the test file)

**Interfaces:**
- Produces (consumed by Tasks 2–4):
  - `LADDER: list[dict]` — ordered tiers `{key, tier, title, emoji, kind, threshold}`.
  - `AVATAR_CATALOG: dict[str, str]` — avatar key → DiceBear URL.
  - `PACKS: list[tuple[str, list[str]]]` — `(ladder_key, [avatar_keys])` per tier.
  - `evaluate(stats: dict) -> list[str]` — earned ladder keys for `{"has_upload": bool, "best_hold_s": float|None, "plank_attempts": int}`.
  - `unlocked_avatar_keys(earned_keys) -> list[str]`
  - `resolve_avatar_url(key) -> str | None`
  - `next_milestone(stats, earned_keys) -> dict | None` — `{key, title, emoji, tier, progress: {best_hold_s, needed_s, plank_attempts, needed_attempts}}` (needed fields None when not applicable).
  - `badge_total() -> int`

- [ ] **Step 1: Write the failing tests**

```python
"""DB-free tests for the achievements ladder (services/achievements.py)."""
from toms_gym.services.achievements import (
    LADDER, AVATAR_CATALOG, PACKS, evaluate, unlocked_avatar_keys,
    resolve_avatar_url, next_milestone, badge_total,
)


def _stats(has_upload=False, best_hold_s=None, plank_attempts=0):
    return {"has_upload": has_upload, "best_hold_s": best_hold_s,
            "plank_attempts": plank_attempts}


def test_ladder_shape():
    assert [t["key"] for t in LADDER] == [
        "first_steps", "half_minute", "iron_minute",
        "two_minute_club", "statue_tier", "plank_royalty",
    ]
    assert badge_total() == 6


def test_no_activity_earns_nothing():
    assert evaluate(_stats()) == []


def test_first_upload_earns_tier1_only():
    assert evaluate(_stats(has_upload=True)) == ["first_steps"]


def test_hold_thresholds_pin_boundaries():
    assert "half_minute" in evaluate(_stats(True, 30.0, 1))
    assert "half_minute" not in evaluate(_stats(True, 29.9, 1))
    assert "iron_minute" in evaluate(_stats(True, 60.0, 1))
    assert "two_minute_club" in evaluate(_stats(True, 120.0, 1))
    assert "statue_tier" in evaluate(_stats(True, 180.0, 1))


def test_royalty_needs_attempts_and_hold():
    assert "plank_royalty" not in evaluate(_stats(True, 240.0, 4))
    assert "plank_royalty" not in evaluate(_stats(True, 119.0, 9))
    assert "plank_royalty" in evaluate(_stats(True, 120.0, 5))


def test_unlocked_avatars_accumulate_by_tier():
    none = unlocked_avatar_keys([])
    t1 = unlocked_avatar_keys(["first_steps"])
    t2 = unlocked_avatar_keys(["first_steps", "half_minute"])
    assert none == []
    assert len(t1) == 6 and len(t2) == 12
    assert set(t1) <= set(t2)


def test_catalog_has_36_resolvable_avatars():
    assert len(AVATAR_CATALOG) == 36
    assert sum(len(keys) for _, keys in PACKS) == 36
    for key, url in AVATAR_CATALOG.items():
        assert resolve_avatar_url(key) == url
        assert url.startswith("https://api.dicebear.com/7.x/")
    assert resolve_avatar_url("nope-1") is None


def test_next_milestone_progress():
    nxt = next_milestone(_stats(True, 102.0, 2), ["first_steps", "half_minute", "iron_minute"])
    assert nxt["key"] == "two_minute_club"
    assert nxt["progress"]["best_hold_s"] == 102.0
    assert nxt["progress"]["needed_s"] == 120
    # all earned -> None
    assert next_milestone(_stats(True, 300.0, 9), [t["key"] for t in LADDER]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_achievements.py --noconftest -q`
Expected: FAIL — `ModuleNotFoundError: toms_gym.services.achievements`.

- [ ] **Step 3: Write the implementation**

```python
"""Milestone ladder + avatar catalog — pure and DB-free (like handicap.py).

Ladder tiers unlock 6-avatar DiceBear packs. `User.avatar` stores a catalog
key from AVATAR_CATALOG; resolution to a URL happens server-side so the
frontend never needs the catalog for display.
"""

_DICEBEAR = "https://api.dicebear.com/7.x"

LADDER = [
    {"key": "first_steps", "tier": 1, "title": "First Steps", "emoji": "🌱",
     "kind": "upload", "threshold": None},
    {"key": "half_minute", "tier": 2, "title": "Half Minute", "emoji": "⏱️",
     "kind": "hold", "threshold": 30},
    {"key": "iron_minute", "tier": 3, "title": "Iron Minute", "emoji": "💪",
     "kind": "hold", "threshold": 60},
    {"key": "two_minute_club", "tier": 4, "title": "Two-Minute Club", "emoji": "🔥",
     "kind": "hold", "threshold": 120},
    {"key": "statue_tier", "tier": 5, "title": "Statue Tier", "emoji": "🗿",
     "kind": "hold", "threshold": 180},
    {"key": "plank_royalty", "tier": 6, "title": "Plank Royalty", "emoji": "👑",
     "kind": "royalty", "threshold": None},
]

_STYLES = [
    ("first_steps", "avataaars", ["ace", "blaze", "coach", "dyno", "echo", "flex"]),
    ("half_minute", "bottts", ["bolt", "cog", "gear", "servo", "volt", "widget"]),
    ("iron_minute", "adventurer", ["arrow", "cliff", "dune", "ridge", "scout", "trail"]),
    ("two_minute_club", "lorelei", ["aria", "iris", "luna", "nova", "sage", "wren"]),
    ("statue_tier", "fun-emoji", ["beam", "grin", "jolt", "smirk", "wink", "zen"]),
    ("plank_royalty", "avataaars", ["monarch", "sovereign", "regal", "crown", "dynasty", "empire"]),
]

AVATAR_CATALOG = {}
PACKS = []
for _ladder_key, _style, _seeds in _STYLES:
    _keys = []
    for _i, _seed in enumerate(_seeds, start=1):
        # legendary pack shares the avataaars style; namespace its keys
        _key = f"{_style}-{_seed}"
        AVATAR_CATALOG[_key] = f"{_DICEBEAR}/{_style}/svg?seed={_seed}"
        _keys.append(_key)
    PACKS.append((_ladder_key, _keys))


def badge_total():
    return len(LADDER)


def evaluate(stats):
    """Earned ladder keys for {'has_upload', 'best_hold_s', 'plank_attempts'}."""
    best = stats.get("best_hold_s") or 0
    attempts = stats.get("plank_attempts") or 0
    earned = []
    for t in LADDER:
        if t["kind"] == "upload" and stats.get("has_upload"):
            earned.append(t["key"])
        elif t["kind"] == "hold" and best >= t["threshold"]:
            earned.append(t["key"])
        elif t["kind"] == "royalty" and attempts >= 5 and best >= 120:
            earned.append(t["key"])
    return earned


def unlocked_avatar_keys(earned_keys):
    earned = set(earned_keys)
    keys = []
    for ladder_key, pack in PACKS:
        if ladder_key in earned:
            keys.extend(pack)
    return keys


def resolve_avatar_url(key):
    return AVATAR_CATALOG.get(key)


def next_milestone(stats, earned_keys):
    """First unearned tier with progress numbers (None when all earned)."""
    earned = set(earned_keys)
    for t in LADDER:
        if t["key"] in earned:
            continue
        progress = {
            "best_hold_s": stats.get("best_hold_s"),
            "needed_s": t["threshold"] if t["kind"] == "hold" else (120 if t["kind"] == "royalty" else None),
            "plank_attempts": stats.get("plank_attempts") or 0,
            "needed_attempts": 5 if t["kind"] == "royalty" else None,
        }
        return {"key": t["key"], "title": t["title"], "emoji": t["emoji"],
                "tier": t["tier"], "progress": progress}
    return None
```

Note the legendary pack's keys are `avataaars-monarch` etc. — distinct seeds keep them unique against tier 1's `avataaars-ace` family.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_achievements.py --noconftest -q`
Expected: 8 passed.

- [ ] **Step 5: Register in the CI gate**

In `backend/tools/run_ci_tests.sh`, add `tests/test_achievements.py \` to the pytest file list (after `tests/test_lift_history.py \`). Run `PYTHON=venv/bin/python bash tools/run_ci_tests.sh` — expect all green.

- [ ] **Step 6: Commit**

```bash
git add backend/toms_gym/services/achievements.py backend/tests/test_achievements.py backend/tools/run_ci_tests.sh
git commit -m "feat(achievements): pure milestone ladder + avatar catalog service"
```

---

### Task 2: Migration 015 — Achievement ledger, User.avatar, SQL backfill

**Files:**
- Create: `backend/toms_gym/migrations/015_achievements.sql` (documentation copy, like 013/014)
- Modify: `backend/toms_gym/app.py` (startup-migration block, after the MagicLinkToken block ending near line 230)

**Interfaces:**
- Produces: `"Achievement"(id, user_id, achievement_key, awarded_at)` with `UNIQUE(user_id, achievement_key)`; `User.avatar VARCHAR(64)`. Backfill INSERTs run every boot, idempotent.

- [ ] **Step 1: Write the SQL file** (`015_achievements.sql`)

```sql
-- 015: Achievement ledger + user avatar key + self-healing backfill.
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS avatar VARCHAR(64);

CREATE TABLE IF NOT EXISTS "Achievement" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    achievement_key VARCHAR(64) NOT NULL,
    awarded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, achievement_key)
);
CREATE INDEX IF NOT EXISTS idx_achievement_user ON "Achievement"(user_id);
```

- [ ] **Step 2: Add the startup block to `app.py`**

Insert after the MagicLinkToken migration block, inside `run_startup_migrations()`:

```python
        # Achievement ledger + avatar key (migration 015). The per-tier
        # INSERT..SELECTs are a self-healing backfill: idempotent via the
        # UNIQUE(user_id, achievement_key) + ON CONFLICT DO NOTHING, they award
        # history on first boot and catch any missed hook awards thereafter.
        try:
            session.execute(sqlalchemy.text("""
                ALTER TABLE "User" ADD COLUMN IF NOT EXISTS avatar VARCHAR(64)
            """))
            session.execute(sqlalchemy.text("""
                CREATE TABLE IF NOT EXISTS "Achievement" (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
                    achievement_key VARCHAR(64) NOT NULL,
                    awarded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE (user_id, achievement_key)
                )
            """))
            session.execute(sqlalchemy.text("""
                CREATE INDEX IF NOT EXISTS idx_achievement_user
                    ON "Achievement"(user_id)
            """))
            # Tier 1: any attempt with a video.
            session.execute(sqlalchemy.text("""
                INSERT INTO "Achievement" (user_id, achievement_key)
                SELECT DISTINCT uc.user_id, 'first_steps'
                FROM "Attempt" a
                JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
                WHERE a.video_url IS NOT NULL
                ON CONFLICT (user_id, achievement_key) DO NOTHING
            """))
            # Hold tiers from best plank hold.
            session.execute(sqlalchemy.text("""
                WITH best AS (
                    SELECT uc.user_id,
                           MAX((lr.report->>'total_in_plank_s')::float) AS best_hold
                    FROM "LiftingResult" lr
                    JOIN "Attempt" a ON lr.attempt_id = a.id
                    JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
                    WHERE lr.report->>'total_in_plank_s' IS NOT NULL
                    GROUP BY uc.user_id
                )
                INSERT INTO "Achievement" (user_id, achievement_key)
                SELECT b.user_id, t.key
                FROM best b
                JOIN (VALUES ('half_minute', 30), ('iron_minute', 60),
                             ('two_minute_club', 120), ('statue_tier', 180)
                     ) AS t(key, needed) ON b.best_hold >= t.needed
                ON CONFLICT (user_id, achievement_key) DO NOTHING
            """))
            # Royalty: >=5 plank attempts AND a >=120s hold.
            session.execute(sqlalchemy.text("""
                WITH plank AS (
                    SELECT uc.user_id,
                           COUNT(*) FILTER (WHERE a.lift_type = 'Plank'
                                OR lr.report->>'lift_type' = 'plank') AS attempts,
                           MAX((lr.report->>'total_in_plank_s')::float) AS best_hold
                    FROM "Attempt" a
                    JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
                    LEFT JOIN "LiftingResult" lr ON lr.attempt_id = a.id
                    WHERE a.video_url IS NOT NULL
                    GROUP BY uc.user_id
                )
                INSERT INTO "Achievement" (user_id, achievement_key)
                SELECT user_id, 'plank_royalty' FROM plank
                WHERE attempts >= 5 AND best_hold >= 120
                ON CONFLICT (user_id, achievement_key) DO NOTHING
            """))
            session.commit()
            logging.info("Achievement migration/backfill complete")
        except Exception as e:
            session.rollback()
            logging.info(f"Achievement migration note: {e}")
```

- [ ] **Step 3: Verify the app still imports**

Run: `cd backend && venv/bin/python -c "import ast; ast.parse(open('toms_gym/app.py').read()); print('ok')"`
Expected: `ok`. (Startup migrations only run against a live DB; the syntax gate is what's checkable locally. The backfill is verified in production in Task 9.)

- [ ] **Step 4: Commit**

```bash
git add backend/toms_gym/migrations/015_achievements.sql backend/toms_gym/app.py
git commit -m "feat(achievements): migration 015 — ledger, avatar column, SQL backfill"
```

---

### Task 3: Award integration + achievements/avatar routes

**Files:**
- Create: `backend/toms_gym/integrations/achievement_award.py`
- Create: `backend/toms_gym/routes/achievement_routes.py`
- Modify: `backend/toms_gym/app.py` (register blueprint where the other blueprints register)
- Modify: `backend/toms_gym/integrations/lifting_processor.py:213-219` (hook after `notify_analysis_complete`)
- Test: `backend/tests/test_achievement_routes.py`

**Interfaces:**
- Consumes: Task 1's `evaluate`, `unlocked_avatar_keys`, `resolve_avatar_url`, `next_milestone`, `LADDER`, `badge_total`.
- Produces:
  - `award_for_user(session, user_id) -> list[str]` — loads stats, inserts new awards, commits; raises nothing (caller wraps).
  - `GET /users/<user_id>/achievements`, `PUT /users/<user_id>/avatar` (shapes per spec).

- [ ] **Step 1: Write the failing route tests**

Follow `tests/test_competition_routes.py`'s mock-session pattern (patch `get_db_connection`, drive the Flask test client from `conftest`-free fixtures — copy its `test_client` construction):

```python
"""Mock-DB tests for achievement routes."""
import json
from unittest.mock import MagicMock, patch

import pytest

from toms_gym.app import app


@pytest.fixture
def test_client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _session(stats_row, earned_rows, avatar=None):
    """Session mock: stats query -> stats_row, earned query -> earned_rows,
    user avatar query -> avatar. Wire by SQL text sniffing."""
    session = MagicMock()

    def execute(clause, params=None):
        sql = str(clause)
        result = MagicMock()
        if "total_in_plank_s" in sql:            # stats query
            result.fetchone.return_value = stats_row
        elif "achievement_key" in sql and sql.strip().upper().startswith("SELECT"):
            result.fetchall.return_value = earned_rows
        elif 'FROM "User"' in sql:
            result.fetchone.return_value = (avatar,)
        return result

    session.execute.side_effect = execute
    return session


def test_get_achievements_shape(test_client):
    stats = MagicMock()
    stats._mapping = {"has_upload": True, "best_hold_s": 65.0, "plank_attempts": 2}
    earned = [MagicMock(_mapping={"achievement_key": "first_steps",
                                  "awarded_at": None})]
    with patch("toms_gym.routes.achievement_routes.get_db_connection",
               return_value=_session(stats, earned)):
        resp = test_client.get("/users/u1/achievements")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["badge_total"] == 6
    assert {e["key"] for e in data["earned"]} >= {"first_steps"}
    assert data["next"] is not None
    assert isinstance(data["avatars"]["unlocked"], list)


def test_put_avatar_locked_403(test_client):
    stats = MagicMock()
    stats._mapping = {"has_upload": True, "best_hold_s": None, "plank_attempts": 0}
    earned = [MagicMock(_mapping={"achievement_key": "first_steps", "awarded_at": None})]
    with patch("toms_gym.routes.achievement_routes.get_db_connection",
               return_value=_session(stats, earned)):
        resp = test_client.put("/users/u1/avatar",
                               data=json.dumps({"avatar_key": "bottts-bolt"}),
                               content_type="application/json")
    assert resp.status_code == 403


def test_put_avatar_unknown_400(test_client):
    with patch("toms_gym.routes.achievement_routes.get_db_connection",
               return_value=_session(MagicMock(_mapping={}), [])):
        resp = test_client.put("/users/u1/avatar",
                               data=json.dumps({"avatar_key": "nope-1"}),
                               content_type="application/json")
    assert resp.status_code == 400
```

Adjust mock wiring during implementation if the SQL sniffing needs different markers — the assertion surface (200 shape / 403 locked / 400 unknown) is the contract.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && venv/bin/python -m pytest tests/test_achievement_routes.py --noconftest -q`
Expected: FAIL (404s — blueprint doesn't exist).

- [ ] **Step 3: Implement the integration module** (`integrations/achievement_award.py`)

```python
"""Best-effort achievement awarding — mirrors analysis_notify's contract:
never raises into the caller's flow; caller wraps in try/except anyway."""
import logging

import sqlalchemy

from toms_gym.services.achievements import evaluate

logger = logging.getLogger(__name__)

STATS_SQL = """
    SELECT
      EXISTS (
        SELECT 1 FROM "Attempt" a
        JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
        WHERE uc.user_id = :user_id AND a.video_url IS NOT NULL
      ) AS has_upload,
      (SELECT MAX((lr.report->>'total_in_plank_s')::float)
         FROM "LiftingResult" lr
         JOIN "Attempt" a ON lr.attempt_id = a.id
         JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
        WHERE uc.user_id = :user_id
          AND lr.report->>'total_in_plank_s' IS NOT NULL) AS best_hold_s,
      (SELECT COUNT(*)
         FROM "Attempt" a
         JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
         LEFT JOIN "LiftingResult" lr ON lr.attempt_id = a.id
        WHERE uc.user_id = :user_id AND a.video_url IS NOT NULL
          AND (a.lift_type = 'Plank' OR lr.report->>'lift_type' = 'plank')
      ) AS plank_attempts
"""


def load_stats(session, user_id):
    row = session.execute(sqlalchemy.text(STATS_SQL), {"user_id": user_id}).fetchone()
    m = row._mapping if row is not None else {}
    return {
        "has_upload": bool(m.get("has_upload")),
        "best_hold_s": float(m["best_hold_s"]) if m.get("best_hold_s") is not None else None,
        "plank_attempts": int(m.get("plank_attempts") or 0),
    }


def award_for_user(session, user_id):
    """Insert any newly-earned achievements. Returns the earned key list."""
    stats = load_stats(session, user_id)
    earned = evaluate(stats)
    for key in earned:
        session.execute(sqlalchemy.text("""
            INSERT INTO "Achievement" (user_id, achievement_key)
            VALUES (:user_id, :key)
            ON CONFLICT (user_id, achievement_key) DO NOTHING
        """), {"user_id": user_id, "key": key})
    session.commit()
    return earned


def award_for_attempt(get_conn, attempt_id):
    """Completion-hook entry: resolve the attempt's user, then award."""
    session = None
    try:
        session = get_conn()
        row = session.execute(sqlalchemy.text("""
            SELECT uc.user_id FROM "Attempt" a
            JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
            WHERE a.id = :attempt_id
        """), {"attempt_id": attempt_id}).fetchone()
        if row is not None:
            award_for_user(session, str(row[0]))
    except Exception as e:
        logger.warning(f"Achievement award failed for attempt {attempt_id}: {e}")
        if session:
            session.rollback()
    finally:
        if session:
            session.close()
```

- [ ] **Step 4: Implement the routes** (`routes/achievement_routes.py`)

```python
"""Milestone/achievement endpoints. GET runs an award-on-read pass first so
missed hook awards (e.g. tier 1 right after upload) self-heal on view."""
from flask import Blueprint, jsonify, request
import sqlalchemy

from toms_gym.db import get_db_connection
from toms_gym.integrations.achievement_award import award_for_user, load_stats
from toms_gym.services.achievements import (
    LADDER, PACKS, badge_total, next_milestone, resolve_avatar_url,
    unlocked_avatar_keys,
)

achievement_bp = Blueprint("achievements", __name__)


@achievement_bp.route("/users/<string:user_id>/achievements")
def get_achievements(user_id):
    session = None
    try:
        session = get_db_connection()
        try:
            award_for_user(session, user_id)  # award-on-read, idempotent
        except Exception:
            session.rollback()
        stats = load_stats(session, user_id)
        rows = session.execute(sqlalchemy.text("""
            SELECT achievement_key, awarded_at FROM "Achievement"
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchall()
        awarded_at = {r._mapping["achievement_key"]: r._mapping["awarded_at"]
                      for r in rows}
        earned_keys = [t["key"] for t in LADDER if t["key"] in awarded_at]
        earned = [{
            "key": t["key"], "title": t["title"], "emoji": t["emoji"],
            "tier": t["tier"],
            "awarded_at": awarded_at[t["key"]].isoformat()
                          if awarded_at.get(t["key"]) else None,
        } for t in LADDER if t["key"] in awarded_at]
        unlocked = [{"key": k, "url": resolve_avatar_url(k)}
                    for k in unlocked_avatar_keys(earned_keys)]
        locked_by_tier = {str(t["tier"]): len(pack)
                          for (lk, pack), t in zip(PACKS, LADDER)
                          if t["key"] not in awarded_at for lk in [lk]}
        avatar_row = session.execute(sqlalchemy.text(
            'SELECT avatar FROM "User" WHERE id = :user_id'
        ), {"user_id": user_id}).fetchone()
        current_key = avatar_row[0] if avatar_row else None
        current = ({"key": current_key, "url": resolve_avatar_url(current_key)}
                   if current_key else None)
        return jsonify({
            "earned": earned,
            "next": next_milestone(stats, earned_keys),
            "avatars": {"unlocked": unlocked, "locked_by_tier": locked_by_tier},
            "current_avatar": current,
            "badge_total": badge_total(),
        })
    except Exception as e:
        if session:
            session.rollback()
        return {"error": str(e)}, 500
    finally:
        if session:
            session.close()


@achievement_bp.route("/users/<string:user_id>/avatar", methods=["PUT"])
def put_avatar(user_id):
    body = request.get_json(silent=True) or {}
    key = body.get("avatar_key")
    if not key or resolve_avatar_url(key) is None:
        return {"error": "unknown avatar_key"}, 400
    session = None
    try:
        session = get_db_connection()
        rows = session.execute(sqlalchemy.text("""
            SELECT achievement_key FROM "Achievement" WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchall()
        earned = [r[0] for r in rows]
        if key not in unlocked_avatar_keys(earned):
            return {"error": "avatar not unlocked"}, 403
        session.execute(sqlalchemy.text(
            'UPDATE "User" SET avatar = :key WHERE id = :user_id'
        ), {"key": key, "user_id": user_id})
        session.commit()
        return jsonify({"key": key, "url": resolve_avatar_url(key)})
    except Exception as e:
        if session:
            session.rollback()
        return {"error": str(e)}, 500
    finally:
        if session:
            session.close()
```

Register in `app.py` next to the other blueprints:
```python
from toms_gym.routes.achievement_routes import achievement_bp
app.register_blueprint(achievement_bp)
```

- [ ] **Step 5: Add the completion hook**

In `lifting_processor.py`, directly after the `notify_analysis_complete` try/except (line ~219):

```python
        # Best-effort: award any newly-earned milestones (hold tiers land here).
        try:
            from toms_gym.integrations.achievement_award import award_for_attempt
            award_for_attempt(get_connection, str(attempt_id))
        except Exception as award_err:
            logger.warning(f"Achievement award hook failed: {award_err}")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && venv/bin/python -m pytest tests/test_achievement_routes.py tests/test_achievements.py --noconftest -q`
Expected: all pass. Then the full gate: `PYTHON=venv/bin/python bash tools/run_ci_tests.sh` (add `tests/test_achievement_routes.py \` to the file list) — all green.

- [ ] **Step 7: Commit**

```bash
git add backend/toms_gym/integrations/achievement_award.py backend/toms_gym/routes/achievement_routes.py backend/toms_gym/integrations/lifting_processor.py backend/toms_gym/app.py backend/tests/test_achievement_routes.py backend/tools/run_ci_tests.sh
git commit -m "feat(achievements): award hooks + achievements/avatar endpoints"
```

---

### Task 4: Chosen avatar propagates to leaderboard + profile responses

**Files:**
- Modify: `backend/toms_gym/routes/competition_routes.py` (leaderboard SELECT ~line 411 + participant dict ~line 445)
- Modify: `backend/toms_gym/services/challenge_leaderboard.py` (row shaping in `_rank_time` and `_rank_weight`)
- Modify: `backend/toms_gym/routes/user_routes.py` (profile response user block)
- Test: `backend/tests/test_challenge_leaderboard.py`, `backend/tests/test_competition_routes.py`

**Interfaces:**
- Produces: leaderboard rows carry `avatar_url: str|null`; profile `user` object carries `avatar: {key,url}|null`.

- [ ] **Step 1: Failing test** — in `test_challenge_leaderboard.py`, add `"avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=bolt"` to a participant dict and assert the ranked row carries it:

```python
def test_rows_carry_avatar_url():
    participants = [{
        "user_id": "u1", "name": "Ann", "weight_class": None, "gender": None,
        "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=bolt",
        "attempts": [_plank("a1", 30.0, "2026-07-01")],
    }]
    rows = rank_challenge(participants, metric="time")
    assert rows[0]["avatar_url"] == "https://api.dicebear.com/7.x/bottts/svg?seed=bolt"
```

Run: `venv/bin/python -m pytest tests/test_challenge_leaderboard.py -k avatar --noconftest -q` → FAIL (KeyError).

- [ ] **Step 2: Implement**

`challenge_leaderboard.py`: in both `_rank_time` and `_rank_weight`, the final `row.update({...})` block (the one adding `user_id`/`name`/…) gains `"avatar_url": p.get("avatar_url")`.

`competition_routes.py`: leaderboard SELECT adds `u.avatar` (after `uc.gender`); the participant dict gains `"avatar_url": resolve_avatar_url(row['avatar']) if row['avatar'] else None` (import `resolve_avatar_url` from `toms_gym.services.achievements`). Add `"avatar": None` (or the column) to `test_competition_routes.py`'s `_prow` base dict — mirroring the Task-4 lesson from the nicknames feature: route mocks must carry every selected column.

`user_routes.py` (`get_user_profile`): where the user dict is built from the user row, add
```python
from toms_gym.services.achievements import resolve_avatar_url
user_data["avatar"] = ({"key": row_avatar, "url": resolve_avatar_url(row_avatar)}
                        if row_avatar else None)
```
selecting `avatar` in the existing user query.

- [ ] **Step 3: Verify**

Run: `PYTHON=venv/bin/python bash tools/run_ci_tests.sh` → all green.

- [ ] **Step 4: Commit**

```bash
git add backend/toms_gym/routes/competition_routes.py backend/toms_gym/services/challenge_leaderboard.py backend/toms_gym/routes/user_routes.py backend/tests/test_challenge_leaderboard.py backend/tests/test_competition_routes.py
git commit -m "feat(achievements): chosen avatar on leaderboard rows + profile"
```

---

### Task 5: Frontend API client + types

**Files:**
- Create: `frontend/src/lib/achievements.ts`
- Modify: `frontend/src/lib/types.ts` (`ChallengeLeaderboardRow` gains `avatar_url: string | null`)

**Interfaces:**
- Produces (consumed by Tasks 6–8):

```ts
export interface EarnedBadge { key: string; title: string; emoji: string; tier: number; awarded_at: string | null; }
export interface NextMilestone { key: string; title: string; emoji: string; tier: number;
  progress: { best_hold_s: number | null; needed_s: number | null; plank_attempts: number; needed_attempts: number | null; }; }
export interface AvatarOption { key: string; url: string; }
export interface AchievementsResponse {
  earned: EarnedBadge[]; next: NextMilestone | null;
  avatars: { unlocked: AvatarOption[]; locked_by_tier: Record<string, number> };
  current_avatar: AvatarOption | null; badge_total: number;
}
export async function fetchAchievements(userId: string): Promise<AchievementsResponse>
export async function setAvatar(userId: string, avatarKey: string): Promise<AvatarOption>
```

- [ ] **Step 1: Implement** (axios against `API_URL`, matching `lib/api.ts` style):

```ts
import axios from "axios";
import { API_URL } from "../config";
// (interfaces from above)

export async function fetchAchievements(userId: string): Promise<AchievementsResponse> {
  const res = await axios.get(`${API_URL}/users/${userId}/achievements`);
  return res.data;
}

export async function setAvatar(userId: string, avatarKey: string): Promise<AvatarOption> {
  const res = await axios.put(`${API_URL}/users/${userId}/avatar`, { avatar_key: avatarKey });
  return res.data;
}
```

In `types.ts`, `ChallengeLeaderboardRow` gains (after `steadiness`):
```ts
  /** chosen avatar URL when the user picked one; null -> deterministic fallback. */
  avatar_url: string | null;
```
Update existing test fixtures that build full rows (`LeaderboardRow.test.tsx`, `YouRow.test.tsx` `makeRow`) with `avatar_url: null`.

- [ ] **Step 2: Verify** — `cd frontend && npx tsc --noEmit` clean; `npx jest src/components/challenge` green.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/achievements.ts frontend/src/lib/types.ts frontend/src/components/challenge/__tests__/LeaderboardRow.test.tsx frontend/src/components/challenge/__tests__/YouRow.test.tsx
git commit -m "feat(achievements): frontend API client + avatar_url type"
```

---

### Task 6: BadgeStrip on Index

**Files:**
- Create: `frontend/src/components/achievements/BadgeStrip.tsx`
- Modify: `frontend/src/pages/Index.tsx` (new section after the IconTiles grid, before "Open challenges")
- Test: `frontend/src/components/achievements/__tests__/BadgeStrip.test.tsx`

**Interfaces:**
- Consumes: `fetchAchievements` (Task 5).
- Produces: `<BadgeStrip />` — self-contained; reads localStorage `userId` itself.

- [ ] **Step 1: Failing tests** (mock `../../lib/achievements`; mock `../../config` like sibling suites):

```tsx
import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

jest.mock("../../../lib/achievements", () => ({
  fetchAchievements: jest.fn(),
}));
import { fetchAchievements } from "../../../lib/achievements";
import BadgeStrip from "../BadgeStrip";

const resp = {
  earned: [{ key: "first_steps", title: "First Steps", emoji: "🌱", tier: 1, awarded_at: null }],
  next: null,
  avatars: { unlocked: [], locked_by_tier: {} },
  current_avatar: null,
  badge_total: 6,
};

describe("BadgeStrip", () => {
  afterEach(() => { localStorage.clear(); jest.clearAllMocks(); });

  it("renders earned badges + count and links to the profile", async () => {
    localStorage.setItem("userId", "u1");
    (fetchAchievements as jest.Mock).mockResolvedValue(resp);
    render(<MemoryRouter><BadgeStrip /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/1 of 6 badges/)).toBeInTheDocument());
    expect(screen.getByRole("link")).toHaveAttribute("href", "/profile/u1");
  });

  it("renders nothing without a userId", () => {
    const { container } = render(<MemoryRouter><BadgeStrip /></MemoryRouter>);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing with zero earned badges", async () => {
    localStorage.setItem("userId", "u1");
    (fetchAchievements as jest.Mock).mockResolvedValue({ ...resp, earned: [] });
    const { container } = render(<MemoryRouter><BadgeStrip /></MemoryRouter>);
    await waitFor(() => expect(fetchAchievements).toHaveBeenCalled());
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify FAIL** — `npx jest src/components/achievements/__tests__/BadgeStrip.test.tsx` → module not found.

- [ ] **Step 3: Implement**

```tsx
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchAchievements, AchievementsResponse } from "../../lib/achievements";

/** Compact trophy shelf for the remembered visitor. Renders nothing when
 * there's no local userId, the fetch fails, or nothing is earned yet. */
const BadgeStrip: React.FC = () => {
  const [data, setData] = useState<AchievementsResponse | null>(null);
  const userId = localStorage.getItem("userId");

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    fetchAchievements(userId)
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [userId]);

  if (!userId || !data || data.earned.length === 0) return null;

  const lockedCount = data.badge_total - data.earned.length;
  return (
    <Link
      to={`/profile/${userId}`}
      className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 hover:bg-white/10 transition-colors"
      aria-label="Your milestone badges"
    >
      <span className="flex gap-1 text-lg">
        {data.earned.map((b) => (
          <span key={b.key} title={b.title}>{b.emoji}</span>
        ))}
        {Array.from({ length: lockedCount }, (_, i) => (
          <span key={`locked-${i}`} className="opacity-40">🔒</span>
        ))}
      </span>
      <span className="text-xs text-muted-foreground">
        {data.earned.length} of {data.badge_total} badges
      </span>
    </Link>
  );
};

export default BadgeStrip;
```

In `Index.tsx`, add a section between the IconTiles grid section and the "Open challenges" section:
```tsx
        <section aria-label="Your badges">
          <BadgeStrip />
        </section>
```
(with `import BadgeStrip from "../components/achievements/BadgeStrip";`). Update `Index` page test mocks if the suite stubs child components.

- [ ] **Step 4: Verify PASS** — the BadgeStrip suite + existing `Index` suite green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/achievements/BadgeStrip.tsx frontend/src/components/achievements/__tests__/BadgeStrip.test.tsx frontend/src/pages/Index.tsx frontend/src/pages/__tests__/Index.test.tsx
git commit -m "feat(achievements): badge strip on home for the remembered visitor"
```

---

### Task 7: MilestonePath + AvatarPicker on Profile

**Files:**
- Create: `frontend/src/components/achievements/MilestonePath.tsx`
- Create: `frontend/src/components/achievements/AvatarPicker.tsx`
- Modify: `frontend/src/pages/Profile.tsx` (render both above the sport tabs; picker only on own profile)
- Test: `frontend/src/components/achievements/__tests__/MilestonePath.test.tsx`, `__tests__/AvatarPicker.test.tsx`

**Interfaces:**
- Consumes: `AchievementsResponse`, `setAvatar` (Task 5).
- Produces: `<MilestonePath data={AchievementsResponse} />`; `<AvatarPicker data={AchievementsResponse} userId={string} onAvatarChange={(a: AvatarOption) => void} />`.

- [ ] **Step 1: Failing tests**

`MilestonePath.test.tsx` — earned rows show ✅ + title; the `next` milestone shows a progress line ("1:42" formatted from `best_hold_s: 102`, needed `2:00`); remaining tiers show 🔒; renders nothing when `data.earned` empty and `next` is tier 1 (fresh user sees the strip only after first badge — same hide rule as BadgeStrip):

```tsx
const data = {
  earned: [
    { key: "first_steps", title: "First Steps", emoji: "🌱", tier: 1, awarded_at: "2026-07-01T00:00:00Z" },
    { key: "half_minute", title: "Half Minute", emoji: "⏱️", tier: 2, awarded_at: null },
    { key: "iron_minute", title: "Iron Minute", emoji: "💪", tier: 3, awarded_at: null },
  ],
  next: { key: "two_minute_club", title: "Two-Minute Club", emoji: "🔥", tier: 4,
          progress: { best_hold_s: 102, needed_s: 120, plank_attempts: 2, needed_attempts: null } },
  avatars: { unlocked: [], locked_by_tier: { "5": 6, "6": 6 } },
  current_avatar: null, badge_total: 6,
};

it("shows earned, next-with-progress, and locked tiers", () => {
  render(<MilestonePath data={data as never} />);
  expect(screen.getByText(/First Steps/)).toBeInTheDocument();
  expect(screen.getByText(/Two-Minute Club/)).toBeInTheDocument();
  expect(screen.getByText(/1:42/)).toBeInTheDocument();   // best hold
  expect(screen.getByText(/85%/)).toBeInTheDocument();     // 102/120
  expect(screen.getAllByText("🔒").length).toBe(2);        // tiers 5,6
});
```

`AvatarPicker.test.tsx` — unlocked avatars render as buttons; clicking one calls `setAvatar` and `onAvatarChange`; locked tiers render hint rows, not buttons; current avatar is marked selected:

```tsx
jest.mock("../../../lib/achievements", () => ({ setAvatar: jest.fn() }));

it("selects an unlocked avatar", async () => {
  (setAvatar as jest.Mock).mockResolvedValue({ key: "bottts-bolt", url: "https://x/bolt" });
  const onChange = jest.fn();
  render(<AvatarPicker data={dataWithUnlocked as never} userId="u1" onAvatarChange={onChange} />);
  fireEvent.click(screen.getByRole("button", { name: /bottts-bolt/i }));
  await waitFor(() => expect(setAvatar).toHaveBeenCalledWith("u1", "bottts-bolt"));
  expect(onChange).toHaveBeenCalled();
});

it("locked tiers show an unlock hint, no buttons", () => {
  render(<AvatarPicker data={dataAllLocked as never} userId="u1" onAvatarChange={() => {}} />);
  expect(screen.queryAllByRole("button")).toHaveLength(0);
  expect(screen.getByText(/unlock/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run to verify FAIL**, then **Step 3: Implement**

`MilestonePath.tsx`: ordered list over all 6 tiers derived from `data` (earned → ✅ emoji title + date; `next` → ◯ + progress bar `min(100, round(best/needed*100))%` and `m:ss` formatting; others → 🔒 + title). Progress bar is a simple `div` width; reuse the muted-pill styling family (`border-white/10 bg-white/5`).

`AvatarPicker.tsx`: header "Avatar" + grid of `data.avatars.unlocked` as `<button>` with `<img src={url} alt={key}>`, ring highlight on `current_avatar.key`; on click: optimistic set → `setAvatar(userId, key)` → `onAvatarChange(result)`, revert on error. Below, one row per entry of `locked_by_tier`: "🔒 6 more — unlock at Tier N".

`Profile.tsx`: fetch achievements alongside the existing profile Promise.all (non-fatal `.catch(() => null)`); render `<MilestonePath data={ach} />` above the sport tabs when present; render `<AvatarPicker …>` only when `resolvedUserId === localStorage.getItem("userId")`; profile header avatar prefers `user.avatar?.url` over the deterministic fallback; `onAvatarChange` updates local state so the header swaps instantly.

- [ ] **Step 4: Verify** — new suites + full `npx jest` + `npx tsc --noEmit` green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/achievements frontend/src/pages/Profile.tsx
git commit -m "feat(achievements): milestone path + avatar picker on profile"
```

---

### Task 8: Chosen avatar preference in challenge components

**Files:**
- Modify: `frontend/src/components/challenge/Podium.tsx`, `LeaderboardRow.tsx`, `MomentumLine.tsx`
- Test: extend `frontend/src/components/challenge/__tests__/LeaderboardRow.test.tsx`

**Interfaces:**
- Consumes: `row.avatar_url` (Tasks 4–5).

- [ ] **Step 1: Failing test** — in `LeaderboardRow.test.tsx`:

```tsx
test("prefers the chosen avatar_url over the deterministic fallback", () => {
  renderRow(makeRow({ avatar_url: "https://chosen/av.svg" }), "time",
            "/challenges/1/participants/u4/video/9");
  const img = screen.getByRole("presentation", { hidden: true }) as HTMLImageElement;
  expect(img.src).toBe("https://chosen/av.svg");
});
```

(The avatar `<img>` is `aria-hidden`; query via `row.querySelector('img[aria-hidden="true"]')` if the role query is awkward — pin during implementation.)

- [ ] **Step 2: Implement** — in each component, replace `src={getGolfAvatar(row.name, row.user_id)}` with `src={row.avatar_url || getGolfAvatar(row.name, row.user_id)}` (MomentumLine iterates joined users — apply the same pattern to whatever field its row exposes; if its data source lacks `avatar_url`, leave MomentumLine unchanged and note it in the commit body).

- [ ] **Step 3: Verify** — challenge suites + tsc green.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/challenge
git commit -m "feat(achievements): render chosen avatars on challenge surfaces"
```

---

### Task 9: Full gates, deploy, production verification

**Files:** none.

- [ ] **Step 1: Gates** — `PYTHON=venv/bin/python bash backend/tools/run_ci_tests.sh` and `cd frontend && npx tsc --noEmit && npx jest` — all green.

- [ ] **Step 2: Deploy** — `python3 deploy.py --skip-iam` (full: backend + frontend).

- [ ] **Step 3: Verify backfill + endpoint** — robert23kim (2 plank attempts, best 239.1s) should hold tiers 1–5, not 6:

```bash
curl -s "https://my-python-backend-quyiiugyoq-ue.a.run.app/users/2a1e1fe7-b337-43d4-a6c0-8fa81de77113/achievements" | python3 -m json.tool
```
Expected: 5 earned keys (`first_steps`…`statue_tier`), `next.key == "plank_royalty"`, 30 unlocked avatars.

- [ ] **Step 4: Verify UI in a browser** (Playwright MCP): Index shows the badge strip for a remembered user; profile shows the milestone path with progress; pick an avatar on own profile → header swaps; challenge leaderboard shows the chosen avatar. Screenshot each. **Render the pages — tsc does not catch scope bugs** (see the nicknames `metric` incident).

- [ ] **Step 5: Document** — add a "Milestone Path + Avatar Unlocks (shipped …)" section to `CLAUDE.md` following the existing feature-section format; commit.

```bash
git add CLAUDE.md && git commit -m "docs: record achievement milestone path + avatar unlocks"
```

---

## Self-Review

**Spec coverage:** ladder+catalog (T1) · migration+backfill (T2) · hooks+endpoints (T3) · avatar propagation (T4) · client/types (T5) · home strip (T6) · profile path+picker (T7) · challenge avatars (T8) · deploy+verify+docs (T9). Every spec section maps to a task.

**Placeholder scan:** none — all steps carry concrete code or exact commands. Two intentionally-pinned-at-implementation details are flagged inline (mock SQL sniffing markers in T3; MomentumLine data source in T8).

**Type consistency:** `avatar_key` in PUT body everywhere; `avatar_url` on rows; catalog keys `<style>-<seed>`; `AchievementsResponse` shape identical in T3 route, T5 types, T6/T7 fixtures.
