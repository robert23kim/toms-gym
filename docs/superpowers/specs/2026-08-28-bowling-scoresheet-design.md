# Bowling Score Sheet Photos → Stored Games → Insights

**Date:** 2026-08-28 · **Status:** approved for implementation (autonomous loop; user can redirect at any tick)

## Goal

Photograph (a) the end-of-night RESULTS screen (per-player Game 1/2/3, Scratch, Hdcp,
Total) and/or (b) a per-game end-of-game lane screen (10 frames of roll symbols with
running score), parse it, store every game, and surface "things to work on".

Nothing else to type — same promise as golf. Optional-auth model applies (user_id or
email).

## What the samples tell us

Four real photos (`backend/tests/fixtures/bowling/night_0N.jpg` + `_truth.json`) are
QubicaAMF RESULTS screens: a Player table (name · G1 · G2 · G3 · Scratch · Hdcp · Total)
and a Team table. One is upside-down; one has glare over a cell. Rows obey two
checksums: `sum(games) == scratch` and `scratch + hdcp == total` — these drive
validation exactly like the golf OUT/IN/TOT checksums.

No per-game (frame) photo exists yet. That path is built to the same contract but its
parser can only be validated on synthetic renders until a real one arrives.

## Approach

**Parse with Gemini on Vertex AI (structured JSON output), validate with a pure scoring
engine, correct on a review page.**

Why not a Vision-OCR grid parser like golf: lane-monitor layouts differ per vendor and
per screen; the golf parser took a fixture corpus to tune and we have four photos of one
vendor. A multimodal model with a strict response schema is layout-agnostic and handles
rotation/glare. Vertex uses the existing service account via ADC — no new secret; the
API was enabled 2026-08-28 and the SA needs `roles/aiplatform.user`. Vision OCR stays
untouched (golf).

Trust boundary: the model's output is never accepted blind. The engine recomputes every
total from the parts; a mismatch flags the row (`flagged`) and the review page makes the
user look at it before confirming — the same "never silently accept" rule as golf.

Model: `gemini-2.5-flash` (cheap, fast, strong on screen text). Configurable via
`BOWLING_SHEET_MODEL`. Temperature 0. Image sent inline (bytes), not via GCS URI, so the
call works identically in dev and prod.

## Data model — migration `017_bowling_scoresheets.sql`

```sql
CREATE TABLE IF NOT EXISTS "BowlingScoreSheet" (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES "User"(id) ON DELETE CASCADE,   -- uploader
  sheet_type TEXT NOT NULL CHECK (sheet_type IN ('night','game')),
  played_on DATE NOT NULL,
  image_url TEXT NOT NULL,
  parser TEXT,                       -- 'gemini' | 'manual'
  raw_parse JSONB,                   -- model output verbatim (debug/re-parse)
  processing_status TEXT NOT NULL DEFAULT 'parsed',  -- parsed | failed | confirmed
  error_message TEXT,
  team_name TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS "BowlingGame" (
  id UUID PRIMARY KEY,
  sheet_id UUID NOT NULL REFERENCES "BowlingScoreSheet"(id) ON DELETE CASCADE,
  user_id UUID REFERENCES "User"(id) ON DELETE SET NULL,   -- NULL until a row is claimed
  player_name TEXT NOT NULL,
  game_number INT NOT NULL,
  total_score INT,                   -- as printed / confirmed
  hdcp INT,                          -- per-game handicap when the sheet shows one
  frames JSONB,                      -- game screens only: [{"rolls":["X"],"cum":30}, ...]
  computed_total INT,                -- engine result from frames (NULL for night sheets)
  flagged BOOLEAN NOT NULL DEFAULT false,
  flag_reason TEXT,
  confidence REAL,
  played_on DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (sheet_id, player_name, game_number)
);
CREATE INDEX IF NOT EXISTS idx_bowlinggame_user ON "BowlingGame"(user_id, played_on DESC);
```

Both the SQL file and the `run_startup_migrations()` block in `app.py` (pattern of 014)
are added — prod only gets the block.

Frame roll symbols are stored as printed (`"X"`, `"/"`, `"-"`, `"7"`, `"F"`); the
engine converts to pins. Night sheets have `frames = NULL`.

Claiming: the uploader picks "this is me" on the review page → that player's games get
`user_id = uploader`. Other rows stay `user_id NULL` (no guest-user creation — unlike
golf, we don't want random league-mates on a leaderboard; nothing here is ranked).
`player_name` is kept so a later "claim my rows by name" feature is possible.

## Pure services (DB-free, fixture-tested)

`services/bowling_score.py`
- `parse_roll(symbol, prev_pins) -> int` and `frame_pins(frame_rolls) -> list[int]`
- `score_frames(frames: list[list[str]]) -> {"cumulative": [..10], "total": int, "valid": bool, "errors": [...]}` — full ten-pin rules incl. 10th-frame bonus balls.
- `validate_night_row(games, scratch, hdcp, total) -> (ok, reason)`; `validate_game_row(frames, printed_total)`.

`services/bowling_sheet_parser.py`
- `SHEET_SCHEMA` (JSON schema for Gemini response) — `{sheet_type, team_name?, players:[{name, games:[int], scratch?, hdcp?, total?}], frame_games:[{name, game_number?, frames:[[str]], printed_cumulative:[int], total?}]}`.
- `parse_sheet_image(image_bytes, mime, sheet_type_hint) -> dict` — builds prompt, calls Vertex, returns validated dict. Raises `SheetParseError`.
- `shape_games(parsed, played_on) -> list[game_row]` — pure; applies engine validation, sets `flagged`/`flag_reason`/`computed_total`. **This is what the tests hit**, with the model output replayed from `tests/fixtures/bowling/night_0N_parsed.json`.

`services/bowling_insights.py` — `compute_insights(games: list[dict]) -> dict`, pure.
- Always (totals only): games, average, high/low, last-5 avg vs prior avg (trend), stdev ("consistency"), game-slot averages (G1/G2/G3 → warm-up or fatigue pattern), % of games ≥ avg+20, pins-over-200 count, handicap trend when `hdcp` present, sessions (nights) count and avg series.
- When frames exist: strike %, spare conversion %, open-frame %, first-ball average, single-pin-leave conversion (first ball = 9), 10th-frame average, per-frame strike heatmap, clean games, "pins left on the table" (what converting all missed spares would have added, approx +11 each).
- `tips` — rule-based, ordered by impact, each `{key, title, body, stat}`. Examples: spare conversion < 0.7 → "Spares are your biggest lever"; G3 avg ≥ 12 below G1 → "You fade in game 3"; stdev > 25 → "Consistency"; no frame data → "Snap a game screen to unlock frame-level insights".

## Routes (`routes/bowling_sheet_routes.py`, blueprint prefix `/bowling`)

| Method | Path | Notes |
|---|---|---|
| POST | `/bowling/scoresheet/upload` | multipart `image`, `user_id` or `email`, `sheet_type` (night\|game), `played_on?` (default today). Stores image at `bowling/sheets/{user_id}/{sheet_id}.{ext}`; runs parser; inserts sheet + games; returns `{sheet_id, sheet_type, players, games, flagged_count, processing_status}`. On parser failure: sheet stored with `failed` + empty games so the review page can go manual. `@rate_limit('20/hour')`. |
| GET | `/bowling/scoresheet/<id>` | sheet + games grouped by player. |
| PUT | `/bowling/scoresheet/<id>/confirm` | body `{claim_player?: str, players:[{name, games:[{game_number, total_score, hdcp?, frames?}]}]}`; re-validates via engine, upserts rows, sets `user_id` on claimed rows, status `confirmed`. |
| DELETE | `/bowling/scoresheet/<id>` | cascade. |
| GET | `/bowling/games?user_id=&limit=&offset=` | confirmed games, newest first, `{games,total}`. |
| GET | `/bowling/insights/<user_id>` | `compute_insights` over that user's confirmed games. |

Route tests need Postgres and are deselected in CI like the ticket tests; the pure
services are in the CI gate (`run_ci_tests.sh`).

## Frontend

- `pages/BowlingSheetUpload.tsx` — camera-first like `GolfUpload` (two hidden inputs, `autoCamera` prop; `/bowling/snap` route = autoCamera). Sheet-type toggle (Night results / Single game) and date (default today). Posts, navigates to review.
- `pages/BowlingSheetReview.tsx` at `/bowling/scoresheet/:id` — photo thumbnail (lightbox reuse), player rows with editable game totals (night) or an editable 10-frame strip (game) with live engine-computed running score (`lib/bowlingScore.ts` — TS port of the engine, fixture-tested against the same cases), flagged rows highlighted, "This is me" radio per player (pre-selects a name matching the profile name), Confirm → PUT → navigate to insights. Works for `failed` sheets as a blank manual form.
- `pages/BowlingInsights.tsx` at `/bowling/insights/:userId` — stat tiles, tips list, game-slot bars, recent games list (link to sheet). Empty state → snap CTA.
- `BowlHub`: primary becomes "Snap a score sheet" (`/bowling/snap`); secondary: "Analyze a video" (`/bowling/upload`), "My insights", "Challenges".
- Profile Bowl tab: a "Score sheets" block (last N games + link to insights) above the existing attempts list.
- `api.ts`: `uploadBowlingSheet`, `fetchBowlingSheet`, `confirmBowlingSheet`, `fetchBowlingGames`, `fetchBowlingInsights`.

## Error handling

- Vertex unavailable / 403 / schema-invalid → sheet saved as `failed`, user lands on manual review; the error is logged with the sheet id. Never lose the photo.
- Engine invalid frames → row flagged, not rejected.
- Unknown `sheet_type` → 400. Missing user/email → 400. Image > 20 MB → 413.

## Testing

- Backend: `test_bowling_score.py` (rules incl. 300, 0, 10th-frame variants, foul, invalid combos), `test_bowling_sheet_parser.py` (`shape_games` over replayed parses for all 4 fixtures must reproduce `_truth.json` exactly with 0 flags; a corrupted parse must flag), `test_bowling_insights.py` (fixtures for totals-only and frame-level). All DB-free, registered in `run_ci_tests.sh`. A `tools/bowling_sheet_probe.py` runs the live model over the fixture photos and reports hit-rate — run manually, not in CI.
- Frontend: jest for `lib/bowlingScore.ts`, `BowlingSheetUpload`, `BowlingSheetReview`, `BowlingInsights`, updated `BowlHub`.
- Prod verification: deploy, upload `night_01.jpg` via the real UI in a browser, confirm Tom's row, check insights render.

## Out of scope (v1)

Guest users / leaderboard for sheet games; league/team tracking beyond storing `team_name`; pin-leave diagrams; auto-claiming rows by name across uploads; a Cloud Tasks async path (parse is a single ~5s call, done inline).
