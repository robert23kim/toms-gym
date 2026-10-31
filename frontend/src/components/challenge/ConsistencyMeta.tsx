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
