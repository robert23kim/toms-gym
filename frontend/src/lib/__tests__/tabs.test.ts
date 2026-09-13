import { activeTab, meTarget } from "../tabs";

describe("activeTab", () => {
  it.each([
    ["/", "home"],
    ["/lift", "lift"],
    ["/lift/upload", "lift"],
    ["/upload", "lift"],
    ["/challenges/abc", "lift"],
    ["/champions", "lift"],
    ["/bowl", "bowl"],
    ["/bowling/scoresheet/1", "bowl"],
    ["/golf/snap", "golf"],
    ["/profile/u1", "me"],
    ["/find-profile", "me"],
    ["/signin", "me"],
    ["/auth/magic/t", "me"],
    ["/terms", null],
    ["/golfing", null],
  ])("%s → %s", (path, tab) => {
    expect(activeTab(path)).toBe(tab);
  });
});

describe("meTarget", () => {
  it("goes to the saved profile", () => expect(meTarget("u1")).toBe("/profile/u1"));
  it("goes to find-profile when anonymous", () => expect(meTarget(null)).toBe("/find-profile"));
});
