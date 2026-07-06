import { lazy } from "react";
import { RouteObject } from "react-router-dom";
import { Navigate, useParams } from "react-router-dom";
import ShortLinkRedirect from "../pages/ShortLinkRedirect";

const Index = lazy(() => import("../pages/Index"));
const Challenges = lazy(() => import("../pages/Challenges"));
const Athletes = lazy(() => import("../pages/Athletes"));
const About = lazy(() => import("../pages/About"));
const ChallengeDetail = lazy(() => import("../pages/ChallengeDetail"));
const ChallengeVideos = lazy(() => import("../pages/ChallengeVideos"));
const VideoPlayer = lazy(() => import("../pages/VideoPlayer"));
const UploadVideo = lazy(() => import("../pages/UploadVideo"));
const NotFound = lazy(() => import("../pages/NotFound"));
const Leaderboard = lazy(() => import("../pages/Leaderboard"));
const Store = lazy(() => import("../pages/Store"));
const Profile = lazy(() => import("../pages/Profile"));
const WeeklyLifts = lazy(() => import("../pages/WeeklyLifts"));
const AuthCallback = lazy(() => import("../pages/AuthCallback"));
const AuthError = lazy(() => import("../pages/AuthError"));
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
const Terms = lazy(() => import("../pages/Terms"));
const Privacy = lazy(() => import("../pages/Privacy"));

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
  { path: "/upload", element: <UploadVideo /> },
  {
    path: "/challenges/:id/participants/:participantId/video/:videoId",
    element: <VideoPlayer />,
  },
  { path: "/video-player/:id/:participantId/:videoId", element: <VideoPlayerRedirect /> },
  { path: "/s/:code", element: <ShortLinkRedirect /> },
  { path: "/athletes", element: <Athletes /> },
  { path: "/about", element: <About /> },
  { path: "/leaderboard", element: <Leaderboard /> },
  { path: "/store", element: <Store /> },
  { path: "/profile", element: <Profile /> },
  { path: "/profile/:id", element: <Profile /> },
  { path: "/profile/:id/weekly-lifts", element: <WeeklyLifts /> },
  { path: "/auth/callback", element: <AuthCallback /> },
  { path: "/auth/error", element: <AuthError /> },
  { path: "/bowling/upload", element: <BowlingUpload /> },
  { path: "/bowling/upload/:competitionId", element: <BowlingUpload /> },
  { path: "/bowling/result/:attemptId", element: <BowlingResult /> },
  { path: "/bowling/result/:attemptId/annotate", element: <AnnotationWorkspace /> },
  { path: "/bowling/challenge/:id", element: <BowlingChallenge /> },
  { path: "/golf/upload", element: <GolfUpload /> },
  { path: "/golf/review/:roundId", element: <GolfReview /> },
  { path: "/golf/round/:roundId", element: <GolfRound /> },
  { path: "/golf/profile", element: <GolfProfile /> },
  { path: "/golf/profile/:userId", element: <GolfProfile /> },
  { path: "/golf/leaderboard", element: <GolfLeaderboard /> },
  { path: "/feedback", element: <FileTicket /> },
  { path: "/feedback/list", element: <TicketList /> },
  { path: "/terms", element: <Terms /> },
  { path: "/privacy", element: <Privacy /> },
  { path: "*", element: <NotFound /> },
];
