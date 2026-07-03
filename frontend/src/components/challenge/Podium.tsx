import React from "react";
import { Link } from "react-router-dom";
import { Play, Trophy } from "lucide-react";
import type { ChallengeLeaderboardRow, ChallengeMetric } from "../../lib/types";
import { getGolfAvatar } from "../../lib/api";
import { formatScoreValue, scoreUnit } from "./metric";

interface PodiumProps {
  /** Ranked rows (best-first). Only rows with score > 0 occupy pedestals. */
  rows: ChallengeLeaderboardRow[];
  metric: ChallengeMetric;
  /** Builds the clip route for an entrant's best attempt, or null if none. */
  getClipHref: (row: ChallengeLeaderboardRow) => string | null;
}

const MEDAL: Record<number, { color: string; name: string }> = {
  1: { color: "#f5c542", name: "gold" },
  2: { color: "#cbd5e1", name: "silver" },
  3: { color: "#cd7f52", name: "bronze" },
};

// Per-place geometry. Mobile values from #2b, desktop (lg:) scale-ups from #1b —
// larger avatars, pedestals, scores, and column widths on wide viewports.
const GEOMETRY: Record<
  number,
  { pedestal: string; avatar: string; score: string; col: string; rank: string; name: string }
> = {
  1: {
    pedestal: "h-24 lg:h-[132px]",
    avatar: "h-[54px] w-[54px] lg:h-[68px] lg:w-[68px]",
    score: "text-[23px] lg:text-[32px]",
    col: "w-[114px] lg:w-[210px]",
    rank: "text-base lg:text-[26px]",
    name: "text-xs lg:text-[15px]",
  },
  2: {
    pedestal: "h-[70px] lg:h-24",
    avatar: "h-11 w-11 lg:h-14 lg:w-14",
    score: "text-[18px] lg:text-[26px]",
    col: "w-[104px] lg:w-[200px]",
    rank: "text-sm lg:text-[22px]",
    name: "text-xs lg:text-sm",
  },
  3: {
    pedestal: "h-14 lg:h-[76px]",
    avatar: "h-10 w-10 lg:h-[52px] lg:w-[52px]",
    score: "text-[17px] lg:text-[24px]",
    col: "w-[104px] lg:w-[200px]",
    rank: "text-sm lg:text-[20px]",
    name: "text-xs lg:text-sm",
  },
};

const PodiumColumn: React.FC<{
  row: ChallengeLeaderboardRow;
  metric: ChallengeMetric;
  clipHref: string | null;
}> = ({ row, metric, clipHref }) => {
  const medal = MEDAL[row.rank];
  const geo = GEOMETRY[row.rank];
  const isChampion = row.rank === 1;

  const avatar = (
    <div className={`relative mb-2 lg:mb-2.5 ${geo.avatar}`}>
      <img
        src={getGolfAvatar(row.name, row.user_id)}
        alt={row.name || "Athlete"}
        className="h-full w-full rounded-full border-[2.5px] bg-[#2a2f3a] object-cover lg:border-[3px]"
        style={{ borderColor: medal.color }}
      />
      {clipHref && (
        <span
          data-testid="podium-play-badge"
          className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-[#2f7bf6] lg:h-6 lg:w-6"
          style={{ border: "2px solid #0a0a0b" }}
        >
          <Play className="ml-px h-2.5 w-2.5 text-white lg:h-3 lg:w-3" fill="currentColor" />
        </span>
      )}
    </div>
  );

  return (
    <div
      data-testid={`podium-place-${row.rank}`}
      className={`flex flex-col items-center ${geo.col}`}
    >
      {isChampion && (
        <Trophy
          data-testid="podium-crown"
          className="mb-1 h-[18px] w-[18px] lg:mb-1.5 lg:h-[22px] lg:w-[22px]"
          style={{ color: "#f5c542" }}
          fill="#f5c542"
        />
      )}
      {clipHref ? (
        <Link to={clipHref} aria-label={`Watch ${row.name || "athlete"}'s clip`}>
          {avatar}
        </Link>
      ) : (
        avatar
      )}
      <div className={`mb-0.5 max-w-full truncate text-center font-semibold ${geo.name}`}>
        {row.name || "Athlete"}
      </div>
      <div
        data-testid={`podium-score-${row.rank}`}
        className={`mb-2 font-bold tracking-tight tabular-nums lg:mb-3 ${geo.score}`}
        style={{ color: medal.color }}
      >
        {formatScoreValue(row.score, metric)}
        <span className="ml-0.5 text-[55%] opacity-80">{scoreUnit(metric)}</span>
      </div>
      <div
        data-testid={`podium-pedestal-${row.rank}`}
        data-medal={medal.name}
        className={`flex w-full items-start justify-center rounded-t-[10px] pt-2 font-bold tracking-tight lg:rounded-t-[12px] lg:pt-3 ${geo.pedestal} ${geo.rank}`}
        style={{
          color: medal.color,
          background: `linear-gradient(180deg, ${medal.color}33, ${medal.color}08)`,
          border: `1px solid ${medal.color}55`,
          borderBottom: "none",
        }}
      >
        {row.rank}
      </div>
    </div>
  );
};

/** Top-3 podium, columns ordered 2 · 1 · 3, bottom-aligned. Renders only the
 * places that are actually occupied (thin states fill fewer columns). */
const Podium: React.FC<PodiumProps> = ({ rows, metric, getClipHref }) => {
  const byRank = new Map(rows.filter((r) => r.score > 0 && r.rank <= 3).map((r) => [r.rank, r]));
  const order = [2, 1, 3].filter((rank) => byRank.has(rank));

  if (order.length === 0) return null;

  return (
    <div data-testid="podium" className="mb-7 flex items-end justify-center gap-2 lg:mb-[38px] lg:mt-3.5 lg:gap-[18px]">
      {order.map((rank) => {
        const row = byRank.get(rank)!;
        return (
          <PodiumColumn
            key={rank}
            row={row}
            metric={metric}
            clipHref={getClipHref(row)}
          />
        );
      })}
    </div>
  );
};

export default Podium;
