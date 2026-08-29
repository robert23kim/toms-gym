interface SteadinessRow {
  attempt_id: string;
  steadiness?: number | null;
}

/** True when this attempt's body-line stdev beats every other measured attempt of the athlete's. */
export function steadiestYet(rows: SteadinessRow[], attemptId: string, stdev: number | null | undefined): boolean {
  if (stdev == null || !Number.isFinite(stdev)) return false;
  const others = rows
    .filter((r) => r.attempt_id !== attemptId && r.steadiness != null && Number.isFinite(r.steadiness))
    .map((r) => r.steadiness as number);
  return others.length > 0 && stdev < Math.min(...others);
}
