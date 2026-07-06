import React, { useEffect, useState } from "react";
import { Dumbbell, Upload, Trophy, Flame, Timer } from "lucide-react";
import HubPage from "../components/HubPage";
import { getCompetitions } from "../lib/api";

const LiftHub: React.FC = () => {
  const localUserId = localStorage.getItem("userId");
  const [plank, setPlank] = useState<{ id: string; title: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCompetitions()
      .then((comps) => {
        if (cancelled) return;
        const p = comps.find(
          (c) => c.status === "ongoing" && (c.categories || []).includes("Plank")
        );
        setPlank(p ? { id: p.id, title: p.title } : null);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <HubPage
      title="Lift"
      subtitle="Upload a lifting video and get AI-graded, annotated feedback on every rep."
      icon={<Dumbbell className="w-8 h-8" />}
      primary={{
        to: "/lift/upload",
        label: "Upload a lift",
        description: "Squat, bench, deadlift, curl — get per-rep grades in minutes.",
        icon: <Upload className="w-7 h-7" />,
      }}
      secondary={[
        ...(plank
          ? [
              {
                to: `/challenges/${plank.id}`,
                label: "Plank challenge",
                description: "Record your plank — straight to the board.",
                icon: <Timer className="w-5 h-5" />,
              },
            ]
          : []),
        {
          to: "/leaderboard",
          label: "Leaderboard",
          description: "Top lifts this month.",
          icon: <Trophy className="w-5 h-5" />,
        },
        {
          to: "/challenges",
          label: "Challenges",
          description: "Join a lifting competition.",
          icon: <Flame className="w-5 h-5" />,
        },
        ...(localUserId
          ? [
              {
                to: `/profile/${localUserId}`,
                label: "My lifts",
                description: "Your uploads and grades.",
                icon: <Dumbbell className="w-5 h-5" />,
              },
            ]
          : []),
      ]}
    />
  );
};

export default LiftHub;
