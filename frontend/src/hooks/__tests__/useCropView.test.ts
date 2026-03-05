import { computeCropRegion } from '../useCropView';
import type { LaneEdges } from '../../lib/types';

function makeEdges(overrides?: Partial<LaneEdges>): LaneEdges {
  return {
    top_left: [100, 50],
    top_right: [300, 50],
    bottom_left: [50, 400],
    bottom_right: [350, 400],
    ...overrides,
  };
}

describe('computeCropRegion', () => {
  it('returns null when no lane edges', () => {
    expect(computeCropRegion(null, 1920, 1080)).toBeNull();
    expect(computeCropRegion(undefined, 1920, 1080)).toBeNull();
  });

  it('computes bounding box correctly from 4 corners', () => {
    const edges = makeEdges();
    const result = computeCropRegion(edges, 1920, 1080)!;
    // bbox: x=[50,350], y=[50,400] -> w=300, h=350
    // padding: 20% of 300=60, 20% of 350=70
    // cropX = 50-60 = -10 -> clamped to 0
    // cropY = 50-70 = -20 -> clamped to 0
    // cropRight = 350+60 = 410
    // cropBottom = 400+70 = 470
    expect(result.cropX).toBe(0);
    expect(result.cropY).toBe(0);
    expect(result.cropW).toBe(410);
    expect(result.cropH).toBe(470);
  });

  it('applies 20% padding on each side', () => {
    // Use edges far from frame boundaries so clamping doesn't affect padding
    const edges = makeEdges({
      top_left: [500, 300],
      top_right: [700, 300],
      bottom_left: [500, 500],
      bottom_right: [700, 500],
    });
    const result = computeCropRegion(edges, 1920, 1080)!;
    // bbox: x=[500,700], y=[300,500] -> w=200, h=200
    // padding: 20% of 200=40 each side
    expect(result.cropX).toBe(460); // 500 - 40
    expect(result.cropY).toBe(260); // 300 - 40
    expect(result.cropW).toBe(280); // 740 - 460
    expect(result.cropH).toBe(280); // 540 - 260
  });

  it('clamps to frame dimensions (no negative coords, no overflow)', () => {
    // Edges near the frame boundaries
    const edges = makeEdges({
      top_left: [10, 5],
      top_right: [1910, 5],
      bottom_left: [10, 1075],
      bottom_right: [1910, 1075],
    });
    const result = computeCropRegion(edges, 1920, 1080)!;
    // bbox: x=[10,1910]=1900, y=[5,1075]=1070
    // pad: 20%*1900=380, 20%*1070=214
    // Would be: x=10-380=-370, y=5-214=-209, right=1910+380=2290, bottom=1075+214=1289
    // Clamped: x=0, y=0, right=1920, bottom=1080
    expect(result.cropX).toBe(0);
    expect(result.cropY).toBe(0);
    expect(result.cropW).toBe(1920);
    expect(result.cropH).toBe(1080);
  });

  it('includes polyline points in bounding box', () => {
    const edges = makeEdges({
      top_left: [500, 300],
      top_right: [700, 300],
      bottom_left: [500, 500],
      bottom_right: [700, 500],
      // Left polyline extends further left than corners
      left_edge_points: [[500, 300], [400, 400], [500, 500]],
    });
    const result = computeCropRegion(edges, 1920, 1080)!;
    // bbox: x=[400,700]=300, y=[300,500]=200
    // padding: 20% of 300=60, 20% of 200=40
    expect(result.cropX).toBe(340); // 400 - 60
    expect(result.cropY).toBe(260); // 300 - 40
    expect(result.cropW).toBe(420); // 760 - 340
    expect(result.cropH).toBe(280); // 540 - 260
  });

  it('frameToDisplay and displayToFrame are inverses (roundtrip)', () => {
    const edges = makeEdges({
      top_left: [500, 300],
      top_right: [700, 300],
      bottom_left: [500, 500],
      bottom_right: [700, 500],
    });
    const result = computeCropRegion(edges, 1920, 1080)!;
    const canvasW = 800;
    const canvasH = 600;

    // Frame -> Display -> Frame roundtrip
    const fx = 600, fy = 400;
    const display = result.frameToDisplay(fx, fy, canvasW, canvasH);
    const back = result.displayToFrame(display.x, display.y, canvasW, canvasH);
    expect(back.x).toBeCloseTo(fx, 5);
    expect(back.y).toBeCloseTo(fy, 5);

    // Display -> Frame -> Display roundtrip
    const dx = 200, dy = 150;
    const frame = result.displayToFrame(dx, dy, canvasW, canvasH);
    const backD = result.frameToDisplay(frame.x, frame.y, canvasW, canvasH);
    expect(backD.x).toBeCloseTo(dx, 5);
    expect(backD.y).toBeCloseTo(dy, 5);
  });
});
