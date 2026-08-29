/** "Jul 2" this year, "Jul 2, 2025" otherwise; bare ISO dates are parsed as local days. */
export const formatDay = (iso: string | null | undefined, now: Date = new Date()): string => {
  if (!iso) return "";
  const d = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T00:00:00`) : new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", ...(sameYear ? {} : { year: "numeric" }) });
};
