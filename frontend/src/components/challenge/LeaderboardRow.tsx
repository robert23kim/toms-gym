import React from "react";
import { Link } from "react-router-dom";
import { Play } from "lucide-react";
import type { ChallengeLeaderboardRow, ChallengeMetric } from "../../lib/types";
import { getGolfAvatar } from "../../lib/api";
import { formatScoreValue, scoreUnit } from "./metric";

interface LeaderboardRowProps {
  row: ChallengeLeaderboardRow;
  metric: ChallengeMetric;
  /** Clip route for this entrant's best attempt, or null if not resolvable. */
  clipHref: string | null;
  /** Attempt-history accordion (optional): chip shows at attemptCount > 1. */
  attemptCount?: number;
  expanded?: boolean;
  onToggleAttempts?: () => void;
}

function formatDate(date: string | null): string {
  if (!date) return "";
  // Treat the ISO date as local midnight so the day doesn't shift under offset.
  const d = new Date(`${date}T00:00:00`);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/**
 * A single "Everyone else" row. Mobile is a flex row (rank · 44×44 clip
 * thumbnail · name+date · score, #2b); desktop (lg:) becomes a 4-column grid
 * aligned to the table header — rank · avatar+name · score · 30×30 clip button
 * (#1b). One clip element is grid-placed into the CLIP column on desktop so we
 * never render two clip links.
 */
const LeaderboardRow: React.FC<LeaderboardRowProps> = ({
  row,
  metric,
  clipHref,
  attemptCount,
  expanded = false,
  onToggleAttempts,
}) => {
  const dimmed = row.score <= 0;
  const showAttemptsChip = (attemptCount ?? 0) > 1 && !!onToggleAttempts;

  const thumb = (
    <div className="relative h-11 w-11 flex-none overflow-hidden rounded-lg bg-gradient-to-br from-[#2a3340] to-[#171b22] lg:h-[30px] lg:w-[30px]">
      {row.clip_url ? (
        <video
          src={row.clip_url}
          muted
          playsInline
          preload="metadata"
          className="h-full w-full object-cover"
          onLoadedData={(e) => {
            (e.target as HTMLVideoElement).currentTime = 0.5;
          }}
        />
      ) : null}
      <div className="absolute inset-0 flex items-center justify-center bg-black/20">
        <Play className="ml-px h-3.5 w-3.5 text-white/90 lg:h-3 lg:w-3" fill="currentColor" />
      </div>
    </div>
  );

  const clip = clipHref ? (
    <Link
      to={clipHref}
      aria-label={`Watch ${row.name || "athlete"}'s clip`}
      className="lg:col-start-4 lg:row-start-1 lg:justify-self-end"
    >
      {thumb}
    </Link>
  ) : (
    <div className="lg:col-start-4 lg:row-start-1 lg:justify-self-end">{thumb}</div>
  );

  return (
    <div
      data-testid="leaderboard-row"
      data-rank={row.rank}
      className="flex items-center gap-3 px-3.5 py-2.5 lg:grid lg:grid-cols-[52px_1fr_120px_90px] lg:items-center lg:gap-3.5 lg:px-[18px] lg:py-3.5"
    >
      <div className="w-[18px] text-sm font-bold tabular-nums text-white/40 lg:col-start-1 lg:row-start-1 lg:w-auto lg:text-[15px] lg:text-white/50">
        {row.rank}
      </div>
      {clip}
      <div className="min-w-0 flex-1 lg:col-start-2 lg:row-start-1 lg:flex lg:items-center lg:gap-2.5">
        <img
          src={getGolfAvatar(row.name, row.user_id)}
          alt=""
          aria-hidden="true"
          className="hidden h-[30px] w-[30px] flex-none rounded-full bg-[#2a2f3a] object-cover lg:block"
        />
        <div className="min-w-0">
          <div className={`truncate text-sm font-semibold lg:text-[14.5px] ${dimmed ? "text-white/50" : ""}`}>
            {row.name || "Athlete"}
          </div>
          <div className="text-[11px] text-white/40 lg:hidden">
            {dimmed ? "No entry yet" : formatDate(row.date)}
          </div>
        </div>
        {showAttemptsChip && (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onToggleAttempts!();
            }}
            aria-expanded={expanded}
            className="ml-2 shrink-0 rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-white/60 hover:text-white hover:bg-white/10 transition-colors"
          >
            {attemptCount} attempts {expanded ? "▴" : "▾"}
          </button>
        )}
      </div>
      <span className="font-bold tracking-tight tabular-nums text-base lg:col-start-3 lg:row-start-1 lg:text-[17px]">
        {dimmed ? (
          <span className="text-white/30">—</span>
        ) : (
          <>
            {formatScoreValue(row.score, metric)}
            <span className="ml-0.5 text-[60%] font-semibold text-white/50">
              {scoreUnit(metric)}
            </span>
          </>
        )}
      </span>
    </div>
  );
};

export default LeaderboardRow;
