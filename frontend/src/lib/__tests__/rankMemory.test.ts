import { rankChange, readRank, writeRank } from "../rankMemory";

const memory = () => {
  const store = new Map<string, string>();
  return {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
  };
};

describe("rankMemory", () => {
  it("round-trips a snapshot per challenge and user", () => {
    const s = memory();
    writeRank(s, "c1", "u1", { rank: 4, best: 20, at: "2026-08-20T00:00:00Z" });
    expect(readRank(s, "c1", "u1")).toEqual({ rank: 4, best: 20, at: "2026-08-20T00:00:00Z" });
    expect(readRank(s, "c1", "u2")).toBeNull();
    expect(readRank(s, "c2", "u1")).toBeNull();
  });

  it("ignores corrupt or partial entries and swallows storage failures", () => {
    const s = memory();
    s.setItem("rank:c1:u1", "{not json");
    expect(readRank(s, "c1", "u1")).toBeNull();
    s.setItem("rank:c1:u1", JSON.stringify({ rank: "2" }));
    expect(readRank(s, "c1", "u1")).toBeNull();
    const broken = { getItem: () => { throw new Error("no"); }, setItem: () => { throw new Error("no"); } };
    expect(readRank(broken, "c1", "u1")).toBeNull();
    expect(() => writeRank(broken, "c1", "u1", { rank: 1, best: 1, at: "" })).not.toThrow();
  });

  it("reports a move up, a slip, or nothing", () => {
    expect(rankChange({ rank: 4, best: 20, at: "" }, { rank: 2 })).toEqual({ kind: "up", from: 4, to: 2 });
    expect(rankChange({ rank: 2, best: 35, at: "" }, { rank: 3 })).toEqual({ kind: "down", from: 2, to: 3 });
    expect(rankChange({ rank: 2, best: 35, at: "" }, { rank: 2 })).toBeNull();
    expect(rankChange(null, { rank: 2 })).toBeNull();
  });
});
