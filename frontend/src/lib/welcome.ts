export interface LastLift {
  lift_type: string | null;
  grade?: string | null;
  hold_s?: number | null;
  total_reps?: number | null;
  weight?: number | null;
  created_at: string | null;
  competition_name?: string | null;
}

const DAY = 86_400_000;

export const sinceCopy = (iso: string | null | undefined, now: Date = new Date()): string | null => {
  if (!iso) return null;
  const then = new Date(iso);
  if (isNaN(then.getTime())) return null;
  const days = Math.floor((now.getTime() - then.getTime()) / DAY);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months === 1 ? "" : "s"} ago`;
  const years = Math.floor(days / 365);
  return `${years} year${years === 1 ? "" : "s"} ago`;
};

const title = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();

const isBodyweight = (lift: string): boolean => /plank|pushup|situp/i.test(lift);

/** "Pushup · 35 reps · C" / "Plank · 3:21" / "Bench press · 80kg · D" */
export const lastLiftCopy = (lift: LastLift): string => {
  const type = lift.lift_type ? title(lift.lift_type) : "Lift";
  const bits: string[] = [type];
  if (/plank/i.test(type) && lift.hold_s != null) {
    const total = Math.floor(lift.hold_s);
    bits.push(`${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`);
  } else if (lift.total_reps != null && isBodyweight(type)) {
    bits.push(`${lift.total_reps} rep${lift.total_reps === 1 ? "" : "s"}`);
  } else if (lift.weight && !isBodyweight(type)) {
    bits.push(`${lift.weight}kg`);
  }
  if (lift.grade) bits.push(lift.grade);
  return bits.join(" · ");
};
