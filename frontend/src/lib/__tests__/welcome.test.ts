import { lastLiftCopy, sinceCopy } from "../welcome";

const now = new Date("2026-08-29T12:00:00Z");

describe("sinceCopy", () => {
  it("speaks in days, then months, then years", () => {
    expect(sinceCopy("2026-08-29T01:00:00Z", now)).toBe("today");
    expect(sinceCopy("2026-08-28T01:00:00Z", now)).toBe("yesterday");
    expect(sinceCopy("2026-08-20T01:00:00Z", now)).toBe("9 days ago");
    expect(sinceCopy("2026-04-12T01:00:00Z", now)).toBe("4 months ago");
    expect(sinceCopy("2026-07-20T01:00:00Z", now)).toBe("1 month ago");
    expect(sinceCopy("2024-01-01T01:00:00Z", now)).toBe("2 years ago");
  });

  it("returns null for missing or unparseable dates", () => {
    expect(sinceCopy(null, now)).toBeNull();
    expect(sinceCopy("nope", now)).toBeNull();
  });
});

describe("lastLiftCopy", () => {
  it("leads with the lift and its payoff in the lift's own unit", () => {
    expect(lastLiftCopy({ lift_type: "pushup", total_reps: 35, grade: "C", weight: 60, created_at: null })).toBe("Pushup · 35 reps · C");
    expect(lastLiftCopy({ lift_type: "situp", total_reps: 1, grade: "B", weight: 0, created_at: null })).toBe("Situp · 1 rep · B");
    expect(lastLiftCopy({ lift_type: "plank", hold_s: 201.3, grade: null, weight: 60, created_at: null })).toBe("Plank · 3:21");
    expect(lastLiftCopy({ lift_type: "Bench Press", weight: 80, grade: "D", created_at: null })).toBe("Bench press · 80kg · D");
    expect(lastLiftCopy({ lift_type: null, created_at: null })).toBe("Lift");
  });
});
