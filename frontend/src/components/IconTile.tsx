import React from "react";
import { Link } from "react-router-dom";

interface Props {
  to: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}

/**
 * Quiet-gym primitive: centered icon-chip tile, whole tile is the link.
 * Used by the home page verticals and the upload chooser.
 */
const IconTile: React.FC<Props> = ({ to, icon, title, description }) => (
  <Link
    to={to}
    className="group flex flex-col items-center gap-2.5 glass rounded-2xl px-4 py-6 text-center transition-all hover:bg-secondary/40 hover:-translate-y-0.5"
  >
    <span className="w-11 h-11 rounded-xl bg-accent/10 text-accent grid place-items-center">
      {icon}
    </span>
    <span className="font-semibold">{title}</span>
    <span className="text-sm text-muted-foreground leading-snug">{description}</span>
  </Link>
);

export default IconTile;
