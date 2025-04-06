import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config';
import VideoPlayer from '../components/VideoPlayer';
import { Button } from '../components/ui/button';
import { SkipForward, Upload, Filter, X } from 'lucide-react';
import Layout from '../components/Layout';
import { useNavigate, useLocation } from 'react-router-dom';

const RandomVideo = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const liftTypeFilter = queryParams.get('type');
  
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
      let url = `${API_URL}/${endpoint}`;
      
      // Add lift type filter if provided
      if (liftTypeFilter) {
        url += `?lift_type=${encodeURIComponent(liftTypeFilter)}`;
      }
      
      console.log('Fetching video from URL:', url);
      const response = await axios.get(url);
      console.log('Received response:', response.data);
      
      if (!response.data.video_url) {
        throw new Error('Video URL not found in response');
      }
      
      setVideoData({
        ...response.data,
        video_url: response.data.video_url
      });
      setError(null);
    } catch (err) {
      console.error('Error fetching video:', err);
      const errorMessage = err.response 
        ? `Error: ${err.response.status} - ${err.response.statusText}` 
        : 'Failed to fetch video. Please check your connection and try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideo('random-video');
  }, [liftTypeFilter]); // Re-fetch when the filter changes

  const handleNextVideo = () => {
    fetchVideo('next-video');
  };

  const handleUploadClick = () => {
    navigate('/upload');
  };
  
  const clearFilter = () => {
    navigate('/random-video');
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
              {liftTypeFilter && (
                <div className="flex items-center mt-2 bg-primary/10 text-primary px-3 py-1 rounded-full text-sm">
                  <Filter className="w-3 h-3 mr-1" />
                  <span>Filtered by: {liftTypeFilter}</span>
                  <button 
                    onClick={clearFilter}
                    className="ml-2 p-1 hover:bg-primary/20 rounded-full"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              )}
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