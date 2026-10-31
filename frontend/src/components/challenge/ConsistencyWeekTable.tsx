import React from "react";
import type { ConsistencyWeek } from "../../lib/types";
import { formatScoreValue } from "./metric";

interface Props {
  weeks: ConsistencyWeek[];
  /** Index of the week in progress (its bonuses are not awarded yet). */
  liveIndex?: number | null;
}

/** Per-athlete week table shown in place of the attempt list on a 100 Club board. */
const ConsistencyWeekTable: React.FC<Props> = ({ weeks, liveIndex = null }) => {
  if (!weeks.length) {
    return (
      <div data-testid="week-table" className="px-4 py-3 text-[12.5px] text-white/50">
        No scoring weeks yet.
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
    <table data-testid="week-table" className="w-full bg-white/[.02] text-left text-[12px] tabular-nums lg:text-[12.5px]">
      <thead>
        <tr className="text-[10.5px] font-semibold uppercase tracking-wide text-white/40">
          <th className="px-2 py-2 lg:px-3 font-semibold">Week</th>
          <th className="px-1.5 py-2 font-semibold lg:px-2">Quota</th>
          <th className="px-1.5 py-2 font-semibold lg:px-2">Lifts</th>
          <th className="px-1.5 py-2 font-semibold lg:px-2">Met</th>
          <th className="px-1.5 py-2 font-semibold lg:px-2">Bonuses</th>
          <th className="px-2 py-2 lg:px-3 text-right font-semibold">Points</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-white/[.05]">
        {weeks.map((w) => {
          const live = liveIndex === w.index;
          return (
            <tr key={w.index} data-testid={`week-row-${w.index}`} className="text-white/75">
              <td className="px-2 py-2 lg:px-3 font-semibold">
                {w.index}
                {live && <span className="ml-1.5 text-[10px] font-semibold uppercase text-[#7fb0ff]">now</span>}
              </td>
              <td className="px-1.5 py-2 lg:px-2">{w.quota}</td>
              <td className="px-1.5 py-2 lg:px-2">{formatScoreValue(w.lifts, "consistency")}</td>
              <td className="px-1.5 py-2 lg:px-2">
                {w.met ? (
                  <span className="text-[#4ade80]" role="img" aria-label="met">✓</span>
                ) : (
                  <span className="text-white/35" role="img" aria-label={live ? "in progress" : "missed"}>{live ? "…" : "—"}</span>
                )}
              </td>
              <td className="px-1.5 py-2 lg:px-2">{w.bonuses.length ? w.bonuses.join(", ") : "—"}</td>
              <td className="px-2 py-2 lg:px-3 text-right font-semibold">{formatScoreValue(w.points, "consistency")}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
    </div>
  );
};

export default ConsistencyWeekTable;
