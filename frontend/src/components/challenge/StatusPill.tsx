import React from "react";

type Status = "upcoming" | "ongoing" | "completed";

interface StatusPillProps {
  status: Status;
  startDate: string;
  endDate: string;
}

function daysBetween(from: Date, to: Date): number {
  return Math.ceil((to.getTime() - from.getTime()) / 86_400_000);
}

/**
 * Challenge status pill with a countdown, e.g. "Ongoing · 23d left". Extends the
 * page's `determineStatus` by deriving the remaining/until days from the dates.
 */
const StatusPill: React.FC<StatusPillProps> = ({ status, startDate, endDate }) => {
  const now = new Date();

  let label: string;
  let tone: string;
  let dot: string;

  if (status === "upcoming") {
    const d = Math.max(0, daysBetween(now, new Date(startDate)));
    label = d > 0 ? `Upcoming · starts in ${d}d` : "Starts today";
    tone = "bg-blue-500/15 text-blue-400";
    dot = "bg-blue-400";
  } else if (status === "ongoing") {
    const d = daysBetween(now, new Date(endDate));
    label = d > 0 ? `Ongoing · ${d}d left` : "Ongoing · ends today";
    tone = "text-[#4ade80] bg-[rgba(52,199,89,.14)]";
    dot = "bg-[#4ade80]";
  } else {
    label = "Ended";
    tone = "bg-white/10 text-white/50";
    dot = "bg-white/40";
  }

  return (
    <span
      data-testid="status-pill"
      data-status={status}
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${tone}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
};

export default StatusPill;
