import { useEffect } from "react";

/**
 * Guard an in-progress upload against accidental interruption.
 *
 * While `active` is true:
 *  - a `beforeunload` handler warns the user if they try to close the tab,
 *    refresh, or navigate away (the browser shows its native "Leave site?"
 *    dialog), and
 *  - a screen Wake Lock keeps the device awake so a phone screen locking
 *    can't suspend/throttle the upload mid-flight.
 *
 * Both are best-effort: Wake Lock is unsupported on some browsers and is
 * wrapped so it never throws. Everything is torn down when `active` goes
 * false or the component unmounts.
 */
export function useUploadGuard(active: boolean): void {
  useEffect(() => {
    if (!active) return;

    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      // Required for Chrome to actually show the prompt.
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);

    // Screen Wake Lock — keep the screen on during the upload. Typed loosely
    // because navigator.wakeLock isn't in older TS DOM lib definitions.
    let wakeLock: { release: () => Promise<void> } | null = null;
    let released = false;
    const nav = navigator as Navigator & {
      wakeLock?: { request: (type: "screen") => Promise<{ release: () => Promise<void> }> };
    };

    const acquire = async () => {
      try {
        if (nav.wakeLock) {
          const lock = await nav.wakeLock.request("screen");
          if (released) {
            void lock.release();
          } else {
            wakeLock = lock;
          }
        }
      } catch {
        // Wake Lock can be rejected (e.g. tab not visible); harmless.
      }
    };

    // Re-acquire if the tab is hidden then shown again (the lock auto-releases
    // when a tab loses visibility).
    const onVisibility = () => {
      if (document.visibilityState === "visible") void acquire();
    };
    document.addEventListener("visibilitychange", onVisibility);
    void acquire();

    return () => {
      released = true;
      window.removeEventListener("beforeunload", onBeforeUnload);
      document.removeEventListener("visibilitychange", onVisibility);
      if (wakeLock) void wakeLock.release();
    };
  }, [active]);
}
