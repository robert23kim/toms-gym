import React, { useEffect, useState } from "react";
import { Flame, Share2 } from "lucide-react";
import { fetchUserActivity } from "../lib/api";
import { computeStreak, Streak } from "../lib/streak";
import { createAndCopyShareLink } from "../lib/share";

const StreakCard: React.FC = () => {
  const [streak, setStreak] = useState<Streak | null>(null);
  const [shareState, setShareState] = useState<"idle" | "copied" | "failed">("idle");
  const userId = typeof localStorage !== "undefined" ? localStorage.getItem("userId") : null;

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    fetchUserActivity(userId)
      .then((activity) => {
        if (!cancelled) setStreak(computeStreak(activity));
      })
      .catch(() => {}); // non-fatal: card simply stays hidden
    return () => {
      cancelled = true;
    };
  }, [userId]);

  if (!userId || !streak) return null;

  const onShare = async () => {
    try {
      await createAndCopyShareLink({
        targetUrl: `${window.location.origin}/profile/${userId}`,
        ogTitle: `${streak.weeks}-week streak on Tom's Gym`,
        ogDescription: "Lifting, bowling and golf — tracked every week.",
        ogStat: `${streak.weeks}w`,
      });
      setShareState("copied");
    } catch {
      setShareState("failed");
    }
    setTimeout(() => setShareState("idle"), 2000);
  };

  return (
    <div className="rounded-2xl border border-border bg-card/60 px-5 py-4 text-left" data-testid="streak-card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold">Your streak</h2>
        <button
          type="button"
          onClick={onShare}
          className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-sm hover:bg-secondary transition-colors"
        >
          <Share2 className="w-4 h-4" aria-hidden="true" />
          {shareState === "copied" ? "Copied!" : shareState === "failed" ? "Failed" : "Share"}
        </button>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex flex-col items-center w-16 shrink-0" aria-label={`${streak.weeks} week streak`}>
          <div className="relative">
            <Flame className="w-14 h-14 text-orange-500 fill-orange-500" aria-hidden="true" />
            <span className="absolute inset-0 flex items-center justify-center pt-4 text-white font-bold text-lg">
              {streak.weeks}
            </span>
          </div>
          <span className="text-orange-500 font-semibold text-sm">
            {streak.weeks === 1 ? "Week" : "Weeks"}
          </span>
        </div>
        <ol className="flex-1 grid grid-cols-7 gap-1 list-none m-0 p-0">
          {streak.week.map((d) => (
            <li key={d.date.toISOString()} className="flex flex-col items-center gap-2">
              <span className="text-xs text-muted-foreground">{d.label}</span>
              <span
                data-testid={d.active ? "streak-day-active" : "streak-day"}
                className={[
                  "w-9 h-9 rounded-full flex items-center justify-center text-sm",
                  d.active
                    ? "bg-foreground text-background"
                    : d.isToday
                      ? "border-2 border-foreground"
                      : d.isFuture
                        ? "border border-border text-muted-foreground"
                        : "bg-secondary text-muted-foreground",
                ].join(" ")}
              >
                {d.active ? <Flame className="w-4 h-4" aria-hidden="true" /> : d.date.getDate()}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
};

export default StreakCard;
