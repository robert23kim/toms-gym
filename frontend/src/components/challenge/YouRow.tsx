import React from "react";
import { Link } from "react-router-dom";
import { Play } from "lucide-react";
import type { ChallengeLeaderboardRow, ChallengeMetric } from "../../lib/types";
import { formatScoreValue, scoreUnit } from "./metric";

// Highlighted "You" row. When the viewer has an entry it sits inline at their
// actual rank showing rank + score; when they don't, it's an upload prompt.
// Mobile is a flex row; desktop (lg:) becomes a 4-column grid aligned to the
// "Everyone else" table header + rows (#1b).
type YouRowProps =
  | { entered: false; onUpload: () => void }
  | {
      entered: true;
      row: ChallengeLeaderboardRow;
      metric: ChallengeMetric;
      clipHref: string | null;
      /** Live goal subtitle, e.g. "3.9s to reach #6" (motivation layer). */
      subtitle?: string | null;
      /** Attempt-history accordion (optional): chip shows at attemptCount > 1. */
      attemptCount?: number;
      expanded?: boolean;
      onToggleAttempts?: () => void;
    };

const HIGHLIGHT =
  "border-t border-[rgba(47,123,246,.35)] bg-[rgba(47,123,246,.14)]";

// Shared responsive layout: flex on mobile, 4-column grid on desktop.
const LAYOUT =
  "flex items-center gap-3 px-3.5 py-2.5 lg:grid lg:grid-cols-[52px_1fr_120px_90px] lg:items-center lg:gap-3.5 lg:px-[18px] lg:py-3.5";

const YouAvatar: React.FC<{ className?: string }> = ({ className = "" }) => (
  <span
    className={`flex h-[30px] w-[30px] flex-none items-center justify-center rounded-full bg-[#2f7bf6] text-[10px] font-semibold text-white ${className}`}
  >
    YOU
  </span>
);

const YouRow: React.FC<YouRowProps> = (props) => {
  // Narrow via `in` — a boolean discriminant doesn't narrow under the repo's
  // strictNullChecks:false config, but the operator narrowing does.
  if ("onUpload" in props) {
    return (
      <button
        type="button"
        data-testid="you-row"
        data-entered="false"
        onClick={props.onUpload}
        className={`w-full text-left ${LAYOUT} ${HIGHLIGHT}`}
      >
        <div className="w-[18px] text-center text-[13px] font-bold text-[#7fb0ff] lg:col-start-1 lg:row-start-1 lg:w-auto lg:text-left lg:text-[15px]">
          —
        </div>
        <div className="flex min-w-0 flex-1 items-center gap-3 lg:col-start-2 lg:row-start-1 lg:gap-2.5">
          <YouAvatar />
          <span className="truncate text-[12.5px] font-semibold text-[#7fb0ff] lg:text-[14.5px]">
            Not logged yet
          </span>
        </div>
        <div className="hidden text-[13px] font-medium text-white/50 lg:col-start-3 lg:row-start-1 lg:block">
          —
        </div>
        <span className="text-[11.5px] font-semibold text-[#7fb0ff] lg:col-start-4 lg:row-start-1 lg:justify-self-end">
          Upload →
        </span>
      </button>
    );
  }

  const { row, metric, clipHref, subtitle, attemptCount, expanded, onToggleAttempts } = props;
  const showAttemptsChip = (attemptCount ?? 0) > 1 && !!onToggleAttempts;

  const thumb = (
    <div className="relative h-11 w-11 flex-none overflow-hidden rounded-lg bg-gradient-to-br from-[#2a3340] to-[#171b22] lg:h-[30px] lg:w-[30px]">
      {row.clip_url ? (
        <video
          src={row.clip_url}
          muted
          playsInline
          preload="metadata"
          className="h-full w-full object-cover"
          onLoadedData={(e) => {
            (e.target as HTMLVideoElement).currentTime = 0.5;
          }}
        />
      ) : null}
      <div className="absolute inset-0 flex items-center justify-center bg-black/20">
        <Play className="ml-px h-3.5 w-3.5 text-white/90 lg:h-3 lg:w-3" fill="currentColor" />
      </div>
    </div>
  );

  const clip = clipHref ? (
    <Link
      to={clipHref}
      aria-label="Watch your clip"
      className="lg:col-start-4 lg:row-start-1 lg:justify-self-end"
    >
      {thumb}
    </Link>
  ) : (
    <div className="lg:col-start-4 lg:row-start-1 lg:justify-self-end">{thumb}</div>
  );

  return (
    <div
      data-testid="you-row"
      data-entered="true"
      data-rank={row.rank}
      className={`${LAYOUT} ${HIGHLIGHT}`}
    >
      <div className="w-[18px] text-sm font-bold tabular-nums text-[#7fb0ff] lg:col-start-1 lg:row-start-1 lg:w-auto lg:text-[15px]">
        {row.rank}
      </div>
      {clip}
      <div className="min-w-0 flex-1 lg:col-start-2 lg:row-start-1 lg:flex lg:items-center lg:gap-2.5">
        <YouAvatar className="hidden lg:flex" />
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-[#7fb0ff] lg:text-[14.5px]">
            {row.name || "You"} <span className="text-white/40">· You</span>
          </div>
          {subtitle && (
            <div data-testid="you-row-subtitle" className="truncate text-[11px] text-[#7fb0ff]/70">
              {subtitle}
            </div>
          )}
        </div>
        {showAttemptsChip && (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onToggleAttempts!();
            }}
            aria-expanded={expanded}
            className="ml-2 shrink-0 rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-white/60 hover:text-white hover:bg-white/10 transition-colors"
          >
            {attemptCount} attempts {expanded ? "▴" : "▾"}
          </button>
        )}
      </div>
      <span className="font-bold tracking-tight tabular-nums text-base lg:col-start-3 lg:row-start-1 lg:text-[17px]">
        {formatScoreValue(row.score, metric)}
        <span className="ml-0.5 text-[60%] font-semibold text-white/50">
          {scoreUnit(metric)}
        </span>
      </span>
    </div>
  );
};

export default YouRow;
