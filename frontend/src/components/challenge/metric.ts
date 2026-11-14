import type { ChallengeMetric, ConsistencyRules } from "../../lib/types";

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
  if (metric === "consistency") return "POINTS";
  return "TOTAL";
}

export function scoreUnit(metric: ChallengeMetric): string {
  if (metric === "time") return "s";
  if (metric === "reps") return "reps";
  if (metric === "consistency") return "pts";
  return "lbs";
}

/** Number part of a score, formatted for the metric (one decimal for time;
 * reps keep a half when quality scoring produced one). */
export function formatScoreValue(score: number, metric: ChallengeMetric): string {
  if (metric === "time") return score.toFixed(1);
  if ((metric === "reps" || metric === "consistency") && !Number.isInteger(score)) return score.toFixed(1);
  return String(Math.round(score));
}

const isSitupOnly = (liftTypes?: string[]): boolean =>
  !!liftTypes && liftTypes.length > 0 && liftTypes.every((t) => t.toLowerCase() === "situp");

export function uploadCtaLabel(metric: ChallengeMetric, liftTypes?: string[]): string {
  if (metric === "time") return "Upload your plank";
  if (metric === "consistency") return "Log this week's lifts";
  if (metric === "reps") return isSitupOnly(liftTypes) ? "Upload your situps" : "Upload your pushups";
  return "Upload your lift";
}

/** One line explaining a board whose score is not simply "how many". */
export function scoringNote(
  metric: ChallengeMetric,
  liftTypes?: string[],
  rules?: Partial<ConsistencyRules>,
): string | null {
  if (metric === "consistency")
    return consistencyNote(rules, liftTypes?.filter((t) => CLUB_COUNTED_TYPES.includes(t)).length ?? 0);
  if (metric !== "reps") return null;
  if (!liftTypes?.some((t) => t.toLowerCase() === "situp")) return null;
  return "Clean reps count in full and sloppy reps count half — a rep is clean when its form grades C or better.";
}

// Mirrors COUNTED_LIFT_TYPES in backend/toms_gym/services/consistency.py.
const CLUB_COUNTED_TYPES = ["Situp", "Pushup", "Squat", "Plank"];

export const typeBonusClause = (bonus: number): string =>
  `+${bonus} extra for each lift type you log that week where nobody logs more`;

const CONSISTENCY_DEFAULTS = {
  base_quota: 100,
  ramp: 25,
  quota_bonus: 50,
  type_bonus: 25,
  plank_seconds_per_lift: 10,
};

function consistencyNote(rules: Partial<ConsistencyRules> | undefined, typeCount: number): string {
  const r = { ...CONSISTENCY_DEFAULTS, ...rules };
  const cap = typeCount > 0 ? `, up to +${r.type_bonus * typeCount}` : "";
  return (
    `Every rep is a lift (sloppy situps count half) and every ${r.plank_seconds_per_lift} s of plank is one. ` +
    `Hit the weekly quota for +${r.quota_bonus} and next week's goes up ${r.ramp}; miss it and it resets to ${r.base_quota}. ` +
    `${typeBonusClause(r.type_bonus)}${cap}; any mix counts toward the quota.`
  );
}
