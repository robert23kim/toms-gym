<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Challenge Attempt History (shipped 2026-07-06)

Expandable per-athlete attempt history on challenge leaderboards. Spec: `docs/superpowers/specs/2026-07-06-challenge-attempt-history-design.md`; plan: `docs/superpowers/plans/2026-07-06-challenge-attempt-history.md`.

- **Backend:** `GET /users/<id>/lifts` gained an optional `competition_id` filter (WHERE clause on page + COUNT; the clause is a fixed literal toggled by presence — no injection surface).
- **`components/challenge/AttemptHistory.tsx`** — lazy panel fetched on expand: date · payoff (time boards: `m:ss` hold; weight boards: kg + grade pill) · 🏆 on the metric-best (only when >1 valued attempt) · links to the attempt's VideoPlayer route.
- **Chips:** `LeaderboardRow` + `YouRow` (entered) accept optional `{attemptCount, expanded, onToggleAttempts}` and render an `N attempts ▾` chip at count > 1. **Podium members** (top 3 — usually the multi-attempt users) get a chips strip *below* the podium instead (podium cards stay pure visuals). `ChallengeDetail` holds a single-open accordion (`expandedAttemptsUserId`).
- Suite at ship: 50 suites / 312 frontend tests; backend gate 138.
