import type { ChallengeMetric } from "../../lib/types";

// Metric-aware rendering. A challenge is ranked by exactly one metric — `time`
// (plank: seconds held), `reps` (pushup/situp: rep count) or `weight` (best-lift
// total). The layout is identical; only the score unit, column label, and CTA
// wording switch.
//
// Weight scores are shown raw (no kg→lbs conversion) to stay consistent with the
// existing lift feed, which aliases `weight_kg` and renders it as `{weight} lbs`.

export function scoreColumnLabel(metric: ChallengeMetric): string {
  if (metric === "time") return "HOLD";
  if (metric === "reps") return "REPS";
  return "TOTAL";
}

export function scoreUnit(metric: ChallengeMetric): string {
  if (metric === "time") return "s";
  if (metric === "reps") return "reps";
  return "lbs";
}

/** Number part of a score, formatted for the metric (one decimal for time;
 * reps keep a half when quality scoring produced one). */
export function formatScoreValue(score: number, metric: ChallengeMetric): string {
  if (metric === "time") return score.toFixed(1);
  if (metric === "reps" && !Number.isInteger(score)) return score.toFixed(1);
  return String(Math.round(score));
}

const isSitupOnly = (liftTypes?: string[]): boolean =>
  !!liftTypes && liftTypes.length > 0 && liftTypes.every((t) => t.toLowerCase() === "situp");

export function uploadCtaLabel(metric: ChallengeMetric, liftTypes?: string[]): string {
  if (metric === "time") return "Upload your plank";
  if (metric === "reps") return isSitupOnly(liftTypes) ? "Upload your situps" : "Upload your pushups";
  return "Upload your lift";
}

/** One line explaining a board whose score is not simply "how many". */
export function scoringNote(metric: ChallengeMetric, liftTypes?: string[]): string | null {
  if (metric !== "reps") return null;
  if (!liftTypes?.some((t) => t.toLowerCase() === "situp")) return null;
  return "Clean reps count in full and sloppy reps count half — a rep is clean when its form grades C or better.";
}
