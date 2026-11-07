import React, { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import type { ChallengeLeaderboardRow, ConsistencyBlock, ConsistencyThisWeek } from "../../lib/types";
import { formatScoreValue } from "./metric";
import {
  groupUploadsByDay,
  pointsReceipt,
  ringSegments,
  timeLabel,
  typeColor,
  type ClubUpload,
} from "./clubBreakdown";

interface ConsistencyHeroProps {
  block: ConsistencyBlock;
  liftTypes: string[];
  /** The viewer's own row; null for anonymous visitors and non-entrants (no ring). */
  viewerRow: ChallengeLeaderboardRow | null;
  /** The viewer's uploads in the week in progress, shown behind a tap. */
  uploads?: ClubUpload[];
}

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "Monday 2 Nov" from a bare YYYY-MM-DD, read as a local day. */
export const startDayLabel = (iso: string): string => {
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return `${WEEKDAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
};

/** "Sun 27 Dec": the last day of the final week, read as a local day. */
export const finalDayLabel = (rules: Pick<ConsistencyBlock["rules"], "week_start" | "weeks">): string => {
  const d = new Date(`${rules.week_start}T00:00:00`);
  if (Number.isNaN(d.getTime())) return rules.week_start;
  d.setDate(d.getDate() + rules.weeks * 7 - 1);
  return `${WEEKDAYS[d.getDay()].slice(0, 3)} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
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
const SEG_GAP = 1.5;

const fmt = (n: number) => formatScoreValue(n, "consistency");
const isPlank = (t: string) => t.trim().toLowerCase() === "plank";

const ProgressRing: React.FC<{ week: ConsistencyThisWeek; liftTypes: string[] }> = ({ week, liftTypes }) => {
  const segments = ringSegments(week, liftTypes);
  return (
    <div className="relative h-[104px] w-[104px] flex-none">
      <svg viewBox="0 0 84 84" className="h-full w-full -rotate-90" aria-hidden="true">
        <circle cx="42" cy="42" r={RING_R} fill="none" stroke="rgba(255,255,255,.1)" strokeWidth="9" />
        {segments.map((s) => {
          const length = Math.max(0, s.fraction * RING_C - (segments.length > 1 ? SEG_GAP : 0));
          return (
            <circle
              key={s.type}
              data-testid={`consistency-ring-seg-${s.type}`}
              data-fraction={s.fraction}
              cx="42"
              cy="42"
              r={RING_R}
              fill="none"
              stroke={typeColor(s.type)}
              strokeWidth="9"
              strokeDasharray={`${length} ${RING_C}`}
              strokeDashoffset={-s.start * RING_C}
            />
          );
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
        <span data-testid="consistency-ring-count" className="text-[14px] font-bold tabular-nums">
          {fmt(week.lifts)} / {week.quota}
        </span>
        <span className="mt-1 text-[9.5px] font-semibold uppercase tracking-wider text-white/60">lifts</span>
      </div>
    </div>
  );
};

const Legend: React.FC<{ week: ConsistencyThisWeek; liftTypes: string[] }> = ({ week, liftTypes }) => {
  const byType = week.by_type ?? {};
  const types = [...liftTypes, ...Object.keys(byType).filter((t) => !liftTypes.includes(t))];
  return (
    <div data-testid="consistency-legend" className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[13px] tabular-nums">
      {types.map((t) => {
        const n = byType[t] ?? 0;
        const zero = n <= 0;
        const leads = week.leading.includes(t);
        return (
          <div
            key={t}
            data-testid={`consistency-legend-${t}`}
            className={`flex min-h-[28px] items-center gap-2 ${zero ? "text-white/55" : ""}`}
          >
            <span
              className="h-2.5 w-2.5 flex-none rounded-[3px]"
              style={{ background: zero ? "rgba(255,255,255,.22)" : typeColor(t) }}
              aria-hidden="true"
            />
            <span className="flex-1 font-semibold">{t}</span>
            <span className="font-bold">{fmt(n)}</span>
            {isPlank(t) && n > 0 && (
              <span className="font-medium text-white/60">· {fmt(week.plank_seconds)} s</span>
            )}
            {leads && (
              <span className="rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-wide text-amber-300">
                lead
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
};

const RowLine: React.FC<{ testId: string; earned?: boolean; pending?: boolean; children: React.ReactNode }> = ({
  testId,
  earned,
  pending,
  children,
}) => (
  <div
    data-testid={testId}
    data-earned={earned === undefined ? undefined : String(earned)}
    className={`flex items-center justify-between gap-3 py-2 ${pending ? "border-t border-dashed border-white/15 text-white/60" : "border-t border-white/[.06]"} ${earned === false ? "text-white/60" : ""}`}
  >
    {children}
  </div>
);

const Receipt: React.FC<{ week: ConsistencyThisWeek; block: ConsistencyBlock; score: number }> = ({ week, block, score }) => {
  const r = pointsReceipt(week, block.rules);
  return (
    <div data-testid="consistency-receipt" className="border-t border-white/10 pt-1 text-[13px] tabular-nums">
      <div className="pb-0.5 pt-2.5 text-[10.5px] font-semibold uppercase tracking-wider text-[#9fc2ff]">Points this week</div>
      <RowLine testId="receipt-banked">
        <span className="flex items-baseline gap-1.5">
          <span className="font-semibold">Lifts banked</span>
          <span className="font-medium text-white/60">{fmt(r.banked)} of {r.quota}</span>
        </span>
        <span className="font-extrabold text-green-300">+{fmt(r.banked)}</span>
      </RowLine>
      <RowLine testId="receipt-quota" earned={r.met}>
        <span className="flex items-baseline gap-1.5">
          <span className="font-semibold">Quota met</span>
          {!r.met && <span className="font-medium">{fmt(r.toGo)} to go</span>}
        </span>
        <span className={`font-extrabold ${r.met ? "text-green-300" : ""}`}>+{block.rules.quota_bonus}</span>
      </RowLine>
      {r.leads.map((t) => (
        <RowLine key={t} testId={`receipt-lead-${t}`} pending>
          <span className="flex items-baseline gap-1.5">
            <span className="font-semibold">{t} lead</span>
            <span className="font-medium">· locks Sun</span>
          </span>
          <span className="font-extrabold text-amber-300">+{r.typeBonus}</span>
        </RowLine>
      ))}
      <div
        data-testid="receipt-total"
        className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 border-t border-white/15 pt-2.5"
      >
        <span className="text-[15px] font-extrabold">{fmt(r.total)} pts this week</span>
        <span className="text-[12px] font-semibold text-white/60">
          {r.leads.length > 0 && (
            <span>
              {fmt(r.ifLeadsHold)} if the {r.leads.length === 1 ? "lead holds" : "leads hold"}
            </span>
          )}
          {r.leads.length > 0 && score !== r.total && <span> · </span>}
          {score !== r.total && <span>{fmt(score)} overall</span>}
        </span>
      </div>
    </div>
  );
};

const Uploads: React.FC<{ uploads: ClubUpload[]; tz: string }> = ({ uploads, tz }) => {
  const [open, setOpen] = useState(false);
  const days = open ? groupUploadsByDay(uploads, tz) : [];
  return (
    <div>
      <button
        type="button"
        data-testid="consistency-uploads-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex min-h-[44px] w-full items-center justify-between gap-2 rounded-xl border border-white/10 bg-white/5 px-3 text-[13px] font-semibold text-white hover:bg-white/10"
      >
        <span>
          This week&apos;s uploads <span className="text-white/60">· {uploads.length}</span>
        </span>
        <span aria-hidden="true" className="text-white/60">{open ? "▴" : "▾"}</span>
      </button>
      {open && (
        <div data-testid="consistency-uploads" className="mt-2 flex flex-col">
          {days.map((d) => (
            <Fragment key={d.day}>
              <div
                data-testid="consistency-upload-day"
                className="pb-1 pt-2 text-[10.5px] font-semibold uppercase tracking-wider text-white/60"
              >
                {d.day}
              </div>
              {d.items.map((u) => (
                <Link
                  key={u.id}
                  to={u.href}
                  data-testid={`consistency-upload-${u.id}`}
                  className="flex min-h-[52px] items-center gap-3 border-t border-white/[.06] py-1.5 text-white no-underline hover:bg-white/5"
                >
                  <span
                    className="flex h-10 w-10 flex-none items-center justify-center rounded-[10px] border"
                    style={{ background: `${typeColor(u.liftType)}22`, borderColor: `${typeColor(u.liftType)}55` }}
                    aria-hidden="true"
                  >
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: typeColor(u.liftType) }} />
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="flex items-baseline gap-1.5 text-[14px] font-bold">
                      <span>{u.liftType}</span>
                      {u.seconds != null && <span className="font-medium text-white/60">{u.seconds.toFixed(1)} s</span>}
                    </span>
                    <span className="text-[12px] text-white/60">{timeLabel(u.at, tz)}</span>
                  </span>
                  {u.failed ? (
                    <span className="text-[12px] font-semibold text-white/60">failed</span>
                  ) : u.lifts == null ? (
                    <span className="text-[12px] font-semibold text-white/60">analysing</span>
                  ) : (
                    <span className="text-[16px] font-extrabold tabular-nums text-green-300">+{fmt(u.lifts)}</span>
                  )}
                </Link>
              ))}
            </Fragment>
          ))}
        </div>
      )}
    </div>
  );
};

/** 100 Club hero: the week line, the viewer's ring, legend, points receipt and uploads, and this week's type leaders. */
const ConsistencyHero: React.FC<ConsistencyHeroProps> = ({ block, liftTypes, viewerRow, uploads = [] }) => {
  const week = viewerRow?.this_week ?? null;
  const streak = viewerRow?.streak ?? 0;
  const live = block.status === "live";
  const leaders = live ? liftTypes.filter((t) => (block.type_leaders[t] ?? []).length > 0) : [];
  const warmup = viewerRow?.warmup_lifts ?? 0;

  return (
    <div data-testid="consistency-hero" className="mb-6 rounded-2xl p-4 lg:max-w-2xl lg:p-5" style={CARD_STYLE}>
      <div data-testid="consistency-eyebrow" className="text-[10.5px] font-semibold uppercase tracking-wider text-[#9fc2ff]">Weekly quota</div>
      <div data-testid="consistency-week-line" className="mt-1 text-[17px] font-bold tracking-tight">
        {weekLine(block)}
      </div>

      {week && (
        <div data-testid="consistency-viewer" className="mt-3.5 flex items-center gap-4">
          <ProgressRing week={week} liftTypes={liftTypes} />
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
                {fmt(warmup)} warm-up {warmup === 1 ? "lift" : "lifts"} logged — scoring starts Monday
              </div>
            )}
          </div>
        </div>
      )}

      {week && live && (
        <div className="mt-3.5 flex flex-col gap-3.5">
          <Legend week={week} liftTypes={liftTypes} />
          <Receipt week={week} block={block} score={viewerRow!.score} />
          {uploads.length > 0 && <Uploads uploads={uploads} tz={block.rules.tz} />}
        </div>
      )}

      {leaders.length > 0 && (
        <div className="mt-3.5 flex flex-wrap gap-2">
          {leaders.map((t) => {
            const unit = isPlank(t) ? " s" : "";
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
                  {names} {fmt(amount)}
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
