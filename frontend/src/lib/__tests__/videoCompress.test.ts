/**
 * Mode semantics for compressVideo. jsdom has no WebCodecs, so the hardware
 * path is unavailable here; these tests pin the fallback behavior around it:
 * fastPathOnly must return the original without ever consulting the realtime
 * MediaRecorder pipeline, while the default mode is allowed to attempt it.
 *
 * Observable: the fallback's first act is probing MediaRecorder mime support,
 * so a stubbed `MediaRecorder.isTypeSupported` records whether the fallback
 * was entered at all.
 */
import { compressVideo, canCompressVideo } from "../videoCompress";

const makeFile = () =>
  new File([new Uint8Array(2048)], "clip.mp4", { type: "video/mp4" });

describe("compressVideo modes", () => {
  const isTypeSupported = jest.fn(() => false);

  beforeEach(() => {
    isTypeSupported.mockClear();
    (globalThis as Record<string, unknown>).MediaRecorder = { isTypeSupported };
  });

  afterEach(() => {
    delete (globalThis as Record<string, unknown>).MediaRecorder;
  });

  test("jsdom sanity: WebCodecs path is unavailable", () => {
    expect(canCompressVideo()).toBe(false);
  });

  test("fastPathOnly never consults the MediaRecorder fallback and returns the original", async () => {
    const file = makeFile();
    const out = await compressVideo(file, { fastPathOnly: true });
    expect(out).toBe(file);
    expect(isTypeSupported).not.toHaveBeenCalled();
  });

  test("default mode attempts the MediaRecorder fallback (then falls back to the original here)", async () => {
    const file = makeFile();
    const out = await compressVideo(file);
    // No supported mimeType in the stub, so the contract is: original returned…
    expect(out).toBe(file);
    // …but the fallback pipeline was at least consulted.
    expect(isTypeSupported).toHaveBeenCalled();
  });

  test("fastPathOnly still reports terminal progress", async () => {
    const file = makeFile();
    const seen: number[] = [];
    await compressVideo(file, { fastPathOnly: true }, (pct) => seen.push(pct));
    expect(seen[0]).toBe(0);
    expect(seen[seen.length - 1]).toBe(100);
  });
});
