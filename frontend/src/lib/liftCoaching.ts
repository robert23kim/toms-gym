/**
 * Plain-language coaching copy for the lifting rep breakdown (T11).
 *
 * The analysis engine emits raw per-metric numbers (see
 * `bowling-app/analysis-engine/src/lifting/analysis/analyze.py` +
 * `config.py`). This module is a STATIC copy map that turns a
 * (lift type, metric key, pass/fail) tuple into a one-sentence takeaway,
 * plus a one-line overall summary for the letter grade. Coaching copy is
 * additive — the raw numbers stay visible in the UI.
 *
 * Metric coverage per lift type mirrors the engine exactly:
 *   - deadlift        → rom, lockout, back_position, control, tempo
 *   - everything else → rom, control, elbow_stability, shoulder_swing, tempo
 *     (squat/bench_press fall back to the bicep_curl metric set in the engine)
 */

import type { MetricFeedback } from "./types";

/**
 * lift_type values the report can carry. These are the strings produced by
 * `_normalize_lift_type` in `backend/toms_gym/integrations/lifting_processor.py`
 * for the four lift types the upload UI offers. `plank` is handled by a
 * separate result card and has no per-rep metrics, so it is not covered here.
 */
export type CoachingLiftType =
  | "bicep_curl"
  | "squat"
  | "bench_press"
  | "deadlift";

export const SUPPORTED_LIFT_TYPES: CoachingLiftType[] = [
  "bicep_curl",
  "squat",
  "bench_press",
  "deadlift",
];

/**
 * Metric keys the UI can render per lift type, mirroring the engine's
 * `_build_metrics_feedback` (bicep_curl/squat/bench_press) and
 * `_build_deadlift_metrics_feedback` (deadlift).
 */
export const LIFT_METRIC_KEYS: Record<CoachingLiftType, string[]> = {
  bicep_curl: ["rom", "control", "elbow_stability", "shoulder_swing", "tempo"],
  squat: ["rom", "control", "elbow_stability", "shoulder_swing", "tempo"],
  bench_press: ["rom", "control", "elbow_stability", "shoulder_swing", "tempo"],
  deadlift: ["rom", "lockout", "back_position", "control", "tempo"],
};

interface MetricCoaching {
  /** Default one-sentence takeaway when the metric fails. */
  fail: string;
  /** Range-metric (tempo) override when the value is below the target range. */
  failFast?: string;
  /** Range-metric (tempo) override when the value is above the target range. */
  failSlow?: string;
}

type LiftCoachingMap = Record<CoachingLiftType, Record<string, MetricCoaching>>;

// Shared tempo copy — tempo is a lowering:lifting ratio; below range = lowering
// too fast, above range = lowering too slowly / pausing.
const TEMPO_COACHING: MetricCoaching = {
  fail: "Your tempo is off — aim to lower about twice as slowly as you lift, on a smooth count.",
  failFast:
    "You're lowering too quickly — control the descent and take about twice as long to lower as you do to lift.",
  failSlow:
    "You're lowering too slowly or pausing — keep the descent smooth and continuous, roughly twice your lifting speed.",
};

const COACHING: LiftCoachingMap = {
  bicep_curl: {
    rom: {
      fail: "You're not using your full range — extend all the way at the bottom and squeeze at the top of each curl.",
    },
    control: {
      fail: "You're dropping the weight on the way down — lower it slowly and stay in control of every rep.",
    },
    elbow_stability: {
      fail: "Your elbow is drifting — pin your upper arm to your side and keep the elbow fixed as you curl.",
    },
    shoulder_swing: {
      fail: "You're swinging your shoulders to lift — keep them still and let your biceps do the work.",
    },
    tempo: TEMPO_COACHING,
  },
  squat: {
    rom: {
      fail: "You're cutting the squat short — sink to at least parallel and drive all the way back up to standing.",
    },
    control: {
      fail: "You're descending too fast — control the way down instead of dropping into the bottom.",
    },
    elbow_stability: {
      fail: "Your upper body is shifting — keep your torso braced and the bar stacked over your midfoot.",
    },
    shoulder_swing: {
      fail: "You're using body swing for momentum — keep your torso steady and drive the weight with your legs.",
    },
    tempo: TEMPO_COACHING,
  },
  bench_press: {
    rom: {
      fail: "You're not using full range — bring the bar to your chest and press to full lockout every rep.",
    },
    control: {
      fail: "You're letting the bar fall — lower it under control to your chest instead of bouncing it.",
    },
    elbow_stability: {
      fail: "Your elbows are wandering — keep them tucked and moving in a straight, stable path.",
    },
    shoulder_swing: {
      fail: "Your shoulders are rolling forward — keep them pinned back and down against the bench.",
    },
    tempo: TEMPO_COACHING,
  },
  deadlift: {
    rom: {
      fail: "You're not covering the full hinge — start with the bar low and stand all the way tall at the top.",
    },
    lockout: {
      fail: "You didn't finish fully upright — stand tall and squeeze your glutes to lock out at the top.",
    },
    back_position: {
      fail: "Your back is rounding — brace your core and keep a flat, neutral spine throughout the pull.",
    },
    control: {
      fail: "You're dropping the bar on the way down — lower it under control rather than letting it fall.",
    },
    tempo: TEMPO_COACHING,
  },
};

/** Human-friendly lift name used in overall-summary copy. */
const LIFT_DISPLAY_NAME: Record<CoachingLiftType, string> = {
  bicep_curl: "curl",
  squat: "squat",
  bench_press: "bench press",
  deadlift: "deadlift",
};

/**
 * Normalize an arbitrary report lift_type string onto a supported coaching
 * lift type. Mirrors the engine's fallback: unknown lift types are coached as
 * bicep_curl (the engine uses the bicep_curl config for them).
 */
export function normalizeCoachingLiftType(
  liftType: string | undefined | null
): CoachingLiftType {
  if (!liftType) return "bicep_curl";
  const key = liftType.trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (key in COACHING) return key as CoachingLiftType;
  // Common aliases from older upload copy.
  if (key === "bench" || key === "bench_press") return "bench_press";
  if (key === "bicep" || key === "bicep_curl" || key === "curl")
    return "bicep_curl";
  return "bicep_curl";
}

/**
 * One-sentence coaching takeaway for a failed metric. Returns null for
 * passing/warning metrics (coaching copy is only shown on failure) or for a
 * metric key that has no copy for the given lift type.
 *
 * `value` is optional and only used to pick a directional variant for the
 * range-based tempo metric (too fast vs too slow).
 */
export function getMetricCoaching(
  liftType: string | undefined | null,
  metricKey: string,
  status: MetricFeedback["status"],
  value?: number
): string | null {
  if (status !== "fail") return null;
  const lift = normalizeCoachingLiftType(liftType);
  const entry = COACHING[lift][metricKey];
  if (!entry) return null;

  if (metricKey === "tempo" && value != null && Number.isFinite(value)) {
    // Tempo target ranges start at 1.5 for every lift; below = lowering too fast.
    const lowerBound = 1.5;
    if (value < lowerBound && entry.failFast) return entry.failFast;
    if (value >= lowerBound && entry.failSlow) return entry.failSlow;
  }
  return entry.fail;
}

/** Coaching takeaway keyed directly off a MetricFeedback item. */
export function getMetricCoachingFor(
  liftType: string | undefined | null,
  metric: Pick<MetricFeedback, "key" | "status" | "value">
): string | null {
  return getMetricCoaching(liftType, metric.key, metric.status, metric.value);
}

/**
 * One-line overall takeaway shown next to the letter grade. Always returns a
 * non-empty sentence for grades A–F.
 */
export function getOverallSummary(
  liftType: string | undefined | null,
  grade: string
): string {
  const name = LIFT_DISPLAY_NAME[normalizeCoachingLiftType(liftType)];
  switch ((grade || "").toUpperCase()) {
    case "A":
      return `Excellent form — your ${name} reps were clean and well controlled.`;
    case "B":
      return `Solid ${name} form with just a little room to tighten up.`;
    case "C":
      return `Decent ${name} form — clean up the flagged metrics for stronger reps.`;
    case "D":
      return `Your ${name} form needs work — focus on the failed metrics below.`;
    case "F":
    default:
      return `Your ${name} form broke down — start lighter and rebuild the movement from the basics.`;
  }
}
