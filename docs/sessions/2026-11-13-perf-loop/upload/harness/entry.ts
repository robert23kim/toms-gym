import { compressVideo, canCompressVideo } from "/Users/toka/code/toms_gym-perf/frontend/src/lib/videoCompress";

declare global {
  interface Window {
    runCompress: (url: string, name: string, fastPathOnly: boolean) => Promise<Record<string, unknown>>;
    mrStarts: number;
  }
}

window.mrStarts = 0;
const RealMR = window.MediaRecorder;
if (RealMR) {
  const origStart = RealMR.prototype.start;
  RealMR.prototype.start = function (...args: [number?]) {
    window.mrStarts += 1;
    return origStart.apply(this, args);
  };
}

window.runCompress = async (url, name, fastPathOnly) => {
  const t0 = performance.now();
  const blob = await (await fetch(url)).blob();
  const file = new File([blob], name, { type: "video/mp4" });
  const tFetch = performance.now();
  const before = window.mrStarts;
  let lastPct = -1;
  const out = await compressVideo(file, { maxHeight: 720, fastPathOnly }, (p) => { lastPct = p; });
  const t1 = performance.now();
  return {
    name, fastPathOnly, canCompress: canCompressVideo(),
    inBytes: file.size, outBytes: out.size, returnedOriginal: out === file,
    outType: out.type, outName: out.name,
    fetchMs: Math.round(tFetch - t0), compressMs: Math.round(t1 - tFetch),
    mediaRecorderRan: window.mrStarts > before, lastPct,
  };
};
