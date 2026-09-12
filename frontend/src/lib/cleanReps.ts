/**
 * Quality-scored rep boards: a situp whose form grades C or better counts in
 * full, anything sloppier counts half. Mirrors backend
 * services/challenge_leaderboard.py so the result page and the board never
 * disagree on an athlete's score.
 */
export const CLEAN_REP_MIN_FORM = 70;
export const SLOPPY_REP_CREDIT = 0.5;

export interface RepReport {
  lift_type?: string | null;
  total_reps?: number | null;
  rep_metrics?: { form_score?: number | null }[] | null;
}

export function isQualityScoredLift(liftType: string | null | undefined): boolean {
  return (liftType || "").trim().toLowerCase() === "situp";
}

/** Reps whose form score clears the bar. Null when there are no per-rep scores. */
export function cleanRepCount(
  repMetrics: { form_score?: number | null }[] | null | undefined,
): number | null {
  if (!repMetrics || repMetrics.length === 0) return null;
  return repMetrics.filter((m) => (m.form_score ?? -1) >= CLEAN_REP_MIN_FORM).length;
}

/** The score a rep-lift report contributes to its board. */
export function boardReps(report: RepReport | null | undefined): number | null {
  if (!report) return null;
  const total = report.total_reps ?? null;
  if (total == null) return null;
  if (!isQualityScoredLift(report.lift_type)) return total;
  const clean = cleanRepCount(report.rep_metrics);
  if (clean == null) return total;
  return clean + SLOPPY_REP_CREDIT * Math.max(0, total - clean);
}
