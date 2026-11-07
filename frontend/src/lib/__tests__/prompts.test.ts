import { consistencyPill } from "../prompts";
import {
  consistencyLeaderboard,
  endedConsistencyLeaderboard,
  upcomingConsistencyLeaderboard,
} from "../../__fixtures__/consistencyLeaderboard";
import { buildPrompts, quickLiftType } from "../prompts";

describe("quickLiftType", () => {
  it("accepts a single bodyweight lift alongside gender and weight-class categories", () => {
    expect(quickLiftType(["Situp"])).toBe("Situp");
    expect(quickLiftType(["Situp", "Men", "Women"])).toBe("Situp");
    expect(quickLiftType(["Plank", "Open", "Men"])).toBe("Plank");
  });
  it("refuses weighted, multi-category or empty challenges", () => {
    expect(quickLiftType(["Squat"])).toBeNull();
    expect(quickLiftType(["Squat", "Men", "Women"])).toBeNull();
    expect(quickLiftType(["Situp", "Pushup", "Men"])).toBeNull();
    expect(quickLiftType([])).toBeNull();
    expect(quickLiftType(undefined)).toBeNull();
  });
});

describe("buildPrompts", () => {
  it("leads with the recap and single-game camera rows and ends with golf and lift", () => {
    const prompts = buildPrompts([]);
    expect(prompts.map((p) => p.id)).toEqual(["bowl-snap", "game-snap", "golf-snap", "lift-upload"]);
    expect(prompts[0]).toEqual({
      id: "bowl-snap",
      kind: "camera",
      title: "Snap tonight's bowling recap",
      sheetType: "night",
      fallbackTo: "/bowling/snap",
    });
    expect(prompts[1]).toEqual({
      id: "game-snap",
      kind: "camera",
      title: "Snap a bowling game",
      sheetType: "game",
      fallbackTo: "/bowling/snap",
    });
    expect(prompts[2]).toMatchObject({ kind: "link", to: "/golf/snap" });
    expect(prompts[3]).toMatchObject({ kind: "link", to: "/lift/upload" });
  });

  it("drops the bowling and golf rows when sports is off", () => {
    const prompts = buildPrompts([{ id: "c1", title: "Situp challenge", categories: ["Situp"] }], {}, { sports: false });
    expect(prompts.map((p) => p.id)).toEqual(["challenge:c1", "lift-upload"]);
  });

  it("makes a bodyweight challenge a video row with its lift type preset", () => {
    const prompts = buildPrompts([{ id: "c1", title: "Situp challenge", categories: ["Situp"] }]);
    expect(prompts[2]).toEqual({
      id: "challenge:c1",
      kind: "video",
      title: "Situp challenge",
      pill: "Situp",
      competitionId: "c1",
      liftType: "Situp",
      fallbackTo: "/challenges/c1",
    });
  });

  it("links weighted challenges to the challenge page, never the bare upload form", () => {
    const prompts = buildPrompts([{ id: "c2", title: "Squat-off", categories: ["Squat"] }]);
    expect(prompts[2]).toEqual({ id: "challenge:c2", kind: "link", title: "Squat-off", to: "/challenges/c2", pill: "Squat" });
    expect(prompts).toHaveLength(5);
  });
});


describe("100 Club home row", () => {
  const club = {
    id: "club-100",
    title: "The 100 Club",
    categories: ["Situp", "Pushup", "Squat", "Plank", "Men", "Women"],
    mode: "consistency",
  };

  it("reads the viewer's week progress and days left off the board", () => {
    expect(consistencyPill(consistencyLeaderboard, "a1")).toBe("42 / 150 · 4 days left");
    expect(consistencyPill(consistencyLeaderboard, "b1")).toBe("10 / 125 · 4 days left");
    expect(consistencyPill(consistencyLeaderboard, "c1")).toBe("0 / 100 · 4 days left");
  });

  it("says one day on the last day of the week", () => {
    const sunday = { ...consistencyLeaderboard, consistency: { ...consistencyLeaderboard.consistency!, days_left: 1 } };
    expect(consistencyPill(sunday, "a1")).toBe("42 / 150 · 1 day left");
  });

  it("says Starts Mon before week 1 and nothing after the end", () => {
    expect(consistencyPill(upcomingConsistencyLeaderboard, "a1")).toBe("Starts Mon");
    expect(consistencyPill(endedConsistencyLeaderboard, "a1")).toBeNull();
  });

  it("gives anonymous visitors and non-entrants no progress pill", () => {
    expect(consistencyPill(consistencyLeaderboard, null)).toBeNull();
    expect(consistencyPill(consistencyLeaderboard, "stranger")).toBeNull();
  });

  it("is a link row to the challenge page carrying the progress pill", () => {
    const prompts = buildPrompts([club], { "club-100": "42 / 150 · 4 days left" });
    expect(prompts[2]).toEqual({
      id: "challenge:club-100",
      kind: "link",
      title: "The 100 Club",
      to: "/challenges/club-100",
      pill: "42 / 150 · 4 days left",
    });
  });

  it("is a plain link row with no pill for anonymous visitors, never the bare upload route", () => {
    const prompts = buildPrompts([club]);
    expect(prompts[2]).toEqual({ id: "challenge:club-100", kind: "link", title: "The 100 Club", to: "/challenges/club-100", pill: undefined });
  });

  it("stays a link row even if the club only listed one bodyweight lift", () => {
    const prompts = buildPrompts([{ ...club, categories: ["Situp"] }]);
    expect(prompts[2]).toMatchObject({ kind: "link", to: "/challenges/club-100" });
  });
});
