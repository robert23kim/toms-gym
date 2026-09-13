import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Home, Dumbbell, CircleDot, Flag, User } from "lucide-react";
import { activeTab, meTarget, TabKey } from "../lib/tabs";

const readUserId = (): string | null => {
  try {
    return localStorage.getItem("userId");
  } catch {
    return null;
  }
};

const BottomTabBar: React.FC = () => {
  const { pathname } = useLocation();
  const current = activeTab(pathname);
  const tabs: { key: TabKey; to: string; label: string; icon: React.ReactNode }[] = [
    { key: "home", to: "/", label: "Home", icon: <Home className="w-5 h-5" /> },
    { key: "lift", to: "/lift", label: "Lift", icon: <Dumbbell className="w-5 h-5" /> },
    { key: "bowl", to: "/bowl", label: "Bowl", icon: <CircleDot className="w-5 h-5" /> },
    { key: "golf", to: "/golf", label: "Golf", icon: <Flag className="w-5 h-5" /> },
    { key: "me", to: meTarget(readUserId()), label: "Me", icon: <User className="w-5 h-5" /> },
  ];

  return (
    <nav
      aria-label="Primary"
      className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-background/90 backdrop-blur-md border-t border-border/40"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="grid grid-cols-5 h-16">
        {tabs.map((tab) => {
          const active = tab.key === current;
          return (
            <Link
              key={tab.key}
              to={tab.to}
              aria-current={active ? "page" : undefined}
              className={`flex flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors ${
                active ? "text-accent" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.icon}
              {tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
};

export default BottomTabBar;
