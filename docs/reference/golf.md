<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Golf Feature

> **Phase B schema migration landed 2026-04-18** (branch `golf/fairway-phase-b`, migration `008_fairway_schema.sql`). The flat `GolfRound` / `GolfHoleScore` / `GolfHandicap` tables were dropped and replaced with the normalized `Course` / `Tee` / `Round` / `HoleScore` / `HandicapSnapshot` model below. PRs or docs written before that date refer to the old shape — see the Field Rename Map at the end of this section.

### Data Model
- **`Course`** — one per golf course: `id` (UUID), `name`, `city`, `state`, `country`, `latitude`, `longitude`, `holes` (9 or 18), `status` (`'verified'` | `'pending'`). `pending` is set by the OCR matcher on a miss; admins promote to `verified`. GIN trigram index on `name` for fuzzy search.
- **`Tee`** — one per tee box per course: `course_id`, `name` (e.g. `"Blue"`), `color_hex`, 18-hole `rating_18` / `slope_18`, optional 9-hole splits (`rating_9_front` / `slope_9_front` / `rating_9_back` / `slope_9_back`), `yardage`, `par`, `hole_pars[]`, `hole_yardages[]`, `hole_handicaps[]` (per-hole stroke-allocation ranks 1..18; null falls back to the flat NDB-10 cap). Slope columns enforce WHS legal range 55–155.
- **`Round`** — one per upload: `user_id`, `course_id`, `tee_id` (nullable until user picks a tee), `played_on` (DATE), `holes` (9 or 18), `scores[]`, `total_score`, `front_nine`, `back_nine`, `score_differential`, `scorecard_image_url`, `ocr_raw` (JSONB: `{text, detected_players}`), `ocr_confidence`, `processing_status`.
- **`HoleScore`** — one per hole (9 or 18 per round): `round_id`, `hole_number`, `par`, `strokes`, `ocr_confidence`, `manually_corrected`. `UNIQUE (round_id, hole_number)`.
- **`HandicapSnapshot`** — append-only handicap history: `user_id`, `handicap_index`, `rounds_used`, `differentials_used` (JSONB), `triggered_by_round_id`, `created_at`. Written on every round save, edit, or delete; indexed by `(user_id, created_at DESC)` for history queries.

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/golf/upload` | POST | Multipart form: scorecard image + `user_id` OR `email` — everything else optional (photo-only since migration 011). The grid parser extracts players/pars/tees; `course_name` (optional) links via `match_or_create_course`; card-printed tee rating/slopes auto-create `Tee` rows when the course is known. Returns `round_id`, `hole_scores`, `detected_players` (holes carry `flagged`), `detected_tees`, `needs_tee`, `needs_course`, `parser` (`grid`\|`legacy`), and `guest_rounds` (see "Multi-player auto-save"). |
| `/golf/round/<id>` | GET | Fetch round with nested `course` (nullable) and `tee` objects + `hole_scores`, `detected_players`, `detected_tees`, `needs_tee`, `needs_course` for the review UI. |
| `/golf/round/<id>/scores` | PUT | Confirm/correct holes; also accepts review-page overrides: `course_id` or `course_name`, `tee_id` or `rating`+`slope` (+`tee_name`), and `played_on` (YYYY-MM-DD). Computes `score_differential`, recalculates WHS index, writes a new `HandicapSnapshot`. |
| `/golf/round/<id>` | DELETE | Delete a round and write a recalculated `HandicapSnapshot`. |
| `/golf/rounds?user_id=` | GET | List a user's rounds; each entry carries nested `course` and `tee`. |
| `/golf/handicap/<user_id>` | GET | Current handicap index + differentials used (reads latest `HandicapSnapshot`). |
| `/golf/handicap/<user_id>/recompute` | POST | Force a fresh `HandicapSnapshot` for a user from their stored rounds. Used when engine rules change (e.g. the 1-round minimum below) and existing users need to refresh their index without re-confirming rounds. |
| `/golf/leaderboard` | GET | Global leaderboard sourced from latest `HandicapSnapshot` per user; each row includes `monthly_delta` (30-day handicap change). The frontend renders a signed ▲/▼ pill on `GolfLeaderboard` rows (lower-is-better: negative delta = green improvement); zero/null deltas render nothing. |
| `/golf/courses?q=&near=lat,lng` | GET | `pg_trgm` fuzzy search over `Course.name`; optional geo-biased tie-break. |
| `/golf/courses` | POST | Create a new course. Body: `{name, city?, state?, country?, latitude?, longitude?, holes?}`. Authenticated callers create `status='verified'`; anonymous callers create `status='pending'`. |
| `/golf/users/<user_id>/handicap/history?range=6m\|12m\|24m\|all` | GET | Ordered `HandicapSnapshot` series for the trend chart (Phase D dashboard consumer). |

### Handicap Engine (WHS 2020+)

`backend/toms_gym/services/handicap.py` is a pure, DB-free module exposing `net_double_bogey_cap`, `compute_differential`, `compute_handicap_index`, `allocate_strokes`, `apply_twelve_month_cap`. Route code loads rounds, calls these helpers, writes snapshots.

- **Net-double-bogey cap.** Per-hole strokes are capped before the differential is computed. Cap is `par + 2 + strokes_received_on_hole` when a handicap exists; a flat **10** per hole when the user is still establishing. Hole-handicap ranks come from `Tee.hole_handicaps`; the flat-10 fallback kicks in whenever those ranks are missing (OCR rarely extracts them today — see Phase D follow-up).
- **Differential.** `((adjusted_total − rating − PCC) × 113) / slope`. `PCC = 0` (Playing Conditions Calculation is MVP-disabled). Works for both 9- and 18-hole rounds — the route picks the correct rating/slope pair.
- **WHS adjustment table (no 0.96 multiplier).** Final index = `trunc((avg_of_lowest_N + adjustment) × 10) / 10`, capped at 54.0. The pre-2020 `× 0.96` "bonus for excellence" is intentionally omitted per USGA Rules of Handicapping §5.2. Tom's Gym extended the table down to 1-and-2-round states (lowest 1, no adjustment) so a single upload produces a provisional index instead of an empty leaderboard — the 3-round floor in the official spec was dropped for UX reasons.

  | Rounds in pool | Lowest N used | Adjustment |
  |---|---|---|
  | 1 | 1 | 0 (provisional; Tom's Gym extension) |
  | 2 | 1 | 0 (provisional; Tom's Gym extension) |
  | 3 | 1 | −2.0 |
  | 4 | 1 | −1.0 |
  | 5 | 1 | 0 |
  | 6 | 2 | −1.0 |
  | 7–8 | 2 | 0 |
  | 9–11 | 3 | 0 |
  | 12–14 | 4 | 0 |
  | 15–16 | 5 | 0 |
  | 17–18 | 6 | 0 |
  | 19 | 7 | 0 |
  | 20+ | 8 | 0 |

- **Establishing state.** Only triggered at `effective < 1` (i.e. no rounds at all) → `handicap_index=None`, `status="establishing"`, `rounds_needed=1`.
- **12-month low cap.** A user's index cannot rise more than **5.0** above their lowest index in the preceding 12 months (`apply_twelve_month_cap`). The cap only prevents rises — it never pushes the index down.
- **Snapshot poison-lows.** `HandicapSnapshot` is append-only and the cap MINs over it — so a garbage low from a since-deleted bug-era round silently clamps every future index (Paul sat at 9.0 with a real 25.0 until his orphaned 4.0 snapshot was purged, 2026-07-02). Deleting a round does NOT remove the snapshots it produced, and there is no API for snapshot deletion — cleanup is direct SQL + `POST /golf/handicap/<id>/recompute`. If an index looks impossibly low or won't rise after good rounds, check snapshot history before suspecting the engine.
- **9-hole rounds.** Weighted at **0.5** toward the "last 20" pool. `_effective_round_count` = full 18-hole rounds + (nine-hole rounds // 2).
- **Reference fixtures.** `backend/tests/fixtures/whs_reference_cases.json` + `backend/tests/test_handicap.py` exercise every adjustment-table row plus NDB cap, establishing, 12-month cap, and 9-hole weighting. Any handicap change must re-pass this fixture bit-for-bit.

### Grid parser (primary since 2026-07-02)

`services/scorecard_grid.py` — pure, DB-free. Pipeline: card-quad detection →
vanishing-point metric rectification from the table's own Hough line families
(the quad alone is unreliable: clips/pavement pollute it) → morphological
h/v line profiles → cell matrix → Vision OCR symbols (from ONE pass on the
original image) mapped through the composed homography into cells → semantic
labeling (PAR row anchors the 18 hole columns; multi-digit par-row cells are
OUT/IN/TOT) → per-cell scores with confidence → checksum validation against
handwritten OUT/IN/TOT (mismatch flags the lowest-confidence hole, never
silently accepts) → tee rating/slopes from y-banded `NN.N/NNN` text lines
(grid rows merge under clips; y-banding after rectification doesn't).

Measured on `tests/fixtures/scorecards/`: 55/55 score cells, 36/36 pars,
10/10 tees (baseline with the legacy parser: 18/55). Tests:
`venv/bin/python -m pytest tests/test_scorecard_grid.py --noconftest`;
debug overlays + hit-rate report: `venv/bin/python tools/grid_debug.py`.
Gotchas learned on real cards: Vision double-emits glyphs (dedupe at <12px
— wider merges legit repeated digits like slope "116"); handwritten names
straddle printed row lines (nameless digit rows adopt an adjacent name row);
tee rows are half the height of header rows so grid rows can merge them.

Falls back to the legacy symbol parser below (`GridParseError`, zero players,
or any crash), which remains fully functional.

### Legacy OCR Parser (multi-player fallback)
`_parse_scorecard_symbols(symbols, page_width, page_height)` in `golf_routes.py` operates on **symbol-level** Vision output (not words — Vision tends to concatenate handwritten digits into garbage tokens like `"7864856T65854494444"`).

Pipeline:
1. Group symbols into rows by y-proximity (~2% of page height).
2. Run `_extract_pars` (see below) on all symbols to recover the per-hole par sequence. This happens once per scorecard and is shared across every detected player.
3. For each row, skip if it has too many letters (label/tee row) or too few digits (hole-number or blank row).
4. Extract the leftmost contiguous letter cluster as the player's name; reject known labels (`PAR`, `HANDICAP`, `BLACK`, `GOLD`, `GREEN`, `WHITE`, …) and label prefixes.
5. Cluster the row's digits by x-gap: single-digit clusters are hole scores; multi-digit clusters (`"56"`, `"105"`) are subtotals (OUT/IN/TOT) and used as column separators.
6. First 9 singles before the OUT subtotal = front 9; first 9 singles between OUT and IN = back 9.
7. Return `{players: [{name, holes: [{hole_number, par, strokes, ocr_confidence}] x18}, ...]}` with each hole's `par` pulled from the extracted sequence (falls back to `4` only when extraction fails).

Image rotation: `_auto_orient_image` only applies EXIF transpose. If the parser detects no players, the upload route retries OCR on a 90°-rotated copy and keeps whichever pass produced more players. It does **not** force portrait orientation (that was a previous bug that broke valid landscape scorecards).

### Par-row extraction (`_extract_pars`)

Per-hole pars come from the scorecard itself (not a hardcoded 4). The extractor lives next to the player parser in `golf_routes.py` and is driven by three helpers:

1. **`_find_par_label(symbols)`** — locates the `PAR` anchor. Requires three letters `P`–`A`–`R` consecutive in x with consistent y (within 20 px), and rejects any match where a fourth letter follows within 100 px (so `PARTICIPANT` / `PART` / `PARK` can't masquerade as the PAR row).
2. **`_fit_row_slope(symbols, anchor_y, anchor_x)`** — scorecard photos are tilted a few degrees from the camera, so the PAR row's y drifts by ~150 px across 3500 px of x (typical slope ≈ -0.04). The helper iteratively fits OLS (y vs. x) across 3 passes — wide y-band (±180 px), then tighten (±90), then tighten again (±55) — so noise from adjacent rows (HANDICAP, tee yardages) gets squeezed out.
3. **`_extract_pars(...)`** — projects the slope-adjusted y-line from the PAR anchor, keeps digits within ±tolerance (≈1.5% of page height), clusters them by x-gap, treats multi-digit clusters as OUT/IN/TOT subtotals (separator between the two nines), and keeps only single-digit values in the legal 3–6 range. Returns a list of 18 pars, or `None` if fewer than 14 could be recovered (in which case the caller falls back to par-4).

The fixture scorecard (`tests/fixtures/golf_scorecard_ocr.json`) recovers `[4,4,3,5,5,4,4,3,4, 4,4,4,5,3,4,5,3,4]` — front 36 / back 36 / total 72. `tools/run_golf_parser_tests.py` covers the happy path, the `None`-when-absent path, and the end-to-end wiring into player holes.

### Multi-player auto-save (`_save_guest_player_round`)

When OCR returns two or more players on the same scorecard (e.g. TOM and CHRIS), the upload route auto-creates a guest `User` for each detected name and saves a fully-confirmed `Round` + `HoleScore` rows under that guest, in addition to the uploader's own primary round. Each guest then appears on the leaderboard with their own handicap.

Keys:
- **Deterministic email.** A detected name maps to `<slug>@guest.tomsgym.local` (slug = lowercased alphanumeric). Same name across uploads → same guest user → handicap accumulates instead of duplicating.
- **Auto-confirm.** Differential is computed at upload with the flat NDB-10 cap (`min(strokes, 10)` per hole), the round is stored with `processing_status='confirmed'`, and a `HandicapSnapshot` is written via `_recalculate_handicap`. No human review step required.
- **Partial rounds** (`_classify_guest_round`): <6 captured holes → not saved; exactly 9 in one nine → saved as a 9-hole round whose differential is scored against half the 18-hole rating then **doubled** to an 18-hole equivalent (raw 9-hole diffs are ~half scale and would always win the lowest-N pool — a back-nine-only card once hit the leaderboard at -42.0); exactly 18 → scored normally; anything else → saved for display, `score_differential` NULL (invisible to the handicap engine).
- **Failure isolation.** Each guest save runs in a try/except; a single guest failure logs a warning and rolls back that sub-transaction without killing the uploader's primary round.
- **Auth-method nullable.** Guest `User` inserts leave `auth_method` NULL because the enum only covers `('google','password')`; the guest path is neither.

### Leaderboard stale-snapshot filter

The leaderboard query picks the most-recent `HandicapSnapshot` per user with a subquery pattern:

```sql
SELECT user_id, handicap_index, rounds_used, created_at
FROM (
    SELECT DISTINCT ON (user_id)
           user_id, handicap_index, rounds_used, created_at
    FROM "HandicapSnapshot"
    ORDER BY user_id, created_at DESC
) _latest
WHERE handicap_index IS NOT NULL
```

The `WHERE handicap_index IS NOT NULL` must run **outside** `DISTINCT ON`. Doing it inside would let a stale non-null snapshot outrank a later null one, so a user who deletes all their rounds would stick around on the leaderboard with their old index. Keep this inversion on any future snapshot-based query.

### Avatars (`getGolfAvatar(name, id)`)

`frontend/src/lib/api.ts` exposes `getGolfAvatar(name, id)` — a DiceBear `avataaars` URL helper used by `GolfLeaderboard` and `GolfProfile`. A `KNOWN_GOLFER_AVATARS` map carries hand-tuned presets for recurring fictional names (today: `tom` = tanned skin / dark hair / hoodie, `chris` = lighter skin / curly hair / beard / sweater). Unknown names fall back to a deterministic avataaars seeded by the name (or `id` when name is missing), so the same golfer keeps the same face across visits. The older `getGhibliAvatar` (Pokémon sprites) is still used by lifting/challenges UI — don't remove it.

### Tests
- `tests/test_golf_parser.py` — pytest suite covering helpers + end-to-end multi-player parsing against a real OCR fixture (`tests/fixtures/golf_scorecard_ocr.json`).
- `tools/run_golf_parser_tests.py` — standalone runner that bypasses the DB-heavy conftest. Use this for quick iteration: `cd backend && venv/bin/python tools/run_golf_parser_tests.py`.
- `tools/ocr_inspect3.py` — debug tool: runs Vision API on a local image and prints symbol-level row/column layout. Requires `GOOGLE_APPLICATION_CREDENTIALS=backend/credentials.json`.

### Frontend Pages
| Route | Component | Description |
|-------|-----------|-------------|
| `/golf/upload` | `GolfUpload` | Scorecard upload + course info form. |
| `/golf/review/:roundId` | `GolfReview` | OCR result review: shows detected players, lets user pick their row, edit scores, confirm. A "Change" link on the course/tee header opens `TeePickerDrawer` (`frontend/src/components/golf/TeePickerDrawer.tsx`) — up to 4 tee cards, editable rating (step 0.1) / slope (step 1) / yardage, `DifficultyMeter` anchored at slope 113, and a live differential preview. Selected tee carries the `fw-selected` class (2px `fw-info` border from Phase A). |
| `/golf/round/:roundId` | `GolfRound` | Completed round detail; reads nested `course` / `tee`. |
| `/golf/leaderboard` | `GolfLeaderboard` | Handicap leaderboard; rows are fed from latest `HandicapSnapshot` per user. |
| `/golf/profile/:userId?` | `GolfProfile` | User's golf stats and rounds. Consumes `GET /golf/users/:id/handicap/history` for the handicap trend (Phase D dashboard surface). Each expanded round renders a compact 9-up hole grid showing `#` / `Par N` / strokes with color-coded cells (birdie / par / bogey+). The scorecard thumbnail is clickable and opens a fullscreen lightbox (Escape or click-outside to close, body scroll locked) so the user can verify OCR scores against the physical card. Reads the user name from `GET /users/:id/profile` via `profileRes.data.user.name` — note the `.user` nesting; the endpoint wraps user fields (`{user: {name, email, ...}, competitions: [...], ...}`) and early code that read `profileRes.data.name` silently fell through to the avatar's fallback seed. |

### Field Rename Map (Phase A → Phase B)
Anyone reading pre-2026-04-18 PRs, branches, or issues should map old flat fields onto the new nested shape:

| Old (flat) | New (nested) |
|---|---|
| `course_rating` | `tee.rating_18` |
| `slope_rating` | `tee.slope_18` |
| `course_name` | `course.name` |
| `played_at` | `played_on` |
| `differential` | `score_differential` |
| `adjusted_gross_score` | `total_score` |
| `holes: GolfHole[]` (array) | `hole_scores: GolfHole[]` |
| `holes` (top-level) | now a number: `9` or `18` (round length) |
| `GolfHandicap.handicap_index` | latest `HandicapSnapshot.handicap_index` |
