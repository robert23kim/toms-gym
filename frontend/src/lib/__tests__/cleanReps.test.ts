import { boardReps, cleanRepCount, isQualityScoredLift, CLEAN_REP_MIN_FORM } from "../cleanReps";

const reps = (...scores: (number | null)[]) => scores.map((form_score) => ({ form_score }));

describe("cleanReps", () => {
  test("only situps are quality-scored", () => {
    expect(isQualityScoredLift("situp")).toBe(true);
    expect(isQualityScoredLift("Situp")).toBe(true);
    expect(isQualityScoredLift("pushup")).toBe(false);
    expect(isQualityScoredLift(null)).toBe(false);
  });

  test("counts reps at or above the bar; null without per-rep scores", () => {
    expect(cleanRepCount(reps(90, CLEAN_REP_MIN_FORM, 69.9, null))).toBe(2);
    expect(cleanRepCount([])).toBeNull();
    expect(cleanRepCount(undefined)).toBeNull();
  });

  test("a situp scores clean reps in full and sloppy reps at half", () => {
    const metrics = reps(95, 80, 40, 72);
    expect(boardReps({ lift_type: "situp", total_reps: 4, rep_metrics: metrics })).toBe(3.5);
    expect(boardReps({ lift_type: "pushup", total_reps: 4, rep_metrics: metrics })).toBe(4);
  });

  test("a situp without per-rep scores falls back to its raw count", () => {
    expect(boardReps({ lift_type: "situp", total_reps: 0, rep_metrics: [] })).toBe(0);
    expect(boardReps({ lift_type: "situp", total_reps: 6 })).toBe(6);
    expect(boardReps({ lift_type: "situp", total_reps: null })).toBeNull();
    expect(boardReps(null)).toBeNull();
  });
});
