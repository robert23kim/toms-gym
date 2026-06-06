import axios from "axios";
import { API_URL } from "../config";
import {
  UploadFields,
  FinalizeResponse,
  uploadVideoViaSignedUrl,
} from "./upload";

const CHUNK_SIZE = 8 * 1024 * 1024; // 8 MiB per chunk (must be a multiple of 256 KiB)
const MAX_CHUNK_RETRIES = 5;
// Files at/above this size use the resumable chunked path; smaller ones use a
// single PUT (simpler, and a blip just means re-sending one small request).
const RESUMABLE_THRESHOLD = 32 * 1024 * 1024; // 32 MiB

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
 * Upload a video the best way for its size: large files go through the
 * resumable chunked path (survives mobile network drops); small files use the
 * simpler single-PUT signed URL. Both upload directly to GCS, bypassing Cloud
 * Run's 32 MiB request-body limit.
 */
export function uploadVideo(
  file: File,
  fields: UploadFields,
  onProgress?: (pct: number) => void
): Promise<FinalizeResponse> {
  if (file.size >= RESUMABLE_THRESHOLD) {
    return uploadVideoResumable(file, fields, onProgress);
  }
  return uploadVideoViaSignedUrl(file, fields, onProgress);
}
