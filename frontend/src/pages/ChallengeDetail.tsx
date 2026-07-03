import React, { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Calendar, MapPin, Users, Dumbbell, CheckCircle2, Upload, Play } from "lucide-react";
import axios from "axios";
import { Challenge, LiftingResult } from "../lib/types";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import { getLiftingResult, triggerLiftingAnalysis } from "../lib/api";
// VideoGallery replaced by inline unified lift feed
import { useToast } from "../components/ui/use-toast";
import { reportUploadError } from "../lib/telemetry";
import { uploadVideo } from "../lib/resumableUpload";
import { useUploadGuard } from "../lib/useUploadGuard";

// Use the local API URL for competitions
const COMPETITIONS_API_URL = API_URL;

interface Attempt {
  id: string;
  participant_id: string;
  lift_type: string;
  weight: number;
  status: string;
  video_url: string | null;
  timestamp?: string;
}

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

function genderToCategories(gender: string | null | undefined): string[] {
  if (gender === 'F') return ['Women'];
  if (gender === 'M') return ['Men'];
  // 'MF', 'all', empty, or any other value => open to both
  return ['Men', 'Women'];
}

const ChallengeDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [videoData, setVideoData] = useState<VideoData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isJoining, setIsJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<any[]>([]);
  const [hasJoined, setHasJoined] = useState(false);
  const [selectedWeightClass, setSelectedWeightClass] = useState<string>("");
  const [challengeName, setChallengeName] = useState<string>("");
  const [showUpload, setShowUpload] = useState(false);
  const uploadRef = useRef<HTMLDivElement>(null);
  const [liftingResults, setLiftingResults] = useState<Record<string, LiftingResult>>({});

  // Upload form state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [liftType, setLiftType] = useState<string>("Squat");
  const [weight, setWeight] = useState<string>("60");
  const [email, setEmail] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Keep the device awake + warn before navigating away during an upload.
  useUploadGuard(isUploading);

  // Default weights for each lift type
  const defaultWeights: Record<string, string> = {
    "Squat": "60",
    "Bench": "40",
    "Deadlift": "80",
    "BicepCurl": "15"
  };

  // Handle file selection
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadError(null);
    }
  };

  // Handle lift type change
  const handleLiftTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLiftType = e.target.value;
    setLiftType(newLiftType);
    setWeight(defaultWeights[newLiftType] || "60");
  };

  // Handle video upload
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedFile) {
      setUploadError("Please select a video file");
      return;
    }

    if (!email) {
      setUploadError("Please enter your email address");
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setUploadError(null);

    try {
      // Direct-to-GCS via signed URL — bypasses Cloud Run's 32 MiB request cap
      // that was silently 413-ing large phone videos.
      const data = await uploadVideo(
        selectedFile,
        {
          competition_id: id || '1',
          lift_type: liftType,
          weight,
          email,
        },
        (pct) => setUploadProgress(pct)
      );

      if (data.url) {
        toast({
          title: "Upload Successful!",
          description: "Analyzing your form automatically...",
          duration: 5000,
        });

        // Reset form
        setSelectedFile(null);
        setUploadError(null);
        setShowUpload(false);

        // Refresh videos to show the new upload
        await fetchVideos();

        // Update hasJoined status
        setHasJoined(true);

        // Auto-trigger analysis for the new upload
        const attemptId = data.attempt_id;
        if (attemptId) {
          try {
            await triggerLiftingAnalysis(attemptId);
            // Poll until complete, then refresh results
            const pollInterval = setInterval(async () => {
              try {
                const result = await getLiftingResult(attemptId);
                if (result.processing_status === 'completed' || result.processing_status === 'failed') {
                  clearInterval(pollInterval);
                  setLiftingResults(prev => ({ ...prev, [attemptId]: result }));
                  const isPlank = result.report?.lift_type === 'plank';
                  toast({
                    title: isPlank
                      ? "Plank Analyzed"
                      : (result.report?.overall_grade && ['A','B','C','D'].includes(result.report.overall_grade)
                          ? "Lift Approved!" : "Analysis Complete"),
                    description: isPlank
                      ? `Held: ${result.report?.total_in_plank_s?.toFixed(1)}s (form ${((result.report?.overall_form_score ?? 0) * 100).toFixed(0)}%)`
                      : (result.report
                          ? `Grade: ${result.report.overall_grade} (${result.report.overall_score?.toFixed(0)}%)`
                          : "Check your lift for details."),
                    duration: 5000,
                  });
                }
              } catch { /* continue polling */ }
            }, 3000);
          } catch (err) {
            console.error("Auto-analyze failed:", err);
          }
        }
      }
    } catch (err: any) {
      console.error("Upload error:", err);
      reportUploadError("ChallengeDetail", selectedFile, err, {
        liftType,
        competitionId: id || "1",
      });
      let errorMsg = "Upload failed. Please try again.";
      if (err.response?.data?.error) {
        errorMsg = err.response.data.error;
      }
      setUploadError(errorMsg);
    } finally {
      setIsUploading(false);
    }
  };

  // Fetch lifting analysis results for all videos
  const fetchLiftingResults = async (videos: VideoData[]) => {
    const results: Record<string, LiftingResult> = {};
    await Promise.all(
      videos.map(async (v) => {
        try {
          const result = await getLiftingResult(v.attempt_id);
          if (result && result.processing_status === 'completed') {
            results[v.attempt_id] = result;
          }
        } catch { /* no result yet */ }
      })
    );
    setLiftingResults(results);
  };

  // Function to fetch videos - can be called to refresh after deletion
  const fetchVideos = async () => {
    try {
      const liftsResponse = await axios.get(`${COMPETITIONS_API_URL}/competitions/${id}/lifts`);
      const liftsDataBackend = liftsResponse.data.lifts || [];

      setAttempts(liftsDataBackend);

      const processedVideoData: VideoData[] = liftsDataBackend
        .filter((lift: any) => lift.video_url)
        .map((lift: any) => ({
          attempt_id: lift.id.toString(),
          user_id: lift.participant_id,
          lift_type: lift.lift_type,
          weight: lift.weight,
          status: lift.status,
          video_url: lift.video_url,
          created_at: lift.created_at || new Date().toISOString(),
          competition_id: id || '',
          competition_name: challengeName
        }));

      setVideoData(processedVideoData);
      fetchLiftingResults(processedVideoData);
      console.log("Refreshed video data:", processedVideoData);
    } catch (err) {
      console.error("Error fetching videos:", err);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const userId = localStorage.getItem('userId');

        // Fetch challenge, participants, and check if user has joined
        const [challengeData, participantsData, liftsData] = await Promise.all([
          axios.get(`${COMPETITIONS_API_URL}/competitions/${id}`),
          axios.get(`${COMPETITIONS_API_URL}/competitions/${id}/participants`),
          axios.get(`${COMPETITIONS_API_URL}/competitions/${id}/lifts`)
        ]);

        const backendData = challengeData.data.competition;
        const participantsDataBackend = participantsData.data.participants || [];
        const liftsDataBackend = liftsData.data.lifts || [];

        // Store challenge name for video refresh
        setChallengeName(backendData.name);

        // Store the lifts/attempts with full data including video URLs
        setAttempts(liftsDataBackend);

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
            created_at: lift.created_at || new Date().toISOString(),
            competition_id: id || '',
            competition_name: backendData.name
          }));

        setVideoData(processedVideoData);
        fetchLiftingResults(processedVideoData);

        // Debug logging
        console.log("Processed video data:", processedVideoData);

        setParticipants(participantsDataBackend);

        // Check if the current user has already joined
        if (userId) {
          const hasUserJoined = participantsDataBackend.some((p: any) => p.id === userId);
          setHasJoined(hasUserJoined);
        }

        // Transform backend data to match frontend Challenge type
        const transformedChallenge: Challenge = {
          id: backendData.id,
          title: backendData.name,
          date: backendData.start_date,
          registrationDeadline: backendData.end_date,
          location: backendData.location || (backendData.description ? backendData.description.split(' - ')[0] : ""),
          description: backendData.description || "",
          status: determineStatus(backendData.start_date, backendData.end_date),
          categories: [],
          participants: participantsDataBackend.length
        };

        // Add categories from metadata fields if available
        if (backendData.lifttypes || backendData.weightclasses || backendData.gender) {
          const categories = [
            ...(backendData.lifttypes || []),
            ...(backendData.weightclasses || []),
            ...genderToCategories(backendData.gender),
          ];
          transformedChallenge.categories = categories;
        }
        // Otherwise try to parse metadata from description field if it exists
        else if (backendData.description && backendData.description.includes(' - ')) {
          try {
            // Extract the JSON part from the description
            const metadataString = backendData.description.split(' - ')[1];
            const metadata = JSON.parse(metadataString);

            // Add categories from metadata
            const categories = [
              ...(metadata.lifttypes || []),
              ...(metadata.weightclasses || []),
              ...genderToCategories(metadata.gender),
            ];

            transformedChallenge.categories = categories;
          } catch (err) {
            console.warn('Failed to parse competition metadata from description', err);
            // Use empty categories if parsing fails
            transformedChallenge.categories = [];
          }
        }

        setChallenge(transformedChallenge);
      } catch (err: any) {
        console.error("Error fetching data:", err);
        console.error("Error details:", {
          message: err.message,
          response: err.response?.data,
          status: err.response?.status,
          url: `${COMPETITIONS_API_URL}/competitions/${id}`
        });
        setError(
          err.response?.data?.error ||
          err.message ||
          "Failed to load challenge details"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  useEffect(() => {
    if (challenge?.categories) {
      const weightClasses = challenge.categories.filter(cat => cat.includes('kg'));
      if (weightClasses.length > 0) {
        setSelectedWeightClass(weightClasses[0]);
      }
      // Auto-select the challenge's lift type if the form's current selection isn't allowed.
      const allowedDbValues = challenge.categories.filter(
        c => !c.includes('kg') && c !== 'Men' && c !== 'Women'
      );
      const dbToFormId: Record<string, string> = {
        'Squat': 'Squat',
        'Bench Press': 'Bench',
        'Deadlift': 'Deadlift',
        'Bicep Curl': 'BicepCurl',
        'Plank': 'Plank',
      };
      const allowedFormIds = allowedDbValues.map(d => dbToFormId[d]).filter(Boolean);
      if (allowedFormIds.length > 0 && !allowedFormIds.includes(liftType)) {
        setLiftType(allowedFormIds[0]);
        setWeight(defaultWeights[allowedFormIds[0]] || "60");
      }
    }
  }, [challenge]);

  const determineStatus = (startDate: string, endDate: string): "upcoming" | "ongoing" | "completed" => {
    const now = new Date();
    const start = new Date(startDate);
    const end = new Date(endDate);

    if (now < start) return "upcoming";
    if (now > end) return "completed";
    return "ongoing";
  };

  const handleJoinChallenge = async () => {
    try {
      setIsJoining(true);
      setJoinError(null);

      const userId = localStorage.getItem('userId');
      if (!userId) {
        setJoinError('Please create a profile before joining a challenge');
        return;
      }

      // Get appropriate weight class and gender from challenge metadata if available
      let weightClass = selectedWeightClass || "83kg"; // Use selected or default
      let gender = "male"; // Default to male instead of "M"

      if (challenge?.categories && challenge.categories.length > 0) {
        // Set gender based on whether 'Women' is in the categories
        if (challenge.categories.includes('Women')) {
          gender = "female"; // Use female instead of "F"
        }
      }

      await axios.post(
        `${COMPETITIONS_API_URL}/join_competition`,
        {
          user_id: userId,
          competition_id: id,
          weight_class: weightClass,
          gender: gender
        }
      );

      // Fetch updated participants count
      const participantsResponse = await axios.get(`${COMPETITIONS_API_URL}/competitions/${id}/participants`);
      const participantsData = participantsResponse.data.participants || [];

      // Update the challenge with the new participants count
      if (challenge) {
        setChallenge({
          ...challenge,
          participants: participantsData.length
        });
      }

      // Update hasJoined state
      setHasJoined(true);
      setParticipants(participantsData);
    } catch (err: any) {
      console.error("Error joining challenge:", err);
      setJoinError(err.response?.data?.error || "Failed to join challenge. Please try again.");
    } finally {
      setIsJoining(false);
    }
  };

  const handleUploadClick = () => {
    setShowUpload((prev) => !prev);
    if (!showUpload) {
      setTimeout(() => {
        uploadRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
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

  if (!challenge) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <div className="text-center">
              <h2 className="text-2xl font-bold">Challenge not found</h2>
              <Link to="/challenges" className="text-primary hover:underline mt-4 inline-block">
                Return to Challenges
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
        <div className="max-w-5xl mx-auto">
          <Link
            to="/challenges"
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Challenges
          </Link>

          <div className="bg-card rounded-lg shadow-lg overflow-hidden mb-8">
            <div className="p-6 sm:p-8">
              {/* Header: title + status + upload button */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4">
                <div className="flex items-center gap-3 mb-2 sm:mb-0">
                  <h1 className="text-3xl font-bold">{challenge.title}</h1>
                  <span
                    className={`px-3 py-1.5 rounded-full text-sm font-medium ${
                      challenge.status === "upcoming"
                        ? "bg-blue-500/10 text-blue-500"
                        : challenge.status === "ongoing"
                        ? "bg-green-500/10 text-green-500"
                        : "bg-gray-500/10 text-gray-500"
                    }`}
                  >
                    {challenge.status.charAt(0).toUpperCase() + challenge.status.slice(1)}
                  </span>
                  {hasJoined && (
                    <div className="flex items-center gap-1 bg-green-500/10 text-green-500 px-3 py-1.5 rounded-full text-sm font-medium">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Joined</span>
                    </div>
                  )}
                </div>
                {(challenge.status === "upcoming" || challenge.status === "ongoing") && (
                  <button
                    onClick={handleUploadClick}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 transition-colors"
                  >
                    <Upload className="w-4 h-4" />
                    Upload Lift
                  </button>
                )}
              </div>

              {challenge.status === "completed" && (
                <div className="mb-4 text-center text-muted-foreground p-3 bg-gray-100 rounded-lg text-sm">
                  This challenge has ended
                </div>
              )}

              {/* Metadata row */}
              <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground mb-4">
                <div className="flex items-center gap-1">
                  <Calendar size={14} />
                  <span>{new Date(challenge.date).toLocaleDateString()} &mdash; {new Date(challenge.registrationDeadline).toLocaleDateString()}</span>
                </div>
                {challenge.location && (
                  <div className="flex items-center gap-1">
                    <MapPin size={14} />
                    <span>{challenge.location}</span>
                  </div>
                )}
                <div className="flex items-center gap-1">
                  <Users size={14} />
                  <span>{challenge.participants} participants</span>
                </div>
              </div>

              {/* Tags: lift types prominent, weight classes compact */}
              {challenge.categories.length > 0 && (() => {
                const liftTypes = challenge.categories.filter(c => !c.includes('kg') && c !== 'Men' && c !== 'Women');
                const weightClasses = challenge.categories.filter(c => c.includes('kg'));
                const genders = challenge.categories.filter(c => c === 'Men' || c === 'Women');
                return (
                  <div className="mb-6 space-y-2">
                    <div className="flex flex-wrap gap-2">
                      {liftTypes.map((tag) => (
                        <span key={tag} className="px-3 py-1 rounded-full text-sm bg-primary/10 text-primary">{tag}</span>
                      ))}
                      {genders.map((tag) => (
                        <span key={tag} className="px-3 py-1 rounded-full text-sm bg-purple-500/10 text-purple-500">{tag}</span>
                      ))}
                    </div>
                    {weightClasses.length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        Weight classes: {weightClasses.join(', ')}
                      </p>
                    )}
                  </div>
                );
              })()}

            </div>
          </div>

          {/* Unified Lift Feed */}
          <div className="mt-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Dumbbell className="mr-2" size={20} />
              Lifts ({videoData.length})
            </h2>

            {videoData.length > 0 ? (
              <div className="space-y-3">
                {videoData
                  .sort((a, b) => b.weight - a.weight)
                  .map((video) => {
                    // Find participant name for this lift
                    const participant = participants.find((p: any) => p.id === video.user_id);
                    const participantName = participant?.name || 'Unknown';

                    return (
                      <Link
                        key={video.attempt_id}
                        to={`/challenges/${id}/participants/${video.user_id}/video/${video.attempt_id}`}
                        className="flex items-center gap-4 bg-card rounded-lg shadow hover:shadow-lg transition-shadow p-4 group"
                      >
                        {/* Video thumbnail */}
                        <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-lg bg-black overflow-hidden shrink-0 relative">
                          <video
                            src={video.video_url}
                            muted
                            playsInline
                            preload="metadata"
                            className="w-full h-full object-cover"
                            onLoadedData={(e) => { (e.target as HTMLVideoElement).currentTime = 0.5; }}
                          />
                          <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/30 transition-colors">
                            <div className="w-8 h-8 rounded-full bg-white/90 flex items-center justify-center">
                              <Play className="w-4 h-4 text-primary ml-0.5" fill="currentColor" />
                            </div>
                          </div>
                        </div>

                        {/* Lift info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <h3 className="font-semibold truncate">{participantName}</h3>
                            {video.lift_type?.toLowerCase() !== 'plank' && video.weight ? (
                              <span className="text-lg font-bold text-primary ml-2 shrink-0">{video.weight} lbs</span>
                            ) : null}
                          </div>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <span>{video.lift_type}</span>
                            <span>&middot;</span>
                            <span>{new Date(video.created_at).toLocaleDateString()}</span>
                          </div>
                          <div className="mt-1">
                            {(() => {
                              const lr = liftingResults[video.attempt_id];
                              const report = lr?.report;
                              if (report?.lift_type === 'plank') {
                                const heldS = report.total_in_plank_s ?? 0;
                                return (
                                  <span className="inline-block px-2 py-0.5 rounded-full text-xs bg-blue-500/10 text-blue-500">
                                    Held {heldS.toFixed(1)}s
                                  </span>
                                );
                              }
                              const grade = report?.overall_grade;
                              const isApproved = grade && ['A', 'B', 'C', 'D'].includes(grade);
                              const isFailed = grade === 'F';
                              const badgeClass = isApproved ? 'bg-green-500/10 text-green-500' :
                                                 isFailed ? 'bg-red-500/10 text-red-500' :
                                                 'bg-yellow-500/10 text-yellow-500';
                              const badgeText = isApproved ? `Approved (${grade})` :
                                                isFailed ? 'Failed' : 'Pending';
                              return (
                                <span className={`inline-block px-2 py-0.5 rounded-full text-xs ${badgeClass}`}>
                                  {badgeText}
                                </span>
                              );
                            })()}
                          </div>
                        </div>
                      </Link>
                    );
                  })}
              </div>
            ) : (
              <div className="bg-card rounded-lg shadow p-8 text-center">
                <Dumbbell className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground mb-4">No lifts uploaded yet. Be the first!</p>
                <button
                  onClick={() => { setShowUpload(true); setTimeout(() => uploadRef.current?.scrollIntoView({ behavior: 'smooth' }), 100); }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600"
                >
                  <Upload className="w-4 h-4" />
                  Upload Lift
                </button>
              </div>
            )}
          </div>

          {/* Upload form - toggled via header button */}
          {showUpload && (challenge.status === "upcoming" || challenge.status === "ongoing") && (
            <div ref={uploadRef} className="mt-8 bg-blue-500/5 rounded-lg p-6 border border-blue-500/10">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Upload className="w-5 h-5 text-blue-500" />
                </div>
                <h2 className="text-xl font-semibold">Upload Your Lift</h2>
              </div>

              <form onSubmit={handleUploadSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Your Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your email"
                    required
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                {(() => {
                  const ALL_LIFT_OPTIONS: { id: string; label: string; dbValue: string }[] = [
                    { id: 'Squat', label: 'Squat', dbValue: 'Squat' },
                    { id: 'Bench', label: 'Bench Press', dbValue: 'Bench Press' },
                    { id: 'Deadlift', label: 'Deadlift', dbValue: 'Deadlift' },
                    { id: 'BicepCurl', label: 'Bicep Curl', dbValue: 'Bicep Curl' },
                    { id: 'Plank', label: 'Plank', dbValue: 'Plank' },
                  ];
                  const challengeLiftDbValues = (challenge?.categories || []).filter(
                    c => !c.includes('kg') && c !== 'Men' && c !== 'Women'
                  );
                  const liftOptions = challengeLiftDbValues.length > 0
                    ? ALL_LIFT_OPTIONS.filter(o => challengeLiftDbValues.includes(o.dbValue))
                    : ALL_LIFT_OPTIONS;
                  const onlyOne = liftOptions.length === 1;
                  return (
                    <div className={liftType === 'Plank' ? '' : 'grid grid-cols-1 sm:grid-cols-2 gap-4'}>
                      <div>
                        <label className="block text-sm font-medium mb-1">Lift Type</label>
                        {onlyOne ? (
                          <div className="w-full px-3 py-2 bg-muted/40 border border-input rounded-lg text-foreground">
                            {liftOptions[0].label}
                          </div>
                        ) : (
                          <select
                            value={liftType}
                            onChange={handleLiftTypeChange}
                            className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                          >
                            {liftOptions.map(opt => (
                              <option key={opt.id} value={opt.id}>{opt.label}</option>
                            ))}
                          </select>
                        )}
                      </div>

                      {liftType !== 'Plank' && (
                        <div>
                          <label className="block text-sm font-medium mb-1">Weight (lbs)</label>
                          <input
                            type="number"
                            value={weight}
                            onChange={(e) => setWeight(e.target.value)}
                            placeholder="Enter weight"
                            min="1"
                            className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                          />
                        </div>
                      )}
                    </div>
                  );
                })()}

                <div>
                  <label className="block text-sm font-medium mb-1">Video</label>
                  <div className="border-2 border-dashed border-input rounded-lg p-4 text-center hover:border-primary/50 transition-colors">
                    <input
                      type="file"
                      accept="video/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="challenge-video-upload"
                    />
                    <label
                      htmlFor="challenge-video-upload"
                      className="cursor-pointer flex flex-col items-center"
                    >
                      <Dumbbell className="w-6 h-6 text-muted-foreground mb-2" />
                      <span className="text-sm text-muted-foreground">
                        {selectedFile ? selectedFile.name : "Click to select a video file"}
                      </span>
                    </label>
                  </div>
                </div>

                {uploadError && (
                  <div className="text-red-500 text-sm">{uploadError}</div>
                )}

                {isUploading && (
                  <div className="space-y-1">
                    <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-blue-500 transition-all duration-200"
                        style={{ width: `${uploadProgress >= 100 ? 100 : uploadProgress}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground text-center">
                      {uploadProgress < 100
                        ? `Uploading ${uploadProgress}% — keep this page open`
                        : 'Finishing up…'}
                    </p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isUploading || !selectedFile}
                  className={`w-full py-3 px-4 rounded-lg bg-blue-500 text-white font-medium
                    shadow-sm transition-all hover:bg-blue-600 hover:shadow
                    ${(isUploading || !selectedFile) ? 'opacity-50 cursor-not-allowed' : 'hover:translate-y-[-1px]'}`}
                >
                  {isUploading
                    ? (uploadProgress < 100 ? `Uploading ${uploadProgress}%` : 'Finishing up…')
                    : 'Upload Video'}
                </button>
              </form>
            </div>
          )}
        </div>
      </motion.div>
    </Layout>
  );
};

export default ChallengeDetail;
