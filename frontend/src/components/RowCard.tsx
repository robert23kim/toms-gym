import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

interface Props {
  to: string;
  icon?: React.ReactNode;
  title: string;
  pill?: string;
  trailing?: string;
}

/**
 * Quiet-gym primitive: slim horizontal link row — icon · title · pill · "Open →".
 * Used by the home open-challenges strip, hub secondary links, and Challenges.
 */
const RowCard: React.FC<Props> = ({ to, icon, title, pill, trailing = "Open" }) => (
  <Link
    to={to}
    className="group flex items-center gap-3 glass rounded-xl px-4 py-3.5 text-left transition-colors hover:bg-secondary/40"
  >
    {icon && <span className="text-accent shrink-0">{icon}</span>}
    <span className="flex-1 min-w-0 font-medium truncate">{title}</span>
    {pill && (
      <span className="shrink-0 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-accent/10 text-accent">
        {pill}
      </span>
    )}
    <span className="shrink-0 inline-flex items-center gap-1 text-sm text-muted-foreground group-hover:text-foreground transition-colors">
      {trailing}
      <ArrowRight className="w-3.5 h-3.5" />
    </span>
  </Link>
);

export default RowCard;
