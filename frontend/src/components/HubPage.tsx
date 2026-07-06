import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import Layout from "./Layout";
import RowCard from "./RowCard";

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
        className="max-w-2xl mx-auto text-center py-6"
      >
        <div className="flex flex-col items-center gap-2 mb-2">
          <span className="w-14 h-14 rounded-2xl bg-accent/10 text-accent grid place-items-center">
            {icon}
          </span>
          <h1 className="text-3xl font-semibold">{title}</h1>
        </div>
        <p className="text-muted-foreground mb-8 max-w-md mx-auto">{subtitle}</p>

        {/* Primary CTA — Upload */}
        <Link
          to={primary.to}
          className="group flex items-center justify-between w-full p-6 mb-8 rounded-2xl bg-accent text-accent-foreground shadow-sm hover:bg-accent/90 transition-colors text-left"
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

        {/* Secondary surfaces — quiet-gym rows */}
        <div className="flex flex-col gap-2.5">
          {secondary.map((item) => (
            <RowCard
              key={item.to + item.label}
              to={item.to}
              icon={item.icon}
              title={item.label}
            />
          ))}
        </div>
      </motion.div>
    </Layout>
  );
};

export default HubPage;
