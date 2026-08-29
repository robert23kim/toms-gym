jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
import {
  championTally,
  dynastyLabel,
  marginCopy,
  reignDays,
  groupByYear,
  ordinalWin,
} from "../championStats";
import { Champion } from "../api";

const champ = (over: Partial<Champion>): Champion => ({
  user_id: "u1",
  name: "wonder725",
  competition_id: "c1",
  competition_name: "Summer plank challenge",
  metric: "time",
  score: 275.4,
  ended_on: "2026-07-31",
  attempt_id: "a1",
  ...over,
});

describe("championTally", () => {
  it("counts wins per athlete, most wins first then most recent", () => {
    const tally = championTally([
      champ({ user_id: "u1", ended_on: "2026-07-31" }),
      champ({ user_id: "u2", name: "Toka", competition_id: "c2", ended_on: "2026-04-04" }),
      champ({ user_id: "u2", name: "Toka", competition_id: "c3", ended_on: "2026-02-04" }),
    ]);
    expect(tally.map((t) => [t.user_id, t.wins])).toEqual([["u2", 2], ["u1", 1]]);
    expect(tally[0].latest.competition_id).toBe("c2");
  });
});

describe("dynastyLabel", () => {
  it.each([
    [1, null],
    [2, "Back-to-back champion"],
    [3, "Three-peat"],
    [5, "5× champion"],
  ])("wins=%s → %s", (wins, label) => {
    expect(dynastyLabel(wins)).toBe(label);
  });
});

describe("ordinalWin", () => {
  it("numbers an athlete's wins oldest-first", () => {
    const list = [
      champ({ competition_id: "new", ended_on: "2026-07-31", user_id: "u2" }),
      champ({ competition_id: "old", ended_on: "2026-02-04", user_id: "u2" }),
    ];
    expect(ordinalWin(list, list[0])).toBe(2);
    expect(ordinalWin(list, list[1])).toBe(1);
  });
});

describe("marginCopy", () => {
  it("is null when unopposed", () => {
    expect(marginCopy(champ({ margin: null, runners_up: [] }))).toBeNull();
  });
  it("describes a time win in m:ss", () => {
    expect(
      marginCopy(
        champ({ margin: 30.5, runners_up: [{ name: "victoria", user_id: "u2", score: 244.9 }] })
      )
    ).toBe("Won by 0:30 over victoria");
  });
  it("calls a tiny weight margin a photo finish", () => {
    expect(
      marginCopy(
        champ({
          metric: "weight",
          score: 115,
          margin: 2.5,
          runners_up: [{ name: "Sam", user_id: "u2", score: 112.5 }],
        })
      )
    ).toBe("Edged out Sam by 2.5 kg — a photo finish");
  });
  it("describes reps", () => {
    expect(
      marginCopy(
        champ({ metric: "reps", score: 40, margin: 12, runners_up: [{ name: "Sam", user_id: "u2", score: 28 }] })
      )
    ).toBe("Won by 12 reps over Sam");
  });
});

describe("reignDays", () => {
  it("counts whole days since the challenge ended", () => {
    expect(reignDays("2026-07-31", new Date("2026-08-28T12:00:00"))).toBe(28);
  });
});

describe("groupByYear", () => {
  it("buckets champions by ended_on year, newest year first", () => {
    const g = groupByYear([
      champ({ ended_on: "2025-12-01", competition_id: "a" }),
      champ({ ended_on: "2026-07-31", competition_id: "b" }),
    ]);
    expect(g.map(([y, cs]) => [y, cs.length])).toEqual([[2026, 1], [2025, 1]]);
  });
});
