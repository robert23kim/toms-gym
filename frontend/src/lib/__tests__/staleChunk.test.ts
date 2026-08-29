import { handleStaleChunk } from "../staleChunk";

describe("handleStaleChunk", () => {
  const reload = jest.fn();

  beforeEach(() => {
    sessionStorage.clear();
    reload.mockClear();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { reload },
    });
  });

  it("reloads once and suppresses the error on first failure", () => {
    const event = new Event("vite:preloadError", { cancelable: true });
    expect(handleStaleChunk(event)).toBe(true);
    expect(reload).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);
  });

  it("does not reload again within the guard window", () => {
    handleStaleChunk(new Event("vite:preloadError", { cancelable: true }));
    const second = new Event("vite:preloadError", { cancelable: true });
    expect(handleStaleChunk(second)).toBe(false);
    expect(reload).toHaveBeenCalledTimes(1);
    expect(second.defaultPrevented).toBe(false);
  });

  it("reloads again once the guard window has passed", () => {
    sessionStorage.setItem("staleChunkReloadedAt", String(Date.now() - 120_000));
    expect(handleStaleChunk(new Event("vite:preloadError", { cancelable: true }))).toBe(true);
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
