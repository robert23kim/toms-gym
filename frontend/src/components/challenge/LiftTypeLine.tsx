import React, { useState } from "react";
import { changeLiftType } from "../../lib/api";
import { CONFIRM_THRESHOLD, isAutoLiftType, liftTypeCountedAs, liftTypeQuestion } from "../../lib/autoLiftType";

export type LiftTypeSource = "user" | "auto";

interface Props {
  attemptId: string;
  viewerId: string | null;
  isOwner: boolean;
  /** The competition's lift types (DB names), the only choices offered. */
  candidates: string[];
  liftType: string | null | undefined;
  source: LiftTypeSource | null | undefined;
  confidence: number | null | undefined;
  needsLiftType: boolean;
  /** A change was accepted and analysis re-queued; the page shows its analysing state. */
  onRequeued: (liftType: string) => void;
  className?: string;
}

const chip =
  "inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-medium text-white/70 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-50";
const chipYes =
  "inline-flex items-center rounded-full border border-[#2f7bf6]/40 bg-[#2f7bf6]/15 px-2.5 py-1 text-[11px] font-semibold text-[#7fb0ff] transition-colors hover:bg-[#2f7bf6]/25 disabled:opacity-50";

const errorText = (err: unknown): string => {
  const e = err as { response?: { data?: { error?: string } } };
  return e?.response?.data?.error || "Couldn't change the lift type. Try again.";
};

/** "Counted as Pushups · Automatic" with Change; asks "Is this a pushup?" when the guess is unsure. */
const LiftTypeLine: React.FC<Props> = ({
  attemptId,
  viewerId,
  isOwner,
  candidates,
  liftType,
  source,
  confidence,
  needsLiftType,
  onRequeued,
  className = "",
}) => {
  const [confirmed, setConfirmed] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [pick, setPick] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canonical = (t: string | null | undefined) =>
    candidates.find((c) => c.toLowerCase() === (t ?? "").trim().toLowerCase()) ?? null;
  const current = isAutoLiftType(liftType) ? null : canonical(liftType) ?? (liftType || null);
  const effectiveSource: LiftTypeSource = confirmed ? "user" : source === "auto" ? "auto" : "user";
  const unsure =
    !confirmed &&
    (needsLiftType || !current || (effectiveSource === "auto" && confidence != null && confidence < CONFIRM_THRESHOLD));

  if (!isOwner && !current) return null;

  const openSheet = () => {
    setPick(canonical(current));
    setError(null);
    setSheetOpen(true);
  };

  const confirmYes = async () => {
    if (!current) return;
    setBusy(true);
    try {
      const res = await changeLiftType(attemptId, canonical(current) ?? current, viewerId ?? "");
      if (res.status === "queued") onRequeued(res.lift_type);
      else setConfirmed(true);
    } catch {
      setSheetOpen(true);
      setPick(canonical(current));
    } finally {
      setBusy(false);
    }
  };

  const submitPick = async () => {
    if (!pick) return;
    setBusy(true);
    setError(null);
    try {
      const res = await changeLiftType(attemptId, pick, viewerId ?? "");
      setSheetOpen(false);
      if (res.status === "queued") onRequeued(res.lift_type);
      else setConfirmed(true);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const state = isOwner && unsure ? "confirm" : effectiveSource === "auto" ? "automatic" : "manual";

  return (
    <>
      <div
        data-testid="lift-type-line"
        data-state={state}
        className={`mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground ${className}`}
      >
        {state === "confirm" ? (
          <span>{current ? `Is this ${liftTypeQuestion(current)}?` : "Which lift is this?"}</span>
        ) : (
          <span>
            Counted as <span className="font-semibold text-foreground">{liftTypeCountedAs(current ?? "")}</span>
            {state === "automatic" && " · Automatic"}
          </span>
        )}
        {isOwner && (
          <span className="inline-flex items-center gap-1.5">
            {state === "confirm" && current && (
              <button type="button" className={chipYes} onClick={confirmYes} disabled={busy}>
                Yes
              </button>
            )}
            <button type="button" className={chip} onClick={openSheet} disabled={busy}>
              Change
            </button>
          </span>
        )}
      </div>

      {sheetOpen && (
        <div
          className="fixed inset-0 z-[60] flex items-end justify-center bg-black/60 sm:items-center"
          onClick={() => !busy && setSheetOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Change lift type"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md rounded-t-2xl border border-white/[.07] bg-card p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] text-left sm:rounded-2xl sm:pb-5"
          >
            <h2 className="text-lg font-semibold">Change lift type</h2>
            <p className="mt-1 text-sm text-muted-foreground">We'll re-analyse your video as the lift you pick.</p>
            <div role="radiogroup" aria-label="Lift type" className="mt-4 grid grid-cols-2 gap-2">
              {candidates.map((c) => {
                const selected = pick === c;
                return (
                  <button
                    key={c}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => setPick(c)}
                    className={`rounded-xl border px-3 py-3 text-sm font-medium transition-colors ${
                      selected
                        ? "border-[#2f7bf6] bg-[#2f7bf6]/15 text-[#7fb0ff]"
                        : "border-white/10 bg-white/5 text-white/70 hover:bg-white/10"
                    }`}
                  >
                    {liftTypeCountedAs(c)}
                  </button>
                );
              })}
            </div>
            {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
            <button
              type="button"
              onClick={submitPick}
              disabled={busy || !pick}
              className="mt-4 w-full rounded-xl bg-[#2f7bf6] py-3 font-semibold text-white transition-colors hover:bg-blue-600 disabled:opacity-50"
            >
              {busy ? "Saving…" : "Re-analyse"}
            </button>
            <button
              type="button"
              onClick={() => setSheetOpen(false)}
              disabled={busy}
              className="mt-2 w-full rounded-xl py-2 text-sm text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default LiftTypeLine;
