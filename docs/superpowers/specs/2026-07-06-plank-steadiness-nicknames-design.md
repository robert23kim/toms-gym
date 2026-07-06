# Plank Steadiness Nicknames — Design

**Date:** 2026-07-06
**Status:** Approved, ready for implementation plan
**Scope:** Frontend-mostly + one backend field. No new endpoints, no `per_second` on list rows.

## Problem

The plank challenge leaderboard shows raw hold times but nothing about *how* the
hold looked. The video result page already assigns a funny archetype
(`personality()` — 🗿 Statue, 💪 Steady Eddie, 🪼 Jelly, etc.) from the full
`per_second[]` form curve, but that flavor never reaches the leaderboard,
podium, or attempt history where people actually compare athletes.

We want funny nicknames on the plank challenge, derived from **steadiness** plus
two behavioral signals the user asked for: **number of attempts** and **time
between uploads**.

## Constraints & data reality

- `per_second[]` is heavy and is deliberately never shipped on list rows. So
  list-row nicknames must come from lighter signals.
- `body_line_stdev_deg` is a single top-level field in the plank report — cheap
  to surface. It already drives `steadinessScore()` on the video page.
- `attempt_count` and per-attempt upload **dates** are *already* on every
  `ChallengeLeaderboardRow` (`attempt_count`, `history[].date`). No new backend
  field is needed for the behavioral signals — only for steadiness.
- Attempts and cadence are **athlete-level**, not per-attempt. A single
  attempt-history line can only honestly reflect its own steadiness.

## Design

### Two vocabularies, one universe

- **Video result page** — unchanged. Keeps the full `personality()` archetype
  logic (it has `per_second`).
- **Everywhere else** — a lighter nickname built from `body_line_stdev_deg`,
  reusing the archetype names/emoji where they map cleanly onto one number.

### Base name: steadiness → archetype (per-attempt)

New pure helper in `lib/plankStats.ts`:

```ts
steadinessNickname(stdevDeg?: number | null): { name: string; emoji: string } | null
```

Runs `steadinessScore()` internally and maps its band:

| Steadiness score | Nickname | Emoji | Reuses |
|---|---|---|---|
| ≥ 85 (Rock Solid) | Statue | 🗿 | Statue archetype |
| ≥ 70 (Steady) | Steady Eddie | 💪 | Steady Eddie archetype |
| ≥ 50 (Wobbly) | The Wobbler | 🌊 | new (middle tier) |
| < 50 (Jelly Mode) | Human Jellyfish | 🪼 | Jelly archetype/emoji |
| null / NaN stdev | *(returns `null`)* | — | — |

Returning `null` for missing stdev is what lets non-plank rows and un-analyzed
attempts render no badge (no layout shift, no "—").

### Composite: base + behavior modifier (athlete-level)

New pure helper:

```ts
athleteNickname(input: {
  stdevDeg?: number | null;
  attemptCount: number;
  uploadDates: (string | null)[];   // ISO dates, any order; nulls ignored
}): { name: string; emoji: string } | null
```

- Base name/emoji come from `steadinessNickname(stdevDeg)`. If that is `null`
  (no steadiness), `athleteNickname` returns `null` — the composite always needs
  a base.
- A **modifier** word is prepended based on volume + cadence. Cadence is derived
  from `uploadDates`: drop nulls, parse to day numbers, sort, take consecutive
  gaps in **days**. First matching rule wins:

| Condition | Modifier |
|---|---|
| `attemptCount === 1` | **One-Shot** |
| `attemptCount >= 4` and median gap ≤ 1 day | **Relentless** |
| `attemptCount >= 2` and longest gap ≥ 14 days | **The Elusive** |
| otherwise | *(no modifier)* |

Composed display name:
- with modifier: `"{modifier} {baseName}"` (e.g. `Relentless Human Jellyfish`)
- without: just `baseName` (e.g. `The Wobbler`)

Emoji is always the base emoji.

Worked examples:
- `One-Shot Statue 🗿` — perfect hold, first and only try
- `Relentless Human Jellyfish 🪼` — uploads daily, still all wobble
- `The Elusive Steady Eddie 💪` — surfaces once a month, always rock solid
- `The Wobbler 🌊` — middling steadiness, normal cadence

**Cadence helper details** (kept pure and testable):
- Parse each non-null date as a local calendar day; if fewer than 2 valid dates
  remain, there are no gaps → only the `attemptCount === 1` rule can fire (or no
  modifier).
- `median gap` = median of consecutive-day gaps (even count → average of the two
  middle values). `longest gap` = max consecutive-day gap.
- Ordering of `uploadDates` in the input does not matter (sorted internally).

### Rendering placements

| Surface | Component | Nickname shown |
|---|---|---|
| Attempt-history lines | `AttemptHistory.tsx` | `steadinessNickname(row.steadiness)` per attempt (time metric only) |
| "Everyone else" rows | `LeaderboardRow.tsx` | `athleteNickname` (metric === "time" only) |
| Viewer's own row | `YouRow.tsx` | `athleteNickname` (metric === "time" only) |
| Podium chips strip | `ChallengeDetail.tsx` podium chips | `athleteNickname` on top-3 |

- Badges only render for plank/time challenges with analyzed steadiness. Weight
  boards and un-analyzed attempts render nothing.
- Badge visual: small pill `"{emoji} {name}"`, muted styling consistent with the
  existing attempt chip (`rounded-full border border-white/10 bg-white/5`).
- `athleteNickname` inputs on a `ChallengeLeaderboardRow`:
  `{ stdevDeg: row.steadiness, attemptCount: row.attempt_count, uploadDates: row.history.map(h => h.date) }`.

## Backend changes

Only one new field to surface: `body_line_stdev_deg`.

1. **`routes/competition_routes.py`** (leaderboard query, ~line 415): add
   `lr.report->>'body_line_stdev_deg' AS steadiness` and put
   `"steadiness": _to_float(row['steadiness'])` into each attempt dict.
2. **`services/challenge_leaderboard.py`** `_rank_time`: carry the **best
   attempt's** `steadiness` onto the ranked row (parallel to `form_score`).
   Non-qualifying / zero-score rows get `steadiness: None`. `_rank_weight` does
   not set it (weight boards ignore steadiness).
3. **`routes/user_routes.py`** (`/users/<id>/lifts` query, ~line 131): add
   `lr.report->>'body_line_stdev_deg' AS steadiness`.
4. **`services/lift_history.py`** `shape_lift_row`: add null-safe
   `"steadiness": _to_float(get("steadiness"))`.

## Frontend type changes

- `ChallengeLeaderboardRow`: add `steadiness: number | null` (time only; null
  otherwise — mirrors `form_score`).
- `AttemptHistory.tsx` `AttemptRow` interface: add `steadiness: number | null`.

## Testing

- **`lib/__tests__/plankStats.test.ts`**: threshold-pinned cases for
  `steadinessNickname` (each band boundary + null) and `athleteNickname`
  (each modifier rule: one-shot, relentless burst, elusive long-gap, no-modifier
  normal cadence; null-base → null; date parsing with nulls / unsorted input /
  <2 valid dates).
- **Backend `tests/test_lift_history.py`**: `shape_lift_row` includes
  `steadiness` (present and null cases).
- **Backend `tests/test_challenge_leaderboard.py`** (or the existing rank test):
  best-attempt `steadiness` carries onto the time-ranked row; weight rows omit
  it.
- **Component tests**: `LeaderboardRow` / `AttemptHistory` render the badge only
  for time metric with steadiness present, and render nothing otherwise.

## Out of scope (YAGNI)

- No new endpoints.
- No `per_second` on list rows.
- No changes to the video-page `personality()`.
- No flat combinatorial name table (base+modifier chosen instead).
- No multi-account detection (the "accounts" signal was clarified to mean
  attempts-per-athlete).
- No config toggles.
