import React from "react";
import type { Nickname } from "../../lib/plankStats";

/** Muted pill for a plank steadiness nickname. Renders nothing when null. */
const NicknameBadge: React.FC<{ nickname: Nickname | null; className?: string }> = ({
  nickname,
  className = "",
}) => {
  if (!nickname) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-white/60 ${className}`}
    >
      <span aria-hidden>{nickname.emoji}</span>
      {nickname.name}
    </span>
  );
};

export default NicknameBadge;
