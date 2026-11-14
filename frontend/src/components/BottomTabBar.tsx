import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Home, Dumbbell, CircleDot, Flag, Trophy, User } from "lucide-react";
import { activeTab, meTarget, TabKey } from "../lib/tabs";
import { useIsOwner } from "../hooks/useIsOwner";
import { getUserId } from "../lib/identity";

const readUserId = (): string | null => {
  try {
    return getUserId();
  } catch {
    return null;
  }
};

const BottomTabBar: React.FC = () => {
  const { pathname } = useLocation();
  const current = activeTab(pathname);
  const isOwner = useIsOwner();
  const tabs: { key: TabKey; to: string; label: string; icon: React.ReactNode }[] = [
    { key: "home", to: "/", label: "Home", icon: <Home className="w-5 h-5" /> },
    { key: "lift", to: "/lift", label: "Lift", icon: <Dumbbell className="w-5 h-5" /> },
    ...(isOwner
      ? [
          { key: "bowl" as const, to: "/bowl", label: "Bowl", icon: <CircleDot className="w-5 h-5" /> },
          { key: "golf" as const, to: "/golf", label: "Golf", icon: <Flag className="w-5 h-5" /> },
        ]
      : []),
    { key: "champions", to: "/champions", label: "Champions", icon: <Trophy className="w-5 h-5" /> },
    { key: "me", to: meTarget(readUserId()), label: "Me", icon: <User className="w-5 h-5" /> },
  ];

  return (
    <nav
      aria-label="Primary"
      className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-background/90 backdrop-blur-md border-t border-border/40"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className={`grid h-16 ${tabs.length === 6 ? "grid-cols-6" : "grid-cols-4"}`}>
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
