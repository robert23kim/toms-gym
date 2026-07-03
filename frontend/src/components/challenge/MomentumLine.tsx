import React from "react";
import type {
  ChallengeLeaderboardMomentum,
  ChallengeLeaderboardRow,
} from "../../lib/types";
import { getGolfAvatar } from "../../lib/api";

interface MomentumLineProps {
  /** Ranked rows — the top few supply the overlapping avatars. */
  rows: ChallengeLeaderboardRow[];
  momentum: ChallengeLeaderboardMomentum;
}

/**
 * Hero social-proof line: three overlapping mini-avatars + "4 uploaded today ·
 * 12 joined". Avatars reuse the deterministic `getGolfAvatar` helper (same as
 * the podium). Hidden when there's no one to show and nothing has happened.
 */
const MomentumLine: React.FC<MomentumLineProps> = ({ rows, momentum }) => {
  const faces = rows.slice(0, 3);
  const { uploaded_today, joined } = momentum;

  if (faces.length === 0 && !joined && !uploaded_today) return null;

  const parts: string[] = [];
  if (uploaded_today > 0) parts.push(`${uploaded_today} uploaded today`);
  if (joined > 0) parts.push(`${joined} joined`);
  const text = parts.join(" · ");

  return (
    <div data-testid="momentum-line" className="mt-3 flex items-center gap-2">
      {faces.length > 0 && (
        <div className="flex items-center">
          {faces.map((row, i) => (
            <img
              key={row.user_id}
              src={getGolfAvatar(row.name, row.user_id)}
              alt={row.name || "Athlete"}
              className="h-5 w-5 rounded-full bg-[#2a2f3a] object-cover"
              style={{
                marginLeft: i === 0 ? 0 : -6,
                border: "1.5px solid #0a0a0b",
                zIndex: faces.length - i,
              }}
            />
          ))}
        </div>
      )}
      {text && <span className="text-[12px] text-white/50">{text}</span>}
    </div>
  );
};

export default MomentumLine;
