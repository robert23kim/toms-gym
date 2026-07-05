import { JOURNEY_KEY } from "../uploadJourney";

// config.ts uses import.meta.env (Vite-only syntax) and cannot be loaded under
// Jest's CJS runtime — substitute the two values telemetry needs.
jest.mock("../../config", () => ({
  API_URL: "https://test-api.example",
  APP_BUILD: 1234567890,
}));

// jest.setup.js installs a non-storing localStorage mock; telemetry's dead-
// journey detection needs real get/set semantics.
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

type SentReport = { url: string; payload: Record<string, unknown> };

/** Route telemetry through the fetch fallback and collect decoded payloads. */
function captureReports(): SentReport[] {
  const sent: SentReport[] = [];
  // No sendBeacon → telemetry must fall back to fetch.
  Object.defineProperty(navigator, "sendBeacon", {
    value: undefined,
    writable: true,
    configurable: true,
  });
  (global.fetch as jest.Mock).mockImplementation(
    (url: string, init?: { body?: string }) => {
      sent.push({ url, payload: JSON.parse(init?.body ?? "{}") });
      return Promise.resolve({ ok: true });
    }
  );
  return sent;
}

describe("telemetry", () => {
  let telemetry: typeof import("../telemetry");

  beforeEach(async () => {
    installRealLocalStorage();
    window.sessionStorage.clear();
    (global.fetch as jest.Mock).mockReset();
    jest.resetModules();
    telemetry = await import("../telemetry");
  });

  test("reportError payloads carry a build stamp and platform", () => {
    const sent = captureReports();
    telemetry.reportError("TestPage", "test-action", new Error("boom"));
    expect(sent).toHaveLength(1);
    expect(sent[0].url).toContain("/log-error");
    expect(sent[0].payload).toMatchObject({
      page: "TestPage",
      action: "test-action",
      error: "boom",
    });
    expect(sent[0].payload).toHaveProperty("build");
    expect(sent[0].payload).toHaveProperty("platform");
  });

  test("initTelemetry reports a journey that died in a previous session", () => {
    const sent = captureReports();
    window.localStorage.setItem(
      JOURNEY_KEY,
      JSON.stringify({
        stage: "compress-start",
        stages: ["started", "compress-start"],
        fileName: "lift.mov",
        fileSizeMB: 412.5,
        fileType: "video/quicktime",
        startedAt: 1,
        stageAt: 2,
      })
    );

    telemetry.initTelemetry();

    const died = sent.find((r) => r.payload.action === "upload-died");
    expect(died).toBeDefined();
    const details = died!.payload.details as Record<string, unknown>;
    expect(details.stage).toBe("compress-start");
    expect(details.fileSizeMB).toBe(412.5);
    // The dead journey is consumed — a second boot must not re-report it.
    expect(window.localStorage.getItem(JOURNEY_KEY)).toBeNull();
  });

  test("initTelemetry sends a boot ping once per session", () => {
    const sent = captureReports();
    telemetry.initTelemetry();
    const boots = sent.filter((r) => r.payload.action === "boot");
    expect(boots).toHaveLength(1);

    // Same session, re-init (e.g. hot reload): no second ping.
    jest.resetModules();
    return import("../telemetry").then((again) => {
      again.initTelemetry();
      expect(sent.filter((r) => r.payload.action === "boot")).toHaveLength(1);
    });
  });

  test("uncaught window errors are reported after init", () => {
    const sent = captureReports();
    telemetry.initTelemetry();
    window.dispatchEvent(
      new ErrorEvent("error", { message: "undefined is not a function", error: new Error("undefined is not a function") })
    );
    const report = sent.find((r) => r.payload.action === "window-error");
    expect(report).toBeDefined();
    expect(String(report!.payload.error)).toContain("undefined is not a function");
  });
});
