import React, { useEffect, useState } from "react";
import { Dumbbell, Upload, Crown, Flame, Timer } from "lucide-react";
import HubPage from "../components/HubPage";
import { getCompetitions } from "../lib/api";
import { getUserId } from "../lib/identity";

const LiftHub: React.FC = () => {
  const localUserId = getUserId();
  const [plank, setPlank] = useState<{ id: string; title: string } | null>(null);
  const [club, setClub] = useState<{ id: string; title: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCompetitions()
      .then((comps) => {
        if (cancelled) return;
        const ongoing = comps.filter((c) => c.status === "ongoing");
        const k = ongoing.find((c) => c.mode === "consistency");
        const p = ongoing.find((c) => c.mode !== "consistency" && (c.categories || []).includes("Plank"));
        setClub(k ? { id: k.id, title: k.title } : null);
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
      lead={
        club
          ? { to: `/challenges/${club.id}`, label: `${club.title} · Log this week's lifts`, icon: <Flame className="w-5 h-5" /> }
          : null
      }
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
          to: "/champions",
          label: "Hall of Champions",
          description: "Every challenge winner, crowned.",
          icon: <Crown className="w-5 h-5" />,
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
