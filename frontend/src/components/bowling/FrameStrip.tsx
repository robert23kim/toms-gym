import React from "react";
import {
  Roll,
  framePins,
  scoreFrames,
  parseFrameInput,
  formatFrameInput,
} from "../../lib/bowlingScore";

interface Props {
  playerName: string;
  frames: Roll[][];
  onChange: (frames: Roll[][]) => void;
  /** 1-based frames whose rolls were guessed from the running score — worth a second look. */
  inferred?: number[];
}

export const frameErrors = (frames: Roll[][]): (string | null)[] =>
  frames.map((frame, index) => {
    if (frame.length === 0) return null;
    try {
      framePins(frame, index);
      return null;
    } catch (err) {
      return err instanceof Error ? err.message : String(err);
    }
  });

/** The scored prefix — trailing unfilled frames must not be scored as zeros. */
const filledPrefix = (frames: Roll[][]): Roll[][] => {
  let last = -1;
  frames.forEach((frame, index) => {
    if (frame.length > 0) last = index;
  });
  return frames.slice(0, last + 1);
};

const FrameStrip: React.FC<Props> = ({ playerName, frames, onChange, inferred = [] }) => {
  const errors = frameErrors(frames);
  const inferredSet = new Set(inferred);
  const scored = scoreFrames(filledPrefix(frames));
  const firstError = errors.find((e) => e !== null) || null;

  const setFrame = (index: number, text: string) => {
    const next = frames.map((frame, i) => (i === index ? parseFrameInput(text, index) : frame));
    onChange(next);
  };

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-5 sm:grid-cols-10 gap-1">
        {frames.map((frame, index) => (
          <div key={index} className="text-center">
            <span className="block text-[10px] text-muted-foreground mb-0.5">{index + 1}</span>
            <input
              type="text"
              inputMode="text"
              aria-label={`${playerName} frame ${index + 1}`}
              value={formatFrameInput(frame)}
              onChange={(e) => setFrame(index, e.target.value)}
              maxLength={index === 9 ? 3 : 2}
              title={inferredSet.has(index + 1) ? "Rolls guessed from the running score — check them" : undefined}
              className={`w-full h-9 text-center uppercase text-sm rounded-md bg-background border focus:outline-none focus:ring-2 focus:ring-accent ${
                errors[index]
                  ? "border-destructive"
                  : inferredSet.has(index + 1)
                    ? "border-amber-500 border-dashed"
                    : "border-input"
              }`}
            />
            <span
              data-testid={`cumulative-${index}`}
              className="block text-xs font-medium mt-0.5 tabular-nums"
            >
              {scored.cumulative[index] !== undefined ? scored.cumulative[index] : "—"}
            </span>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className={firstError ? "text-destructive" : inferred.length ? "text-amber-600" : "text-muted-foreground"}>
          {firstError ||
            (inferred.length
              ? `Frame${inferred.length === 1 ? "" : "s"} ${inferred.join(", ")} read from the score — check the rolls`
              : scored.complete
                ? "Complete game"
                : "Fill every frame to finish")}
        </span>
        <span className="font-medium tabular-nums">Total {scored.total}</span>
      </div>
    </div>
  );
};

export default FrameStrip;
