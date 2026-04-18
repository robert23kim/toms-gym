# Fairway Migration — Phase B → Phase D Handoff

**Prepared:** 2026-04-18 by Phase B team.
**Next agent:** write and execute Phase D (dashboard landing page + handicap trend chart).

---

## Where we are

Phase B of the Fairway incremental migration is complete. The flat `GolfRound` / `GolfHoleScore` / `GolfHandicap` tables are gone; the normalized `Course` / `Tee` / `Round` / `HoleScore` / `HandicapSnapshot` model is authoritative. WHS 2020+ handicap engine, `pg_trgm` course matcher, tee-picker drawer, and three new endpoints all shipped together on one branch.

### Canonical documents

- **Spec (A, B, D in one):** `docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md`
- **Phase A plan (shipped):** `docs/superpowers/plans/2026-04-18-fairway-phase-a.md`
- **Phase B plan (shipped):** `docs/superpowers/plans/2026-04-18-fairway-phase-b.md` (818 lines — condensed; earlier 1807-line version was pruned before execution)
- **Phase D plan:** NOT WRITTEN YET — next agent's first deliverable.
- **Phase A → B handoff (reference template):** `docs/superpowers/handoffs/2026-04-18-fairway-phase-a-to-b.md`
- **Fairway source bundle:** `fairway_spec_bundle/` (SPEC.md + designs/).

### Branch state

- `main` has Phase A merged plus the Phase B plan document. Does NOT yet have Phase B code.
- `golf/fairway-phase-b` (pushed to `origin`) has Phase B implementation — **14 commits** (tip `77975de`).
  - Opens against `main`. `gh pr create` may still fail with "Enterprise Managed User / Unauthorized" on this machine's gh auth; fall back to pushing and sharing the branch URL manually as Phase A did.
  - After merge: apply migration 008 against Cloud SQL, then `python3 deploy.py --skip-iam`. Re-run `golf-fairway-phase-a.spec.ts` (12 assertions) + `golf-fairway-phase-b.spec.ts` (6 assertions) against prod as the regression gate.

### What Phase B delivered

**Schema (migration `008_fairway_schema.sql`).** Drops old flat golf tables, installs `pg_trgm`, creates `Course` / `Tee` / `Round` / `HoleScore` / `HandicapSnapshot`. GIN trigram index on `Course.name`; `(latitude, longitude)` index; slope CHECKs in WHS legal range 55–155; `holes IN (9, 18)` CHECKs on both `Course` and `Round`. Inline `CREATE TABLE` block at `app.py:117–194` removed (~84 lines).

**Handicap engine (`backend/toms_gym/services/handicap.py`).** Pure, DB-free. Exposes `net_double_bogey_cap`, `compute_differential`, `compute_handicap_index`, `allocate_strokes`, `apply_twelve_month_cap`. WHS 2020+ adjustment table (no `× 0.96`); establishing state below 3 rounds; 12-month low cap at +5.0; 9-hole rounds weighted 0.5; index capped at 54.0. Reference fixtures at `backend/tests/fixtures/whs_reference_cases.json`; unit tests at `backend/tests/test_handicap.py`.

**Courses service (`backend/toms_gym/services/courses.py`).** `match_or_create_course` (pg_trgm similarity ≥ 0.55, optional geo-bias tie-break, creates `status='pending'` on miss), `match_or_create_tee` (matches by name per course; creates when rating/slope present; returns `needs_input=True` otherwise), `search_courses` (ordered by similarity, then distance). Tests at `backend/tests/test_courses_service.py`.

**Routes (`backend/toms_gym/routes/golf_routes.py`).** Substantial rewrite: all existing `/golf/*` paths return nested `course` / `tee` objects; every round save / edit / delete writes a `HandicapSnapshot`; leaderboard sources from latest snapshot per user. Three new endpoints:
- `GET /golf/courses?q=&near=lat,lng` — fuzzy search.
- `POST /golf/courses` — authenticated = `verified`; anonymous = `pending`.
- `GET /golf/users/:id/handicap/history?range=6m|12m|24m|all` — ordered series for the trend chart.

**Frontend.** Types updated in `frontend/src/lib/types.ts` + `lib/api.ts`; read-only pages (`GolfRound`, `GolfProfile`, `GolfLeaderboard`) swapped onto nested shapes. `TeePickerDrawer.tsx` (up to 4 cards, editable rating/slope/yardage, `fw-selected` 2px `fw-info` border, live differential preview) and `DifficultyMeter.tsx` (horizontal meter 55–155, anchored at 113, labels 100 / 113 / 130 / 145) landed with unit tests. `GolfReview.tsx` wires a "Change" link → drawer.

**Tests.** `backend/tests/test_handicap.py` (+190 lines), `test_courses_service.py` (+102 lines), `test_golf_parser.py` (+181 lines with course/tee matching integration cases). Frontend: component tests for TeePickerDrawer + DifficultyMeter, new `golf-fairway-phase-b.spec.ts` (6 assertions) + updated `golf-fairway-phase-a.spec.ts` stubs to the nested shape.

**Documentation.** `backend/toms_gym/migrations/README.md` documents 008 + rollback. `CLAUDE.md` "Golf Feature" section rewritten for the new data model, API surface, handicap engine, and TeePickerDrawer, with a field rename map.

**Enabled for Phase D (not consumed yet).**
- `HandicapSnapshot` append-only history is the data source for the handicap trend chart.
- `GET /golf/users/:id/handicap/history` ships with four range buckets (`6m` / `12m` / `24m` / `all`), ready to wire into a sparkline or full chart.
- `TeePickerDrawer` is a general course/tee picker — any Phase D surface that needs one should reuse it instead of rolling its own.
- Leaderboard rows already carry a `monthly_delta` field (30-day handicap change) — backend computed, UI pill not yet rendered.

### Known caveats for Phase D

1. **Tee-change persistence is incomplete.** `TeePickerDrawer` on `GolfReview` lets the user pick a tee and updates local state, but `PUT /round/<id>/scores` does not yet accept a `tee_id` override — confirming scores does not persist a tee change. Tracked as team task **#26**. Phase D should either fold this into the dashboard work (if a dashboard surface needs tee editing) or call it out as its own task.
2. **Leaderboard `monthly_delta` has no UI.** Backend returns the field; `GolfLeaderboard.tsx` does not render a delta pill. Design it with Phase A's Fairway token palette (green/red/neutral) when it lands.
3. **Flat NDB-10 cap is the common case.** The OCR parser rarely extracts per-hole handicap ranks, so `Tee.hole_handicaps` is usually null and `allocate_strokes` returns None — the engine falls back to capping at a flat 10 per hole. This is correct per spec for users without an established handicap but understates the cap for established players. Improving OCR to pick up the HANDICAP row is a Phase D-or-later follow-up.
4. **Rate limit on `/golf/upload` is still 10/hr** (`golf_routes.py:464`). Phase B e2e uses `page.route` stubs; Phase D should do the same.
5. **Pre-existing `user-workflows.spec.ts` reds** — `navigation links work` and `bowling challenge page loads and shows upload form` fail on `main` already (Phase A→B handoff caveat #2 — unchanged). Do not let them block Phase D.
6. **`tsconfig.json` has `noUnusedLocals: false`** (Phase A→B handoff caveat #3 — unchanged). Don't rely on TS to flag dead imports from the Phase B data swap.
7. **Greenfield migration policy still in effect.** The user confirmed no production data to preserve; Phase B dropped old tables without a backup. Phase D does not change the schema — but if it needs to, it can add another drop-and-recreate migration.
8. **Phase A visuals are locked.** `fairway.css` tokens, `FairwayScope`, `StagedParseProgress`, `HighlightsGrid`, `HoleBarChart`, `ReviewBanner` — do not re-style. Phase D's dashboard is built from these same tokens.

---

## What Phase D needs to do

From the spec (`docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md`, §Phase D):

### D1. Dashboard landing page
New `/golf` (or `/golf/dashboard`) route that becomes the default golf entry point. Surfaces:
- Current handicap index card (+ establishing-state messaging when applicable).
- Handicap trend chart over the selected range (6m / 12m / 24m / all) sourced from `GET /golf/users/:id/handicap/history`.
- Recent rounds list (last 5) linking to `/golf/round/:id`.
- Quick actions: Upload scorecard, View leaderboard, View full profile.

### D2. Handicap trend chart
SVG or canvas line chart under `frontend/src/components/golf/HandicapTrendChart.tsx`:
- X-axis: `created_at` from `HandicapSnapshot` points.
- Y-axis: `handicap_index` (null points → establishing — render a flat marker or skip).
- Range buttons (6m / 12m / 24m / all) map 1:1 to the `range` query param.
- Use Phase A Fairway tokens (`--fw-info`, `--fw-surface`, `--fw-border`).

### D3. Leaderboard `monthly_delta` pill
Small change: `GolfLeaderboard.tsx` consumes the existing `monthly_delta` field and renders a colored pill (green if < 0, red if > 0, neutral if null). Already tracked as a Phase D follow-up, not its own plan task.

### D4. Tee-change persistence (optional, see caveat #1)
If Phase D touches `GolfReview.tsx` for any reason, fold in: extend `PUT /round/:id/scores` to accept `tee_id` + optional tee overrides (rating/slope/yardage); update the drawer's confirm handler to send them. Team task **#26** tracks this.

### D5. Testing
- Playwright `frontend/e2e/golf-fairway-phase-d.spec.ts` — dashboard renders, range buttons switch the chart, handicap card shows establishing/active states, recent rounds link through.
- Unit tests for `HandicapTrendChart` (render + range-switching).
- Re-run Phase A (12) + Phase B (6) specs as regression gates.

---

## Post-merge polish (shipped same-day as Phase B)

After the Phase B merge commit `3a8a778` landed on `main`, a short round of polish was shipped as a series of fast-follows. All are live in prod as of `cb82a6c`:

- **`8091cda` — Restored Challenges and Golf nav tabs.** The Phase A → B reskin had dropped two nav links; href-prefix `isActive` matching brought back alongside them (replaces the old substring-in-label approach).
- **`711b568` — Fairway scope dark by default.** The wider app uses a single dark theme via Tailwind `:root` HSL tokens (no `html.dark` class is ever set). The Phase A `fw-scope` assumed a next-themes-style toggle, so its dark-mode block never activated and golf pages rendered as a white card on a black page. The dark palette is now the scope default and the wrapper background is `transparent` so the site chrome bleeds through.
- **`d946448` — Dropped the 3-round minimum + surfaced Golf Profile button.** `WHS_TABLE` now covers 1- and 2-round states with lowest-1 differential and no adjustment; engine threshold lowered from `< 3` to `< 1`. A `POST /golf/handicap/<user_id>/recompute` internal endpoint was added to backfill snapshots for users whose rounds predate the rule change. The `My Golf Profile` link on the leaderboard was promoted from a low-contrast text link to a bordered button and is now shown in both empty- and populated-state layouts.
- **`f6c0a06` + `86df471` — Auto-create guest golfers per detected scorecard player.** See the "Multi-player auto-save" section in `CLAUDE.md`. The first attempt failed silently because `auth_method` enum had no `'guest'` value; the nullable column is now left NULL.
- **`cb82a6c` — Leaderboard stale-snapshot fix + named avatars.** The leaderboard query filter now runs *outside* `DISTINCT ON` so a user whose latest snapshot is null drops off the board instead of reviving their stale 33.0 index. A new `getGolfAvatar(name, id)` helper (DiceBear avataaars) ships hand-tuned presets for known recurring golfer names (`tom`, `chris`) and a name-seeded fallback for everyone else; leaderboard and profile pages migrated off `getGhibliAvatar` for golf contexts only.

**Manual smoke against prod:** two real-scorecard uploads (Pebble Beach and Waverly Oaks) ran cleanly end-to-end. OCR returned TOM 56/49/105 + CHRIS 93; guest rounds were auto-created for both detected names; leaderboard ordered Chris (21.0) ahead of Tom (33.0); avatars rendered with distinct skin/hair via the new preset map. The uploader's test user was later deleted (4 rounds cleared via `DELETE /golf/round/<id>?user_id=...`) and drops off the board as expected.

None of this changes Phase D scope — the entry points called out below are still the right starting list.

## Kick-off prompt for the next agent

> Continue the Fairway incremental migration at Phase D. Start by writing `docs/superpowers/plans/<today>-fairway-phase-d.md` per the spec's §Phase D requirements, using the same bite-sized TDD task structure as Phase B's plan. Once the plan is reviewed and approved, execute it on a new branch `golf/fairway-phase-d` off `main`.
>
> Context:
> - Read this handoff doc: `docs/superpowers/handoffs/2026-04-18-fairway-phase-b-to-d.md`.
> - Read the spec: `docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md` §Phase D.
> - Reference the Phase B plan style: `docs/superpowers/plans/2026-04-18-fairway-phase-b.md`.
> - Phase B ships separately on branch `golf/fairway-phase-b`; assume it will be merged before Phase D deploys. Plan Phase D against `main` post-merge (the `Course` / `Tee` / `Round` / `HoleScore` / `HandicapSnapshot` schema is authoritative; Phase A visuals + Phase B endpoints are load-bearing).
> - Phase D is primarily a frontend phase — the `GET /golf/users/:id/handicap/history` and leaderboard `monthly_delta` fields already exist. The only backend work is optional tee-change persistence (team task #26).
> - User preferences: one long-lived branch per phase; ship when the phase is coherent. Use `TeamCreate` with `isolation: "worktree"` for parallel work where tasks touch different files, but serialize implementers that share a file (same file = conflict).
