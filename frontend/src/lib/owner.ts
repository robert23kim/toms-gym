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

const SPORT_CATEGORIES = new Set(["bowling", "golf"]);

/** Challenges with a bowling or golf category (gender entries ride along in every list); hidden from everyone but the owner. */
export const isSportChallenge = (c: { categories?: string[] }): boolean =>
  (c.categories ?? []).some((x) => SPORT_CATEGORIES.has(x.toLowerCase()));

export const visibleChallenges = <T extends { categories?: string[] }>(list: T[], isOwner: boolean): T[] =>
  isOwner ? list : list.filter((c) => !isSportChallenge(c));
