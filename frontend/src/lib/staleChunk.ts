const RELOAD_KEY = "staleChunkReloadedAt";
const RELOAD_WINDOW_MS = 60_000;

const recentlyReloaded = (): boolean => {
  try {
    const at = Number(sessionStorage.getItem(RELOAD_KEY) || 0);
    return Date.now() - at < RELOAD_WINDOW_MS;
  } catch {
    return false;
  }
};

const markReloaded = (): void => {
  try {
    sessionStorage.setItem(RELOAD_KEY, String(Date.now()));
  } catch {
    // storage unavailable; reload anyway
  }
};

/**
 * After a deploy, hashed chunk names change and a tab that loaded the old
 * index.html fails lazy imports with "Failed to fetch dynamically imported
 * module". Vite raises `vite:preloadError` for that; reload once to pick up
 * the new manifest. The window guard avoids a reload loop if the error is
 * something else.
 */
export function handleStaleChunk(event: Event): boolean {
  if (recentlyReloaded()) return false;
  event.preventDefault();
  markReloaded();
  window.location.reload();
  return true;
}

export function installStaleChunkReload(): void {
  window.addEventListener("vite:preloadError", handleStaleChunk);
}
