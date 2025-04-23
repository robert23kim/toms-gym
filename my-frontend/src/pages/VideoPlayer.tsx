import React, { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Play, Pause, Volume2, VolumeX, Maximize2, BarChart2, Activity, Target, Award } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL, PROD_API_URL } from "../config";

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
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);
  const [debugInfo, setDebugInfo] = useState({
    apiUrl: API_URL,
    productionUrl: PROD_API_URL,
    userAgent: '',
    isMobile: false
  });
  const [isVideoLoaded, setIsVideoLoaded] = useState(false);
  const [videoLoadError, setVideoLoadError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // We still need device type info for video path transformation
  const isAndroid = /Android/i.test(navigator.userAgent);
  const isiOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
  const isLinux = /Linux|X11/i.test(navigator.userAgent);
  const isLinuxDesktop = isLinux && !(/Mobile|Android/i.test(navigator.userAgent));
  
  // For device type info only (not API URL selection)
  const isMobile = (
    /iPhone|iPad|iPod|Android|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
    /Mobile|Tablet|Touch/i.test(navigator.userAgent) ||
    window.innerWidth < 768
  );

  useEffect(() => {
    // Update debug info
    setDebugInfo({
      apiUrl: API_URL,
      productionUrl: PROD_API_URL,
      userAgent: navigator.userAgent.substring(0, 100), // Truncate for display
      isMobile: isMobile
    });
  }, [isMobile]);

  useEffect(() => {
    const fetchVideoData = async () => {
      try {
        setLoading(true);
        setError(null);
        setVideoLoadError(null);
        
        console.log(`Using API URL for fetch: ${API_URL}`);
        
        const response = await axios.get(`${API_URL}/competitions/${id}/participants/${participantId}/attempts/${videoId}`);
        console.log("Video data response:", response.data);
        
        if (response.data) {
          let videoDataResponse = response.data;

          // Check if the response has an attempt property or is the attempt itself
          if (response.data.attempt) {
            videoDataResponse = response.data.attempt;
          }
          
          // Process the video URL for mobile if needed
          if (videoDataResponse.video_url) {
            const originalUrl = videoDataResponse.video_url;
            console.log("Original video URL:", originalUrl);
            
            // Process URL for mobile devices
            let processedUrl = originalUrl;
            
            // Handle Google Storage URLs
            if (originalUrl.includes('storage.googleapis.com')) {
              // Extract video path
              let videoPath = '';
              if (originalUrl.includes('jtr-lift-u-4ever-cool-bucket/videos/')) {
                videoPath = originalUrl.split('jtr-lift-u-4ever-cool-bucket/')[1];
              } else {
                // In case the URL format changes but still contains the bucket name
                const bucketPart = originalUrl.indexOf('jtr-lift-u-4ever-cool-bucket/');
                if (bucketPart >= 0) {
                  videoPath = originalUrl.substring(bucketPart + 'jtr-lift-u-4ever-cool-bucket/'.length);
                }
              }
              
              if (videoPath) {
                // ALWAYS use production URL for the video proxy (direct video access needs prod URL)
                const videoProxyBaseUrl = PROD_API_URL;
                
                console.log("Video path extracted:", videoPath);
                
                // Use the video proxy endpoint with explicit parameters - FORCE proxy usage
                processedUrl = `${videoProxyBaseUrl}/video/${encodeURIComponent(videoPath)}?mobile=true&t=${new Date().getTime()}`;
                
                // Add device type for debugging and better handling on backend
                let deviceType = 'desktop';
                if (isAndroid) deviceType = 'android';
                else if (isiOS) deviceType = 'ios';
                else if (isLinuxDesktop) deviceType = 'linux';
                
                processedUrl += `&device=${deviceType}`;
                console.log("Using proxy URL for device:", processedUrl);
              } else {
                console.warn("Could not extract video path from URL:", originalUrl);
                // Still try to use the proxy with the filename
                const videoProxyBaseUrl = PROD_API_URL;
                const filename = originalUrl.split('/').pop();
                if (filename) {
                  processedUrl = `${videoProxyBaseUrl}/video/videos/${encodeURIComponent(filename)}?mobile=true&t=${new Date().getTime()}`;
                  console.log("Fallback to proxy URL with filename:", processedUrl);
                } else {
                  // Add cache busting to direct URLs as last resort
                  const cacheBuster = `t=${new Date().getTime()}`;
                  processedUrl = originalUrl.includes('?') ? 
                    `${originalUrl}&${cacheBuster}` : 
                    `${originalUrl}?${cacheBuster}`;
                  console.log("Using direct URL with cache busting:", processedUrl);
                }
              }
            } else {
              console.log("URL is not from Google Storage, using as is:", originalUrl);
            }
            
            // Set the processed URL
            setFinalVideoUrl(processedUrl);
            console.log("Final video URL set to:", processedUrl);
          } else {
            console.error("No video URL found in the response data", videoDataResponse);
            setVideoLoadError("No video URL available in the server response");
          }
          
          setVideoData(videoDataResponse);
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

  // Add event handlers for video element
  const handleVideoError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    const videoElement = e.currentTarget;
    console.error("Video error:", videoElement.error);
    let errorMessage = "Unknown video playback error";
    
    if (videoElement.error) {
      switch (videoElement.error.code) {
        case 1:
          errorMessage = "Video loading aborted";
          break;
        case 2:
          errorMessage = "Network error occurred while loading video";
          break;
        case 3:
          errorMessage = "Video decoding failed - format may be unsupported";
          break;
        case 4:
          errorMessage = "Video format not supported by your browser";
          break;
        default:
          errorMessage = `Error code: ${videoElement.error.code}`;
      }
    }
    
    console.error("Video error details:", errorMessage);
    setVideoLoadError(errorMessage);
    setIsVideoLoaded(false);
  };
  
  const handleVideoLoad = () => {
    console.log("Video loaded successfully");
    setIsVideoLoaded(true);
    setVideoLoadError(null);
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
                {(finalVideoUrl || (videoData && videoData.video_url)) ? (
                  <>
                    <video
                      ref={videoRef}
                      src={finalVideoUrl || (videoData && videoData.video_url)}
                      controls
                      className="w-full h-full"
                      autoPlay
                      playsInline // For iOS compatibility
                      onError={handleVideoError}
                      onLoadedData={handleVideoLoad}
                      onLoadedMetadata={() => console.log("Video metadata loaded successfully")}
                      onCanPlay={() => console.log("Video can play now")}
                    >
                      Your browser does not support the video tag.
                    </video>
                    {videoLoadError && (
                      <div className="mt-2 p-2 bg-red-100 border border-red-400 text-red-700 rounded">
                        <p><strong>Error loading video:</strong> {videoLoadError}</p>
                        <p className="text-sm mt-1">Try refreshing the page or check your internet connection.</p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    No video available
                  </div>
                )}
              </div>
              
              {/* Debug info */}
              <div className="mt-4 p-2 text-xs bg-gray-100 rounded-md">
                <details>
                  <summary className="cursor-pointer font-medium">Debug Info (click to expand)</summary>
                  <div className="mt-2 space-y-1">
                    <p><strong>API URL:</strong> {debugInfo.apiUrl}</p>
                    <p><strong>Production URL:</strong> {debugInfo.productionUrl}</p>
                    <p><strong>Device:</strong> {isAndroid ? 'Android' : (isiOS ? 'iOS' : (isLinux ? 'Linux' : 'Desktop'))}</p>
                    <p><strong>Is Mobile:</strong> {isMobile ? 'Yes' : 'No'}</p>
                    <p><strong>UA:</strong> {debugInfo.userAgent}</p>
                    <p><strong>Original URL:</strong> {videoData?.video_url || 'N/A'}</p>
                    <p><strong>Processed URL:</strong> {finalVideoUrl || 'N/A'}</p>
                    <p><strong>Video Loaded:</strong> {isVideoLoaded ? 'Yes' : 'No'}</p>
                    {videoRef.current && (
                      <>
                        <p><strong>Video Ready State:</strong> {videoRef.current.readyState}</p>
                        <p><strong>Network State:</strong> {videoRef.current.networkState}</p>
                      </>
                    )}
                  </div>
                </details>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default VideoPlayer;
