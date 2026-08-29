import React from "react";
import type { RankShift } from "../../lib/rankMemory";

interface Props {
  shift: RankShift;
}

const RankChangeBanner: React.FC<Props> = ({ shift }) => {
  const up = shift.kind === "up";
  return (
    <div
      role="status"
      aria-label="Rank change"
      className={`mb-4 rounded-xl px-4 py-3 text-sm font-medium ${
        up ? "border border-green-500/30 bg-green-500/10 text-green-500" : "bg-secondary/60 text-muted-foreground"
      }`}
    >
      {up ? "▲ You moved up" : "▼ You slipped"} — #{shift.from} → #{shift.to} since your last visit
    </div>
  );
};

export default RankChangeBanner;
