import { API_URL, APP_BUILD } from "../config";
import { takeDeadJourney } from "./uploadJourney";

/**
 * Frontend telemetry → backend /log-error → Cloud Run logs (FRONTEND_ERROR).
 *
 * Transport rules learned the hard way: reports are often fired by a page that
 * is about to die (crash, reload, navigation), so they go out via
 * `navigator.sendBeacon` — the only transport the browser guarantees to
 * deliver after unload. Beacons can only carry CORS-safelisted content types
 * cross-origin, so the JSON ships as text/plain and the backend sniffs it.
 * Fetch (with keepalive) is the fallback for browsers without sendBeacon.
 */

const MAX_GLOBAL_REPORTS_PER_PAGE = 10;
const BOOT_PING_KEY = "tg:boot-pinged";

interface CapacitorGlobal {
  isNativePlatform?: () => boolean;
}

function platform(): string {
  const cap = (window as { Capacitor?: CapacitorGlobal }).Capacitor;
  return cap?.isNativePlatform?.() ? "capacitor" : "web";
}

function navigationType(): string {
  try {
    const nav = performance.getEntriesByType("navigation")[0] as
      | PerformanceNavigationTiming
      | undefined;
    return nav?.type ?? "unknown";
  } catch {
    return "unknown";
  }
}

/** Fire-and-forget delivery that survives page unload. Never throws. */
function sendTelemetry(payload: Record<string, unknown>): void {
  const url = `${API_URL}/log-error`;
  const body = JSON.stringify(payload);
  try {
    if (typeof navigator.sendBeacon === "function") {
      // text/plain keeps the beacon CORS-safelisted (no preflight to miss).
      if (navigator.sendBeacon(url, new Blob([body], { type: "text/plain" }))) {
        return;
      }
    }
  } catch {
    // Fall through to fetch.
  }
  try {
    const p = fetch(url, {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body,
      keepalive: true,
    });
    if (p && typeof p.catch === "function") {
      p.catch(() => {
        // Silently ignore — telemetry must never break the app.
      });
    }
  } catch {
    // Silently ignore
  }
}

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

    sendTelemetry({
      page,
      action,
      error: errorMessage,
      details: details || {},
      userAgent: navigator.userAgent,
      url: window.location.href,
      build: APP_BUILD,
      platform: platform(),
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
  /** Set by the upload flow: which stage failed (signed-url/gcs-put/finalize…). */
  uploadStage?: string;
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
    uploadStage: axiosErr.uploadStage ?? null,
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

let initialized = false;

/**
 * Boot-time telemetry. Call once, as early as possible:
 *  - reports an upload journey that died with the previous page (the only way
 *    to observe a crash/OOM-kill — the dying page can't report itself),
 *  - sends one "boot" ping per session (positive signal + build stamp, so
 *    stale clients in the wild are queryable),
 *  - installs global error/unhandledrejection/resource-failure reporters.
 */
export function initTelemetry(): void {
  if (initialized) return;
  initialized = true;

  try {
    const dead = takeDeadJourney();
    if (dead) {
      reportError(
        "UploadVideo",
        "upload-died",
        `upload session died at stage=${dead.stage}`,
        { ...dead, navigationType: navigationType() }
      );
    }
  } catch {
    /* never block boot */
  }

  try {
    if (!window.sessionStorage.getItem(BOOT_PING_KEY)) {
      window.sessionStorage.setItem(BOOT_PING_KEY, "1");
      reportError("app", "boot", "-", { navigationType: navigationType() });
    }
  } catch {
    /* sessionStorage blocked — skip the ping */
  }

  let reportsLeft = MAX_GLOBAL_REPORTS_PER_PAGE;
  const budgeted = (fn: () => void): void => {
    if (reportsLeft <= 0) return;
    reportsLeft -= 1;
    fn();
  };

  // Capture phase so failed <script>/<link>/<img> loads (which don't bubble)
  // are seen too — that's how a stale build's purged-chunk 404 shows up.
  window.addEventListener(
    "error",
    (event: Event) => {
      if (event instanceof ErrorEvent) {
        budgeted(() =>
          reportError("window", "window-error", event.error ?? event.message)
        );
      } else {
        const target = event.target as { src?: string; href?: string; tagName?: string } | null;
        const resource = target?.src || target?.href;
        if (resource) {
          budgeted(() =>
            reportError("window", "resource-error", `failed to load ${resource}`, {
              tagName: target?.tagName ?? null,
            })
          );
        }
      }
    },
    true
  );

  window.addEventListener("unhandledrejection", (event) => {
    budgeted(() =>
      reportError("window", "unhandled-rejection", event.reason ?? "unknown")
    );
  });
}
