import { compareThrow, throwComparisonCopy } from "../throwCompare";

const rows = [
  { attempt_id: "t1", created_at: "2026-02-21 16:39:44+00:00", entry_board: 31 },
  { attempt_id: "t2", created_at: "2026-02-21 16:49:34+00:00", entry_board: null },
  { attempt_id: "t3", created_at: "2026-02-26 13:19:31+00:00", entry_board: 28 },
];

describe("compareThrow", () => {
  it("compares with the most recent earlier throw that was tracked, skipping untracked ones", () => {
    expect(compareThrow(rows, "t3", 28)).toEqual({ previousBoard: 31, delta: -3 });
  });

  it("is null for the first tracked throw, an unknown attempt, or no entry board", () => {
    expect(compareThrow(rows, "t1", 31)).toBeNull();
    expect(compareThrow(rows, "zzz", 20)).toBeNull();
    expect(compareThrow(rows, "t3", null)).toBeNull();
  });

  it("writes the copy in boards, with direction", () => {
    expect(throwComparisonCopy({ previousBoard: 31, delta: -3 })).toBe("3 boards left of your last throw (31)");
    expect(throwComparisonCopy({ previousBoard: 27, delta: 1 })).toBe("1 board right of your last throw (27)");
    expect(throwComparisonCopy({ previousBoard: 28, delta: 0 })).toBe("Same board as your last throw (28)");
  });
});
