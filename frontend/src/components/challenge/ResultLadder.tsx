import React from "react";
import { Link } from "react-router-dom";
import type { ChallengeMetric } from "../../lib/types";
import { PersonalBest, Standing, formatWithUnit } from "../../lib/standing";

interface Props {
  standing: Standing;
  personalBest: PersonalBest;
  metric: ChallengeMetric;
  athleteName: string | null | undefined;
  isOwner: boolean;
  challengeId: string;
  challengeOpen: boolean;
  extraPill?: string | null;
  className?: string;
}

const first = (name: string | null | undefined): string => (name || "Anonymous").split(/\s+/)[0];

const Rung: React.FC<{ label: string; score: string; highlight?: boolean }> = ({ label, score, highlight }) => (
  <div
    className={`flex items-baseline justify-between gap-3 rounded-lg px-3 py-2 ${
      highlight ? "border border-accent/40 bg-accent/10 font-semibold text-foreground" : "text-muted-foreground"
    }`}
  >
    <span className="truncate">{label}</span>
    <span className="shrink-0 tabular-nums">{score}</span>
  </div>
);

const Gap: React.FC<{ text: string }> = ({ text }) => (
  <div className="flex items-center gap-2 px-4 text-xs text-muted-foreground">
    <span className="h-3 w-px bg-border" aria-hidden="true" />
    <span>{text}</span>
  </div>
);

const ResultLadder: React.FC<Props> = ({
  standing,
  personalBest,
  metric,
  athleteName,
  isOwner,
  challengeId,
  challengeOpen,
  extraPill = null,
  className = "",
}) => {
  const you = isOwner ? "You" : first(athleteName);
  const eyebrow = isOwner ? "Where you stand" : `Where ${you} stands`;
  const solo = standing.participantCount === 1;

  const subtitle = solo
    ? "First on the board"
    : standing.isLeader
      ? `${you} lead${isOwner ? "" : "s"} the field`
      : !standing.isLeader && standing.gap != null
        ? `${formatWithUnit(standing.gap, metric)} to pass ${first(standing.nextName)}`
        : null;

  return (
    <section aria-label={eyebrow} className={`bg-card rounded-lg shadow-lg p-6 ${className}`}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <p className="whitespace-nowrap text-xs uppercase tracking-widest text-muted-foreground">{eyebrow}</p>
        {personalBest.isPersonalBest && personalBest.previousBest != null ? (
          <span className="shrink-0 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400">
            ▲ New best · up from {formatWithUnit(personalBest.previousBest, metric)}
          </span>
        ) : personalBest.belowBest ? (
          <span className="shrink-0 rounded-full bg-secondary/60 px-2.5 py-0.5 text-xs text-muted-foreground">
            Best: {formatWithUnit(standing.best, metric)}
          </span>
        ) : null}
        {extraPill && (
          <span className="shrink-0 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400">
            ▲ {extraPill}
          </span>
        )}
      </div>

      <div className="mb-1 flex items-baseline gap-2">
        <span className="text-5xl font-bold leading-none tabular-nums">#{standing.rank}</span>
        <span className="text-muted-foreground">of {standing.participantCount}</span>
      </div>
      {subtitle && <p className="mb-4 text-sm text-muted-foreground">{subtitle}</p>}

      {!solo && (
        <div className="flex flex-col gap-1">
          {!standing.isLeader && standing.gap != null && (
            <>
              <Rung
                label={first(standing.nextName)}
                score={formatWithUnit(standing.best + standing.gap, metric)}
              />
              <Gap text={`${formatWithUnit(standing.gap, metric)} to pass`} />
            </>
          )}
          <Rung label={you} score={formatWithUnit(standing.best, metric)} highlight />
          {standing.below && (
            <>
              <Gap text={`${formatWithUnit(standing.below.gap, metric)} clear`} />
              <Rung label={first(standing.below.name)} score={formatWithUnit(standing.below.score, metric)} />
            </>
          )}
        </div>
      )}

      {standing.podiumGap != null && standing.podiumGap > 0 && (
        <p className="mt-3 text-sm text-muted-foreground">
          {formatWithUnit(standing.podiumGap, metric)} from the podium
        </p>
      )}

      {!isOwner && challengeOpen && (
        <Link
          to={`/challenges/${challengeId}/upload`}
          className="mt-4 inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2.5 font-medium text-primary-foreground hover:bg-primary/90"
        >
          Beat this →
        </Link>
      )}
    </section>
  );
};

export default ResultLadder;
