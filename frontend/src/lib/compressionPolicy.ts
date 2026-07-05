/**
 * Policy gate for client-side video compression.
 *
 * The compression pipeline (videoCompress.ts) demuxes the source by reading the
 * WHOLE file into memory (`file.arrayBuffer()` + mp4box sample copies ≈ 2× the
 * file size resident at once). On iOS, WebKit's per-tab memory budget makes
 * that a jetsam kill for typical phone videos — the tab dies and Safari
 * auto-reloads the page before the first upload request is ever sent. Desktop
 * browsers have far larger budgets but still hit the same cliff on huge files.
 *
 * So: never compress on iOS (every iOS browser is WebKit), and never compress
 * files above a hard size cap anywhere else. Skipped files upload as originals
 * through the chunked/parallel paths, which slice the Blob and are memory-safe.
 */

export interface CompressionDecision {
  compress: boolean;
  /** Why, for telemetry: "ok" | "ios-webkit" | "file-too-large". */
  reason: "ok" | "ios-webkit" | "file-too-large";
}

/** Hard cap: above this, whole-file demux is an OOM risk on any platform. */
export const COMPRESS_MAX_BYTES = 200 * 1024 * 1024; // 200 MiB

/**
 * True for any iOS/iPadOS device. iPadOS 13+ reports a desktop-Mac UA string,
 * so a "Macintosh" UA with multiple touch points is treated as iPad.
 */
function isIosWebKit(userAgent: string, maxTouchPoints: number): boolean {
  if (/iPhone|iPad|iPod/i.test(userAgent)) return true;
  return /Macintosh/i.test(userAgent) && maxTouchPoints > 1;
}

export function shouldCompress(
  fileSizeBytes: number,
  userAgent: string,
  maxTouchPoints: number
): CompressionDecision {
  if (isIosWebKit(userAgent, maxTouchPoints)) {
    return { compress: false, reason: "ios-webkit" };
  }
  if (fileSizeBytes > COMPRESS_MAX_BYTES) {
    return { compress: false, reason: "file-too-large" };
  }
  return { compress: true, reason: "ok" };
}
