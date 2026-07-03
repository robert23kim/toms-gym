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
  };
}

/** Sticky-CTA text: goal-reframed when the viewer is entered, else the default. */
export function ctaLabelFor(
  standing: Standing | null,
  metric: ChallengeMetric,
): string {
  return standing ? standing.ctaLabel : uploadCtaLabel(metric);
}
