import { Champion, formatChampionScore } from "./api";

export const localDate = (iso: string): Date => new Date(`${iso}T00:00:00`);

export interface ChampionTally {
  user_id: string;
  name: string;
  wins: number;
  latest: Champion;
}

export const championTally = (champions: Champion[]): ChampionTally[] => {
  const byUser = new Map<string, ChampionTally>();
  for (const c of champions) {
    const t = byUser.get(c.user_id);
    if (!t) {
      byUser.set(c.user_id, { user_id: c.user_id, name: c.name, wins: 1, latest: c });
    } else {
      t.wins += 1;
      if (c.ended_on > t.latest.ended_on) t.latest = c;
    }
  }
  return [...byUser.values()].sort(
    (a, b) => b.wins - a.wins || b.latest.ended_on.localeCompare(a.latest.ended_on)
  );
};

export const dynastyLabel = (wins: number): string | null => {
  if (wins < 2) return null;
  if (wins === 2) return "Back-to-back champion";
  if (wins === 3) return "Three-peat";
  return `${wins}× champion`;
};

/** 1 for an athlete's first-ever win, 2 for the second, … (by ended_on). */
export const ordinalWin = (all: Champion[], c: Champion): number =>
  all.filter((o) => o.user_id === c.user_id && o.ended_on <= c.ended_on).length;

const PHOTO_FINISH: Record<Champion["metric"], number> = {
  time: 5,
  weight: 2.5,
  reps: 1,
};

export const marginCopy = (c: Champion): string | null => {
  const rival = c.runners_up?.[0];
  if (c.margin == null || !rival) return null;
  const name = rival.name || "the runner-up";
  const amount = formatChampionScore(c.metric, c.margin);
  if (c.margin <= PHOTO_FINISH[c.metric]) {
    return `Edged out ${name} by ${amount} — a photo finish`;
  }
  return `Won by ${amount} over ${name}`;
};

export const reignDays = (endedOn: string, now: Date = new Date()): number =>
  Math.max(0, Math.floor((now.getTime() - localDate(endedOn).getTime()) / 86_400_000));

export const groupByYear = (champions: Champion[]): [number, Champion[]][] => {
  const groups = new Map<number, Champion[]>();
  for (const c of champions) {
    const y = localDate(c.ended_on).getFullYear();
    groups.set(y, [...(groups.get(y) || []), c]);
  }
  return [...groups.entries()].sort((a, b) => b[0] - a[0]);
};
