# Bowling Score Sheet Photos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Photograph an end-of-night RESULTS screen or a per-game lane screen, parse it with Vision OCR, store every game, and show insights on what to work on.

**Architecture:** Golf-style pipeline — Vision `document_text_detection` → pure DB-free parser (`services/bowling_sheet_parser.py`) → pure ten-pin scoring engine (`services/bowling_score.py`) validates → rows stored in `BowlingScoreSheet`/`BowlingGame` (migration 017) → review page for corrections/claiming → `services/bowling_insights.py` computes stats + tips for `/bowling/insights/<user_id>`.

**Tech Stack:** Flask + raw `sqlalchemy.text`, google-cloud-vision (already a dep), Pillow; React + TS + axios + jest.

**Spec:** `docs/superpowers/specs/2026-08-28-bowling-scoresheet-design.md`

## Global Constraints

- No new Python deps; no new secrets; Vision via ADC exactly like `golf_routes._run_ocr`.
- Pure services must not import Flask/DB and must be registered in `backend/tools/run_ci_tests.sh`.
- Migration = `backend/toms_gym/migrations/017_bowling_scoresheets.sql` **and** a block in `run_startup_migrations()` in `backend/toms_gym/app.py` (pattern of migration 014, lines ~225–252).
- Frontend: no `any`; page tests mock `../../config` and stub `Layout`; conventional commits, one per task.
- Roll symbols stored as printed strings: `"X"`, `"/"`, `"-"`, `"F"`, `"0"`–`"9"`.
- Truth fixtures in `backend/tests/fixtures/bowling/` are authoritative; parser tests must match them exactly.

## Work split (parallel)

| Branch / worktree | Owner | Tasks |
|---|---|---|
| `feat/bowling-sheet-backend` | doer-1 | 1, 2, 4, 5 |
| `feat/bowling-sheet-frontend` | doer-2 | 6, 7, 8, 9, 10 |
| `feat/bowling-scoresheet` (main feature branch) | lead | 3 (parser + OCR fixtures + debug tool), 11 (merge, deploy, prod test, docs) |

Task 4's route imports `parse_sheet`/`shape_games` from Task 3; doer-1 codes against the interface in Task 3 and uses a stub in tests.

---

### Task 1: Ten-pin scoring engine (`services/bowling_score.py`)

**Files:**
- Create: `backend/toms_gym/services/bowling_score.py`
- Test: `backend/tests/test_bowling_score.py`
- Modify: `backend/tools/run_ci_tests.sh` (add the test file to the list)

**Interfaces — Produces:**
```python
class InvalidFrame(ValueError): ...
def frame_pins(rolls: list[str], frame_index: int) -> list[int]      # symbols → pins for one frame
def score_frames(frames: list[list[str]]) -> dict
#   {"cumulative": list[int] (len == len(frames)), "total": int, "valid": bool, "errors": list[str]}
#   partial games (<10 frames) score what is there; frame bonuses that need future rolls not yet
#   thrown contribute 0 and set "complete": False
def validate_night_row(games: list[int|None], scratch: int|None, hdcp: int|None, total: int|None) -> tuple[bool, str|None]
def infer_night_row(games, scratch, hdcp, total) -> tuple[dict, list[str]]
#   fills exactly one missing value from the two checksums; returns (row, inferred_keys)
```

- [ ] **Step 1: Write failing tests** (`backend/tests/test_bowling_score.py`)

```python
import pytest
from toms_gym.services.bowling_score import (
    frame_pins, score_frames, validate_night_row, infer_night_row, InvalidFrame)

PERFECT = [["X"]] * 9 + [["X", "X", "X"]]
GUTTER = [["-", "-"]] * 10
ALL_NINE_SPARE = [["9", "/"]] * 9 + [["9", "/", "9"]]
TOM = [["X"], ["8", "1"], ["X"], ["9", "/"], ["X"], ["6", "3"], ["8", "/"], ["X"], ["9", "-"], ["7", "/", "9"]]
CHRIS = [["X"], ["9", "-"], ["X"], ["8", "-"], ["X"], ["9", "/"], ["9", "/"], ["9", "/"], ["X"], ["X", "8", "-"]]

def test_perfect_game():
    r = score_frames(PERFECT)
    assert r["total"] == 300 and r["valid"] and r["cumulative"] == [30 * i for i in range(1, 11)]

def test_gutter_game():
    assert score_frames(GUTTER)["total"] == 0

def test_all_nine_spare():
    assert score_frames(ALL_NINE_SPARE)["total"] == 190

def test_real_fixture_rows():
    assert score_frames(TOM)["cumulative"] == [19, 28, 48, 68, 87, 96, 116, 135, 144, 163]
    assert score_frames(CHRIS)["cumulative"] == [19, 28, 46, 54, 74, 93, 112, 132, 160, 178]

def test_tenth_frame_variants():
    assert score_frames([["-", "-"]] * 9 + [["X", "X", "X"]])["total"] == 30
    assert score_frames([["-", "-"]] * 9 + [["X", "9", "/"]])["total"] == 20
    assert score_frames([["-", "-"]] * 9 + [["9", "/", "X"]])["total"] == 20
    assert score_frames([["-", "-"]] * 9 + [["9", "-"]])["total"] == 9

def test_foul_counts_zero():
    assert frame_pins(["F", "9"], 0) == [0, 9]

def test_invalid_frames_flagged_not_raised():
    r = score_frames([["9", "9"]] + [["-", "-"]] * 9)
    assert not r["valid"] and "frame 1" in r["errors"][0]

def test_partial_game_incomplete():
    r = score_frames([["X"], ["9", "/"]])
    assert r["complete"] is False and r["cumulative"] == [20, 10]

def test_frame_pins_rejects_third_ball_before_tenth():
    with pytest.raises(InvalidFrame):
        frame_pins(["9", "-", "5"], 3)

def test_validate_night_row():
    assert validate_night_row([164, 236, 196], 596, 111, 707) == (True, None)
    ok, why = validate_night_row([164, 236, 196], 597, 111, 707)
    assert not ok and "scratch" in why

def test_infer_missing_total():
    row, inferred = infer_night_row([225, 205, 176], 606, 186, None)
    assert row["total"] == 792 and inferred == ["total"]

def test_infer_missing_game():
    row, inferred = infer_night_row([116, None, 91], 340, 270, 610)
    assert row["games"] == [116, 133, 91] and inferred == ["games[1]"]
```

- [ ] **Step 2: Run** `cd backend && venv/bin/python -m pytest tests/test_bowling_score.py --noconftest -q` → fails (module missing).

- [ ] **Step 3: Implement** `backend/toms_gym/services/bowling_score.py`

```python
"""Ten-pin scoring from printed roll symbols. Pure, DB-free."""

class InvalidFrame(ValueError):
    pass


def _pins(symbol, prev, frame_index, roll_index):
    s = symbol.strip().upper()
    if s == "X":
        return 10
    if s == "/":
        if prev is None:
            raise InvalidFrame("spare with no first ball")
        return 10 - prev
    if s in ("-", "F", ""):
        return 0
    if s.isdigit():
        v = int(s)
        if v > 9:
            raise InvalidFrame(f"pin count {v} out of range")
        return v
    raise InvalidFrame(f"unknown symbol {symbol!r}")


def frame_pins(rolls, frame_index):
    if not rolls:
        raise InvalidFrame("empty frame")
    tenth = frame_index == 9
    if len(rolls) > (3 if tenth else 2):
        raise InvalidFrame("too many rolls")
    pins = []
    prev = None
    for i, sym in enumerate(rolls):
        p = _pins(sym, prev, frame_index, i)
        # after a strike or spare the rack resets; otherwise a second ball is a follow-up
        if tenth and (p == 10 or (prev is not None and prev + p == 10 and sym == "/")):
            prev = None
        elif prev is not None and sym != "/":
            if prev + p > 10:
                raise InvalidFrame(f"{prev}+{p} exceeds 10")
            prev = None if tenth else p
        else:
            prev = None if p == 10 else p
        pins.append(p)
    if not tenth and len(rolls) == 1 and pins[0] != 10:
        raise InvalidFrame("open frame needs two balls")
    if tenth:
        need_third = pins[0] == 10 or (len(pins) >= 2 and pins[0] + pins[1] == 10)
        if need_third and len(pins) < 3:
            raise InvalidFrame("tenth frame bonus ball missing")
        if not need_third and len(pins) == 3:
            raise InvalidFrame("tenth frame has an extra ball")
    return pins


def score_frames(frames):
    frames = list(frames)[:10]
    rolls, frame_of = [], []
    errors = []
    for i, f in enumerate(frames):
        try:
            p = frame_pins(f, i)
        except InvalidFrame as e:
            errors.append(f"frame {i + 1}: {e}")
            p = [0, 0]
        rolls.extend(p)
        frame_of.extend([i] * len(p))
    cumulative, total, i = [], 0, 0
    complete = len(frames) == 10
    for fr in range(len(frames)):
        if i >= len(rolls):
            break
        first = rolls[i]
        if fr == 9:
            total += sum(rolls[i:])
            i = len(rolls)
        elif first == 10:
            bonus = rolls[i + 1:i + 3]
            if len(bonus) < 2:
                complete = False
            total += 10 + sum(bonus)
            i += 1
        elif i + 1 < len(rolls) and first + rolls[i + 1] == 10:
            bonus = rolls[i + 2:i + 3]
            if not bonus:
                complete = False
            total += 10 + sum(bonus)
            i += 2
        else:
            total += first + (rolls[i + 1] if i + 1 < len(rolls) else 0)
            i += 2
        cumulative.append(total)
    return {"cumulative": cumulative, "total": total, "valid": not errors,
            "errors": errors, "complete": complete}


def validate_night_row(games, scratch, hdcp, total):
    g = [x for x in games if x is not None]
    if len(g) != len(games):
        return False, "missing game"
    if scratch is not None and sum(g) != scratch:
        return False, f"games sum {sum(g)} != scratch {scratch}"
    if scratch is not None and hdcp is not None and total is not None and scratch + hdcp != total:
        return False, f"scratch {scratch} + hdcp {hdcp} != total {total}"
    return True, None


def infer_night_row(games, scratch, hdcp, total):
    games = list(games)
    inferred = []
    missing_games = [i for i, g in enumerate(games) if g is None]
    if len(missing_games) == 1 and scratch is not None:
        i = missing_games[0]
        games[i] = scratch - sum(g for g in games if g is not None)
        inferred.append(f"games[{i}]")
    elif not missing_games and scratch is None:
        scratch = sum(games)
        inferred.append("scratch")
    if scratch is not None:
        if total is None and hdcp is not None:
            total, _ = scratch + hdcp, inferred.append("total")
        elif hdcp is None and total is not None:
            hdcp, _ = total - scratch, inferred.append("hdcp")
    return {"games": games, "scratch": scratch, "hdcp": hdcp, "total": total}, inferred
```

- [ ] **Step 4: Run tests** → all pass. Fix `frame_pins` state handling until `test_tenth_frame_variants` and `test_real_fixture_rows` pass — those are the authority.
- [ ] **Step 5: Add `tests/test_bowling_score.py` to `run_ci_tests.sh`; run `tools/run_ci_tests.sh`; commit** `feat(bowling): ten-pin scoring engine for score-sheet validation`.

---

### Task 2: Insights (`services/bowling_insights.py`)

**Files:** Create `backend/toms_gym/services/bowling_insights.py`, `backend/tests/test_bowling_insights.py`; modify `run_ci_tests.sh`.

**Interfaces — Consumes:** `score_frames`. **Produces:**
```python
def compute_insights(games: list[dict]) -> dict
# game dict: {"total_score": int, "game_number": int, "played_on": "YYYY-MM-DD", "hdcp": int|None, "frames": list[list[str]]|None}
# returns {
#   "games": int, "average": float, "high": int, "low": int, "stdev": float,
#   "trend": {"last5": float|None, "prior": float|None, "delta": float|None},
#   "slot_averages": {"1": float|None, "2": float|None, "3": float|None},
#   "sessions": int, "session_series": [{"played_on", "average", "games"}],   # oldest → newest
#   "over_200": int, "hdcp_latest": int|None,
#   "frame_stats": None | {"strike_pct", "spare_pct", "open_pct", "first_ball_avg",
#        "single_pin_conversion", "tenth_frame_avg", "strike_by_frame": [10 floats],
#        "clean_games": int, "pins_left": int, "frames_analyzed": int},
#   "tips": [{"key", "title", "body", "stat"}],
# }
```

- [ ] **Step 1: Tests** — build 9 totals-only games over 3 dates (`slot 3` avg 15 below slot 1; stdev > 25), assert `average`, `trend.delta`, `slot_averages`, tip keys include `"fade_game3"` and `"consistency"` and `"snap_a_game"`; build 2 frame games (TOM + CHRIS from Task 1) → `strike_pct == 11/20`, `spare_pct` = spares / spare opportunities (Tom: 4 of 7 → CHRIS: 3 of 4 ...; compute by hand and pin), `open_pct`, `first_ball_avg`, `strike_by_frame[0] == 1.0`, `clean_games == 0`, `pins_left > 0`, tip `"spares"` present iff `spare_pct < 0.7`. Empty list → `games == 0`, tips == [`{"key": "no_games", ...}`].
- [ ] **Step 2: Run → fail. Step 3: Implement.** Tips rules (first matching rules in this order, max 4): `no_games`; `spares` (frame data, spare_pct < .7: "Converting spares is worth ~{pins_left/games:.0f} pins a game"); `first_ball` (first_ball_avg < 8.5); `tenth` (tenth_frame_avg < average/10 − 2); `fade_game3` (slot3 ≤ slot1 − 12, ≥ 3 sessions); `slow_start` (slot1 ≤ slot3 − 12); `consistency` (stdev > 25); `trend_up`/`trend_down` (|delta| ≥ 8); `snap_a_game` (no frame data). Spare opportunity = frame with first ball < 10 (frames 1–9; in the 10th count each rack). Single-pin leave = first ball 9. `pins_left` = 11 × missed spares (approx; documented in code by name `PINS_PER_MISSED_SPARE = 11`).
- [ ] **Step 4: pass; register in CI script; commit** `feat(bowling): insights engine (totals + frame-level stats, tips)`.

---

### Task 3: Vision OCR parser + fixtures + debug tool (lead)

**Files:** Create `backend/toms_gym/services/vision_ocr.py`, `backend/toms_gym/services/bowling_sheet_parser.py`, `backend/tests/test_bowling_sheet_parser.py`, `backend/tools/bowling_sheet_debug.py`; fixtures `backend/tests/fixtures/bowling/<stem>_ocr.json`.

**Interfaces — Produces:**
```python
# services/vision_ocr.py
def extract_words_and_symbols(full_text_annotation) -> tuple[list[dict], list[dict], int, int]
#   words: {text, x, y, w, h, conf}; symbols: {text, x, y, conf}; page_w, page_h
def run_document_ocr(image_bytes: bytes)   # Vision document_text_detection on inline bytes; returns full_text_annotation

# services/bowling_sheet_parser.py
class SheetParseError(Exception): ...
def parse_sheet(sheet_type: str, words, symbols, page_w, page_h) -> dict
#   night: {"team_name": str|None, "players": [{"name", "games": [int|None]*3, "scratch", "hdcp", "total",
#           "inferred": [str], "flagged": bool, "flag_reason": str|None}]}
#   game:  {"team_name", "players": [{"name", "frames": [[str]]*10, "printed_cumulative": [int|None]*10,
#           "total": int|None, "flagged", "flag_reason"}]}
def shape_games(parsed: dict, sheet_type: str, played_on: str) -> list[dict]
#   [{"player_name", "game_number", "total_score", "hdcp", "frames", "computed_total", "flagged",
#     "flag_reason", "confidence"}]
```
- Fixture `_ocr.json` = `{"words": [...], "symbols": [...], "page_w", "page_h", "rotation": int}` produced by the debug tool (it tries 0/90/180/270 and caches the winning pass).
- Tests: every `<stem>_ocr.json` parsed must equal `<stem>_truth.json` (players by name, all cells); night_04 Andrew must carry `inferred == ["total"]` if OCR misses the glared cell; a test that deletes a scratch value from night_01's OCR must produce `flagged` on that row; game_01 all four bowlers' frames + cumulative exact.

---

### Task 4: Migration 017 + routes (`routes/bowling_sheet_routes.py`)

**Files:** Create `backend/toms_gym/migrations/017_bowling_scoresheets.sql` (SQL from spec), `backend/toms_gym/routes/bowling_sheet_routes.py`, `backend/tests/test_bowling_sheet_routes.py` (needs Postgres; NOT in CI list); modify `backend/toms_gym/app.py` (startup block after 016 pattern + `app.register_blueprint(bowling_sheet_bp)` next to `bowling_bp`).

**Interfaces — Consumes:** `parse_sheet`, `shape_games`, `SheetParseError` (Task 3), `run_document_ocr`, `extract_words_and_symbols`, `compute_insights` (Task 2), `score_frames` (Task 1). Import the parser lazily inside the route function so the module imports even before Task 3 merges; tests monkeypatch `bowling_sheet_routes._ocr_and_parse`.

Routes (blueprint `bowling_sheet_bp`, `url_prefix='/bowling'`), copying the user-resolution + GCS upload code from `bowling_routes.py:33-124` and `golf_routes.py` upload (`_auto_orient_image`):

- `POST /scoresheet/upload` `@rate_limit('20/hour')`: fields `image` (file), `user_id`|`email`, `sheet_type` ∈ {night, game} (400 otherwise), `played_on` (default today, `YYYY-MM-DD`). >20 MB → 413. Auto-orient; upload to `bowling/sheets/{user_id}/{sheet_id}.{ext}`; `_ocr_and_parse(image_bytes, sheet_type)` tries rotations 0, 180, 90, 270 (re-encoding via Pillow) and returns the parse with the most non-flagged players; on `SheetParseError` for all → insert sheet with `processing_status='failed'`, `error_message`, zero games, HTTP 200 with `games: []`. Else insert sheet (`parser='vision'`, `raw_parse` = parsed + words) and one `BowlingGame` per `shape_games` row (`user_id` NULL). Response: `{sheet_id, sheet_type, played_on, image_url, team_name, processing_status, players: [{name, games:[game rows]}], flagged_count}`.
- `GET /scoresheet/<id>` → same shape as upload response (404 if missing).
- `PUT /scoresheet/<id>/confirm`: body `{claim_player: str|None, players: [{name, games: [{game_number, total_score, hdcp?, frames?}]}]}`. Re-run `score_frames` on any frames (400 if `valid` false); delete existing games for the sheet and reinsert; rows whose `name == claim_player` get `user_id = sheet.user_id`; sheet → `confirmed`. Returns the GET shape.
- `DELETE /scoresheet/<id>` → 204.
- `GET /games?user_id=&limit=20&offset=0` (limit cap 50): confirmed games with `user_id`, newest `played_on` then `game_number` desc; `{games:[{id, sheet_id, played_on, game_number, total_score, hdcp, has_frames, flagged}], total, limit, offset}`.
- `GET /insights/<user_id>` → `compute_insights` over that user's confirmed games (frames included) → the dict plus `{"recent": first 10 of the games list}`.

- [ ] Steps: write route tests against a local Postgres (`docker run --rm -d -p 5434:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_DB=toms_gym_test postgres:15`, `DATABASE_URL=postgresql://postgres:test@localhost:5434/toms_gym_test`, apply `migrations/schema.sql` + 017, follow `tests/test_ticket_routes.py` setup) with `_ocr_and_parse` monkeypatched to return the night_01 truth; cover upload→get→confirm(claim Tom)→games→insights, failed parse path, 400s, delete. Run; implement; run; commit `feat(bowling): score-sheet upload/confirm/games/insights routes + migration 017`.

---

### Task 5: `app.py` startup migration + blueprint, CI registration

Folded into Task 4's commit; verify `python -c "import toms_gym.app"` works with `GOOGLE_APPLICATION_CREDENTIALS=none` and the DB env unset the way `test_ticket_routes.py` does.

---

### Task 6: TS scoring engine (`frontend/src/lib/bowlingScore.ts`)

**Files:** Create `frontend/src/lib/bowlingScore.ts`, `frontend/src/lib/__tests__/bowlingScore.test.ts`.

**Produces:** `export type Roll = string; export function scoreFrames(frames: Roll[][]): { cumulative: number[]; total: number; valid: boolean; errors: string[]; complete: boolean }` — a line-for-line port of Task 1's `score_frames`; the jest file pins the same cases (PERFECT=300, GUTTER=0, ALL_NINE_SPARE=190, TOM/CHRIS cumulative arrays, tenth-frame variants, invalid `["9","9"]`, partial).

- [ ] Test → fail → implement → pass → commit `feat(bowling): TS ten-pin scoring for live review`.

---

### Task 7: API helpers + types (`frontend/src/lib/api.ts`)

Add types `BowlingSheetGame { id?: string; game_number: number; total_score: number|null; hdcp: number|null; frames: string[][]|null; computed_total: number|null; flagged: boolean; flag_reason: string|null; confidence: number|null }`, `BowlingSheetPlayer { name: string; games: BowlingSheetGame[] }`, `BowlingSheet { sheet_id; sheet_type: "night"|"game"; played_on; image_url; team_name: string|null; processing_status: "parsed"|"failed"|"confirmed"; players: BowlingSheetPlayer[]; flagged_count: number }`, `BowlingGameRow`, `BowlingInsights` (mirror Task 2 dict; `frame_stats: FrameStats|null`).
Functions: `uploadBowlingSheet(form: FormData): Promise<BowlingSheet>` (`POST ${API_URL}/bowling/scoresheet/upload`), `fetchBowlingSheet(id)`, `confirmBowlingSheet(id, body: {claim_player: string|null; players: {name: string; games: {game_number: number; total_score: number|null; hdcp?: number|null; frames?: string[][]|null}[]}[]})`, `deleteBowlingSheet(id)`, `fetchBowlingGames(userId, limit=20, offset=0)`, `fetchBowlingInsights(userId): Promise<BowlingInsights & {recent: BowlingGameRow[]}>`.
- [ ] Commit `feat(bowling): api helpers for score sheets`.

---

### Task 8: Upload page + routes + hub

**Files:** Create `frontend/src/pages/BowlingSheetUpload.tsx`, `frontend/src/pages/__tests__/BowlingSheetUpload.test.tsx`; modify `frontend/src/routes/index.tsx` (lazy imports + routes `/bowling/scoresheet/upload`, `/bowling/snap` = `<BowlingSheetUpload autoCamera />`, `/bowling/scoresheet/:id`, `/bowling/insights/:userId`), `frontend/src/pages/BowlHub.tsx` (primary → `/bowling/snap` "Snap a score sheet"; secondary: `/bowling/upload` "Analyze a video", `/bowling/insights/me` "My insights" — the page resolves `me` from localStorage `userId`, `/challenges`), `frontend/public/manifest.json` (shortcut "Snap bowling scores" → `/bowling/snap`), `frontend/src/pages/__tests__/BowlHub.test.tsx` if present.

Page: copy `GolfUpload.tsx` structure (two hidden inputs `#bowling-sheet-upload` and `#bowling-sheet-camera capture="environment"`, `autoCamera` auto-click, email field when no `userId` in localStorage, preview thumbnail). Add a two-option segmented toggle `sheet_type` (Night results / Single game; default night) and a date input defaulting to today. Submit → `uploadBowlingSheet` → `navigate('/bowling/scoresheet/'+sheet_id)`. Tests: renders both inputs, camera input has `capture`, toggle switches the posted `sheet_type`, submit navigates with the returned id (mock api + `useNavigate`).
- [ ] Commit `feat(bowling): camera-first score-sheet upload page + hub links`.

---

### Task 9: Review page (`BowlingSheetReview.tsx`)

**Files:** Create `frontend/src/pages/BowlingSheetReview.tsx`, `frontend/src/components/bowling/FrameStrip.tsx`, `frontend/src/pages/__tests__/BowlingSheetReview.test.tsx`.

Behavior: load `fetchBowlingSheet(id)`; photo thumbnail (clicking opens the same fullscreen lightbox pattern `GolfProfile` uses — copy it, don't import). Player list; radio "This is me" per player (preselect the player whose name case-insensitively equals the profile name from `GET /users/<id>/profile` → `data.user.name`, first token match acceptable). Night: editable number inputs for G1/G2/G3 + Hdcp per player, live `scratch` and `total` computed; a row is highlighted amber with its `flag_reason` when `flagged`. Game: `FrameStrip` renders 10 cells each with a text input accepting the roll string (e.g. `9/`, `X`, `X X 8` typed as `XX8`; split into symbols by char, `/` and `-` allowed) and shows the live `scoreFrames` cumulative under each cell; invalid → red border + `errors[0]`. `failed` sheets render the same form empty with one blank player row and an "Add player" button. Confirm → `confirmBowlingSheet` → navigate `/bowling/insights/<userId>` when a row was claimed, else `/bowl`. Delete button with `window.confirm` **must not** be used (browser dialogs block automation) — use an inline two-step "Delete → Really delete?" button.
Tests: night sheet renders 4 players with totals, editing G2 updates scratch/total, flagged row shows reason, confirm posts `claim_player`; game sheet renders 10 frames and updates cumulative on edit.
- [ ] Commit `feat(bowling): score-sheet review page with live scoring + claiming`.

---

### Task 10: Insights page + Profile block

**Files:** Create `frontend/src/pages/BowlingInsights.tsx`, `frontend/src/components/bowling/InsightTiles.tsx`, `frontend/src/pages/__tests__/BowlingInsights.test.tsx`; modify `frontend/src/pages/Profile.tsx` Bowl tab (a "Score sheets" block above "Bowling Attempts": last 5 games via `fetchBowlingGames`, link "Insights →" to `/bowling/insights/:id`, "Snap a sheet" link when empty).

Page: `userId` param (`me` → localStorage `userId`, else redirect to `/find-profile`); tiles Average / High / Games / Trend (signed ▲▼ like GolfLeaderboard pill), then Tips list (title + body + stat), then slot averages as three bars, frame stats tiles when present (Strike % / Spare % / Open % / First ball), per-frame strike heatmap (10 cells shaded by value), recent games list linking to `/bowling/scoresheet/:sheet_id`. Empty state → CTA `/bowling/snap`. Use `RowCard`/`IconTile` where they fit; keep the quiet-gym styling of `HubPage`.
Tests: renders tiles from a mocked insights payload, renders tips, empty state CTA, `me` resolves from localStorage.
- [ ] Commit `feat(bowling): insights page + profile score-sheet block`.

---

### Task 11: Integrate, deploy, verify in prod, docs (lead)

- [ ] Merge both worktree branches into `feat/bowling-scoresheet`; run `backend/tools/run_ci_tests.sh`, `cd frontend && npx tsc --noEmit && npm test`.
- [ ] `python3 deploy.py --skip-iam`; confirm startup log shows "017 migration complete".
- [ ] Browser: upload `night_01.jpg` via `/bowling/snap` on prod, verify 4 players parsed with 0 flags, claim Tom, confirm, insights render; repeat with `game_01.jpg`; check `/profile/<id>` Bowl tab.
- [ ] CLAUDE.md: add "Bowling Score Sheets (shipped 2026-08-28)" section (routes, tables, parser gotchas, fixture workflow); commit; merge to `main`; push.
