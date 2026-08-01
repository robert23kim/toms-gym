jest.mock("../../config", () => ({ API_URL: "http://test.local" }));

import { formatChampionScore } from "../api";

describe("formatChampionScore", () => {
  it("formats time scores as m:ss with floored seconds", () => {
    expect(formatChampionScore("time", 275.4)).toBe("4:35");
    expect(formatChampionScore("time", 59.9)).toBe("0:59");
    expect(formatChampionScore("time", 60)).toBe("1:00");
    expect(formatChampionScore("time", 0)).toBe("0:00");
  });

  it("formats weight scores in kg", () => {
    expect(formatChampionScore("weight", 120)).toBe("120 kg");
  });
});
