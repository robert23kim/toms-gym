import React from "react";

interface SparklineProps {
  /** Score series in chronological order. */
  values: number[];
  width?: number;
  height?: number;
  className?: string;
}

const STROKE = "#4ade80";

/**
 * Minimal SVG sparkline for the viewer's attempt history: a green polyline with
 * a dot on the most recent point. A single attempt renders just the dot.
 */
const Sparkline: React.FC<SparklineProps> = ({
  values,
  width = 132,
  height = 34,
  className,
}) => {
  if (!values || values.length === 0) return null;

  const pad = 3;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  const points = values.map((v, i) => {
    const x = values.length === 1 ? width / 2 : pad + (i / (values.length - 1)) * w;
    // Higher score → higher on the chart (smaller y).
    const y = pad + (1 - (v - min) / span) * h;
    return { x, y };
  });

  const last = points[points.length - 1];

  return (
    <svg
      data-testid="sparkline"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      fill="none"
      className={className}
      aria-hidden="true"
    >
      {points.length > 1 && (
        <polyline
          data-testid="sparkline-line"
          points={points.map((p) => `${p.x},${p.y}`).join(" ")}
          stroke={STROKE}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
      <circle
        data-testid="sparkline-dot"
        cx={last.x}
        cy={last.y}
        r={2.6}
        fill={STROKE}
      />
    </svg>
  );
};

export default Sparkline;
