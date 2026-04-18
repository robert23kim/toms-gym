# Fairway Phase B — Retrospective

**Date:** 2026-04-18
**Branch:** `golf/fairway-phase-b` → merged to `main` at `3a8a778`
**Team:** manager, architect, doer-schema, doer-handicap, doer-frontend, qa, reviewer, docs

## What Shipped

18 commits on `golf/fairway-phase-b`, fast-forwarded to `origin/main`. Deployed to prod via `python3 deploy.py --skip-iam` with migration 008 applied against Cloud SQL (via Cloud SQL Auth Proxy fallback). End-to-end real-OCR smoke green on first try.

**Schema (B1):** `Course` / `Tee` / `Round` / `HoleScore` / `HandicapSnapshot` replace flat `GolfRound` / `GolfHoleScore` / `GolfHandicap`. `pg_trgm` + GIN trigram index. Nullable `hole_handicaps[]` on `Tee`.

**Handicap engine (B2):** WHS 2020+ math in `backend/toms_gym/services/handicap.py`. `net_double_bogey_cap`, `compute_differential`, `compute_handicap_index`, `allocate_strokes`, `apply_twelve_month_cap`. 37 parametric unit tests.

**OCR matching (B3):** `backend/toms_gym/services/courses.py`. `pg_trgm` fuzzy match + geo tie-break. 7 integration tests.

**API (B5):** `golf_routes.py` rewritten end-to-end. Nested `course`/`tee` response shapes. 3 new endpoints: `GET /golf/courses`, `POST /golf/courses`, `GET /golf/users/:id/handicap/history`.

**Frontend (B4 + B6):** `lib/types.ts` re-typed, `lib/api.ts` fetchers, all read-only pages + review re-plumbed. `TeePickerDrawer` + `DifficultyMeter` on `/golf/review`. Phase A CSS preserved.

**Tests (B7):** 121 backend + 107 jest + 16 new golf components + 12 Phase A regression + 7 Phase B Playwright. All green.

**Production smoke:** Real Google Vision OCR on the `golf_scorecard.jpg` fixture produced TOM 56/49/105 and CHRIS 93 — exact match on baseline. Handicap math `((105 − 72) × 113) / 113 = 33.0` verified by hand against PUT response. No halt-triggers fired.

## Went Well

- **Plan correctness review caught two bugs pre-implementation.** WHS_TABLE rows 10-16 had off-by-one adjustments that would have silently produced wrong handicaps. NDB per-hole cap would have defaulted to flat-10 everywhere due to missing stroke allocation. Both caught at plan review, fixed in Revision 1 before any code shipped. Spec-vs-implementation cross-check during planning is worth every minute.
- **QA caught the 0.96 multiplier bug pre-deploy.** Engine + test + fixture all encoded the pre-2020 USGA weighting factor, so tests passed against themselves while the math was ~4% wrong vs actual WHS. Reading engine + tests together (not just running them) caught it. Every handicap would have been silently wrong in prod.
- **"Read shipped backend over spec" discipline by doer-frontend.** Before touching #15, read `_fetch_and_serialize_round` in full and reconciled 7 concrete field deltas against the plan briefing. First `tsc --noEmit` after #15 was clean. When code and plan disagree, code wins.
- **Unprompted self-correction by doer-handicap (`eecaa8b`).** Shipped `7229fc9` before the plan was on disk; when the plan landed, proactively realigned signatures, tightened WHS formula, added missing tests. Bias toward correctness over velocity paid off.
- **`nestedRoundBody()` factory for stub shape migrations (#21).** One factory collapsed 5 inline Phase A stub payloads. Reviewer could verify nested shape in one place. Reusable pattern for any future schema migration's e2e work.
- **Per-task QA baselines.** Recording bowling/lifting e2e baseline (27 green vs prod) BEFORE Phase B touched anything meant QA closed #5 with `git diff main = empty` — cheap proof beat expensive re-run.
- **Cloud SQL Auth Proxy fallback.** When `gcloud sql connect` failed on IPv6 and `apply_schema.py` hit `invalid_grant` on stale ADC, doer-handicap pivoted to the Auth Proxy + one-shot pg8000 script reading the password fresh from Secret Manager.
- **Real-OCR smoke on first try in prod.** End-to-end Vision API + symbol-level parser + multi-player detection + pg_trgm + handicap math, all green with exact baseline numbers.

## Didn't Go Well

- **Plan file was hallucinated in first architect session.** Architect reported "plan written at `<path>`" but file was never persisted. Reviewer + doer-frontend hit file-not-found and wasted ~15 minutes verifying. Re-spawned architect recovered, but implementation had started against message-based briefings instead of a shared canonical doc.
- **Plan file drifted from briefings when finally written.** Re-written plan was 819 lines vs the hallucinated 1807. Drift: `CourseMatch`/`TeeMatch` dataclasses (code) vs `MatchedCourse`/`MatchedTee` TypedDicts (plan), `needs_tee` vs `needs_input`, types in `lib/types.ts` vs `lib/api.ts`, `test_courses_service.py` vs `test_courses.py`. Cosmetic but required reviewer flagging.
- **Doer-schema context-loop.** Agent sent 6+ consecutive stale-state reports. Triggered an escalation + approved-but-unexecuted reassignment cycle; withdrawn after agent recovered.
- **Manager routed live work to a shutdown agent.** Treated doer-schema as alive after a shutdown-then-withdraw dance; briefly routed `git push origin main` to a dead inbox. Team lead caught within minutes; countermanded to doer-handicap. Near-miss on silent deploy stall.
- **QA's #25 false alarm.** Diagnosed conftest regression from one bad `run_tests.sh` run without re-running. Actual cause was transient postgres container issue. Retracted before doer-handicap started hotfix — but the diagnosis still prompted a real fix commit (`b974d6f`) shipped against a cancellation, catching a real latent BEGIN/COMMIT-in-SA-session footgun. Net: code improved, process friction.
- **Scorecard fixture recovery took 4 round-trips.** File was untracked, stashed with plain `git stash` (not `-u`), but lived on `stash@{0}^3` (third-parent commit). Manager + team lead both guessed wrong paths; QA verified each false lead.
- **CLAUDE.md had stale prod URL.** `toms-gym-web-*` documented but live service is `my-frontend-*`. Caught during post-deploy smoke when `curl` 404'd; required an 18th branch commit (`3a8a778`) before merge.

## Change Next Time

- **"Re-run before escalate" rule.** When a test-harness failure has both a plausible product hypothesis AND a plausible infra hypothesis, re-run before opening a blocker task. 30-second second-run would have avoided #25. Applies to manager too: verify with a quick `git log` before concluding an agent is stuck.
- **Plan file must exist on disk before spawning implementers.** Don't point doers at `<path>` until `ls <path>` succeeds. Message-based briefings are not a substitute for a committed spec.
- **Put response-shape JSON literals in the plan.** 5-10 lines of example JSON per endpoint would have prevented every one of doer-frontend's 7 field-delta reconciliations.
- **`git stash -u` should be team default.** The whole 4-message fixture-recovery dance was one `git stash list` away if the original stash had captured untracked files. Update CLAUDE.md's deploy section.
- **Seed prod sample data on greenfield migrations.** Leaderboard empty-state is correct UX but feels broken to first post-greenfield user. Phase D deploy should optionally seed 1-2 sample rounds.
- **Test fixtures used in QA smoke should be committed.** `golf_scorecard.jpg` living only in one working tree caused the recovery cycle. Either commit to `tests/fixtures/` (private GCS if PII), or commit a README with fetch instructions.
- **Verify agent liveness before routing deploy-grade work.** Manager got bitten by routing push-to-origin to a shutdown agent.
- **Document Cloud SQL Auth Proxy fallback path** in `backend/toms_gym/migrations/README.md`.
- **Document `stash@{0}^3` untracked-file recovery** in a team git-tips section.
- **`Expect<Equal<X,Y>>` compile-time type assertions as tests.** New pattern in this phase; document for future schema migrations.

## Phase D Entry-Point

**Branch:** off `main` at `3a8a778`. Spec: `docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md` §Phase D. Handoff doc: `docs/superpowers/handoffs/2026-04-18-fairway-phase-b-to-d.md`.

**Backlog tasks filed during Phase B:**
- **#26** — tee-change persistence in `PUT /round/:id/scores`.
- **#32** — `GolfLeaderboard.tsx` visualize `monthly_delta` via trend pill.
- **#33** — `jest.config.js` add `testPathIgnorePatterns: ['/e2e/']`.

**Phase D scope (D1–D5 per spec):** `/golf` dashboard landing, handicap trend chart, `monthly_delta` pill, empty-state + establishing-state variants, optional tee-change persistence.

**Seeded knowledge from Phase B that accelerates Phase D:** `HandicapSnapshot` history + endpoint ready for trend chart; `TeePickerDrawer` reusable pattern; `nestedRoundBody()` factory pattern; Cloud SQL Auth Proxy known-working fallback; WHS 2020+ engine correct and regression-covered.

## Numbers

- **18 Phase B commits** merged to main in one session.
- **29 tasks** tracked: 28 completed, 1 deferred to Phase D (#26).
- **3 correctness bugs caught pre-deploy:** WHS_TABLE off-by-one, NDB flat-10 silent no-op, 0.96 pre-2020 multiplier.
- **1 latent infrastructure bug caught + fixed:** conftest BEGIN/COMMIT footgun.
- **0 production regressions.** Phase A + B green in prod post-deploy; bowling/lifting unchanged.
- **Zero halt-triggers fired during deploy or smoke.**

## Contributors

Retro input from: manager (compiler), QA, docs, doer-frontend. Doer-handicap + reviewer shutdowns ran before their contributions landed; their work is reflected in "Went Well" via the manager's direct observation.
