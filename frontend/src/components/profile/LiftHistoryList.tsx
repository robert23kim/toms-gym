import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import axios from "axios";
import { API_URL } from "../../config";

interface LiftRow {
  attempt_id: string;
  competition_id: string;
  competition_name: string | null;
  lift_type: string | null;
  weight: number | null;
  created_at: string | null;
  status: string | null;
  analysis_status: string | null;
  grade: string | null;
  total_reps: number | null;
  hold_s: number | null;
}

interface Props {
  userId: string;
}

const PAGE = 20;

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

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** The analysis payoff cell: hold time for planks, grade pill for rep lifts,
 * or a muted processing/absent state. */
const Payoff: React.FC<{ row: LiftRow }> = ({ row }) => {
  if (row.analysis_status === "completed") {
    if (row.lift_type === "plank" && row.hold_s != null) {
      return <span className="font-semibold tabular-nums">{fmtHold(row.hold_s)}</span>;
    }
    if (row.grade) {
      return (
        <span className={`inline-flex items-center justify-center w-7 h-7 rounded-md text-sm font-bold ${GRADE_CLASS[row.grade] ?? "bg-secondary"}`}>
          {row.grade}
        </span>
      );
    }
  }
  if (row.analysis_status === "queued" || row.analysis_status === "processing") {
    return <span className="text-xs text-muted-foreground">analyzing…</span>;
  }
  return <span className="text-xs text-muted-foreground">—</span>;
};

/**
 * Paginated lift history: date · lift · weight · analysis payoff, each row
 * linking straight to the VideoPlayer result. Renders nothing when the user
 * has no lifts (the gallery's empty state handles that) or on fetch failure.
 */
const LiftHistoryList: React.FC<Props> = ({ userId }) => {
  const [lifts, setLifts] = useState<LiftRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  const fetchPage = async (offset: number) => {
    setLoading(true);
    try {
      const res = await axios.get(
        `${API_URL}/users/${userId}/lifts?limit=${PAGE}&offset=${offset}`
      );
      setLifts((prev) => (offset === 0 ? res.data.lifts : [...prev, ...res.data.lifts]));
      setTotal(res.data.total ?? 0);
    } catch {
      if (offset === 0) setFailed(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLifts([]);
    setFailed(false);
    fetchPage(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  if (failed || (total === 0 && lifts.length === 0)) return null;

  return (
    <div className="bg-card rounded-xl p-6 shadow-sm mb-6">
      <h2 className="text-xl font-semibold mb-4">
        My lifts <span className="text-sm font-normal text-muted-foreground">({total})</span>
      </h2>
      <div className="flex flex-col gap-2">
        {lifts.map((row) => (
          <Link
            key={row.attempt_id}
            to={`/challenges/${row.competition_id}/participants/${userId}/video/${row.attempt_id}`}
            className="group flex items-center gap-3 glass rounded-xl px-4 py-3 hover:bg-secondary/40 transition-colors"
          >
            <span className="text-xs text-muted-foreground w-12 shrink-0 tabular-nums">
              {fmtDate(row.created_at)}
            </span>
            <span className="flex-1 min-w-0 truncate font-medium">
              {row.lift_type ? cap(row.lift_type.replace(/_/g, " ")) : "Lift"}
              {row.lift_type !== "plank" && row.weight != null && row.weight > 0 && (
                <span className="text-muted-foreground font-normal"> · {row.weight}kg</span>
              )}
            </span>
            <Payoff row={row} />
            <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
          </Link>
        ))}
      </div>
      {lifts.length < total && (
        <div className="text-center mt-4">
          <button
            onClick={() => fetchPage(lifts.length)}
            disabled={loading}
            className="px-4 py-2 text-sm rounded-md bg-secondary/50 text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
          >
            {loading ? "Loading…" : "Load more"}
          </button>
        </div>
      )}
    </div>
  );
};

export default LiftHistoryList;
