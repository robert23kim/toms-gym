# Fairway Incremental Migration — Design

**Status:** Approved 2026-04-18
**Source of inspiration:** `fairway_spec_bundle/SPEC.md`
**Existing surface:** `backend/toms_gym/routes/golf_routes.py`, `frontend/src/pages/Golf*.tsx`, tables `GolfRound` / `GolfHoleScore` / `GolfHandicap`.

## Goal

Move the existing Tom's Gym golf feature toward the Fairway product vision through three long-lived phase branches, merged in order: **A (visual + UX polish) → B (correctness + schema) → D (dashboard)**. Social (C in the Fairway spec) is explicitly deferred.

## Ground rules

- Keep the existing stack: Flask + Cloud Run + Cloud SQL (Postgres) + Google Vision OCR + React/Vite frontend + custom JWT passwordless auth.
- No production data to preserve — greenfield migration is acceptable in Phase B.
- Cadence: one long-lived branch per phase, multiple logical commits within each, merged when the phase is coherent.
- Existing `/golf/*` routes and brand remain; no rename to `/fairway/*`.

## Non-goals

- Tech-stack migration (no Next.js, no Supabase, no Prisma, no Claude vision).
- Social layer (groups, feed, reactions, comments, rematches) — separate future phase.
- Course DB seeding at scale — pending courses are created on demand.
- Push notifications, PWA install, export-as-image.

---

## Phase A — Visual + UX polish

Branch: `golf/fairway-phase-a`. No schema changes, no backend contract changes.

### A1. Design tokens (golf-scoped)

Add `frontend/src/styles/fairway.css` with CSS variables:

- Palette: `--fw-success #1D9E75`, `--fw-warning #EF9F27`, `--fw-danger #D85A30`, `--fw-info #185FA5`.
- User accent palette: 8 fixed hues for friend differentiation (only used for current user in Phase A/B since social is deferred).
- Typography: H1 22px, H2 18px, body 14–16px; weights restricted to 400 and 500.
- Radii: 8px default, 12px for cards.
- Borders: 0.5px `rgba(0,0,0,0.15)`; 2px `--fw-info` for selected/featured only.
- Dark-mode overrides via `prefers-color-scheme: dark`.

Import only from `/golf/*` routes so the reskin can't touch lifting/bowling pages.

### A2. Page reskin order (one commit each)

1. `GolfUpload.tsx` — Fairway capture viewport (corner alignment guides, "Capture" + "Upload from library" CTAs, hint text "Lay flat, fill frame, avoid glare").
2. `GolfReview.tsx` — see A3.
3. `GolfRound.tsx` — preview card layout: green course banner, highlights grid (birdies/pars/bogeys/doubles), hole-by-hole bar chart vs par, standout holes.
4. `GolfProfile.tsx` — stat cards + handicap value + rounds list matching the Fairway profile layout.
5. `GolfLeaderboard.tsx` — row style: avatar, name, handicap, monthly delta.

### A3. Review-page UX wins (no schema change)

- Cell background by score vs par: red (bogey+), white (par), green (birdie−). Derived from existing `par` and `strokes`.
- Amber "confidence glow" ring on cells where `ocr_confidence < 0.85`. Field already exists on `GolfHoleScore`.
- Top banner "N holes need review" when any cell < 0.85.
- Live differential footer: `((totalStrokes − course_rating) × 113 / slope_rating)`, recomputes on every cell edit. Formula uses the existing flat fields on `GolfRound`.
- Staged parse progress on `GolfUpload`: five sequential pulsing tasks ("Detecting layout → Identifying course → Reading par/yardage → Extracting player scores → Flagging low-confidence holes") with fake stepped progression running alongside the real `/golf/upload` latency. UI-only; no backend change.

### A4. Testing

- Playwright smoke that walks `/golf/upload → review → round` against seeded data.
- Visual assertions where they matter: color class present on cells, `needs-review` banner renders when any `ocr_confidence < 0.85`.
- Backend tests unchanged.

### Out of scope in A

Course/Tee tables, net-double-bogey, dashboard, social, rebranding to `/fairway/*`.

---

## Phase B — Correctness + schema

Branch: `golf/fairway-phase-b`. Re-plumbs Phase A's review page onto a proper model; visuals untouched.

### B1. Schema (drop + recreate)

Replace `GolfRound` / `GolfHoleScore` / `GolfHandicap` with:

- **`Course`** — `id`, `name`, `city`, `state`, `country`, `latitude`, `longitude`, `holes` (9 or 18), `status` (`verified` | `pending`).
- **`Tee`** — `id`, `course_id`, `name`, `color_hex`, `rating_18`, `slope_18`, `rating_9_front`, `slope_9_front`, `rating_9_back`, `slope_9_back`, `yardage`, `par`, `hole_pars` (int[]), `hole_yardages` (int[] nullable).
- **`Round`** — `id`, `user_id`, `course_id`, `tee_id`, `played_on` (date, no time), `holes` (9|18), `scores` (int[]), `total_score`, `front_nine`, `back_nine`, `score_differential`, `scorecard_image_url`, `ocr_raw`, `ocr_confidence`, `created_at`.
- **`HoleScore`** — `round_id`, `hole_number`, `par`, `strokes`, `ocr_confidence`, `manually_corrected`. Kept as its own table so per-cell confidence and manual-correction flags remain queryable.
- **`HandicapSnapshot`** — `id`, `user_id`, `handicap_index`, `rounds_used`, `triggered_by_round_id`, `created_at`. One row per recalc (replaces the single-row `GolfHandicap`).

Write a proper migration SQL file under `backend/toms_gym/migrations/`. Remove the inline `CREATE TABLE IF NOT EXISTS` block in `backend/toms_gym/app.py` (around line 117).

### B2. Handicap engine rewrite

New module `backend/toms_gym/services/handicap.py`.

- **Net-double-bogey cap** on per-hole scores before differential. Cap at 10 for users without a handicap yet.
- **Differential:** `((adjusted_total − rating − PCC) × 113) / slope`; PCC = 0 for MVP.
- **Index:** WHS adjustment table.
    | Rounds | Differentials used | Adjustment |
    | --- | --- | --- |
    | 3 | lowest 1 | −2.0 |
    | 4 | lowest 1 | −1.0 |
    | 5 | lowest 1 | 0 |
    | 6 | avg lowest 2 | −1.0 |
    | 7–8 | avg lowest 2 | 0 |
    | 9–11 | avg lowest 3 | 0 |
    | 12–14 | avg lowest 4 | 0 |
    | 15–16 | avg lowest 5 | 0 |
    | 17–18 | avg lowest 6 | 0 |
    | 19 | avg lowest 7 | 0 |
    | 20+ | avg lowest 8 | 0 |
- **Establishing state:** < 3 rounds → `null` index + `{status: "establishing", rounds_needed: 3 − N}`.
- **12-month low cap:** handicap can't rise more than 5.0 above the user's lowest `HandicapSnapshot.handicap_index` in the past 12 months.
- **9-hole rounds:** use 9-hole rating/slope; count as 0.5 toward "last 20".
- Save a `HandicapSnapshot` on every round save/edit/delete.

Unit tests against WHS reference examples per Fairway spec §8.1.

### B3. OCR → Course / Tee matching

In the `/golf/upload` handler after parsing:

1. Fuzzy-match `detected.course_name` against `Course` using `pg_trgm` similarity, optionally filtered by user lat/lng. No match → create `Course` with `status='pending'`.
2. Fuzzy-match tee name against that course's `Tee` rows. No match and rating/slope present → create `Tee`. No match and no rating/slope → mark round `needs_tee` and surface a tee-entry form on review.
3. Response includes `course_id`, `tee_id`, plus existing `detected_players` payload.

### B4. Tee-picker drawer on review page

"Change" link on the course header opens a modal:

- Up to 4 tee cards (from `Tee` rows on the course). Rating/slope beneath each. Selected tee → `border: 2px solid var(--fw-info)`.
- Editable rating (step 0.1), slope (step 1), yardage (step 1).
- Difficulty meter anchored at slope 113. Labels at 100 / 113 / 130 / 145: "Forgiving / Average / Above average / Brutal".
- Live differential preview card showing the formula and current value.
- "Look up official values" button → `GET /golf/courses?q=<name>&near=<lat,lng>`. Stub the endpoint to return pending courses only for now.

### B5. API surface

- Existing `/golf/*` paths stay. Response shapes now include nested `course` and `tee` objects in place of the flat `course_name` / `slope_rating` / `course_rating`.
- `GET /golf/courses?q=&near=` — fuzzy search.
- `POST /golf/courses` — manual unknown-course submission.
- `GET /golf/users/:id/handicap/history` — `[{handicap_index, created_at}, ...]` for the Phase D trend chart.

### B6. Frontend data swap

`GolfReview.tsx`, `GolfRound.tsx`, `GolfProfile.tsx` re-plumb to the new response shapes. Visual/styling code from Phase A unchanged. Minimal JSX diffs.

### B7. Testing

- `backend/tests/test_handicap.py` — unit tests for differential, net-double-bogey, index with every adjustment-table row, 12-month cap, 9-hole handling.
- Extend `tests/test_golf_parser.py` with course/tee matching integration tests against seeded `Course` / `Tee` rows.
- Playwright: existing flow passes on new shapes; tee-picker drawer opens; differential updates live.

### Out of scope in B

Dashboard, social, rematch, export.

---

## Phase D — Dashboard

Branch: `golf/fairway-phase-d`. Fairway landing screen, solo-user variant.

### D1. Route change

`/golf` becomes the dashboard landing. Other `/golf/*` routes unchanged.

### D2. `GolfDashboard.tsx` (new)

- **Header:** wordmark + "+ Log round" + "Invite friend" CTAs. Invite is a placeholder (no-op) until the future social phase.
- **Four stat cards:**
    1. Handicap index + monthly trend arrow (delta vs ≥30-day-old `HandicapSnapshot`). < 3 rounds → "Establishing (N of 3)".
    2. Rounds this season (calendar year).
    3. Best round (lowest `score_differential`).
    4. Rank — hidden when solo.
- **Leaderboard card:** hidden for solo users; empty-state "Invite friends" CTA when leaderboard would otherwise be empty.
- **Handicap trend chart:** single line (current user only for now), 6 / 12 / 24-month toggle, y-axis inverted (lower handicap = higher). Data from `GET /golf/users/:id/handicap/history`.
- **Recent rounds table:** user's own rounds, chronological desc, columns: course, date, score, differential. Tap → `/golf/round/:id`.

### D3. Empty states

- 0 rounds → stat cards show "—"; primary CTA "Log your first round".
- 1–2 rounds → handicap card shows "Establishing (N of 3)".
- Fewer than 3 rounds → trend chart replaced by "Need 3 rounds to chart".

### D4. Navigation

Add a top-nav entry so `/golf` is reachable from anywhere in the app, not only from a post-upload success screen.

### D5. Testing

Playwright smoke:

- Brand-new user → sees empty-state CTA, no errors.
- User with 3 rounds → sees handicap + chart + table.
- User with 1 round → sees "Establishing" copy.

### Out of scope in D

Multi-user trend chart, populated leaderboard, share-card export, push notifications.

---

## Shared conventions

- **Branching:** one long-lived branch per phase; rebase on `main` before merging.
- **Commits:** logical chunks within a branch, each green on CI.
- **Feature flags:** not needed; phases land as whole-branch merges.
- **Planning:** each phase gets its own `writing-plans` output after this spec lands.
- **Rollback:** Phase B drops tables — since greenfield, rollback is `DROP TABLE` + redeploy prior image.

## Success criteria

- **Phase A merged:** all five `/golf/*` pages render in the Fairway visual idiom; review page shows color-coded cells, amber confidence glow, live differential, staged parse progress. Playwright smoke green.
- **Phase B merged:** WHS handicap math matches reference examples bit-for-bit in unit tests; new Course/Tee model in place; upload → review → save creates both a `Round` and a `HandicapSnapshot`; tee-picker drawer functional.
- **Phase D merged:** `/golf` is the landing page; stat cards + trend chart + recent rounds render; empty and Establishing states look right; navigation reaches dashboard from anywhere.
