/**
 * Crash-surviving upload breadcrumbs.
 *
 * An upload that kills the page (iOS jetsam during compression, WebView
 * renderer crash, tab OOM) can never report its own failure — the JS dies with
 * the tab. So every stage transition is persisted to localStorage as it
 * happens. A journey that ends normally is erased; one still present at the
 * next app boot means the previous session died mid-upload, and telemetry
 * reports it then, with the last stage reached and the file's size/type.
 */

export const JOURNEY_KEY = "tg:upload-journey";

export interface JourneyMeta {
  fileName: string;
  fileSizeMB: number;
  fileType: string;
}

export interface DeadJourney extends JourneyMeta {
  /** Last stage reached before the page died. */
  stage: string;
  /** Every stage reached, in order. */
  stages: string[];
  startedAt: number;
  stageAt: number;
  /** Plus any extra fields merged in via markStage. */
  [key: string]: unknown;
}

function read(): DeadJourney | null {
  try {
    const raw = window.localStorage.getItem(JOURNEY_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as DeadJourney;
  } catch {
    return null;
  }
}

function write(record: DeadJourney): void {
  try {
    window.localStorage.setItem(JOURNEY_KEY, JSON.stringify(record));
  } catch {
    // Storage full/blocked — breadcrumbs are best-effort.
  }
}

/** Start recording an upload. Overwrites any stale journey. */
export function beginJourney(meta: JourneyMeta): void {
  const now = Date.now();
  write({ ...meta, stage: "started", stages: ["started"], startedAt: now, stageAt: now });
}

/** Record reaching `stage`, merging any extra context (method, pct, decision…). */
export function markStage(stage: string, extra?: Record<string, unknown>): void {
  const current = read();
  if (!current) return;
  const stages = Array.isArray(current.stages) ? current.stages : [];
  if (stages[stages.length - 1] !== stage) stages.push(stage);
  write({ ...current, ...extra, stage, stages, stageAt: Date.now() });
}

/** The upload finished (success or a handled, already-reported error). */
export function endJourney(): void {
  try {
    window.localStorage.removeItem(JOURNEY_KEY);
  } catch {
    /* best-effort */
  }
}

/**
 * If a previous session died mid-upload, return its journey and clear it.
 * Returns null when there is nothing (or nothing readable) to report.
 */
export function takeDeadJourney(): DeadJourney | null {
  const record = read();
  endJourney();
  return record;
}
