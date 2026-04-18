# Fairway Migration — Phase A → Phase B Handoff

**Prepared:** 2026-04-18 by prior session.
**Next agent:** resume the migration by writing and executing Phase B.

---

## Where we are

Phase A of the Fairway incremental migration is complete. All 16 planned tasks shipped on a feature branch; 12/12 Phase-A Playwright assertions pass locally.

### Canonical documents

- **Spec (A, B, D in one):** `docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md`
- **Phase A plan (executed):** `docs/superpowers/plans/2026-04-18-fairway-phase-a.md`
- **Phase B plan:** NOT WRITTEN YET — next agent's first deliverable.
- **Phase D plan:** not yet started.
- **Fairway source bundle:** `fairway_spec_bundle/` (SPEC.md + designs/).

### Branch state

- `main` has the spec + Phase A plan (commits `f750aa9`, `eec1e89`). Does NOT have Phase A code.
- `golf/fairway-phase-a` (pushed to `origin`) has Phase A implementation — 14 commits.
  - Open PR: https://github.com/robert23kim/toms-gym/pull/new/golf/fairway-phase-a (must be opened manually — `gh pr create` failed with "Enterprise Managed User / Unauthorized" on this machine's gh auth).
  - After merge: `python3 deploy.py --frontend-only --skip-iam`, then re-run `e2e/golf-fairway-phase-a.spec.ts` against prod.
- Worktree: `/Users/toka/code/toms_gym-fairway-phase-a` (still checked out on the branch). Remove with `git worktree remove` once merged.

### What Phase A delivered

- `frontend/src/styles/fairway.css` — design tokens scoped under `.fw-scope`.
- `frontend/src/components/FairwayScope.tsx` — wrapper applied to all 5 `/golf/*` pages.
- `frontend/src/components/golf/`:
  - `StagedParseProgress.tsx` — 5-stage upload indicator.
  - `HighlightsGrid.tsx` — 4-tile birdies/pars/bogeys/doubles summary.
  - `HoleBarChart.tsx` — 18-column SVG strokes-vs-par chart.
  - `ReviewBanner.tsx` — "N holes need review" amber banner.
- Reskinned pages (Tailwind layout + `fw-*` tokens): `GolfUpload`, `GolfReview`, `GolfRound`, `GolfProfile`, `GolfLeaderboard`.
- Review UX wins: Fairway cell palette (birdie/par/bogey+), amber glow at 0.85 confidence, banner, live score differential footer.
- E2E: `frontend/e2e/golf-fairway-phase-a.spec.ts` (12 tests; deterministic UUIDs + per-test `page.route` stubs).
- Tangential fix: gitignore pattern `lib/` was swallowing `frontend/src/lib/`. Anchored to `/lib/` on the branch; committed the previously-untracked `api.ts`, `utils.ts`, `data.ts`, `constants.ts`, `telemetry.ts` (commit `51fc45f`).

### Known caveats for Phase B

1. **`/golf/upload` is rate-limited 10/hr** (`backend/toms_gym/routes/golf_routes.py:387`). Phase B adds tests that may need to stub rather than seed real rounds.
2. **Two e2e tests in `user-workflows.spec.ts` fail on `main` already** — `navigation links work` and `bowling challenge page loads and shows upload form`. Not a Phase A regression; do not let them block Phase B.
3. **`tsconfig.json` has `noUnusedLocals: false`** — TS won't flag dead imports; don't rely on it for cleanup.
4. **Inline `CREATE TABLE IF NOT EXISTS`** for `GolfRound` / `GolfHoleScore` / `GolfHandicap` lives in `backend/toms_gym/app.py:117-194`. Phase B §B1 calls for removing that block and writing proper migration SQL under `backend/toms_gym/migrations/`.
5. **Greenfield migration** — the user confirmed no production data to preserve. Phase B can drop existing golf tables.

---

## What Phase B needs to do

From the spec (`docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md`, §Phase B):

### B1. Schema (drop + recreate)
Replace flat `GolfRound` / `GolfHoleScore` / `GolfHandicap` with `Course`, `Tee`, `Round`, `HoleScore`, `HandicapSnapshot`. Write proper migration SQL under `backend/toms_gym/migrations/`, remove the inline block in `app.py`.

### B2. Handicap engine rewrite
New `backend/toms_gym/services/handicap.py`:
- Net-double-bogey cap per hole (cap at 10 for users without a handicap).
- Differential `((adjusted − rating − PCC) × 113) / slope`, PCC = 0 for MVP.
- WHS index table (lowest 1 @ 3 rounds with −2.0, …, best 8 of last 20).
- Establishing state (<3 rounds → null + `{status: "establishing", rounds_needed}`).
- 12-month low cap (can't rise >5.0 above 12-month low).
- 9-hole rounds (9-hole rating/slope, count as 0.5 toward "last 20").
- Write a `HandicapSnapshot` per round save/edit/delete.
- Unit tests against WHS reference examples.

### B3. OCR → Course/Tee matching
- `pg_trgm` fuzzy match on course name, optional geo filter, create `status='pending'` on miss.
- Tee match by name; create tee when rating/slope present; prompt user when missing.

### B4. Tee-picker drawer on `GolfReview`
- Up to 4 tee cards; selected tee gets `border: 2px solid var(--fw-info)` (using the existing `fw-selected` class from Phase A).
- Editable rating (step 0.1), slope (step 1), yardage (step 1).
- Difficulty meter anchored at slope 113; labels at 100 / 113 / 130 / 145.
- Live differential preview.
- "Look up official values" → stubbed `GET /golf/courses?q=&near=`.

### B5. API surface
- Existing `/golf/*` paths stay; response shapes now return nested `course` / `tee` objects instead of flat `course_name` / `slope_rating` / `course_rating`.
- New: `GET /golf/courses?q=&near=`, `POST /golf/courses`, `GET /golf/users/:id/handicap/history`.

### B6. Frontend data swap
Re-plumb `GolfReview.tsx`, `GolfRound.tsx`, `GolfProfile.tsx` to the new response shapes. **Phase A's visuals and CSS classes stay.** Minimal JSX diffs.

### B7. Testing
- `backend/tests/test_handicap.py` — unit tests for every rule above.
- Extend `backend/tests/test_golf_parser.py` with course/tee matching integration tests.
- Playwright: existing flow passes; tee-picker drawer opens; differential updates live.

---

## Kick-off prompt for the next agent

> Continue the Fairway incremental migration at Phase B. Start by writing `docs/superpowers/plans/<today>-fairway-phase-b.md` per the spec's §Phase B requirements, using the same bite-sized TDD task structure as Phase A's plan. Once the plan is reviewed and approved, execute it on a new branch `golf/fairway-phase-b` off `main`.
>
> Context:
> - Read this handoff doc: `docs/superpowers/handoffs/2026-04-18-fairway-phase-a-to-b.md`.
> - Read the spec: `docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md` §Phase B.
> - Reference the Phase A plan style: `docs/superpowers/plans/2026-04-18-fairway-phase-a.md`.
> - Phase A ships separately on branch `golf/fairway-phase-a`; assume it will be merged before Phase B deploys. Plan Phase B against `main` post-merge (Course/Tee tables replace the existing GolfRound schema; Phase A's visuals stay intact).
> - User preferences: one long-lived branch per phase; ship when the phase is coherent. Greenfield schema migration is fine — no production golf data to preserve.
> - Use `TeamCreate` for parallel work where tasks touch different files, but serialize implementers that share a file (same file = conflict).
