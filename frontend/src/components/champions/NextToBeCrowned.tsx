import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getChallengeLeaderboard, getCompetitions, formatChampionScore } from "../../lib/api";
import { ChallengeMetric } from "../../lib/types";

interface LiveRace {
  id: string;
  title: string;
  daysLeft: number;
  leader: { name: string; score: number; metric: ChallengeMetric } | null;
}

const daysUntil = (iso: string): number =>
  Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000));

/** Ongoing challenges with their current leader — the throne is still up for grabs. */
const NextToBeCrowned: React.FC = () => {
  const [races, setRaces] = useState<LiveRace[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const comps = (await getCompetitions()).filter((c) => c.status === "ongoing");
        const rows = await Promise.all(
          comps.map(async (c): Promise<LiveRace> => {
            let leader: LiveRace["leader"] = null;
            try {
              const lb = await getChallengeLeaderboard(c.id);
              const top = lb.rows.find((r) => r.rank === 1 && r.score > 0);
              if (top) leader = { name: top.name || "Anonymous", score: top.score, metric: lb.metric };
            } catch {
              // leader simply stays unknown
            }
            return { id: c.id, title: c.title, daysLeft: daysUntil(c.registrationDeadline), leader };
          })
        );
        if (!cancelled) setRaces(rows);
      } catch {
        // strip stays hidden
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!races.length) return null;

  return (
    <section aria-label="Next to be crowned">
      <div className="mb-3 flex items-center gap-3.5 text-xs uppercase tracking-widest text-muted-foreground">
        <span className="h-px flex-1 bg-border" aria-hidden="true" />
        Next to be crowned
        <span className="h-px flex-1 bg-border" aria-hidden="true" />
      </div>
      <div className="flex flex-col gap-2">
        {races.map((r) => (
          <Link
            key={r.id}
            to={`/challenges/${r.id}`}
            className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 transition-colors hover:border-amber-500/40"
          >
            <span className="text-xl" aria-hidden="true">⏳</span>
            <div className="min-w-0 flex-1 text-left">
              <div className="truncate font-medium">{r.title}</div>
              <div className="text-sm text-muted-foreground">
                {r.leader
                  ? `${r.leader.name} leads at ${formatChampionScore(r.leader.metric, r.leader.score)}`
                  : "No entries yet — the throne is empty"}
                {" · "}
                {r.daysLeft === 0 ? "ends today" : `${r.daysLeft} day${r.daysLeft === 1 ? "" : "s"} left`}
              </div>
            </div>
            <span className="shrink-0 text-sm text-muted-foreground">Compete →</span>
          </Link>
        ))}
      </div>
    </section>
  );
};

export default NextToBeCrowned;
