import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import ChampionHero from "../components/champions/ChampionHero";
import ChampionCard from "../components/champions/ChampionCard";
import NextToBeCrowned from "../components/champions/NextToBeCrowned";
import ChampionConfetti from "../components/profile/ChampionConfetti";
import { Champion, fetchChampions, getGolfAvatar } from "../lib/api";
import { championTally, dynastyLabel, groupByYear, ordinalWin } from "../lib/championStats";

const HallOfChampions: React.FC = () => {
  const viewerId = localStorage.getItem("userId");
  const [champions, setChampions] = useState<Champion[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchChampions()
      .then((c) => !cancelled && setChampions(c))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const reigning = champions?.[0] ?? null;
  const tally = champions ? championTally(champions) : [];
  const winsFor = (userId: string) => tally.find((t) => t.user_id === userId)?.wins ?? 1;
  const viewerWins = viewerId ? tally.find((t) => t.user_id === viewerId) : undefined;

  return (
    <Layout>
      <div className="mx-auto max-w-3xl px-4 py-10 space-y-10 text-center">
        <header>
          <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Lift</div>
          <h1 className="mt-2 text-4xl font-black tracking-tight">Hall of Champions</h1>
          <p className="mt-3 text-muted-foreground">
            Every challenge crowns one winner. This is where they live forever.
          </p>
        </header>

        {viewerWins && (
          <ChampionConfetti competitionId="hall" userId={viewerWins.user_id} />
        )}

        {failed && (
          <p className="text-sm text-muted-foreground">Couldn't load the hall right now. Try again in a moment.</p>
        )}
        {champions && !champions.length && (
          <div className="rounded-2xl border border-dashed border-border px-6 py-12">
            <div className="text-4xl" aria-hidden="true">👑</div>
            <p className="mt-3 font-medium">The throne is empty.</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Win a challenge and your name goes here first.
            </p>
            <Link to="/challenges" className="mt-4 inline-block text-sm underline">
              See open challenges →
            </Link>
          </div>
        )}

        {reigning && (
          <ChampionHero
            champion={reigning}
            wins={winsFor(reigning.user_id)}
            isViewer={reigning.user_id === viewerId}
          />
        )}

        {tally.some((t) => t.wins > 1) && (
          <section aria-label="Dynasties">
            <div className="mb-3 flex items-center gap-3.5 text-xs uppercase tracking-widest text-muted-foreground">
              <span className="h-px flex-1 bg-border" aria-hidden="true" />
              Dynasties
              <span className="h-px flex-1 bg-border" aria-hidden="true" />
            </div>
            <div className="flex flex-wrap justify-center gap-3">
              {tally
                .filter((t) => t.wins > 1)
                .map((t) => (
                  <Link
                    key={t.user_id}
                    to={`/profile/${t.user_id}`}
                    className="flex items-center gap-3 rounded-full border border-amber-500/40 bg-amber-500/5 py-1.5 pl-1.5 pr-4 transition-colors hover:bg-amber-500/10"
                  >
                    <img
                      src={getGolfAvatar(t.name, t.user_id)}
                      alt=""
                      className="h-9 w-9 rounded-full bg-secondary object-cover"
                    />
                    <span className="text-left">
                      <span className="block text-sm font-semibold">{t.name}</span>
                      <span className="block text-xs text-amber-700 dark:text-amber-300">
                        🔥 {dynastyLabel(t.wins)}
                      </span>
                    </span>
                  </Link>
                ))}
            </div>
          </section>
        )}

        {champions && champions.length > 0 && (
          <section aria-label="Wall of fame" className="space-y-6">
            {groupByYear(champions).map(([year, list]) => (
              <div key={year}>
                <div className="mb-3 flex items-center gap-3.5 text-xs uppercase tracking-widest text-muted-foreground">
                  <span className="h-px flex-1 bg-border" aria-hidden="true" />
                  {year}
                  <span className="h-px flex-1 bg-border" aria-hidden="true" />
                </div>
                <div className="flex flex-col gap-2.5">
                  {list.map((c) => (
                    <ChampionCard
                      key={c.competition_id}
                      champion={c}
                      winNumber={ordinalWin(champions, c)}
                      isViewer={c.user_id === viewerId}
                    />
                  ))}
                </div>
              </div>
            ))}
          </section>
        )}

        <NextToBeCrowned />
      </div>
    </Layout>
  );
};

export default HallOfChampions;
