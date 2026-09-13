/**
 * Pace and fade across a rep set, from the engine's per-rep timing
 * (`start_s` / `peak_s` / `end_s`). Pure and DB-free so it can be
 * fixture-tested (mirrors lib/setSummary.ts).
 */
import { CLEAN_REP_MIN_FORM } from "./cleanReps";

export interface TimedRepInput {
  form_score?: number | null;
  start_s?: number | null;
  peak_s?: number | null;
  end_s?: number | null;
}

export interface SetThird {
  reps: number;
  /** Mean form score of the reps peaking in this window; null when empty. */
  avgForm: number | null;
}

export interface SetPace {
  reps: number;
  durationS: number;
  repsPerMinute: number;
  thirds: [SetThird, SetThird, SetThird];
  longestPauseS: number;
  bestCleanStreak: number;
  fastestRepS: number;
  slowestRepS: number;
}

export const MIN_TIMED_REPS = 3;

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}

function isNum(n: number | null | undefined): n is number {
  return typeof n === "number" && Number.isFinite(n);
}

interface TimedRep {
  form: number | null;
  start: number;
  peak: number;
  end: number;
}

export function setPace(repMetrics: TimedRepInput[] | null | undefined): SetPace | null {
  if (!repMetrics) return null;
  const reps: TimedRep[] = repMetrics
    .filter((r) => isNum(r.start_s) && isNum(r.peak_s) && isNum(r.end_s))
    .map((r) => ({
      form: isNum(r.form_score) ? r.form_score : null,
      start: r.start_s as number,
      peak: r.peak_s as number,
      end: r.end_s as number,
    }))
    .sort((a, b) => a.start - b.start);
  if (reps.length < MIN_TIMED_REPS) return null;

  const first = reps[0].start;
  const last = Math.max(...reps.map((r) => r.end));
  const duration = last - first;
  if (duration <= 0) return null;

  const buckets: TimedRep[][] = [[], [], []];
  const window = duration / 3;
  for (const r of reps) {
    // A peak exactly on a boundary belongs to the later window.
    const i = Math.min(2, Math.max(0, Math.floor((r.peak - first) / window)));
    buckets[i].push(r);
  }
  const thirds = buckets.map((b) => {
    const forms = b.map((r) => r.form).filter(isNum);
    return {
      reps: b.length,
      avgForm: forms.length ? Math.round(forms.reduce((s, f) => s + f, 0) / forms.length) : null,
    };
  }) as [SetThird, SetThird, SetThird];

  let longestPause = 0;
  for (let i = 1; i < reps.length; i++) {
    longestPause = Math.max(longestPause, reps[i].start - reps[i - 1].end);
  }

  let streak = 0;
  let bestStreak = 0;
  for (const r of reps) {
    streak = r.form != null && r.form >= CLEAN_REP_MIN_FORM ? streak + 1 : 0;
    bestStreak = Math.max(bestStreak, streak);
  }

  const lengths = reps.map((r) => r.end - r.start);

  return {
    reps: reps.length,
    durationS: round1(duration),
    repsPerMinute: round1((reps.length / duration) * 60),
    thirds,
    longestPauseS: round1(longestPause),
    bestCleanStreak: bestStreak,
    fastestRepS: round1(Math.min(...lengths)),
    slowestRepS: round1(Math.max(...lengths)),
  };
}
