import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchChampions,
  formatChampionScore,
  getGolfAvatar,
  Champion,
} from "../lib/api";

/**
 * Celebrates the most recent challenge winner on the home page.
 * Hidden entirely when nothing has been won yet or the fetch fails.
 */
const ChampionSpotlight: React.FC = () => {
  const [champion, setChampion] = useState<Champion | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchChampions()
      .then((champs) => {
        if (cancelled) return;
        setChampion(champs[0] || null);
      })
      .catch(() => {}); // non-fatal: card simply stays hidden
    return () => {
      cancelled = true;
    };
  }, []);

  if (!champion) return null;

  return (
    <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 px-6 py-5 flex flex-col items-center gap-3">
      <img
        src={getGolfAvatar(champion.name, champion.user_id)}
        alt=""
        aria-hidden="true"
        className="h-16 w-16 rounded-full bg-secondary object-cover"
      />
      <div>
        <div className="text-lg font-semibold">
          <span aria-hidden="true">👑 </span>
          {champion.name}
        </div>
        <p className="text-sm text-muted-foreground">
          {champion.competition_name} champion —{" "}
          {formatChampionScore(champion.metric, champion.score)}
        </p>
      </div>
      <div className="flex items-center gap-4 text-sm">
        <Link
          to={`/profile/${champion.user_id}`}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          View profile →
        </Link>
        {champion.attempt_id && (
          <Link
            to={`/challenges/${champion.competition_id}/participants/${champion.user_id}/video/${champion.attempt_id}`}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Watch the win →
          </Link>
        )}
      </div>
    </div>
  );
};

export default ChampionSpotlight;
