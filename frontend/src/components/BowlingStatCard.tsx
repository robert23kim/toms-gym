import React from "react";

type StatTone = "default" | "good" | "warn" | "muted";

interface BowlingStatCardProps {
  /** Big headline value — a number, "—", or short label. */
  value: React.ReactNode;
  /** What the stat is (e.g. "Entry Board"). */
  label: string;
  /** Optional smaller line under the value (e.g. "est. · mph"). */
  sublabel?: string;
  tone?: StatTone;
}

const toneClasses: Record<StatTone, { box: string; value: string }> = {
  default: { box: "bg-primary/5", value: "text-primary" },
  good: { box: "bg-green-500/10", value: "text-green-600 dark:text-green-400" },
  warn: { box: "bg-amber-500/10", value: "text-amber-600 dark:text-amber-400" },
  muted: { box: "bg-muted", value: "text-muted-foreground" },
};

/** Compact headline stat card used on the bowling result page. */
const BowlingStatCard: React.FC<BowlingStatCardProps> = ({
  value,
  label,
  sublabel,
  tone = "default",
}) => {
  const t = toneClasses[tone];
  return (
    <div className={`${t.box} rounded-lg p-4 text-center`}>
      <div className={`text-2xl font-bold ${t.value}`}>{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{label}</div>
      {sublabel && (
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground/70 mt-0.5">
          {sublabel}
        </div>
      )}
    </div>
  );
};

export default BowlingStatCard;
