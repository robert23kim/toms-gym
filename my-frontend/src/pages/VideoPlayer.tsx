import React, { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL, PROD_API_URL } from "../config";
import { triggerLiftingAnalysis, getLiftingResult } from '../lib/api';
import type { LiftingResult } from '../lib/types';

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

function formatDate(ts: string | undefined): string {
  if (!ts) return '';
  const d = new Date(ts);
  return isNaN(d.getTime()) ? '' : d.toLocaleDateString();
}

function statusBadge(status: string | undefined): { label: string; className: string } {
  switch (status) {
    case 'completed':
      return { label: 'Successful', className: 'bg-green-500/10 text-green-500' };
    case 'pending':
      return { label: 'Pending', className: 'bg-yellow-500/10 text-yellow-500' };
    case 'failed':
      return { label: 'Failed', className: 'bg-red-500/10 text-red-500' };
    default:
      return { label: status || 'Unknown', className: 'bg-gray-500/10 text-gray-500' };
  }
}

const VideoPlayer: React.FC = () => {
  const { id, participantId, videoId } = useParams<{ id: string; participantId: string; videoId: string }>();
  const [videoData, setVideoData] = useState<VideoData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);
  const [isVideoLoaded, setIsVideoLoaded] = useState(false);
  const [videoLoadError, setVideoLoadError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [liftingResult, setLiftingResult] = useState<LiftingResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // We still need device type info for video path transformation
  const isAndroid = /Android/i.test(navigator.userAgent);
  const isiOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
  const isLinux = /Linux|X11/i.test(navigator.userAgent);
  const isLinuxDesktop = isLinux && !(/Mobile|Android/i.test(navigator.userAgent));

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
              // Extract video path - get everything after the bucket name
              let videoPath = '';
              if (originalUrl.includes('jtr-lift-u-4ever-cool-bucket/')) {
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

                // Extract just the filename (without 'videos/' prefix) to avoid encoding issues
                // The backend will add the 'videos/' prefix automatically if needed
                let pathToSend = videoPath;
                if (videoPath.startsWith('videos/')) {
                  pathToSend = videoPath.substring('videos/'.length);
                }

                // Encode the filename/path to handle special characters
                const encodedPath = encodeURIComponent(pathToSend);

                // Use the video proxy endpoint with explicit parameters - FORCE proxy usage
                processedUrl = `${videoProxyBaseUrl}/video/${encodedPath}?mobile=true&t=${new Date().getTime()}`;

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

  // Check for existing lifting result on mount
  useEffect(() => {
    if (videoId) {
      getLiftingResult(videoId)
        .then(setLiftingResult)
        .catch(() => {}); // No result yet — that's fine
    }
  }, [videoId]);

  // Poll for lifting analysis progress
  useEffect(() => {
    if (!isAnalyzing || !liftingResult) return;
    if (liftingResult.processing_status === 'completed' || liftingResult.processing_status === 'failed') {
      setIsAnalyzing(false);
      return;
    }
    const interval = setInterval(async () => {
      try {
        const result = await getLiftingResult(videoId!);
        setLiftingResult(result);
        if (result.processing_status === 'completed' || result.processing_status === 'failed') {
          setIsAnalyzing(false);
        }
      } catch (e) { /* continue polling */ }
    }, 3000);
    return () => clearInterval(interval);
  }, [isAnalyzing, liftingResult?.processing_status, videoId]);

  const handleAnalyzeForm = async () => {
    if (!videoId) return;
    setIsAnalyzing(true);
    try {
      await triggerLiftingAnalysis(videoId);
      const result = await getLiftingResult(videoId);
      setLiftingResult(result);
    } catch (e) {
      setIsAnalyzing(false);
    }
  };

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

  const badge = statusBadge(videoData.success);
  const dateStr = formatDate(videoData.timestamp);

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-6xl mx-auto">
          <Link
            to={`/challenges/${id}`}
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Challenge
          </Link>

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Left column: Video */}
            <div className="lg:col-span-3">
              {(finalVideoUrl || (videoData && videoData.video_url)) ? (
                <>
                  <video
                    ref={videoRef}
                    src={finalVideoUrl || (videoData && videoData.video_url)}
                    controls
                    className="max-h-[70vh] w-full object-contain rounded-lg bg-black"
                    autoPlay
                    muted
                    playsInline
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
                <div className="flex items-center justify-center h-64 bg-black rounded-lg text-muted-foreground">
                  No video available
                </div>
              )}
            </div>

            {/* Right column: Info + Analysis */}
            <div className="lg:col-span-2">
              <div className="bg-card rounded-lg shadow-lg p-6">
                <h1 className="text-2xl font-bold mb-4">{videoData.participant_name}'s {videoData.lift_type}</h1>
                <div className="flex items-center gap-4 text-muted-foreground mb-6">
                  <span>{videoData.weight}kg</span>
                  <span className={`px-2 py-1 rounded-full text-sm ${badge.className}`}>
                    {badge.label}
                  </span>
                  {dateStr && <span>{dateStr}</span>}
                </div>

                {/* Lifting Analysis */}
                {videoData && videoData.lift_type && videoData.lift_type !== 'Bowling' && (
                  <div>
                    {!liftingResult || liftingResult.processing_status === 'failed' ? (
                      <button
                        onClick={handleAnalyzeForm}
                        disabled={isAnalyzing}
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                      >
                        {isAnalyzing ? 'Analyzing...' : 'Analyze Form'}
                      </button>
                    ) : liftingResult.processing_status === 'queued' || liftingResult.processing_status === 'processing' ? (
                      <div className="flex items-center gap-2">
                        <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full" />
                        <span>Analyzing form...</span>
                      </div>
                    ) : liftingResult.processing_status === 'completed' && liftingResult.report ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          <span className={`text-2xl font-bold ${
                            liftingResult.report.overall_grade === 'A' ? 'text-green-500' :
                            liftingResult.report.overall_grade === 'B' ? 'text-green-400' :
                            liftingResult.report.overall_grade === 'C' ? 'text-yellow-500' :
                            liftingResult.report.overall_grade === 'D' ? 'text-orange-500' : 'text-red-500'
                          }`}>{liftingResult.report.overall_grade}</span>
                          <span>{liftingResult.report.total_reps} reps | Score: {liftingResult.report.overall_score?.toFixed(0)}%</span>
                        </div>
                        {liftingResult.report.insights.length > 0 && (
                          <ul className="text-sm text-gray-600">
                            {liftingResult.report.insights.map((insight, i) => (
                              <li key={i}>- {insight}</li>
                            ))}
                          </ul>
                        )}
                        {liftingResult.annotated_video_url && (
                          <video controls className="w-full rounded" src={liftingResult.annotated_video_url} />
                        )}
                        <button onClick={handleAnalyzeForm} className="text-sm text-blue-500 hover:underline">
                          Re-analyze
                        </button>
                      </div>
                    ) : null}
                    {liftingResult?.error_message && (
                      <p className="text-red-500 text-sm mt-2">Error: {liftingResult.error_message}</p>
                    )}
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
