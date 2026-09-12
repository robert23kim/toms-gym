import {
  SUPPORTED_LIFT_TYPES,
  LIFT_METRIC_KEYS,
  getMetricCoaching,
  getMetricCoachingFor,
  getOverallSummary,
  getMetricLabel,
  getMetricDescription,
  metricAppliesToLift,
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

describe("pushup copy never uses barbell/weight language", () => {
  // A pushup has no weight to lighten and nothing to lower to a chest. This
  // guards the whole pushup copy surface against curl/barbell wording leaking
  // back in via the bicep_curl fallback.
  const BANNED = /\b(weight|barbell|bar|lighter|curl|bench)\b/i;

  it.each(["A", "B", "C", "D", "F"])("overall summary for grade %s is clean", (g) => {
    const copy = getOverallSummary("pushup", g);
    expect(copy).not.toMatch(BANNED);
    expect(copy.length).toBeGreaterThan(0);
  });

  it.each(LIFT_METRIC_KEYS.pushup)("fail coaching for %s is clean", (key) => {
    const copy = getMetricCoaching("pushup", key, "fail", 0);
    expect(copy).toBeTruthy();
    expect(copy).not.toMatch(BANNED);
  });

  it("overrides metric labels away from curl wording", () => {
    expect(getMetricLabel("pushup", "rom", "Range of Motion")).toBe("Depth");
    expect(getMetricLabel("pushup", "shoulder_swing", "Shoulder Swing")).toBe("Body Line");
    expect(getMetricLabel("pushup", "elbow_stability", "Elbow Stability")).toBe("Elbow Flare");
  });

  it("overrides the curl-flavored description the engine bakes in", () => {
    const engine = "How much of the full curl range you used.";
    const shown = getMetricDescription("pushup", "rom", engine);
    expect(shown).not.toMatch(BANNED);
    expect(shown).not.toBe(engine);
  });

  it("leaves other lifts' labels and descriptions untouched", () => {
    expect(getMetricLabel("bicep_curl", "rom", "Range of Motion")).toBe("Range of Motion");
    expect(getMetricDescription("squat", "rom", "engine text")).toBe("engine text");
  });
});

describe("situp copy never uses barbell/arm language", () => {
  const BANNED = /\b(weight|barbell|bar|lighter|curl|bench|press|elbow)\b/i;

  it.each(["A", "B", "C", "D", "F"])("overall summary for grade %s is clean", (g) => {
    const copy = getOverallSummary("situp", g);
    expect(copy).not.toMatch(BANNED);
    expect(copy.length).toBeGreaterThan(0);
  });

  it.each(LIFT_METRIC_KEYS.situp)("fail coaching for %s is clean", (key) => {
    const copy = getMetricCoaching("situp", key, "fail", 0);
    expect(copy).toBeTruthy();
    expect(copy).not.toMatch(BANNED);
  });

  it("renders only the metrics that describe a situp", () => {
    expect(LIFT_METRIC_KEYS.situp).toEqual(["rom", "control", "tempo"]);
    expect(normalizeCoachingLiftType("Situp")).toBe("situp");
    expect(metricAppliesToLift("situp", "elbow_stability")).toBe(false);
    expect(metricAppliesToLift("situp", "shoulder_swing")).toBe(false);
    expect(metricAppliesToLift("situp", "rom")).toBe(true);
    expect(metricAppliesToLift("pushup", "elbow_stability")).toBe(true);
  });

  it("overrides the curl-flavored range label and description", () => {
    expect(getMetricLabel("situp", "rom", "Range of Motion")).toBe("Range");
    const engine = "How much of the full curl range you used.";
    expect(getMetricDescription("situp", "rom", engine)).not.toMatch(BANNED);
  });
});
