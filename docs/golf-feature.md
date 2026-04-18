# Golf Feature

A scorecard-photo → handicap pipeline. Users photograph a paper scorecard; the
backend runs Google Cloud Vision OCR, extracts hole-by-hole scores for every
handwritten player on the card, and computes a USGA WHS handicap index after
three or more confirmed rounds.

Design predecessor: [`docs/superpowers/specs/2026-03-16-golf-scorecard-tracker-design.md`](superpowers/specs/2026-03-16-golf-scorecard-tracker-design.md).

## User flow

1. `/golf/upload` — user selects a scorecard photo, enters course name, slope
   rating, course rating, and date. Submits as multipart form.
2. Backend stores the image in GCS, runs Vision `document_text_detection`,
   and parses every detected player row into 18 holes.
3. Frontend navigates to `/golf/review/:roundId`. The review page shows the
   scorecard thumbnail plus a "Detected *N* players — pick your row" panel.
4. User picks their row; the 18-hole grid loads with OCR scores. Tap any
   cell to correct a misread.
5. User confirms. The backend computes the differential and, if the user has
   three or more confirmed rounds, recalculates the handicap index.

## Data model

Three tables, created lazily by the startup migration in `backend/toms_gym/app.py`:

| Table | Key columns |
|---|---|
| `GolfRound` | `user_id`, `course_name`, `slope_rating`, `course_rating`, `adjusted_gross_score`, `differential`, `scorecard_image_url`, `ocr_raw` (JSONB `{text, detected_players}`), `ocr_confidence`, `played_at`, `processing_status` |
| `GolfHoleScore` | `round_id`, `hole_number` (1–18), `par`, `strokes`, `ocr_confidence`, `manually_corrected` |
| `GolfHandicap` | `user_id` (unique), `handicap_index`, `rounds_used`, `differentials_used` (JSONB) |

The multi-player detection output is persisted alongside the primary player's
scores inside `GolfRound.ocr_raw` so the review UI can offer row-switching
without re-running OCR.

## HTTP API

| Endpoint | Method | Behaviour |
|---|---|---|
| `/golf/upload` | POST | Multipart form: `image`, `course_name`, `slope_rating` (55–155), `course_rating` (55–85), `played_at` (optional), `user_id` **or** `email`. Returns `round_id`, `holes` (first detected player), `detected_players` (all detected), `scorecard_image_url`, `ocr_confidence`. Auto-creates a user from `email` if it's not already in the DB. |
| `/golf/round/<id>` | GET | Full round including `holes` and `detected_players`. |
| `/golf/round/<id>/scores` | PUT | Body `{holes: [{hole_number, par, strokes}, …×18], user_id}`. Computes `adjusted_gross_score`, differential = `⌊(113 / slope) × (score − course_rating) × 10⌋ / 10`, sets `processing_status='confirmed'`, then recalculates the user's handicap. |
| `/golf/round/<id>` | DELETE | Requires `?user_id=` matching the round owner. Cascades to `GolfHoleScore`. Recalculates handicap. |
| `/golf/rounds?user_id=&limit=&offset=` | GET | List a user's rounds (paginated) with their hole scores and current handicap. |
| `/golf/handicap/<user_id>` | GET | Current handicap index, rounds used, differentials used. |
| `/golf/leaderboard?limit=&offset=` | GET | Global leaderboard ordered by lowest handicap index. |

All routes are rate-limited at the module level; uploads are capped at
10 per hour per caller.

## OCR pipeline

Pure functions in `backend/toms_gym/routes/golf_routes.py`:

1. `_auto_orient_image(bytes, content_type)` — applies EXIF transpose only.
   **Does not force portrait.** An earlier version rotated any landscape image
   90° on the assumption that scorecards are portrait; this silently corrupted
   legitimate landscape photos and has been removed. If the downstream parser
   detects zero players, the upload route retries OCR on a 90°-rotated copy
   and keeps whichever orientation yielded more players.

2. `_extract_symbols(ocr_response)` — flattens the Vision response to
   `{text, x, y, conf}` dicts at **symbol granularity**. Word-level output is
   unusable here: Vision routinely concatenates handwritten digits across a
   wide row into a single word token like `"7864856T65854494444"`.

3. `_group_rows(symbols, page_height)` — clusters symbols by y-proximity.
   Threshold is `max(15, min(60, page_height × 0.02))`.

4. `_parse_player_row(row_symbols, gap_threshold)` — the per-row detector:
   - Requires at least 15 digits and at most 20 letters (rejects tee/label
     rows that are thick with letters like `"BLACK GOLD GREEN WHITE…"`).
   - Takes the leftmost contiguous letter cluster (x-gap < 150 px) as the
     player's name.
   - Rejects names that match or start with a known scorecard label
     (`PAR`, `HANDICAP`, `BLACK`, `GOLD`, `GREEN`, `WHITE`, `HOLE`, `OUT`,
     `IN`, `TOT`, `PLAYER`, …).
   - Deduplicates digits at near-identical positions (Vision often emits a
     handwritten "5" twice with slightly different bounding boxes).
   - Clusters remaining digits by x-gap (default threshold `max(40,
     min(90, page_width × 0.018))`). Single-digit clusters are scores;
     multi-digit clusters are OUT / IN / TOT subtotals.
   - Uses the first multi-digit cluster as the OUT separator: the 9 singles
     before it are the front 9; the first 9 singles between OUT and IN are
     the back 9. This rejects spurious digits that OCR sometimes places
     past the real scorecard columns.

5. `_parse_scorecard_symbols(symbols, width, height)` — iterates rows and
   returns `{players: [{name, holes: [{hole_number, par, strokes,
   ocr_confidence}] ×18}, …]}`. Par defaults to 4 per hole; the review UI
   lets users correct par values alongside strokes.

6. `_extract_players_from_ocr(response)` — convenience wrapper used by the
   upload route.

### Why symbol-level?

Vision's word groupings span arbitrarily wide when handwriting is not
perfectly column-aligned. On the fixture scorecard, the two player rows came
back as, e.g., `TOM  58  467864  7864856T65854494444  /  105`, which is
impossible to align to hole columns from word text alone. Symbol-level
output gives each digit its own bounding box; x-clustering then recovers
the column structure reliably.

## WHS handicap

`_recalculate_handicap(session, user_id)` implements USGA Rule 5.2:

1. Pull the last 20 confirmed rounds' differentials (ordered by `played_at`).
2. Sort ascending; select `WHS_TABLE[n]` best differentials and adjustment.
3. `handicap_index = trunc(((avg(best) + adjustment) × 0.96) × 10) / 10`,
   capped at 54.0.
4. Upserts `GolfHandicap` for the user. Fewer than 3 rounds → `NULL`.

## Frontend pages

| Route | Component | Notes |
|---|---|---|
| `/golf/upload` | `GolfUpload` | Multipart form + drag-and-drop file picker. |
| `/golf/review/:roundId` | `GolfReview` | Player picker + editable 18-hole grid + scorecard thumbnail. |
| `/golf/round/:roundId` | `GolfRound` | Completed round detail. |
| `/golf/profile/:userId?` | `GolfProfile` | Handicap badge + rounds card-feed. |
| `/golf/leaderboard` | `GolfLeaderboard` | Global handicap leaderboard. |

## Testing

- `backend/tests/test_golf_parser.py` — pytest coverage of the helper
  functions and an end-to-end multi-player assertion against the saved
  fixture.
- `backend/tests/fixtures/golf_scorecard_ocr.json` — 740 real Vision symbols
  from a two-player scorecard (`TOM` 105, `CHRIS` 93).
- `backend/tools/run_golf_parser_tests.py` — standalone runner. Use this
  for local regression checks; it does **not** load the main `conftest.py`,
  so it runs with no database, no GCS auth, and no Flask app context.
- `backend/tools/ocr_inspect3.py` — debug utility: runs Vision on a local
  image and prints symbol-level row/column layout. Requires
  `GOOGLE_APPLICATION_CREDENTIALS=backend/credentials.json`.

## Recent changes

The two-player scorecard fixture was introduced to lock down a regression:
the original parser only extracted one score row per nine, and the image
auto-orient rotated valid landscape scorecards the wrong way. Both are
fixed; see commit `a016db6`.
