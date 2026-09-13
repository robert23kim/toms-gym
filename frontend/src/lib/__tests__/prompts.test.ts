import { buildPrompts, quickLiftType } from "../prompts";

describe("quickLiftType", () => {
  it("accepts a single bodyweight category", () => {
    expect(quickLiftType(["Situp"])).toBe("Situp");
    expect(quickLiftType(["Plank"])).toBe("Plank");
  });
  it("refuses weighted, multi-category or empty challenges", () => {
    expect(quickLiftType(["Squat"])).toBeNull();
    expect(quickLiftType(["Situp", "Pushup"])).toBeNull();
    expect(quickLiftType([])).toBeNull();
    expect(quickLiftType(undefined)).toBeNull();
  });
});

describe("buildPrompts", () => {
  it("leads with the bowling camera row and ends with golf and lift", () => {
    const prompts = buildPrompts([]);
    expect(prompts.map((p) => p.id)).toEqual(["bowl-snap", "golf-snap", "lift-upload"]);
    expect(prompts[0]).toEqual({
      id: "bowl-snap",
      kind: "camera",
      title: "Snap tonight's scores",
      fallbackTo: "/bowling/snap",
    });
    expect(prompts[1]).toMatchObject({ kind: "link", to: "/golf/snap" });
    expect(prompts[2]).toMatchObject({ kind: "link", to: "/lift/upload" });
  });

  it("makes a bodyweight challenge a video row with its lift type preset", () => {
    const prompts = buildPrompts([{ id: "c1", title: "Situp challenge", categories: ["Situp"] }]);
    expect(prompts[1]).toEqual({
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
    expect(prompts[1]).toEqual({ id: "challenge:c2", kind: "link", title: "Squat-off", to: "/challenges/c2", pill: "Squat" });
    expect(prompts).toHaveLength(4);
  });
});
