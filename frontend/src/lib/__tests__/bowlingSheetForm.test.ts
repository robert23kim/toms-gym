import { buildSheetForm } from "../bowlingSheetForm";
import { todayLocal } from "../dates";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

const file = new File(["x"], "sheet.jpg", { type: "image/jpeg" });

describe("buildSheetForm", () => {
  it("posts the photo, type, date and the saved user", () => {
    const form = buildSheetForm(file, { sheetType: "night", playedOn: "2026-09-13", userId: "u1", email: "x@y.z" });
    expect(form.get("image")).toBe(file);
    expect(form.get("sheet_type")).toBe("night");
    expect(form.get("played_on")).toBe("2026-09-13");
    expect(form.get("user_id")).toBe("u1");
    expect(form.get("email")).toBeNull();
  });

  it("falls back to email when there is no user id", () => {
    const form = buildSheetForm(file, { sheetType: "game", playedOn: "2026-09-13", userId: null, email: "x@y.z" });
    expect(form.get("user_id")).toBeNull();
    expect(form.get("email")).toBe("x@y.z");
  });
});

describe("todayLocal", () => {
  it("formats the local calendar day", () => {
    expect(todayLocal(new Date(2026, 8, 3, 23, 30))).toBe("2026-09-03");
  });
});
