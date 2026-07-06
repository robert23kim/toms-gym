import {
  SUPPORTED_LIFT_TYPES,
  LIFT_METRIC_KEYS,
  getMetricCoaching,
  getMetricCoachingFor,
  getOverallSummary,
  normalizeCoachingLiftType,
  type CoachingLiftType,
} from "../liftCoaching";

describe("liftCoaching copy map", () => {
  // Completeness: every (lift, metric, fail) combination the app can render
  // must resolve to a non-empty coaching sentence.
  describe("coverage of every failable (lift, metric) combination", () => {
    for (const lift of SUPPORTED_LIFT_TYPES) {
      for (const metric of LIFT_METRIC_KEYS[lift]) {
        it(`${lift} / ${metric} → non-empty fail copy`, () => {
          const copy = getMetricCoaching(lift, metric, "fail");
          expect(typeof copy).toBe("string");
          expect((copy ?? "").trim().length).toBeGreaterThan(0);
        });
      }
    }
  });

  it("covers exactly the metric set the engine emits per lift type", () => {
    expect(LIFT_METRIC_KEYS.bicep_curl).toEqual([
      "rom",
      "control",
      "elbow_stability",
      "shoulder_swing",
      "tempo",
    ]);
    expect(LIFT_METRIC_KEYS.squat).toEqual(LIFT_METRIC_KEYS.bicep_curl);
    expect(LIFT_METRIC_KEYS.bench_press).toEqual(LIFT_METRIC_KEYS.bicep_curl);
    expect(LIFT_METRIC_KEYS.deadlift).toEqual([
      "rom",
      "lockout",
      "back_position",
      "control",
      "tempo",
    ]);
  });

  it("returns null for passing and warning metrics (copy is failure-only)", () => {
    expect(getMetricCoaching("deadlift", "lockout", "pass")).toBeNull();
    expect(getMetricCoaching("deadlift", "lockout", "warn")).toBeNull();
  });

  it("returns null for a metric key that does not apply to the lift type", () => {
    // lockout/back_position only exist on deadlift.
    expect(getMetricCoaching("bicep_curl", "lockout", "fail")).toBeNull();
    expect(getMetricCoaching("squat", "back_position", "fail")).toBeNull();
  });

  it("picks a directional tempo sentence from the value", () => {
    const fast = getMetricCoaching("bicep_curl", "tempo", "fail", 0.1);
    const slow = getMetricCoaching("bicep_curl", "tempo", "fail", 4.0);
    expect(fast).toMatch(/quickly/i);
    expect(slow).toMatch(/slowly|pausing/i);
    expect(fast).not.toEqual(slow);
  });

  it("falls back to generic tempo copy when no value is provided", () => {
    const copy = getMetricCoaching("squat", "tempo", "fail");
    expect((copy ?? "").length).toBeGreaterThan(0);
  });

  it("resolves coaching directly from a MetricFeedback item", () => {
    const copy = getMetricCoachingFor("deadlift", {
      key: "back_position",
      status: "fail",
      value: 89.7,
    });
    expect(copy).toMatch(/back/i);
  });

  it("normalizes report lift_type strings and aliases onto supported types", () => {
    const cases: Array<[string | undefined | null, CoachingLiftType]> = [
      ["bench_press", "bench_press"],
      ["Bench Press", "bench_press"],
      ["Bench", "bench_press"],
      ["Bicep Curl", "bicep_curl"],
      ["curl", "bicep_curl"],
      ["Deadlift", "deadlift"],
      ["squat", "squat"],
      ["something-unknown", "bicep_curl"],
      [undefined, "bicep_curl"],
      [null, "bicep_curl"],
    ];
    for (const [input, expected] of cases) {
      expect(normalizeCoachingLiftType(input)).toBe(expected);
    }
  });

  it("resolves coaching for a bench_press report (engine falls back to bicep set)", () => {
    for (const metric of LIFT_METRIC_KEYS.bench_press) {
      const copy = getMetricCoaching("Bench Press", metric, "fail");
      expect((copy ?? "").length).toBeGreaterThan(0);
    }
  });

  describe("overall summary", () => {
    it("returns a non-empty sentence for every grade and lift type", () => {
      for (const lift of SUPPORTED_LIFT_TYPES) {
        for (const grade of ["A", "B", "C", "D", "F"]) {
          const summary = getOverallSummary(lift, grade);
          expect(summary.trim().length).toBeGreaterThan(0);
        }
      }
    });

    it("mentions the lift name in the summary", () => {
      expect(getOverallSummary("deadlift", "A")).toMatch(/deadlift/i);
      expect(getOverallSummary("bench_press", "F")).toMatch(/bench press/i);
    });

    it("treats an unknown grade as a failing summary", () => {
      expect(getOverallSummary("squat", "?")).toMatch(/broke down/i);
    });
  });
});
