import React, { useState } from "react";

/** localStorage key: the burst fires once per (win, browser). */
export const confettiSeenKey = (competitionId: string, userId: string): string =>
  `champ-confetti-${competitionId}-${userId}`;

const COLORS = ["#f59e0b", "#fbbf24", "#34d399", "#60a5fa", "#f472b6"];
const PIECES = 40;

interface ChampionConfettiProps {
  competitionId: string;
  userId: string;
}

/**
 * One-time celebration when a champion's profile is first opened after a win.
 * Pure CSS keyframes (`confetti-fall` in index.css) — no new dependency.
 */
const ChampionConfetti: React.FC<ChampionConfettiProps> = ({
  competitionId,
  userId,
}) => {
  const [show] = useState(() => {
    const key = confettiSeenKey(competitionId, userId);
    if (localStorage.getItem(key)) return false;
    localStorage.setItem(key, "1");
    return true;
  });
  const [dismissed, setDismissed] = useState(false);

  if (!show || dismissed) return null;

  const reduced =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  return (
    <div
      className="pointer-events-none fixed inset-0 z-50 overflow-hidden"
      aria-live="polite"
    >
      {!reduced &&
        Array.from({ length: PIECES }).map((_, i) => (
          <span
            key={i}
            className="absolute top-0 w-2 h-3 rounded-[1px]"
            style={{
              left: `${(i * 97) % 100}%`,
              backgroundColor: COLORS[i % COLORS.length],
              animation: `confetti-fall ${2.4 + (i % 5) * 0.3}s ease-in ${
                (i % 8) * 0.12
              }s forwards`,
            }}
            aria-hidden="true"
          />
        ))}
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="pointer-events-auto absolute left-1/2 top-24 -translate-x-1/2 rounded-full border border-amber-500/40 bg-amber-500/15 px-5 py-2.5 text-sm font-medium text-amber-700 dark:text-amber-300 backdrop-blur shadow-lg"
      >
        👑 Champion! Nice work.
      </button>
    </div>
  );
};

export default ChampionConfetti;
