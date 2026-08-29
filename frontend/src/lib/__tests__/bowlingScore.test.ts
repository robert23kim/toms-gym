import {
  framePins,
  scoreFrames,
  parseFrameInput,
  formatFrameInput,
  InvalidFrame,
  Roll,
} from "../bowlingScore";

const PERFECT: Roll[][] = [
  ...Array.from({ length: 9 }, () => ["X"]),
  ["X", "X", "X"],
];
const GUTTER: Roll[][] = Array.from({ length: 10 }, () => ["-", "-"]);
const ALL_NINE_SPARE: Roll[][] = [
  ...Array.from({ length: 9 }, () => ["9", "/"]),
  ["9", "/", "9"],
];
const TOM: Roll[][] = [
  ["X"], ["8", "1"], ["X"], ["9", "/"], ["X"],
  ["6", "3"], ["8", "/"], ["X"], ["9", "-"], ["7", "/", "9"],
];
const CHRIS: Roll[][] = [
  ["X"], ["9", "-"], ["X"], ["8", "-"], ["X"],
  ["9", "/"], ["9", "/"], ["9", "/"], ["X"], ["X", "8", "-"],
];

const nineGutters = (tenth: Roll[]): Roll[][] => [
  ...Array.from({ length: 9 }, () => ["-", "-"]),
  tenth,
];

describe("scoreFrames", () => {
  it("scores a perfect game", () => {
    const r = scoreFrames(PERFECT);
    expect(r.total).toBe(300);
    expect(r.valid).toBe(true);
    expect(r.complete).toBe(true);
    expect(r.cumulative).toEqual([30, 60, 90, 120, 150, 180, 210, 240, 270, 300]);
  });

  it("scores a gutter game", () => {
    expect(scoreFrames(GUTTER).total).toBe(0);
  });

  it("scores an all-nine-spare game", () => {
    expect(scoreFrames(ALL_NINE_SPARE).total).toBe(190);
  });

  it("matches the fixture rows", () => {
    expect(scoreFrames(TOM).cumulative).toEqual([19, 28, 48, 68, 87, 96, 116, 135, 144, 163]);
    expect(scoreFrames(CHRIS).cumulative).toEqual([19, 28, 46, 54, 74, 93, 112, 132, 160, 178]);
  });

  it("handles every tenth-frame variant", () => {
    expect(scoreFrames(nineGutters(["X", "X", "X"])).total).toBe(30);
    expect(scoreFrames(nineGutters(["X", "9", "/"])).total).toBe(20);
    expect(scoreFrames(nineGutters(["9", "/", "X"])).total).toBe(20);
    expect(scoreFrames(nineGutters(["9", "-"])).total).toBe(9);
  });

  it("flags invalid frames instead of throwing", () => {
    const r = scoreFrames([["9", "9"], ...Array.from({ length: 9 }, () => ["-", "-"])]);
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toContain("frame 1");
  });

  it("scores a partial game and reports it incomplete", () => {
    const r = scoreFrames([["X"], ["9", "/"]]);
    expect(r.complete).toBe(false);
    expect(r.cumulative).toEqual([20, 30]);
  });

  it("treats an empty frame list as a zero game", () => {
    const r = scoreFrames([]);
    expect(r.cumulative).toEqual([]);
    expect(r.total).toBe(0);
    expect(r.complete).toBe(false);
  });
});

describe("framePins", () => {
  it("counts a foul as zero", () => {
    expect(framePins(["F", "9"], 0)).toEqual([0, 9]);
  });

  it("counts a blank symbol as zero", () => {
    expect(framePins(["-", " "], 0)).toEqual([0, 0]);
  });

  it("resolves a spare against the first ball", () => {
    expect(framePins(["3", "/"], 5)).toEqual([3, 7]);
  });

  it("rejects a third ball before the tenth", () => {
    expect(() => framePins(["9", "-", "5"], 3)).toThrow(InvalidFrame);
  });

  it("rejects a two-ball frame that exceeds the rack", () => {
    expect(() => framePins(["9", "9"], 2)).toThrow(/exceeds 10/);
  });

  it("rejects a lone open first ball", () => {
    expect(() => framePins(["7"], 2)).toThrow(InvalidFrame);
  });

  it("rejects a ball thrown after a strike outside the tenth", () => {
    expect(() => framePins(["X", "5"], 2)).toThrow(InvalidFrame);
  });

  it("requires the tenth-frame bonus ball after a strike or spare", () => {
    expect(() => framePins(["X", "X"], 9)).toThrow(/bonus ball/);
    expect(() => framePins(["9", "/"], 9)).toThrow(/bonus ball/);
  });

  it("rejects a third ball in an open tenth frame", () => {
    expect(() => framePins(["7", "1", "5"], 9)).toThrow(/extra ball/);
  });

  it("resets the rack after a tenth-frame strike", () => {
    expect(framePins(["X", "9", "/"], 9)).toEqual([10, 9, 1]);
    expect(framePins(["9", "/", "X"], 9)).toEqual([9, 1, 10]);
  });

  it("rejects unknown symbols and out-of-range counts", () => {
    expect(() => framePins(["Q", "1"], 0)).toThrow(/unknown symbol/);
    expect(() => framePins(["/", "1"], 0)).toThrow(/no first ball/);
  });

  it("rejects an empty frame", () => {
    expect(() => framePins([], 0)).toThrow(/empty frame/);
  });
});

describe("frame input helpers", () => {
  it("splits a typed cell into roll symbols", () => {
    expect(parseFrameInput("9/", 0)).toEqual(["9", "/"]);
    expect(parseFrameInput("x", 0)).toEqual(["X"]);
    expect(parseFrameInput("X X 8", 9)).toEqual(["X", "X", "8"]);
    expect(parseFrameInput("XX8", 2)).toEqual(["X", "X"]);
  });

  it("round-trips roll symbols back into a cell string", () => {
    expect(formatFrameInput(["9", "/"])).toBe("9/");
    expect(formatFrameInput(null)).toBe("");
  });
});
