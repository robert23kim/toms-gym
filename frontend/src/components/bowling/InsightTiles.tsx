import React from "react";

export interface InsightTile {
  key: string;
  label: string;
  value: string;
  hint?: string;
  tone?: "up" | "down" | "neutral";
}

const toneClass = (tone: InsightTile["tone"]): string => {
  if (tone === "up") return "text-emerald-500";
  if (tone === "down") return "text-destructive";
  return "";
};

const InsightTiles: React.FC<{ tiles: InsightTile[] }> = ({ tiles }) => (
  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
    {tiles.map((tile) => (
      <div
        key={tile.key}
        data-testid={`tile-${tile.key}`}
        className="glass rounded-xl px-4 py-3 text-center"
      >
        <span className="block text-xs text-muted-foreground">{tile.label}</span>
        <span className={`block text-2xl font-semibold tabular-nums ${toneClass(tile.tone)}`}>
          {tile.value}
        </span>
        {tile.hint && (
          <span className="block text-[11px] text-muted-foreground mt-0.5">{tile.hint}</span>
        )}
      </div>
    ))}
  </div>
);

export default InsightTiles;
