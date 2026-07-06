import React from "react";
import { Link } from "react-router-dom";
import Navbar from "./Navbar";
import AmbientBackground from "./AmbientBackground";
import { motion } from "framer-motion";
import { Bug } from "lucide-react";
import { APP_VERSION } from "../config";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <AmbientBackground />
      <Navbar />
      <motion.main 
        className="flex-1 px-4 py-6 md:px-6 lg:px-8 max-w-7xl mx-auto w-full"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        {children}
      </motion.main>
      <footer className="py-6 px-4 border-t border-border/40 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-sm text-muted-foreground">
          <Link to="/feedback" className="inline-flex items-center gap-1.5 hover:text-foreground transition-colors">
            <Bug className="w-3.5 h-3.5" />
            Report a bug
          </Link>
          <span aria-hidden="true">·</span>
          <Link to="/feedback" className="hover:text-foreground transition-colors">
            Request a feature
          </Link>
          <span aria-hidden="true">·</span>
          <Link to="/terms" className="hover:text-foreground transition-colors">
            Terms
          </Link>
          <span aria-hidden="true">·</span>
          <Link to="/privacy" className="hover:text-foreground transition-colors">
            Privacy
          </Link>
          <span className="text-xs text-muted-foreground/60" title="Frontend build">
            v{APP_VERSION}
          </span>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
