export interface RankSnapshot {
  rank: number;
  best: number;
  at: string;
}

export interface RankShift {
  kind: "up" | "down";
  from: number;
  to: number;
}

type StorageLike = Pick<Storage, "getItem" | "setItem">;

const key = (challengeId: string, userId: string): string => `rank:${challengeId}:${userId}`;

export function readRank(storage: StorageLike, challengeId: string, userId: string): RankSnapshot | null {
  try {
    const raw = storage.getItem(key(challengeId, userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<RankSnapshot>;
    return typeof parsed.rank === "number" && typeof parsed.best === "number"
      ? { rank: parsed.rank, best: parsed.best, at: String(parsed.at ?? "") }
      : null;
  } catch {
    return null;
  }
}

export function writeRank(storage: StorageLike, challengeId: string, userId: string, snap: RankSnapshot): void {
  try {
    storage.setItem(key(challengeId, userId), JSON.stringify(snap));
  } catch {
    /* storage unavailable: the moment simply does not fire next visit */
  }
}

export function rankChange(prev: RankSnapshot | null, current: { rank: number }): RankShift | null {
  if (!prev || prev.rank === current.rank) return null;
  return { kind: prev.rank > current.rank ? "up" : "down", from: prev.rank, to: current.rank };
}
