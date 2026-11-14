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

describe("consistency metric (The 100 Club)", () => {
  test("labels the score column POINTS with a pts unit", () => {
    expect(scoreColumnLabel("consistency")).toBe("POINTS");
    expect(scoreUnit("consistency")).toBe("pts");
  });

  test("formats points as integers, keeping a situp half-credit", () => {
    expect(formatScoreValue(467, "consistency")).toBe("467");
    expect(formatScoreValue(41.5, "consistency")).toBe("41.5");
  });

  test("asks for this week's lifts", () => {
    expect(uploadCtaLabel("consistency", ["Situp", "Pushup", "Squat", "Plank"])).toBe("Log this week's lifts");
  });

  test("explains the rules in one line, from the stored rules", () => {
    const note = scoringNote("consistency", ["Situp", "Pushup", "Squat", "Plank"]);
    expect(note).toMatch(/10 s of plank/);
    expect(note).toMatch(/\+50/);
    expect(note).toMatch(/resets to 100/);
    expect(note).toMatch(/\+25/);
    expect(note).not.toMatch(/\n/);
    expect(scoringNote("consistency", [], { plank_seconds_per_lift: 15, base_quota: 80 })).toMatch(/15 s of plank.*resets to 80/);
  });

  test("words the type bonus as an extra per type, not a split of the quota", () => {
    const note = scoringNote("consistency", ["Situp", "Pushup", "Squat", "Plank"]);
    expect(note).toMatch(/ \+25 extra for each lift type you log the most of that week, ties included, up to \+100; any mix counts toward the quota\.$/);
    expect(note).not.toMatch(/nobody logs more than you/);
    expect(note).not.toMatch(/Most of a lift type/);
    expect(scoringNote("consistency", ["Situp", "Pushup"], { type_bonus: 10 })).toMatch(/\+10 extra for each lift type .* up to \+20;/);
    expect(scoringNote("consistency", ["Situp", "Pushup", "Bench"], { type_bonus: 10 })).toMatch(/ up to \+20;/);
  });
});
