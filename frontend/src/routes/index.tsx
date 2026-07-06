import { lazy } from "react";
import { RouteObject } from "react-router-dom";
import { Navigate, useParams } from "react-router-dom";
import ShortLinkRedirect from "../pages/ShortLinkRedirect";

const Index = lazy(() => import("../pages/Index"));
const Challenges = lazy(() => import("../pages/Challenges"));
const About = lazy(() => import("../pages/About"));
const ChallengeDetail = lazy(() => import("../pages/ChallengeDetail"));
const ChallengeVideos = lazy(() => import("../pages/ChallengeVideos"));
const VideoPlayer = lazy(() => import("../pages/VideoPlayer"));
const UploadVideo = lazy(() => import("../pages/UploadVideo"));
// T7 unified upload chooser — /upload now asks "what are you analyzing?"
const UploadChooser = lazy(() => import("../pages/UploadChooser"));
const NotFound = lazy(() => import("../pages/NotFound"));
const Leaderboard = lazy(() => import("../pages/Leaderboard"));
const Store = lazy(() => import("../pages/Store"));
const Profile = lazy(() => import("../pages/Profile"));
const WeeklyLifts = lazy(() => import("../pages/WeeklyLifts"));
const AuthCallback = lazy(() => import("../pages/AuthCallback"));
const AuthError = lazy(() => import("../pages/AuthError"));
// T15 passwordless magic-link sign-in
const SignIn = lazy(() => import("../pages/SignIn"));
const MagicLink = lazy(() => import("../pages/MagicLink"));
const BowlingUpload = lazy(() => import("../pages/BowlingUpload"));
const BowlingResult = lazy(() => import("../pages/BowlingResult"));
const BowlingChallenge = lazy(() => import("../pages/BowlingChallenge"));
const AnnotationWorkspace = lazy(() => import("../pages/AnnotationWorkspace"));
const GolfUpload = lazy(() => import("../pages/GolfUpload"));
const GolfReview = lazy(() => import("../pages/GolfReview"));
const GolfRound = lazy(() => import("../pages/GolfRound"));
const GolfProfile = lazy(() => import("../pages/GolfProfile"));
const GolfLeaderboard = lazy(() => import("../pages/GolfLeaderboard"));
const FileTicket = lazy(() => import("../pages/FileTicket"));
const TicketList = lazy(() => import("../pages/TicketList"));
// T5 nav restructure — Lift / Bowl / Golf vertical hub pages
const LiftHub = lazy(() => import("../pages/LiftHub"));
const BowlHub = lazy(() => import("../pages/BowlHub"));
const GolfHub = lazy(() => import("../pages/GolfHub"));
const Terms = lazy(() => import("../pages/Terms"));
const Privacy = lazy(() => import("../pages/Privacy"));
// T8 — post-upload status page (shared component, one route per analysis kind)
const AnalysisStatus = lazy(() => import("../pages/AnalysisStatus"));

// Redirect component for backward compatibility
const VideoPlayerRedirect = () => {
  const { id, participantId, videoId } = useParams();
  return <Navigate to={`/challenges/${id}/participants/${participantId}/video/${videoId}`} replace />;
};

export const routes: RouteObject[] = [
  { path: "/", element: <Index /> },
  { path: "/challenges", element: <Challenges /> },
  { path: "/challenges/:id", element: <ChallengeDetail /> },
  { path: "/challenges/:id/videos", element: <ChallengeVideos /> },
  { path: "/challenges/:id/upload", element: <UploadVideo /> },
  // T7 unified upload chooser: /upload is the sport chooser; lifting upload
  // moved to /lift/upload. /upload/lift kept as a redirect for old deep links.
  { path: "/upload", element: <UploadChooser /> },
  { path: "/lift/upload", element: <UploadVideo /> },
  { path: "/upload/lift", element: <Navigate to="/lift/upload" replace /> },
  {
    path: "/challenges/:id/participants/:participantId/video/:videoId",
    element: <VideoPlayer />,
  },
  { path: "/video-player/:id/:participantId/:videoId", element: <VideoPlayerRedirect /> },
  { path: "/s/:code", element: <ShortLinkRedirect /> },
  { path: "/about", element: <About /> },
  { path: "/leaderboard", element: <Leaderboard /> },
  { path: "/store", element: <Store /> },
  { path: "/profile", element: <Profile /> },
  { path: "/profile/:id", element: <Profile /> },
  { path: "/profile/:id/weekly-lifts", element: <WeeklyLifts /> },
  { path: "/auth/callback", element: <AuthCallback /> },
  { path: "/auth/error", element: <AuthError /> },
  // T15 passwordless magic-link sign-in — request a link, then consume it.
  { path: "/signin", element: <SignIn /> },
  { path: "/auth/magic/:token", element: <MagicLink /> },
  { path: "/bowling/upload", element: <BowlingUpload /> },
  { path: "/bowling/upload/:competitionId", element: <BowlingUpload /> },
  { path: "/bowling/result/:attemptId", element: <BowlingResult /> },
  // T8 — post-upload analysis status pages (poll existing per-attempt result
  // endpoints; survive reload via the attemptId in the URL)
  { path: "/lift/status/:attemptId", element: <AnalysisStatus kind="lifting" /> },
  { path: "/bowling/status/:attemptId", element: <AnalysisStatus kind="bowling" /> },
  { path: "/bowling/result/:attemptId/annotate", element: <AnnotationWorkspace /> },
  { path: "/bowling/challenge/:id", element: <BowlingChallenge /> },
  { path: "/golf/upload", element: <GolfUpload /> },
  { path: "/golf/review/:roundId", element: <GolfReview /> },
  { path: "/golf/round/:roundId", element: <GolfRound /> },
  { path: "/golf/profile", element: <GolfProfile /> },
  { path: "/golf/profile/:userId", element: <GolfProfile /> },
  { path: "/golf/leaderboard", element: <GolfLeaderboard /> },
  // T5 nav restructure — Lift / Bowl / Golf hub landing pages (primary nav)
  { path: "/lift", element: <LiftHub /> },
  { path: "/bowl", element: <BowlHub /> },
  { path: "/golf", element: <GolfHub /> },
  { path: "/feedback", element: <FileTicket /> },
  { path: "/feedback/list", element: <TicketList /> },
  { path: "/terms", element: <Terms /> },
  { path: "/privacy", element: <Privacy /> },
  { path: "*", element: <NotFound /> },
];
