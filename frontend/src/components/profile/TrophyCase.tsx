import React from "react";
import { Link } from "react-router-dom";
import { Champion, formatChampionScore } from "../../lib/api";

/** "👑 Summer plank challenge Champion 2026" — profile flair line. */
export const championTitle = (c: Champion): string =>
  `👑 ${c.competition_name} Champion ${new Date(c.ended_on).getFullYear()}`;

interface TrophyCaseProps {
  champions: Champion[];
}

/** One 🏆 card per challenge won. Renders nothing when there are no wins. */
const TrophyCase: React.FC<TrophyCaseProps> = ({ champions }) => {
  if (!champions.length) return null;

  return (
    <div className="bg-card rounded-xl p-6 mb-6 shadow-sm">
      <div className="flex items-center gap-3.5 text-xs uppercase tracking-widest text-muted-foreground mb-4">
        <span className="flex-1 h-px bg-border" aria-hidden="true" />
        Trophy case
        <span className="flex-1 h-px bg-border" aria-hidden="true" />
      </div>
      <div className="flex flex-col gap-2.5">
        {champions.map((c) => (
          <Link
            key={c.competition_id}
            to={`/challenges/${c.competition_id}`}
            className="flex items-center gap-3 rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3 hover:bg-amber-500/10 transition-colors"
          >
            <span className="text-2xl" aria-hidden="true">
              🏆
            </span>
            <div className="flex-1 min-w-0 text-left">
              <div className="font-medium truncate">{c.competition_name}</div>
              <div className="text-sm text-muted-foreground">
                {formatChampionScore(c.metric, c.score)} · won{" "}
                {new Date(c.ended_on).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </div>
            </div>
            <span className="text-sm text-muted-foreground shrink-0">
              Open →
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default TrophyCase;
