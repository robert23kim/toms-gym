import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Dumbbell, Target, Flag, Timer } from "lucide-react";
import Layout from "../components/Layout";
import IconTile from "../components/IconTile";
import RowCard from "../components/RowCard";
import DemoLoop from "../components/DemoLoop";
import { getCompetitions } from "../lib/api";
import { Competition } from "../lib/types";

// The three analysis verticals — each tile IS the upload entry point.
const VERTICALS = [
  {
    to: "/lift/upload",
    icon: <Dumbbell className="w-5 h-5" />,
    title: "Lift",
    description: "Per-rep grades on squat, bench, deadlift & curls.",
  },
  {
    to: "/bowling/upload",
    icon: <Target className="w-5 h-5" />,
    title: "Bowl",
    description: "Ball trajectory, entry board & pocket impact.",
  },
  {
    to: "/golf/snap",
    icon: <Flag className="w-5 h-5" />,
    title: "Golf",
    description: "Snap a scorecard, get your handicap.",
  },
];

const Index = () => {
  const [open, setOpen] = useState<Competition[]>([]);

  useEffect(() => {
    let cancelled = false;
    getCompetitions()
      .then((comps) => {
        if (cancelled) return;
        setOpen(comps.filter((c) => c.status === "ongoing"));
      })
      .catch(() => {}); // non-fatal: strip simply stays hidden
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="max-w-2xl mx-auto text-center flex flex-col gap-14 py-10"
      >
        {/* Hero */}
        <section>
          <h1 className="text-3xl md:text-4xl font-bold leading-tight mb-3 text-balance">
            AI analysis of your lift, bowl, or round — in minutes.
          </h1>
          <p className="text-muted-foreground max-w-md mx-auto">
            Upload a video or snap a photo and get annotated feedback. No signup — just your email.
          </p>
        </section>

        {/* Animated demo of what the analysis produces */}
        <section aria-label="Analysis demo">
          <DemoLoop />
        </section>

        {/* The three verticals */}
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {VERTICALS.map((v) => (
            <IconTile key={v.to} {...v} />
          ))}
        </section>

        {/* Open challenges — hidden entirely when nothing is ongoing */}
        <section className="flex flex-col gap-2.5">
          {open.length > 0 && (
            <>
              <div className="flex items-center gap-3.5 text-xs uppercase tracking-widest text-muted-foreground mb-1">
                <span className="flex-1 h-px bg-border" aria-hidden="true" />
                Open challenges
                <span className="flex-1 h-px bg-border" aria-hidden="true" />
              </div>
              {open.map((c) => (
                <RowCard
                  key={c.id}
                  to={`/challenges/${c.id}`}
                  icon={<Timer className="w-[18px] h-[18px]" />}
                  title={c.title}
                  pill={c.categories?.[0]}
                />
              ))}
            </>
          )}
          <Link
            to="/challenges"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors mt-1"
          >
            All challenges →
          </Link>
        </section>
      </motion.div>
    </Layout>
  );
};

export default Index;
