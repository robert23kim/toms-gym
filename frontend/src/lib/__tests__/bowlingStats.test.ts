import {
  deriveEntryBoard,
  derivePocket,
  deriveSpeedMph,
  deriveHook,
  isLowDetection,
  LOW_DETECTION_THRESHOLD,
} from "../bowlingStats";
import type { Annotation, BowlingResult } from "../types";

function makeResult(overrides: Partial<BowlingResult> = {}): BowlingResult {
  return {
    id: "r1",
    attempt_id: "a1",
    processing_status: "completed",
    ...overrides,
  };
}

function makeAnnotation(overrides: Partial<Annotation> = {}): Annotation {
  return {
    version: "1.0",
    video_metadata: { fps: 30, total_frames: 120, width: 1920, height: 1080 },
    frame_markers: {},
    ball_annotations: {},
    ...overrides,
  };
}

describe("deriveEntryBoard", () => {
  test("prefers entry_board", () => {
    expect(deriveEntryBoard(makeResult({ entry_board: 17, board_at_pins: 20 }))).toBe(17);
  });
  test("falls back to board_at_pins", () => {
    expect(deriveEntryBoard(makeResult({ board_at_pins: 20 }))).toBe(20);
  });
  test("null when neither present", () => {
    expect(deriveEntryBoard(makeResult())).toBeNull();
  });
});

describe("derivePocket", () => {
  test("in-tolerance board is a pocket hit", () => {
    const p = derivePocket(18);
    expect(p?.hit).toBe(true);
    expect(p?.label).toBe("Pocket");
  });
  test("high entry board reads as boards left of pocket", () => {
    const p = derivePocket(22);
    expect(p?.hit).toBe(false);
    expect(p?.side).toBe("left");
    expect(p?.label).toBe("5 boards left");
  });
  test("low entry board reads as boards right of pocket", () => {
    const p = derivePocket(13);
    expect(p?.side).toBe("right");
    expect(p?.label).toBe("5 boards right");
  });
  test("just outside tolerance reads as a whole-board miss", () => {
    expect(derivePocket(19.5)?.label).toBe("2 boards left");
  });
  test("null entry board yields null", () => {
    expect(derivePocket(null)).toBeNull();
  });
});

describe("deriveSpeedMph", () => {
  test("times the ball over the lane between markers", () => {
    // 45 frames at 30fps = 1.5s over 60ft => 40 ft/s => ~27.3 mph
    const a = makeAnnotation({ frame_markers: { ball_down: 0, pin_hit: 45 } });
    expect(deriveSpeedMph(a)).toBeCloseTo(27.3, 1);
  });
  test("null without both markers", () => {
    expect(deriveSpeedMph(makeAnnotation({ frame_markers: { ball_down: 0 } }))).toBeNull();
  });
  test("null when pin_hit precedes ball_down", () => {
    const a = makeAnnotation({ frame_markers: { ball_down: 50, pin_hit: 10 } });
    expect(deriveSpeedMph(a)).toBeNull();
  });
  test("rejects implausible (too fast) speeds", () => {
    // 2 frames at 30fps = 0.067s => way over 40 mph
    const a = makeAnnotation({ frame_markers: { ball_down: 0, pin_hit: 2 } });
    expect(deriveSpeedMph(a)).toBeNull();
  });
  test("null annotation yields null", () => {
    expect(deriveSpeedMph(null)).toBeNull();
  });
});

describe("deriveHook", () => {
  test("equal boards read as straight", () => {
    expect(deriveHook(makeResult({ board_at_pins: 17, entry_board: 17 }))).toEqual({
      direction: "straight",
      boards: 0,
    });
  });
  test("left displacement", () => {
    expect(deriveHook(makeResult({ board_at_pins: 20, entry_board: 15 }))).toEqual({
      direction: "left",
      boards: 5,
    });
  });
  test("right displacement", () => {
    expect(deriveHook(makeResult({ board_at_pins: 12, entry_board: 18 }))).toEqual({
      direction: "right",
      boards: 6,
    });
  });
  test("null when a board is missing", () => {
    expect(deriveHook(makeResult({ entry_board: 17 }))).toBeNull();
  });
});

describe("isLowDetection (T12 filming-tips gate)", () => {
  test("shows tips below the threshold", () => {
    expect(isLowDetection(makeResult({ detection_rate: 0.011 }))).toBe(true);
    expect(
      isLowDetection(makeResult({ detection_rate: LOW_DETECTION_THRESHOLD - 0.01 }))
    ).toBe(true);
  });
  test("hides tips at or above the threshold", () => {
    expect(isLowDetection(makeResult({ detection_rate: LOW_DETECTION_THRESHOLD }))).toBe(false);
    expect(isLowDetection(makeResult({ detection_rate: 0.9 }))).toBe(false);
  });
  test("hides tips when detection_rate is absent (treated as healthy)", () => {
    expect(isLowDetection(makeResult())).toBe(false);
  });
});
