import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { routes } from "./routes";
import { AuthProvider } from "./auth/AuthContext";

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

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <TitleUpdater />
          <TooltipProvider>
            <Routes>
              {routes.map((route, index) => (
                <Route key={index} path={route.path} element={route.element} />
              ))}
            </Routes>
            <Toaster />
            <Sonner />
          </TooltipProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;

