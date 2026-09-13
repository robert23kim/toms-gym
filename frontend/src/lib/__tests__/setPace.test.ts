import { setPace } from "../setPace";

const rep = (start: number, peak: number, end: number, form: number | null = 80) => ({
  start_s: start,
  peak_s: peak,
  end_s: end,
  form_score: form,
});

describe("setPace", () => {
  it("returns null for missing input or fewer than 3 timed reps", () => {
    expect(setPace(null)).toBeNull();
    expect(setPace(undefined)).toBeNull();
    expect(setPace([])).toBeNull();
    expect(setPace([rep(0, 1, 2), rep(2, 3, 4)])).toBeNull();
  });

  it("ignores reps without timing (old reports)", () => {
    expect(setPace([{ form_score: 90 }, { form_score: 90 }, rep(0, 1, 2), rep(2, 3, 4)])).toBeNull();
    const out = setPace([{ form_score: 10 }, rep(0, 1, 2), rep(2, 3, 4), rep(4, 5, 6)]);
    expect(out?.reps).toBe(3);
  });

  it("returns null when the set has no duration", () => {
    expect(setPace([rep(5, 5, 5), rep(5, 5, 5), rep(5, 5, 5)])).toBeNull();
  });

  it("computes duration, pace and rep lengths", () => {
    const out = setPace([rep(1, 2, 3), rep(3, 4, 5.5), rep(5.5, 6, 7)])!;
    expect(out.reps).toBe(3);
    expect(out.durationS).toBe(6);
    expect(out.repsPerMinute).toBe(30);
    expect(out.fastestRepS).toBe(1.5);
    expect(out.slowestRepS).toBe(2.5);
  });

  it("rounds pace to one decimal", () => {
    // 3 reps in 7s = 25.714... rpm
    expect(setPace([rep(0, 1, 2), rep(2, 3, 4), rep(4, 5, 7)])!.repsPerMinute).toBe(25.7);
  });

  it("sorts reps by start time before measuring the set", () => {
    const out = setPace([rep(9, 10, 11.5), rep(0, 1, 2), rep(4, 5, 6)])!;
    expect(out.durationS).toBe(11.5);
    expect(out.slowestRepS).toBe(2.5);
    expect(out.thirds.map((t) => t.reps)).toEqual([1, 1, 1]);
  });

  it("splits reps into equal-time thirds by peak, boundary peaks going later", () => {
    // Set spans 0..9 → windows [0,3) [3,6) [6,9].
    const out = setPace([
      rep(0, 1, 2, 90),
      rep(2, 2.9, 3, 80),
      rep(3, 3, 4, 70), // exactly on the 3s boundary → middle
      rep(4, 6, 7, 51), // exactly on the 6s boundary → end
      rep(7, 9, 9, 50), // on the set end → end
    ])!;
    expect(out.thirds).toEqual([
      { reps: 2, avgForm: 85 },
      { reps: 1, avgForm: 70 },
      { reps: 2, avgForm: 51 },
    ]);
  });

  it("reports an empty third with null form and skips null form scores", () => {
    const out = setPace([rep(0, 1, 2, null), rep(2, 2.5, 3, 60), rep(8, 8.5, 9, 75)])!;
    expect(out.thirds).toEqual([
      { reps: 2, avgForm: 60 },
      { reps: 0, avgForm: null },
      { reps: 1, avgForm: 75 },
    ]);
  });

  it("counts the best run of consecutive reps at or above the clean bar", () => {
    const forms = [69.9, 70, 70, 70, 10, 90, 90, null, 100];
    const out = setPace(forms.map((f, i) => rep(i, i + 0.5, i + 1, f)))!;
    expect(out.bestCleanStreak).toBe(3);
  });

  it("scores a streak of zero when no rep is clean", () => {
    const out = setPace([rep(0, 1, 2, 10), rep(2, 3, 4, 69), rep(4, 5, 6, null)])!;
    expect(out.bestCleanStreak).toBe(0);
  });
});
