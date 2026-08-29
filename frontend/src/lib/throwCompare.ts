export interface ThrowRow {
  attempt_id: string;
  created_at: string | null;
  entry_board: number | null;
}

export interface ThrowComparison {
  previousBoard: number;
  delta: number;
}

/** This throw's entry board against the athlete's most recent earlier throw that was tracked. */
export function compareThrow(rows: ThrowRow[], attemptId: string, entryBoard: number | null | undefined): ThrowComparison | null {
  if (entryBoard == null) return null;
  const me = rows.find((r) => r.attempt_id === attemptId);
  if (!me?.created_at) return null;
  const earlier = rows
    .filter((r) => r.attempt_id !== attemptId && r.entry_board != null && r.created_at && r.created_at < me.created_at)
    .sort((a, b) => (a.created_at! < b.created_at! ? 1 : -1));
  if (earlier.length === 0) return null;
  const previousBoard = earlier[0].entry_board as number;
  return { previousBoard, delta: Math.round(entryBoard - previousBoard) };
}

export function throwComparisonCopy(c: ThrowComparison): string {
  if (c.delta === 0) return `Same board as your last throw (${Math.round(c.previousBoard)})`;
  const n = Math.abs(c.delta);
  return `${n} board${n === 1 ? "" : "s"} ${c.delta > 0 ? "right" : "left"} of your last throw (${Math.round(c.previousBoard)})`;
}
