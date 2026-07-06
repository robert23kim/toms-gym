# Challenge Attempt History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Expandable per-athlete attempt history on the challenge leaderboard — per spec `docs/superpowers/specs/2026-07-06-challenge-attempt-history-design.md`.

**Architecture:** Reuse the lift-history endpoint with a new `competition_id` filter; new lazy-fetching `AttemptHistory` component; chip + accordion wiring in `LeaderboardRow`, `YouRow`, and `ChallengeDetail`.

**Tech Stack:** Flask text SQL (one clause), React 18 + TS + jest.

## Global Constraints

- Chip only at `attempt_count > 1`; single-open accordion; fetch on expand only.
- Row links use `/challenges/{competitionId}/participants/{userId}/video/{attempt_id}`.
- 🏆 = max `hold_s` (time metric) / max `weight` (weight metric).
- Gates: backend CI script; frontend targeted jest + `vite build`; final full jest + `tsc --noEmit`; full deploy; prod verify on the plank challenge.

---

### Task 1: backend `competition_id` filter
- [x] Add optional param to `get_user_lifts` (WHERE clause on page + COUNT queries); run `PYTHON=venv/bin/python tools/run_ci_tests.sh`.
- [x] Commit — `feat(challenges): competition filter on lift history endpoint`

### Task 2: AttemptHistory component (TDD)
- [x] Failing tests (time rows `m:ss` + 🏆 max hold; weight rows kg + grade; hrefs; error copy) → red → implement → green + build.
- [x] Commit — `feat(challenges): per-athlete attempt history panel`

### Task 3: chip + accordion wiring (TDD on LeaderboardRow chip)
- [x] Extend `LeaderboardRow.test.tsx` (chip at >1 with handler, absent otherwise, click fires toggle) → implement chip props on `LeaderboardRow` + `YouRow` → wire single-open accordion + `<AttemptHistory>` in `ChallengeDetail` → green.
- [x] Commit — `feat(challenges): expandable leaderboard rows with attempt history`

### Task 4: gate + deploy + docs
- [x] Full jest + build + tsc + backend CI; deploy `--skip-iam`; prod verify (expand wonder725: 4:04 🏆 / 3:35 / 2:31); CLAUDE.md; mark plan; merge; push.
