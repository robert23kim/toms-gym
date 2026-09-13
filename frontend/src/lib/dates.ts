/** "Jul 2" this year, "Jul 2, 2025" otherwise; bare ISO dates are parsed as local days. */
export const formatDay = (iso: string | null | undefined, now: Date = new Date()): string => {
  if (!iso) return "";
  const d = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T00:00:00`) : new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", ...(sameYear ? {} : { year: "numeric" }) });
};

/** Local calendar date as YYYY-MM-DD (never UTC, which flips the day after ~7pm US time). */
export const todayLocal = (now: Date = new Date()): string => {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
};
