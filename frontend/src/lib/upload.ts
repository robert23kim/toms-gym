import axios from "axios";
import { API_URL } from "../config";

export interface UploadFields {
  competition_id: string;
  lift_type: string;
  weight: string;
  user_id?: string;
  email?: string;
}

export interface FinalizeResponse {
  message?: string;
  url: string;
  attempt_id?: string;
  user_competition_id?: string;
  user_id?: string;
}

interface SignedUrlResponse {
  upload_url: string;
  object_name: string;
  public_url: string;
  content_type: string;
}

/** Which of the three stages an upload error came from, for telemetry. */
export type UploadStage = "signed-url" | "gcs-put" | "finalize";

/** Tag an error with the stage it failed at, then rethrow it. */
function failAtStage(err: unknown, stage: UploadStage): never {
  if (err && typeof err === "object") {
    (err as Record<string, unknown>).uploadStage = stage;
  }
  throw err;
}

/**
 * Upload a video directly to GCS via a signed URL, bypassing Cloud Run's
 * 32 MiB request-body limit (which silently 413s large phone videos before
 * they reach the backend), then finalize the attempt.
 *
 * Three stages, each tagged on failure via `err.uploadStage`:
 *   1. signed-url — ask the backend for a signed PUT URL
 *   2. gcs-put    — PUT the file straight to GCS (no size limit)
 *   3. finalize   — backend creates the Attempt and returns its id
 */
export async function uploadVideoViaSignedUrl(
  file: File,
  fields: UploadFields,
  onProgress?: (pct: number) => void
): Promise<FinalizeResponse> {
  const contentType = file.type || "application/octet-stream";

  let signed: SignedUrlResponse;
  try {
    const res = await axios.post<SignedUrlResponse>(`${API_URL}/upload/signed-url`, {
      filename: file.name,
      content_type: contentType,
    });
    signed = res.data;
  } catch (err) {
    return failAtStage(err, "signed-url");
  }

  try {
    // PUT raw bytes straight to GCS. Content-Type MUST match what was signed,
    // or GCS rejects the request with a 403 SignatureDoesNotMatch.
    await axios.put(signed.upload_url, file, {
      headers: { "Content-Type": signed.content_type },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    });
  } catch (err) {
    return failAtStage(err, "gcs-put");
  }

  try {
    const res = await axios.post<FinalizeResponse>(`${API_URL}/upload/finalize`, {
      object_name: signed.object_name,
      public_url: signed.public_url,
      ...fields,
    });
    return res.data;
  } catch (err) {
    return failAtStage(err, "finalize");
  }
}
