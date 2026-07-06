import React from "react";
import { Dumbbell, Upload, Trophy, Flame } from "lucide-react";
import HubPage from "../components/HubPage";

const LiftHub: React.FC = () => {
  const localUserId = localStorage.getItem("userId");

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
