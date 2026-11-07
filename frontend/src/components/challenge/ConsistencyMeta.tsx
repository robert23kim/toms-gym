import React from "react";
import type { ChallengeLeaderboardRow } from "../../lib/types";
import { formatScoreValue } from "./metric";

/** "42/150 this week" (plus a warm-up note before any lift scores); null off a 100 Club row. */
export const thisWeekText = (row: ChallengeLeaderboardRow): string | null => {
  if (!row.this_week) return null;
  const base = `${formatScoreValue(row.this_week.lifts, "consistency")}/${row.this_week.quota} this week`;
  const warmup = row.warmup_lifts ?? 0;
  if (row.score <= 0 && warmup > 0) return `${base} · ${formatScoreValue(warmup, "consistency")} warm-up`;
  return base;
};

/** Flame + current streak of met weeks; renders nothing at zero. */
export const StreakFlame: React.FC<{ streak?: number; className?: string }> = ({ streak, className = "" }) => {
  if (!streak || streak <= 0) return null;
  return (
    <span
      data-testid="streak-flame"
      role="img"
      aria-label={`${streak}-week streak`}
      className={`shrink-0 text-[11px] font-semibold text-amber-300 ${className}`}
    >
      <span aria-hidden="true">🔥</span>
      {streak}
    </span>
  );
};

/** The week-table toggle shows when the row has any scoring week. */
export const hasWeeks = (row: ChallengeLeaderboardRow): boolean => (row.weeks?.length ?? 0) > 0;

const TIEBREAKS: [string, (r: ChallengeLeaderboardRow) => number][] = [
  ["a longer streak", (r) => r.streak ?? 0],
  ["more weeks met", (r) => r.weeks_met ?? 0],
  ["more lifts this week", (r) => r.this_week?.lifts ?? 0],
];

/** One line naming the first points tie on the board and what breaks it; null when nobody ties. */
export const tieLine = (rows: ChallengeLeaderboardRow[]): string | null => {
  for (let i = 1; i < rows.length; i++) {
    const [a, b] = [rows[i - 1], rows[i]];
    if (a.score <= 0 || a.score !== b.score) continue;
    const first = a.name || "Athlete";
    const decider = TIEBREAKS.find(([, key]) => key(a) !== key(b));
    const reason = decider ? decider[0] : "name order";
    return `${first} and ${b.name || "Athlete"} are tied on points; ${reason} puts ${first} ahead.`;
  }
  return null;
};
