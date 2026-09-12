import {
  scoreColumnLabel,
  scoreUnit,
  formatScoreValue,
  uploadCtaLabel,
  scoringNote,
} from "../metric";

describe("challenge metric helpers", () => {
  test("column label switches HOLD / TOTAL", () => {
    expect(scoreColumnLabel("time")).toBe("HOLD");
    expect(scoreColumnLabel("weight")).toBe("TOTAL");
  });

  test("unit switches s / lbs", () => {
    expect(scoreUnit("time")).toBe("s");
    expect(scoreUnit("weight")).toBe("lbs");
  });

  test("time keeps one decimal; weight rounds to a whole number", () => {
    expect(formatScoreValue(65.83, "time")).toBe("65.8");
    expect(formatScoreValue(300.6, "weight")).toBe("301");
  });

  test("CTA wording is metric-appropriate", () => {
    expect(uploadCtaLabel("time")).toBe("Upload your plank");
    expect(uploadCtaLabel("weight")).toBe("Upload your lift");
  });
});

describe("reps metric (pushup challenges)", () => {
  test("labels the score column REPS", () => {
    expect(scoreColumnLabel("reps")).toBe("REPS");
  });

  test("uses a reps unit", () => {
    expect(scoreUnit("reps")).toBe("reps");
  });

  test("formats rep scores as whole numbers", () => {
    expect(formatScoreValue(30, "reps")).toBe("30");
    expect(formatScoreValue(30.5, "reps")).toBe("30.5");
  });

  test("uses a pushup CTA", () => {
    expect(uploadCtaLabel("reps")).toBe("Upload your pushups");
    expect(uploadCtaLabel("reps", ["Pushup"])).toBe("Upload your pushups");
  });

  test("uses a situp CTA on a situp-only board", () => {
    expect(uploadCtaLabel("reps", ["Situp"])).toBe("Upload your situps");
    expect(uploadCtaLabel("reps", ["Pushup", "Situp"])).toBe("Upload your pushups");
  });

  test("explains clean-rep scoring only where it applies", () => {
    expect(scoringNote("reps", ["Situp"])).toMatch(/clean reps/i);
    expect(scoringNote("reps", ["Pushup"])).toBeNull();
    expect(scoringNote("time", ["Situp"])).toBeNull();
  });
});
