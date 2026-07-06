# Plank Stats v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Render the plank report's dormant `per_second` data as a scrubbable steadiness timeline + score + personality on the VideoPlayer page — per spec `docs/superpowers/specs/2026-07-06-plank-stats-v1-design.md`.

**Architecture:** Frontend-only, two layers: pure stat helpers in `lib/plankStats.ts` (fixture-tested math, no React) and a presentational `PlankSteadiness` component (custom SVG chart, video-seek interaction) wired into VideoPlayer's plank branch. No backend/engine changes; data verified present in prod reports.

**Tech Stack:** React 18 + TypeScript, custom inline SVG (no chart deps; author per the dataviz skill), jest + RTL, vite.

## Global Constraints

- Zero backend/engine changes. Input is the existing `PlankPerSecond[]` type (`lib/types.ts`).
- All helpers are total functions: empty input → null/[] — the component renders nothing and VideoPlayer's existing plank stat list remains the fallback.
- Thresholds exactly as specified: wobble Δ>2.5° (in_plank only, 2s merge), steadiness `clamp(100−stdev×10)`, decay = ≥5 consecutive in_plank seconds with form<0.7, personality priority Jelly→Phoenix→Slow Melter→Statue→Steady Eddie, min 10 in_plank seconds.
- Seek only — never autoplay on chart interaction.
- Validation gate per task: targeted jest + `npx vite build`. Final: full jest + `tsc --noEmit`, deploy `--frontend-only`, verify on the prod 244s plank result.

---

### Task 1: plankStats helpers (TDD)

**Files:**
- Create: `frontend/src/lib/plankStats.ts`
- Test: `frontend/src/lib/__tests__/plankStats.test.ts`

**Interfaces:**
- Produces (all exported; consumed by Task 2):
  - `holdRuns(ps: PlankPerSecond[]): { start: number; end: number; duration: number; longest: boolean }[]`
  - `steadinessScore(stdevDeg?: number | null): { score: number; label: string } | null`
  - `wobbleEvents(ps: PlankPerSecond[]): { t: number; delta: number }[]`
  - `decayPoint(ps: PlankPerSecond[]): number | null`
  - `milestones(ps: PlankPerSecond[]): { label: string; t: number | null; reached: boolean }[]`
  - `personality(ps: PlankPerSecond[], stdevDeg?: number | null): { key: string; emoji: string; name: string; blurb: string } | null`

- [x] **Step 1: Write the failing tests** (fixtures: flat statue curve, linear melter, dip-recover phoenix, alternating jelly, decay window, multi-run holds, milestone crossing at cumulative time, empty, NaN seconds skipped)
- [x] **Step 2: Run to verify fail** — `npx jest src/lib/__tests__/plankStats.test.ts` → module not found
- [x] **Step 3: Implement helpers exactly to spec thresholds**
- [x] **Step 4: Run to verify pass**
- [x] **Step 5: Commit** — `feat(lift): plank steadiness stat helpers`

---

### Task 2: PlankSteadiness component (TDD; read dataviz skill before chart code)

**Files:**
- Create: `frontend/src/components/lifting/PlankSteadiness.tsx`
- Test: `frontend/src/components/lifting/__tests__/PlankSteadiness.test.tsx`

**Interfaces:**
- Consumes: all Task 1 helpers; `LiftingReport` type.
- Produces: `<PlankSteadiness report onSeek currentTime />` — props `{ report: LiftingReport; onSeek: (t: number) => void; currentTime?: number }`.

- [x] **Step 1: Failing test** — fixture report renders score pill ("Steady"/number), personality name, hold-segments strip, milestone ticks; chart click fires `onSeek` with 0 ≤ t ≤ duration; empty per_second renders null.
- [x] **Step 2: Verify fail**
- [x] **Step 3: Invoke the dataviz skill, then implement** — hero row (score pill tiered colors + personality badge), SVG timeline (state bands, form area+line, wobble markers, milestone ticks, decay annotation, playhead at currentTime, pointer → onSeek), hold segments strip.
- [x] **Step 4: Verify pass + `npx vite build`**
- [x] **Step 5: Commit** — `feat(lift): plank steadiness timeline component`

---

### Task 3: VideoPlayer wiring + full gate + deploy + docs

**Files:**
- Modify: `frontend/src/pages/VideoPlayer.tsx` (plank results branch + video ref/timeupdate)
- Modify: `CLAUDE.md`

- [x] **Step 1: Wire in** — locate the plank stats block; render `PlankSteadiness` above it; `onSeek` sets `video.currentTime`; track `currentTime` from the existing video element's `timeupdate`.
- [x] **Step 2: Full gate** — `npx jest && npx vite build && npx tsc --noEmit` all green.
- [x] **Step 3: Deploy + prod verify** — `python3 deploy.py --frontend-only --skip-iam`; open the 244s plank attempt result (`/video/226e7383-be5f-4dd7-8eb3-5041c2de015d` route per app) and confirm chart renders with real data (Playwright screenshot).
- [x] **Step 4: Docs + merge** — CLAUDE.md section, mark plan checkboxes, merge branch to main, push.
