import React, { useMemo, useRef, useState } from "react";
import { LiftingReport } from "../../lib/types";
import {
  holdRuns,
  steadinessScore,
  wobbleEvents,
  decayPoint,
  milestones,
  personality,
} from "../../lib/plankStats";

interface Props {
  report: LiftingReport;
  onSeek: (t: number) => void;
  currentTime?: number;
}

// Chart geometry (SVG user units; the element scales responsively).
const W = 560;
const H = 160;
const PAD_X = 8;
const PAD_TOP = 10;
const PAD_BOTTOM = 22; // milestone labels live here
const PLOT_W = W - PAD_X * 2;
const PLOT_H = H - PAD_TOP - PAD_BOTTOM;

const STATE_FILL: Record<string, string> = {
  in_plank: "hsl(220 90% 56% / 0.10)",
  settling: "hsl(40 90% 55% / 0.10)",
  no_pose: "hsl(240 5% 50% / 0.06)",
};

const STATE_LABEL: Record<string, string> = {
  in_plank: "Holding",
  settling: "Settling",
  no_pose: "Lost you",
};

const TIER_CLASS: Record<string, string> = {
  "Rock Solid": "bg-green-500/15 text-green-500",
  Steady: "bg-accent/15 text-accent",
  Wobbly: "bg-orange-500/15 text-orange-500",
  "Jelly Mode": "bg-red-500/15 text-red-500",
};

const fmt = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

/**
 * Scrubbable steadiness story for a plank result: per-second form score as an
 * area line over state bands, wobble markers, milestone ticks, decay
 * annotation, and a hold-segments strip. Clicking/dragging the chart seeks
 * the video (never autoplays). Renders nothing without per_second data —
 * the parent's plain stat list is the fallback.
 */
const PlankSteadiness: React.FC<Props> = ({ report, onSeek, currentTime }) => {
  const ps = report.per_second ?? [];
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverT, setHoverT] = useState<number | null>(null);

  const stats = useMemo(() => {
    if (ps.length === 0) return null;
    const duration = ps[ps.length - 1].t + 1;
    return {
      duration,
      runs: holdRuns(ps),
      score: steadinessScore(report.body_line_stdev_deg),
      wobbles: wobbleEvents(ps),
      decay: decayPoint(ps),
      marks: milestones(ps),
      archetype: personality(ps, report.body_line_stdev_deg),
    };
  }, [ps, report.body_line_stdev_deg]);

  if (!stats) return null;
  const { duration, runs, score, wobbles, decay, marks, archetype } = stats;

  const x = (t: number) => PAD_X + (t / duration) * PLOT_W;
  const y = (form: number) => PAD_TOP + (1 - Math.min(Math.max(form, 0), 1)) * PLOT_H;

  // State bands: consecutive same-state groups.
  const bands: { state: string; t0: number; t1: number }[] = [];
  for (const s of ps) {
    const last = bands[bands.length - 1];
    if (last && last.state === s.state && s.t === last.t1) last.t1 = s.t + 1;
    else bands.push({ state: s.state, t0: s.t, t1: s.t + 1 });
  }

  // Form line + area paths.
  const linePts = ps.map((s) => `${x(s.t).toFixed(1)},${y(s.form_score).toFixed(1)}`);
  const linePath = `M ${linePts.join(" L ")}`;
  const areaPath = `${linePath} L ${x(ps[ps.length - 1].t).toFixed(1)},${(PAD_TOP + PLOT_H).toFixed(1)} L ${x(ps[0].t).toFixed(1)},${(PAD_TOP + PLOT_H).toFixed(1)} Z`;

  const firstHold = ps.find((s) => s.state === "in_plank")?.t ?? 0;
  const heldFor = decay != null ? Math.max(0, decay - firstHold) : null;

  const pointerT = (clientX: number): number => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0) return 0;
    const frac = Math.min(Math.max((clientX - rect.left) / rect.width, 0), 1);
    const t = (frac * W - PAD_X) / PLOT_W * duration;
    return Math.min(Math.max(t, 0), duration);
  };

  const hoverSec = hoverT != null ? ps[Math.min(Math.floor(hoverT), ps.length - 1)] : null;

  return (
    <div className="space-y-3">
      {/* Hero row: steadiness score + personality */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        {score && (
          <div className={`flex items-baseline gap-2 px-4 py-2 rounded-xl ${TIER_CLASS[score.label] ?? "bg-secondary"}`}>
            <span className="text-2xl font-bold">{score.score}</span>
            <span className="text-sm font-medium">{score.label}</span>
          </div>
        )}
        {archetype && (
          <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl glass text-left">
            <span className="text-2xl" aria-hidden="true">{archetype.emoji}</span>
            <div>
              <div className="text-sm font-semibold">{archetype.name}</div>
              <div className="text-xs text-muted-foreground">{archetype.blurb}</div>
            </div>
          </div>
        )}
      </div>

      {/* Steadiness timeline */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs uppercase tracking-wider text-muted-foreground">
            Steadiness over time — tap to jump the video
          </span>
          {hoverSec && (
            <span className="text-xs text-muted-foreground tabular-nums">
              {fmt(hoverSec.t)} · {(hoverSec.form_score * 100).toFixed(0)}% · {STATE_LABEL[hoverSec.state] ?? hoverSec.state}
            </span>
          )}
        </div>
        <svg
          ref={svgRef}
          data-testid="steadiness-chart"
          viewBox={`0 0 ${W} ${H}`}
          className="w-full h-auto cursor-crosshair select-none rounded-lg border border-border bg-secondary/20"
          role="img"
          aria-label="Plank form score per second; click to seek the video"
          onPointerDown={(e) => onSeek(pointerT(e.clientX))}
          onPointerMove={(e) => {
            const t = pointerT(e.clientX);
            setHoverT(t);
            if (e.buttons === 1) onSeek(t);
          }}
          onPointerLeave={() => setHoverT(null)}
        >
          {/* state bands */}
          {bands.map((b, i) => (
            <rect
              key={i}
              x={x(b.t0)}
              y={PAD_TOP}
              width={x(b.t1) - x(b.t0)}
              height={PLOT_H}
              fill={STATE_FILL[b.state] ?? "transparent"}
            />
          ))}
          {/* recessive grid: 50% and 100% form */}
          {[0.5, 1].map((g) => (
            <line
              key={g}
              x1={PAD_X}
              x2={W - PAD_X}
              y1={y(g)}
              y2={y(g)}
              stroke="hsl(240 4% 26%)"
              strokeWidth="0.5"
              strokeDasharray="3 4"
            />
          ))}
          {/* form area + line */}
          <path d={areaPath} fill="hsl(220 90% 56% / 0.15)" />
          <path d={linePath} fill="none" stroke="hsl(220 90% 56%)" strokeWidth="2" strokeLinejoin="round" />
          {/* decay annotation */}
          {decay != null && (
            <g>
              <line x1={x(decay)} x2={x(decay)} y1={PAD_TOP} y2={PAD_TOP + PLOT_H} stroke="hsl(30 90% 55%)" strokeWidth="1" strokeDasharray="4 3" />
              <text x={Math.min(x(decay) + 4, W - 90)} y={PAD_TOP + 12} fontSize="10" fill="hsl(30 90% 65%)">
                form held {heldFor}s
              </text>
            </g>
          )}
          {/* wobble markers */}
          {wobbles.map((w) => {
            const s = ps[Math.min(w.t, ps.length - 1)];
            return (
              <g key={w.t} transform={`translate(${x(w.t)}, ${y(s?.form_score ?? 0.5)})`}>
                <rect x="-4" y="-4" width="8" height="8" transform="rotate(45)" fill="hsl(30 90% 55%)" stroke="hsl(240 10% 4%)" strokeWidth="1.5">
                  <title>{`Wobble at ${fmt(w.t)} (${w.delta.toFixed(1)}°)`}</title>
                </rect>
              </g>
            );
          })}
          {/* milestone ticks */}
          {marks.filter((m) => m.reached && m.t != null).map((m) => (
            <g key={m.label}>
              <line x1={x(m.t!)} x2={x(m.t!)} y1={PAD_TOP + PLOT_H} y2={PAD_TOP + PLOT_H + 5} stroke="hsl(220 90% 56%)" strokeWidth="1.5" />
              <text x={x(m.t!)} y={H - 6} fontSize="10" textAnchor="middle" fill="hsl(220 90% 66%)">
                {m.label}
              </text>
            </g>
          ))}
          {/* hover crosshair */}
          {hoverT != null && (
            <line x1={x(hoverT)} x2={x(hoverT)} y1={PAD_TOP} y2={PAD_TOP + PLOT_H} stroke="hsl(0 0% 90% / 0.35)" strokeWidth="1" />
          )}
          {/* playhead */}
          {currentTime != null && currentTime > 0 && currentTime <= duration && (
            <line x1={x(currentTime)} x2={x(currentTime)} y1={PAD_TOP} y2={PAD_TOP + PLOT_H} stroke="hsl(0 0% 98%)" strokeWidth="1.5" />
          )}
        </svg>
        {/* state key — labels, never color alone */}
        <div className="flex gap-4 justify-center mt-1.5 text-[11px] text-muted-foreground">
          {Object.entries(STATE_LABEL).map(([state, label]) => (
            <span key={state} className="inline-flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm border border-border" style={{ background: STATE_FILL[state] }} />
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* Hold segments strip */}
      <div data-testid="hold-segments">
        <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1 text-left">
          Holds — {runs.length} {runs.length === 1 ? "run" : "runs"}
        </div>
        <div className="relative h-3 rounded-full bg-secondary/40 overflow-hidden">
          {runs.map((r) => (
            <div
              key={r.start}
              className={`absolute top-0 h-full rounded-full ${r.longest ? "bg-accent" : "bg-accent/40"}`}
              style={{
                left: `${(r.start / duration) * 100}%`,
                width: `${Math.max((r.duration / duration) * 100, 1)}%`,
              }}
              title={`${fmt(r.start)}–${fmt(r.end)} · ${r.duration}s${r.longest ? " (longest)" : ""}`}
            />
          ))}
        </div>
        {runs.some((r) => r.longest) && (
          <div className="text-xs text-muted-foreground mt-1 text-left">
            Longest hold: {runs.find((r) => r.longest)!.duration}s
          </div>
        )}
      </div>
    </div>
  );
};

export default PlankSteadiness;
