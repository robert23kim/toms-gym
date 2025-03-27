import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { useEffect } from "react";
import Index from "./pages/Index";
import Competitions from "./pages/Competitions";
import Athletes from "./pages/Athletes";
import About from "./pages/About";
import CompetitionDetail from "./pages/CompetitionDetail";
import VideoPlayer from "./pages/VideoPlayer";
import NotFound from "./pages/NotFound";
import Leaderboard from "./pages/Leaderboard";
import Store from './pages/Store';
import Profile from "./pages/Profile";

const queryClient = new QueryClient();

const TitleUpdater = () => {
  const location = useLocation();

  useEffect(() => {
    const getTitle = () => {
      const path = location.pathname;
      const baseTitle = "Tom's Gym";
      
      if (path === "/") return baseTitle;
      const pageName = path.split("/")[1];
      if (!pageName) return baseTitle;
      
      return `${pageName.charAt(0).toUpperCase() + pageName.slice(1)} | ${baseTitle}`;
    };

    document.title = getTitle();
  }, [location]);

  return null;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <TitleUpdater />
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/competitions" element={<Competitions />} />
          <Route path="/athletes" element={<Athletes />} />
          <Route path="/about" element={<About />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/store" element={<Store />} />
          <Route path="/competitions/:id" element={<CompetitionDetail />} />
          <Route path="/competitions/:competitionId/participants/:participantId/video" element={<VideoPlayer />} />
          <Route path="/competitions/:competitionId/participants/:participantId/video/:liftId" element={<VideoPlayer />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/profile/:id" element={<Profile />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;

