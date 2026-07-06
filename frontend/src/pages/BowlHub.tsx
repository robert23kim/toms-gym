import React from "react";
import { CircleDot, Upload, Trophy } from "lucide-react";
import HubPage from "../components/HubPage";

const BowlHub: React.FC = () => {
  return (
    <HubPage
      title="Bowl"
      subtitle="Upload a bowling video to track ball trajectory, lane edges, and entry board."
      icon={<CircleDot className="w-8 h-8" />}
      primary={{
        to: "/bowling/upload",
        label: "Upload a bowling video",
        description: "See your ball path, hook shape, and pocket entry.",
        icon: <Upload className="w-7 h-7" />,
      }}
      secondary={[
        {
          to: "/challenges",
          label: "Challenges",
          description: "Join a bowling competition.",
          icon: <Trophy className="w-5 h-5" />,
        },
      ]}
    />
  );
};

export default BowlHub;
