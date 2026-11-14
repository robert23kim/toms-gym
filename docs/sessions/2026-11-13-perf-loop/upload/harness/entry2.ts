import { uploadVideo } from "/Users/toka/code/toms_gym-perf/frontend/src/lib/resumableUpload";

declare global {
  interface Window {
    runUpload: (url: string, name: string, liftType: string, compression?: "auto" | "fast-only" | "off") => Promise<Record<string, unknown>>;
    mrStarts: number;
  }
}
window.mrStarts = 0;
if (window.MediaRecorder) {
  const origStart = window.MediaRecorder.prototype.start;
  window.MediaRecorder.prototype.start = function (...args: [number?]) {
    window.mrStarts += 1;
    return origStart.apply(this, args);
  };
}
window.runUpload = async (url, name, liftType, compression) => {
  const blob = await (await fetch(url)).blob();
  const file = new File([blob], name, { type: "video/mp4" });
  const t0 = performance.now();
  const result = await uploadVideo(
    file,
    { competition_id: "perf-bench-local", lift_type: liftType, weight: "0", user_id: "perf-bench-local" },
    undefined,
    compression ? { compression } : undefined
  );
  return { wallMs: Math.round(performance.now() - t0), attempt: result.attempt_id, mediaRecorderStarts: window.mrStarts };
};
