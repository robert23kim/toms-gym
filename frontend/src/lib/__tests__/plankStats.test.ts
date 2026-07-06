import {
  holdRuns,
  steadinessScore,
  wobbleEvents,
  decayPoint,
  milestones,
  personality,
} from "../plankStats";
import { PlankPerSecond } from "../types";

const sec = (
  t: number,
  state: string,
  body_line_deg: number,
  form_score: number,
  elbow_deg = 90
): PlankPerSecond => ({ t, state, body_line_deg, elbow_deg, form_score });

/** n seconds of rock-steady in_plank hold starting at t0. */
const flat = (n: number, t0 = 0, deg = 175, form = 0.95): PlankPerSecond[] =>
  Array.from({ length: n }, (_, i) => sec(t0 + i, "in_plank", deg, form));

describe("holdRuns", () => {
  it("finds contiguous in_plank runs and flags the longest", () => {
    const ps = [
      ...flat(5, 0), // run 1: 0-4 (5s)
      sec(5, "no_pose", NaN, 0),
      sec(6, "settling", 170, 0.3),
      ...flat(10, 7), // run 2: 7-16 (10s) — longest
    ];
    const runs = holdRuns(ps);
    expect(runs).toHaveLength(2);
    expect(runs[0]).toMatchObject({ start: 0, end: 4, duration: 5, longest: false });
    expect(runs[1]).toMatchObject({ start: 7, end: 16, duration: 10, longest: true });
  });

  it("returns [] for empty input", () => {
    expect(holdRuns([])).toEqual([]);
  });
});

describe("steadinessScore", () => {
  it("maps stdev to a clamped 0-100 score with tier labels", () => {
    expect(steadinessScore(0)).toEqual({ score: 100, label: "Rock Solid" });
    expect(steadinessScore(1)).toEqual({ score: 90, label: "Rock Solid" });
    expect(steadinessScore(2.09)).toEqual({ score: 79, label: "Steady" });
    expect(steadinessScore(4)).toEqual({ score: 60, label: "Wobbly" });
    expect(steadinessScore(6)).toEqual({ score: 40, label: "Jelly Mode" });
    expect(steadinessScore(20)).toEqual({ score: 0, label: "Jelly Mode" });
  });

  it("returns null for missing/NaN stdev", () => {
    expect(steadinessScore(undefined)).toBeNull();
    expect(steadinessScore(null)).toBeNull();
    expect(steadinessScore(NaN)).toBeNull();
  });
});

describe("wobbleEvents", () => {
  it("detects >2.5° jumps between consecutive in_plank seconds", () => {
    const ps = [
      sec(0, "in_plank", 175, 0.9),
      sec(1, "in_plank", 175.5, 0.9), // Δ0.5 — no
      sec(2, "in_plank", 179, 0.8), // Δ3.5 — wobble
      sec(3, "in_plank", 179.2, 0.85),
      sec(4, "in_plank", 175, 0.9), // Δ4.2 — wobble, within 2s of t=2 → merged
    ];
    const events = wobbleEvents(ps);
    expect(events).toHaveLength(1);
    // merged event keeps the larger delta's timestamp and value (spec rule)
    expect(events[0].t).toBe(4);
    expect(events[0].delta).toBeCloseTo(4.2, 1);
  });

  it("ignores jumps involving non-plank seconds and NaN angles", () => {
    const ps = [
      sec(0, "in_plank", 175, 0.9),
      sec(1, "no_pose", NaN, 0),
      sec(2, "in_plank", 165, 0.9), // big jump vs t=0 but t=1 breaks adjacency
    ];
    expect(wobbleEvents(ps)).toEqual([]);
  });

  it("merges adjacent events keeping the larger delta", () => {
    const ps = [
      sec(0, "in_plank", 170, 0.9),
      sec(1, "in_plank", 173, 0.9), // Δ3 wobble
      sec(2, "in_plank", 178, 0.9), // Δ5 wobble, adjacent → merged, keeps t=2
    ];
    const events = wobbleEvents(ps);
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ t: 2, delta: 5 });
  });
});

describe("decayPoint", () => {
  it("returns the start of the first ≥5s sustained sub-0.7 form window", () => {
    const ps = [
      ...flat(10, 0, 175, 0.9),
      ...Array.from({ length: 6 }, (_, i) => sec(10 + i, "in_plank", 172, 0.55)),
    ];
    expect(decayPoint(ps)).toBe(10);
  });

  it("ignores brief dips shorter than 5s", () => {
    const ps = [
      ...flat(10, 0, 175, 0.9),
      ...Array.from({ length: 3 }, (_, i) => sec(10 + i, "in_plank", 172, 0.5)),
      ...flat(10, 13, 175, 0.9),
    ];
    expect(decayPoint(ps)).toBeNull();
  });

  it("returns null when form never decays or input empty", () => {
    expect(decayPoint(flat(30))).toBeNull();
    expect(decayPoint([])).toBeNull();
  });
});

describe("milestones", () => {
  it("marks reached milestones with the video time of crossing (cumulative hold time)", () => {
    // 10s settling first, then 70s of holding: 30s milestone crossed at video t = 10+29
    const ps = [
      ...Array.from({ length: 10 }, (_, i) => sec(i, "settling", 170, 0.3)),
      ...flat(70, 10),
    ];
    const ms = milestones(ps);
    expect(ms).toHaveLength(4);
    expect(ms[0]).toMatchObject({ label: "0:30", reached: true, t: 39 });
    expect(ms[1]).toMatchObject({ label: "1:00", reached: true, t: 69 });
    expect(ms[2]).toMatchObject({ label: "2:00", reached: false, t: null });
    expect(ms[3]).toMatchObject({ label: "3:00", reached: false, t: null });
  });

  it("handles empty input", () => {
    expect(milestones([])).toEqual([
      { label: "0:30", t: null, reached: false },
      { label: "1:00", t: null, reached: false },
      { label: "2:00", t: null, reached: false },
      { label: "3:00", t: null, reached: false },
    ]);
  });
});

describe("personality", () => {
  it("returns null with fewer than 10 in_plank seconds", () => {
    expect(personality(flat(5), 1)).toBeNull();
    expect(personality([], 1)).toBeNull();
  });

  it("Statue: low stdev, ≤1 wobble", () => {
    const p = personality(flat(60), 0.8);
    expect(p?.key).toBe("statue");
  });

  it("Jelly: ≥4 wobbles or stdev > 4", () => {
    // alternating angles → many wobbles
    const ps = Array.from({ length: 40 }, (_, i) =>
      sec(i, "in_plank", i % 2 ? 170 : 176, 0.7)
    );
    expect(personality(ps, 3)?.key).toBe("jelly");
    expect(personality(flat(40), 5)?.key).toBe("jelly");
  });

  it("Slow Melter: steadily declining form", () => {
    const ps = Array.from({ length: 60 }, (_, i) =>
      sec(i, "in_plank", 175, 0.95 - i * 0.005)
    );
    expect(personality(ps, 2)?.key).toBe("melter");
  });

  it("Phoenix: dip then recovery", () => {
    const ps = [
      ...flat(20, 0, 175, 0.9),
      ...Array.from({ length: 8 }, (_, i) => sec(20 + i, "in_plank", 175, 0.6)), // dip
      ...flat(20, 28, 175, 0.92), // recovery
    ];
    expect(personality(ps, 2)?.key).toBe("phoenix");
  });

  it("Steady Eddie: fallback", () => {
    // mild stdev (no statue), no wobbles, flat form (no melter/phoenix)
    const p = personality(flat(60), 2.5);
    expect(p?.key).toBe("eddie");
  });
});
