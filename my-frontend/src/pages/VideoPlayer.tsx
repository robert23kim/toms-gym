import React, { useEffect, useState } from "react";
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
        
        console.log(`Using API URL for fetch: ${API_URL}`);
        
        const response = await axios.get(`${API_URL}/competitions/${id}/participants/${participantId}/attempts/${videoId}`);
        console.log("Video data response:", response.data);
        
        if (response.data && response.data.attempt) {
          const videoDataResponse = response.data.attempt;
          
          // Process the video URL for mobile if needed
          if (videoDataResponse.video_url) {
            const originalUrl = videoDataResponse.video_url;
            console.log("Original video URL:", originalUrl);
            
            // Process URL for mobile devices
            let processedUrl = originalUrl;
            
            // Handle Google Storage URLs
            if (originalUrl.includes('storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/')) {
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
                
                // Use the video proxy endpoint with explicit parameters
                processedUrl = `${videoProxyBaseUrl}/video/${encodeURIComponent(videoPath)}?mobile=true&t=${new Date().getTime()}`;
                
                // Add device type for debugging and better handling on backend
                let deviceType = 'desktop';
                if (isAndroid) deviceType = 'android';
                else if (isiOS) deviceType = 'ios';
                else if (isLinuxDesktop) deviceType = 'linux';
                
                processedUrl += `&device=${deviceType}`;
                console.log("Using proxy URL for device:", processedUrl);
              } else {
                // Add cache busting to direct URLs
                const cacheBuster = `t=${new Date().getTime()}`;
                processedUrl = originalUrl.includes('?') ? 
                  `${originalUrl}&${cacheBuster}` : 
                  `${originalUrl}?${cacheBuster}`;
              }
            }
            
            // Set the processed URL
            setFinalVideoUrl(processedUrl);
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
                {(finalVideoUrl || videoData.video_url) ? (
                  <video
                    src={finalVideoUrl || videoData.video_url}
                    controls
                    className="w-full h-full"
                    autoPlay
                    playsInline // For iOS compatibility
                  >
                    Your browser does not support the video tag.
                  </video>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    No video available
                  </div>
                )}
              </div>
              
              {/* Debug info for mobile */}
              {isMobile && (
                <div className="mt-4 p-2 text-xs bg-gray-100 rounded-md">
                  <p><strong>API URL:</strong> {debugInfo.apiUrl}</p>
                  <p><strong>Production URL:</strong> {debugInfo.productionUrl}</p>
                  <p><strong>Device:</strong> {isAndroid ? 'Android' : (isiOS ? 'iOS' : 'Desktop')}</p>
                  <p><strong>UA:</strong> {debugInfo.userAgent}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default VideoPlayer;
