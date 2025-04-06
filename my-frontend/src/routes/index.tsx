import { RouteObject } from "react-router-dom";
import Index from "../pages/Index";
import Challenges from "../pages/Challenges";
import Athletes from "../pages/Athletes";
import About from "../pages/About";
import ChallengeDetail from "../pages/ChallengeDetail";
import VideoPlayer from "../pages/VideoPlayer";
import UploadVideo from "../pages/UploadVideo";
import NotFound from "../pages/NotFound";
import Leaderboard from "../pages/Leaderboard";
import Store from '../pages/Store';
import Profile from "../pages/Profile";
import RandomVideo from "../pages/RandomVideo";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Index />,
  },
  {
    path: "/challenges",
    element: <Challenges />,
  },
  {
    path: "/challenges/:id",
    element: <ChallengeDetail />,
  },
  {
    path: "/challenges/:id/upload",
    element: <UploadVideo />,
  },
  {
    path: "/upload",
    element: <UploadVideo />,
  },
  {
    path: "/challenges/:id/participants/:participantId/video/:videoId",
    element: <VideoPlayer />,
  },
  {
    path: "/random-video",
    element: <RandomVideo />,
  },
  {
    path: "/athletes",
    element: <Athletes />,
  },
  {
    path: "/about",
    element: <About />,
  },
  {
    path: "/leaderboard",
    element: <Leaderboard />,
  },
  {
    path: "/store",
    element: <Store />,
  },
  {
    path: "/profile",
    element: <Profile />,
  },
  {
    path: "*",
    element: <NotFound />,
  },
]; 