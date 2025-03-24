
import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { getCompetitionById, getLiftsByParticipantId, sampleLifts } from "../lib/data";
import Layout from "../components/Layout";
import VideoPlayerComponent from "../components/VideoPlayer";
import { ArrowLeft } from "lucide-react";

const VideoPlayerPage = () => {
  const { competitionId, participantId, liftId } = useParams<{
    competitionId: string;
    participantId: string;
    liftId?: string;
  }>();
  
  const navigate = useNavigate();
  const competition = getCompetitionById(competitionId || "");
  const participant = competition?.participants.find(p => p.id === participantId);
  
  // Get all lifts for this participant or use the sampleLifts if none exist
  const lifts = getLiftsByParticipantId(participantId || "") || sampleLifts;
  
  // If liftId is provided, find that specific lift, otherwise use the first lift
  const currentLift = liftId 
    ? lifts.find(lift => lift.id === liftId) 
    : lifts[0];

  if (!competition || !participant || !currentLift) {
    return (
      <Layout>
        <div className="min-h-[60vh] flex flex-col items-center justify-center">
          <h2 className="text-2xl font-semibold mb-4">Content Not Found</h2>
          <p className="text-muted-foreground mb-6">
            The requested content doesn't exist or has been removed.
          </p>
          <button
            onClick={() => navigate("/")}
            className="flex items-center px-4 py-2 rounded-md bg-accent text-white hover:bg-accent/90 transition-colors"
          >
            <ArrowLeft size={16} className="mr-2" /> Return to Home
          </button>
        </div>
      </Layout>
    );
  }

  const formatLiftType = (type: string) => {
    return type.charAt(0).toUpperCase() + type.slice(1);
  };

  return (
    <Layout>
      <div className="mb-6 flex items-center">
        <button
          onClick={() => navigate(`/competitions/${competitionId}`)}
          className="mr-4 flex items-center text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={16} className="mr-1" /> Back to Competition
        </button>
        <h1 className="text-2xl font-semibold">Lift Video</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="lg:col-span-2"
        >
          <div className="glass rounded-xl overflow-hidden mb-6">
            <VideoPlayerComponent
              videoUrl={currentLift.videoUrl}
              title={`${participant.name} - ${formatLiftType(currentLift.type)} (${currentLift.weight}kg)`}
            />
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass p-6 rounded-xl"
          >
            <h2 className="text-xl font-semibold mb-4">
              {formatLiftType(currentLift.type)} - {currentLift.weight}kg
              <span className={`ml-3 inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded-full ${
                currentLift.success 
                  ? "bg-green-100 text-green-800" 
                  : "bg-red-100 text-red-800"
              }`}>
                {currentLift.success ? "Good Lift" : "No Lift"}
              </span>
            </h2>
            
            <div className="flex items-center mb-6">
              <img
                src={participant.avatar}
                alt={participant.name}
                className="w-10 h-10 rounded-full mr-3"
              />
              <div>
                <h3 className="font-medium">{participant.name}</h3>
                <div className="text-sm text-muted-foreground">
                  {participant.weightClass} | {participant.country}
                </div>
              </div>
            </div>
            
            <div className="border-t border-border/50 pt-4">
              <h3 className="font-medium mb-2">About This Lift</h3>
              <p className="text-muted-foreground">
                {`This is a ${formatLiftType(currentLift.type)} attempt at ${currentLift.weight}kg by ${participant.name} 
                during the ${competition.title}. The lift was ${currentLift.success ? 'successful' : 'unsuccessful'}.`}
              </p>
            </div>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="glass p-6 rounded-xl sticky top-20">
            <h2 className="text-xl font-semibold mb-4">All Lifts</h2>
            <div className="space-y-3">
              {lifts.map((lift, index) => (
                <motion.div
                  key={lift.id}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.05 * index }}
                >
                  <button
                    onClick={() => navigate(`/competitions/${competitionId}/participants/${participantId}/video/${lift.id}`)}
                    className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                      currentLift.id === lift.id
                        ? "bg-accent/10 border border-accent/30"
                        : "hover:bg-secondary/70"
                    }`}
                  >
                    <div className="flex items-center">
                      <div className={`w-2 h-2 rounded-full mr-3 ${
                        lift.success ? "bg-green-500" : "bg-red-500"
                      }`}></div>
                      <div className="text-left">
                        <div className="font-medium">
                          {formatLiftType(lift.type)} ({lift.weight}kg)
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {new Date(lift.timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                    </div>
                    <div className={`text-xs font-medium ${
                      lift.success ? "text-green-600" : "text-red-600"
                    }`}>
                      {lift.success ? "Good Lift" : "No Lift"}
                    </div>
                  </button>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </Layout>
  );
};

export default VideoPlayerPage;
