import axios from "axios";
import { API_URL } from "../config";
import {
  UploadFields,
  FinalizeResponse,
  uploadVideoViaSignedUrl,
} from "./upload";
import { canCompressVideo, compressVideo } from "./videoCompress";
import { uploadVideoParallel } from "./parallelUpload";

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
  onProgress?: (pct: number) => void
): Promise<FinalizeResponse> {
  // Phase 1 — compress (best-effort). When we attempt it, the encode owns the
  // first COMPRESS_PROGRESS_SHARE of the bar regardless of outcome, so the bar
  // never jumps backwards if compression turns out not to help.
  const attemptCompress = canCompressVideo() && file.size >= COMPRESS_THRESHOLD;
  let toUpload = file;
  if (attemptCompress) {
    try {
      toUpload = await compressVideo(file, { maxHeight: 720 }, (pct) =>
        onProgress?.(Math.round(pct * COMPRESS_PROGRESS_SHARE))
      );
    } catch {
      toUpload = file;
    }
  }

  // Phase 2 — map the upload's 0..100 into the remaining progress band.
  const base = attemptCompress ? COMPRESS_PROGRESS_SHARE * 100 : 0;
  const span = 100 - base;
  const up = (pct: number) => onProgress?.(Math.round(base + (pct * span) / 100));

  if (toUpload.size >= PARALLEL_THRESHOLD) {
    try {
      return await uploadVideoParallel(toUpload, fields, up);
    } catch {
      // Parallel parts don't resume mid-part; fall back to the resilient
      // resumable path (per-chunk retry + resume) if the parallel transfer fails.
      return await uploadVideoResumable(toUpload, fields, up);
    }
  }
  if (toUpload.size >= RESUMABLE_THRESHOLD) {
    return uploadVideoResumable(toUpload, fields, up);
  }
  return uploadVideoViaSignedUrl(toUpload, fields, up);
}
