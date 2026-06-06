import { API_URL } from "../config";

/**
 * Report a frontend error to the backend for Cloud Run log visibility.
 * Fire-and-forget — never throws, never blocks the UI.
 */
export function reportError(
  page: string,
  action: string,
  error: unknown,
  details?: Record<string, unknown>
): void {
  try {
    const errorMessage =
      error instanceof Error
        ? error.message
        : typeof error === "string"
        ? error
        : JSON.stringify(error);

    const payload = {
      page,
      action,
      error: errorMessage,
      details: details || {},
      userAgent: navigator.userAgent,
      url: window.location.href,
    };

    fetch(`${API_URL}/log-error`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch(() => {
      // Silently ignore — telemetry must never break the app
    });
  } catch {
    // Silently ignore
  }
}

/** Minimal axios-error shape, narrowed without `any`. */
interface AxiosLikeError {
  response?: { status?: number; data?: { error?: string } };
  request?: unknown;
  code?: string;
  message?: string;
}

/**
 * Report a failed video upload with diagnostic detail.
 *
 * Upload failures often never reach the backend at all — the request can be
 * rejected by Cloud Run's 32 MiB request-body limit, dropped on a flaky mobile
 * connection, or blocked by CORS — so the server has no record of them. This
 * captures the client-side context (crucially the file size and type) so an
 * oversized phone video can be told apart from a genuine server error.
 *
 * `phase` discriminates where it broke:
 *   - "http-error"  → server responded with a non-2xx status
 *   - "no-response" → request was sent but nothing came back (network/CORS/size)
 *   - "setup"       → threw before the request was even made
 */
export function reportUploadError(
  page: string,
  file: File | null,
  err: unknown,
  extra?: Record<string, unknown>
): void {
  const axiosErr = (err ?? {}) as AxiosLikeError;

  let phase: "http-error" | "no-response" | "setup";
  if (axiosErr.response) {
    phase = "http-error";
  } else if (axiosErr.request) {
    phase = "no-response";
  } else {
    phase = "setup";
  }

  reportError(page, "video-upload", err, {
    phase,
    httpStatus: axiosErr.response?.status ?? null,
    serverError: axiosErr.response?.data?.error ?? null,
    errorCode: axiosErr.code ?? null,
    fileSizeBytes: file?.size ?? null,
    fileSizeMB: file ? Number((file.size / (1024 * 1024)).toFixed(2)) : null,
    fileType: file?.type || null,
    fileName: file?.name ?? null,
    ...extra,
  });
}
