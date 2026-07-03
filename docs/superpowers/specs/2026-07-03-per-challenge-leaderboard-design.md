# Per-Challenge Leaderboard — Design

**Date:** 2026-07-03
**Status:** Draft (awaiting review)
**Author:** Claude + Tom

## Problem

A challenge (`Competition`) page today shows an unranked "Lifts" feed sorted by
weight. There is no true *leaderboard* scoped to a single challenge — no ranks,
no per-athlete rollup, no way to see who is winning. The only ranked view
(`/leaderboard`, `Leaderboard.tsx`) flattens every competition into one global
list, which is not what a participant in a specific challenge wants to see.

**The primary driver is the plank challenge** — a plank has no weight, it's ranked
by how long you hold it. So the leaderboard must rank by *time held* for plank
challenges, and by *weight* for lifting challenges. Time ranking is a first-class
path, not an afterthought.

Goal: give each challenge its own ranked leaderboard, on the challenge page,
that ranks by the metric that fits the challenge.

## Decisions

| Question | Decision | Confirmed? |
|---|---|---|
| Where it lives | **On the challenge page** (`ChallengeDetail.tsx`), as a tab toggle: `Leaderboard \| Lift Feed`, Leaderboard default. | ✅ user |
| Grouping | **One flat board** — a single ranked list for the whole challenge. No weight-class/gender segmentation this iteration (deferred). | ✅ user |
| Ranking metric | **Per-challenge metric.** Plank challenge → rank by **longest hold** (`total_in_plank_s`, DESC). Lifting challenge → **best-lift total** (sum of each athlete's best `completed` attempt per lift type). | ✅ user (plank is primary) |

### The two metrics

A challenge is ranked by exactly one metric, chosen from the challenge's lift
type (see "Metric selection"). The endpoint returns a `metric` field
(`"time" | "weight"`) telling the frontend how to render.

**`time` (plank challenges) — the headline path.**
- Rank by the athlete's **best (longest) hold** across their `completed` plank
  attempts, descending. Longest hold wins.
- Held time is read from the analysis result, not the attempt row:
  `LiftingResult.report->>'total_in_plank_s'`. When the lifting analysis finishes
  it sets `Attempt.status='completed'` and writes the report in the same commit
  (`lifting_processor.py:183,202`), so any `completed` plank attempt has a hold
  time available.
- `report->>'overall_form_score'` is carried through for display (and as the
  tiebreak — see below), but ranking is on time.

**`weight` (lifting challenges).**
- Rank by **best-lift total**: for each athlete, take `max(weight_kg)` per
  `lift_type` among their `completed` attempts, then sum those maxes. Classic
  powerlifting total. For a single-lift challenge this reduces to "best single
  lift". Rewards strength over upload volume (unlike today's sum-of-all-attempts
  `total_weight`).

Only `status = 'completed'` attempts count in either metric; `pending`/`failed`
are ignored for ranking but still show in the lift feed.

### Metric selection (how the route decides)

`metric = "time"` iff the challenge is **plank-only**, else `"weight"`.

Determination, in order:
1. The challenge's declared lift types (`lifttypes` parsed from
   `Competition.description` metadata, as `get_competition_by_id` already does).
   If that set is exactly `{"Plank"}` → `time`.
2. Fallback when metadata is absent/empty: infer from `completed` attempts — if
   every completed attempt is `Plank` → `time`.
3. Otherwise → `weight`.

Edge case — a challenge that mixes Plank with weighted lifts: ranked by `weight`,
and plank attempts are excluded from the weight total (you can't add seconds to
kilograms). Documented, not silently blended.

## Architecture

Ranking logic lives **server-side** in a new endpoint plus a pure, DB-free
helper — mirroring the `/golf/leaderboard` pattern (ranking computed in one
testable place, not smeared across the React component). The frontend renders
whatever the endpoint returns.

```
ChallengeDetail.tsx
  ├─ Tab: Leaderboard  ──GET──▶ /competitions/:id/leaderboard ──▶ rank_challenge(metric=…)  (pure)
  └─ Tab: Lift Feed    (existing feed, unchanged)
```

### Component 1 — `rank_challenge()` (pure helper)

New module `backend/toms_gym/services/challenge_leaderboard.py`. Pure, DB-free,
unit-testable in isolation.

```python
def rank_challenge(participants, *, metric):
    """
    metric: "time" | "weight"
    participants: list of {
        user_id, name, weight_class, gender,
        attempts: [{
            lift_type, weight_kg, status, created_at,
            held_s,          # float|None — from LiftingResult report (plank)
            form_score,      # float|None — report overall_form_score (plank)
        }]
    }
    Returns ranked rows sorted best-first:
    [{
        rank, user_id, name, weight_class, gender,
        score,             # metric="time": best hold seconds; "weight": best-lift total kg
        best_by_lift,      # weight: {lift_type: max_kg}; time: {"Plank": best_hold_s}
        form_score,        # time only: form % at the best hold (display)
        attempt_count,     # completed attempts counted
    }]
    """
```

Rules common to both metrics:
- Consider only `status == 'completed'` attempts.
- Sort by `score` descending.
- **Tiebreak:** equal score → earliest achievement wins (min `created_at` of the
  attempt(s) producing the best score). For `time`, form score is a secondary
  tiebreak before `created_at` (cleaner hold ranks higher on a tie). Deterministic.
- Athletes with zero qualifying attempts → `score = 0` (time) / `0` (weight),
  sorted last. Keeps the "who joined" signal off the podium; frontend may dim them.

Metric-specific:
- `time`: per athlete, `score = max(held_s)` over completed plank attempts with a
  non-null `held_s`. A completed plank attempt whose analysis hasn't produced a
  hold time yet (`held_s is None`) doesn't count toward the score.
- `weight`: per athlete, per `lift_type` → `max(weight_kg)`; `score = sum` of maxes.

### Component 2 — `GET /competitions/<id>/leaderboard`

New route in `competition_routes.py`. Flat board — no query params this iteration.

- Loads the challenge (404 if missing), determines `metric` (see selection rules).
- Loads participants + their `completed` attempts. **LEFT JOINs `LiftingResult`**
  on `attempt_id` and pulls `report->>'total_in_plank_s'` (as `held_s`) and
  `report->>'overall_form_score'` (as `form_score`) so the pure helper gets hold
  times without touching the DB. (This extends the query already backing
  `/competitions/<id>/participants`, plus each attempt's `created_at`.)
- Calls `rank_challenge(participants, metric=metric)`.
- Response:
  ```json
  {
    "competition_id": "...",
    "metric": "time",
    "lift_types": ["Plank"],
    "rows": [
      { "rank": 1, "name": "Tom", "score": 132.4,
        "best_by_lift": {"Plank": 132.4}, "form_score": 0.91,
        "weight_class": "83kg", "gender": "male", "attempt_count": 2 }
    ]
  }
  ```
  For `metric="weight"`, `score` is the best-lift total in kg and `best_by_lift`
  maps each lift type to its best kg; `form_score` is omitted/null.
- `lift_types` = the distinct lift types across completed attempts (drives table
  columns for weight; always `["Plank"]` for a plank board).
- Weights are returned raw in kg (frontend formats to lbs, matching the existing
  feed). Hold times are returned raw in **seconds** (frontend formats `m:ss`).

### Component 3 — Leaderboard tab UI (`ChallengeDetail.tsx`)

- A tab toggle above the current content: `Leaderboard | Lift Feed`. Default
  Leaderboard. The existing feed JSX moves under the "Lift Feed" tab unchanged.
- The table renders by `metric`:
  - **`time` (plank):** `Rank`, `Athlete` (avatar + name → profile),
    `Best Hold` (formatted `m:ss`, e.g. `2:12`), `Form` (`form_score` as %).
  - **`weight`:** `Rank`, `Athlete`, one column per lift type, `Total` (lbs).
- Medal styling for ranks 1–3 (reuse the visual language in `GolfLeaderboard`).
- One flat ranked list — no filter chips this iteration.
- Empty state (metric-aware): plank → "No holds recorded yet — be the first to
  plank!"; weight → "No completed lifts yet — be the first on the board!" Each
  with the existing Upload button.
- A thin `getChallengeLeaderboard(id)` is added to `frontend/src/lib/api.ts`.

## Data flow

1. `ChallengeDetail` mounts → fetches challenge + participants (as today) and, for
   the Leaderboard tab, `GET /competitions/:id/leaderboard`.
2. Backend determines the metric, loads participants + completed attempts (LEFT
   JOIN `LiftingResult` for plank hold times), calls `rank_challenge()`, returns
   ranked rows + `metric`.
3. Component renders the flat ranked table in the shape dictated by `metric`.

No schema migration. No new tables. Ranking is derived at read time from existing
`Attempt` / `UserCompetition` / `LiftingResult` rows.

## Error handling

- Unknown `competition_id` → 404 (consistent with sibling endpoints).
- Challenge with no participants / no completed attempts → 200 with `rows: []`
  and the correct `metric` + `lift_types`; UI shows the metric-aware empty state.
- Plank attempt `completed` but analysis produced no hold time → excluded from the
  score (not counted), athlete falls to `score = 0` if it was their only attempt.
- Endpoint failure → the tab shows an inline error + retry; the Lift Feed tab is
  unaffected (independent fetch).

## Testing

- **`tests/test_challenge_leaderboard.py`** (pure helper):
  - `time`: longest hold wins; `held_s=None` attempts excluded; best-of-multiple
    holds per athlete; tiebreak by form score then `created_at`; zero-hold athletes last.
  - `weight`: best-of-per-lift rollup; single-lift reduces to best single lift;
    `pending`/`failed` excluded; tiebreak by earliest `created_at`.
- **Route test** (`test_competition_routes.py`): plank challenge returns
  `metric="time"` and hold-ranked rows; lifting challenge returns `metric="weight"`;
  404 on bad id; empty-challenge case; metric-selection (plank-only vs mixed).
- **Frontend**: render test for the tab toggle + both table shapes (time vs weight)
  given mock payloads.

## Out of scope (explicit)

- Weight-class / gender segmentation and filter chips — flat board only for now.
  The response carries per-row `weight_class` / `gender`, so filters are additive later.
- Real-time updates / websockets — leaderboard is fetched on tab open.
- Historical/podium snapshots — computed live each time.
- Blended/mixed metrics in one board (plank + weighted lifts share no scale).
- Changes to the global `/leaderboard` page.

## Files touched

| File | Change |
|---|---|
| `backend/toms_gym/services/challenge_leaderboard.py` | **New** — pure `rank_challenge()` (time + weight). |
| `backend/toms_gym/routes/competition_routes.py` | **New** `GET /competitions/<id>/leaderboard`; metric selection; participant query extended with `created_at` + LEFT JOIN `LiftingResult` for plank hold time/form. |
| `backend/tests/test_challenge_leaderboard.py` | **New** — helper unit tests (time + weight). |
| `backend/tests/test_competition_routes.py` | Add route tests. |
| `frontend/src/lib/api.ts` | **New** `getChallengeLeaderboard()`. |
| `frontend/src/pages/ChallengeDetail.tsx` | Tab toggle + metric-aware Leaderboard table; existing feed moves under a tab. |
| `frontend/src/lib/types.ts` | `ChallengeLeaderboardRow` / `ChallengeLeaderboard` types. |
