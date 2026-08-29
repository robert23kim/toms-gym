import React from "react";
import { Link } from "react-router-dom";
import { Champion, formatChampionScore, getGolfAvatar } from "../../lib/api";
import { localDate, marginCopy } from "../../lib/championStats";

interface ChampionCardProps {
  champion: Champion;
  /** 1 = first-ever win, 2 = second, … */
  winNumber: number;
  isViewer: boolean;
}

const ordinal = (n: number): string => {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
};

const ChampionCard: React.FC<ChampionCardProps> = ({ champion, winNumber, isViewer }) => {
  const margin = marginCopy(champion);
  return (
    <article
      className={`relative flex items-center gap-4 rounded-2xl border px-4 py-4 transition-colors ${
        isViewer
          ? "border-amber-500/60 bg-amber-500/10"
          : "border-border bg-card hover:border-amber-500/40"
      }`}
    >
      <div className="relative shrink-0">
        <img
          src={getGolfAvatar(champion.name, champion.user_id)}
          alt=""
          className="h-14 w-14 rounded-full bg-secondary object-cover ring-2 ring-amber-500/60"
        />
        <span className="absolute -right-1 -top-2 text-lg" aria-hidden="true">
          🏆
        </span>
      </div>
      <div className="min-w-0 flex-1 text-left">
        <div className="flex flex-wrap items-center gap-x-2">
          <Link to={`/profile/${champion.user_id}`} className="font-semibold hover:underline">
            {champion.name}
          </Link>
          {winNumber > 1 && (
            <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[11px] font-medium text-amber-700 dark:text-amber-300">
              {ordinal(winNumber)} title
            </span>
          )}
          {isViewer && (
            <span className="rounded-full bg-amber-500 px-2 py-0.5 text-[11px] font-semibold text-black">
              You
            </span>
          )}
        </div>
        <div className="truncate text-sm text-muted-foreground">
          <Link to={`/challenges/${champion.competition_id}`} className="hover:underline">
            {champion.competition_name}
          </Link>{" "}
          · {localDate(champion.ended_on).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
        </div>
        {margin && <div className="text-xs text-muted-foreground">{margin}</div>}
      </div>
      <div className="shrink-0 text-right">
        <div className="font-mono text-lg font-semibold">
          {formatChampionScore(champion.metric, champion.score)}
        </div>
        {champion.attempt_id && (
          <Link
            to={`/challenges/${champion.competition_id}/participants/${champion.user_id}/video/${champion.attempt_id}`}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Watch →
          </Link>
        )}
      </div>
    </article>
  );
};

export default ChampionCard;
