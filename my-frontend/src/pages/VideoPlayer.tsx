import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Play, Pause, Volume2, VolumeX, Maximize2, BarChart2, Activity, Target, Award, MessageSquare, Send } from "lucide-react";
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

interface Comment {
  id: number;
  user_name: string;
  content: string;
  timestamp: string;
}

const VideoPlayer: React.FC = () => {
  const { id, participantId, videoId } = useParams<{ id: string; participantId: string; videoId: string }>();
  const [videoData, setVideoData] = useState<VideoData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [analytics, setAnalytics] = useState({
    formScore: 85,
    barSpeed: "0.5 m/s",
    rangeOfMotion: "Good",
    recommendations: [
      "Keep chest up during descent",
      "Drive through heels on ascent",
      "Maintain neutral spine throughout"
    ]
  });

  useEffect(() => {
    const fetchVideoData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        try {
          const response = await axios.get(`${API_URL}/competitions/${id}/participants/${participantId}/attempts/${videoId}`);
          console.log("Video data response:", response.data);
          
          if (response.data && response.data.attempt) {
            setVideoData(response.data.attempt);
          } else {
            // If specific video not found, get a random video
            const randomResponse = await axios.get(`${API_URL}/random_video`);
            setVideoData({
              id: 0,
              participant_id: 0,
              competition_id: 0,
              lift_type: "Random Lift",
              weight: 0,
              success: "true",
              video_url: randomResponse.data.video_url,
              timestamp: new Date().toISOString(),
              participant_name: "Random Lifter"
            });
          }
        } catch (err) {
          // If any error occurs, fall back to random video
          const randomResponse = await axios.get(`${API_URL}/random_video`);
          setVideoData({
            id: 0,
            participant_id: 0,
            competition_id: 0,
            lift_type: "Random Lift",
            weight: 0,
            success: "true",
            video_url: randomResponse.data.video_url,
            timestamp: new Date().toISOString(),
            participant_name: "Random Lifter"
          });
        }
      } catch (err: any) {
        console.error("Error fetching video data:", err);
        setError(err.response?.data?.error || "Failed to load video");
      } finally {
        setLoading(false);
      }
    };

    fetchVideoData();
  }, [id, participantId, videoId]);

  const handleCommentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    const comment = {
      id: comments.length + 1,
      user_name: "Current User", // This should come from auth context
      content: newComment,
      timestamp: new Date().toISOString()
    };

    setComments(prev => [...prev, comment]);
    setNewComment("");
  };

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

          <div className="bg-card rounded-lg shadow-lg overflow-hidden mb-8">
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

              <div className="aspect-video bg-black rounded-lg overflow-hidden mb-8">
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

              {/* Video Analytics Section */}
              <div className="mb-8">
                <h2 className="text-xl font-semibold mb-4 flex items-center">
                  <BarChart2 className="mr-2" size={20} />
                  Lift Analysis
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-card/50 p-4 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-muted-foreground">Form Score</span>
                      <Activity className="text-primary" size={20} />
                    </div>
                    <div className="text-2xl font-bold text-primary">{analytics.formScore}%</div>
                  </div>
                  <div className="bg-card/50 p-4 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-muted-foreground">Bar Speed</span>
                      <Target className="text-primary" size={20} />
                    </div>
                    <div className="text-2xl font-bold text-primary">{analytics.barSpeed}</div>
                  </div>
                  <div className="bg-card/50 p-4 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-muted-foreground">Range of Motion</span>
                      <Award className="text-primary" size={20} />
                    </div>
                    <div className="text-2xl font-bold text-primary">{analytics.rangeOfMotion}</div>
                  </div>
                </div>
                <div className="mt-4 bg-card/50 p-4 rounded-lg">
                  <h3 className="font-semibold mb-2">Recommendations</h3>
                  <ul className="list-disc list-inside text-muted-foreground">
                    {analytics.recommendations.map((rec, index) => (
                      <li key={index}>{rec}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Comments Section */}
              <div>
                <h2 className="text-xl font-semibold mb-4 flex items-center">
                  <MessageSquare className="mr-2" size={20} />
                  Comments
                </h2>
                <div className="space-y-4 mb-4">
                  {comments.map(comment => (
                    <div key={comment.id} className="bg-card/50 p-4 rounded-lg">
                      <div className="flex justify-between items-start mb-2">
                        <span className="font-medium">{comment.user_name}</span>
                        <span className="text-sm text-muted-foreground">
                          {new Date(comment.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-muted-foreground">{comment.content}</p>
                    </div>
                  ))}
                </div>
                <form onSubmit={handleCommentSubmit} className="flex gap-2">
                  <input
                    type="text"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Add a comment..."
                    className="flex-1 bg-background rounded-lg px-4 py-2 border focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <button
                    type="submit"
                    className="bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors"
                  >
                    <Send size={20} />
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default VideoPlayer;
