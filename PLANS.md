# Pending Implementation Plans

Status: **both plans executed and deployed 2026-07-03** (written 2026-07-02, from the strategic review of toms_gym + analysis-engine).

## 1. Analysis Engine Re-architecture — DONE except post-soak Task 11
**File:** [docs/superpowers/plans/2026-07-02-analysis-engine-rearchitecture.md](docs/superpowers/plans/2026-07-02-analysis-engine-rearchitecture.md)

Tasks 1–10 executed. The engine runs lifting analysis in-process, bowling metrics come from summary JSON, `POSE_DELEGATE` gates GPU, and the backend dispatches analysis jobs via the `analysis-jobs` Cloud Tasks queue (`ANALYSIS_DISPATCH_MODE=tasks`, verified in production 2026-07-03; rollback = flip back to `poller`).

**Remaining:** Task 11 (delete the dormant poller loops) after ~1 week of clean tasks-mode runs — i.e. on/after **2026-07-10**, verify the soak per Task 11 Step 1 and execute the deletions.

## 2. Frontend Consolidation — DONE
**File:** [docs/superpowers/plans/2026-07-02-frontend-consolidation.md](docs/superpowers/plans/2026-07-02-frontend-consolidation.md)

All 8 tasks executed and deployed 2026-07-03: ErrorBoundary, lazy routes (main bundle 1141→481 kB), config.ts cleanup, dead axios instance removed, react-query established via `lib/queries.ts` (GolfLeaderboard converted), shared `useMediaUpload` (GolfUpload + BowlingUpload), repo hygiene. Follow-ups noted in the plan: convert GolfProfile/Leaderboard/Challenges to react-query; adopt `useMediaUpload` in UploadVideo once its WebCodecs flow is untangled.
