export interface RoundLike {
  id: string;
  holes: number;
  total_score: number | null;
  course?: { id?: string | null; name?: string | null } | null;
}

export type RoundHighlight =
  | { kind: "best-ever"; holes: number }
  | { kind: "best-at-course"; course: string }
  | { kind: "first-at-course"; course: string };

export function roundHighlight(rounds: RoundLike[], roundId: string): RoundHighlight | null {
  const me = rounds.find((r) => r.id === roundId);
  if (!me || me.total_score == null) return null;
  const mine = me.total_score;
  const peers = rounds.filter(
    (r): r is RoundLike & { total_score: number } =>
      r.id !== me.id && r.holes === me.holes && r.total_score != null,
  );
  if (peers.length > 0 && peers.every((r) => r.total_score > mine)) {
    return { kind: "best-ever", holes: me.holes };
  }
  const courseId = me.course?.id;
  const courseName = me.course?.name;
  if (!courseId || !courseName) return null;
  const here = peers.filter((r) => r.course?.id === courseId);
  if (here.length === 0) return { kind: "first-at-course", course: courseName };
  if (here.every((r) => r.total_score > mine)) return { kind: "best-at-course", course: courseName };
  return null;
}

export function highlightCopy(h: RoundHighlight): string {
  switch (h.kind) {
    case "best-ever":
      return `Your best ${h.holes} yet`;
    case "best-at-course":
      return `Your best at ${h.course}`;
    case "first-at-course":
      return `First round at ${h.course}`;
  }
}
