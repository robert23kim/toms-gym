# Golf Scorecard & Handicap Tracker — Design Spec

## Problem

Tom's Gym supports lifting and bowling competitions but has no golf tracking. Users want to upload scorecard photos, have scores extracted automatically, track their WHS handicap index over time, and compete on a global leaderboard.

## Solution

A standalone golf module (`/golf/*` routes) with:
- **Photo upload** → Google Cloud Vision OCR extracts hole-by-hole scores
- **Review & confirm** screen for users to verify/correct OCR results
- **WHS handicap calculation** (best 8 of last 20 differentials)
- **Card-based profile** showing round history with birdie/bogey tags
- **Global leaderboard** ranked by lowest handicap index

## User Flows

### Upload a Round
1. User navigates to `/golf/upload`
2. Takes/selects photo of scorecard
3. Enters course name, slope rating, course rating, date
4. Submits → backend uploads image to GCS, runs Vision API OCR
5. Redirected to `/golf/review/:roundId` with extracted scores

### Review & Confirm Scores
1. 18-cell grid shows OCR-extracted scores, color-coded by relation to par
2. Low-confidence cells (<0.7) highlighted with amber border
3. User taps any cell to correct misreads
4. Confirms → backend computes differential and recalculates handicap
5. Navigated to profile or round detail

### View Profile & History
1. `/golf/profile/:userId` shows centered profile with handicap badge
2. Card feed of past rounds: course name, score, differential, birdie/bogey tags
3. Tap card → expands inline to show hole-by-hole grid + scorecard thumbnail

### Leaderboard
1. `/golf/leaderboard` shows all users with valid handicap (3+ rounds)
2. Ranked by lowest handicap index
3. Tap row → navigates to that user's golf profile

## Architecture

### Database (3 new standalone tables)

**GolfRound** — One row per 18-hole round
- Links to User table via `user_id`
- Stores course info, total score, differential, scorecard image URL, OCR data
- `processing_status`: pending → ocr_complete → confirmed | failed

**GolfHoleScore** — 18 rows per round
- Hole number, par, strokes, OCR confidence, manually_corrected flag
- Unique constraint on (round_id, hole_number)

**GolfHandicap** — One row per user (upserted on each confirmation)
- Current handicap_index, rounds_used, differentials_used (JSONB array)

No dependency on existing Competition/UserCompetition/Attempt tables.

### Backend (Flask blueprint)

**New file**: `golf_routes.py` with `/golf` URL prefix

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/golf/upload` | POST | Upload scorecard + course data, run OCR inline |
| `/golf/round/<id>` | GET | Round detail with holes |
| `/golf/round/<id>/scores` | PUT | Confirm/correct scores, compute handicap |
| `/golf/round/<id>` | DELETE | Delete round, recalculate handicap |
| `/golf/rounds?user_id=` | GET | User's round history |
| `/golf/handicap/<user_id>` | GET | Current handicap |
| `/golf/leaderboard` | GET | Global rankings |

**OCR approach**: Inline (synchronous) — Vision API is fast enough (1-3s) to run during the upload request. No background processor needed.

**OCR parsing**: `document_text_detection` → find hole number rows (1-9, 10-18) to anchor grid → extract par row and score row → assign per-hole confidence from word-level API data.

**Handicap calculation**: Helper function called on confirm/delete. Fetches last 20 confirmed differentials, selects best N per WHS table, averages, truncates to 1 decimal, caps at 54.0. Minimum 3 rounds required.

### Frontend (5 new pages)

| Page | Route | Description |
|------|-------|-------------|
| GolfUpload | `/golf/upload` | Image picker + course data form |
| GolfReview | `/golf/review/:roundId` | Interactive 18-hole grid for OCR verification |
| GolfRound | `/golf/round/:roundId` | Read-only round detail |
| GolfProfile | `/golf/profile[/:userId]` | Card-based feed + handicap badge |
| GolfLeaderboard | `/golf/leaderboard` | Global handicap rankings |

**Styling**: Dark theme, Tailwind CSS, Framer Motion animations — consistent with existing app.

### Dependencies

- Add `google-cloud-vision>=3.5.0` to `requirements.txt`
- Add `ALLOWED_IMAGE_EXTENSIONS` to `storage.py`
- Cloud Run service account needs Vision API permissions

## Handicap Formula (WHS)

```
Differential = (113 / slope_rating) × (adjusted_gross_score - course_rating)

Handicap Index = average of best N differentials (from last 20 rounds)
  3-5 rounds  → lowest 1
  6-8 rounds  → lowest 2
  9-10 rounds → lowest 3
  11-12       → lowest 4
  13-14       → lowest 5
  15-16       → lowest 6
  17-18       → lowest 7
  19-20       → lowest 8

Truncate to 1 decimal (not rounded). Cap at 54.0.
```

## Error Handling

- **OCR fails**: Set `processing_status='failed'`, return error. User can retry upload.
- **Low confidence**: Per-hole confidence < 0.7 → amber border in review UI. User must verify.
- **Unparseable cells**: Set `strokes=0, ocr_confidence=0` → red indicator, requires manual entry.
- **Missing user**: Same passwordless pattern as bowling — auto-create from email.
- **Invalid course data**: Frontend validates slope (55-155) and rating (60-80) before submit.
