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
  | "deadlift"
  | "pushup"
  | "situp";

export const SUPPORTED_LIFT_TYPES: CoachingLiftType[] = [
  "bicep_curl",
  "squat",
  "bench_press",
  "deadlift",
  "pushup",
  "situp",
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
  pushup: ["rom", "control", "elbow_stability", "shoulder_swing", "tempo"],
  // Older situp reports also carry the arm metrics; they describe nothing, so
  // only the trunk metrics are rendered.
  situp: ["rom", "control", "hips_planted", "neck_pull", "tempo"],
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
  // Pushups reuse the engine's bicep_curl metric set (same elbow-angle signal),
  // but every piece of copy is rewritten for a bodyweight press — the metric
  // KEYS are shared, the meaning is not. "elbow_stability" is elbow flare,
  // "shoulder_swing" is hip sag/pike.
  pushup: {
    rom: {
      fail: "You're cutting the range short — lower until your chest is near the floor and press all the way to straight arms.",
    },
    control: {
      fail: "You're dropping into the bottom — lower yourself under control instead of collapsing to the floor.",
    },
    elbow_stability: {
      fail: "Your elbows are flaring wide — keep them tracking back at roughly 45° from your body.",
    },
    shoulder_swing: {
      fail: "Your hips are sagging or piking — squeeze your glutes and core to hold one straight line from head to heels.",
    },
    tempo: TEMPO_COACHING,
  },
  // Situps segment reps on the trunk lift. Only the metrics that describe a
  // situp get copy; the arm metrics are hidden for this lift.
  situp: {
    rom: {
      fail: "You're cutting the range short — lower your shoulders back to the floor and lift your head and shoulders clearly off it each rep.",
    },
    control: {
      fail: "You're dropping back down — lower your torso under control instead of falling to the floor.",
    },
    hips_planted: {
      fail: "Your hips are lifting or rocking — keep your lower back and hips on the floor and let your abs do the lifting.",
    },
    neck_pull: {
      fail: "You're pulling on your head — lead with your chest and keep a fist of space between your chin and chest.",
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
  pushup: "pushup",
  situp: "situp",
};

/**
 * Per-grade overall copy for lifts where the generic wording doesn't fit.
 * The generic F line says "start lighter", which is meaningless for a
 * bodyweight movement — there is no weight to drop.
 */
const OVERALL_SUMMARY_OVERRIDES: Partial<
  Record<CoachingLiftType, Record<string, string>>
> = {
  pushup: {
    A: "Excellent form — your whole set stayed clean and controlled.",
    B: "Solid set with just a little room to tighten up.",
    C: "Decent set — clean up the flagged metrics to get more out of each rep.",
    D: "Your form slipped over the set — focus on the failed metrics below.",
    F: "Your form broke down — drop to your knees or a raised surface and rebuild the movement.",
  },
  situp: {
    A: "Excellent form — every rep was full range and controlled, and every one counted.",
    B: "Solid set with just a little room to tighten up — nearly every rep counted.",
    C: "Decent set — sloppy reps don't count, so clean up the flagged metrics to bank more of them.",
    D: "Your form slipped over the set and it cost you reps — focus on the failed metrics below.",
    F: "Your form broke down — slow each rep down and rebuild the movement before adding more.",
  },
};

/**
 * Per-lift overrides for the metric label and help text.
 *
 * The engine bakes `label`/`description` into each report from its
 * bicep_curl METRIC_TARGETS block, so a pushup report literally reads "how
 * much of the full curl range you used". Overriding here (rather than in the
 * engine) fixes reports that were ALREADY analyzed — no re-analysis needed —
 * and keeps the fix in one place. Falls back to whatever the engine sent.
 */
const METRIC_COPY_OVERRIDES: Partial<
  Record<CoachingLiftType, Record<string, { label?: string; description?: string }>>
> = {
  pushup: {
    rom: {
      label: "Depth",
      description:
        "How deep each pushup went. Measures your elbow angle from locked-out arms at the top to the bottom of the rep — deeper is better, to about 90°.",
    },
    control: {
      label: "Control",
      description:
        "How smoothly you lowered yourself. Measures how much you decelerate near the bottom instead of dropping to the floor.",
    },
    elbow_stability: {
      label: "Elbow Flare",
      description:
        "How much your elbows flared out to the sides. Elbows tracking back at roughly 45° are stronger and easier on the shoulders than elbows flared to 90°.",
    },
    shoulder_swing: {
      label: "Body Line",
      description:
        "Whether your hips stayed in line with your shoulders and heels. Higher numbers mean your hips sagged or piked instead of holding a straight plank line.",
    },
    tempo: {
      description:
        "Ratio of lowering time to pressing time. Around 2:1 — lowering twice as slowly as you press — builds the most strength.",
    },
  },
  situp: {
    rom: {
      label: "Range",
      description:
        "How far your head and shoulders lifted off the floor on each rep. A full crunch counts as full range.",
    },
    control: {
      label: "Control",
      description:
        "How smoothly you lowered back down. Measures how much you decelerate near the floor instead of dropping onto it.",
    },
    hips_planted: {
      label: "Hips Planted",
      description:
        "How still your hips stayed on the floor through each rep. Higher is better — above 70% means they stayed put.",
    },
    neck_pull: {
      label: "Neck Pull",
      description:
        "How far your head curled forward past your torso at the top of the rep. Lower is better — under 20° means you weren't pulling on your neck.",
    },
    tempo: {
      description:
        "Ratio of lowering time to sitting-up time. Around 2:1 — lowering twice as slowly as you rise — works the core hardest.",
    },
  },
};

/** Whether a metric the engine emitted describes this lift at all. */
export function metricAppliesToLift(
  liftType: string | undefined | null,
  metricKey: string
): boolean {
  return LIFT_METRIC_KEYS[normalizeCoachingLiftType(liftType)].includes(metricKey);
}

/** Metric label for display, preferring a lift-specific override. */
export function getMetricLabel(
  liftType: string | undefined | null,
  metricKey: string,
  engineLabel: string
): string {
  const lift = normalizeCoachingLiftType(liftType);
  return METRIC_COPY_OVERRIDES[lift]?.[metricKey]?.label ?? engineLabel;
}

/** Metric help text for display, preferring a lift-specific override. */
export function getMetricDescription(
  liftType: string | undefined | null,
  metricKey: string,
  engineDescription: string | undefined
): string | undefined {
  const lift = normalizeCoachingLiftType(liftType);
  return METRIC_COPY_OVERRIDES[lift]?.[metricKey]?.description ?? engineDescription;
}

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
  const lift = normalizeCoachingLiftType(liftType);
  const name = LIFT_DISPLAY_NAME[lift];
  const key = (grade || "").toUpperCase();
  const override = OVERALL_SUMMARY_OVERRIDES[lift];
  if (override) return override[key] ?? override.F;
  switch (key) {
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
