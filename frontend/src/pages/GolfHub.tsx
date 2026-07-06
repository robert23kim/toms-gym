import React from "react";
import { Flag, Camera, Trophy, User } from "lucide-react";
import HubPage from "../components/HubPage";

const GolfHub: React.FC = () => {
  const localUserId = localStorage.getItem("userId");

  return (
    <HubPage
      title="Golf"
      subtitle="Snap a photo of your scorecard — we read the scores and compute your handicap."
      icon={<Flag className="w-8 h-8" />}
      primary={{
        to: "/golf/upload",
        label: "Upload a scorecard",
        description: "Photo-only — no typing. Get an instant handicap differential.",
        icon: <Camera className="w-7 h-7" />,
      }}
      secondary={[
        {
          to: "/golf/leaderboard",
          label: "Leaderboard",
          description: "Handicap rankings.",
          icon: <Trophy className="w-5 h-5" />,
        },
        {
          to: localUserId ? `/golf/profile/${localUserId}` : "/golf/profile",
          label: "My rounds",
          description: "Your rounds and handicap trend.",
          icon: <User className="w-5 h-5" />,
        },
      ]}
    />
  );
};

export default GolfHub;
