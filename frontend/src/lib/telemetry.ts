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
