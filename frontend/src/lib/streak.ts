export type ActivityKind = "lift" | "bowl" | "golf";

export interface ActivityEntry {
  at: string;
  kind: ActivityKind;
}

export interface StreakDay {
  label: string;
  date: Date;
  active: boolean;
  isToday: boolean;
  isFuture: boolean;
}

export interface Streak {
  weeks: number;
  week: StreakDay[];
}

const DAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"];

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function startOfWeek(d: Date): Date {
  const day = startOfDay(d);
  const offset = (day.getDay() + 6) % 7;
  day.setDate(day.getDate() - offset);
  return day;
}

function dayKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

export function computeStreak(activity: ActivityEntry[], now: Date = new Date()): Streak {
  const activeDays = new Set<string>();
  const activeWeeks = new Set<number>();
  for (const entry of activity) {
    const at = new Date(entry.at);
    if (Number.isNaN(at.getTime())) continue;
    activeDays.add(dayKey(at));
    activeWeeks.add(startOfWeek(at).getTime());
  }

  const thisWeek = startOfWeek(now);
  const today = startOfDay(now);
  const week: StreakDay[] = DAY_LABELS.map((label, i) => {
    const date = new Date(thisWeek);
    date.setDate(thisWeek.getDate() + i);
    return {
      label,
      date,
      active: activeDays.has(dayKey(date)),
      isToday: date.getTime() === today.getTime(),
      isFuture: date.getTime() > today.getTime(),
    };
  });

  let weeks = 0;
  const cursor = new Date(thisWeek);
  if (!activeWeeks.has(cursor.getTime())) cursor.setDate(cursor.getDate() - 7);
  while (activeWeeks.has(cursor.getTime())) {
    weeks += 1;
    cursor.setDate(cursor.getDate() - 7);
  }

  return { weeks, week };
}
