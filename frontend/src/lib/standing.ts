import type {
  ChallengeLeaderboard,
  ChallengeLeaderboardHistoryPoint,
  ChallengeLeaderboardRow,
  ChallengeMetric,
} from "./types";
import { formatScoreValue, scoreUnit, uploadCtaLabel } from "../components/challenge/metric";

// Pure, DB-free derivation of the viewer's "Your standing" from the leaderboard
// `rows` + their `user_id`. No server-side viewer awareness — everything the
// motivation layer needs (rank, best, trend delta, gap-to-next, CTA copy) is
// read off the ranked rows. Keeps the StandingCard dumb.

export interface Standing {
  /** The viewer's own row. */
  row: ChallengeLeaderboardRow;
  /** The viewer's rank (1-based). */
  rank: number;
  /** Total entrants — the "of N". */
  participantCount: number;
  /** The viewer's best score (row.score). */
  best: number;
  /** Chronological qualifying attempts — powers the sparkline. */
  history: ChallengeLeaderboardHistoryPoint[];
  /** Number of tries (history length) — the "in N tries" copy. */
  tries: number;
  /** last − first over history; null when there's a single attempt. */
  delta: number | null;
  /** True when the viewer is #1 (defend-your-lead state). */
  isLeader: boolean;
  /** Score the viewer must beat to pass the next entrant; null when leader. */
  gap: number | null;
  /** Fraction toward the next entrant's score, clamped 0..1; null when leader. */
  progress: number | null;
  /** Name of the entrant directly above; null when leader. */
  nextName: string | null;
  /** Rank of the entrant directly above; null when leader. */
  nextRank: number | null;
  /** Goal-reframed sticky-CTA text, e.g. "Beat your best — 18.6s". */
  ctaLabel: string;
  /** "You" row goal subtitle, e.g. "3.9s to reach #6"; null when leader. */
  goalSubtitle: string | null;
  /** Entrant directly below with the margin they must close; null when last. */
  below: Neighbour | null;
  /** Distance to the #3 score when off the podium; null on it. */
  podiumGap: number | null;
}

export interface Neighbour {
  name: string | null;
  rank: number;
  score: number;
  gap: number;
}

export interface PersonalBest {
  isPersonalBest: boolean;
  previousBest: number | null;
  belowBest: boolean;
}

/**
 * Derive the viewer's standing from the leaderboard. Returns `null` when the
 * viewer isn't entered — no `user_id`, no matching row, or a zero score
 * (joined but no qualifying attempt yet) — in which case the card is hidden and
 * the CTA falls back to the default upload label.
 */
export function deriveStanding(
  leaderboard: Pick<ChallengeLeaderboard, "rows" | "metric">,
  userId: string | null | undefined,
): Standing | null {
  const { rows, metric } = leaderboard;
  if (!userId) return null;

  const index = rows.findIndex((r) => String(r.user_id) === String(userId));
  if (index === -1) return null;

  const row = rows[index];
  if (!row.score || row.score <= 0) return null;

  const history = row.history || [];
  const tries = history.length;
  const delta =
    tries >= 2 ? history[tries - 1].score - history[0].score : null;

  const isLeader = index === 0;
  const above = isLeader ? null : rows[index - 1];

  let gap: number | null = null;
  let progress: number | null = null;
  let nextName: string | null = null;
  let nextRank: number | null = null;
  let goalSubtitle: string | null = null;

  if (above) {
    gap = above.score - row.score;
    progress =
      above.score > 0 ? Math.min(1, Math.max(0, row.score / above.score)) : 1;
    nextName = above.name;
    nextRank = above.rank;
    goalSubtitle = `${formatScoreValue(gap, metric)}${scoreUnit(metric)} to reach #${nextRank}`;
  }

  const ctaLabel = `Beat your best — ${formatScoreValue(row.score, metric)}${scoreUnit(metric)}`;

  const under = rows[index + 1];
  const below: Neighbour | null =
    under && under.score > 0
      ? { name: under.name, rank: under.rank, score: under.score, gap: row.score - under.score }
      : null;
  const third = rows[2];
  const podiumGap = row.rank > 3 && third ? Math.max(0, third.score - row.score) : null;

  return {
    row,
    rank: row.rank,
    participantCount: rows.length,
    best: row.score,
    history,
    tries,
    delta,
    isLeader,
    gap,
    progress,
    nextName,
    nextRank,
    ctaLabel,
    goalSubtitle,
    below,
    podiumGap,
  };
}

/** Score the athlete's *viewed* attempt contributes, in the board's metric. */
export function attemptScore(
  metric: ChallengeMetric,
  report: { total_reps?: number | null; total_in_plank_s?: number | null } | null | undefined,
  weight: number | null | undefined,
): number | null {
  if (metric === "reps") return report?.total_reps ?? null;
  if (metric === "time") return report?.total_in_plank_s ?? null;
  return weight ?? null;
}

export function metricForLift(liftType: string | null | undefined): ChallengeMetric {
  const t = (liftType || "").toLowerCase();
  if (t === "plank") return "time";
  if (t === "pushup") return "reps";
  return "weight";
}

/**
 * Whether the viewed attempt beat everything the athlete had logged before it.
 * One occurrence of the attempt's own score is removed from the history first,
 * so a repeat of the best is not a new best; ties are not a best either.
 */
export function personalBest(standing: Standing, score: number | null): PersonalBest {
  const others = standing.history.map((h) => h.score);
  if (score != null) {
    const i = others.indexOf(score);
    if (i >= 0) others.splice(i, 1);
  }
  const previousBest = others.length ? Math.max(...others) : null;
  return {
    isPersonalBest: score != null && previousBest != null && score > previousBest,
    previousBest,
    belowBest: score != null && score < standing.best,
  };
}

export function formatWithUnit(value: number, metric: ChallengeMetric): string {
  if (metric === "reps") {
    const n = Math.round(value);
    return `${n} rep${n === 1 ? "" : "s"}`;
  }
  return `${formatScoreValue(value, metric)}${scoreUnit(metric)}`;
}

/** Sticky-CTA text: goal-reframed when the viewer is entered, else the default. */
export function ctaLabelFor(
  standing: Standing | null,
  metric: ChallengeMetric,
): string {
  return standing ? standing.ctaLabel : uploadCtaLabel(metric);
}

/** Words to travel with a shared result link — written for a group chat. */
export function standingShareText(args: {
  standing: Standing;
  metric: ChallengeMetric;
  challengeName: string | null | undefined;
  athleteName: string | null | undefined;
  isOwner: boolean;
}): string {
  const { standing, metric, isOwner } = args;
  const where = args.challengeName ? `in the ${args.challengeName}` : "in this challenge";
  const score = formatWithUnit(standing.best, metric);
  const place = `#${standing.rank} of ${standing.participantCount}`;
  const last = standing.rank === standing.participantCount && standing.participantCount > 2;
  if (isOwner) {
    if (last) return `I just logged ${score} ${where}. Beat me:`;
    const dare = standing.isLeader ? "Take my spot:" : "Beat me:";
    return `I'm ${place} ${where} — ${score}. ${dare}`;
  }
  if (last) return `${(args.athleteName || "Someone").split(/\s+/)[0]} just logged ${score} ${where}. Can you beat it?`;
  const name = (args.athleteName || "Someone").split(/\s+/)[0];
  return `${name} is ${place} ${where} — ${score}. Can you beat it?`;
}
