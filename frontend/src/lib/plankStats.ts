import { PlankPerSecond } from "./types";

/**
 * Pure stat helpers over the plank report's per-second series
 * ({t, state, body_line_deg, elbow_deg, form_score}). All functions are
 * total: empty/malformed input returns null/[] so the UI can degrade to
 * the plain stat list. Thresholds per the Plank Stats v1 spec.
 */

export interface HoldRun {
  start: number;
  end: number;
  duration: number;
  longest: boolean;
}

export interface WobbleEvent {
  t: number;
  delta: number;
}

export interface SteadinessScore {
  score: number;
  label: string;
}

export interface Milestone {
  label: string;
  t: number | null;
  reached: boolean;
}

export interface Personality {
  key: string;
  emoji: string;
  name: string;
  blurb: string;
}

const WOBBLE_DELTA_DEG = 2.5;
const WOBBLE_MERGE_GAP_S = 2;
const DECAY_FORM_THRESHOLD = 0.7;
const DECAY_WINDOW_S = 5;
const MILESTONE_SECONDS: [string, number][] = [
  ["0:30", 30],
  ["1:00", 60],
  ["2:00", 120],
  ["3:00", 180],
];
const PERSONALITY_MIN_PLANK_S = 10;

const inPlank = (s: PlankPerSecond) => s.state === "in_plank";

/** Contiguous in_plank runs in video time; exactly one `longest` (first of ties). */
export function holdRuns(ps: PlankPerSecond[]): HoldRun[] {
  const runs: HoldRun[] = [];
  let start: number | null = null;
  let prev: number | null = null;

  for (const s of ps) {
    if (inPlank(s)) {
      if (start === null) start = s.t;
      prev = s.t;
    } else if (start !== null && prev !== null) {
      runs.push({ start, end: prev, duration: prev - start + 1, longest: false });
      start = null;
      prev = null;
    }
  }
  if (start !== null && prev !== null) {
    runs.push({ start, end: prev, duration: prev - start + 1, longest: false });
  }

  if (runs.length > 0) {
    let best = 0;
    runs.forEach((r, i) => {
      if (r.duration > runs[best].duration) best = i;
    });
    runs[best].longest = true;
  }
  return runs;
}

/** clamp(100 - stdev*10) with tier labels. Null for missing/NaN stdev. */
export function steadinessScore(
  stdevDeg?: number | null
): SteadinessScore | null {
  if (stdevDeg == null || Number.isNaN(stdevDeg)) return null;
  const score = Math.min(100, Math.max(0, Math.round(100 - stdevDeg * 10)));
  const label =
    score >= 85 ? "Rock Solid" : score >= 70 ? "Steady" : score >= 50 ? "Wobbly" : "Jelly Mode";
  return { score, label };
}

/**
 * Seconds where |Δ body_line_deg| > 2.5° between consecutive in_plank
 * seconds. Events within 2s merge, keeping the larger delta's timestamp.
 */
export function wobbleEvents(ps: PlankPerSecond[]): WobbleEvent[] {
  const raw: WobbleEvent[] = [];
  for (let i = 1; i < ps.length; i++) {
    const a = ps[i - 1];
    const b = ps[i];
    if (!inPlank(a) || !inPlank(b)) continue;
    if (b.t - a.t !== 1) continue; // non-consecutive seconds
    if (Number.isNaN(a.body_line_deg) || Number.isNaN(b.body_line_deg)) continue;
    const delta = Math.abs(b.body_line_deg - a.body_line_deg);
    if (delta > WOBBLE_DELTA_DEG) raw.push({ t: b.t, delta });
  }

  const merged: WobbleEvent[] = [];
  for (const ev of raw) {
    const last = merged[merged.length - 1];
    if (last && ev.t - last.t <= WOBBLE_MERGE_GAP_S) {
      if (ev.delta > last.delta) merged[merged.length - 1] = ev;
    } else {
      merged.push(ev);
    }
  }
  return merged;
}

/** Start t of the first ≥5s run of in_plank seconds with form_score < 0.7. */
export function decayPoint(ps: PlankPerSecond[]): number | null {
  let runStart: number | null = null;
  let runLen = 0;
  for (const s of ps) {
    if (inPlank(s) && s.form_score < DECAY_FORM_THRESHOLD) {
      if (runStart === null) runStart = s.t;
      runLen += 1;
      if (runLen >= DECAY_WINDOW_S) return runStart;
    } else {
      runStart = null;
      runLen = 0;
    }
  }
  return null;
}

/** Milestones of cumulative hold time; t = video time of crossing. */
export function milestones(ps: PlankPerSecond[]): Milestone[] {
  const out: Milestone[] = MILESTONE_SECONDS.map(([label]) => ({
    label,
    t: null,
    reached: false,
  }));
  let cumulative = 0;
  for (const s of ps) {
    if (!inPlank(s)) continue;
    cumulative += 1;
    MILESTONE_SECONDS.forEach(([, secs], i) => {
      if (!out[i].reached && cumulative >= secs) {
        out[i] = { label: out[i].label, t: s.t, reached: true };
      }
    });
  }
  return out;
}

const ARCHETYPES: Record<string, Personality> = {
  jelly: { key: "jelly", emoji: "🪼", name: "Jelly", blurb: "Chaos, but you held on." },
  phoenix: { key: "phoenix", emoji: "🔥", name: "Phoenix", blurb: "Wobbled, recovered, finished strong." },
  melter: { key: "melter", emoji: "🫠", name: "Slow Melter", blurb: "Started strong, gravity won slowly." },
  statue: { key: "statue", emoji: "🗿", name: "Statue", blurb: "Absolutely motionless. Suspiciously so." },
  eddie: { key: "eddie", emoji: "💪", name: "Steady Eddie", blurb: "Consistent, controlled, dependable." },
};

/** Archetype from the in_plank form curve. First match wins; null if <10s of hold. */
export function personality(
  ps: PlankPerSecond[],
  stdevDeg?: number | null
): Personality | null {
  const hold = ps.filter((s) => inPlank(s) && !Number.isNaN(s.form_score));
  if (hold.length < PERSONALITY_MIN_PLANK_S) return null;

  const stdev = stdevDeg != null && !Number.isNaN(stdevDeg) ? stdevDeg : 0;
  const wobbles = wobbleEvents(ps);

  // 1. Jelly — chaos
  if (wobbles.length >= 4 || stdev > 4) return ARCHETYPES.jelly;

  // 2. Phoenix — a dip ≥0.15 below the rolling 10s average, later recovered
  const window = 10;
  let dipAt = -1;
  let preDipAvg = 0;
  for (let i = window; i < hold.length; i++) {
    const avg =
      hold.slice(i - window, i).reduce((acc, s) => acc + s.form_score, 0) / window;
    if (dipAt < 0 && hold[i].form_score <= avg - 0.15) {
      dipAt = i;
      preDipAvg = avg;
    } else if (dipAt >= 0 && hold[i].form_score >= preDipAvg) {
      return ARCHETYPES.phoenix;
    }
  }

  // 3. Slow Melter — OLS slope of form vs t below -0.002/s
  const n = hold.length;
  const meanT = hold.reduce((a, s) => a + s.t, 0) / n;
  const meanF = hold.reduce((a, s) => a + s.form_score, 0) / n;
  let num = 0;
  let den = 0;
  for (const s of hold) {
    num += (s.t - meanT) * (s.form_score - meanF);
    den += (s.t - meanT) ** 2;
  }
  const slope = den > 0 ? num / den : 0;
  if (slope < -0.002) return ARCHETYPES.melter;

  // 4. Statue — barely moved
  if (stdev <= 1.5 && wobbles.length <= 1) return ARCHETYPES.statue;

  // 5. Fallback
  return ARCHETYPES.eddie;
}
