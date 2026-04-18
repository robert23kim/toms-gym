import React from "react";

interface HighlightsGridProps {
  birdies: number;
  pars: number;
  bogeys: number;
  doublesOrWorse: number;
}

const cellClass = "fw-surface p-3 text-center";

const HighlightsGrid: React.FC<HighlightsGridProps> = ({
  birdies, pars, bogeys, doublesOrWorse,
}) => (
  <div data-testid="highlights-grid" className="grid grid-cols-4 gap-2">
    <div className={cellClass}>
      <div className="text-xl font-medium text-[var(--fw-text-success)]">{birdies}</div>
      <div className="text-xs fw-text-secondary">Birdies</div>
    </div>
    <div className={cellClass}>
      <div className="text-xl font-medium">{pars}</div>
      <div className="text-xs fw-text-secondary">Pars</div>
    </div>
    <div className={cellClass}>
      <div className="text-xl font-medium text-[var(--fw-text-warning)]">{bogeys}</div>
      <div className="text-xs fw-text-secondary">Bogeys</div>
    </div>
    <div className={cellClass}>
      <div className="text-xl font-medium text-[var(--fw-text-danger)]">{doublesOrWorse}</div>
      <div className="text-xs fw-text-secondary">Doubles+</div>
    </div>
  </div>
);

export default HighlightsGrid;
