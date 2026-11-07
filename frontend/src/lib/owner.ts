export const OWNER_EMAIL = "toka778@gmail.com";

const CACHE_KEY = "ownerCheck";

export const isOwnerEmail = (email: string | null | undefined): boolean =>
  typeof email === "string" && email.trim().toLowerCase() === OWNER_EMAIL;

/** Cached verdict for this userId, or null when none or for another user. */
export const readOwnerCache = (userId: string): boolean | null => {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (typeof raw !== "string") return null;
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const { userId: cachedId, owner } = parsed as { userId?: unknown; owner?: unknown };
    return cachedId === userId && typeof owner === "boolean" ? owner : null;
  } catch {
    return null;
  }
};

export const writeOwnerCache = (userId: string, owner: boolean): void => {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ userId, owner }));
  } catch {
    // storage unavailable: the next load fetches again
  }
};
