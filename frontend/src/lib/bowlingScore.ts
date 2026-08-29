/**
 * Ten-pin scoring from printed roll symbols.
 * Port of backend `services/bowling_score.py::score_frames` — the review page
 * scores edits live, the confirm route re-scores server-side, and the two must
 * agree symbol for symbol.
 */

export type Roll = string;

export interface ScoredFrames {
  cumulative: number[];
  total: number;
  valid: boolean;
  errors: string[];
  complete: boolean;
}

export class InvalidFrame extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidFrame";
    Object.setPrototypeOf(this, InvalidFrame.prototype);
  }
}

const normalize = (symbol: Roll): string => symbol.trim().toUpperCase();

const sum = (values: number[]): number => values.reduce((a, b) => a + b, 0);

function pinsFor(symbol: Roll, standing: number | null): number {
  const s = normalize(symbol);
  if (s === "X") return 10;
  if (s === "/") {
    if (standing === null) throw new InvalidFrame("spare with no first ball");
    return 10 - standing;
  }
  if (s === "-" || s === "F" || s === "") return 0;
  if (/^\d+$/.test(s)) {
    const v = Number(s);
    if (v > 9) throw new InvalidFrame(`pin count ${v} out of range`);
    return v;
  }
  throw new InvalidFrame(`unknown symbol "${symbol}"`);
}

/** Pins knocked down per ball. Throws `InvalidFrame` on an impossible frame. */
export function framePins(rolls: Roll[], frameIndex: number): number[] {
  if (rolls.length === 0) throw new InvalidFrame("empty frame");
  const tenth = frameIndex === 9;
  if (rolls.length > (tenth ? 3 : 2)) throw new InvalidFrame("too many rolls");

  const pins: number[] = [];
  // Pins felled by the first ball of the rack in play; null = fresh rack.
  let standing: number | null = null;
  for (const symbol of rolls) {
    const p = pinsFor(symbol, standing);
    if (standing !== null) {
      if (standing + p > 10) throw new InvalidFrame(`${standing}+${p} exceeds 10`);
      standing = null;
    } else if (p < 10) {
      standing = p;
    }
    pins.push(p);
  }

  if (!tenth) {
    if (pins.length === 1 && pins[0] !== 10) {
      throw new InvalidFrame("open frame needs two balls");
    }
    if (pins.length === 2 && pins[0] === 10) {
      throw new InvalidFrame("a strike ends the frame");
    }
    return pins;
  }

  const needsThird = pins[0] === 10 || (pins.length >= 2 && pins[0] + pins[1] === 10);
  if (needsThird && pins.length < 3) {
    throw new InvalidFrame("tenth frame bonus ball missing");
  }
  if (!needsThird && pins.length === 3) {
    throw new InvalidFrame("tenth frame has an extra ball");
  }
  if (pins.length === 1) throw new InvalidFrame("tenth frame needs two balls");
  return pins;
}

/**
 * Running score for up to ten frames. Invalid frames are reported in `errors`
 * (and scored as an open zero) rather than thrown, so a half-typed review row
 * still renders. `complete` is false while any bonus ball is still unthrown.
 */
export function scoreFrames(frames: Roll[][]): ScoredFrames {
  const capped = frames.slice(0, 10);
  const rolls: number[] = [];
  const errors: string[] = [];

  capped.forEach((frame, index) => {
    try {
      rolls.push(...framePins(frame, index));
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      errors.push(`frame ${index + 1}: ${message}`);
      rolls.push(0, 0);
    }
  });

  const cumulative: number[] = [];
  let total = 0;
  let i = 0;
  let complete = capped.length === 10;

  for (let frame = 0; frame < capped.length; frame += 1) {
    if (i >= rolls.length) break;
    const first = rolls[i];
    if (frame === 9) {
      total += sum(rolls.slice(i));
      i = rolls.length;
    } else if (first === 10) {
      const bonus = rolls.slice(i + 1, i + 3);
      if (bonus.length < 2) complete = false;
      total += 10 + sum(bonus);
      i += 1;
    } else if (i + 1 < rolls.length && first + rolls[i + 1] === 10) {
      const bonus = rolls.slice(i + 2, i + 3);
      if (bonus.length === 0) complete = false;
      total += 10 + sum(bonus);
      i += 2;
    } else {
      total += first + (i + 1 < rolls.length ? rolls[i + 1] : 0);
      i += 2;
    }
    cumulative.push(total);
  }

  return { cumulative, total, valid: errors.length === 0, errors, complete };
}

/**
 * Split a typed cell ("X", "9/", "XX8", "F-") into roll symbols. Frames 1-9
 * take two balls, the tenth takes three.
 */
export function parseFrameInput(text: string, frameIndex: number): Roll[] {
  const max = frameIndex === 9 ? 3 : 2;
  return text
    .toUpperCase()
    .split("")
    .filter((c) => c !== " ")
    .slice(0, max);
}

/** Render roll symbols back into a single editable cell string. */
export function formatFrameInput(rolls: Roll[] | null | undefined): string {
  return (rolls || []).map(normalize).join("");
}
