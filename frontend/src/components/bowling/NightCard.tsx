import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import type { Night } from "../../lib/bowlingNight";

const shortDate = (iso: string): string =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });

const highLine = (n: Night): string => {
  switch (n.bestSince.kind) {
    case "first":
      return `${n.high} high — first night on the books`;
    case "best-yet":
      return `${n.high} high — your best game yet`;
    case "since":
      return `${n.high} high — your best game since ${shortDate(n.bestSince.date)}`;
    default:
      return `${n.high} high`;
  }
};

const NightCard: React.FC<{ night: Night }> = ({ night }) => {
  const reduceMotion = useReducedMotion();
  const up = night.delta != null && night.delta > 0;
  const down = night.delta != null && night.delta < 0;
  return (
    <motion.section
      aria-label="Tonight"
      initial={reduceMotion ? false : { scale: 1.06, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 260, damping: 20 }}
      className="glass rounded-2xl p-5"
    >
      <p className="text-xs uppercase tracking-widest text-muted-foreground">
        Tonight · {shortDate(night.playedOn)}
      </p>
      <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-5xl font-bold tabular-nums leading-none">{night.avg}</span>
        <span className="text-muted-foreground">
          avg over {night.count} game{night.count === 1 ? "" : "s"}
        </span>
        {night.delta != null && night.delta !== 0 && (
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
              up ? "bg-green-500/10 text-green-500" : "bg-secondary/60 text-muted-foreground"
            }`}
          >
            {up ? "▲" : down ? "▼" : ""} {up ? "+" : ""}
            {night.delta} vs your average
          </span>
        )}
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{highLine(night)}</p>
    </motion.section>
  );
};

export default NightCard;
