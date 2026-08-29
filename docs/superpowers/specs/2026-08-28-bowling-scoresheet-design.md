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

One real per-game screen (`game_01.jpg` + `_truth.json`, four bowlers, 10 frames each
with roll glyphs over a running score) covers the frame-level path; its truth is
verified against the ten-pin scoring rules.

## Approach

**Same path as golf: Google Vision OCR → deterministic, DB-free parser → checksum
validation → review page.** Accuracy is measured, not assumed: every real photo in
`backend/tests/fixtures/bowling/` gets a cached `_ocr.json` (Vision symbol dump) and a
hand-checked `_truth.json`; the parser must reproduce the truth offline in CI, and
`tools/bowling_sheet_debug.py` prints a per-photo hit-rate report + overlay like
`tools/grid_debug.py` does for golf.

Why this over a multimodal LLM (Gemini on Vertex was probed 2026-08-28 and works, but is
deferred): lane screens are *printed* digital text — Vision reads them cleanly, the
parser is deterministic and unit-testable without network, and no new IAM/secret is
needed. An LLM fallback can be added later behind a flag if a vendor layout defeats
the parser.

Parser design (`services/bowling_sheet_parser.py`, pure; input = Vision word+symbol
list with centroids and page size, same shape as `golf_routes._extract_symbols`):

- **Rotation.** Try 0°, then 90/180/270 (re-OCR) and keep the pass with the most
  checksum-valid player rows — the golf route already does this for player count.
- **Night sheet.** Find header words (`Game 1..3`, `Scratch`, `Hdcp`, `Total`) → column
  x-centres; the first header band is the Player block, the second (below `Team`) is the
  Team block. Name = leftmost alphabetic word left of the Game 1 column. Numbers are
  assigned to the nearest name row by y (they sit ~⅓ row lower than the names on
  QubicaAMF) and to the nearest header column by x. Validate `sum(games)==scratch` and
  `scratch+hdcp==total`; one missing cell (glare) is inferred from the other two and
  marked `inferred`; any other mismatch flags the row.
- **Game screen.** Header `1..10`,`Total` gives frame column x-centres. Each player band
  (between consecutive name rows) splits into an upper roll line and a lower cumulative
  line. Roll glyphs (`X / - F 0-9`) are taken at **symbol** level (Vision merges `9/`
  into one word) and binned into frame columns by cell boundaries; cumulative numbers
  by nearest column. Then `bowling_score.score_frames` recomputes the running score;
  a frame whose recomputed cumulative disagrees with the printed one is repaired if a
  single hidden roll explains the printed number (e.g. the 10th-frame ball hidden under
  a split-circle graphic), else flagged.

Trust boundary: the parser never silently accepts — a mismatch flags the row and the
review page makes the user look at it before confirming, exactly like golf.

## Data model — migration `017_bowling_scoresheets.sql`

```sql
CREATE TABLE IF NOT EXISTS "BowlingScoreSheet" (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES "User"(id) ON DELETE CASCADE,   -- uploader
  sheet_type TEXT NOT NULL CHECK (sheet_type IN ('night','game')),
  played_on DATE NOT NULL,
  image_url TEXT NOT NULL,
  parser TEXT,                       -- 'vision' | 'manual'
  raw_parse JSONB,                   -- parser output + OCR word dump (debug/re-parse)
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
- `parse_night_sheet(words, page_w, page_h) -> {team_name, players:[{name, games:[int|None], scratch, hdcp, total, inferred:[str], flagged, flag_reason}]}`.
- `parse_game_sheet(words, symbols, page_w, page_h) -> {team_name, players:[{name, frames:[[str]], printed_cumulative:[int], total, flagged, flag_reason}]}`.
- `parse_sheet(sheet_type, words, symbols, page_w, page_h)` dispatches; raises `SheetParseError` when no player row is found (route then retries rotations, then stores `failed`).
- `shape_games(parsed, sheet_type, played_on) -> list[game_row]` — pure; one row per (player, game) with engine validation applied (`computed_total`, `flagged`, `flag_reason`, `confidence`).
- Input shape: `words = [{text, x, y, w, h, conf}]`, `symbols = [{text, x, y, conf}]` from `golf_routes._extract_symbols`-style walkers (a new shared `services/vision_ocr.py` exposes `extract_words_and_symbols(full_text_annotation)`). **Tests replay `tests/fixtures/bowling/<stem>_ocr.json` and must match `<stem>_truth.json` exactly.**

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

- Vision error / `SheetParseError` after all rotations → sheet saved as `failed`, user lands on manual review; the error is logged with the sheet id. Never lose the photo.
- Engine invalid frames → row flagged, not rejected.
- Unknown `sheet_type` → 400. Missing user/email → 400. Image > 20 MB → 413.

## Testing

- Backend: `test_bowling_score.py` (rules incl. 300, 0, 10th-frame variants, foul, invalid combos), `test_bowling_sheet_parser.py` (parse of every cached `_ocr.json` must reproduce its `_truth.json` exactly — 4 night sheets: all 16 player rows × 6 cells, team block; 1 game screen: 4 bowlers × 10 frames + cumulative; a glare-damaged row must be `inferred`, a corrupted OCR must flag, never silently accept), `test_bowling_insights.py` (fixtures for totals-only and frame-level). All DB-free, registered in `run_ci_tests.sh`. `tools/bowling_sheet_debug.py` (needs `GOOGLE_APPLICATION_CREDENTIALS=backend/credentials.json`) OCRs each fixture photo, writes/refreshes `<stem>_ocr.json`, and prints a per-photo cell hit-rate against truth — run manually, not in CI.
- Frontend: jest for `lib/bowlingScore.ts`, `BowlingSheetUpload`, `BowlingSheetReview`, `BowlingInsights`, updated `BowlHub`.
- Prod verification: deploy, upload `night_01.jpg` via the real UI in a browser, confirm Tom's row, check insights render.

## Out of scope (v1)

Guest users / leaderboard for sheet games; league/team tracking beyond storing `team_name`; pin-leave diagrams; auto-claiming rows by name across uploads; a Cloud Tasks async path (parse is a single ~5s call, done inline).
