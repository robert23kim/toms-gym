# Challenge Champions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reusable "challenge champion" system — trophy case / title flair / avatar pack / confetti on the winner's profile plus a front-page spotlight — with wonder725 (Summer plank challenge, 4:35 hold) as the first recipient.

**Architecture:** A cached `GET /champions` endpoint computes champions on read (rank 1 of each ended challenge's leaderboard, reusing the existing leaderboard builder). The unmerged `achievements/milestone-avatar-unlocks` branch is merged first; its pure catalog service gains a Champion avatar pack unlocked by holding ≥1 championship. Frontend consumes `/champions` in three places: Profile (trophy case, flair, confetti), ChallengeDetail (👑 on rows), Index (spotlight card).

**Tech Stack:** Flask + SQLAlchemy text queries (backend), React + TS + jest (frontend), DiceBear URLs for avatars, CSS keyframes for confetti (no new deps).

**Spec:** `docs/superpowers/specs/2026-08-01-challenge-champions-design.md`

## Global Constraints

- Pure/DB-free service modules (like `handicap.py`); routes only load data and shape responses.
- All new backend suites must be DB-free and registered in `backend/tools/run_ci_tests.sh`.
- Frontend page tests mock `../../config` and stub `Layout`/`Navbar` (established pattern).
- `/champions` failures are non-fatal everywhere in the UI (components render nothing).
- No new npm/pip dependencies.
- `ChallengeDetail` changes MUST be verified in a real browser before deploy (block-scope bug class invisible to tsc).
- Deploys: `python3 deploy.py --backend-only --skip-iam` / `--frontend-only` — then verify at https://my-frontend-quyiiugyoq-ue.a.run.app.

---

### Task 1: Merge achievements branch

**Files:**
- Merge: branch `achievements/milestone-avatar-unlocks` (adds `backend/toms_gym/services/achievements.py`, `backend/tests/test_achievements.py`, `run_ci_tests.sh` line)

**Interfaces:**
- Produces: `services/achievements.py` with `LADDER`, `AVATAR_CATALOG`, `PACKS`, `evaluate(stats)`, `unlocked_avatar_keys(earned_keys)`, `resolve_avatar_url(key)`, `next_milestone(stats, earned_keys)`.

- [ ] **Step 1: Merge and run its tests**

```bash
git merge achievements/milestone-avatar-unlocks --no-edit
cd backend && venv/bin/python -m pytest tests/test_achievements.py --noconftest -q
```
Expected: merge clean (branch is ahead-of-main only by f45ebc1), tests PASS.

- [ ] **Step 2: Run the full backend CI gate**

```bash
cd backend && bash tools/run_ci_tests.sh
```
Expected: all suites pass. (Merge commit already exists; no extra commit needed.)

---

### Task 2: Pure champions service

**Files:**
- Create: `backend/toms_gym/services/champions.py`
- Test: `backend/tests/test_champions.py`
- Modify: `backend/tools/run_ci_tests.sh` (add the suite)

**Interfaces:**
- Consumes: leaderboard payload shape from the existing `/competitions/<id>/leaderboard` route: `{"metric": "time"|"weight", "rows": [{"user_id","name","rank","score","attempt_id",...}]}`.
- Produces: `shape_champions(ended) -> list[dict]` where `ended` is `[{"competition": {"id","name","end_date"}, "leaderboard": payload}]` and each result dict is `{"user_id","name","competition_id","competition_name","metric","score","ended_on","attempt_id"}`, sorted newest `ended_on` first.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_champions.py
"""Pure champion shaping — DB-free."""
from toms_gym.services.champions import shape_champions


def _comp(cid, name, end):
    return {"id": cid, "name": name, "end_date": end}


def _lb(metric, rows):
    return {"metric": metric, "rows": rows}


def _row(rank, name, uid, score, attempt="a1"):
    return {"rank": rank, "name": name, "user_id": uid, "score": score,
            "attempt_id": attempt}


def test_rank_one_becomes_champion():
    out = shape_champions([{
        "competition": _comp("c1", "Summer plank challenge", "2026-07-31"),
        "leaderboard": _lb("time", [_row(1, "wonder725", "u1", 275.4),
                                    _row(2, "victoria", "u2", 244.9)]),
    }])
    assert len(out) == 1
    c = out[0]
    assert c["name"] == "wonder725"
    assert c["user_id"] == "u1"
    assert c["competition_name"] == "Summer plank challenge"
    assert c["metric"] == "time"
    assert c["score"] == 275.4
    assert c["ended_on"] == "2026-07-31"
    assert c["attempt_id"] == "a1"


def test_challenge_with_no_valued_entries_produces_no_champion():
    out = shape_champions([{
        "competition": _comp("c1", "Empty", "2026-07-31"),
        "leaderboard": _lb("time", [_row(1, "joiner", "u1", 0),
                                    _row(2, "joiner2", "u2", None)]),
    }])
    assert out == []


def test_sorted_newest_ended_first():
    out = shape_champions([
        {"competition": _comp("old", "Old", "2026-05-01"),
         "leaderboard": _lb("weight", [_row(1, "a", "u1", 100)])},
        {"competition": _comp("new", "New", "2026-07-31"),
         "leaderboard": _lb("time", [_row(1, "b", "u2", 200)])},
    ])
    assert [c["competition_id"] for c in out] == ["new", "old"]


def test_missing_leaderboard_is_skipped():
    out = shape_champions([{"competition": _comp("c1", "Broken", "2026-07-31"),
                            "leaderboard": None}])
    assert out == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && venv/bin/python -m pytest tests/test_champions.py --noconftest -q
```
Expected: FAIL — `ModuleNotFoundError: toms_gym.services.champions`.

- [ ] **Step 3: Write the implementation**

```python
# backend/toms_gym/services/champions.py
"""Champion records from ended challenges — pure and DB-free.

A champion is rank 1 of an ended challenge's leaderboard with a truthy
score. No Champion table: recomputing on read lets late re-analyses
self-correct (route layer adds a short TTL cache).
"""


def shape_champions(ended):
    """ended: [{"competition": {id,name,end_date}, "leaderboard": payload}]"""
    champions = []
    for item in ended or []:
        comp = item.get("competition") or {}
        lb = item.get("leaderboard") or {}
        rows = lb.get("rows") or []
        top = next((r for r in rows if r.get("rank") == 1 and r.get("score")), None)
        if top is None:
            continue
        champions.append({
            "user_id": top.get("user_id"),
            "name": top.get("name"),
            "competition_id": comp.get("id"),
            "competition_name": comp.get("name"),
            "metric": lb.get("metric"),
            "score": top.get("score"),
            "ended_on": comp.get("end_date"),
            "attempt_id": top.get("attempt_id"),
        })
    champions.sort(key=lambda c: str(c["ended_on"] or ""), reverse=True)
    return champions
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && venv/bin/python -m pytest tests/test_champions.py --noconftest -q
```
Expected: 4 passed.

- [ ] **Step 5: Register in CI gate and commit**

Add to `backend/tools/run_ci_tests.sh` next to the other `--noconftest` suites:
```bash
venv/bin/python -m pytest tests/test_champions.py --noconftest -q
```
```bash
git add backend/toms_gym/services/champions.py backend/tests/test_champions.py backend/tools/run_ci_tests.sh
git commit -m "feat(champions): pure champion shaping service"
```

---

### Task 3: `GET /champions` route with TTL cache

**Files:**
- Modify: `backend/toms_gym/routes/competition_routes.py` (extract leaderboard builder ~lines 386–507; add route)

**Interfaces:**
- Consumes: `shape_champions` (Task 2); existing leaderboard code.
- Produces: `GET /champions?user_id=` → `{"champions": [shape_champions record, ...]}`. Also `_leaderboard_payload(session, competition_id) -> dict | None` (None when competition missing) as an internal helper the existing leaderboard route now delegates to.

- [ ] **Step 1: Extract the leaderboard builder**

Refactor the body of the existing leaderboard route into a module-level function, leaving the route as a thin wrapper (same behavior, same response):

```python
def _leaderboard_payload(session, competition_id):
    """Build the leaderboard response dict, or None if competition missing."""
    # body moved verbatim from the route: comp fetch -> None instead of 404,
    # declared/_parse_lifttypes, rows query, participants fold, metric
    # selection, rank_challenge, momentum, return dict
```

Route wrapper keeps the 404 and error handling:

```python
@competition_bp.route('/competitions/<string:competition_id>/leaderboard')
def get_competition_leaderboard(competition_id):
    session = None
    try:
        session = get_db_connection()
        payload = _leaderboard_payload(session, competition_id)
        if payload is None:
            return {"error": "Competition not found"}, 404
        return payload
    except Exception as e:
        ...  # unchanged error block
```

- [ ] **Step 2: Add the champions route**

```python
_champions_cache = {"at": 0.0, "data": None}
_CHAMPIONS_TTL_S = 600  # computed-on-read + cache; staleness <= 10 min accepted


@competition_bp.route('/champions')
def get_champions():
    """Champions of ended challenges (rank 1), newest first. ?user_id= filters."""
    import time as _time
    from toms_gym.services.champions import shape_champions

    session = None
    try:
        now = _time.monotonic()
        data = _champions_cache["data"]
        if data is None or now - _champions_cache["at"] > _CHAMPIONS_TTL_S:
            session = get_db_connection()
            comps = session.execute(
                sqlalchemy.text("""
                    SELECT id, name, end_date FROM "Competition"
                    WHERE end_date < NOW()
                    ORDER BY end_date DESC
                """)
            ).mappings().fetchall()
            ended = []
            for c in comps:
                lb = _leaderboard_payload(session, str(c["id"]))
                ended.append({
                    "competition": {"id": str(c["id"]), "name": c["name"],
                                    "end_date": c["end_date"].date().isoformat()},
                    "leaderboard": lb,
                })
            data = shape_champions(ended)
            _champions_cache.update(at=now, data=data)
        user_id = request.args.get("user_id")
        if user_id:
            data = [c for c in data if c["user_id"] == user_id]
        return {"champions": data}
    except Exception as e:
        logger.error(f"Error fetching champions: {str(e)}")
        logger.error(traceback.format_exc())
        if session:
            session.rollback()
        return {"error": f"Server error: {type(e).__name__}"}, 500
    finally:
        if session:
            session.close()
```

- [ ] **Step 3: Verify locally against Postgres**

Spin the disposable Postgres from CLAUDE.md if not running, run the existing route test suite plus a smoke import:

```bash
cd backend && venv/bin/python -c "import toms_gym.routes.competition_routes"
bash tools/run_ci_tests.sh
```
Expected: import clean, CI gate green.

- [ ] **Step 4: Commit**

```bash
git add backend/toms_gym/routes/competition_routes.py
git commit -m "feat(champions): GET /champions endpoint with 10-min cache"
```

---

### Task 4: Champion avatar pack + achievements/avatar routes

**Files:**
- Modify: `backend/toms_gym/services/achievements.py` (champion pack), `backend/tests/test_achievements.py`
- Create: `backend/toms_gym/routes/achievement_routes.py`, `backend/toms_gym/migrations/015_user_avatar.sql`
- Modify: blueprint registration (where other `*_bp` are registered, see `toms_gym/__init__.py` or `app.py`), startup-migration list (pattern of migrations 012–014), profile endpoint in `user_routes.py` (return `avatar_url`)

**Interfaces:**
- Consumes: `AVATAR_CATALOG`/`PACKS`/`evaluate`/`unlocked_avatar_keys`/`resolve_avatar_url` (Task 1); `GET /champions?user_id=` computation path (Task 3 — call `shape_champions` internally, not via HTTP).
- Produces:
  - `GET /users/<id>/achievements` → `{"ladder": [...], "earned": [keys], "next": next_milestone(...), "avatar_keys": [unlocked keys], "avatar": current key|null}`
  - `PUT /users/<id>/avatar` body `{"key": str}` → 200 `{"avatar": key, "avatar_url": url}` | 400 on locked/unknown key
  - Profile endpoint gains `user.avatar_url` (resolved; null when unset).

- [ ] **Step 1: Failing tests for the champion pack (pure part)**

Append to `backend/tests/test_achievements.py`:

```python
from toms_gym.services.achievements import (
    AVATAR_CATALOG, CHAMPION_PACK_KEYS, unlocked_avatar_keys,
)


def test_champion_pack_exists_and_resolves():
    assert len(CHAMPION_PACK_KEYS) == 6
    for key in CHAMPION_PACK_KEYS:
        assert key in AVATAR_CATALOG


def test_champion_pack_unlocked_only_via_champion_key():
    assert not set(CHAMPION_PACK_KEYS) & set(unlocked_avatar_keys(["first_steps"]))
    assert set(CHAMPION_PACK_KEYS) <= set(unlocked_avatar_keys(["champion"]))
```

Run: `cd backend && venv/bin/python -m pytest tests/test_achievements.py --noconftest -q` — expected FAIL (`CHAMPION_PACK_KEYS` undefined).

- [ ] **Step 2: Implement the pack**

In `services/achievements.py`, append to `_STYLES` (before the derivation loop) — gold-themed seeds, `big-smile` style keeps keys unique:

```python
    ("champion", "big-smile", ["goldie", "laurel", "victor", "trophy", "glory", "champ"]),
```

`"champion"` is a pack key, not a LADDER tier — `unlocked_avatar_keys` already unlocks any pack whose key is in `earned_keys`; callers append `"champion"` when championships ≥ 1. After the loop add:

```python
CHAMPION_PACK_KEYS = dict(PACKS)["champion"]
```

Re-run the suite — expected PASS.

- [ ] **Step 3: Migration 015 (User.avatar)**

`backend/toms_gym/migrations/015_user_avatar.sql`, registered in the startup-migration runner exactly like 013/014:

```sql
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS avatar TEXT;
```

- [ ] **Step 4: Routes**

`backend/toms_gym/routes/achievement_routes.py` (follow the session/error idiom of `competition_routes.py`):

```python
from flask import Blueprint, request
import sqlalchemy
from toms_gym.db import get_db_connection  # match existing import path
from toms_gym.services import achievements
from toms_gym.services.champions import shape_champions

achievement_bp = Blueprint('achievement', __name__)


def _user_stats(session, user_id):
    row = session.execute(sqlalchemy.text("""
        SELECT COUNT(a.id) AS uploads,
               MAX((lr.report->>'total_in_plank_s')::float) AS best_hold,
               COUNT(*) FILTER (WHERE a.lift_type = 'Plank') AS plank_attempts
        FROM "Attempt" a
        JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
        LEFT JOIN "LiftingResult" lr ON lr.attempt_id = a.id
        WHERE uc.user_id = :uid AND a.status <> 'failed'
    """), {"uid": user_id}).mappings().fetchone()
    return {"has_upload": (row["uploads"] or 0) > 0,
            "best_hold_s": row["best_hold"],
            "plank_attempts": row["plank_attempts"] or 0}


def _championship_count(session, user_id):
    # reuse the champions computation (cached path lives in competition_routes;
    # here a direct count of ended comps won by the user is enough)
    from toms_gym.routes.competition_routes import _leaderboard_payload
    comps = session.execute(sqlalchemy.text(
        'SELECT id, name, end_date FROM "Competition" WHERE end_date < NOW()'
    )).mappings().fetchall()
    ended = [{"competition": {"id": str(c["id"]), "name": c["name"],
                              "end_date": str(c["end_date"])},
              "leaderboard": _leaderboard_payload(session, str(c["id"]))}
             for c in comps]
    return sum(1 for ch in shape_champions(ended) if ch["user_id"] == user_id)


@achievement_bp.route('/users/<string:user_id>/achievements')
def get_achievements(user_id):
    ...  # session boilerplate
    stats = _user_stats(session, user_id)
    earned = achievements.evaluate(stats)
    if _championship_count(session, user_id) >= 1:
        earned.append("champion")
    current = session.execute(sqlalchemy.text(
        'SELECT avatar FROM "User" WHERE id = :uid'), {"uid": user_id}
    ).scalar()
    return {
        "ladder": achievements.LADDER,
        "earned": earned,
        "next": achievements.next_milestone(stats, earned),
        "avatar_keys": achievements.unlocked_avatar_keys(earned),
        "avatar": current,
    }


@achievement_bp.route('/users/<string:user_id>/avatar', methods=['PUT'])
def put_avatar(user_id):
    ...  # session boilerplate
    key = (request.get_json(silent=True) or {}).get("key")
    stats = _user_stats(session, user_id)
    earned = achievements.evaluate(stats)
    if _championship_count(session, user_id) >= 1:
        earned.append("champion")
    if key not in achievements.unlocked_avatar_keys(earned):
        return {"error": "avatar locked or unknown"}, 400
    session.execute(sqlalchemy.text(
        'UPDATE "User" SET avatar = :k WHERE id = :uid'),
        {"k": key, "uid": user_id})
    session.commit()
    return {"avatar": key, "avatar_url": achievements.resolve_avatar_url(key)}
```

Register `achievement_bp` beside the other blueprints. In the profile endpoint (`user_routes.py`), add `avatar` to the user SELECT and `"avatar_url": achievements.resolve_avatar_url(row["avatar"]) if row["avatar"] else None` to the `user` dict.

- [ ] **Step 5: Validate + commit**

```bash
cd backend && bash tools/run_ci_tests.sh
git add -A backend && git commit -m "feat(champions): champion avatar pack + achievements/avatar routes + User.avatar migration"
```

---

### Task 5: Frontend API client + types

**Files:**
- Modify: `frontend/src/lib/api.ts`

**Interfaces:**
- Produces:

```ts
export interface Champion {
  user_id: string; name: string; competition_id: string;
  competition_name: string; metric: "time" | "weight";
  score: number; ended_on: string; attempt_id: string | null;
}
export async function fetchChampions(userId?: string): Promise<Champion[]>
export interface AchievementsResponse {
  ladder: { key: string; tier: number; title: string; emoji: string }[];
  earned: string[]; avatar_keys: string[]; avatar: string | null;
  next: { key: string; title: string; emoji: string; tier: number } | null;
}
export async function fetchAchievements(userId: string): Promise<AchievementsResponse>
export async function setAvatar(userId: string, key: string): Promise<{ avatar: string; avatar_url: string }>
export const formatChampionScore = (metric: "time" | "weight", score: number): string
```

- [ ] **Step 1: Implement** (follow the `fetchTickets` idiom — axios/fetch per file convention; `fetchChampions` returns `res.champions ?? []`, errors propagate to callers who treat them as non-fatal). `formatChampionScore`: `time` → `m:ss` (`275.4 → "4:35"`, floor seconds, pad), `weight` → `` `${score} kg` ``.

- [ ] **Step 2: Jest test for `formatChampionScore`** in `frontend/src/lib/__tests__/champions.test.ts`: `("time", 275.4) → "4:35"`, `("time", 59.9) → "0:59"`, `("weight", 120) → "120 kg"`. Run `npx jest champions` — pass.

- [ ] **Step 3: Commit** — `feat(champions): champions/achievements API client + score formatting`.

---

### Task 6: TrophyCase on Profile

**Files:**
- Create: `frontend/src/components/profile/TrophyCase.tsx`, `frontend/src/components/profile/__tests__/TrophyCase.test.tsx`
- Modify: `frontend/src/pages/Profile.tsx` (fetch champions for the profile user; render above the tab strip, flair under the name at line ~250)

**Interfaces:**
- Consumes: `fetchChampions(userId)`, `formatChampionScore` (Task 5).
- Produces: `<TrophyCase champions={Champion[]} />` — renders nothing when empty; `championTitle(c: Champion): string` exported from TrophyCase, e.g. `👑 Summer plank challenge Champion 2026` (year from `ended_on`).

- [ ] **Step 1: Failing tests** — renders a 🏆 card per championship with name/score/date; renders null for `[]`; `championTitle` formats the flair string.
- [ ] **Step 2: Implement** — RowCard-style muted cards (match `AttemptHistory` styling): `🏆 {competition_name}` · `{formatChampionScore(metric, score)}` · `{ended_on}`. Flair in Profile: under `<h1>{profileData.user.name}</h1>` render `championTitle(latest)` in a small amber pill when champions non-empty.
- [ ] **Step 3: Run jest, verify pass, commit** — `feat(champions): trophy case + champion title flair on profile`.

---

### Task 7: Confetti entrance

**Files:**
- Create: `frontend/src/components/profile/ChampionConfetti.tsx` + test
- Modify: `frontend/src/index.css` (keyframes), `frontend/src/pages/Profile.tsx`

**Interfaces:**
- Consumes: champions list already fetched in Profile (Task 6).
- Produces: `<ChampionConfetti competitionId={string} userId={string} />` — on mount, if `localStorage["champ-confetti-<competitionId>-<userId>"]` unset: sets it, renders ~40 absolutely-positioned falling squares (CSS `confetti-fall` keyframes, 5 brand colors, randomized `left`/`animation-delay` via index math, `animation: confetti-fall 2.5s ease-in forwards`) + a "👑 Champion!" toast (existing toast util if present, else a self-dismissing div). Honors `prefers-reduced-motion` (renders toast only). Renders null on revisit.

- [ ] **Step 1: Failing test** — first render sets the localStorage key and shows the 👑 toast; second render (key present) renders null.
- [ ] **Step 2: Implement + keyframes** (`@keyframes confetti-fall { from { transform: translateY(-10vh) rotate(0); opacity: 1 } to { transform: translateY(110vh) rotate(720deg); opacity: 0 } }` next to the `demo-*` block).
- [ ] **Step 3: Jest pass, commit** — `feat(champions): one-time confetti entrance for champions`.

---

### Task 8: 👑 flair on challenge leaderboard rows

**Files:**
- Modify: `frontend/src/pages/ChallengeDetail.tsx` (fetch champions when the challenge has ended; pass a `champion` flag), `frontend/src/components/challenge/LeaderboardRow.tsx` (and `YouRow`/podium chips if they render names)

**Interfaces:**
- Consumes: `fetchChampions()` (Task 5), challenge end state already on the page.
- Produces: 👑 emoji before the name on the row whose `user_id` matches the challenge's champion; nothing for ongoing challenges.

- [ ] **Step 1: Failing test** — extend the existing `ChallengeDetail`/`LeaderboardRow` suites: ended challenge + matching champion → 👑 rendered; ongoing → not.
- [ ] **Step 2: Implement** — component-scoped state (`champions`), fetched only when `status === 'completed'`; **read component-scoped variables, not block-scoped destructures** (the `rowNickname` bug class).
- [ ] **Step 3: Jest pass, commit** — `feat(champions): crown flair on ended-challenge leaderboard rows`.

---

### Task 9: Avatar picker drawer

**Files:**
- Create: `frontend/src/components/profile/AvatarPicker.tsx` + test
- Modify: `frontend/src/pages/Profile.tsx` (owner-only entry point next to the avatar; owner = `localStorage userId === profile id`, matching existing owner checks)

**Interfaces:**
- Consumes: `fetchAchievements`, `setAvatar` (Task 5).
- Produces: drawer (follow `TeePickerDrawer.tsx` interaction pattern) listing all packs from `ladder` order + Champion pack; unlocked keys render as selectable DiceBear `<img>`s, locked packs greyed with the tier's `emoji + title` hint ("👑 Win a challenge" for the champion pack); selecting calls `setAvatar` and updates the profile avatar in place; PUT 400 keeps prior selection and shows the error.

- [ ] **Step 1: Failing tests** — locked pack greyed + hint text; unlocked selectable; `setAvatar` called with the picked key.
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Jest pass, commit** — `feat(champions): avatar picker with milestone/champion pack unlocks`.

---

### Task 10: Front-page ChampionSpotlight

**Files:**
- Create: `frontend/src/components/ChampionSpotlight.tsx`, `frontend/src/components/__tests__/ChampionSpotlight.test.tsx`
- Modify: `frontend/src/pages/Index.tsx` (between DemoLoop section and verticals grid), `frontend/src/pages/__tests__/Index.test.tsx`

**Interfaces:**
- Consumes: `fetchChampions()`, `formatChampionScore`, `getGolfAvatar(name, id)` for the avatar image.
- Produces: `<ChampionSpotlight />` — self-fetching; renders latest champion as an ambient celebratory card: avatar, `👑 {name}`, `{competition_name} champion — {formatChampionScore(...)}`, links "View profile" → `/profile/{user_id}` and "Watch the win" → `/challenges/{competition_id}/participants/{user_id}/video/{attempt_id}` (omit when `attempt_id` null). Hidden (null) when fetch fails or list empty.

- [ ] **Step 1: Failing tests** — renders name/score/links from a mocked fetch; renders null on empty and on rejection.
- [ ] **Step 2: Implement + wire into Index** (own `<section aria-label="Latest champion">`).
- [ ] **Step 3: Jest pass, commit** — `feat(champions): front-page champion spotlight card`.

---

### Task 11: Full validation, deploy, prod verification loop

**Files:** none new.

- [ ] **Step 1: Full local gate**

```bash
cd frontend && npx tsc --noEmit && npx jest
cd ../backend && bash tools/run_ci_tests.sh
```
Expected: all green. Fix anything red before proceeding.

- [ ] **Step 2: Browser check before deploy** — run the frontend locally against prod backend; load `/`, `/profile/f3b7a7d6-846d-4ef1-989b-e80a83a6da28` (wonder725), and the ended plank challenge page `/challenges/a0f27fa4-5874-4379-9bd8-23ad842255cf`; confirm no console errors (the tsc-invisible scope-bug class).

- [ ] **Step 3: Deploy backend, verify API**

```bash
python3 deploy.py --backend-only --skip-iam
curl -s "https://my-python-backend-quyiiugyoq-ue.a.run.app/champions" | python3 -m json.tool
```
Expected: wonder725 as champion of the Summer plank challenge, score ≈ 275.4.

- [ ] **Step 4: Deploy frontend, verify in prod browser** — front page shows the spotlight; wonder725's profile shows trophy case + flair + (first visit) confetti; plank challenge leaderboard shows 👑; avatar picker shows the champion pack unlocked for wonder725.

```bash
python3 deploy.py --frontend-only --skip-iam
```

- [ ] **Step 5: Loop until green** — any failure at steps 3–4: fix, re-run the local gate, redeploy the affected half, re-verify. Repeat until all prod checks pass.

- [ ] **Step 6: Update docs + commit** — add a "Challenge Champions" section to `toms_gym/CLAUDE.md` (endpoint, cache, components, migration 015) and commit `docs(champions): record challenge champions feature`.
