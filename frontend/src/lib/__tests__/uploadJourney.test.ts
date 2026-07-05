import {
  beginJourney,
  markStage,
  endJourney,
  takeDeadJourney,
  JOURNEY_KEY,
} from "../uploadJourney";

// jest.setup.js installs a non-storing localStorage mock; these tests need real
// get/set semantics, so install an in-memory implementation per test.
function installRealLocalStorage(): void {
  const store = new Map<string, string>();
  Object.defineProperty(window, "localStorage", {
    value: {
      getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
      setItem: (k: string, v: string) => void store.set(k, String(v)),
      removeItem: (k: string) => void store.delete(k),
      clear: () => store.clear(),
    },
    writable: true,
  });
}

const META = { fileName: "lift.mov", fileSizeMB: 412.5, fileType: "video/quicktime" };

describe("upload journey crash evidence", () => {
  beforeEach(installRealLocalStorage);

  test("no journey recorded → takeDeadJourney returns null", () => {
    expect(takeDeadJourney()).toBeNull();
  });

  test("a journey that never ended is returned as dead, with its last stage and file meta", () => {
    beginJourney(META);
    markStage("compress-start", { decision: "ok" });

    const dead = takeDeadJourney();
    expect(dead).not.toBeNull();
    expect(dead!.stage).toBe("compress-start");
    expect(dead!.fileName).toBe("lift.mov");
    expect(dead!.fileSizeMB).toBe(412.5);
    expect(dead!.decision).toBe("ok");
    expect(dead!.stages).toEqual(["started", "compress-start"]);
  });

  test("takeDeadJourney clears the record — second call returns null", () => {
    beginJourney(META);
    takeDeadJourney();
    expect(takeDeadJourney()).toBeNull();
  });

  test("a journey ended normally leaves no dead record", () => {
    beginJourney(META);
    markStage("finalize-ok");
    endJourney();
    expect(takeDeadJourney()).toBeNull();
  });

  test("markStage merges extra fields across stages", () => {
    beginJourney(META);
    markStage("gcs-parts", { method: "parallel" });
    markStage("put-progress", { pct: 40 });

    const dead = takeDeadJourney();
    expect(dead!.method).toBe("parallel");
    expect(dead!.pct).toBe(40);
    expect(dead!.stage).toBe("put-progress");
  });

  test("markStage without an active journey is a no-op", () => {
    expect(() => markStage("compress-start")).not.toThrow();
    expect(takeDeadJourney()).toBeNull();
  });

  test("corrupt stored JSON is discarded, not thrown", () => {
    window.localStorage.setItem(JOURNEY_KEY, "{not json");
    expect(takeDeadJourney()).toBeNull();
    expect(window.localStorage.getItem(JOURNEY_KEY)).toBeNull();
  });
});
