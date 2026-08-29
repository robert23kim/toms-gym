import { formatDay } from "../dates";

const now = new Date("2026-08-29T12:00:00");

describe("formatDay", () => {
  it("drops the year inside the current year and keeps it otherwise", () => {
    expect(formatDay("2026-07-02", now)).toBe("Jul 2");
    expect(formatDay("2025-11-30", now)).toBe("Nov 30, 2025");
  });

  it("treats a bare ISO date as a local day, not UTC midnight", () => {
    expect(formatDay("2026-08-01", now)).toBe("Aug 1");
  });

  it("passes through junk and empties quietly", () => {
    expect(formatDay(null, now)).toBe("");
    expect(formatDay("not a date", now)).toBe("not a date");
  });
});
