/**
 * Set-level form aggregation for rep-based lifts.
 *
 * A pushup set is judged as a set, not rep-by-rep: 30 separate cards is noise,
 * and one bad rep out of 30 is not the story. This collapses the engine's
 * per-rep `rep_metrics` into one row per metric, averaging the value and
 * reporting how many reps passed.
 *
 * Pure and DB-free so it can be fixture-tested (mirrors lib/plankStats.ts).
 */

export type MetricStatus = "pass" | "warn" | "fail";

export interface SetMetricInput {
  key: string;
  label: string;
  value: number;
  unit: string;
  target: string;
  status: string;
  description?: string;
}

export interface RepMetricsInput {
  rep_number: number;
  metrics?: SetMetricInput[] | null;
}

export interface SetMetric {
  key: string;
  label: string;
  /** Mean value across every rep that reported this metric. */
  value: number;
  unit: string;
  target: string;
  /** Aggregate status — see `aggregateStatus`. */
  status: MetricStatus;
  description?: string;
  /** How many reps passed this metric. */
  passCount: number;
  /** How many reps reported this metric at all. */
  repCount: number;
}

/**
 * Aggregate status for a metric across a set:
 *   - every rep passed        -> "pass"
 *   - at least half passed    -> "warn"
 *   - fewer than half passed  -> "fail"
 *
 * Deliberately simple and explainable — it never invents a numeric threshold
 * the engine didn't give us, it only counts the engine's own per-rep verdicts.
 */
export function aggregateStatus(passCount: number, repCount: number): MetricStatus {
  if (repCount <= 0) return "fail";
  if (passCount === repCount) return "pass";
  if (passCount * 2 >= repCount) return "warn";
  return "fail";
}

/** Round to one decimal, dropping a trailing ".0". */
function round1(n: number): number {
  return Math.round(n * 10) / 10;
}

/**
 * Collapse per-rep metrics into one row per metric key, preserving the order
 * the metrics first appear in. Reps that reported no metrics are ignored.
 * Returns [] when there is nothing to summarize.
 */
export function summarizeSet(repMetrics: RepMetricsInput[] | null | undefined): SetMetric[] {
  if (!repMetrics || repMetrics.length === 0) return [];

  const order: string[] = [];
  const acc = new Map<
    string,
    { label: string; unit: string; target: string; description?: string; sum: number; n: number; pass: number }
  >();

  for (const rep of repMetrics) {
    if (!rep.metrics) continue;
    for (const m of rep.metrics) {
      if (typeof m.value !== "number" || Number.isNaN(m.value)) continue;
      let entry = acc.get(m.key);
      if (!entry) {
        entry = {
          label: m.label,
          unit: m.unit,
          target: m.target,
          description: m.description,
          sum: 0,
          n: 0,
          pass: 0,
        };
        acc.set(m.key, entry);
        order.push(m.key);
      }
      entry.sum += m.value;
      entry.n += 1;
      if (m.status === "pass") entry.pass += 1;
    }
  }

  return order.map((key) => {
    const e = acc.get(key)!;
    return {
      key,
      label: e.label,
      value: round1(e.sum / e.n),
      unit: e.unit,
      target: e.target,
      description: e.description,
      status: aggregateStatus(e.pass, e.n),
      passCount: e.pass,
      repCount: e.n,
    };
  });
}
