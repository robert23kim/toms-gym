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
  status: string;
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
  const [videoTab, setVideoTab] = useState<'original' | 'annotated'>('original');
  const [showRepDetails, setShowRepDetails] = useState(false);
  const [expandedMetric, setExpandedMetric] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState<string | null>(null);

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
    if (!isAnalyzing || !videoId) return;
    // Already done — stop polling
    if (liftingResult?.processing_status === 'completed' || liftingResult?.processing_status === 'failed') {
      setIsAnalyzing(false);
      return;
    }
    const interval = setInterval(async () => {
      try {
        const result = await getLiftingResult(videoId);
        setLiftingResult(result);
        if (result.processing_status === 'completed' || result.processing_status === 'failed') {
          setIsAnalyzing(false);
        }
      } catch (e) { /* continue polling — result may not exist yet */ }
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

  const liftReport = liftingResult?.report;
  const hasPassingGrade = liftReport && ['A', 'B', 'C', 'D'].includes(liftReport.overall_grade);
  const hasFailingGrade = liftReport && liftReport.overall_grade === 'F' && liftReport.total_reps > 0;
  const badge = hasPassingGrade
    ? { label: 'Approved', className: 'bg-green-500/10 text-green-500' }
    : hasFailingGrade
      ? { label: 'Failed', className: 'bg-red-500/10 text-red-500' }
      : statusBadge(videoData.status);
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

          {(() => {
            const hasAnalysis = liftingResult?.processing_status === 'completed' && liftingResult.report;
            const hasAnnotatedVideo = hasAnalysis && liftingResult?.annotated_video_url;
            const report = liftingResult?.report;

            const gradeColor = (grade: string) =>
              grade === 'A' ? 'text-green-500' :
              grade === 'B' ? 'text-green-400' :
              grade === 'C' ? 'text-yellow-500' :
              grade === 'D' ? 'text-orange-500' : 'text-red-500';

            const gradeBg = (grade: string) =>
              grade === 'A' ? 'bg-green-500' :
              grade === 'B' ? 'bg-green-400' :
              grade === 'C' ? 'bg-yellow-500' :
              grade === 'D' ? 'bg-orange-500' : 'bg-red-500';

            // Auto-switch to annotated tab when analysis completes
            const activeTab = videoTab === 'annotated' && !hasAnnotatedVideo ? 'original' : videoTab;

            return (
              <>
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                  {/* Left column: Video with tab toggle */}
                  <div className="lg:col-span-3">
                    {/* Tab toggle (only show when annotated video exists) */}
                    {hasAnnotatedVideo && (
                      <div className="flex gap-1 mb-3 bg-muted rounded-lg p-1">
                        <button
                          onClick={() => setVideoTab('original')}
                          className={`flex-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                            activeTab === 'original' ? 'bg-card shadow text-foreground' : 'text-muted-foreground hover:text-foreground'
                          }`}
                        >
                          Original
                        </button>
                        <button
                          onClick={() => setVideoTab('annotated')}
                          className={`flex-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                            activeTab === 'annotated' ? 'bg-card shadow text-foreground' : 'text-muted-foreground hover:text-foreground'
                          }`}
                        >
                          Annotated
                        </button>
                      </div>
                    )}

                    {activeTab === 'annotated' && hasAnnotatedVideo ? (
                      <video
                        controls
                        autoPlay
                        muted
                        playsInline
                        className="max-h-[70vh] w-full object-contain rounded-lg bg-black"
                        src={liftingResult!.annotated_video_url}
                      />
                    ) : (finalVideoUrl || videoData?.video_url) ? (
                      <>
                        <video
                          ref={videoRef}
                          src={finalVideoUrl || videoData?.video_url}
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
                  <div className="lg:col-span-2 space-y-4">
                    {/* Title + metadata */}
                    <div className="bg-card rounded-lg shadow-lg p-6">
                      <h1 className="text-2xl font-bold mb-2">{videoData.participant_name}'s {videoData.lift_type}</h1>
                      <div className="flex items-center gap-3 text-muted-foreground">
                        <span className="font-medium text-foreground">{videoData.weight} lbs</span>
                        <span className={`px-2 py-1 rounded-full text-sm ${badge.className}`}>
                          {badge.label}
                        </span>
                        {dateStr && <span>{dateStr}</span>}
                      </div>
                    </div>

                    {/* Analysis section */}
                    {videoData.lift_type && videoData.lift_type !== 'Bowling' && (
                      <>
                        {/* No analysis yet or failed */}
                        {(!liftingResult || liftingResult.processing_status === 'failed') && (
                          <div className="bg-card rounded-lg shadow-lg p-6 text-center">
                            <p className="text-muted-foreground text-sm mb-3">
                              Get AI-powered form analysis with rep counting and technique feedback.
                            </p>
                            <button
                              onClick={handleAnalyzeForm}
                              disabled={isAnalyzing}
                              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
                            >
                              {isAnalyzing ? (
                                <span className="flex items-center justify-center gap-2">
                                  <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
                                  Analyzing...
                                </span>
                              ) : 'Analyze Form'}
                            </button>
                            {liftingResult?.error_message && (
                              <p className="text-red-500 text-sm mt-2">{liftingResult.error_message}</p>
                            )}
                          </div>
                        )}

                        {/* Analyzing in progress */}
                        {liftingResult && (liftingResult.processing_status === 'queued' || liftingResult.processing_status === 'processing') && (
                          <div className="bg-card rounded-lg shadow-lg p-6 text-center">
                            <div className="animate-spin h-8 w-8 border-[3px] border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
                            <p className="font-medium">Analyzing your form...</p>
                            <p className="text-sm text-muted-foreground mt-1">This usually takes 30-60 seconds.</p>
                          </div>
                        )}

                        {/* Analysis complete — Score Card */}
                        {hasAnalysis && report && (
                          <>
                            {/* Score card */}
                            <div className="bg-card rounded-lg shadow-lg p-6">
                              <div className="flex items-center gap-4 mb-4">
                                <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${gradeBg(report.overall_grade)}/15`}>
                                  <span className={`text-3xl font-bold ${gradeColor(report.overall_grade)}`}>
                                    {report.overall_grade}
                                  </span>
                                </div>
                                <div className="flex-1">
                                  <div className="flex justify-between items-center mb-1">
                                    <span className="font-medium">{report.total_reps} rep{report.total_reps !== 1 ? 's' : ''} detected</span>
                                    <span className="text-sm text-muted-foreground">{report.overall_score?.toFixed(0)}%</span>
                                  </div>
                                  <div className="w-full bg-muted rounded-full h-2.5">
                                    <div
                                      className={`h-2.5 rounded-full transition-all ${gradeBg(report.overall_grade)}`}
                                      style={{ width: `${Math.min(report.overall_score || 0, 100)}%` }}
                                    />
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Per-rep breakdown with progress bars */}
                            {report.rep_metrics.length > 0 && (
                              <div className="bg-card rounded-lg shadow-lg p-6 space-y-3">
                                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Rep Breakdown</h3>
                                {report.rep_metrics.map((rm) => (
                                  <div key={rm.rep_number} className="border border-border rounded-lg p-3">
                                    <div className="flex items-center justify-between mb-3">
                                      <span className="font-medium text-sm">Rep {rm.rep_number}</span>
                                      <span className={`text-sm font-bold ${gradeColor(rm.form_grade)}`}>
                                        {rm.form_grade} ({rm.form_score.toFixed(0)}%)
                                      </span>
                                    </div>
                                    {rm.metrics && rm.metrics.length > 0 ? (
                                      <div className="space-y-2">
                                        {rm.metrics.map((m) => {
                                          const statusColor = m.status === 'pass' ? 'bg-green-500' : m.status === 'warn' ? 'bg-yellow-500' : 'bg-red-500';
                                          const statusText = m.status === 'pass' ? 'text-green-400' : m.status === 'warn' ? 'text-yellow-400' : 'text-red-400';
                                          const isPercent = m.unit === '%';
                                          // For degree-based metrics (shoulder swing), show an inverted bar (lower = better)
                                          const isDegree = m.unit === '°';
                                          const isTempo = m.unit === ':1';
                                          const showBar = isPercent || isDegree || isTempo;
                                          const barWidth = isPercent
                                            ? Math.min(m.value, 100)
                                            : isDegree
                                              ? Math.max(0, Math.min(100, 100 - (m.value / 90) * 100))  // 0°=100%, 90°=0%
                                              : isTempo
                                                ? Math.max(0, Math.min(100, (m.value / 3) * 100))  // 0:1=0%, 3:1=100%
                                                : 0;
                                          const hasClips = m.clip_url != null || (m.best_time_s != null && m.worst_time_s != null);
                                          const isExpanded = expandedMetric === `${rm.rep_number}-${m.key}`;
                                          const metricId = `${rm.rep_number}-${m.key}`;
                                          return (
                                            <div key={m.key} className="text-xs">
                                              <div
                                                className={`flex justify-between items-center mb-0.5 ${hasClips ? 'cursor-pointer hover:bg-muted/30 -mx-1 px-1 rounded' : ''}`}
                                                onClick={hasClips ? () => setExpandedMetric(isExpanded ? null : metricId) : undefined}
                                              >
                                                <span className="text-muted-foreground flex items-center gap-1">
                                                  {hasClips && <span className="text-[10px]">{isExpanded ? '▼' : '▶'}</span>}
                                                  {m.label}
                                                  <span
                                                    className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-muted text-[9px] text-muted-foreground/70 cursor-pointer shrink-0 hover:bg-muted/80"
                                                    onClick={(e) => { e.stopPropagation(); setShowHelp(showHelp === m.key ? null : m.key); }}
                                                  >?</span>
                                                </span>
                                                <div className="flex items-center gap-2">
                                                  <span className={`font-medium ${statusText}`}>
                                                    {m.value}{m.unit}
                                                  </span>
                                                  <span className="text-muted-foreground/60 w-16 text-right">{m.target}</span>
                                                </div>
                                              </div>
                                              {showHelp === m.key && (
                                                <div className="text-[10px] text-muted-foreground/80 bg-muted/40 rounded px-2 py-1 mb-1">
                                                  {{
                                                    rom: 'How much of the full curl range you used. Measures the angle between full extension (~160°) and peak contraction (~60°).',
                                                    control: 'How smoothly you lowered the weight. Measures wrist deceleration in the last 20% of the lowering phase.',
                                                    elbow_stability: 'How stationary your elbow stayed during the curl. Measures horizontal drift of the elbow joint relative to your upper arm length.',
                                                    shoulder_swing: 'How much your upper arm swung forward. Measures the angle between your torso and upper arm at the shoulder joint.',
                                                    tempo: 'Ratio of lowering time to lifting time. A 2:1 ratio means you lower twice as slowly as you lift — good for muscle growth.',
                                                  }[m.key]}
                                                </div>
                                              )}
                                              {showBar && (
                                                <div className="w-full bg-muted rounded-full h-1.5">
                                                  <div
                                                    className={`h-1.5 rounded-full ${statusColor}`}
                                                    style={{ width: `${barWidth}%` }}
                                                  />
                                                </div>
                                              )}
                                              {isExpanded && hasClips && (() => {
                                                const borderColor = m.status === 'pass' ? 'border-green-500/40' : m.status === 'warn' ? 'border-yellow-500/40' : 'border-red-500/40';
                                                // Prefer dedicated clip, fall back to annotated video seek
                                                const clipSrc = m.clip_url
                                                  ? m.clip_url
                                                  : liftingResult?.annotated_video_url
                                                    ? `${liftingResult.annotated_video_url}#t=${m.status === 'pass' ? m.best_time_s! : m.worst_time_s!},${(m.status === 'pass' ? m.best_time_s! : m.worst_time_s!) + 2}`
                                                    : null;
                                                if (!clipSrc) return null;
                                                return (
                                                  <div className={`border ${borderColor} rounded overflow-hidden mt-2 mb-1`}>
                                                    <video
                                                      className="w-full rounded"
                                                      src={clipSrc}
                                                      autoPlay
                                                      muted
                                                      loop
                                                      playsInline
                                                      onLoadedData={(e) => { (e.target as HTMLVideoElement).playbackRate = 0.25; }}
                                                    />
                                                  </div>
                                                );
                                              })()}
                                            </div>
                                          );
                                        })}
                                      </div>
                                    ) : (
                                      <div className="text-xs text-muted-foreground">
                                        Elbow: {rm.elbow_angle_range[0].toFixed(0)}-{rm.elbow_angle_range[1].toFixed(0)}° | Tempo: {rm.tempo_ratio.toFixed(1)}:1
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Tips */}
                            {report.insights.length > 0 && (
                              <div className="bg-blue-500/5 border border-blue-500/10 rounded-lg p-4 space-y-2">
                                <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">Tips</h3>
                                {report.insights.map((insight, i) => (
                                  <div key={i} className="flex items-start gap-2 text-sm">
                                    <span className="text-blue-400 mt-0.5 shrink-0">&#9656;</span>
                                    <span className="text-muted-foreground">{insight}</span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Re-analyze button */}
                            <button
                              onClick={handleAnalyzeForm}
                              disabled={isAnalyzing}
                              className="w-full px-4 py-2 bg-muted text-muted-foreground rounded-lg hover:bg-muted/80 disabled:opacity-50 text-sm"
                            >
                              {isAnalyzing ? 'Re-analyzing...' : 'Re-analyze'}
                            </button>
                          </>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Rep Details table — below the two columns */}
                {hasAnalysis && report && report.rep_metrics && report.rep_metrics.length > 0 && (
                  <div className="mt-6">
                    <button
                      onClick={() => setShowRepDetails(!showRepDetails)}
                      className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-2"
                    >
                      <span className={`transition-transform ${showRepDetails ? 'rotate-90' : ''}`}>&#9656;</span>
                      Rep-by-Rep Details ({report.rep_metrics.length} rep{report.rep_metrics.length !== 1 ? 's' : ''})
                    </button>
                    {showRepDetails && (
                      <div className="bg-card rounded-lg shadow-lg overflow-hidden">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-muted">
                              <th className="text-left p-3 text-muted-foreground font-medium">Rep</th>
                              <th className="text-left p-3 text-muted-foreground font-medium">Grade</th>
                              <th className="text-left p-3 text-muted-foreground font-medium">Score</th>
                              <th className="text-left p-3 text-muted-foreground font-medium">Elbow Range</th>
                              <th className="text-left p-3 text-muted-foreground font-medium">Tempo</th>
                              <th className="text-left p-3 text-muted-foreground font-medium">Drift</th>
                              <th className="text-left p-3 text-muted-foreground font-medium">Sway</th>
                            </tr>
                          </thead>
                          <tbody>
                            {report.rep_metrics.map((rep) => (
                              <tr key={rep.rep_number} className="border-b border-muted/50">
                                <td className="p-3">{rep.rep_number}</td>
                                <td className="p-3">
                                  <span className={`font-bold ${gradeColor(rep.form_grade)}`}>{rep.form_grade}</span>
                                </td>
                                <td className="p-3">{rep.form_score?.toFixed(0)}%</td>
                                <td className="p-3">{Math.round(rep.elbow_angle_range[0])}°–{Math.round(rep.elbow_angle_range[1])}°</td>
                                <td className="p-3">{rep.tempo_ratio?.toFixed(1)}:1</td>
                                <td className="p-3">{rep.elbow_drift_pct?.toFixed(1)}%</td>
                                <td className="p-3">{rep.body_sway_pct?.toFixed(1)}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </>
            );
          })()}
        </div>
      </motion.div>
    </Layout>
  );
};

export default VideoPlayer;
