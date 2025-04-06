import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config';
import VideoPlayer from '../components/VideoPlayer';
import { Button } from '../components/ui/button';
import { SkipForward, Upload } from 'lucide-react';
import Layout from '../components/Layout';
import { useNavigate } from 'react-router-dom';

const RandomVideo = () => {
  const navigate = useNavigate();
  const [videoData, setVideoData] = useState<{
    video_id: number;
    participant_id: number;
    competition_id: number;
    video_url: string;
    participant_name: string;
    lift_type: string;
    weight: number;
    success: boolean;
    total_videos: number;
    current_index: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVideo = async (endpoint: string) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/${endpoint}`);
      setVideoData({
        ...response.data,
        video_url: response.data.video_url
      });
      setError(null);
    } catch (err) {
      setError('Failed to fetch video');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideo('random-video');
  }, []);

  const handleNextVideo = () => {
    fetchVideo('next-video');
  };

  const handleUploadClick = () => {
    navigate('/upload');
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-xl">Loading video...</div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-xl text-red-500">{error}</div>
        </div>
      );
    }

    if (!videoData) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-xl">No videos found</div>
        </div>
      );
    }

    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">Random Video</h1>
              <p className="text-muted-foreground mt-2">
                {videoData.participant_name} - {videoData.lift_type} @ {videoData.weight}kg
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Video {videoData.current_index + 1} of {videoData.total_videos}
              </p>
            </div>
            <Button 
              variant="outline" 
              size="lg"
              onClick={handleUploadClick}
              className="flex items-center gap-2"
            >
              <Upload className="h-4 w-4" />
              Upload Video
            </Button>
          </div>
        </div>
        <VideoPlayer
          videoUrl={videoData.video_url}
          title={`${videoData.participant_name} - ${videoData.lift_type} @ ${videoData.weight}kg`}
          onNextVideo={handleNextVideo}
        />
      </div>
    );
  };

  return (
    <Layout>
      {renderContent()}
    </Layout>
  );
};

export default RandomVideo; 