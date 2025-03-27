import React from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Play, Pause, Volume2, VolumeX, Maximize2, BarChart2, Activity, Target, Award } from "lucide-react";

const VideoPlayer: React.FC = () => {
  const { challengeId, participantId, liftId } = useParams<{
    challengeId: string;
    participantId: string;
    liftId: string;
  }>();

  // Mock video data
  const mockVideo = {
    id: liftId,
    title: "Squat Attempt - 225kg",
    participant: "John Smith",
    weight: "225kg",
    timestamp: "2024-03-20T10:30:00Z",
    videoUrl: "https://example.com/video1",
    status: "success",
    notes: "Good depth, proper form maintained throughout the lift.",
    analytics: {
      depth: "95%",
      speed: "0.8s",
      form: "92%",
      power: "85%",
      stability: "88%",
      previousAttempts: [
        { weight: "220kg", status: "success", date: "2024-03-19" },
        { weight: "215kg", status: "success", date: "2024-03-18" },
        { weight: "210kg", status: "success", date: "2024-03-17" }
      ]
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
    >
      <div className="max-w-7xl mx-auto">
        <Link
          to={`/challenges/${challengeId}`}
          className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
        >
          <ArrowLeft className="mr-2" size={16} />
          Back to Challenge
        </Link>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Player */}
          <div className="lg:col-span-2">
            <div className="bg-card rounded-lg shadow-lg overflow-hidden">
              <div className="relative aspect-video bg-black">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <div className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Play className="w-8 h-8 text-white" />
                    </div>
                    <p className="text-white/80">Video Player Placeholder</p>
                  </div>
                </div>
                {/* Video Controls */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <button className="text-white hover:text-white/80">
                        <Play className="w-6 h-6" />
                      </button>
                      <div className="flex items-center gap-2">
                        <button className="text-white hover:text-white/80">
                          <Volume2 className="w-5 h-5" />
                        </button>
                        <div className="w-24 h-1 bg-white/20 rounded-full">
                          <div className="w-1/2 h-full bg-white rounded-full"></div>
                        </div>
                      </div>
                    </div>
                    <button className="text-white hover:text-white/80">
                      <Maximize2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Video Info */}
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h1 className="text-2xl font-bold">{mockVideo.title}</h1>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    mockVideo.status === "success" ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
                  }`}>
                    {mockVideo.status === "success" ? "Successful" : "Failed"}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                  <div>
                    <p className="text-sm text-muted-foreground">Athlete</p>
                    <p className="font-medium">{mockVideo.participant}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Weight</p>
                    <p className="font-medium">{mockVideo.weight}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Date</p>
                    <p className="font-medium">{new Date(mockVideo.timestamp).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Status</p>
                    <p className="font-medium capitalize">{mockVideo.status}</p>
                  </div>
                </div>

                <div>
                  <h2 className="text-lg font-semibold mb-2">Notes</h2>
                  <p className="text-muted-foreground">{mockVideo.notes}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Analytics Panel */}
          <div className="lg:col-span-1">
            <div className="bg-card rounded-lg shadow-lg overflow-hidden">
              <div className="p-6">
                <div className="flex items-center gap-2 mb-6">
                  <BarChart2 className="text-primary" size={24} />
                  <h2 className="text-xl font-semibold">Lift Analytics</h2>
                </div>

                <div className="space-y-6">
                  {/* Performance Metrics */}
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-3">Performance Metrics</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-secondary/5 p-4 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <Activity className="w-4 h-4 text-primary" />
                          <span className="text-sm font-medium">Depth</span>
                        </div>
                        <div className="text-2xl font-bold">{mockVideo.analytics.depth}</div>
                      </div>
                      <div className="bg-secondary/5 p-4 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <Target className="w-4 h-4 text-primary" />
                          <span className="text-sm font-medium">Speed</span>
                        </div>
                        <div className="text-2xl font-bold">{mockVideo.analytics.speed}</div>
                      </div>
                      <div className="bg-secondary/5 p-4 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <Award className="w-4 h-4 text-primary" />
                          <span className="text-sm font-medium">Form</span>
                        </div>
                        <div className="text-2xl font-bold">{mockVideo.analytics.form}</div>
                      </div>
                      <div className="bg-secondary/5 p-4 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <BarChart2 className="w-4 h-4 text-primary" />
                          <span className="text-sm font-medium">Power</span>
                        </div>
                        <div className="text-2xl font-bold">{mockVideo.analytics.power}</div>
                      </div>
                    </div>
                  </div>

                  {/* Previous Attempts */}
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-3">Previous Attempts</h3>
                    <div className="space-y-2">
                      {mockVideo.analytics.previousAttempts.map((attempt, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 bg-secondary/5 rounded-lg"
                        >
                          <div>
                            <div className="font-medium">{attempt.weight}</div>
                            <div className="text-sm text-muted-foreground">
                              {new Date(attempt.date).toLocaleDateString()}
                            </div>
                          </div>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            attempt.status === "success" ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
                          }`}>
                            {attempt.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default VideoPlayer;
