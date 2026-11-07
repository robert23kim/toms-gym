import React from "react";
import type { ChallengeLeaderboardRow, ConsistencyBlock } from "../../lib/types";
import { formatScoreValue } from "./metric";

interface ConsistencyHeroProps {
  block: ConsistencyBlock;
  liftTypes: string[];
  /** The viewer's own row; null for anonymous visitors and non-entrants (no ring). */
  viewerRow: ChallengeLeaderboardRow | null;
}

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "Monday 2 Nov" from a bare YYYY-MM-DD, read as a local day. */
export const startDayLabel = (iso: string): string => {
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return `${WEEKDAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
};

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

export const weekLine = (block: ConsistencyBlock): string => {
  if (block.status === "upcoming") return `Starts ${startDayLabel(block.rules.week_start)}`;
  if (block.status === "ended") return "Ended";
  return `Week ${block.week_index} of ${block.weeks_total} · ${plural(block.days_left, "day")} left`;
};

/** Caption beside the ring. this_week.index is 0 before the start and weeks+1 after the end. */
export const viewerCaption = (block: ConsistencyBlock, row: ChallengeLeaderboardRow): string => {
  const week = row.this_week!;
  if (block.status === "upcoming") return `Week 1 quota: ${week.quota} lifts`;
  if (block.status === "ended") {
    return `Final: ${formatScoreValue(row.score, "consistency")} pts · ${row.weeks_met ?? 0} of ${block.weeks_total} weeks met`;
  }
  if (week.met) return block.week_index < block.weeks_total ? "Quota met — the bar rises next week." : "Quota met.";
  return `Week ${block.week_index} quota: ${week.quota} lifts`;
};

const CARD_STYLE: React.CSSProperties = {
  background: "linear-gradient(160deg, rgba(47,123,246,.18), rgba(47,123,246,.05))",
  border: "1px solid rgba(47,123,246,.32)",
};

const RING_R = 34;
const RING_C = 2 * Math.PI * RING_R;

const ProgressRing: React.FC<{ lifts: number; quota: number; met: boolean }> = ({ lifts, quota, met }) => {
  const fraction = quota > 0 ? Math.min(1, Math.max(0, lifts / quota)) : 0;
  const color = met ? "#4ade80" : "#2f7bf6";
  return (
    <div className="relative h-[100px] w-[100px] flex-none">
      <svg viewBox="0 0 84 84" className="h-full w-full -rotate-90" aria-hidden="true">
        <circle cx="42" cy="42" r={RING_R} fill="none" stroke="rgba(255,255,255,.12)" strokeWidth="8" />
        <circle
          data-testid="consistency-ring-arc"
          cx="42"
          cy="42"
          r={RING_R}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={RING_C}
          strokeDashoffset={RING_C * (1 - fraction)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
        <span data-testid="consistency-ring-count" className="text-[14px] font-bold tabular-nums">
          {formatScoreValue(lifts, "consistency")} / {quota}
        </span>
        <span className="mt-1 text-[9.5px] font-semibold uppercase tracking-wider text-white/45">lifts</span>
      </div>
    </div>
  );
};

/** 100 Club hero: the week line, the viewer's ring + streak, and this week's type leaders. */
const ConsistencyHero: React.FC<ConsistencyHeroProps> = ({ block, liftTypes, viewerRow }) => {
  const week = viewerRow?.this_week ?? null;
  const streak = viewerRow?.streak ?? 0;
  const leaders = block.status === "live"
    ? liftTypes.filter((t) => (block.type_leaders[t] ?? []).length > 0)
    : [];
  const warmup = viewerRow?.warmup_lifts ?? 0;

  return (
    <div data-testid="consistency-hero" className="mb-6 rounded-2xl p-4 lg:max-w-2xl lg:p-5" style={CARD_STYLE}>
      <div data-testid="consistency-eyebrow" className="text-[10.5px] font-semibold uppercase tracking-wider text-[#9fc2ff]">Weekly quota</div>
      <div data-testid="consistency-week-line" className="mt-1 text-[17px] font-bold tracking-tight">
        {weekLine(block)}
      </div>

      {week && (
        <div data-testid="consistency-viewer" className="mt-3.5 flex items-center gap-4">
          <ProgressRing lifts={week.lifts} quota={week.quota} met={week.met} />
          <div className="min-w-0 space-y-1 text-[13px]">
            <div data-testid="consistency-caption" className="font-medium text-white/80">
              {viewerCaption(block, viewerRow!)}
            </div>
            {streak > 0 && (
              <div data-testid="consistency-streak" className="font-semibold text-amber-300">
                <span aria-hidden="true">🔥 </span>
                {streak}-week streak
              </div>
            )}
            {week.pending > 0 && (
              <div data-testid="consistency-pending" className="text-white/60">
                {plural(week.pending, "video")} still analysing
              </div>
            )}
            {block.status === "upcoming" && warmup > 0 && (
              <div data-testid="consistency-warmup" className="text-white/60">
                {formatScoreValue(warmup, "consistency")} warm-up {warmup === 1 ? "lift" : "lifts"} logged — scoring starts Monday
              </div>
            )}
            {week.leading.length > 0 && block.status === "live" && (
              <div className="text-white/60">You lead {week.leading.join(", ")} this week</div>
            )}
          </div>
        </div>
      )}

      {leaders.length > 0 && (
        <div className="mt-3.5 flex flex-wrap gap-2">
          {leaders.map((t) => {
            const unit = t === "Plank" ? " s" : "";
            const names = block.type_leaders[t].map((l) => l.name || "Athlete").join(" & ");
            const amount = block.type_leaders[t][0].amount;
            return (
              <span
                key={t}
                data-testid={`consistency-leader-${t}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-white/70"
              >
                <span className="font-semibold text-white/85">{t}</span>
                <span>
                  {names} {formatScoreValue(amount, "consistency")}
                  {unit}
                </span>
                <span className="rounded-full bg-amber-500/15 px-1.5 text-[10px] font-semibold uppercase tracking-wide text-amber-300">
                  leading
                </span>
              </span>
            );
          })}
        </div>
      )}
      {leaders.length > 0 && (
        <div data-testid="consistency-bonus-note" className="mt-2 text-[11.5px] text-white/50">
          Type bonuses (+{block.rules.type_bonus} each) are added when the week ends on Sunday.
        </div>
      )}
    </div>
  );
};

export default ConsistencyHero;
