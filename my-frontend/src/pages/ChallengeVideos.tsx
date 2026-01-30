import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Play } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import VideoGallery from "../components/VideoGallery";
import { API_URL } from "../config";

const COMPETITIONS_API_URL = API_URL;

interface VideoData {
  attempt_id: string;
  user_id: string;
  lift_type: string;
  weight: number;
  status: string;
  video_url: string;
  created_at: string;
  competition_id: string;
  competition_name?: string;
}

const ChallengeVideos: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [challengeName, setChallengeName] = useState<string>("");
  const [videoData, setVideoData] = useState<VideoData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Function to fetch videos - can be called to refresh after deletion
  const fetchVideos = async (showLoading = false) => {
    try {
      if (showLoading) {
        setLoading(true);
        setError(null);
      }

      // Fetch challenge details and lifts in parallel
      const [challengeResponse, liftsResponse] = await Promise.all([
        axios.get(`${COMPETITIONS_API_URL}/competitions/${id}`),
        axios.get(`${COMPETITIONS_API_URL}/competitions/${id}/lifts`)
      ]);

      const backendData = challengeResponse.data.competition;
      const liftsDataBackend = liftsResponse.data.lifts || [];

      setChallengeName(backendData.name);

      // Process video data for the gallery
      const processedVideoData: VideoData[] = liftsDataBackend
        .filter((lift: any) => lift.video_url) // Only include lifts with videos
        .map((lift: any) => ({
          attempt_id: lift.id.toString(),
          user_id: lift.participant_id,
          lift_type: lift.lift_type,
          weight: lift.weight,
          status: lift.status,
          video_url: lift.video_url,
          created_at: lift.timestamp || new Date().toISOString(),
          competition_id: id || '',
          competition_name: backendData.name
        }));

      setVideoData(processedVideoData);
    } catch (err: any) {
      console.error("Error fetching data:", err);
      if (showLoading) {
        setError(
          err.response?.data?.error ||
          err.message ||
          "Failed to load challenge videos"
        );
      }
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchVideos(true);
  }, [id]);

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

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-7xl mx-auto">
          <Link
            to={`/challenges/${id}`}
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Challenge
          </Link>

          <div className="mb-8">
            <h1 className="text-3xl font-bold mb-2">Challenge Videos</h1>
            <p className="text-muted-foreground">
              All videos uploaded to <span className="font-medium text-foreground">{challengeName}</span>
            </p>
          </div>

          {videoData.length > 0 ? (
            <VideoGallery
              videos={videoData}
              title=""
              emptyMessage="No videos uploaded yet for this challenge"
              maxVideos={100}
              showCompetitionName={false}
              onVideoDeleted={() => fetchVideos(false)}
            />
          ) : (
            <div className="bg-card p-12 rounded-lg text-center">
              <Play className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">No Videos Yet</h3>
              <p className="text-muted-foreground mb-6">
                Be the first to upload a video for this challenge!
              </p>
              <Link
                to={`/challenges/${id}/upload`}
                className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-6 py-3 rounded-lg hover:bg-primary/90 transition-colors"
              >
                Upload Video
              </Link>
            </div>
          )}
        </div>
      </motion.div>
    </Layout>
  );
};

export default ChallengeVideos;
