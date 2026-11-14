/**
 * The upload path must never run the MediaRecorder fallback: it plays the whole
 * clip in realtime before a byte is sent (measured 92.7 s for an 86 s clip that
 * WebCodecs could not shrink, against 6.2 s without it), and what it uploads is
 * a 30 fps canvas re-recording instead of the athlete's video.
 *
 * WebCodecs is "present" here (stub globals) but cannot encode the fake bytes,
 * which is exactly the case that used to fall through to MediaRecorder. The
 * fallback's first act is probing `MediaRecorder.isTypeSupported`.
 */
import axios from "axios";
import { uploadVideo } from "../resumableUpload";
import { canCompressVideo } from "../videoCompress";

jest.mock("axios");
jest.mock("../../config", () => ({
  API_URL: "https://test-api.example",
  APP_BUILD: 1234567890,
}));

const mockedAxios = axios as jest.Mocked<typeof axios>;
const MIB = 1024 * 1024;
const WEBCODECS_GLOBALS = ["VideoEncoder", "VideoDecoder", "OffscreenCanvas"] as const;

type Compression = "auto" | "fast-only" | "off";

let timingDetails: Array<Record<string, string | number | null>>;
const isTypeSupported = jest.fn(() => false);

/** 30 MiB by reported size: over the 24 MiB compress threshold, under the 32 MiB parallel one. */
function makeLargeFile(): File {
  const file = new File([new Uint8Array(4096)], "clip.mp4", { type: "video/mp4" });
  Object.defineProperty(file, "size", { value: 30 * MIB });
  return file;
}

const fields = { competition_id: "c1", lift_type: "Situp", weight: "0", user_id: "u1" };

beforeEach(() => {
  timingDetails = [];
  isTypeSupported.mockClear();
  const globals = globalThis as Record<string, unknown>;
  for (const name of WEBCODECS_GLOBALS) globals[name] = class {};
  globals.MediaRecorder = { isTypeSupported };

  Object.defineProperty(navigator, "sendBeacon", { value: undefined, writable: true, configurable: true });
  (global.fetch as jest.Mock).mockReset();
  (global.fetch as jest.Mock).mockImplementation((_url: string, init?: { body?: string }) => {
    const parsed = JSON.parse(init?.body ?? "{}");
    if (parsed.action === "upload-timing") timingDetails.push(parsed.details);
    return Promise.resolve({ ok: true });
  });

  mockedAxios.post.mockReset();
  mockedAxios.put.mockReset();
  mockedAxios.post.mockImplementation((url: string) =>
    Promise.resolve(
      url.endsWith("/upload/signed-url")
        ? {
            data: {
              upload_url: "https://storage.example/signed",
              object_name: "videos/x.mp4",
              public_url: "https://storage.example/videos/x.mp4",
              content_type: "video/mp4",
            },
          }
        : { data: { url: "https://storage.example/videos/x.mp4", attempt_id: "attempt-1" } }
    )
  );
  mockedAxios.put.mockResolvedValue({ status: 200 });
});

afterEach(() => {
  const globals = globalThis as Record<string, unknown>;
  for (const name of WEBCODECS_GLOBALS) delete globals[name];
  delete globals.MediaRecorder;
});

describe("uploadVideo compression modes", () => {
  test("sanity: the stubs make WebCodecs look available", () => {
    expect(canCompressVideo()).toBe(true);
  });

  test.each<[string, Compression | undefined]>([
    ["no option (default)", undefined],
    ["'auto'", "auto"],
    ["'fast-only'", "fast-only"],
  ])("%s: a failed hardware encode sends the original and never tries MediaRecorder", async (_label, compression) => {
    const file = makeLargeFile();
    const result = await uploadVideo(file, fields, undefined, compression ? { compression } : undefined);

    expect(result.attempt_id).toBe("attempt-1");
    expect(isTypeSupported).not.toHaveBeenCalled();
    expect(mockedAxios.put).toHaveBeenCalledTimes(1);
    expect(mockedAxios.put.mock.calls[0][1]).toBe(file);
    expect(timingDetails).toHaveLength(1);
    // "kept-original" (not "skipped:…") proves the hardware encode was attempted.
    expect(timingDetails[0]).toMatchObject({
      compress: "kept-original",
      path: "single-put",
      srcBytes: 30 * MIB,
      sentBytes: 30 * MIB,
    });
  });

  test("the default mode is reported as fast-only", async () => {
    await uploadVideo(makeLargeFile(), fields);
    expect(timingDetails[0].mode).toBe("fast-only");
  });

  test("'off' skips compression entirely", async () => {
    const file = makeLargeFile();
    await uploadVideo(file, fields, undefined, { compression: "off" });
    expect(isTypeSupported).not.toHaveBeenCalled();
    expect(mockedAxios.put.mock.calls[0][1]).toBe(file);
    expect(timingDetails[0]).toMatchObject({ compress: "skipped:off", compressMs: 0 });
  });
});
