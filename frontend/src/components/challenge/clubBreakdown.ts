import type { ConsistencyRules, ConsistencyThisWeek } from "../../lib/types";

const TYPE_COLORS: Record<string, string> = {
  situp: "#5b9cff",
  pushup: "#4ade80",
  plank: "#fbbf24",
  squat: "#a1a1aa",
};
const OTHER_COLOR = "#c4b5fd";

export const typeColor = (type: string): string => TYPE_COLORS[type.trim().toLowerCase()] ?? OTHER_COLOR;

export interface RingSegment {
  type: string;
  fraction: number;
  start: number;
}

/** Arcs for the quota ring, one per type with lifts, in lift-type order; never past a full ring. */
export function ringSegments(
  week: Pick<ConsistencyThisWeek, "by_type" | "quota" | "lifts">,
  liftTypes: string[],
): RingSegment[] {
  const byType = week.by_type ?? {};
  const order = [...liftTypes, ...Object.keys(byType).filter((t) => !liftTypes.includes(t))];
  const denominator = Math.max(week.quota, week.lifts, 1);
  const out: RingSegment[] = [];
  let start = 0;
  for (const type of order) {
    const n = byType[type] ?? 0;
    if (n <= 0) continue;
    const fraction = Math.min(n / denominator, 1 - start);
    if (fraction <= 0) break;
    out.push({ type, fraction, start });
    start += fraction;
  }
  return out;
}

export interface Receipt {
  banked: number;
  quota: number;
  met: boolean;
  toGo: number;
  quotaBonus: number;
  leads: string[];
  typeBonus: number;
  total: number;
  ifLeadsHold: number;
}

/** This week's points itemised; mirrors backend consistency scoring for the week in progress. */
export function pointsReceipt(
  week: Pick<ConsistencyThisWeek, "quota" | "lifts" | "met" | "leading">,
  rules: Pick<ConsistencyRules, "quota_bonus" | "type_bonus">,
): Receipt {
  const banked = Math.min(week.lifts, week.quota);
  const quotaBonus = week.met ? rules.quota_bonus : 0;
  const leads = week.leading ?? [];
  const total = banked + quotaBonus;
  return {
    banked,
    quota: week.quota,
    met: week.met,
    toGo: Math.max(0, week.quota - week.lifts),
    quotaBonus,
    leads,
    typeBonus: rules.type_bonus,
    total,
    ifLeadsHold: total + leads.length * rules.type_bonus,
  };
}

export interface ClubUpload {
  id: string;
  liftType: string;
  /** Upload instant, ISO. */
  at: string;
  /** Lifts the attempt banked; null while analysis is pending. */
  lifts: number | null;
  /** Plank seconds held, when known. */
  seconds: number | null;
  failed: boolean;
  href: string;
}

const HAS_OFFSET = /([zZ]|[+-]\d\d:?\d\d)$/;
const instantOf = (at: string): Date => new Date(HAS_OFFSET.test(at) ? at : `${at}Z`);

const dayKey = (at: string, tz: string): string =>
  new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(instantOf(at));

const dayLabel = (at: string, tz: string): string =>
  new Intl.DateTimeFormat("en-GB", { timeZone: tz, weekday: "short", day: "numeric", month: "short" })
    .format(instantOf(at))
    .replace(",", "");

/** "1:24 pm" in the challenge's zone. */
export const timeLabel = (at: string, tz: string): string =>
  new Intl.DateTimeFormat("en-US", { timeZone: tz, hour: "numeric", minute: "2-digit", hour12: true })
    .format(instantOf(at))
    .toLowerCase()
    .replace(/\s+/g, " ");

export interface UploadDay {
  day: string;
  items: ClubUpload[];
}

/** Uploads grouped by local day, newest day and newest upload first. */
export function groupUploadsByDay(uploads: ClubUpload[], tz: string): UploadDay[] {
  const sorted = [...uploads].sort((a, b) => instantOf(b.at).getTime() - instantOf(a.at).getTime());
  const groups: { key: string; day: string; items: ClubUpload[] }[] = [];
  for (const u of sorted) {
    const key = dayKey(u.at, tz);
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.items.push(u);
    else groups.push({ key, day: dayLabel(u.at, tz), items: [u] });
  }
  return groups.map(({ day, items }) => ({ day, items }));
}
