import {
  buildUploadTiming,
  createUploadTimer,
  megabitsPerSecond,
  networkHints,
  untimed,
  watchHidden,
} from "../uploadTiming";

/** A clock the test advances by hand. */
function fakeClock() {
  let t = 1000;
  return { now: () => t, advance: (ms: number) => void (t += ms) };
}

describe("createUploadTimer", () => {
  test("records each phase's duration and returns the phase's value", async () => {
    const clock = fakeClock();
    const timer = createUploadTimer(clock.now);
    const signed = await timer.time("sign", async () => {
      clock.advance(120);
      return "url";
    });
    await timer.time("put", async () => clock.advance(4000));
    expect(signed).toBe("url");
    expect(timer.phases()).toEqual({ sign: 120, put: 4000 });
  });

  test("a phase that throws is still timed and the error propagates", async () => {
    const clock = fakeClock();
    const timer = createUploadTimer(clock.now);
    await expect(
      timer.time("put", async () => {
        clock.advance(700);
        throw new Error("network");
      })
    ).rejects.toThrow("network");
    expect(timer.phases()).toEqual({ put: 700 });
  });

  test("a phase run twice (parallel attempt, then resumable fallback) sums", async () => {
    const clock = fakeClock();
    const timer = createUploadTimer(clock.now);
    await timer.time("sign", async () => clock.advance(100));
    await timer.time("sign", async () => clock.advance(150));
    expect(timer.phases().sign).toBe(250);
  });

  test("untimed runs the phase without recording anything", async () => {
    await expect(untimed("put", async () => 7)).resolves.toBe(7);
  });
});

describe("megabitsPerSecond", () => {
  test("10 MB in 8 s is 10 Mbit/s", () => {
    expect(megabitsPerSecond(10_000_000, 8000)).toBe(10);
  });

  test("is null when the duration is missing or zero", () => {
    expect(megabitsPerSecond(10_000_000, undefined)).toBeNull();
    expect(megabitsPerSecond(10_000_000, 0)).toBeNull();
  });
});

describe("watchHidden", () => {
  function setVisibility(state: "hidden" | "visible"): void {
    Object.defineProperty(document, "visibilityState", { value: state, configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
  }

  afterEach(() => setVisibility("visible"));

  test("counts each time the page goes to the background, and stops when told", () => {
    const stop = watchHidden();
    setVisibility("hidden");
    setVisibility("visible");
    setVisibility("hidden");
    expect(stop()).toBe(2);
    setVisibility("visible");
    setVisibility("hidden");
    expect(stop()).toBe(2);
  });
});

describe("networkHints", () => {
  test("reads the connection when the browser exposes one", () => {
    const nav = { connection: { type: "wifi", effectiveType: "4g", downlink: 9.5 } };
    expect(networkHints(nav as unknown as Navigator)).toEqual({
      netType: "wifi",
      netEffective: "4g",
      netDownMbps: 9.5,
    });
  });

  test("is all null on browsers without the API (iOS)", () => {
    expect(networkHints({} as unknown as Navigator)).toEqual({
      netType: null,
      netEffective: null,
      netDownMbps: null,
    });
  });
});

describe("buildUploadTiming", () => {
  test("flattens a compressed single-PUT upload into rounded, labelled fields", () => {
    const details = buildUploadTiming({
      liftType: "Pushup",
      mode: "auto",
      compress: "webcodecs",
      compressMs: 7350.4,
      path: "single-put",
      srcBytes: 60_000_000,
      sentBytes: 9_173_010,
      srcType: "video/mp4",
      sentType: "video/mp4",
      phases: { sign: 210.6, put: 4870.2, finalize: 190.1 },
      transferMs: 5300.9,
      totalMs: 12651.3,
      hiddenCount: 0,
    });
    expect(details).toEqual({
      liftType: "Pushup",
      mode: "auto",
      compress: "webcodecs",
      path: "single-put",
      srcBytes: 60_000_000,
      sentBytes: 9_173_010,
      srcType: "video/mp4",
      sentType: "video/mp4",
      compressMs: 7350,
      signMs: 211,
      putMs: 4870,
      completeMs: null,
      finalizeMs: 190,
      transferMs: 5301,
      totalMs: 12651,
      putMbps: 15.07,
      hiddenCount: 0,
    });
  });
});
