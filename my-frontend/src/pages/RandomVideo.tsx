import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL, PROD_API_URL } from '../config';
import VideoPlayer from '../components/VideoPlayer';
import { Button } from '../components/ui/button';
import { SkipForward, Upload, Filter, X, Play, Trophy } from 'lucide-react';
import Layout from '../components/Layout';
import { useNavigate, useLocation, Link } from 'react-router-dom';

interface CompetitionVideos {
  competition_id: string;
  competition_name: string;
  videos: Array<{
    attempt_id: string;
    user_id: string;
    lift_type: string;
    weight: number;
    status: string;
    created_at: string;
    video_url: string;
  }>;
}

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
  const [retryCount, setRetryCount] = useState(0);
  const [debugInfo, setDebugInfo] = useState({
    apiUrl: API_URL,
    productionUrl: PROD_API_URL,
    envValue: import.meta.env.VITE_API_URL || 'not set',
    errorDetails: '',
    isMobile: false,
    userAgent: ''
  });
  const [allVideos, setAllVideos] = useState<CompetitionVideos[]>([]);
  const [loadingAllVideos, setLoadingAllVideos] = useState(true);

  // We still need device type info for video path transformation
  const isAndroid = /Android/i.test(navigator.userAgent);
  const isiOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
  const isLinux = /Linux|X11/i.test(navigator.userAgent);
  const isLinuxDesktop = isLinux && !(/Mobile|Android/i.test(navigator.userAgent));
  
  // Use navigator for device detection (only for device type info, not API URL)
  const isMobile = (
    /iPhone|iPad|iPod|Android|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
    /Mobile|Tablet|Touch/i.test(navigator.userAgent) ||
    window.innerWidth < 768
  );

  useEffect(() => {
    // Update debug info with detailed mobile status
    setDebugInfo(prev => ({
      ...prev, 
      isMobile: isMobile,
      userAgent: navigator.userAgent.substring(0, 100) // Truncate for display
    }));
  }, [isMobile]);

  // Fetch all videos from all competitions
  const fetchAllVideos = async () => {
    try {
      setLoadingAllVideos(true);
      
      // Get list of all competitions first
      const competitionsResponse = await axios.get(`${API_URL}/competitions`);
      const competitions = competitionsResponse.data.competitions || [];
      
      // For each competition, get participants with videos
      const competitionVideos: CompetitionVideos[] = [];
      
      for (const competition of competitions) {
        const participantsResponse = await axios.get(`${API_URL}/competitions/${competition.id}/participants`);
        const participants = participantsResponse.data.participants || [];
        
        // Collect all videos from all participants
        const videos = [];
        for (const participant of participants) {
          // Filter for attempts that have video_url
          for (const attempt of (participant.attempts || [])) {
            if (attempt.video_url) {
              videos.push({
                attempt_id: attempt.id,
                user_id: participant.id,
                lift_type: attempt.lift_type,
                weight: attempt.weight,
                status: attempt.status,
                created_at: attempt.created_at || new Date().toISOString(),
                video_url: attempt.video_url
              });
            }
          }
        }
        
        // Only add competitions that have videos
        if (videos.length > 0) {
          competitionVideos.push({
            competition_id: competition.id,
            competition_name: competition.name,
            videos
          });
        }
      }
      
      setAllVideos(competitionVideos);
    } catch (err) {
      console.error('Error fetching all videos:', err);
    } finally {
      setLoadingAllVideos(false);
    }
  };

  const fetchVideo = async (endpoint: string) => {
    try {
      setLoading(true);
      
      // Build URL with any needed query parameters
      const params = new URLSearchParams();
      
      // Add lift type filter if provided
      if (liftTypeFilter) {
        params.append('lift_type', liftTypeFilter);
      }
      
      // Always add mobile flag for mobile devices to ensure backend knows
      if (isMobile || isAndroid || isiOS || isLinuxDesktop) {
        params.append('mobile', 'true');
      }
      
      // Add timestamp to prevent caching
      params.append('t', new Date().getTime().toString());
      
      // Construct final URL
      const queryString = params.toString();
      let url = `${API_URL}/${endpoint}${queryString ? `?${queryString}` : ''}`;
      
      console.log('Fetching video from URL:', url);
      console.log('Is mobile device?', isMobile);
      console.log('Using API URL:', API_URL);
      
      setDebugInfo(prev => ({
        ...prev, 
        apiUrl: API_URL,
        isMobile: isMobile
      }));
      
      const response = await axios.get(url);
      console.log('Received response:', response.data);
      
      if (!response.data.video_url) {
        throw new Error('Video URL not found in response');
      }
      
      // Extract the original video URL
      const videoUrl = response.data.video_url;
      console.log('Original video URL from response:', videoUrl);
      
      // Handle URL differently based on device and URL type
      let finalVideoUrl = videoUrl;
      
      // Check if it's a Google Storage URL
      if (videoUrl.includes('storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/')) {
        // Extract video path - handle both formats
        let videoPath = '';
        if (videoUrl.includes('jtr-lift-u-4ever-cool-bucket/videos/')) {
          videoPath = videoUrl.split('jtr-lift-u-4ever-cool-bucket/')[1];
        } else {
          // In case the URL format changes but still contains the bucket name
          const bucketPart = videoUrl.indexOf('jtr-lift-u-4ever-cool-bucket/');
          if (bucketPart >= 0) {
            videoPath = videoUrl.substring(bucketPart + 'jtr-lift-u-4ever-cool-bucket/'.length);
          }
        }
        
        if (videoPath) {
          // Log for debugging
          console.log(`Video path extracted: ${videoPath}`);
          
          // FORCE PRODUCTION URL - no conditions
          const videoProxyBaseUrl = PROD_API_URL;
          
          // Use our proxy endpoint with explicit parameters
          finalVideoUrl = `${videoProxyBaseUrl}/video/${encodeURIComponent(videoPath)}?mobile=true`;
          console.log(`Using proxy URL: ${finalVideoUrl}`);
          
          // Add cache busting parameter and device info for debugging
          finalVideoUrl += `&t=${new Date().getTime()}`;
          
          // Determine device type
          let deviceType = 'desktop';
          if (isAndroid) deviceType = 'android';
          else if (isiOS) deviceType = 'ios';
          else if (isLinuxDesktop) deviceType = 'linux';
          
          finalVideoUrl += `&device=${deviceType}`;
        } else {
          // Fallback with alt=media and cache busting for Google Storage
          console.log('Could not extract video path, using fallback');
          const cacheBuster = `t=${new Date().getTime()}`;
          finalVideoUrl = videoUrl.includes('?') ? 
            `${videoUrl}&alt=media&${cacheBuster}` : 
            `${videoUrl}?alt=media&${cacheBuster}`;
        }
      } else {
        // For non-Google Storage URLs, just add cache busting
        const cacheBuster = `t=${new Date().getTime()}`;
        finalVideoUrl = videoUrl.includes('?') ? 
          `${videoUrl}&${cacheBuster}` : 
          `${videoUrl}?${cacheBuster}`;
      }
      
      console.log('Final video URL:', finalVideoUrl);
      
      setVideoData({
        ...response.data,
        video_url: finalVideoUrl
      });
      setError(null);
    } catch (err) {
      console.error('Error fetching video:', err);
      const errorMessage = err.response 
        ? `Error: ${err.response.status} - ${err.response.statusText}` 
        : 'Failed to fetch video. Please check your connection and try again.';
      setError(errorMessage);
      
      setDebugInfo(prev => ({
        ...prev, 
        errorDetails: JSON.stringify(err.response?.data || err.message || 'Unknown error')
      }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideo('random-video');
    fetchAllVideos(); // Fetch all videos when component mounts
  }, [liftTypeFilter]); // Re-fetch when the filter changes

  const handleRetry = () => {
    setRetryCount(prev => prev + 1);
    fetchVideo('random-video');
  };

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
        <div className="flex flex-col items-center justify-center min-h-screen">
          <div className="text-xl mb-4">Loading video...</div>
          <div className="bg-gray-100 p-4 rounded max-w-md">
            <h3 className="font-bold">Debug Info:</h3>
            <p><strong>API URL:</strong> {debugInfo.apiUrl}</p>
            <p><strong>Production URL:</strong> {debugInfo.productionUrl}</p>
            <p><strong>Is Mobile:</strong> {debugInfo.isMobile ? 'Yes' : 'No'}</p>
            <p><strong>Device:</strong> {isAndroid ? 'Android' : (isiOS ? 'iOS' : 'Desktop')}</p>
            <p><strong>User Agent:</strong> {debugInfo.userAgent}</p>
            <p><strong>ENV Value:</strong> {debugInfo.envValue}</p>
          </div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center min-h-screen p-4">
          <div className="text-xl text-red-500 mb-4">{error}</div>
          <div className="bg-gray-100 p-4 rounded max-w-md mb-4">
            <h3 className="font-bold">Debug Info:</h3>
            <p><strong>API URL:</strong> {debugInfo.apiUrl}</p>
            <p><strong>Production URL:</strong> {debugInfo.productionUrl}</p>
            <p><strong>Is Mobile:</strong> {debugInfo.isMobile ? 'Yes' : 'No'}</p>
            <p><strong>Device:</strong> {isAndroid ? 'Android' : (isiOS ? 'iOS' : 'Desktop')}</p>
            <p><strong>User Agent:</strong> {debugInfo.userAgent}</p>
            <p><strong>ENV Value:</strong> {debugInfo.envValue}</p>
            <p><strong>Error Details:</strong> {debugInfo.errorDetails}</p>
          </div>
          <Button onClick={handleRetry} variant="outline" className="mt-4">
            Retry
          </Button>
        </div>
      );
    }

    if (!videoData) {
      return (
        <div className="flex flex-col items-center justify-center min-h-screen">
          <div className="text-xl mb-4">No videos found</div>
          <div className="bg-gray-100 p-4 rounded max-w-md">
            <h3 className="font-bold">Debug Info:</h3>
            <p><strong>API URL:</strong> {debugInfo.apiUrl}</p>
            <p><strong>Production URL:</strong> {debugInfo.productionUrl}</p>
            <p><strong>Is Mobile:</strong> {debugInfo.isMobile ? 'Yes' : 'No'}</p>
            <p><strong>Device:</strong> {isAndroid ? 'Android' : (isiOS ? 'iOS' : 'Desktop')}</p>
            <p><strong>User Agent:</strong> {debugInfo.userAgent}</p>
            <p><strong>ENV Value:</strong> {debugInfo.envValue}</p>
          </div>
        </div>
      );
    }

    return (
      <div>
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
        
        {/* All Videos Section */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 mb-8">
          <div className="flex items-center gap-3 mb-8">
            <Trophy className="text-accent" size={24} />
            <h2 className="text-2xl font-bold">Browse All Videos</h2>
          </div>
          
          {loadingAllVideos ? (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
            </div>
          ) : allVideos.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p>No videos available from competitions yet.</p>
              <Button 
                variant="outline" 
                className="mt-4"
                onClick={handleUploadClick}
              >
                Upload the first video
              </Button>
            </div>
          ) : (
            <div className="space-y-12">
              {allVideos.map(competition => (
                <div key={competition.competition_id} className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Link 
                      to={`/competitions/${competition.competition_id}`}
                      className="text-xl font-semibold flex items-center gap-2 hover:text-accent transition-colors"
                    >
                      <Trophy className="h-5 w-5" />
                      {competition.competition_name}
                    </Link>
                    <span className="text-sm text-muted-foreground">
                      {competition.videos.length} {competition.videos.length === 1 ? 'video' : 'videos'}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {competition.videos.slice(0, 3).map(video => (
                      <Link 
                        key={video.attempt_id}
                        to={`/video-player/${competition.competition_id}/${video.user_id}/${video.attempt_id}`}
                        className="bg-background rounded-lg overflow-hidden transition-all hover:scale-[1.02] focus:scale-[1.02] shadow-sm"
                      >
                        <div className="aspect-video bg-muted relative">
                          <div className="absolute inset-0 flex items-center justify-center">
                            <Play className="w-12 h-12 text-accent/75" />
                          </div>
                        </div>
                        <div className="p-4">
                          <h3 className="font-medium">{video.lift_type} - {video.weight}kg</h3>
                          <p className="text-sm text-muted-foreground">
                            {new Date(video.created_at).toLocaleDateString()}
                          </p>
                          <span className={`mt-2 inline-block px-2 py-0.5 rounded-full text-xs ${
                            video.status === 'completed' ? 'bg-green-100 text-green-800' : 
                            video.status === 'failed' ? 'bg-red-100 text-red-800' : 
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {video.status}
                          </span>
                        </div>
                      </Link>
                    ))}
                    
                    {competition.videos.length > 3 && (
                      <Link 
                        to={`/competitions/${competition.competition_id}`}
                        className="bg-muted/30 rounded-lg flex items-center justify-center aspect-video hover:bg-muted/50 transition-colors col-span-1"
                      >
                        <div className="text-center">
                          <p className="text-lg font-medium">View {competition.videos.length - 3} more</p>
                          <p className="text-sm text-muted-foreground">from this competition</p>
                        </div>
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
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