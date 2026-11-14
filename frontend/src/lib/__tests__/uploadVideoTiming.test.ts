/**
 * uploadVideo end to end with only the network mocked: every successful upload
 * must report exactly one `upload-timing` event the backend will accept, and
 * the timing plumbing must not change how uploads succeed or fail.
 */
import axios from "axios";
import { uploadVideo } from "../resumableUpload";
import * as telemetry from "../telemetry";

jest.mock("axios");
jest.mock("../../config", () => ({
  API_URL: "https://test-api.example",
  APP_BUILD: 1234567890,
}));

const mockedAxios = axios as jest.Mocked<typeof axios>;

const MIB = 1024 * 1024;
/** The backend's /log-error drops any body larger than this without logging. */
const BACKEND_BODY_CAP_BYTES = 2048;

interface SentEvent {
  body: string;
  action: string;
  page: string;
  details: Record<string, string | number | null>;
}

let events: SentEvent[];

/** Telemetry goes out by fetch here; resumable chunk PUTs use fetch too. */
function routeFetch(): void {
  Object.defineProperty(navigator, "sendBeacon", {
    value: undefined,
    writable: true,
    configurable: true,
  });
  (global.fetch as jest.Mock).mockImplementation((url: string, init?: { body?: unknown }) => {
    if (String(url).endsWith("/log-error")) {
      const body = String(init?.body ?? "{}");
      const parsed = JSON.parse(body);
      events.push({ body, action: parsed.action, page: parsed.page, details: parsed.details });
      return Promise.resolve({ ok: true });
    }
    return Promise.resolve({ status: 200, headers: { get: () => null } });
  });
}

function routeAxios(overrides: { put?: () => Promise<unknown>; failCompositeSign?: boolean } = {}): void {
  mockedAxios.post.mockImplementation((url: string, body?: unknown) => {
    if (url.endsWith("/upload/signed-url")) {
      return Promise.resolve({
        data: {
          upload_url: "https://storage.example/signed",
          object_name: "videos/x.mp4",
          public_url: "https://storage.example/videos/x.mp4",
          content_type: "video/mp4",
        },
      });
    }
    if (url.endsWith("/upload/composite/sign")) {
      if (overrides.failCompositeSign) return Promise.reject(new Error("sign down"));
      const parts = (body as { parts: number }).parts;
      return Promise.resolve({
        data: {
          final_object: "videos/x.mp4",
          public_url: "https://storage.example/videos/x.mp4",
          content_type: "video/mp4",
          parts: Array.from({ length: parts }, (_, i) => ({
            part_number: i + 1,
            object_name: `videos/x.mp4.part${i + 1}`,
            upload_url: `https://storage.example/part${i + 1}`,
          })),
        },
      });
    }
    if (url.endsWith("/upload/composite/complete")) {
      return Promise.resolve({ data: { public_url: "https://storage.example/videos/x.mp4" } });
    }
    if (url.endsWith("/upload/resumable-url")) {
      return Promise.resolve({
        data: {
          session_uri: "https://storage.example/session",
          object_name: "videos/x.mp4",
          public_url: "https://storage.example/videos/x.mp4",
          content_type: "video/mp4",
        },
      });
    }
    if (url.endsWith("/upload/finalize")) {
      return Promise.resolve({
        data: { url: "https://storage.example/videos/x.mp4", attempt_id: "attempt-1" },
      });
    }
    return Promise.reject(new Error(`unexpected POST ${url}`));
  });
  mockedAxios.put.mockImplementation(
    overrides.put ?? (() => new Promise((resolve) => setTimeout(() => resolve({ status: 200 }), 40)))
  );
}

function makeFile(reportedSize?: number): File {
  const file = new File([new Uint8Array(4096)], "my-private-clip.mp4", { type: "video/mp4" });
  if (reportedSize !== undefined) {
    Object.defineProperty(file, "size", { value: reportedSize });
  }
  return file;
}

const fields = { competition_id: "c1", lift_type: "Pushup", weight: "0", user_id: "u1" };

describe("uploadVideo timing telemetry", () => {
  beforeEach(() => {
    events = [];
    (global.fetch as jest.Mock).mockReset();
    mockedAxios.post.mockReset();
    mockedAxios.put.mockReset();
    routeFetch();
    routeAxios();
  });

  test("a single-PUT upload returns the finalize result and reports one timing event", async () => {
    const result = await uploadVideo(makeFile(), fields);

    expect(result.attempt_id).toBe("attempt-1");
    expect(events).toHaveLength(1);
    const [event] = events;
    expect(event.page).toBe("upload");
    expect(event.action).toBe("upload-timing");
    expect(event.details).toMatchObject({
      liftType: "Pushup",
      mode: "fast-only",
      compress: "skipped:no-webcodecs",
      path: "single-put",
      srcBytes: 4096,
      sentBytes: 4096,
      sentType: "video/mp4",
      completeMs: null,
      hiddenCount: 0,
    });
    // The mocked PUT takes 40 ms; sign and finalize resolve immediately.
    expect(event.details.putMs).toBeGreaterThanOrEqual(30);
    expect(event.details.totalMs).toBeGreaterThanOrEqual(event.details.putMs as number);
    expect(event.details.transferMs).toBeGreaterThanOrEqual(event.details.putMs as number);
    expect(typeof event.details.signMs).toBe("number");
    expect(typeof event.details.finalizeMs).toBe("number");
    expect(event.details.putMbps).toBeGreaterThan(0);
  });

  test("the event never carries the file name", async () => {
    await uploadVideo(makeFile(), fields);
    expect(events[0].body).not.toContain("my-private-clip");
  });

  test("the event fits the backend's 2 KB body cap even with a huge UA and URL", async () => {
    const realUserAgent = navigator.userAgent;
    Object.defineProperty(navigator, "userAgent", { value: "U".repeat(1500), configurable: true });
    window.history.pushState({}, "", `/challenges/abc?next=${"q".repeat(2500)}`);
    try {
      await uploadVideo(makeFile(), {
        ...fields,
        lift_type: "Overhead",
      });
    } finally {
      Object.defineProperty(navigator, "userAgent", { value: realUserAgent, configurable: true });
      window.history.pushState({}, "", "/");
    }
    expect(events).toHaveLength(1);
    expect(Buffer.byteLength(events[0].body, "utf8")).toBeLessThanOrEqual(BACKEND_BODY_CAP_BYTES);
  });

  test("going to the background mid-upload is counted", async () => {
    routeAxios({
      put: () => {
        Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));
        Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));
        return Promise.resolve({ status: 200 });
      },
    });
    await uploadVideo(makeFile(), fields);
    expect(events[0].details.hiddenCount).toBe(1);
  });

  test("a failed PUT rejects with its stage tag and reports no timing event", async () => {
    routeAxios({ put: () => Promise.reject(new Error("connection reset")) });
    await expect(uploadVideo(makeFile(), fields)).rejects.toMatchObject({
      message: "connection reset",
      uploadStage: "gcs-put",
    });
    expect(events).toHaveLength(0);
  });

  test("a telemetry failure does not fail a finished upload", async () => {
    const spy = jest.spyOn(telemetry, "reportUploadTiming").mockImplementation(() => {
      throw new Error("telemetry exploded");
    });
    try {
      const result = await uploadVideo(makeFile(), fields);
      expect(result.attempt_id).toBe("attempt-1");
      expect(spy).toHaveBeenCalledTimes(1);
    } finally {
      spy.mockRestore();
    }
  });

  test("a 40 MiB file takes the parallel path and times the compose step", async () => {
    await uploadVideo(makeFile(40 * MIB), fields);
    expect(mockedAxios.put).toHaveBeenCalledTimes(3);
    expect(events).toHaveLength(1);
    expect(events[0].details).toMatchObject({ path: "parallel", sentBytes: 40 * MIB });
    expect(typeof events[0].details.completeMs).toBe("number");
    expect(events[0].details.putMs).toBeGreaterThanOrEqual(30);
  });

  test("when the parallel path fails, the resumable fallback is what gets reported", async () => {
    routeAxios({ failCompositeSign: true });
    const result = await uploadVideo(makeFile(40 * MIB), fields);
    expect(result.attempt_id).toBe("attempt-1");
    expect(events).toHaveLength(1);
    expect(events[0].details).toMatchObject({ path: "resumable-fallback", completeMs: null });
    expect(typeof events[0].details.putMs).toBe("number");
  });
});
