import React, { useEffect, useState } from "react";

const STAGES = [
  "Detecting layout",
  "Identifying course",
  "Reading par and yardage",
  "Extracting player scores",
  "Flagging low-confidence holes",
] as const;

/**
 * Shows a 5-stage fake-progression list while the real /golf/upload call
 * is in flight. Each stage becomes "active" (pulsing info dot) after a
 * short delay, then "done" (green dot) when the next stage starts. The
 * last stage stays active until the parent unmounts the component.
 *
 * Why fake-stage: the real backend does a single OCR call that takes
 * 2-6s with no intermediate signal. A staged UI makes the wait feel
 * intentional (Fairway spec Section 5.2 Step 2).
 */
const StagedParseProgress: React.FC = () => {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    STAGES.forEach((_, i) => {
      if (i === 0) return;
      timers.push(setTimeout(() => setActiveIndex(i), i * 700));
    });
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="fw-surface p-5">
      <h3 className="fw-h3 mb-3">Reading your scorecard</h3>
      <ul className="space-y-2 text-sm">
        {STAGES.map((label, i) => {
          const state =
            i < activeIndex ? "fw-parse-dot-done" :
            i === activeIndex ? "fw-parse-dot-active" : "";
          return (
            <li key={label} className="flex items-center">
              <span className={`fw-parse-dot ${state}`} />
              <span className={i <= activeIndex ? "" : "fw-text-secondary"}>{label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default StagedParseProgress;
