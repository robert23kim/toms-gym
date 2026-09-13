import React from "react";
import { setPace, type TimedRepInput } from "../../lib/setPace";

interface Props {
  repMetrics: TimedRepInput[] | null | undefined;
}

const THIRD_LABELS = ["Start", "Middle", "End"];

function formColor(form: number | null): string {
  if (form == null) return "bg-muted";
  if (form >= 70) return "bg-green-500";
  if (form >= 50) return "bg-yellow-500";
  return "bg-red-500";
}

function formatSeconds(s: number): string {
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rest = Math.round(s - m * 60);
  return `${m}:${String(rest).padStart(2, "0")}`;
}

const SetStats: React.FC<Props> = ({ repMetrics }) => {
  const pace = setPace(repMetrics);
  if (!pace) return null;

  return (
    <div data-testid="set-stats" className="bg-card rounded-lg shadow-lg p-6 space-y-3">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        Set Stats
      </h3>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="border border-border rounded-lg p-2 min-w-0">
          <div className="text-lg font-bold" data-testid="set-stats-pace">{pace.repsPerMinute}</div>
          <div className="text-[11px] text-muted-foreground">reps/min</div>
        </div>
        <div className="border border-border rounded-lg p-2 min-w-0">
          <div className="text-lg font-bold" data-testid="set-stats-streak">{pace.bestCleanStreak}</div>
          <div className="text-[11px] text-muted-foreground">clean in a row</div>
        </div>
        <div className="border border-border rounded-lg p-2 min-w-0">
          <div className="text-lg font-bold" data-testid="set-stats-pause">{formatSeconds(pace.longestPauseS)}</div>
          <div className="text-[11px] text-muted-foreground">longest pause</div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2" data-testid="set-stats-thirds">
        {pace.thirds.map((t, i) => (
          <div key={THIRD_LABELS[i]} className="min-w-0 text-xs">
            <div className="flex justify-between gap-1 mb-1">
              <span className="text-muted-foreground truncate">{THIRD_LABELS[i]}</span>
              <span className="font-medium">{t.reps}</span>
            </div>
            <div className="w-full bg-muted rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full ${formColor(t.avgForm)}`}
                style={{ width: `${Math.max(0, Math.min(100, t.avgForm ?? 0))}%` }}
              />
            </div>
            <div className="text-[11px] text-muted-foreground mt-1">
              {t.avgForm != null ? `form ${t.avgForm}` : "no reps"}
            </div>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-muted-foreground">
        {pace.reps} reps in {formatSeconds(pace.durationS)} · reps {pace.fastestRepS}–{pace.slowestRepS}s each
      </p>
    </div>
  );
};

export default SetStats;
