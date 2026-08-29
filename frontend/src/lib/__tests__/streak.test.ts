import { computeStreak, milestoneCopy, milestoneReached } from "../streak";

// Friday 2026-08-28 local time.
const now = new Date(2026, 7, 28, 11, 0);
const local = (y: number, m: number, d: number, h = 12) => new Date(y, m - 1, d, h).toISOString();

describe("computeStreak", () => {
  it("returns zero weeks and an all-inactive strip with no activity", () => {
    const s = computeStreak([], now);
    expect(s.weeks).toBe(0);
    expect(s.week.map((d) => d.label)).toEqual(["M", "T", "W", "T", "F", "S", "S"]);
    expect(s.week.every((d) => !d.active)).toBe(true);
    expect(s.week[4].isToday).toBe(true);
    expect(s.week.filter((d) => d.isFuture).map((d) => d.label)).toEqual(["S", "S"]);
  });

  it("marks this week's active days using local dates", () => {
    const s = computeStreak(
      [
        { at: local(2026, 8, 24), kind: "lift" },
        { at: local(2026, 8, 25, 23), kind: "bowl" },
        { at: local(2026, 8, 27), kind: "golf" },
        { at: local(2026, 8, 28), kind: "lift" },
      ],
      now,
    );
    expect(s.week.map((d) => d.active)).toEqual([true, true, false, true, true, false, false]);
    expect(s.week[0].date.getDate()).toBe(24);
    expect(s.weeks).toBe(1);
  });

  it("counts consecutive weeks ending at the current week", () => {
    const s = computeStreak(
      [
        { at: local(2026, 8, 26), kind: "lift" },
        { at: local(2026, 8, 19), kind: "lift" },
        { at: local(2026, 8, 12), kind: "lift" },
        { at: local(2026, 8, 5), kind: "lift" },
        { at: local(2026, 7, 22), kind: "lift" },
      ],
      now,
    );
    expect(s.weeks).toBe(4);
  });

  it("does not break the streak when the current week is still empty", () => {
    const s = computeStreak(
      [
        { at: local(2026, 8, 19), kind: "lift" },
        { at: local(2026, 8, 12), kind: "lift" },
      ],
      now,
    );
    expect(s.weeks).toBe(2);
  });

  it("breaks the streak when the previous week was empty too", () => {
    const s = computeStreak([{ at: local(2026, 8, 12), kind: "lift" }], now);
    expect(s.weeks).toBe(0);
  });

  it("ignores unparseable timestamps", () => {
    const s = computeStreak([{ at: "nope", kind: "lift" }], now);
    expect(s.weeks).toBe(0);
  });
});

describe("milestoneReached", () => {
  it("returns the highest uncelebrated milestone at or below the streak", () => {
    expect(milestoneReached(1, 0)).toBeNull();
    expect(milestoneReached(2, 0)).toBe(2);
    expect(milestoneReached(5, 0)).toBe(4);
    expect(milestoneReached(5, 4)).toBeNull();
    expect(milestoneReached(9, 4)).toBe(8);
    expect(milestoneReached(52, 26)).toBe(52);
  });

  it("has a line for every milestone", () => {
    expect(milestoneCopy(2)).toMatch(/Two weeks/);
    expect(milestoneCopy(4)).toMatch(/Four weeks/);
    expect(milestoneCopy(52)).toMatch(/year/);
    expect(milestoneCopy(7)).toBe("7 weeks straight.");
  });
});
