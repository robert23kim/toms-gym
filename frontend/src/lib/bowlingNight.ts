export interface NightGame {
  sheet_id: string;
  played_on: string;
  total_score: number | null;
}

export type BestSince =
  | { kind: "first" }
  | { kind: "best-yet" }
  | { kind: "since"; date: string }
  | { kind: "none" };

export interface Night {
  playedOn: string;
  count: number;
  avg: number;
  high: number;
  priorAvg: number | null;
  delta: number | null;
  bestSince: BestSince;
}

const scored = (g: NightGame): g is NightGame & { total_score: number } => g.total_score != null;

const mean = (xs: number[]): number => xs.reduce((a, b) => a + b, 0) / xs.length;

export const summarizeNight = (games: NightGame[], sheetId: string | null | undefined): Night | null => {
  if (!sheetId) return null;
  const tonight = games.filter(scored).filter((g) => g.sheet_id === sheetId);
  if (tonight.length === 0) return null;
  const playedOn = tonight[0].played_on;
  const scores = tonight.map((g) => g.total_score);
  const avg = Math.round(mean(scores) * 10) / 10;
  const high = Math.max(...scores);

  const others = games.filter(scored).filter((g) => g.sheet_id !== sheetId);
  const priorAvg = others.length ? Math.round(mean(others.map((g) => g.total_score)) * 10) / 10 : null;
  const delta = priorAvg == null ? null : Math.round((avg - priorAvg) * 10) / 10;

  const earlier = others.filter((g) => g.played_on <= playedOn).sort((a, b) => (a.played_on < b.played_on ? 1 : -1));
  let bestSince: BestSince;
  if (earlier.length === 0) bestSince = { kind: "first" };
  else {
    const match = earlier.find((g) => g.total_score >= high);
    bestSince = match ? { kind: "since", date: match.played_on } : { kind: "best-yet" };
  }

  return { playedOn, count: tonight.length, avg, high, priorAvg, delta, bestSince };
};
