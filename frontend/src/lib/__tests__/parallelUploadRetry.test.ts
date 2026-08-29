import { withRetry } from "../parallelUpload";

jest.mock("../../config", () => ({ API_URL: "http://test" }));

describe("withRetry", () => {
  it("returns on first success without retrying", async () => {
    const fn = jest.fn().mockResolvedValue("ok");
    await expect(withRetry(fn, 3, 0)).resolves.toBe("ok");
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("retries a transient failure and succeeds", async () => {
    const fn = jest
      .fn()
      .mockRejectedValueOnce(new Error("503"))
      .mockRejectedValueOnce(new Error("reset"))
      .mockResolvedValue("ok");
    await expect(withRetry(fn, 3, 0)).resolves.toBe("ok");
    expect(fn).toHaveBeenCalledTimes(3);
  });

  it("throws the last error after exhausting attempts", async () => {
    const fn = jest.fn().mockRejectedValue(new Error("still down"));
    await expect(withRetry(fn, 3, 0)).rejects.toThrow("still down");
    expect(fn).toHaveBeenCalledTimes(3);
  });
});
