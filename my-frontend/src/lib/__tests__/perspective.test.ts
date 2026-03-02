import {
  computeHomography,
  transformPoint,
  laneEdgesToTransform,
  laneXToBoard,
  cameraToLane,
} from '../perspective';
import type { LaneEdges } from '../types';

describe('perspective', () => {
  test('identity: square corners map to same square', () => {
    const square = [
      [0, 0],
      [100, 0],
      [100, 100],
      [0, 100],
    ];
    const H = computeHomography(square, square);
    const p1 = transformPoint(H, 0, 0);
    expect(p1.x).toBeCloseTo(0, 5);
    expect(p1.y).toBeCloseTo(0, 5);

    const p2 = transformPoint(H, 50, 50);
    expect(p2.x).toBeCloseTo(50, 5);
    expect(p2.y).toBeCloseTo(50, 5);

    const p3 = transformPoint(H, 100, 100);
    expect(p3.x).toBeCloseTo(100, 5);
    expect(p3.y).toBeCloseTo(100, 5);
  });

  test('lane corners map to expected lane coords', () => {
    const edges: LaneEdges = {
      top_left: [100, 50],
      top_right: [300, 50],
      bottom_right: [350, 500],
      bottom_left: [50, 500],
    };
    const laneW = 390;
    const laneH = 720;
    const H = laneEdgesToTransform(edges, laneW, laneH);

    // top_left -> (laneW, 0)
    const tl = transformPoint(H, 100, 50);
    expect(tl.x).toBeCloseTo(laneW, 1);
    expect(tl.y).toBeCloseTo(0, 1);

    // top_right -> (0, 0)
    const tr = transformPoint(H, 300, 50);
    expect(tr.x).toBeCloseTo(0, 1);
    expect(tr.y).toBeCloseTo(0, 1);

    // bottom_right -> (0, laneH)
    const br = transformPoint(H, 350, 500);
    expect(br.x).toBeCloseTo(0, 1);
    expect(br.y).toBeCloseTo(laneH, 1);

    // bottom_left -> (laneW, laneH)
    const bl = transformPoint(H, 50, 500);
    expect(bl.x).toBeCloseTo(laneW, 1);
    expect(bl.y).toBeCloseTo(laneH, 1);
  });

  test('laneXToBoard: key values', () => {
    const laneW = 390;
    // laneX=0 -> board 1 (right gutter)
    expect(laneXToBoard(0, laneW)).toBe(1);
    // laneX=laneW -> board 39 (left gutter)
    expect(laneXToBoard(laneW, laneW)).toBe(39);
    // laneX=laneW/2 -> board 20 (center)
    expect(laneXToBoard(laneW / 2, laneW)).toBe(20);
  });

  test('laneXToBoard: clamping', () => {
    const laneW = 390;
    // Negative -> 0
    expect(laneXToBoard(-100, laneW)).toBe(0);
    // Way over -> 40
    expect(laneXToBoard(laneW * 2, laneW)).toBe(40);
  });

  test('mid-lane camera point transforms to reasonable lane coords', () => {
    const edges: LaneEdges = {
      top_left: [100, 50],
      top_right: [300, 50],
      bottom_right: [350, 500],
      bottom_left: [50, 500],
    };
    const laneW = 390;
    const laneH = 720;
    const H = laneEdgesToTransform(edges, laneW, laneH);

    // Mid-point of camera view (200, 275) should land roughly mid-lane
    const result = cameraToLane(H, 200, 275, laneW, laneH);
    // Should be within lane bounds
    expect(result.laneX).toBeGreaterThan(0);
    expect(result.laneX).toBeLessThan(laneW);
    expect(result.laneY).toBeGreaterThan(0);
    expect(result.laneY).toBeLessThan(laneH);
    // Board should be reasonable (10-30 range for mid-lane)
    expect(result.board).toBeGreaterThanOrEqual(10);
    expect(result.board).toBeLessThanOrEqual(30);
    // Distance ratio between 0 and 1
    expect(result.distanceRatio).toBeGreaterThan(0);
    expect(result.distanceRatio).toBeLessThan(1);
  });

  test('transform then inverse-transform returns original (roundtrip)', () => {
    const src = [
      [100, 50],
      [300, 50],
      [350, 500],
      [50, 500],
    ];
    const dst = [
      [0, 0],
      [390, 0],
      [390, 720],
      [0, 720],
    ];
    const H = computeHomography(src, dst);
    const Hinv = computeHomography(dst, src);

    // Transform a point forward then back
    const testPoints = [
      [150, 100],
      [250, 300],
      [200, 400],
    ];

    for (const [ox, oy] of testPoints) {
      const fwd = transformPoint(H, ox, oy);
      const back = transformPoint(Hinv, fwd.x, fwd.y);
      expect(back.x).toBeCloseTo(ox, 0); // within 1px
      expect(back.y).toBeCloseTo(oy, 0); // within 1px
    }
  });
});
