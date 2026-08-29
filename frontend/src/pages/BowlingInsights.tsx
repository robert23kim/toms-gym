import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Camera } from "lucide-react";
import Layout from "../components/Layout";
import { formatDay } from "../lib/dates";
import InsightTiles, { InsightTile } from "../components/bowling/InsightTiles";
import NightCard from "../components/bowling/NightCard";
import { Night, summarizeNight } from "../lib/bowlingNight";
import {
  BowlingGameRow,
  BowlingInsights as BowlingInsightsPayload,
  fetchBowlingInsights,
  fetchBowlingGames,
} from "../lib/api";

type Payload = BowlingInsightsPayload & { recent: BowlingGameRow[] };

const pct = (value: number): string => `${Math.round(value * 100)}%`;

const oneDp = (value: number): string => value.toFixed(1);

const SLOTS: ("1" | "2" | "3")[] = ["1", "2", "3"];

const headlineTiles = (data: Payload): InsightTile[] => {
  const delta = data.trend.delta;
  const tiles: InsightTile[] = [
    { key: "average", label: "Average", value: oneDp(data.average) },
    { key: "high", label: "High game", value: String(data.high) },
    { key: "games", label: "Games", value: String(data.games) },
  ];
  if (delta !== null) {
    tiles.push({
      key: "trend",
      label: "Last 5 vs before",
      // Bowling is higher-is-better, so a positive delta is the green one.
      value: `${delta >= 0 ? "▲" : "▼"} ${oneDp(Math.abs(delta))}`,
      tone: delta === 0 ? "neutral" : delta > 0 ? "up" : "down",
    });
  }
  return tiles;
};

const frameTiles = (data: Payload): InsightTile[] => {
  const stats = data.frame_stats;
  if (!stats) return [];
  return [
    { key: "strike_pct", label: "Strikes", value: pct(stats.strike_pct) },
    { key: "spare_pct", label: "Spares", value: pct(stats.spare_pct) },
    { key: "open_pct", label: "Open frames", value: pct(stats.open_pct) },
    { key: "first_ball_avg", label: "First ball", value: oneDp(stats.first_ball_avg) },
  ];
};

const strikeShade = (value: number): string => {
  if (value >= 0.6) return "bg-accent text-accent-foreground";
  if (value >= 0.35) return "bg-accent/60";
  if (value >= 0.15) return "bg-accent/30";
  return "bg-secondary";
};

const BowlingInsights: React.FC = () => {
  const { userId: userIdParam } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const sheetId = searchParams.get("sheet");
  const [night, setNight] = useState<Night | null>(null);

  const resolvedUserId =
    userIdParam === "me" ? localStorage.getItem("userId") : userIdParam ?? null;

  useEffect(() => {
    if (!resolvedUserId) {
      navigate("/find-profile");
      return;
    }
    let cancelled = false;
    fetchBowlingInsights(resolvedUserId)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load your bowling insights.");
      });
    return () => {
      cancelled = true;
    };
  }, [resolvedUserId, navigate]);

  useEffect(() => {
    if (!sheetId || !resolvedUserId) return;
    let cancelled = false;
    fetchBowlingGames(resolvedUserId, 100)
      .then((r) => { if (!cancelled) setNight(summarizeNight(r.games, sheetId)); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [sheetId, resolvedUserId]);

  const slotMax = data
    ? Math.max(...SLOTS.map((slot) => data.slot_averages[slot] ?? 0), 1)
    : 1;

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl mx-auto py-6 px-4"
      >
        <Link
          to="/bowl"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-6"
        >
          <ArrowLeft className="mr-2" size={16} />
          Back to Bowl
        </Link>

        <h1 className="text-3xl font-semibold text-center mb-1">Your bowling</h1>
        <p className="text-sm text-muted-foreground text-center mb-8">
          What the score sheets say you should work on.
        </p>

        {error && <p className="text-center text-muted-foreground">{error}</p>}

        {data && data.games === 0 && (
          <div className="glass rounded-2xl p-8 text-center space-y-4">
            <p className="text-muted-foreground">
              No games banked yet. Photograph the screen at the end of the night and
              every game lands here.
            </p>
            <Link
              to="/bowling/snap"
              className="inline-flex items-center gap-2 h-11 px-5 rounded-lg bg-accent text-accent-foreground text-sm font-medium hover:bg-accent/90"
            >
              <Camera className="w-4 h-4" />
              Snap a score sheet
            </Link>
          </div>
        )}

        {data && data.games > 0 && (
          <div className="space-y-8">
            {night && <NightCard night={night} />}
            <InsightTiles
              tiles={
                night && night.priorAvg == null
                  ? headlineTiles(data).filter((t) => t.key !== "average" && t.key !== "high")
                  : headlineTiles(data)
              }
            />

            {data.tips.length > 0 && (
              <section className="space-y-2.5">
                <h2 className="text-sm font-semibold text-muted-foreground">Work on this</h2>
                {data.tips.map((tip) => (
                  <div key={tip.key} className="glass rounded-xl px-4 py-3.5">
                    <div className="flex items-baseline justify-between gap-3">
                      <p className="font-medium">{tip.title}</p>
                      {tip.stat && (
                        <span className="shrink-0 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-accent/10 text-accent">
                          {tip.stat}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{tip.body}</p>
                  </div>
                ))}
              </section>
            )}

            <section className="space-y-2.5">
              <h2 className="text-sm font-semibold text-muted-foreground">
                Average by game of the night
              </h2>
              <div className="glass rounded-xl px-4 py-4 space-y-2.5">
                {SLOTS.map((slot) => {
                  const value = data.slot_averages[slot];
                  return (
                    <div key={slot} className="flex items-center gap-3">
                      <span className="w-14 shrink-0 text-xs text-muted-foreground">
                        Game {slot}
                      </span>
                      <div className="flex-1 h-2.5 rounded-full bg-secondary overflow-hidden">
                        <div
                          className="h-full rounded-full bg-accent"
                          style={{ width: `${((value ?? 0) / slotMax) * 100}%` }}
                        />
                      </div>
                      <span
                        data-testid={`slot-${slot}`}
                        className="w-12 shrink-0 text-right text-sm font-medium tabular-nums"
                      >
                        {value === null ? "—" : Math.round(value)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>

            {data.frame_stats && (
              <section className="space-y-2.5">
                <h2 className="text-sm font-semibold text-muted-foreground">
                  Frame by frame ({data.frame_stats.frames_analyzed} frames read)
                </h2>
                <InsightTiles tiles={frameTiles(data)} />
                <div className="glass rounded-xl px-4 py-4">
                  <p className="text-xs text-muted-foreground mb-2">Strike rate per frame</p>
                  <div className="grid grid-cols-10 gap-1">
                    {data.frame_stats.strike_by_frame.map((value, index) => (
                      <div key={index} className="text-center">
                        <div
                          data-testid={`strike-frame-${index}`}
                          title={`Frame ${index + 1}: ${pct(value)}`}
                          className={`h-8 rounded-md grid place-items-center text-[10px] font-semibold ${strikeShade(value)}`}
                        >
                          {Math.round(value * 100)}
                        </div>
                        <span className="block text-[10px] text-muted-foreground mt-0.5">
                          {index + 1}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            )}

            {data.recent.length > 0 && (
              <section className="space-y-2.5">
                <h2 className="text-sm font-semibold text-muted-foreground">Recent games</h2>
                <div className="flex flex-col gap-2">
                  {data.recent.map((row) => (
                    <Link
                      key={row.id}
                      data-testid={`recent-game-${row.id}`}
                      to={`/bowling/scoresheet/${row.sheet_id}`}
                      className="group flex items-center gap-3 glass rounded-xl px-4 py-3 hover:bg-secondary/40 transition-colors"
                    >
                      <span className="text-sm text-muted-foreground w-24 shrink-0">
                        {formatDay(row.played_on)}
                      </span>
                      <span className="flex-1 text-sm text-muted-foreground">
                        Game {row.game_number}
                      </span>
                      <span className="text-lg font-semibold tabular-nums">
                        {row.total_score ?? "—"}
                      </span>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </motion.div>
    </Layout>
  );
};

export default BowlingInsights;
