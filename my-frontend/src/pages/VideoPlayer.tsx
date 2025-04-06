import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Play, Pause, Volume2, VolumeX, Maximize2, BarChart2, Activity, Target, Award } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";

interface VideoData {
  id: number;
  participant_id: number;
  competition_id: number;
  lift_type: string;
  weight: number;
  success: string;
  video_url: string;
  timestamp: string;
  participant_name: string;
}

const VideoPlayer: React.FC = () => {
  const { id, participantId, videoId } = useParams<{ id: string; participantId: string; videoId: string }>();
  const [videoData, setVideoData] = useState<VideoData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVideoData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await axios.get(`${API_URL}/competitions/${id}/participants/${participantId}/attempts/${videoId}`);
        console.log("Video data response:", response.data);
        
        if (response.data && response.data.attempt) {
          setVideoData(response.data.attempt);
        } else {
          setError("Video data not found");
        }
      } catch (err: any) {
        console.error("Error fetching video data:", err);
        setError(err.response?.data?.error || "Failed to load video data");
      } finally {
        setLoading(false);
      }
    };

    fetchVideoData();
  }, [id, participantId, videoId]);

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500">
              {error}
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (!videoData) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="text-center">
              <h2 className="text-2xl font-bold">Video not found</h2>
              <Link to={`/challenges/${id}`} className="text-primary hover:underline mt-4 inline-block">
                Return to Challenge
              </Link>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-4xl mx-auto">
          <Link
            to={`/challenges/${id}`}
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Challenge
          </Link>

          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-6 sm:p-8">
              <div className="mb-6">
                <h1 className="text-2xl font-bold mb-2">{videoData.participant_name}'s {videoData.lift_type}</h1>
                <div className="flex items-center gap-4 text-muted-foreground">
                  <span>{videoData.weight}kg</span>
                  <span className={`px-2 py-1 rounded-full text-sm ${
                    videoData.success === 'true' ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
                  }`}>
                    {videoData.success === 'true' ? "Successful" : "Failed"}
                  </span>
                  <span>{new Date(videoData.timestamp).toLocaleString()}</span>
                </div>
              </div>

              <div className="aspect-video bg-black rounded-lg overflow-hidden">
                {videoData.video_url ? (
                  <video
                    src={videoData.video_url}
                    controls
                    className="w-full h-full"
                    autoPlay
                  >
                    Your browser does not support the video tag.
                  </video>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    No video available
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default VideoPlayer;
