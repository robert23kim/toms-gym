import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Play } from "lucide-react";
import axios from "axios";
import { API_URL } from "../../config";
import type { ChallengeMetric } from "../../lib/types";

interface AttemptRow {
  attempt_id: string;
  lift_type: string | null;
  weight: number | null;
  created_at: string | null;
  analysis_status: string | null;
  grade: string | null;
  hold_s: number | null;
}

interface Props {
  userId: string;
  competitionId: string;
  metric: ChallengeMetric;
}

const GRADE_CLASS: Record<string, string> = {
  A: "bg-green-500/15 text-green-500",
  B: "bg-green-400/15 text-green-400",
  C: "bg-yellow-500/15 text-yellow-500",
  D: "bg-orange-500/15 text-orange-500",
  F: "bg-red-500/15 text-red-500",
};

const fmtHold = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

const fmtDate = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" })
    : "";

/** The attempt's value under this challenge's metric, for 🏆 ranking. */
const metricValue = (row: AttemptRow, metric: ChallengeMetric): number | null =>
  metric === "time" ? row.hold_s : row.weight;

/**
 * Lazy attempt history for one athlete in one challenge — rendered under an
 * expanded leaderboard row. Newest first; the best attempt (max hold for time
 * boards, max weight for weight boards) gets the 🏆.
 */
const AttemptHistory: React.FC<Props> = ({ userId, competitionId, metric }) => {
  const [rows, setRows] = useState<AttemptRow[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    axios
      .get(`${API_URL}/users/${userId}/lifts?competition_id=${competitionId}&limit=50`)
      .then((res) => {
        if (!cancelled) setRows(res.data.lifts ?? []);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [userId, competitionId]);

  if (failed) {
    return (
      <div className="px-3.5 py-2 text-xs text-muted-foreground">Couldn't load attempts.</div>
    );
  }
  if (rows === null) {
    return (
      <div className="px-3.5 py-2 text-xs text-muted-foreground">Loading attempts…</div>
    );
  }
  if (rows.length === 0) return null;

  const values = rows
    .map((r) => metricValue(r, metric))
    .filter((v): v is number => v != null);
  const best = values.length > 1 ? Math.max(...values) : null;

  return (
    <div className="border-t border-white/5 bg-black/20">
      {rows.map((row) => {
        const value = metricValue(row, metric);
        const isBest = best != null && value != null && value === best;
        const analyzing =
          row.analysis_status === "queued" || row.analysis_status === "processing";
        return (
          <Link
            key={row.attempt_id}
            to={`/challenges/${competitionId}/participants/${userId}/video/${row.attempt_id}`}
            className="flex items-center gap-3 pl-10 pr-3.5 py-2 text-sm hover:bg-white/5 transition-colors"
          >
            <span className="text-xs text-muted-foreground w-12 shrink-0 tabular-nums">
              {fmtDate(row.created_at)}
            </span>
            <span className="flex-1 min-w-0 flex items-center gap-2">
              {metric === "time" ? (
                <span className="font-medium tabular-nums">
                  {row.hold_s != null ? fmtHold(row.hold_s) : analyzing ? "analyzing…" : "—"}
                </span>
              ) : (
                <>
                  <span className="font-medium">
                    {row.weight != null && row.weight > 0 ? `${row.weight}kg` : "—"}
                  </span>
                  {row.grade && (
                    <span className={`inline-flex items-center justify-center w-5 h-5 rounded text-[11px] font-bold ${GRADE_CLASS[row.grade] ?? "bg-secondary"}`}>
                      {row.grade}
                    </span>
                  )}
                </>
              )}
              {isBest && <span aria-label="best attempt">🏆</span>}
            </span>
            <Play className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          </Link>
        );
      })}
    </div>
  );
};

export default AttemptHistory;
