import { autoLiftTypeEnabled, liftTypeCountedAs, liftTypeQuestion, offersAutomatic } from "../autoLiftType";

describe("offersAutomatic", () => {
  test("the 100 Club's four types qualify (club squats are air squats)", () => {
    expect(offersAutomatic(true, ["Situp", "Pushup", "Squat", "Plank"], "consistency")).toBe(true);
  });
  test("a squat outside the club is weighted", () => {
    expect(offersAutomatic(true, ["Squat", "Pushup"], null)).toBe(false);
  });
  test("an all-bodyweight board qualifies in any mode", () => {
    expect(offersAutomatic(true, ["Pushup", "Situp"], undefined)).toBe(true);
  });
  test("switch off, one type, or a weighted type never qualify", () => {
    expect(offersAutomatic(false, ["Situp", "Pushup"], "consistency")).toBe(false);
    expect(offersAutomatic(true, ["Plank"], "consistency")).toBe(false);
    expect(offersAutomatic(true, ["Pushup", "Bench Press"], "consistency")).toBe(false);
    expect(offersAutomatic(true, [], "consistency")).toBe(false);
  });
});

describe("autoLiftTypeEnabled", () => {
  test("only a literal true, nested or top level", () => {
    expect(autoLiftTypeEnabled({ competition: { auto_lift_type_enabled: true } })).toBe(true);
    expect(autoLiftTypeEnabled({ auto_lift_type_enabled: true, competition: {} })).toBe(true);
    expect(autoLiftTypeEnabled({ competition: { auto_lift_type_enabled: "1" } })).toBe(false);
    expect(autoLiftTypeEnabled({ competition: {} })).toBe(false);
    expect(autoLiftTypeEnabled(null)).toBe(false);
  });
});

describe("copy", () => {
  test("plural for the result line, singular for the question", () => {
    expect(liftTypeCountedAs("Pushup")).toBe("Pushups");
    expect(liftTypeCountedAs("situp")).toBe("Situps");
    expect(liftTypeQuestion("Pushup")).toBe("a pushup");
    expect(liftTypeQuestion("plank")).toBe("a plank");
  });
});
