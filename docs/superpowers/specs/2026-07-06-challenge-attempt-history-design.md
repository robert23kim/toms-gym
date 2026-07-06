# Challenge Leaderboard — Expandable Attempt History — Design

**Date:** 2026-07-06
**Status:** Approved (Tom picked: expandable rows for everyone, over your-row-only or a separate card)
**Problem:** The challenge page shows only each athlete's single best attempt; past attempts in the challenge are invisible (wonder725 has `attempt_count: 3` but only 4:04 shows).

## Goal

Any leaderboard row with more than one attempt expands inline into that athlete's attempt history for this challenge: date · payoff · tap-to-watch, newest first, best attempt marked 🏆. Same public data the leaderboard already exposes; fetched lazily on expand.

## Backend (tiny)

`GET /users/<id>/lifts` gains an optional `competition_id` query param: when present, both the page query and the COUNT add `AND uc.competition_id = :competition_id`. Nothing else changes (shape, pagination, JSONB extraction all reused from the lift-history feature).

## Frontend

### `components/challenge/AttemptHistory.tsx` (new)
Props `{ userId: string; competitionId: string; metric: ChallengeMetric }`.
- On mount fetches `/users/{userId}/lifts?competition_id={competitionId}&limit=50`.
- Rows (compact, indented under the leaderboard row): date (`Jul 6`) · payoff — **time metric:** `hold_s` as `m:ss`; **weight metric:** `{weight}kg` (+ grade pill when present); analysis queued/processing → "analyzing…" · Play affordance. Whole row links to `/challenges/{competitionId}/participants/{userId}/video/{attempt_id}`.
- 🏆 on the best attempt: max `hold_s` (time) / max `weight` (weight); only marked when >1 attempt with a value.
- Loading: single muted "Loading attempts…" line; error: muted "Couldn't load attempts."; a lone attempt still lists (the chip that opens this only shows at count > 1, but data races are tolerated).

### Row chip + expansion
- `LeaderboardRow` gains optional props `{ attemptCount?: number; expanded?: boolean; onToggleAttempts?: () => void }`. When `attemptCount > 1` and the handler is present, render a small chip after the name/date block: `3 attempts ▾` (▴ when expanded). Chip is a button (stops link/navigation propagation).
- `YouRow` (entered variant) gains the same optional props/chip so the viewer's own highlighted row expands identically.
- `ChallengeDetail` owns a single-open accordion state `expandedAttemptsUserId: string | null`; renders `<AttemptHistory …/>` directly below the expanded row. Toggling another row closes the first. State resets when the leaderboard reloads.

## Testing

- `AttemptHistory.test.tsx` (mock config + axios): time-metric rows show `m:ss` + 🏆 on max hold; weight-metric shows kg + grade pill; hrefs correct; error → "Couldn't load attempts."
- `LeaderboardRow.test.tsx` additions: chip renders at `attemptCount > 1` with handler, absent at 1 or without handler; click fires `onToggleAttempts`, not navigation.
- Full gate; deploy full stack; prod verify: expand wonder725's row on the plank challenge (3 attempts: 4:04 🏆 / 3:35 / 2:31).

## Non-goals

Bowling-board attempt history (weight/time lifting boards only for now); pagination inside the expansion (50-cap is plenty per challenge); showing form scores per attempt.
