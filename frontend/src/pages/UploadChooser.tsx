import React from "react";
import { motion } from "framer-motion";
import { Dumbbell, Target, Flag } from "lucide-react";
import Layout from "../components/Layout";
import IconTile from "../components/IconTile";

/**
 * Unified upload entry (T7). Asks "What are you analyzing?" and routes to
 * one of the three existing, separate upload flows — same tiles as home.
 */
const OPTIONS = [
  {
    to: "/lift/upload",
    title: "Lift",
    description: "Per-rep grades on squat, bench, deadlift & curls.",
    icon: <Dumbbell className="w-5 h-5" />,
  },
  {
    to: "/bowling/upload",
    title: "Bowl",
    description: "Ball trajectory, entry board & pocket impact.",
    icon: <Target className="w-5 h-5" />,
  },
  {
    to: "/golf/snap",
    title: "Golf",
    description: "Snap a scorecard, get your handicap.",
    icon: <Flag className="w-5 h-5" />,
  },
];

const UploadChooser: React.FC = () => {
  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-2xl mx-auto text-center py-10"
      >
        <h1 className="text-3xl font-semibold mb-2">What are you analyzing?</h1>
        <p className="text-muted-foreground mb-8">
          Pick a sport to start — each upload gives you analysis you can't get anywhere else.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {OPTIONS.map((opt) => (
            <IconTile key={opt.to} {...opt} />
          ))}
        </div>
      </motion.div>
    </Layout>
  );
};

export default UploadChooser;
