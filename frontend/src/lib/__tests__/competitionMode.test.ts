import { transformCompetitionData } from "../api";
import { consistencyRules } from "../../__fixtures__/consistencyLeaderboard";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

const meta = { lifttypes: ["Situp", "Pushup", "Squat", "Plank"], weightclasses: [], gender: "", mode: "consistency", rules: consistencyRules };

describe("transformCompetitionData mode/rules", () => {
  it("parses mode and rules from the description metadata (list endpoint)", () => {
    const c = transformCompetitionData({
      id: "club-100",
      name: "The 100 Club",
      start_date: "2026-10-31",
      end_date: "2026-12-27",
      description: `100 lifts a week. - ${JSON.stringify(meta)}`,
    });
    expect(c.mode).toBe("consistency");
    expect(c.rules).toEqual(consistencyRules);
    expect(c.categories.slice(0, 4)).toEqual(["Situp", "Pushup", "Squat", "Plank"]);
  });

  it("reads flattened mode and rules (detail endpoint)", () => {
    const c = transformCompetitionData({ id: "club-100", name: "x", start_date: "2026-10-31", end_date: "2026-12-27", ...meta, description: "100 lifts a week." });
    expect(c.mode).toBe("consistency");
    expect(c.rules?.ramp).toBe(25);
  });

  it("leaves legacy challenges without a mode", () => {
    const c = transformCompetitionData({
      id: "c1",
      name: "Plank",
      start_date: "2026-07-01",
      end_date: "2026-07-31",
      description: `Hold it. - ${JSON.stringify({ lifttypes: ["Plank"], weightclasses: [], gender: "" })}`,
    });
    expect(c.mode).toBeUndefined();
    expect(c.rules).toBeUndefined();
  });
});
