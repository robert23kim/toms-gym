import axios from "axios";
import { UploadFields, FinalizeResponse } from "./upload";
import { API_URL } from "../config";

/** 16 MiB parts — large enough to keep per-part overhead low, small enough to
 * keep the 4-wide concurrency pool busy on typical phone videos. */
const PART_SIZE = 16 * 1024 * 1024;

/** Max parts uploaded to GCS in parallel. */
const CONCURRENCY = 4;

/** Which stage a parallel-upload error came from, for telemetry. Mirrors the
 * UploadStage tagging in upload.ts. */
type ParallelUploadStage =
  | "composite-sign"
  | "gcs-parts"
  | "composite-complete"
  | "finalize";

/** Tag an error with the stage it failed at, then rethrow it. */
function failAtStage(err: unknown, stage: ParallelUploadStage): never {
  if (err && typeof err === "object") {
    (err as Record<string, unknown>).uploadStage = stage;
  }
  throw err;
}

interface SignedPart {
  part_number: number;
  object_name: string;
  upload_url: string;
}

interface CompositeSignResponse {
  final_object: string;
  public_url: string;
  content_type: string;
  parts: SignedPart[];
}

interface CompositeCompleteResponse {
  public_url: string;
}

/** Run `worker` over `items` with at most `limit` in flight at once. */
async function runPool<T>(
  items: readonly T[],
  limit: number,
  worker: (item: T, index: number) => Promise<void>
): Promise<void> {
  let next = 0;
  async function pump(): Promise<void> {
    while (next < items.length) {
      const i = next++;
      await worker(items[i], i);
    }
  }
  const runners: Promise<void>[] = [];
  for (let i = 0; i < Math.min(limit, items.length); i++) {
    runners.push(pump());
  }
  await Promise.all(runners);
}

/**
 * Upload a video to GCS in parallel via a composite (multi-part) upload, then
 * finalize the attempt.
 *
 * The file is split into N 16 MiB byte-range parts. Each part is PUT to its own
 * signed URL as a separate GCS object, up to 4 in parallel; the backend then
 * GCS-composes the parts, in order, into the final object. This parallelizes
 * the network transfer of large phone videos that a single serial PUT would
 * stream one stream at a time.
 *
 * Four stages, each tagged on failure via `err.uploadStage`:
 *   1. composite-sign     — ask the backend for N signed PUT URLs
 *   2. gcs-parts          — PUT each byte-range part straight to GCS
 *   3. composite-complete — backend composes the parts into the final object
 *   4. finalize           — backend creates the Attempt and returns its id
 */
export async function uploadVideoParallel(
  file: File,
  fields: UploadFields,
  onProgress?: (pct: number) => void
): Promise<FinalizeResponse> {
  const contentType = file.type || "application/octet-stream";
  const parts = Math.max(1, Math.ceil(file.size / PART_SIZE));

  let signed: CompositeSignResponse;
  try {
    const res = await axios.post<CompositeSignResponse>(
      `${API_URL}/upload/composite/sign`,
      {
        filename: file.name,
        content_type: contentType,
        parts,
      }
    );
    signed = res.data;
  } catch (err) {
    return failAtStage(err, "composite-sign");
  }

  // Track per-part uploaded bytes so we can report a single aggregate 0..100.
  const loadedPerPart = new Array<number>(signed.parts.length).fill(0);
  const totalBytes = file.size;
  const reportProgress = () => {
    if (!onProgress || totalBytes <= 0) return;
    const loaded = loadedPerPart.reduce((sum, n) => sum + n, 0);
    onProgress(Math.min(100, Math.round((loaded / totalBytes) * 100)));
  };

  try {
    await runPool(signed.parts, CONCURRENCY, async (part, index) => {
      const start = index * PART_SIZE;
      const end = Math.min(start + PART_SIZE, file.size);
      const chunk = file.slice(start, end);
      // Content-Type MUST match what was signed, or GCS rejects the PUT with a
      // 403 SignatureDoesNotMatch.
      await axios.put(part.upload_url, chunk, {
        headers: { "Content-Type": contentType },
        onUploadProgress: (e) => {
          loadedPerPart[index] = e.loaded;
          reportProgress();
        },
      });
      // Make sure a completed part counts its full size even if the final
      // progress event under-reported.
      loadedPerPart[index] = end - start;
      reportProgress();
    });
  } catch (err) {
    return failAtStage(err, "gcs-parts");
  }

  // Parts are listed in upload order; preserve that order for compose.
  const partObjectNames = signed.parts
    .slice()
    .sort((a, b) => a.part_number - b.part_number)
    .map((p) => p.object_name);

  try {
    await axios.post<CompositeCompleteResponse>(
      `${API_URL}/upload/composite/complete`,
      {
        final_object: signed.final_object,
        content_type: signed.content_type,
        part_object_names: partObjectNames,
      }
    );
  } catch (err) {
    return failAtStage(err, "composite-complete");
  }

  try {
    const res = await axios.post<FinalizeResponse>(`${API_URL}/upload/finalize`, {
      object_name: signed.final_object,
      public_url: signed.public_url,
      ...fields,
    });
    return res.data;
  } catch (err) {
    return failAtStage(err, "finalize");
  }
}
