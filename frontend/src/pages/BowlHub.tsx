import React from "react";
import { CircleDot, Camera, Video, LineChart, Trophy } from "lucide-react";
import HubPage from "../components/HubPage";

const BowlHub: React.FC = () => {
  return (
    <HubPage
      title="Bowl"
      subtitle="Photograph the score screen to bank every game, or upload a video to see your ball path."
      icon={<CircleDot className="w-8 h-8" />}
      primary={{
        to: "/bowling/snap",
        label: "Snap a score sheet",
        description: "Every game read straight off the photo.",
        icon: <Camera className="w-7 h-7" />,
      }}
      secondary={[
        {
          to: "/bowling/upload",
          label: "Analyze a video",
          icon: <Video className="w-5 h-5" />,
        },
        {
          to: "/bowling/insights/me",
          label: "My insights",
          icon: <LineChart className="w-5 h-5" />,
        },
        {
          to: "/challenges",
          label: "Challenges",
          icon: <Trophy className="w-5 h-5" />,
        },
      ]}
    />
  );
};

export default BowlHub;
