/**
 * Timing for one successful upload, reported as a single `upload-timing`
 * telemetry event. The backend only sees sign → finalize; the time a phone
 * spends compressing before the first byte and the real transfer rate are only
 * measurable here.
 */

export type TransferPath = "single-put" | "resumable" | "parallel" | "resumable-fallback";
export type TransferPhase = "sign" | "put" | "complete" | "finalize";
export type CompressPipeline = "webcodecs" | "mediarecorder";

/** Wraps one network phase of a transfer so its duration is recorded. */
export type PhaseTimer = <T>(phase: TransferPhase, run: () => Promise<T>) => Promise<T>;

export const untimed: PhaseTimer = (_phase, run) => run();

export interface UploadTimer {
  time: PhaseTimer;
  /** Milliseconds per phase, summed when a phase runs more than once. */
  phases(): Partial<Record<TransferPhase, number>>;
}

export function createUploadTimer(now: () => number = () => performance.now()): UploadTimer {
  const totals: Partial<Record<TransferPhase, number>> = {};
  return {
    time: async (phase, run) => {
      const start = now();
      try {
        return await run();
      } finally {
        totals[phase] = (totals[phase] ?? 0) + (now() - start);
      }
    },
    phases: () => ({ ...totals }),
  };
}

/**
 * Count how often the page went to the background while uploading: a hidden
 * tab throttles timers and can stall a transfer, which otherwise reads as a
 * slow network. Call the returned function to stop and get the count.
 */
export function watchHidden(doc: Document = document): () => number {
  let hidden = 0;
  const onChange = (): void => {
    if (doc.visibilityState === "hidden") hidden += 1;
  };
  doc.addEventListener("visibilitychange", onChange);
  return () => {
    doc.removeEventListener("visibilitychange", onChange);
    return hidden;
  };
}

interface NetworkInformationLike {
  type?: string;
  effectiveType?: string;
  downlink?: number;
}

/** Network hints where the browser exposes them (Chrome/Android; not iOS). */
export function networkHints(nav: Navigator = navigator): {
  netType: string | null;
  netEffective: string | null;
  netDownMbps: number | null;
} {
  const conn = (nav as Navigator & { connection?: NetworkInformationLike }).connection;
  return {
    netType: conn?.type ?? null,
    netEffective: conn?.effectiveType ?? null,
    netDownMbps: typeof conn?.downlink === "number" ? conn.downlink : null,
  };
}

export interface UploadTimingInput {
  liftType: string;
  /** Compression mode the caller asked for. */
  mode: string;
  /**
   * What compression did: `skipped:<reason>` (never attempted), `kept-original`
   * (attempted, no usable gain), or the pipeline that produced the sent file.
   */
  compress: `skipped:${string}` | "kept-original" | CompressPipeline;
  compressMs: number;
  path: TransferPath;
  srcBytes: number;
  sentBytes: number;
  srcType: string;
  sentType: string;
  phases: Partial<Record<TransferPhase, number>>;
  /** Everything after compression: sign + put + compose + finalize. */
  transferMs: number;
  totalMs: number;
  hiddenCount: number;
}

export type UploadTimingDetails = Record<string, string | number | null>;

const ms = (value: number | undefined): number | null =>
  typeof value === "number" && Number.isFinite(value) ? Math.round(value) : null;

/** Megabits per second for `bytes` sent in `millis`; null when unmeasurable. */
export function megabitsPerSecond(bytes: number, millis: number | undefined): number | null {
  if (typeof millis !== "number" || !Number.isFinite(millis) || millis <= 0) return null;
  return Number(((bytes * 8) / 1_000_000 / (millis / 1000)).toFixed(2));
}

/** Flatten one upload's measurements into the telemetry `details` object. */
export function buildUploadTiming(input: UploadTimingInput): UploadTimingDetails {
  return {
    liftType: input.liftType,
    mode: input.mode,
    compress: input.compress,
    path: input.path,
    srcBytes: input.srcBytes,
    sentBytes: input.sentBytes,
    srcType: input.srcType,
    sentType: input.sentType,
    compressMs: ms(input.compressMs),
    signMs: ms(input.phases.sign),
    putMs: ms(input.phases.put),
    completeMs: ms(input.phases.complete),
    finalizeMs: ms(input.phases.finalize),
    transferMs: ms(input.transferMs),
    totalMs: ms(input.totalMs),
    putMbps: megabitsPerSecond(input.sentBytes, input.phases.put),
    hiddenCount: input.hiddenCount,
  };
}
