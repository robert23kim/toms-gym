import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Dumbbell, Target, Flag } from "lucide-react";
import Layout from "../components/Layout";

interface ChooserOption {
  to: string;
  label: string;
  description: string;
  icon: React.ReactNode;
}

/**
 * Unified upload entry (T7). Asks "What are you analyzing?" and routes to
 * one of the three existing, separate upload flows. Pure IA glue — the
 * flows stay independent underneath.
 */
const OPTIONS: ChooserOption[] = [
  {
    to: "/lift/upload",
    label: "Lift",
    description: "Upload a lifting video for AI-graded, annotated per-rep feedback.",
    icon: <Dumbbell className="w-7 h-7" />,
  },
  {
    to: "/bowling/upload",
    label: "Bowl",
    description: "Upload a bowling video to track ball trajectory, entry board, and pocket.",
    icon: <Target className="w-7 h-7" />,
  },
  {
    to: "/golf/upload",
    label: "Golf",
    description: "Snap a scorecard photo to score your round and update your handicap.",
    icon: <Flag className="w-7 h-7" />,
  },
];

const UploadChooser: React.FC = () => {
  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-2xl mx-auto"
      >
        <h1 className="text-3xl font-semibold mb-2">What are you analyzing?</h1>
        <p className="text-muted-foreground mb-8">
          Pick a sport to start — each upload gives you analysis you can't get anywhere else.
        </p>

        <div className="flex flex-col gap-4">
          {OPTIONS.map((opt) => (
            <Link
              key={opt.to}
              to={opt.to}
              className="group flex items-center justify-between w-full p-6 rounded-2xl glass hover:bg-secondary/40 transition-colors"
            >
              <div className="flex items-center gap-4">
                <span className="text-accent">{opt.icon}</span>
                <div>
                  <p className="text-lg font-semibold">{opt.label}</p>
                  <p className="text-sm text-muted-foreground">{opt.description}</p>
                </div>
              </div>
              <ArrowRight className="w-6 h-6 text-accent transition-transform group-hover:translate-x-1" />
            </Link>
          ))}
        </div>
      </motion.div>
    </Layout>
  );
};

export default UploadChooser;
