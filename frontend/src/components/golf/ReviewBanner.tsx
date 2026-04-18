import React from "react";
import { AlertTriangle } from "lucide-react";

interface ReviewBannerProps {
  needsReviewCount: number;
}

/**
 * Amber banner shown at the top of the review grid when any score cell
 * has ocr_confidence < 0.85 (Fairway spec §5.2 Step 3).
 * Hidden when the count is 0.
 */
const ReviewBanner: React.FC<ReviewBannerProps> = ({ needsReviewCount }) => {
  if (needsReviewCount <= 0) return null;
  const wording =
    needsReviewCount >= 10
      ? "Many holes need review"
      : `${needsReviewCount} hole${needsReviewCount === 1 ? "" : "s"} need review`;
  return (
    <div
      data-testid="review-banner"
      className="flex items-center gap-2 rounded-md border-[0.5px] border-[var(--fw-border-warning)] bg-[var(--fw-bg-warning)] text-[var(--fw-text-warning)] px-3 py-2 text-sm"
    >
      <AlertTriangle className="w-4 h-4" />
      <span>{wording}</span>
    </div>
  );
};

export default ReviewBanner;
