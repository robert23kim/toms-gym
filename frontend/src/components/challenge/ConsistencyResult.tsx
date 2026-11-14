import React from "react";
import { Link } from "react-router-dom";
import type { ChallengeLeaderboard, ConsistencyRules } from "../../lib/types";
import { boardReps, type RepReport } from "../../lib/cleanReps";
import { formatScoreValue } from "./metric";
import { startDayLabel } from "./ConsistencyHero";
import { inChallenge } from "../../lib/standing";

export type ConsistencyReport = RepReport & { total_in_plank_s?: number | null };

const REP_COUNTED = new Set(["situp", "pushup", "squat"]);

/** Lifts one attempt adds to the club; mirrors backend consistency.attempt_lifts. */
export function attemptLifts(
  report: ConsistencyReport | null | undefined,
  rules: Pick<ConsistencyRules, "plank_seconds_per_lift">,
): number | null {
  if (!report) return null;
  const type = (report.lift_type || "").trim().toLowerCase();
  if (type === "auto") return null;
  if (type === "plank") {
    const held = report.total_in_plank_s;
    if (held == null) return null;
    return Math.floor(held / rules.plank_seconds_per_lift);
  }
  if (REP_COUNTED.has(type)) return boardReps(report);
  return 0;
}

const plural = (n: number, word: string) => `${formatScoreValue(n, "consistency")} ${word}${n === 1 ? "" : "s"}`;

const HAS_OFFSET = /([zZ]|[+-]\d\d:?\d\d)$/;

/** 1-based challenge week of an upload instant (<= 0 before week 1); mirrors backend consistency.week_of. */
export function attemptWeek(
  at: string | null | undefined,
  rules: Pick<ConsistencyRules, "tz" | "week_start">,
): number | null {
  if (!at) return null;
  const instant = new Date(HAS_OFFSET.test(at) ? at : `${at}Z`);
  if (Number.isNaN(instant.getTime())) return null;
  const local = new Intl.DateTimeFormat("en-CA", {
    timeZone: rules.tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(instant);
  const day = Date.parse(`${local}T00:00:00Z`);
  const start = Date.parse(`${rules.week_start}T00:00:00Z`);
  if (Number.isNaN(day) || Number.isNaN(start)) return null;
  return Math.floor((day - start) / (7 * 86_400_000)) + 1;
}

interface ClubArgs {
  board: ChallengeLeaderboard;
  userId: string | null | undefined;
  report: ConsistencyReport | null | undefined;
  attemptAt?: string | null;
}

function clubAttempt({ board, userId, report, attemptAt }: ClubArgs) {
  const block = board.consistency!;
  const lifts = attemptLifts(report, block.rules) ?? 0;
  const row = userId ? board.rows.find((r) => String(r.user_id) === String(userId)) : undefined;
  const week = attemptWeek(attemptAt, block.rules);
  const warmup = block.status === "upcoming" || (week != null && week <= 0);
  const afterEnd = week != null && week > block.rules.weeks;
  const inLiveWeek = block.status === "live" && (week == null || week === block.week_index);
  return { block, lifts, row, week, warmup, afterEnd, inLiveWeek };
}

const firstName = (name: string | null | undefined) => (name || "").trim().split(/\s+/)[0] || "Someone";

/** Share text for a 100 Club video: lifts and the week, never a rank. */
export function consistencyShareText(
  args: ClubArgs & { isOwner: boolean; athleteName?: string | null; challengeName?: string | null },
): string {
  const { lifts, row, warmup, inLiveWeek } = clubAttempt(args);
  const who = args.isOwner ? "I" : firstName(row?.name ?? args.athleteName);
  const what = warmup ? `logged ${plural(lifts, "warm-up lift")}` : `banked ${plural(lifts, "lift")}`;
  const w = row?.this_week;
  const progress = !warmup && inLiveWeek && w ? ` — ${formatScoreValue(w.lifts, "consistency")} / ${w.quota} this week` : "";
  return `${who} ${what} ${inChallenge(args.challengeName)}${progress}. ${args.isOwner ? "Join me:" : "Join in:"}`;
}

interface Props {
  board: ChallengeLeaderboard;
  userId: string | null | undefined;
  report: ConsistencyReport | null | undefined;
  /** Attempt upload instant; places it in its own week. Unknown means the live week. */
  attemptAt?: string | null;
  isOwner?: boolean;
  athleteName?: string | null;
  className?: string;
}

/** Result-page block on a 100 Club board: what this upload added and where the week stands. */
const ConsistencyResult: React.FC<Props> = ({
  board,
  userId,
  report,
  attemptAt,
  isOwner = true,
  athleteName,
  className = "",
}) => {
  if (!board.consistency) return null;
  const { block, lifts, row, week, warmup, afterEnd, inLiveWeek } = clubAttempt({ board, userId, report, attemptAt });
  const thisWeek = row?.this_week;

  let headline: string;
  if (attemptLifts(report, block.rules) === null && (report?.lift_type || "").trim().toLowerCase() === "auto") {
    headline = "Not counted until the lift type is set";
  } else if (block.status === "upcoming") {
    headline = `+${plural(lifts, "warm-up lift")} · scoring starts ${startDayLabel(block.rules.week_start)}`;
  } else if (warmup) {
    headline = `+${plural(lifts, "warm-up lift")} · not scored`;
  } else if (afterEnd) {
    headline = `+${plural(lifts, "lift")} · after the last week, not scored`;
  } else if (week != null && !inLiveWeek) {
    headline = `+${plural(lifts, "lift")} banked in week ${week}`;
  } else {
    headline = `+${plural(lifts, "lift")} banked`;
  }

  let weekText: string | null = null;
  if (block.status === "live" && inLiveWeek && !warmup && thisWeek) {
    const progress = `${formatScoreValue(thisWeek.lifts, "consistency")} / ${thisWeek.quota} this week · ${block.days_left} day${block.days_left === 1 ? "" : "s"} left`;
    weekText = thisWeek.met ? `Quota met · ${progress}` : progress;
  } else if (block.status === "ended" && row) {
    weekText = `Final: ${formatScoreValue(row.score, "consistency")} pts`;
  }
  if (weekText && !isOwner) weekText = `${firstName(row?.name ?? athleteName)}: ${weekText}`;

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
