import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Champion, formatChampionScore, getGolfAvatar } from "../../lib/api";
import { createAndCopyShareLink } from "../../lib/share";
import { dynastyLabel, localDate, marginCopy, reignDays } from "../../lib/championStats";

interface ChampionHeroProps {
  champion: Champion;
  wins: number;
  isViewer: boolean;
}

const ChampionHero: React.FC<ChampionHeroProps> = ({ champion, wins, isViewer }) => {
  const [shareState, setShareState] = useState<"idle" | "copied" | "failed">("idle");
  const dynasty = dynastyLabel(wins);
  const margin = marginCopy(champion);
  const days = reignDays(champion.ended_on);
  const watchPath = champion.attempt_id
    ? `/challenges/${champion.competition_id}/participants/${champion.user_id}/video/${champion.attempt_id}`
    : null;

  const share = async () => {
    try {
      await createAndCopyShareLink({
        targetUrl: `${window.location.origin}/champions`,
        ogTitle: `👑 ${champion.name} — ${champion.competition_name} champion`,
        ogDescription: margin || `${champion.field_size ?? ""} athletes competed`.trim(),
        ogStat: formatChampionScore(champion.metric, champion.score),
      });
      setShareState("copied");
    } catch {
      setShareState("failed");
    }
  };

  return (
    <section
      aria-label="Reigning champion"
      className="relative overflow-hidden rounded-3xl border border-amber-500/40 bg-gradient-to-b from-amber-500/10 via-card to-card px-6 py-10 text-center shadow-lg"
    >
      <div className="text-xs uppercase tracking-[0.3em] text-amber-600 dark:text-amber-400">
        {isViewer ? "Your reign" : "Reigning champion"}
      </div>

      <div className="relative mx-auto mt-6 h-36 w-36">
        <div className="laurel-ring absolute inset-0 rounded-full" aria-hidden="true" />
        <div className="absolute inset-[5px] rounded-full bg-card" aria-hidden="true" />
        <img
          src={getGolfAvatar(champion.name, champion.user_id)}
          alt=""
          className="absolute inset-[9px] rounded-full bg-secondary object-cover"
        />
        <span
          className="crown-float absolute -top-5 left-1/2 -translate-x-1/2 text-4xl drop-shadow"
          aria-hidden="true"
        >
          👑
        </span>
      </div>

      <h2 className="hall-shimmer mt-5 text-4xl font-black tracking-tight">{champion.name}</h2>
      {dynasty && (
        <div className="mt-1 text-sm font-semibold text-amber-600 dark:text-amber-400">
          🔥 {dynasty}
        </div>
      )}
      <p className="mt-3 text-lg">
        {champion.competition_name} ·{" "}
        <span className="font-mono font-semibold">
          {formatChampionScore(champion.metric, champion.score)}
        </span>
      </p>
      {margin && <p className="mt-1 text-sm text-muted-foreground">{margin}</p>}

      <dl className="mx-auto mt-6 grid max-w-md grid-cols-3 gap-3 text-center">
        <div className="rounded-xl bg-secondary/60 px-2 py-3">
          <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">Field</dt>
          <dd className="text-xl font-semibold">{champion.field_size ?? "—"}</dd>
        </div>
        <div className="rounded-xl bg-secondary/60 px-2 py-3">
          <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">Attempts</dt>
          <dd className="text-xl font-semibold">{champion.winner_attempts ?? "—"}</dd>
        </div>
        <div className="rounded-xl bg-secondary/60 px-2 py-3">
          <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">Reign</dt>
          <dd className="text-xl font-semibold">
            {days}
            <span className="text-sm font-normal text-muted-foreground"> d</span>
          </dd>
        </div>
      </dl>

      <p className="mt-4 text-xs text-muted-foreground">
        Crowned{" "}
        {localDate(champion.ended_on).toLocaleDateString(undefined, {
          year: "numeric",
          month: "long",
          day: "numeric",
        })}
      </p>

      <div className="mt-6 flex flex-wrap items-center justify-center gap-3 text-sm">
        {watchPath && (
          <Link
            to={watchPath}
            className="rounded-full bg-amber-500 px-5 py-2 font-semibold text-black transition-colors hover:bg-amber-400"
          >
            ▶ Watch the win
          </Link>
        )}
        <Link
          to={`/profile/${champion.user_id}`}
          className="rounded-full border border-border px-5 py-2 transition-colors hover:bg-secondary"
        >
          View profile
        </Link>
        <button
          type="button"
          onClick={share}
          className="rounded-full border border-border px-5 py-2 transition-colors hover:bg-secondary"
        >
          {shareState === "copied" ? "Link copied ✓" : shareState === "failed" ? "Copy failed" : "Share"}
        </button>
      </div>
    </section>
  );
};

export default ChampionHero;
