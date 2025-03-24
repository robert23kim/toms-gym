
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Competitions from "./pages/Competitions";
import Athletes from "./pages/Athletes";
import About from "./pages/About";
import CompetitionDetail from "./pages/CompetitionDetail";
import VideoPlayer from "./pages/VideoPlayer";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/competitions" element={<Competitions />} />
          <Route path="/athletes" element={<Athletes />} />
          <Route path="/about" element={<About />} />
          <Route path="/competitions/:id" element={<CompetitionDetail />} />
          <Route path="/competitions/:competitionId/participants/:participantId/video" element={<VideoPlayer />} />
          <Route path="/competitions/:competitionId/participants/:participantId/video/:liftId" element={<VideoPlayer />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;

