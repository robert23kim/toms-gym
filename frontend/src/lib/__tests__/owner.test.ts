import { isOwnerEmail, readOwnerCache, writeOwnerCache, OWNER_EMAIL, isSportChallenge, visibleChallenges } from "../owner";

describe("visibleChallenges", () => {
  const bowling = { id: "b", categories: ["Bowling", "Men", "Women"] };
  const golf = { id: "g", categories: ["golf", "Open"] };
  const plank = { id: "p", categories: ["Plank"] };
  const mixed = { id: "m", categories: ["Bowling", "Squat"] };
  const none = { id: "n", categories: [] };
  it("flags challenges with a bowling or golf category", () => {
    expect(isSportChallenge(bowling)).toBe(true);
    expect(isSportChallenge(golf)).toBe(true);
    expect(isSportChallenge(plank)).toBe(false);
    expect(isSportChallenge(mixed)).toBe(true);
    expect(isSportChallenge(none)).toBe(false);
    expect(isSportChallenge({})).toBe(false);
  });
  it("drops them for everyone but the owner", () => {
    const all = [bowling, golf, plank, mixed, none];
    expect(visibleChallenges(all, false)).toEqual([plank, none]);
    expect(visibleChallenges(all, true)).toEqual(all);
  });
});

describe("isOwnerEmail", () => {
  it("matches the owner's address case- and space-insensitively", () => {
    expect(isOwnerEmail(OWNER_EMAIL)).toBe(true);
    expect(isOwnerEmail(" Toka778@Gmail.com ")).toBe(true);
  });
  it("rejects anyone else, empty and missing values", () => {
    expect(isOwnerEmail("caleb@example.com")).toBe(false);
    expect(isOwnerEmail("toka778@gmail.com.evil")).toBe(false);
    expect(isOwnerEmail("")).toBe(false);
    expect(isOwnerEmail(null)).toBe(false);
    expect(isOwnerEmail(undefined)).toBe(false);
  });
});

describe("owner cache", () => {
  afterEach(() => {
    (localStorage.getItem as jest.Mock).mockReset();
    (localStorage.setItem as jest.Mock).mockReset();
  });

  it("returns the cached verdict only for the same userId", () => {
    (localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify({ userId: "u1", owner: true }));
    expect(readOwnerCache("u1")).toBe(true);
    expect(readOwnerCache("u2")).toBeNull();
  });

  it("treats garbage, missing and non-boolean values as unknown", () => {
    (localStorage.getItem as jest.Mock).mockReturnValue("{not json");
    expect(readOwnerCache("u1")).toBeNull();
    (localStorage.getItem as jest.Mock).mockReturnValue(undefined);
    expect(readOwnerCache("u1")).toBeNull();
    (localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify({ userId: "u1", owner: "yes" }));
    expect(readOwnerCache("u1")).toBeNull();
  });

  it("writes the verdict under one key", () => {
    writeOwnerCache("u1", false);
    expect(localStorage.setItem).toHaveBeenCalledWith("ownerCheck", JSON.stringify({ userId: "u1", owner: false }));
  });
});
