import {
  scoreColumnLabel,
  scoreUnit,
  formatScoreValue,
  uploadCtaLabel,
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
