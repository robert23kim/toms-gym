import React from "react";
import "../styles/fairway.css";

interface FairwayScopeProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Applies the Fairway design tokens (palette, typography, 0.5px borders)
 * to its subtree. Tokens live in frontend/src/styles/fairway.css under
 * the .fw-scope selector so they can't leak into other features.
 */
const FairwayScope: React.FC<FairwayScopeProps> = ({ children, className = "" }) => (
  <div className={`fw-scope ${className}`.trim()}>{children}</div>
);

export default FairwayScope;
