import type { ChallengeMetric } from "../../lib/types";

// Metric-aware rendering. A challenge is ranked by exactly one metric — `time`
// (plank: seconds held) or `weight` (best-lift total). The layout is identical;
// only the score unit, column label, and CTA wording switch.
//
// Weight scores are shown raw (no kg→lbs conversion) to stay consistent with the
// existing lift feed, which aliases `weight_kg` and renders it as `{weight} lbs`.

export function scoreColumnLabel(metric: ChallengeMetric): string {
  return metric === "time" ? "HOLD" : "TOTAL";
}

export function scoreUnit(metric: ChallengeMetric): string {
  return metric === "time" ? "s" : "lbs";
}

/** Number part of a score, formatted for the metric (one decimal for time). */
export function formatScoreValue(score: number, metric: ChallengeMetric): string {
  return metric === "time" ? score.toFixed(1) : String(Math.round(score));
}

export function uploadCtaLabel(metric: ChallengeMetric): string {
  return metric === "time" ? "Upload your plank" : "Upload your lift";
}
