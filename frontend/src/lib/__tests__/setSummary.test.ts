import { summarizeSet, aggregateStatus } from "../setSummary";

const metric = (
  key: string,
  value: number,
  status: string,
  label = key.toUpperCase(),
  unit = "%",
  target = ">80%"
) => ({ key, label, value, unit, target, status, description: `about ${key}` });

const rep = (n: number, metrics: ReturnType<typeof metric>[] | null) => ({
  rep_number: n,
  metrics,
});

describe("aggregateStatus", () => {
  it("passes only when every rep passed", () => {
    expect(aggregateStatus(3, 3)).toBe("pass");
    expect(aggregateStatus(2, 3)).toBe("warn");
  });

  it("warns at exactly half", () => {
    expect(aggregateStatus(2, 4)).toBe("warn");
    expect(aggregateStatus(1, 4)).toBe("fail");
  });

  it("fails when no reps passed, and on an empty set", () => {
    expect(aggregateStatus(0, 5)).toBe("fail");
    expect(aggregateStatus(0, 0)).toBe("fail");
  });
});

describe("summarizeSet", () => {
  it("returns [] for empty or missing input", () => {
    expect(summarizeSet([])).toEqual([]);
    expect(summarizeSet(null)).toEqual([]);
    expect(summarizeSet(undefined)).toEqual([]);
  });

  it("averages each metric across reps and counts passes", () => {
    const out = summarizeSet([
      rep(1, [metric("rom", 90, "pass"), metric("control", 40, "fail")]),
      rep(2, [metric("rom", 80, "pass"), metric("control", 60, "warn")]),
    ]);

    expect(out.map((m) => m.key)).toEqual(["rom", "control"]);
    const rom = out[0];
    expect(rom.value).toBe(85);
    expect(rom.passCount).toBe(2);
    expect(rom.repCount).toBe(2);
    expect(rom.status).toBe("pass");

    const control = out[1];
    expect(control.value).toBe(50);
    expect(control.passCount).toBe(0);
    expect(control.status).toBe("fail");
  });

  it("rounds the mean to one decimal", () => {
    const out = summarizeSet([
      rep(1, [metric("rom", 10, "pass")]),
      rep(2, [metric("rom", 11, "pass")]),
      rep(3, [metric("rom", 13, "pass")]),
    ]);
    expect(out[0].value).toBe(11.3);
  });

  it("preserves first-seen metric order and carries label/unit/target through", () => {
    const out = summarizeSet([
      rep(1, [metric("tempo", 2, "pass", "Tempo", ":1", "1.5-2.5:1")]),
      rep(2, [metric("rom", 90, "pass")]),
    ]);
    expect(out.map((m) => m.key)).toEqual(["tempo", "rom"]);
    expect(out[0].label).toBe("Tempo");
    expect(out[0].unit).toBe(":1");
    expect(out[0].target).toBe("1.5-2.5:1");
    expect(out[0].description).toBe("about tempo");
  });

  it("ignores reps with no metrics and non-numeric values", () => {
    const out = summarizeSet([
      rep(1, null),
      rep(2, [metric("rom", 80, "pass")]),
      rep(3, [{ ...metric("rom", NaN, "fail") }]),
    ]);
    expect(out).toHaveLength(1);
    expect(out[0].value).toBe(80);
    expect(out[0].repCount).toBe(1);
  });

  it("handles a metric that only some reps report", () => {
    const out = summarizeSet([
      rep(1, [metric("rom", 80, "pass"), metric("tempo", 2, "pass")]),
      rep(2, [metric("rom", 60, "fail")]),
    ]);
    const tempo = out.find((m) => m.key === "tempo")!;
    expect(tempo.repCount).toBe(1);
    expect(tempo.status).toBe("pass");
    const rom = out.find((m) => m.key === "rom")!;
    expect(rom.repCount).toBe(2);
    expect(rom.status).toBe("warn"); // 1 of 2 passed
  });
});
