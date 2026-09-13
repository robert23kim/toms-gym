import { buildPrompts } from "../prompts";

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

  it("puts one upload row per open challenge after the bowling row", () => {
    const prompts = buildPrompts([
      { id: "c1", title: "Situps", categories: ["Situp"] },
      { id: "c2", title: "Plank", categories: [] },
    ]);
    expect(prompts[1]).toEqual({ id: "challenge:c1", kind: "link", title: "Situps", to: "/challenges/c1/upload", pill: "Situp" });
    expect(prompts[2]).toMatchObject({ id: "challenge:c2", to: "/challenges/c2/upload", pill: undefined });
    expect(prompts).toHaveLength(5);
  });
});
