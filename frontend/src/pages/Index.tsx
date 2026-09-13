import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Dumbbell, Target, Flag } from "lucide-react";
import Layout from "../components/Layout";
import IconTile from "../components/IconTile";
import DemoLoop from "../components/DemoLoop";
import StreakCard from "../components/StreakCard";
import PromptList from "../components/home/PromptList";
import { buildPrompts } from "../lib/prompts";
import { getCompetitions } from "../lib/api";
import { Competition } from "../lib/types";

const VERTICALS = [
  {
    to: "/lift",
    icon: <Dumbbell className="w-5 h-5" />,
    title: "Lift",
    description: "Per-rep grades on squat, bench, deadlift & curls.",
  },
  {
    to: "/bowl",
    icon: <Target className="w-5 h-5" />,
    title: "Bowl",
    description: "Ball trajectory, entry board & pocket impact.",
  },
  {
    to: "/golf",
    icon: <Flag className="w-5 h-5" />,
    title: "Golf",
    description: "Snap a scorecard, get your handicap.",
  },
];

const readUserId = (): string | null => {
  try {
    return localStorage.getItem("userId");
  } catch {
    return null;
  }
};

const Index = () => {
  const [open, setOpen] = useState<Competition[]>([]);
  const userId = readUserId();
  const returning = Boolean(userId);

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

  const verticals = (
    <section aria-label="Verticals" className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
      {VERTICALS.map((v) => (
        <IconTile key={v.to} {...v} />
      ))}
    </section>
  );

  const todo = <PromptList prompts={buildPrompts(open)} userId={userId} />;

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="max-w-2xl mx-auto text-center flex flex-col gap-14 py-10 md:py-10 max-md:pt-4"
      >
        {!returning && (
          <section aria-label="Pitch">
            <h1 className="text-3xl md:text-4xl font-bold leading-tight mb-3 text-balance">
              AI analysis of your lift, bowl, or round — in minutes.
            </h1>
            <p className="text-muted-foreground max-w-md mx-auto">
              Upload a video or snap a photo and get annotated feedback. No signup — just your email.
            </p>
          </section>
        )}

        {returning && todo}

        <section aria-label="Your streak">
          <StreakCard />
        </section>

        {!returning && (
          <>
            <section aria-label="Analysis demo">
              <DemoLoop />
            </section>
            {verticals}
            {todo}
          </>
        )}
      </motion.div>
    </Layout>
  );
};

export default Index;
