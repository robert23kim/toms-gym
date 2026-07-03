# Pending Implementation Plans

Status: **not started** (written 2026-07-02, from the strategic review of toms_gym + analysis-engine).

To implement later, open a Claude Code session in this repo and say:
> execute the plan in docs/superpowers/plans/<file> (use superpowers:executing-plans or subagent-driven-development)

## 1. Analysis Engine Re-architecture
**File:** [docs/superpowers/plans/2026-07-02-analysis-engine-rearchitecture.md](docs/superpowers/plans/2026-07-02-analysis-engine-rearchitecture.md)

Removes subprocess-per-request + stdout-regex from `bowling-service` (runs lifting analysis in-process, structured bowling summary JSON, `POSE_DELEGATE` GPU flag) and replaces the backend's daemon-thread pollers with Cloud Tasks push dispatch to new `/jobs/<kind>/<id>` handlers. DB status contract and frontend polling unchanged; cutover gated by `ANALYSIS_DISPATCH_MODE=tasks` with instant rollback. 11 tasks across this repo's `backend/` and `~/code/bowling-app/analysis-engine`.

## 2. Frontend Consolidation
**File:** [docs/superpowers/plans/2026-07-02-frontend-consolidation.md](docs/superpowers/plans/2026-07-02-frontend-consolidation.md)

Top-level ErrorBoundary, lazy-loaded routes, config.ts cleanup (kills UA sniffing + prod console logs), deletes the dead `my-app-...` axios instance, establishes react-query via `lib/queries.ts` (GolfLeaderboard converted), shared `useMediaUpload` hook (GolfUpload + BowlingUpload), repo hygiene (screenshots, tracked mp4, gitignore `frontend/android/`). 8 tasks, all in `frontend/` plus repo root.

## Prerequisites (both plans)
- Commit or stash the dirty working trees first — both this repo and `analysis-engine` have uncommitted changes on `plank/poller-timeouts`, including an in-flight `src/bowling/` relocation in the engine repo that the plans deliberately do not touch.
- The two plans touch disjoint code and can run in parallel (separate worktrees).
