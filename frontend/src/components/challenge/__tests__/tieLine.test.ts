import { tieLine } from "../ConsistencyMeta";
import { consistencyLeaderboard } from "../../../__fixtures__/consistencyLeaderboard";

const [ana, ben, cy] = consistencyLeaderboard.rows;
const tied = (over: Partial<typeof ben>) => [ana, { ...ben, score: ana.score, ...over }, cy];

describe("tieLine", () => {
  it("is null when no two scored rows share points", () => {
    expect(tieLine(consistencyLeaderboard.rows)).toBeNull();
  });

  it("names the deciding tiebreak in ranking order", () => {
    expect(tieLine(tied({ streak: 1 }))).toBe("Ana and Ben are tied on points; a longer streak puts Ana ahead.");
    expect(tieLine(tied({ streak: ana.streak, weeks_met: (ana.weeks_met ?? 0) - 1 }))).toBe(
      "Ana and Ben are tied on points; more weeks met puts Ana ahead.",
    );
    expect(
      tieLine(tied({ streak: ana.streak, weeks_met: ana.weeks_met, this_week: { ...ben.this_week!, lifts: 10 } })),
    ).toBe("Ana and Ben are tied on points; more lifts this week puts Ana ahead.");
  });

  it("ignores ties at zero points", () => {
    expect(tieLine([ana, { ...ben, score: 0 }, cy])).toBeNull();
  });
});
