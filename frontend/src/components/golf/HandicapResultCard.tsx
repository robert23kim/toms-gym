import React from "react";
import { Link } from "react-router-dom";

interface Props {
  handicapIndex: number | null;
  prevIndex: number | null;
  totalScore: number;
  differential: number | null;
  profileTo: string;
  roundTo: string;
}

/**
 * Post-confirm payoff card: leads with the new handicap index and its delta
 * vs. the previous snapshot. Lower is better — a drop renders green (▼),
 * a rise renders in the danger color (▲), matching GolfLeaderboard's pill.
 */
const HandicapResultCard: React.FC<Props> = ({
  handicapIndex,
  prevIndex,
  totalScore,
  differential,
  profileTo,
  roundTo,
}) => {
  const delta =
    handicapIndex !== null && prevIndex !== null
      ? Math.round((handicapIndex - prevIndex) * 10) / 10
      : null;

  return (
    <div>
      <div className="fw-surface p-6 mb-4 text-center">
        <div className="text-xs fw-text-secondary uppercase tracking-wide mb-1">
          Handicap index
        </div>
        {handicapIndex !== null ? (
          <div className="flex items-baseline justify-center gap-3">
            <span className="text-6xl font-semibold text-[var(--fw-text-success)]">
              {handicapIndex.toFixed(1)}
            </span>
            {delta !== null && delta !== 0 && (
              <span
                className={`text-lg font-medium ${
                  delta < 0
                    ? "text-[var(--fw-text-success)]"
                    : "text-[var(--fw-danger)]"
                }`}
              >
                {delta < 0 ? "▼" : "▲"} {Math.abs(delta).toFixed(1)}
              </span>
            )}
          </div>
        ) : (
          <div className="text-sm fw-text-secondary">
            Provisional index pending — confirm another round to establish it.
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mb-6 text-left">
        <div className="fw-surface p-4">
          <div className="text-2xl font-medium">{totalScore}</div>
          <div className="text-xs fw-text-secondary">Total score</div>
        </div>
        <div className="fw-surface p-4">
          <div className="text-2xl font-medium">
            {differential !== null ? differential.toFixed(1) : "N/A"}
          </div>
          <div className="text-xs fw-text-secondary">Differential</div>
        </div>
      </div>

      <div className="flex gap-3 justify-center flex-wrap">
        <Link
          to="/golf/leaderboard"
          className="h-9 px-4 rounded-md bg-[var(--fw-info)] text-white text-sm inline-flex items-center"
        >
          Leaderboard
        </Link>
        <Link
          to={profileTo}
          className="h-9 px-4 rounded-md border-[0.5px] border-[var(--fw-border-secondary)] text-sm inline-flex items-center"
        >
          My rounds
        </Link>
        <Link
          to={roundTo}
          className="h-9 px-4 rounded-md border-[0.5px] border-[var(--fw-border-secondary)] text-sm inline-flex items-center"
        >
          Round details
        </Link>
      </div>
    </div>
  );
};

export default HandicapResultCard;
