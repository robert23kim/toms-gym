import type { Annotation, BowlingResult } from "./types";

// Consumer-facing derivations for the bowling result page.
//
// The analysis payload only stores a handful of raw numbers (entry_board,
// board_at_pins, detection_rate, processing_time_s) plus a trajectory PNG and
// the annotated video. It does NOT carry a ball speed or a hook magnitude, so
// anything a bowler actually cares about has to be derived from those fields —
// and where the data can't support a stat we return null and the UI shows "—"
// rather than inventing a number.

/**
 * Below this ball-detection rate the tracker saw the ball in too few frames for
 * the derived stats to be trustworthy, so the result page swaps the numbers for
 * filming tips + a retry CTA (T12). 0.25 = ball tracked in under a quarter of
 * frames; the "1.1% detected" cards seen in the field sit far below this.
 */
export const LOW_DETECTION_THRESHOLD = 0.25;

/**
 * True when detection_rate is present AND below the low-confidence threshold.
 * A missing detection_rate is treated as healthy (no tips) so we never nag on
 * results that simply don't carry the field.
 */
export function isLowDetection(result: BowlingResult): boolean {
  return (
    result.detection_rate != null &&
    result.detection_rate < LOW_DETECTION_THRESHOLD
  );
}

/** 1-3 pocket target board (between board 17 and 18), measured from the right. */
export const POCKET_BOARD = 17.5;
/** How many boards off the pocket still counts as "in the pocket". */
export const POCKET_TOLERANCE = 1.5;

/** Regulation distance, foul line to head pin, in feet. */
const LANE_LENGTH_FT = 60;
/** ft/s -> mph. */
const FPS_TO_MPH = 0.6818182;

/** Entry board the ball crossed at the pins. Falls back to board_at_pins. */
export function deriveEntryBoard(result: BowlingResult): number | null {
  if (result.entry_board != null) return result.entry_board;
  if (result.board_at_pins != null) return result.board_at_pins;
  return null;
}

export interface PocketResult {
  hit: boolean;
  /** Whole boards off the pocket (0 when a hit). */
  boardsOff: number;
  /** "left" | "right" of the pocket; "" on a hit. */
  side: "left" | "right" | "";
  label: string;
}

/**
 * Pocket hit/miss from the entry board. Board numbers increase to the left, so
 * an entry board above the pocket target is left of the pocket and below is
 * right of it. Handedness is unknown, so we describe the miss neutrally rather
 * than guessing "brooklyn" vs "light".
 */
export function derivePocket(entryBoard: number | null): PocketResult | null {
  if (entryBoard == null) return null;
  const off = entryBoard - POCKET_BOARD;
  if (Math.abs(off) <= POCKET_TOLERANCE) {
    return { hit: true, boardsOff: 0, side: "", label: "Pocket" };
  }
  const boardsOff = Math.round(Math.abs(off));
  const side: "left" | "right" = off > 0 ? "left" : "right";
  const noun = boardsOff === 1 ? "board" : "boards";
  return { hit: false, boardsOff, side, label: `${boardsOff} ${noun} ${side}` };
}

/**
 * Estimated ball speed in mph. Needs the ball-down and pin-hit frame markers
 * (from analysis or manual annotation) plus fps to time the ball over the ~60ft
 * lane. Returns null when the markers are missing or the result is implausible
 * (outside 5-40 mph) — we never fabricate a speed from data that can't support it.
 */
export function deriveSpeedMph(annotation: Annotation | null): number | null {
  if (!annotation) return null;
  const fps = annotation.video_metadata?.fps;
  const ballDown = annotation.frame_markers?.ball_down;
  const pinHit = annotation.frame_markers?.pin_hit;
  if (fps == null || fps <= 0) return null;
  if (ballDown == null || pinHit == null) return null;
  if (pinHit <= ballDown) return null;

  const timeS = (pinHit - ballDown) / fps;
  if (timeS <= 0) return null;
  const mph = (LANE_LENGTH_FT / timeS) * FPS_TO_MPH;
  if (mph < 5 || mph > 40) return null;
  return Math.round(mph * 10) / 10;
}

export interface HookResult {
  direction: "left" | "right" | "straight";
  boards: number;
}

/**
 * Coarse hook indicator from the lateral spread between the ball's board at the
 * pin line (board_at_pins) and its entry board. Both are real measured board
 * positions, so their difference is a genuine displacement — but it's a weak
 * signal (the two are often near-identical), so a zero/one-board delta reads as
 * "straight" and a missing field returns null.
 */
export function deriveHook(result: BowlingResult): HookResult | null {
  const { board_at_pins, entry_board } = result;
  if (board_at_pins == null || entry_board == null) return null;
  const delta = board_at_pins - entry_board;
  const boards = Math.round(Math.abs(delta));
  if (boards === 0) return { direction: "straight", boards: 0 };
  return { direction: delta > 0 ? "left" : "right", boards };
}
