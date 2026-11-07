import React from "react";
import { Link } from "react-router-dom";
import type { ChallengeLeaderboard, ConsistencyRules } from "../../lib/types";
import { boardReps, type RepReport } from "../../lib/cleanReps";
import { formatScoreValue } from "./metric";
import { startDayLabel } from "./ConsistencyHero";

export type ConsistencyReport = RepReport & { total_in_plank_s?: number | null };

const REP_COUNTED = new Set(["situp", "pushup", "squat"]);

/** Lifts one attempt adds to the club; mirrors backend consistency.attempt_lifts. */
export function attemptLifts(
  report: ConsistencyReport | null | undefined,
  rules: Pick<ConsistencyRules, "plank_seconds_per_lift">,
): number | null {
  if (!report) return null;
  const type = (report.lift_type || "").trim().toLowerCase();
  if (type === "plank") {
    const held = report.total_in_plank_s;
    if (held == null) return null;
    return Math.floor(held / rules.plank_seconds_per_lift);
  }
  if (REP_COUNTED.has(type)) return boardReps(report);
  return 0;
}

const plural = (n: number, word: string) => `${formatScoreValue(n, "consistency")} ${word}${n === 1 ? "" : "s"}`;

interface Props {
  board: ChallengeLeaderboard;
  userId: string | null | undefined;
  report: ConsistencyReport | null | undefined;
  className?: string;
}

/** Result-page block on a 100 Club board: what this upload added and where the week stands. */
const ConsistencyResult: React.FC<Props> = ({ board, userId, report, className = "" }) => {
  const block = board.consistency;
  if (!block) return null;
  const lifts = attemptLifts(report, block.rules) ?? 0;
  const row = userId ? board.rows.find((r) => String(r.user_id) === String(userId)) : undefined;
  const week = row?.this_week;

  const headline =
    block.status === "upcoming"
      ? `+${plural(lifts, "warm-up lift")} · scoring starts ${startDayLabel(block.rules.week_start)}`
      : `+${plural(lifts, "lift")} banked`;

  let weekText: string | null = null;
  if (block.status === "live" && week) {
    const progress = `${formatScoreValue(week.lifts, "consistency")} / ${week.quota} this week · ${block.days_left} day${block.days_left === 1 ? "" : "s"} left`;
    weekText = week.met ? `Quota met · ${progress}` : progress;
  } else if (block.status === "ended" && row) {
    weekText = `Final: ${formatScoreValue(row.score, "consistency")} pts`;
  }

  return (
    <div data-testid="consistency-result" className={`rounded-xl border border-accent/30 bg-accent/5 p-4 ${className}`}>
      <p className="text-lg font-semibold tabular-nums">{headline}</p>
      {weekText && <p className="mt-1 text-sm text-muted-foreground tabular-nums">{weekText}</p>}
      <Link to={`/challenges/${board.competition_id}`} className="mt-3 inline-block text-sm font-medium text-accent hover:underline">
        See the board →
      </Link>
    </div>
  );
};

export default ConsistencyResult;
