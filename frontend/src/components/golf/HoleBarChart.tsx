import React from "react";

interface HoleBarChartProps {
  holes: { hole_number: number; par: number; strokes: number | null }[];
}

/**
 * 18-column bar chart: each bar shows strokes relative to par. Positive
 * bars (above the par baseline) represent over-par; negative bars (below)
 * represent under-par. Colors follow the Fairway semantics.
 */
const HoleBarChart: React.FC<HoleBarChartProps> = ({ holes }) => {
  const width = 360;
  const height = 100;
  const padding = 12;
  const barW = (width - padding * 2) / 18;
  const maxDelta = 4;

  const sorted = [...holes].sort((a, b) => a.hole_number - b.hole_number);

  return (
    <div className="fw-surface p-4">
      <h3 className="fw-h3 mb-2">Hole by hole vs par</h3>
      <svg
        data-testid="hole-bar-chart"
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-auto"
        role="img"
        aria-label="Hole-by-hole strokes vs par"
      >
        <line
          x1={padding} x2={width - padding}
          y1={height / 2} y2={height / 2}
          stroke="var(--fw-border-secondary)" strokeWidth="0.5" strokeDasharray="2 3"
        />
        {sorted.map((h, i) => {
          const delta = h.strokes === null ? 0 : h.strokes - h.par;
          const clamped = Math.max(-maxDelta, Math.min(maxDelta, delta));
          const h2 = (height / 2) - padding;
          const barH = (Math.abs(clamped) / maxDelta) * h2;
          const y = clamped >= 0 ? height / 2 : (height / 2) - barH;
          const color =
            delta < 0 ? "var(--fw-success)" :
            delta === 0 ? "var(--fw-border-secondary)" :
            delta === 1 ? "var(--fw-warning)" :
            "var(--fw-danger)";
          return (
            <rect
              key={h.hole_number}
              x={padding + i * barW + 1}
              y={y}
              width={barW - 2}
              height={barH || 1}
              fill={color}
              rx="1"
            />
          );
        })}
      </svg>
    </div>
  );
};

export default HoleBarChart;
