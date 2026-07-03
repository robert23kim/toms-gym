import React from "react";
import type { ChallengeMetric } from "../../lib/types";
import type { Standing } from "../../lib/standing";
import { formatScoreValue, scoreUnit } from "./metric";
import Sparkline from "./Sparkline";

interface StandingCardProps {
  standing: Standing;
  metric: ChallengeMetric;
}

const CARD_STYLE: React.CSSProperties = {
  background:
    "linear-gradient(160deg, rgba(47,123,246,.18), rgba(47,123,246,.05))",
  border: "1px solid rgba(47,123,246,.32)",
};

/** Formats a score with its metric unit as a small muted suffix. */
const Score: React.FC<{ value: number; metric: ChallengeMetric; className?: string }> = ({
  value,
  metric,
  className,
}) => (
  <span className={className}>
    {formatScoreValue(value, metric)}
    <span className="ml-0.5 text-[55%] font-semibold text-white/50">{scoreUnit(metric)}</span>
  </span>
);

/**
 * "Your standing" personal-progress card (#3a/#3b). Rendered only when the
 * viewer has a qualifying entry. Three parts: standing (rank + best), trend
 * (sparkline + delta + raw series), and gap-to-next (accented copy + bar).
 * #1 → defend-your-lead message, no bar. Single attempt → point, no delta.
 */
const StandingCard: React.FC<StandingCardProps> = ({ standing, metric }) => {
  const {
    rank,
    participantCount,
    best,
    history,
    tries,
    delta,
    isLeader,
    gap,
    progress,
    nextName,
    nextRank,
  } = standing;

  const unit = scoreUnit(metric);
  const series = history.map((h) => `${formatScoreValue(h.score, metric)}${unit}`).join(" → ");
  const deltaSign = delta !== null && delta >= 0 ? "+" : "−";
  const deltaAbs = delta !== null ? formatScoreValue(Math.abs(delta), metric) : "";

  return (
    <div
      data-testid="standing-card"
      className="mb-6 rounded-2xl p-4 lg:max-w-2xl lg:p-5"
      style={CARD_STYLE}
    >
      {/* Standing */}
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-wider text-[#9fc2ff]">
            Your standing
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span
              data-testid="standing-rank"
              className="text-[30px] font-bold leading-none tracking-tight tabular-nums"
            >
              #{rank}
            </span>
            <span className="text-xs font-medium text-white/45">of {participantCount}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10.5px] font-semibold uppercase tracking-wider text-white/45">
            Your best
          </div>
          <Score
            value={best}
            metric={metric}
            className="mt-1 block text-[22px] font-bold leading-none tracking-tight tabular-nums"
          />
        </div>
      </div>

      {/* Trend */}
      <div
        data-testid="standing-trend"
        className="mt-3.5 flex items-center gap-3 rounded-[10px] p-3"
        style={{ background: "rgba(0,0,0,.22)" }}
      >
        <Sparkline values={history.map((h) => h.score)} />
        <div className="min-w-0">
          {delta !== null && (
            <div
              data-testid="standing-delta"
              className="text-[13px] font-semibold text-[#4ade80]"
            >
              ↑ {deltaSign}{deltaAbs}{unit} in {tries} tries
            </div>
          )}
          <div className="truncate text-[11.5px] text-white/45">{series}</div>
        </div>
      </div>

      {/* Gap-to-next */}
      {isLeader ? (
        <div data-testid="standing-lead" className="mt-3.5 text-[13px] font-medium text-white/70">
          You're <span className="font-semibold text-[#7fb0ff]">#1</span> — defend your lead.
        </div>
      ) : (
        <div className="mt-3.5">
          <div data-testid="standing-gap" className="text-[13px] font-medium text-white/70">
            Beat <span className="font-semibold text-[#7fb0ff]">{formatScoreValue(gap ?? 0, metric)}{unit}</span>{" "}
            to pass {nextName || "the next athlete"} for{" "}
            <span className="font-semibold text-[#7fb0ff]">#{nextRank}</span>
          </div>
          <div
            className="mt-2 h-2 overflow-hidden rounded-full"
            style={{ background: "rgba(255,255,255,.12)" }}
          >
            <div
              data-testid="standing-progress"
              className="h-full rounded-full"
              style={{
                width: `${Math.round((progress ?? 0) * 100)}%`,
                background: "linear-gradient(90deg,#2f7bf6,#7fb0ff)",
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default StandingCard;
