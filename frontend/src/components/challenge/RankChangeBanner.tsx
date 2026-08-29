import React from "react";
import type { ChallengeMetric } from "../../lib/types";
import type { RankShift } from "../../lib/rankMemory";
import { Standing, formatWithUnit } from "../../lib/standing";

interface Props {
  shift: RankShift;
  standing: Standing;
  metric: ChallengeMetric;
}

const first = (name: string | null): string => (name || "the athlete above").split(/\s+/)[0];

const RankChangeBanner: React.FC<Props> = ({ shift, standing, metric }) => {
  const up = shift.kind === "up";
  const takeBack =
    !up && standing.gap != null && standing.gap > 0
      ? ` · ${formatWithUnit(standing.gap, metric)} to pass ${first(standing.nextName)} and take it back`
      : "";
  return (
    <div
      role="status"
      aria-label="Rank change"
      className={`mb-4 rounded-xl px-4 py-3 text-sm font-medium ${
        up ? "border border-green-500/30 bg-green-500/10 text-green-500" : "bg-secondary/60 text-muted-foreground"
      }`}
    >
      {up ? "▲ You moved up" : "▼ You slipped"} — #{shift.from} → #{shift.to} since your last visit{takeBack}
    </div>
  );
};

export default RankChangeBanner;
