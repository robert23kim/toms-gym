# Lift History on Profile — Design

**Date:** 2026-07-06
**Status:** Approved (scope picked by Tom: full history list, not the LIMIT-bump quick fix)
**Problem:** Past lifts are effectively invisible: the profile endpoint hard-caps `uploaded_videos` at `LIMIT 10` with no pagination, and the gallery is thumbnails with no grades/hold times — you can't scan your history.

## Goal

A scannable, paginated lift history on the profile's Lift tab: date · lift type · weight · analysis payoff (grade pill for rep lifts, hold time for planks, status otherwise) · one tap to the VideoPlayer result. Thumbnails gallery stays below for visual browsing.

## Backend

### New endpoint: `GET /users/<user_id>/lifts?limit=&offset=`
In `routes/user_routes.py`. No auth (matches the profile read model). `limit` default 20, capped 50; `offset` default 0.

SQL (one query + one count):

```sql
SELECT a.id AS attempt_id, a.lift_type, a.weight_kg AS weight,
       a.video_url, a.created_at, a.status,
       uc.competition_id, c.name AS competition_name,
       lr.processing_status AS analysis_status,
       lr.report->>'overall_grade'  AS grade,
       lr.report->>'lift_type'      AS report_lift_type,
       (lr.report->>'total_reps')         AS total_reps,
       (lr.report->>'total_in_plank_s')   AS hold_s
FROM "Attempt" a
JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
JOIN "Competition" c ON uc.competition_id = c.id
LEFT JOIN "LiftingResult" lr ON lr.attempt_id = a.id
WHERE uc.user_id = :user_id AND a.video_url IS NOT NULL
ORDER BY a.created_at DESC
LIMIT :limit OFFSET :offset
```

Response: `{ "lifts": [row…], "total": <count>, "limit": n, "offset": n }`. Row shaping lives in a pure helper `services/lift_history.py: shape_lift_row(mapping) -> dict` (casts `total_reps`→int, `hold_s`→float, ISO-formats `created_at`, passes grades/status through, null-safe on every LiftingResult field) so it's DB-free testable. The JSONB `->>'…'` extraction keeps `per_second` off the wire.

`report_lift_type` (from the analysis) wins over `a.lift_type` for the plank-vs-reps display decision when present.

## Frontend

### `components/profile/LiftHistoryList.tsx`
Props `{ userId: string }`. Fetches `GET /users/:id/lifts?limit=20&offset=…`; "Load more" appends the next page while `lifts.length < total`. Fetch failure → renders nothing (gallery below still works). Empty first page → renders nothing (gallery's empty state already handles it).

Row layout (quiet-gym row language, whole row links to `/challenges/{competition_id}/participants/{userId}/video/{attempt_id}`):
- Left: date (`Jul 6`) + `Plank` / `Squat · 100kg` (weight shown only when > 0 and not a plank)
- Right: the payoff —
  - plank + completed → hold time `m:ss` (from `hold_s`)
  - rep lift + completed with grade → colored grade pill (A/B green, C yellow, D orange, F red — same mapping as VideoPlayer)
  - analysis `queued`/`processing` → muted "analyzing…"
  - `failed` or no analysis → muted "—"
- Chevron/"Open" trailing affordance.

Header: `My lifts (N)` using `total`. "Load more" button centered below.

### Profile wiring
`Profile.tsx` Lift tab: render `<LiftHistoryList userId={userId} />` in a card **above** the existing Lift Videos gallery. Nothing else on the page changes; the old LIMIT-10 `uploaded_videos` keeps feeding the gallery.

## Testing

- Backend: `tests/test_lift_history.py` (DB-free, registered in `tools/run_ci_tests.sh`) — `shape_lift_row` cases: full rep-lift row, plank row, no-analysis row, null grade, string numerics cast, missing keys.
- Frontend: `components/profile/__tests__/LiftHistoryList.test.tsx` (mock `../../config` + axios) — renders grade pill and formatted plank hold; correct VideoPlayer hrefs; "Load more" fetches offset 20 and appends; renders nothing on error/empty.
- Prod verify: curl the endpoint for the wonder725 user (has plank attempts) and screenshot the profile Lift tab.

## Non-goals

Bowling/golf history rows (profile tabs already link those verticals' own lists); deleting attempts; server-side filtering by lift type (client has full list soon enough at 20/page); touching the LIMIT-10 gallery feed.
