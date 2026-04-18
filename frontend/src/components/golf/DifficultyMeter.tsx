import React from "react";

interface DifficultyMeterProps {
  slope: number | null;
}

const MIN_SLOPE = 55;
const MAX_SLOPE = 155;

const ANCHORS = [
  { slope: 100, label: "Forgiving" },
  { slope: 113, label: "Average" },
  { slope: 130, label: "Above average" },
  { slope: 145, label: "Brutal" },
] as const;

const slopeToPercent = (slope: number): number => {
  const raw = ((slope - MIN_SLOPE) / (MAX_SLOPE - MIN_SLOPE)) * 100;
  return Math.max(0, Math.min(100, raw));
};

const DifficultyMeter: React.FC<DifficultyMeterProps> = ({ slope }) => {
  if (slope === null) return null;

  const needleLeft = slopeToPercent(slope);

  return (
    <div data-testid="difficulty-meter" className="w-full">
      <div className="relative h-2 rounded-full bg-[var(--fw-bg-tertiary)] border-[0.5px] border-[var(--fw-border-tertiary)]">
        <div
          className="absolute top-0 bottom-0 border-l-[0.5px] border-[var(--fw-border-secondary)]"
          style={{ left: `${slopeToPercent(113)}%` }}
          aria-hidden="true"
        />
        <div
          data-testid="difficulty-meter-needle"
          className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-[var(--fw-info)] border-[0.5px] border-[var(--fw-border-info)]"
          style={{ left: `${needleLeft}%` }}
        />
      </div>
      <div className="relative mt-2 text-[11px] fw-text-secondary h-8">
        {ANCHORS.map((a) => (
          <span
            key={a.slope}
            className="absolute -translate-x-1/2 text-center leading-tight"
            style={{ left: `${slopeToPercent(a.slope)}%` }}
          >
            <span className="block font-medium text-[var(--fw-text-primary)]">
              {a.slope}
            </span>
            <span className="block">{a.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
};

export default DifficultyMeter;
