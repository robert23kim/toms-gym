import axios from "axios";
import { API_URL } from "../config";
import {
  UploadFields,
  FinalizeResponse,
  uploadVideoViaSignedUrl,
} from "./upload";
import { canCompressVideo, compressVideo } from "./videoCompress";
import { uploadVideoParallel } from "./parallelUpload";
import { shouldCompress } from "./compressionPolicy";
import { beginJourney, markStage, endJourney } from "./uploadJourney";

const CHUNK_SIZE = 8 * 1024 * 1024; // 8 MiB per chunk (must be a multiple of 256 KiB)
const MAX_CHUNK_RETRIES = 5;
// Files at/above this size use the resumable chunked path; smaller ones use a
// single PUT (simpler, and a blip just means re-sending one small request).
const RESUMABLE_THRESHOLD = 32 * 1024 * 1024; // 32 MiB
// Files at/above this (after compression) use the parallel composite path —
// the transfer is parallelized across 4 connections instead of streamed serially.
const PARALLEL_THRESHOLD = 48 * 1024 * 1024; // 48 MiB
// Compress videos at/above this size before uploading (smaller files aren't
// worth the encode time). Best-effort: returns the original if it can't help.
const COMPRESS_THRESHOLD = 24 * 1024 * 1024; // 24 MiB
// When we compress, the encode owns the first 40% of the progress bar and the
// upload the remaining 60%.
const COMPRESS_PROGRESS_SHARE = 0.4;

interface ResumableSession {
  session_uri: string;
  object_name: string;
  public_url: string;
  content_type: string;
}

/** Tag an error with the stage it failed at, then rethrow (for telemetry). */
function failAtStage(err: unknown, stage: string): never {
  if (err && typeof err === "object") {
    (err as Record<string, unknown>).uploadStage = stage;
  }
  throw err;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Ask GCS how many bytes it has durably received for this session, so we can
 * resume from the real confirmed offset after a failure. Returns `total` if
 * the object is already complete.
 */
async function queryConfirmedOffset(sessionUri: string, total: number): Promise<number> {
  const res = await fetch(sessionUri, {
    method: "PUT",
    headers: { "Content-Range": `bytes */${total}` },
  });
  if (res.status === 200 || res.status === 201) return total;
  if (res.status === 308) {
    const range = res.headers.get("Range"); // e.g. "bytes=0-262143"
    if (range) {
      const end = parseInt(range.split("-")[1], 10);
      if (!Number.isNaN(end)) return end + 1;
    }
    return 0;
  }
  throw new Error(`Unexpected status querying upload offset: ${res.status}`);
}

/**
 * Upload a file to a GCS resumable session in chunks, resuming after a dropped
 * connection instead of restarting. Resolves once GCS reports the object complete.
 */
async function putChunks(
  sessionUri: string,
  file: File,
  onProgress?: (pct: number) => void
): Promise<void> {
  const total = file.size;
  let offset = 0;
  let failures = 0;

  while (offset < total) {
    const end = Math.min(offset + CHUNK_SIZE, total);
    const chunk = file.slice(offset, end);
    const contentRange = `bytes ${offset}-${end - 1}/${total}`;

    try {
      const res = await fetch(sessionUri, {
        method: "PUT",
        headers: { "Content-Range": contentRange },
        body: chunk,
      });

      if (res.status === 200 || res.status === 201) {
        offset = total; // final chunk accepted — object complete
      } else if (res.status === 308) {
        const range = res.headers.get("Range");
        offset = range ? parseInt(range.split("-")[1], 10) + 1 : end;
        failures = 0;
      } else if (res.status >= 400 && res.status < 500) {
        throw new Error(`Upload rejected by storage: ${res.status}`);
      } else {
        throw new Error(`Chunk upload failed: ${res.status}`);
      }
    } catch (err) {
      failures += 1;
      if (failures > MAX_CHUNK_RETRIES) throw err;
      await sleep(Math.min(1000 * 2 ** (failures - 1), 8000));
      // Re-sync from GCS so the next loop resumes at the real confirmed offset.
      try {
        offset = await queryConfirmedOffset(sessionUri, total);
      } catch {
        /* keep current offset and retry the same window */
      }
    }
    onProgress?.(Math.min(100, Math.round((offset / total) * 100)));
  }
}

/**
 * Resumable, chunked upload: start a session on the backend, stream the file to
 * GCS in chunks (surviving network blips), then finalize the attempt.
 * Errors are stage-tagged (resumable-init / gcs-chunk / finalize) for telemetry.
 */
export async function uploadVideoResumable(
  file: File,
  fields: UploadFields,
  onProgress?: (pct: number) => void
): Promise<FinalizeResponse> {
  let session: ResumableSession;
  try {
    const res = await axios.post<ResumableSession>(`${API_URL}/upload/resumable-url`, {
      filename: file.name,
      content_type: file.type || "application/octet-stream",
    });
    session = res.data;
  } catch (err) {
    return failAtStage(err, "resumable-init");
  }

  try {
    await putChunks(session.session_uri, file, onProgress);
  } catch (err) {
    return failAtStage(err, "gcs-chunk");
  }

  try {
    const res = await axios.post<FinalizeResponse>(`${API_URL}/upload/finalize`, {
      object_name: session.object_name,
      public_url: session.public_url,
      ...fields,
    });
    return res.data;
  } catch (err) {
    return failAtStage(err, "finalize");
  }
}

/**
 * Upload a video the best way for its size, after optionally compressing it.
 *
 * 1. Compress large videos client-side (downscale to 720p) so there's less to
 *    send — best-effort, falls back to the original on any failure.
 * 2. Pick the transfer method by the resulting size:
 *      - >= 48 MiB  → parallel composite (4 parallel connections), falling back
 *                     to the resumable path if the parallel transfer fails
 *      - >= 32 MiB  → resumable chunked (survives mobile network drops)
 *      - otherwise  → single-PUT signed URL (simplest)
 * All paths upload directly to GCS, bypassing Cloud Run's 32 MiB request cap.
 */
export async function uploadVideo(
  file: File,
  fields: UploadFields,
  onProgress?: (pct: number) => void,
  options?: {
    /**
     * 'auto' (default) — hardware WebCodecs encode when supported, slow
     *   MediaRecorder fallback otherwise;
     * 'fast-only' — hardware encode or nothing: never pay the realtime
     *   MediaRecorder fallback (right for analyzers that downsample anyway);
     * 'off' — always upload the original bytes.
     */
    compression?: 'auto' | 'fast-only' | 'off';
  }
): Promise<FinalizeResponse> {
  // Crash breadcrumbs: persisted at every stage so a page death mid-upload
  // (iOS jetsam during compression, tab OOM) is reported on the next boot.
  beginJourney({
    fileName: file.name,
    fileSizeMB: Number((file.size / (1024 * 1024)).toFixed(2)),
    fileType: file.type || "unknown",
  });
  try {
    const result = await runUpload(file, fields, onProgress, options);
    endJourney();
    return result;
  } catch (err) {
    // A thrown error is handled (and reported) by the caller — clear the
    // journey so the next boot doesn't double-report it as a page death.
    endJourney();
    throw err;
  }
}

async function runUpload(
  file: File,
  fields: UploadFields,
  onProgress?: (pct: number) => void,
  options?: { compression?: 'auto' | 'fast-only' | 'off' }
): Promise<FinalizeResponse> {
  // Phase 1 — compress (best-effort). When we attempt it, the encode owns the
  // first COMPRESS_PROGRESS_SHARE of the bar regardless of outcome, so the bar
  // never jumps backwards if compression turns out not to help.
  //
  // Gated by shouldCompress: the WebCodecs demux buffers the whole file in
  // memory, which OOM-kills the tab on iOS (Safari then auto-reloads the page)
  // and on very large files anywhere. Skipped files upload as originals via
  // the chunked paths below, which slice the Blob and are memory-safe.
  const mode = options?.compression ?? 'auto';
  const decision = shouldCompress(
    file.size,
    navigator.userAgent,
    navigator.maxTouchPoints ?? 0
  );
  const attemptCompress =
    mode !== 'off' &&
    decision.compress &&
    canCompressVideo() &&
    file.size >= COMPRESS_THRESHOLD;
  let toUpload = file;
  if (attemptCompress) {
    markStage("compress-start", { compressDecision: decision.reason });
    try {
      toUpload = await compressVideo(
        file,
        { maxHeight: 720, fastPathOnly: mode === 'fast-only' },
        (pct) => onProgress?.(Math.round(pct * COMPRESS_PROGRESS_SHARE))
      );
    } catch {
      toUpload = file;
    }
    markStage("compress-done", {
      compressedMB: Number((toUpload.size / (1024 * 1024)).toFixed(2)),
    });
  } else {
    markStage("compress-skipped", { compressDecision: decision.reason });
  }

  // Phase 2 — map the upload's 0..100 into the remaining progress band.
  const base = attemptCompress ? COMPRESS_PROGRESS_SHARE * 100 : 0;
  const span = 100 - base;
  // Breadcrumb every 10% so a mid-transfer death records how far it got.
  let lastMarkedDecile = -1;
  const up = (pct: number) => {
    const decile = Math.floor(pct / 10);
    if (decile > lastMarkedDecile) {
      lastMarkedDecile = decile;
      markStage("put-progress", { pct });
    }
    onProgress?.(Math.round(base + (pct * span) / 100));
  };

  if (toUpload.size >= PARALLEL_THRESHOLD) {
    markStage("transfer-start", { method: "parallel" });
    try {
      return await uploadVideoParallel(toUpload, fields, up);
    } catch {
      // Parallel parts don't resume mid-part; fall back to the resilient
      // resumable path (per-chunk retry + resume) if the parallel transfer fails.
      markStage("transfer-start", { method: "resumable-fallback" });
      return await uploadVideoResumable(toUpload, fields, up);
    }
  }
  if (toUpload.size >= RESUMABLE_THRESHOLD) {
    markStage("transfer-start", { method: "resumable" });
    return uploadVideoResumable(toUpload, fields, up);
  }
  markStage("transfer-start", { method: "single-put" });
  return uploadVideoViaSignedUrl(toUpload, fields, up);
}
