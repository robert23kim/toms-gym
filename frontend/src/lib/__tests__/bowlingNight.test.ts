import { summarizeNight } from "../bowlingNight";

const g = (sheet_id: string, played_on: string, total_score: number | null) => ({ sheet_id, played_on, total_score });

const history = [
  g("s1", "2026-07-10", 205),
  g("s1", "2026-07-10", 150),
  g("s2", "2026-08-01", 160),
  g("s2", "2026-08-01", 171),
  g("s3", "2026-08-29", 202),
  g("s3", "2026-08-29", 157),
  g("s3", "2026-08-29", 148),
];

describe("summarizeNight", () => {
  it("summarises the confirmed sheet against every other night", () => {
    const n = summarizeNight(history, "s3")!;
    expect(n).toMatchObject({ playedOn: "2026-08-29", count: 3, avg: 169, high: 202 });
    expect(n.priorAvg).toBeCloseTo(171.5, 1);
    expect(n.delta).toBeCloseTo(-2.5, 1);
    expect(n.bestSince).toEqual({ kind: "since", date: "2026-07-10" });
  });

  it("calls a high game the best yet when nothing earlier beats it", () => {
    const n = summarizeNight([...history, g("s4", "2026-09-05", 231)], "s4")!;
    expect(n.bestSince).toEqual({ kind: "best-yet" });
    expect(n.delta).toBeCloseTo(231 - 170.4, 1);
  });

  it("treats the only night on record as the first", () => {
    const n = summarizeNight(history.filter((x) => x.sheet_id === "s3"), "s3")!;
    expect(n).toMatchObject({ priorAvg: null, delta: null, bestSince: { kind: "first" } });
  });

  it("ignores unscored games and hides without a sheet", () => {
    expect(summarizeNight(history, null)).toBeNull();
    expect(summarizeNight([g("s9", "2026-09-01", null)], "s9")).toBeNull();
    expect(summarizeNight([g("s9", "2026-09-01", null), g("s9", "2026-09-01", 180)], "s9")!.count).toBe(1);
  });
});
