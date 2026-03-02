import { renderHook, act } from '@testing-library/react';
import {
  findPointAt,
  findNearestSegment,
  addPolylinePoint,
  removePolylinePoint,
  useEdgeEditor,
} from '../useEdgeEditor';
import type { LaneEdges, Annotation } from '../../lib/types';

// --- Test fixtures ---

function makeEdges(overrides?: Partial<LaneEdges>): LaneEdges {
  return {
    top_left: [100, 50],
    top_right: [300, 50],
    bottom_left: [50, 400],
    bottom_right: [350, 400],
    ...overrides,
  };
}

function makeEdgesWithPolylines(): LaneEdges {
  return {
    top_left: [100, 50],
    top_right: [300, 50],
    bottom_left: [50, 400],
    bottom_right: [350, 400],
    left_edge_points: [[100, 50], [80, 200], [50, 400]],
    right_edge_points: [[300, 50], [320, 200], [350, 400]],
  };
}

function makeAnnotation(overrides?: Partial<Annotation>): Annotation {
  return {
    version: '1.0',
    video_metadata: { fps: 30, total_frames: 60, width: 1920, height: 1080 },
    ball_annotations: {},
    frame_markers: {},
    lane_edges: makeEdges(),
    frame_lane_edges: {},
    ...overrides,
  };
}

// --- Pure geometry function tests ---

describe('findPointAt', () => {
  test('1. returns correct corner within 15px', () => {
    const edges = makeEdges();
    // Click 10px away from top_left (100, 50)
    const hit = findPointAt(110, 50, edges);
    expect(hit).not.toBeNull();
    expect(hit!.type).toBe('corner');
    expect(hit!.key).toBe('top_left');
    expect(hit!.side).toBe('left');
  });

  test('2. returns null beyond 15px', () => {
    const edges = makeEdges();
    // Click 20px away from any corner
    const hit = findPointAt(130, 50, edges);
    expect(hit).toBeNull();
  });

  test('3. prefers corners over polyline points when both within 15px', () => {
    // Place a polyline point at exactly the same location as top_left
    const edges = makeEdgesWithPolylines();
    // left_edge_points[0] = [100, 50] = same as top_left
    const hit = findPointAt(105, 50, edges);
    expect(hit).not.toBeNull();
    expect(hit!.type).toBe('corner');
    expect(hit!.key).toBe('top_left');
  });
});

describe('findNearestSegment', () => {
  test('4. returns correct insert index for mid-segment click', () => {
    const edges = makeEdgesWithPolylines();
    // Click near the midpoint of left edge segment [0]->[1] i.e. (100,50) -> (80,200)
    // Midpoint is roughly (90, 125)
    const hit = findNearestSegment(90, 125, edges);
    expect(hit).not.toBeNull();
    expect(hit!.side).toBe('left');
    expect(hit!.insertIndex).toBe(1);
  });

  test('5. returns null beyond 50px', () => {
    const edges = makeEdgesWithPolylines();
    // Click far from any edge
    const hit = findNearestSegment(500, 500, edges);
    expect(hit).toBeNull();
  });
});

describe('addPolylinePoint', () => {
  test('6. inserts at correct segment index', () => {
    const edges = makeEdgesWithPolylines();
    const updated = addPolylinePoint(edges, 'left', 1, 90, 125);
    expect(updated.left_edge_points).toHaveLength(4);
    expect(updated.left_edge_points![1]).toEqual([90, 125]);
    // Original points shift
    expect(updated.left_edge_points![0]).toEqual([100, 50]);
    expect(updated.left_edge_points![2]).toEqual([80, 200]);
    expect(updated.left_edge_points![3]).toEqual([50, 400]);
  });

  test('7. on left side does not affect right side', () => {
    const edges = makeEdgesWithPolylines();
    const updated = addPolylinePoint(edges, 'left', 1, 90, 125);
    expect(updated.right_edge_points).toEqual(edges.right_edge_points);
    // Also verify original is not mutated
    expect(edges.left_edge_points).toHaveLength(3);
  });
});

describe('removePolylinePoint', () => {
  test('8. removes intermediate point', () => {
    const edges = makeEdgesWithPolylines();
    const updated = removePolylinePoint(edges, 'left', 1);
    expect(updated).not.toBeNull();
    expect(updated!.left_edge_points).toHaveLength(2);
    expect(updated!.left_edge_points![0]).toEqual([100, 50]);
    expect(updated!.left_edge_points![1]).toEqual([50, 400]);
  });

  test('9. refuses to remove first/last (corner anchors)', () => {
    const edges = makeEdgesWithPolylines();
    expect(removePolylinePoint(edges, 'left', 0)).toBeNull();
    expect(removePolylinePoint(edges, 'left', 2)).toBeNull();
  });
});

// --- React hook tests ---

describe('useEdgeEditor hook', () => {
  const mockSave = jest.fn();
  const mockDelete = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  function renderEdgeEditor(
    annotation: Annotation | null = makeAnnotation(),
    currentFrame = 0,
  ) {
    const props = { annotation, currentFrame, onSave: mockSave, onDelete: mockDelete };
    return renderHook(
      ({ annotation, currentFrame }) => useEdgeEditor({
        annotation,
        currentFrame,
        onSave: mockSave,
        onDelete: mockDelete,
      }),
      { initialProps: { annotation: props.annotation, currentFrame: props.currentFrame } },
    );
  }

  test('10. startDrag -> updateDrag -> endDrag -> final position correct', () => {
    const anno = makeAnnotation({
      lane_edges: makeEdgesWithPolylines(),
    });
    const { result } = renderEdgeEditor(anno, 0);

    // Click on the polyline midpoint (80, 200) = left_edge_points[1]
    act(() => { result.current.handleMouseDown(80, 200); });
    expect(result.current.isDragging).toBe(true);

    act(() => { result.current.handleMouseMove(90, 210); });
    act(() => { result.current.handleMouseMove(95, 220); });

    act(() => { result.current.handleMouseUp(); });
    expect(result.current.isDragging).toBe(false);

    // Save should have been called with final drag position
    expect(mockSave).toHaveBeenCalledTimes(1);
    const savedEdges = mockSave.mock.calls[0][1] as LaneEdges;
    expect(savedEdges.left_edge_points![1]).toEqual([95, 220]);
  });

  test('11. dragging corner updates matching polyline endpoint', () => {
    const anno = makeAnnotation({
      lane_edges: makeEdgesWithPolylines(),
    });
    const { result } = renderEdgeEditor(anno, 0);

    // Click on top_left corner (100, 50)
    act(() => { result.current.handleMouseDown(100, 50); });
    act(() => { result.current.handleMouseMove(110, 60); });
    act(() => { result.current.handleMouseUp(); });

    const savedEdges = mockSave.mock.calls[0][1] as LaneEdges;
    // Corner should be updated
    expect(savedEdges.top_left).toEqual([110, 60]);
    // Polyline first point should also be updated
    expect(savedEdges.left_edge_points![0]).toEqual([110, 60]);
  });

  test('12. endDrag triggers save callback', () => {
    const anno = makeAnnotation({
      lane_edges: makeEdgesWithPolylines(),
    });
    const { result } = renderEdgeEditor(anno, 5);

    act(() => { result.current.handleMouseDown(80, 200); });
    act(() => { result.current.handleMouseMove(85, 205); });
    act(() => { result.current.handleMouseUp(); });

    expect(mockSave).toHaveBeenCalledTimes(1);
    expect(mockSave.mock.calls[0][0]).toBe(5); // frame number
  });

  test('13. ensureFrameEdges creates deep copy, mutations do not affect original', () => {
    const globalEdges = makeEdges();
    const anno = makeAnnotation({ lane_edges: globalEdges });
    const { result } = renderEdgeEditor(anno, 0);

    act(() => { result.current.ensureFrameEdges(); });

    expect(mockSave).toHaveBeenCalledTimes(1);
    const savedEdges = mockSave.mock.calls[0][1] as LaneEdges;

    // Should be equal in value
    expect(savedEdges.top_left).toEqual(globalEdges.top_left);
    // But NOT the same reference
    expect(savedEdges.top_left).not.toBe(globalEdges.top_left);

    // Mutating the saved copy should not affect original
    savedEdges.top_left[0] = 999;
    expect(globalEdges.top_left[0]).toBe(100);
  });

  test('14. effectiveEdges returns per-frame override when present, global otherwise', () => {
    const globalEdges = makeEdges();
    const frameEdges = makeEdges({ top_left: [999, 999] });
    const anno = makeAnnotation({
      lane_edges: globalEdges,
      frame_lane_edges: { '5': frameEdges },
    });

    // Frame 0: no override, should return global
    const { result, rerender } = renderEdgeEditor(anno, 0);
    expect(result.current.effectiveEdges?.top_left).toEqual([100, 50]);

    // Frame 5: has override, should return per-frame
    rerender({ annotation: anno, currentFrame: 5 });
    expect(result.current.effectiveEdges?.top_left).toEqual([999, 999]);
  });

  test('15. edge propagation fires on forward +1 nav, creates copy for next frame', () => {
    const frameEdges = makeEdges({ top_left: [111, 222] });
    const anno = makeAnnotation({
      frame_lane_edges: { '3': frameEdges },
    });

    const { rerender } = renderEdgeEditor(anno, 3);

    // Navigate forward +1 to frame 4 (no override exists for frame 4)
    rerender({ annotation: anno, currentFrame: 4 });

    expect(mockSave).toHaveBeenCalledTimes(1);
    expect(mockSave.mock.calls[0][0]).toBe(4);
    const propagated = mockSave.mock.calls[0][1] as LaneEdges;
    expect(propagated.top_left).toEqual([111, 222]);
    // Deep copy, not reference
    expect(propagated.top_left).not.toBe(frameEdges.top_left);
  });

  test('16. edge propagation does NOT fire on backward nav or jump', () => {
    const frameEdges = makeEdges({ top_left: [111, 222] });
    const anno = makeAnnotation({
      frame_lane_edges: { '5': frameEdges },
    });

    const { rerender } = renderEdgeEditor(anno, 5);

    // Navigate backward to frame 4
    rerender({ annotation: anno, currentFrame: 4 });
    expect(mockSave).not.toHaveBeenCalled();

    // Jump from frame 4 to frame 10
    rerender({ annotation: anno, currentFrame: 10 });
    expect(mockSave).not.toHaveBeenCalled();
  });
});
