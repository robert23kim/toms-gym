# Home Page Redesign + "Quiet Gym" Cohesion Pass — Design

**Date:** 2026-07-06
**Status:** Approved (mockup reviewed by Tom: https://claude.ai/code/artifact/4fb41bea-f84c-490f-aecc-6fc12df0983e; static copy committed at `docs/superpowers/specs/assets/2026-07-06-home-redesign-mockup.html`)
**Scope:** Frontend only. No backend changes, no new endpoints.

## Goal

Reimage the home page as a minimal, centered experience — Top Lifts removed, one-glance path into the analysis flows and open challenges — and extend the same visual language ("quiet gym": dark ground, ambient warmth, slim cards, icon chips) across the app's navigational pages so the whole app feels cohesive.

## Visual language

Derived from the approved mockup; all values come from the existing token set in `src/index.css` (no new tokens):

- **Centered column** — `max-w-2xl mx-auto text-center` for landing/nav pages.
- **Card** — `bg` slightly lifted from ground, 1px border, `rounded-xl`/`rounded-2xl`. Matches existing `glass` usage; prefer semantic tokens (`bg-card`/`border-border` equivalents already in use).
- **Icon chip** — 44px rounded square, `accent/12%` background, accent-colored lucide icon.
- **Pill** — small rounded-full chip, `accent/12%` bg + accent text (category labels).
- **Ambient background** — two layers behind all content:
  - *Glows:* three fixed blurred radial blobs (accent blue ~16%, green ~10%, warm orange ~8% opacity) drifting on 26–38s alternating keyframes.
  - *Doodles:* a repeating 320px inline-SVG tile of line-art from the app's world (dumbbell, bowling ball, golf flag + green, stopwatch, swoosh), white stroke at **5% layer opacity**.
  - Both: `position: fixed`, negative z-index, `pointer-events: none`, `aria-hidden`, disabled/static under `prefers-reduced-motion`.

## New shared components

### `src/components/AmbientBackground.tsx`
Renders the glows + doodle layers. No props. Mounted once inside `Layout` so every page using `Layout` inherits it. Golf `fw-*` pages keep their own surfaces; the ambient layer only replaces the flat black behind them. CSS lives in `src/index.css` (keyframes + reduced-motion guards); the doodle tile is an inline `url("data:image/svg+xml,...")` background.

### `src/components/IconTile.tsx`
Props: `{ to: string; icon: React.ReactNode; title: string; description: string }`. Whole tile is a `Link`. Centered column layout: icon chip, title (16px semibold), one-line muted description. Hover: lift 2px + border brighten. Used by Index (3 verticals) and UploadChooser.

### `src/components/RowCard.tsx`
Props: `{ to: string; icon?: React.ReactNode; title: string; pill?: string; trailing?: string }` (`trailing` defaults to `"Open"`). Slim horizontal row: accent icon, left-aligned name (flex-1), optional category pill, muted "Open →" that brightens on hover. Used by Index (open challenges), HubPage (secondary links), Challenges (ongoing strip).

### `src/components/DemoLoop.tsx`
Home-only animated SVG panel, 12s loop, three crossfading scenes (4s each) + three progress dots:

1. **Plank (0–4s):** line-art figure holding a plank with a subtle 3s bob; monospace hold timer swapping 0:15 → 0:32 → 0:47; green "Hips level ✓" pill pops mid-hold.
2. **Bowl (4–8s):** perspective lane + 5 pins; ball (SMIL `animateMotion`, keyTimes-gated to the scene window) hooks along a cubic path into the pocket while a dashed accent trace draws behind it (`stroke-dashoffset` keyframes); "Board 17 · Pocket ✓" pill.
3. **Golf (8–12s):** mini 9-hole scorecard grid; accent scan line sweeps across; "HCP 21.0" pill pops.

All animations are expressed as percentages of the shared 12s cycle so scenes stay in sync. `prefers-reduced-motion`: all animation off, static plank scene shown with final timer + pill visible. Implementation is exactly the animation CSS/SVG from the committed mockup asset, translated to JSX.

## Page changes

### `Index.tsx` — full rebuild
Centered column, top to bottom:
1. **Hero** — h1 "AI analysis of your lift, bowl, or round — in minutes." + one muted line ("Upload a video or snap a photo and get annotated feedback. No signup — just your email.").
2. **DemoLoop.**
3. **Three IconTiles** — Lift → `/lift/upload` ("Per-rep grades on squat, bench, deadlift & curls."), Bowl → `/bowling/upload` ("Ball trajectory, entry board & pocket impact."), Golf → `/golf/snap` ("Snap a scorecard, get your handicap."). Icons: Dumbbell / Target / Flag.
4. **Open challenges strip** — label "Open challenges" between hairlines; fetches `getCompetitions()`, filters `status === "ongoing"`, renders a RowCard per challenge → `/challenges/:id` with first category as pill. **Empty state: the entire section (label included) renders nothing.** "All challenges →" muted link below when the strip is shown; when hidden, a standalone "All challenges →" link still appears so `/challenges` stays reachable from home.

**Removed from Index:** `TopLifts` sidebar (component file kept — still referenced nowhere else after this change; delete is a separate cleanup), photo feature cards + assets imports, "How It Works" section, featured-challenges cards + status filter buttons, `getFeaturedChallenges` usage.

### `Layout.tsx` — footer + background
- Mount `<AmbientBackground />` before `<main>`.
- Footer becomes the mockup's centered single row: **Report a bug · Request a feature · Terms · Privacy · v{APP_VERSION}** — bug/feature both link to `/feedback` (bug icon on "Report a bug"). Copyright line dropped. Hairline top border kept.

### `HubPage.tsx` — restyle (affects Lift/Bowl/Golf hubs)
- Center the header (icon over title over subtitle) to match home.
- Primary CTA unchanged in function; keep accent block styling.
- Secondary links render as `RowCard`s (icon, label, "Open →") in a single column instead of the 2-col glass grid. RowCard gets `title={label}` and no pill; `HubLink.description` is not rendered on hubs (descriptions are sentences, not chips — dropping them keeps the rows minimal). LiftHub's dynamic plank quick link keeps working (it's just another secondary entry).

### `UploadChooser.tsx`
Replace the three stacked glass rows with a centered 3-up `IconTile` grid (same tiles as home, same copy), header centered.

### `Challenges.tsx`
- Header centered ("Challenges" + one muted line); "Create challenge" button kept, moved under the header.
- New "Open now" strip at top: ongoing challenges as RowCards (same component as home).
- Existing detailed challenge cards remain below (they carry dates/participants); status filter pills restyled to match the pill language but keep function.

### `Leaderboard.tsx` — light touch
Centered header; filter buttons restyled to the pill language (accent-soft active state). Table/logic untouched.

### Untouched
Golf `fw-*` page internals (GolfUpload/Review/Round/Leaderboard/Profile), VideoPlayer, BowlingResult, AnnotationWorkspace, Profile tabs, SignIn/FindProfile, Terms/Privacy/Feedback pages. They inherit the ambient background + new footer via `Layout` and nothing else.

## Data

- Open-challenges strip and Challenges "Open now" both use existing `getCompetitions()` (transformed shape: `{ id, title, status: 'upcoming'|'ongoing'|'completed', categories: string[] }`). Filter `status === "ongoing"`. Fetch failure → treat as empty (strip hidden); never block the page.

## Error handling

- All new fetches are non-fatal: `.catch(() => [])`-style, no error UI on home (minimal page stays minimal).
- DemoLoop and AmbientBackground are pure presentational — no data, no failure modes beyond CSS.

## Testing

- `Index.test.tsx` (new): renders 3 tiles with correct hrefs (`/lift/upload`, `/bowling/upload`, `/golf/snap`); ongoing challenges render RowCards linking `/challenges/:id`; strip absent when none ongoing; `getFeaturedChallenges`/TopLifts no longer referenced.
- `RowCard.test.tsx` + `IconTile.test.tsx` (new): href, title, pill/description render.
- `DemoLoop.test.tsx` (new): renders three scenes + dots (structure only; animation not asserted).
- `Layout` footer: assert "Report a bug" link → `/feedback` (extend or add `Layout.test.tsx`; Layout tests must mock `../config`).
- Existing suites must stay green (LiftHub test asserts the plank quick link — HubPage restyle must keep label text).
- Gate per task: targeted jest + `vite build`; final: full jest + `tsc --noEmit`, deploy `--frontend-only`, prod URL check.

## Non-goals

- No golf fw-* redesign, no navbar redesign, no light theme, no real video clips in DemoLoop (CSS/SVG only for now), no TopLifts file deletion (follow-up cleanup), no backend work.
