# Golf Grid-Based Scorecard Parser + Photo-Only Upload — Design

**Date:** 2026-07-02 · **Status:** Approved (user), implementation on `golf/grid-parser`

## Problem

The scorecard OCR pipeline (Google Vision `document_text_detection` + geometry
heuristics in `golf_routes.py`) reconstructs table structure from loose symbol
positions. Measured failures on two real cards (fixtures `1000005113`,
`1000005117`):

| Card | Failure | Root cause |
|---|---|---|
| 5113 | Tom's row lost entirely (0/18) | `_group_rows` 100px span cap severed the handwritten name from its score digits |
| 5113 | Pars defaulted to 4 (0/18) | `_fit_row_slope` OLS converged onto the Handicap row below the PAR anchor |
| 5117 | All scores assigned to holes 1–9; actually written on 10–18 | No column awareness — sequential assignment with no OUT separator |
| both | Pencil misreads accepted silently | No cross-checks against handwritten subtotals |

Separately, the upload form requires course/slope/rating/date entry that the
photo (or review step) can supply.

## Design

### 1. `backend/toms_gym/services/scorecard_grid.py` (new, pure, DB-free)

Primary parser; same module pattern as `services/handicap.py`.

1. **Rectify** — OpenCV: find the card quadrilateral (white card, dark
   background), homography-warp to axis-aligned rectangle. No quad → skip warp.
2. **Grid extraction** — morphological long-kernel h/v line detection →
   intersections → cell matrix. Missing/occluded lines (clip over card)
   interpolated from regular column spacing.
3. **One OCR pass** on the rectified image; symbols assigned to cells by
   centroid containment.
4. **Semantic labeling** — hole-header row (printed 1–18), OUT/IN/TOT columns,
   PAR/HANDICAP/tee rows via label column; player rows = scoring-band rows with
   non-label letters in the label cell.
5. **Per-cell scores** — digits per (player row × hole column) → strokes +
   confidence. Multi-digit in a cell (strikeover) → highest-confidence digit,
   flagged.
6. **Checksums** — front/back sums vs handwritten OUT/IN/TOT; mismatch flags
   lowest-confidence holes `needs_review` instead of silent acceptance.
7. **Card metadata** — per-tee rating/slope from printed `NN.N/NNN` patterns,
   course name from header text when present, handwritten date when legible.

**Fallback chain:** grid parse fails → existing `_parse_scorecard_symbols`
(unchanged) → existing rotation retry.

### 2. API + schema

- Migration `009`: `Round.course_id` nullable (course unknown until review;
  a round cannot be *confirmed* without course/tee since the differential
  needs rating/slope — fits `pending → ocr_complete → confirmed`).
- `/golf/upload`: `course_name` optional; extracted course/tee matched via
  `match_or_create_*`; response gains `needs_course` and per-hole `flagged`.
- `PUT /golf/round/<id>/scores`: accepts `course_id`, `tee_id`, `played_on`
  (closes the Phase D tee-override gap).

### 3. Frontend

- **GolfUpload**: photo picker + email-if-anonymous only. No other fields.
- **GolfReview**: course search prompt when `needs_course` (reuses
  `searchCourses`), extracted tees in `TeePickerDrawer`, editable date
  (default today), flagged holes visually highlighted.

### 4. Validation

- Fixtures: both photos + cached Vision OCR dumps + human-verified ground
  truth JSON in `backend/tests/fixtures/`.
- Metric: cell-level capture rate (correct strokes on correct holes / total
  handwritten cells) + player detection + par extraction.
- Baseline (2026-07-02): 5113 — Paul 18/18, Tom 0/18, pars 0/18;
  5117 — pars 18/18, 0 scores placed on correct holes.
- `tools/grid_debug.py` renders grid + cell-assignment overlay images.
- Deps: `opencv-python-headless`, `numpy`.

## Error handling

- Any OpenCV stage exception → log warning, fall back to symbol parser.
- Vision API remains the only network dependency; behavior on OCR failure
  unchanged from today.
- Ambiguous cells never guess silently: they carry `flagged: true` +
  confidence to the review UI.

## Out of scope

- Course-name OCR from the card's cover side (most cards don't show it on
  the grid side); resolved via review-page search instead.
- LLM-based extraction (explicitly declined by user).
- PCC, hole-handicap stroke allocation extraction (existing Phase D notes).
