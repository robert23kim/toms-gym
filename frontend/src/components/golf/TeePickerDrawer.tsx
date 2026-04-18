import React, { useEffect, useMemo, useState } from "react";
import { X, Search, Check } from "lucide-react";
import DifficultyMeter from "./DifficultyMeter";
import type { GolfCourse, GolfCourseSearchResult, GolfTee } from "../../lib/types";

export interface TeePickerApplyPayload {
  tee_id: string | null;
  rating_18: number | null;
  slope_18: number | null;
  yardage: number | null;
}

export interface TeePickerDrawerProps {
  open: boolean;
  course: GolfCourse;
  tees: GolfTee[];
  selectedTeeId: string | null;
  adjustedGrossScore: number;
  onApply: (payload: TeePickerApplyPayload) => void;
  onClose: () => void;
  onLookup?: (
    query: string,
    near: [number | null, number | null],
  ) => Promise<GolfCourseSearchResult[]>;
}

const TeePickerDrawer: React.FC<TeePickerDrawerProps> = ({
  open,
  course,
  tees,
  selectedTeeId,
  adjustedGrossScore,
  onApply,
  onClose,
  onLookup,
}) => {
  const visibleTees = useMemo(() => tees.slice(0, 4), [tees]);

  const [activeId, setActiveId] = useState<string | null>(selectedTeeId);
  const [rating, setRating] = useState<number | null>(null);
  const [slope, setSlope] = useState<number | null>(null);
  const [yardage, setYardage] = useState<number | null>(null);
  const [lookupResults, setLookupResults] = useState<GolfCourseSearchResult[]>([]);
  const [lookupBusy, setLookupBusy] = useState(false);

  const activeTee = useMemo(
    () => visibleTees.find((t) => t.id === activeId) || null,
    [visibleTees, activeId],
  );

  useEffect(() => {
    if (!open) return;
    setActiveId(selectedTeeId);
  }, [open, selectedTeeId]);

  useEffect(() => {
    if (!activeTee) {
      setRating(null);
      setSlope(null);
      setYardage(null);
      return;
    }
    setRating(activeTee.rating_18);
    setSlope(activeTee.slope_18);
    setYardage(activeTee.yardage);
  }, [activeTee]);

  const liveDifferential = useMemo(() => {
    if (rating === null || slope === null || slope === 0) return null;
    return ((adjustedGrossScore - rating) * 113) / slope;
  }, [rating, slope, adjustedGrossScore]);

  if (!open) return null;

  const handleLookup = async () => {
    if (!onLookup || lookupBusy) return;
    setLookupBusy(true);
    try {
      const results = await onLookup(course.name, [
        course.latitude,
        course.longitude,
      ]);
      setLookupResults(results);
    } finally {
      setLookupBusy(false);
    }
  };

  const parseOptionalNumber = (raw: string): number | null => {
    const trimmed = raw.trim();
    if (!trimmed) return null;
    const n = Number(trimmed);
    return Number.isFinite(n) ? n : null;
  };

  return (
    <div
      data-testid="tee-picker-drawer"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-label="Change tee"
    >
      <div
        className="fw-surface w-full max-w-xl max-h-[90vh] overflow-y-auto p-5 sm:p-6 rounded-t-lg sm:rounded-lg"
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="fw-h2">Change tee</h2>
            <p className="fw-text-secondary text-sm mt-1">{course.name}</p>
          </div>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="p-1 rounded-md hover:bg-[var(--fw-bg-secondary)]"
          >
            <X className="w-4 h-4 fw-text-secondary" />
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-5">
          {visibleTees.map((tee) => {
            const active = tee.id === activeId;
            return (
              <button
                key={tee.id || "unknown"}
                type="button"
                data-testid={`tee-card-${tee.id}`}
                onClick={() => setActiveId(tee.id)}
                className={`fw-surface p-3 text-left transition-colors hover:bg-[var(--fw-bg-secondary)] ${
                  active ? "fw-selected" : ""
                }`}
              >
                <div
                  className="w-4 h-4 rounded-full mb-2 border-[0.5px] border-[var(--fw-border-tertiary)]"
                  style={{ background: tee.color_hex || "transparent" }}
                  aria-hidden="true"
                />
                <div className="text-sm font-medium">{tee.name || "—"}</div>
                <div className="text-xs fw-text-secondary mt-1">
                  {tee.rating_18 !== null ? tee.rating_18.toFixed(1) : "—"} /{" "}
                  {tee.slope_18 ?? "—"}
                </div>
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-3 gap-3 mb-5">
          <label className="block">
            <span className="text-xs fw-text-secondary">Rating</span>
            <input
              type="number"
              step={0.1}
              value={rating ?? ""}
              onChange={(e) => setRating(parseOptionalNumber(e.target.value))}
              className="w-full mt-1 h-9 px-2 rounded-md border-[0.5px] border-[var(--fw-border-secondary)] bg-background focus:outline-none focus:ring-1 focus:ring-[var(--fw-info)]"
              aria-label="Rating"
            />
          </label>
          <label className="block">
            <span className="text-xs fw-text-secondary">Slope</span>
            <input
              type="number"
              step={1}
              value={slope ?? ""}
              onChange={(e) => setSlope(parseOptionalNumber(e.target.value))}
              className="w-full mt-1 h-9 px-2 rounded-md border-[0.5px] border-[var(--fw-border-secondary)] bg-background focus:outline-none focus:ring-1 focus:ring-[var(--fw-info)]"
              aria-label="Slope"
            />
          </label>
          <label className="block">
            <span className="text-xs fw-text-secondary">Yardage</span>
            <input
              type="number"
              step={1}
              value={yardage ?? ""}
              onChange={(e) => setYardage(parseOptionalNumber(e.target.value))}
              className="w-full mt-1 h-9 px-2 rounded-md border-[0.5px] border-[var(--fw-border-secondary)] bg-background focus:outline-none focus:ring-1 focus:ring-[var(--fw-info)]"
              aria-label="Yardage"
            />
          </label>
        </div>

        <div className="mb-5">
          <DifficultyMeter slope={slope} />
        </div>

        <div className="fw-surface p-3 mb-5 text-sm flex items-center justify-between">
          <span className="fw-text-secondary">
            Differential = ((score − rating) × 113) / slope
          </span>
          <span
            data-testid="tee-picker-differential"
            className="font-medium text-[var(--fw-text-info)]"
          >
            {liveDifferential !== null ? liveDifferential.toFixed(1) : "—"}
          </span>
        </div>

        {onLookup && (
          <div className="mb-5">
            <button
              type="button"
              onClick={handleLookup}
              disabled={lookupBusy}
              className="inline-flex items-center gap-2 h-9 px-3 rounded-md border-[0.5px] border-[var(--fw-border-secondary)] text-sm hover:bg-[var(--fw-bg-secondary)] disabled:opacity-50"
            >
              <Search className="w-4 h-4" />
              {lookupBusy ? "Searching…" : "Look up official values"}
            </button>
            {lookupResults.length > 0 && (
              <ul
                data-testid="tee-picker-lookup-results"
                className="mt-2 space-y-1 text-sm"
              >
                {lookupResults.map((r) => (
                  <li key={r.id} className="fw-surface p-2">
                    <div className="font-medium">{r.name}</div>
                    <div className="text-xs fw-text-secondary">
                      {[r.city, r.state, r.country].filter(Boolean).join(", ")}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="h-9 px-4 rounded-md border-[0.5px] border-[var(--fw-border-secondary)] text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() =>
              onApply({
                tee_id: activeId,
                rating_18: rating,
                slope_18: slope,
                yardage,
              })
            }
            className="h-9 px-4 rounded-md bg-[var(--fw-info)] text-white text-sm inline-flex items-center gap-2"
          >
            <Check className="w-4 h-4" />
            Apply
          </button>
        </div>
      </div>
    </div>
  );
};

export default TeePickerDrawer;
