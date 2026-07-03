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

Goal: give each challenge its own ranked leaderboard, on the challenge page.

## Decisions

Three design questions were raised. One was answered by the user; the other two
are defaulted below and **flagged for confirmation** — flip either without
reshaping the design.

| Question | Decision | Confirmed? |
|---|---|---|
| Where it lives | **On the challenge page** (`ChallengeDetail.tsx`), as a tab toggle: `Leaderboard \| Lift Feed`, Leaderboard default. | ✅ user |
| Grouping | **One flat board** — a single ranked list for the whole challenge. No weight-class/gender segmentation this iteration (deferred). | ✅ user |
| Ranking metric | **Best-lift total** — sum of each athlete's *best completed* attempt per lift type present in the challenge. Reduces to "best single lift" for single-lift challenges. | ⚠️ default |

### Why best-lift total (vs. the alternatives)

- **Sum of all attempts** (today's `total_weight`) rewards volume — an athlete
  who uploads ten mediocre squats outranks one who uploads a single huge squat.
  Wrong incentive for a competition.
- **Best single lift** throws away information for multi-lift challenges (a
  squat+bench+deadlift meet should reward the all-round total).
- **Best-lift total** = classic powerlifting total. It adapts: if the challenge
  is configured for one lift type, the sum has one term and it behaves like
  "best single lift"; if three, it's the meet total. One metric, no mode switch.

Only `status = 'completed'` attempts count (an approved lift). `pending` and
`failed` attempts are ignored for ranking but still appear in the lift feed.

### Plank / time-based lifts (scope boundary)

`Plank` is a `lift_type` but is scored by held-time, not weight (the feed already
hides weight for planks). For this iteration the leaderboard ranks by
`weight_kg`; a plank-only challenge would rank everyone at 0. **Out of scope
now**, called out explicitly: a follow-up can rank plank challenges by
`total_in_plank_s` from `LiftingResult`. The endpoint returns a `metric` field
(`"weight" | "time"`) so the frontend and a future iteration can branch without
a breaking change.

## Architecture

Ranking logic lives **server-side** in a new endpoint plus a pure, DB-free
helper — mirroring the existing `/golf/leaderboard` pattern (ranking is computed
in one testable place, not smeared across the React component). The frontend
renders whatever the endpoint returns.

```
ChallengeDetail.tsx
  ├─ Tab: Leaderboard  ──GET──▶ /competitions/:id/leaderboard ──▶ rank_challenge()  (pure)
  └─ Tab: Lift Feed    (existing feed, unchanged)
```

### Component 1 — `rank_challenge()` (pure helper)

New module `backend/toms_gym/services/challenge_leaderboard.py`. Pure, DB-free,
unit-testable in isolation.

```python
def rank_challenge(participants, *, metric="weight"):
    """
    participants: list of {
        user_id, name, weight_class, gender,
        attempts: [{lift_type, weight_kg, status, created_at}]
    }
    Returns ranked rows:
    [{
        rank, user_id, name, weight_class, gender,
        total,                         # sum of best completed weight per lift_type
        best_by_lift: {lift_type: weight}, # per-lift breakdown for the table
        attempt_count                  # completed attempts (tiebreak / display)
    }]  sorted by total desc.
    """
```

Rules:
- Consider only `status == 'completed'` attempts.
- Per athlete, per `lift_type`: take `max(weight_kg)`. `total = sum` of those maxes.
- Sort by `total` descending.
- **Tiebreak:** equal totals → the athlete who reached their total *earliest*
  wins (min `created_at` across their best attempts). Deterministic; rewards
  getting there first.
- Athletes with zero completed attempts are returned with `total = 0` at the
  bottom (they joined but haven't landed a lift) — keeps the "who's joined"
  signal without polluting the podium. Frontend may choose to dim these rows.

### Component 2 — `GET /competitions/<id>/leaderboard`

New route in `competition_routes.py`. Flat board — no query params this
iteration.

- Reuses the same participant+attempt query already backing
  `/competitions/<id>/participants` (extended to include each attempt's
  `created_at` for the tiebreak).
- Response:
  ```json
  {
    "competition_id": "...",
    "metric": "weight",
    "lift_types": ["Squat", "Bench Press", "Deadlift"],
    "rows": [ { "rank": 1, "name": "Tom", "total": 520,
               "best_by_lift": {"Squat":180,"Bench Press":120,"Deadlift":220},
               "weight_class": "83kg", "gender": "male", "attempt_count": 3 } ]
  }
  ```
- `lift_types` is the distinct set of lift types seen across completed attempts
  (drives the table's columns). Unit is kg in the DB; the frontend already
  displays lift weights in lbs elsewhere — **the endpoint returns raw kg and the
  frontend formats**, matching how the existing feed treats `weight`.

### Component 3 — Leaderboard tab UI (`ChallengeDetail.tsx`)

- A tab toggle above the current content: `Leaderboard | Lift Feed`. Default
  Leaderboard. The existing feed JSX moves under the "Lift Feed" tab unchanged.
- Leaderboard table columns: `Rank`, `Athlete` (avatar + name, links to
  profile), one column per lift type in `lift_types`, `Total`. Medal styling for
  ranks 1–3 (reuse the visual language already in `GolfLeaderboard`).
- One flat ranked list — no filter chips this iteration.
- Empty state: "No completed lifts yet — be the first on the board!" with the
  existing Upload button.
- A thin `getChallengeLeaderboard(id)` is added to `frontend/src/lib/api.ts`.

## Data flow

1. `ChallengeDetail` mounts → fetches challenge + participants (as today) and, for
   the Leaderboard tab, `GET /competitions/:id/leaderboard`.
2. Backend loads participants + their completed attempts, calls `rank_challenge()`,
   returns ranked rows.
3. Component renders the flat ranked table.

No schema migration. No new tables. Ranking is derived at read time from
existing `Attempt` / `UserCompetition` rows.

## Error handling

- Unknown `competition_id` → 404 (consistent with sibling endpoints).
- Challenge with no participants or no completed attempts → 200 with `rows: []`
  and `lift_types: []`; UI shows the empty state.
- Endpoint failure → the tab shows an inline error and a retry; the Lift Feed tab
  is unaffected (independent fetch).

## Testing

- **`tests/test_challenge_leaderboard.py`** (pure helper): best-of-per-lift
  rollup; single-lift challenge reduces to best single lift; `pending`/`failed`
  excluded; tiebreak by earliest `created_at`; zero-attempt athletes sort last.
- **Route test** in the competition-routes test suite: happy path shape, 404 on
  bad id, empty-challenge case.
- **Frontend**: a render test for the tab toggle + table given a mock leaderboard
  payload.

## Out of scope (explicit)

- Weight-class / gender segmentation and filter chips — flat board only for now.
  The response still carries per-row `weight_class` / `gender`, so adding filters
  later is additive (no shape change).
- Plank/time-based ranking (endpoint reserves `metric` for it).
- Real-time updates / websockets — leaderboard is fetched on tab open.
- Historical/podium snapshots — computed live each time.
- Changes to the global `/leaderboard` page.

## Files touched

| File | Change |
|---|---|
| `backend/toms_gym/services/challenge_leaderboard.py` | **New** — pure `rank_challenge()`. |
| `backend/toms_gym/routes/competition_routes.py` | **New** `GET /competitions/<id>/leaderboard`; extend participant query with `created_at`. |
| `backend/tests/test_challenge_leaderboard.py` | **New** — helper unit tests. |
| `backend/tests/test_competition_routes.py` | Add route tests. |
| `frontend/src/lib/api.ts` | **New** `getChallengeLeaderboard()`. |
| `frontend/src/pages/ChallengeDetail.tsx` | Tab toggle + Leaderboard table; existing feed moves under a tab. |
| `frontend/src/lib/types.ts` | `ChallengeLeaderboardRow` type. |
