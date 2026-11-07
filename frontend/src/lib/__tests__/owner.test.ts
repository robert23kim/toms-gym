import { isOwnerEmail, readOwnerCache, writeOwnerCache, OWNER_EMAIL } from "../owner";

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
