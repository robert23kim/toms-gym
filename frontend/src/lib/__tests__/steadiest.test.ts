import { steadiestYet } from "../steadiest";

const rows = [
  { attempt_id: "a1", steadiness: 4.2 },
  { attempt_id: "a2", steadiness: 2.9 },
  { attempt_id: "a3", steadiness: null },
  { attempt_id: "a4", steadiness: 1.8 },
];

describe("steadiestYet", () => {
  it("is true only when this attempt beats every other measured attempt", () => {
    expect(steadiestYet(rows, "a4", 1.8)).toBe(true);
    expect(steadiestYet(rows, "a2", 2.9)).toBe(false);
    expect(steadiestYet(rows, "a4", 3.5)).toBe(false);
  });

  it("needs at least one other measured attempt and a real number", () => {
    expect(steadiestYet([{ attempt_id: "a1", steadiness: 3 }], "a1", 3)).toBe(false);
    expect(steadiestYet([{ attempt_id: "a1", steadiness: null }, { attempt_id: "a9", steadiness: 3 }], "a9", 3)).toBe(false);
    expect(steadiestYet(rows, "a9", null)).toBe(false);
    expect(steadiestYet(rows, "a9", NaN)).toBe(false);
  });
});
