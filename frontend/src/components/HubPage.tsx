import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import Layout from "./Layout";

export interface HubLink {
  to: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
}

interface HubPageProps {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  primary: HubLink;
  secondary: HubLink[];
}

/**
 * Small landing "hub" for an analysis vertical (Lift / Bowl / Golf).
 * Leads with a single primary Upload CTA, then lists the vertical's
 * leaderboard / recent / challenge surfaces below.
 */
const HubPage: React.FC<HubPageProps> = ({ title, subtitle, icon, primary, secondary }) => {
  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-2xl mx-auto"
      >
        <div className="flex items-center gap-3 mb-2">
          <span className="text-accent">{icon}</span>
          <h1 className="text-3xl font-semibold">{title}</h1>
        </div>
        <p className="text-muted-foreground mb-8">{subtitle}</p>

        {/* Primary CTA — Upload */}
        <Link
          to={primary.to}
          className="group flex items-center justify-between w-full p-6 mb-8 rounded-2xl bg-accent text-accent-foreground shadow-sm hover:bg-accent/90 transition-colors"
        >
          <div className="flex items-center gap-4">
            <span>{primary.icon}</span>
            <div>
              <p className="text-lg font-semibold">{primary.label}</p>
              {primary.description && (
                <p className="text-sm text-accent-foreground/80">{primary.description}</p>
              )}
            </div>
          </div>
          <ArrowRight className="w-6 h-6 transition-transform group-hover:translate-x-1" />
        </Link>

        {/* Secondary surfaces */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {secondary.map((item) => (
            <Link
              key={item.to + item.label}
              to={item.to}
              className="glass p-5 rounded-xl hover:bg-secondary/40 transition-colors"
            >
              <div className="flex items-center gap-3 mb-1">
                {item.icon && <span className="text-accent">{item.icon}</span>}
                <p className="font-medium">{item.label}</p>
              </div>
              {item.description && (
                <p className="text-sm text-muted-foreground">{item.description}</p>
              )}
            </Link>
          ))}
        </div>
      </motion.div>
    </Layout>
  );
};

export default HubPage;
