import React, { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Dumbbell, Upload } from "lucide-react";
import axios from "axios";
import { Challenge, ChallengeLeaderboard, ChallengeLeaderboardRow, LiftingResult } from "../lib/types";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import { getChallengeLeaderboard, getLiftingResult, triggerLiftingAnalysis } from "../lib/api";
// VideoGallery replaced by inline unified lift feed
import { useToast } from "../components/ui/use-toast";
import { reportUploadError } from "../lib/telemetry";
import { uploadVideo } from "../lib/resumableUpload";
import { useUploadGuard } from "../lib/useUploadGuard";
import StatusPill from "../components/challenge/StatusPill";
import Podium from "../components/challenge/Podium";
import LeaderboardRow from "../components/challenge/LeaderboardRow";
import YouRow from "../components/challenge/YouRow";
import MomentumLine from "../components/challenge/MomentumLine";
import StandingCard from "../components/challenge/StandingCard";
import { scoreColumnLabel } from "../components/challenge/metric";
import { deriveStanding, ctaLabelFor } from "../lib/standing";

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
  const [leaderboard, setLeaderboard] = useState<ChallengeLeaderboard | null>(null);
  const [leaderboardError, setLeaderboardError] = useState<string | null>(null);
  const viewerId = typeof window !== "undefined" ? localStorage.getItem("userId") : null;

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

        // Refresh videos + leaderboard to show the new upload
        await fetchVideos();
        fetchLeaderboard();

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

  // Leaderboard is a separate fetch: its failure must not block the page (the
  // hero + upload CTA still render so the user can upload) — hence its own state.
  const fetchLeaderboard = async () => {
    try {
      const data = await getChallengeLeaderboard(id || "");
      setLeaderboard(data);
      setLeaderboardError(null);
    } catch (err: any) {
      console.error("Error fetching leaderboard:", err);
      setLeaderboardError(
        err.response?.data?.error || err.message || "Failed to load the leaderboard"
      );
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const userId = localStorage.getItem('userId');

        // Fire the leaderboard fetch alongside the challenge load.
        fetchLeaderboard();

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

  const openUpload = () => {
    setShowUpload(true);
    setTimeout(() => uploadRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  };

  // The video player route is keyed by attempt id, which each leaderboard row
  // now carries. Fall back to matching the row's clip URL against the fetched
  // lifts for responses cached from before attempt_id was added.
  const resolveClipHref = (row: ChallengeLeaderboardRow): string | null => {
    if (!row.clip_url) return null;
    if (row.attempt_id) {
      return `/challenges/${id}/participants/${row.user_id}/video/${row.attempt_id}`;
    }
    const mine = attempts.filter(
      (a: any) => String(a.participant_id) === String(row.user_id) && a.video_url
    );
    if (mine.length === 0) return null;
    const exact = mine.find((a: any) => a.video_url === row.clip_url);
    const chosen = exact || mine[0];
    return `/challenges/${id}/participants/${row.user_id}/video/${chosen.id}`;
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

  // Derive the viewer's standing once (drives the card, the "You" row subtitle,
  // and the goal-reframed CTA). Null when the viewer isn't entered.
  const standing = leaderboard ? deriveStanding(leaderboard, viewerId) : null;
  const uploadCta = leaderboard
    ? ctaLabelFor(standing, leaderboard.metric)
    : "Upload Lift";
  const heroDescription = challenge.description
    ? challenge.description.split(" - ")[0]
    : "";

  // Desktop-only hero date range, e.g. "May 9 – Jul 31, 2026" (#1b).
  const dateRange = (() => {
    const start = new Date(`${challenge.date}T00:00:00`);
    const end = new Date(`${challenge.registrationDeadline}T00:00:00`);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "";
    const md: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
    return `${start.toLocaleDateString(undefined, md)} – ${end.toLocaleDateString(
      undefined,
      { ...md, year: "numeric" },
    )}`;
  })();

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background pt-8 pb-28 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-xl lg:max-w-6xl mx-auto">
          {/* Hero */}
          <Link
            to="/challenges"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-5"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Challenges
          </Link>

          <div className="mb-6">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <StatusPill
                  status={challenge.status}
                  startDate={challenge.date}
                  endDate={challenge.registrationDeadline}
                />
                {dateRange && (
                  <span className="hidden text-[12.5px] font-medium text-white/45 lg:inline">
                    {dateRange}
                  </span>
                )}
              </div>
              {(challenge.status === "upcoming" || challenge.status === "ongoing") && (
                <button
                  onClick={handleUploadClick}
                  className="hidden sm:inline-flex flex-none items-center gap-2 rounded-lg bg-[#2f7bf6] px-4 py-2 font-medium text-white transition-colors hover:bg-blue-600 lg:gap-2.5 lg:rounded-xl lg:px-[22px] lg:py-3.5 lg:text-[15px] lg:shadow-[0_10px_26px_-6px_rgba(47,123,246,.7)]"
                >
                  <Upload className="w-4 h-4 lg:h-[18px] lg:w-[18px]" />
                  {uploadCta}
                </button>
              )}
            </div>
            <h1 className="mb-2 text-[27px] sm:text-4xl lg:text-[42px] lg:leading-[1.05] font-bold leading-tight tracking-tight">
              {challenge.title}
            </h1>
            {heroDescription && (
              <p className="text-sm text-muted-foreground lg:max-w-[560px] lg:text-[14.5px] lg:leading-relaxed">
                {heroDescription}
              </p>
            )}
            {leaderboard && (
              <MomentumLine rows={leaderboard.rows} momentum={leaderboard.momentum} />
            )}
          </div>

          {/* Leaderboard */}
          {(() => {
            if (leaderboardError && !leaderboard) {
              return (
                <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
                  <p className="mb-3">{leaderboardError}</p>
                  <button
                    onClick={fetchLeaderboard}
                    className="inline-flex items-center gap-2 rounded-lg border border-red-500/30 px-3 py-1.5 font-medium text-red-300 hover:bg-red-500/10"
                  >
                    Retry
                  </button>
                </div>
              );
            }
            if (!leaderboard) {
              return (
                <div className="flex items-center justify-center py-16">
                  <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-[#2f7bf6]" />
                </div>
              );
            }

            const { metric, rows } = leaderboard;
            const scoredRows = rows.filter((r) => r.score > 0);
            const podiumRows = scoredRows.slice(0, 3);
            const tableRows = rows.filter((r) => r.rank > 3);
            const viewerRow = viewerId
              ? rows.find((r) => String(r.user_id) === String(viewerId))
              : undefined;
            const viewerEntered = !!viewerRow;

            if (scoredRows.length === 0) {
              return (
                <div className="rounded-xl border border-white/[.07] bg-card p-8 text-center">
                  <Dumbbell className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
                  <p className="mb-4 text-muted-foreground">
                    No entries yet. Be the first on the podium!
                  </p>
                  {(challenge.status === "upcoming" || challenge.status === "ongoing") && (
                    <button
                      onClick={openUpload}
                      className="inline-flex items-center gap-2 rounded-lg bg-[#2f7bf6] px-4 py-2 font-medium text-white hover:bg-blue-600"
                    >
                      <Upload className="h-4 w-4" />
                      {uploadCta}
                    </button>
                  )}
                </div>
              );
            }

            const showTable = tableRows.length > 0 || !viewerEntered;

            return (
              <>
                {standing && <StandingCard standing={standing} metric={metric} />}

                <Podium rows={podiumRows} metric={metric} getClipHref={resolveClipHref} />

                {showTable && (
                  <div>
                    <div className="mb-2 flex items-center justify-between px-1 lg:mb-3">
                      <h2 className="text-sm font-semibold text-white/70 lg:text-base lg:text-white/85">
                        Everyone else
                      </h2>
                      <span className="text-[11px] font-semibold uppercase tracking-wide text-white/40 lg:hidden">
                        {scoreColumnLabel(metric)}
                      </span>
                    </div>
                    <div className="flex flex-col divide-y divide-white/[.06] overflow-hidden rounded-xl border border-white/[.07]">
                      {/* Desktop-only table header (#1b): RANK · ATHLETE · HOLD/TOTAL · CLIP. */}
                      <div
                        data-testid="leaderboard-header"
                        className="hidden bg-white/[.03] px-[18px] py-2.5 text-[11px] font-semibold uppercase tracking-[.04em] text-white/40 lg:grid lg:grid-cols-[52px_1fr_120px_90px] lg:gap-3.5"
                      >
                        <div>Rank</div>
                        <div>Athlete</div>
                        <div>{scoreColumnLabel(metric)}</div>
                        <div className="text-right">Clip</div>
                      </div>
                      {tableRows.map((row) =>
                        viewerEntered && String(row.user_id) === String(viewerId) ? (
                          <YouRow
                            key={row.user_id}
                            entered
                            row={row}
                            metric={metric}
                            clipHref={resolveClipHref(row)}
                            subtitle={standing?.goalSubtitle}
                          />
                        ) : (
                          <LeaderboardRow
                            key={row.user_id}
                            row={row}
                            metric={metric}
                            clipHref={resolveClipHref(row)}
                          />
                        )
                      )}
                      {!viewerEntered && <YouRow entered={false} onUpload={openUpload} />}
                    </div>
                  </div>
                )}
              </>
            );
          })()}

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

        {/* Mobile sticky CTA — opens the existing upload flow. */}
        {(challenge.status === "upcoming" || challenge.status === "ongoing") && (
          <div className="sm:hidden fixed inset-x-0 bottom-0 z-40 px-4 pb-6 pt-8 bg-gradient-to-t from-background via-background to-transparent">
            <button
              onClick={handleUploadClick}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#2f7bf6] py-4 font-semibold text-white shadow-[0_8px_22px_-6px_rgba(47,123,246,.7)]"
            >
              <Upload className="h-4 w-4" />
              {uploadCta}
            </button>
          </div>
        )}
      </motion.div>
    </Layout>
  );
};

export default ChallengeDetail;
