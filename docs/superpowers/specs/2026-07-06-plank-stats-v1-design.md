# Plank Stats v1 — Steadiness Pack + Personality — Design

**Date:** 2026-07-06
**Status:** Approved (feature set picked by Tom: steadiness pack items 1–6 + plank personality)
**Scope:** Frontend only. Zero backend/engine changes — verified against a live production report (attempt `226e7383…`, 244s plank): `report.per_second` (256 entries of `{t, state, body_line_deg, elbow_deg, form_score}`), `body_line_stdev_deg`, `total_in_plank_s`, `longest_run_s` all already present. Works retroactively on existing videos; stale pre-engine reports can be refreshed with the existing re-analyze endpoint.

## Goal

Turn the plank result section of `VideoPlayer.tsx` from a flat stat list into a live, scrubbable steadiness story: a per-second form timeline synced to the video, wobble events, hold segments, milestones, a steadiness score, and a fun personality badge.

## New module: `frontend/src/lib/plankStats.ts` (pure, DB/React-free, fixture-tested)

Input type is the existing `PlankPerSecond[]` from `lib/types.ts`. All helpers tolerate empty input (return null/[]).

- `holdRuns(perSecond)` → `{ start: number; end: number; duration: number; longest: boolean }[]` — contiguous `state === "in_plank"` runs in video time; exactly one `longest` flag (first of ties).
- `steadinessScore(stdevDeg)` → `{ score: number; label: string } | null` — `score = clamp(round(100 − stdev×10), 0, 100)`; labels: ≥85 **Rock Solid**, 70–84 **Steady**, 50–69 **Wobbly**, <50 **Jelly Mode**. Null for NaN/undefined stdev.
- `wobbleEvents(perSecond)` → `{ t: number; delta: number }[]` — seconds where `|body_line_deg[t] − body_line_deg[t−1]| > 2.5` and **both** seconds are `in_plank`; adjacent events (within 2s) merge, keeping the larger delta's timestamp.
- `decayPoint(perSecond)` → `number | null` — the `t` starting the first window of ≥5 consecutive `in_plank` seconds with `form_score < 0.7`; null if none. Surfaced as "Form held Xs" where X = that `t` minus the first `in_plank` second (0 floor).
- `milestones(perSecond)` → `{ label: string; t: number | null; reached: boolean }[]` for 30s / 60s / 120s / 180s of **cumulative hold time**; `t` = video time when the cumulative `in_plank` count crosses the milestone (null when not reached).
- `personality(perSecond, stdevDeg)` → `{ key; emoji; name; blurb } | null` — evaluated on `in_plank` seconds only, first match wins:
  1. **Jelly** 🪼 — `wobbleEvents ≥ 4` or `stdev > 4`: "Chaos, but you held on."
  2. **Phoenix** 🔥 — a dip (form ≥0.15 below the rolling 10s average) followed later by recovery to that pre-dip average: "Wobbled, recovered, finished strong."
  3. **Slow Melter** 🫠 — OLS slope of form_score vs t < −0.002/s: "Started strong, gravity won slowly."
  4. **Statue** 🗿 — `stdev ≤ 1.5` and `wobbleEvents ≤ 1`: "Absolutely motionless. Suspiciously so."
  5. **Steady Eddie** 💪 (fallback): "Consistent, controlled, dependable."
  Null when fewer than 10 `in_plank` seconds (not enough signal).

## New component: `frontend/src/components/lifting/PlankSteadiness.tsx`

Props: `{ report: LiftingReport; onSeek: (t: number) => void }`.

- **Hero row:** steadiness score pill (colored by label tier) + personality badge (emoji + name, blurb as subtitle). Rendered next to the existing hold-time stat.
- **Timeline chart** (custom inline SVG, no new deps; follow the dataviz skill when authoring):
  - x = video time, y = form_score 0–1 as an area+line.
  - Background bands per second colored by state: holding (accent-tinted), settling (amber-tinted), no-pose (transparent/gray).
  - Wobble markers (🫨 or small diamond) at event times; milestone ticks (0:30/1:00/2:00/3:00) on the x-axis, lit when reached; decay-point vertical annotation ("form held 35s").
  - **Pointer interaction:** click/drag maps x → t and calls `onSeek(t)`; a playhead line tracks the video's `currentTime` (prop or callback-ref driven; simplest: parent passes `currentTime` number).
- **Hold segments strip** below the chart: proportional bars per run, longest highlighted with its duration label.
- **Graceful degrade:** if `per_second` is empty/missing → render nothing (parent keeps today's simple stat list, which stays).

## VideoPlayer integration

- Plank branch of the results section renders `<PlankSteadiness report={report} onSeek={...} currentTime={...} />` above the existing stat rows (which remain as the detail list).
- `onSeek` sets `videoRef.current.currentTime = t` (and plays if paused? No — seek only, don't autoplay).
- `currentTime` tracked via the existing video element's `timeupdate` listener (state update throttled to the event's natural ~4Hz cadence).

## Error handling

- All helpers total-function over malformed input (NaN angles → skip that second for wobble/personality math).
- Chart renders with as few as 1 second of data; interaction no-ops when duration is 0.

## Testing

- `lib/__tests__/plankStats.test.ts` — handcrafted per-second fixtures: statue (flat), slow melter (linear decline), phoenix (dip + recovery), jelly (alternating angles), decay vs no-decay, milestone crossing, empty input, single-run vs multi-run holds, NaN tolerance. Every helper's thresholds pinned.
- `components/lifting/__tests__/PlankSteadiness.test.tsx` — renders score pill + personality name from a fixture report; clicking the chart calls `onSeek` with a plausible t; renders nothing when `per_second` is empty.
- Existing `VideoPlayer` behavior unchanged for non-plank lifts; full jest + `vite build` + `tsc --noEmit` gate; deploy `--frontend-only`; verify on the real 244s plank result in prod.

## Non-goals

PB tracking, challenge percentile (future); engine changes; chart library adoption; elbow-angle visualization (data exists — v2 candidate).
