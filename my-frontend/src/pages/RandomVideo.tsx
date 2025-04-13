import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL, PROD_API_URL } from '../config';
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
  const [retryCount, setRetryCount] = useState(0);
  const [debugInfo, setDebugInfo] = useState({
    apiUrl: API_URL,
    productionUrl: PROD_API_URL,
    envValue: import.meta.env.VITE_API_URL || 'not set',
    errorDetails: '',
    isMobile: false,
    userAgent: ''
  });

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