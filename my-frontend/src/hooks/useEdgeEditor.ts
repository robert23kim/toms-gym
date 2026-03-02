import { useState, useCallback, useRef, useEffect } from 'react';
import type { Annotation, LaneEdges } from '../lib/types';

// --- Hit-test result types ---

export interface PointHit {
  type: 'corner' | 'polyline';
  side: 'left' | 'right';
  index: number;
  key?: string; // corner key e.g. 'top_left'
}

export interface SegmentHit {
  side: 'left' | 'right';
  insertIndex: number;
  distance: number;
}

// --- Pure geometry functions ---

const CORNER_KEYS_LEFT = ['top_left', 'bottom_left'] as const;
const CORNER_KEYS_RIGHT = ['top_right', 'bottom_right'] as const;

const POINT_HIT_RADIUS = 15;
const SEGMENT_HIT_RADIUS = 50;

function dist(ax: number, ay: number, bx: number, by: number): number {
  return Math.sqrt((ax - bx) ** 2 + (ay - by) ** 2);
}

function pointToSegmentDist(
  px: number, py: number,
  ax: number, ay: number,
  bx: number, by: number,
): number {
  const dx = bx - ax;
  const dy = by - ay;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return dist(px, py, ax, ay);
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lenSq));
  return dist(px, py, ax + t * dx, ay + t * dy);
}

function getPolyline(edges: LaneEdges, side: 'left' | 'right'): [number, number][] {
  if (side === 'left') {
    return edges.left_edge_points && edges.left_edge_points.length > 0
      ? edges.left_edge_points
      : [edges.top_left, edges.bottom_left];
  }
  return edges.right_edge_points && edges.right_edge_points.length > 0
    ? edges.right_edge_points
    : [edges.top_right, edges.bottom_right];
}

export function findPointAt(x: number, y: number, edges: LaneEdges): PointHit | null {
  // Check corners first (priority)
  const corners: { key: string; side: 'left' | 'right'; pt: [number, number] }[] = [
    { key: 'top_left', side: 'left', pt: edges.top_left },
    { key: 'top_right', side: 'right', pt: edges.top_right },
    { key: 'bottom_left', side: 'left', pt: edges.bottom_left },
    { key: 'bottom_right', side: 'right', pt: edges.bottom_right },
  ];

  let bestCorner: PointHit | null = null;
  let bestCornerDist = Infinity;

  for (const c of corners) {
    const d = dist(x, y, c.pt[0], c.pt[1]);
    if (d <= POINT_HIT_RADIUS && d < bestCornerDist) {
      bestCornerDist = d;
      bestCorner = {
        type: 'corner',
        side: c.side,
        index: c.key.startsWith('top') ? 0 : 1,
        key: c.key,
      };
    }
  }

  if (bestCorner) return bestCorner;

  // Check polyline points (skip first/last which are corners)
  for (const side of ['left', 'right'] as const) {
    const pts = side === 'left' ? edges.left_edge_points : edges.right_edge_points;
    if (!pts) continue;
    for (let i = 0; i < pts.length; i++) {
      const d = dist(x, y, pts[i][0], pts[i][1]);
      if (d <= POINT_HIT_RADIUS) {
        return { type: 'polyline', side, index: i };
      }
    }
  }

  return null;
}

export function findNearestSegment(x: number, y: number, edges: LaneEdges): SegmentHit | null {
  let best: SegmentHit | null = null;

  for (const side of ['left', 'right'] as const) {
    const pts = getPolyline(edges, side);
    for (let i = 0; i < pts.length - 1; i++) {
      const d = pointToSegmentDist(x, y, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]);
      if (d <= SEGMENT_HIT_RADIUS && (!best || d < best.distance)) {
        best = { side, insertIndex: i + 1, distance: d };
      }
    }
  }

  return best;
}

export function addPolylinePoint(
  edges: LaneEdges, side: 'left' | 'right', insertIndex: number, x: number, y: number,
): LaneEdges {
  const copy = deepCopyEdges(edges);

  if (side === 'left') {
    if (!copy.left_edge_points || copy.left_edge_points.length === 0) {
      copy.left_edge_points = [[...copy.top_left], [...copy.bottom_left]];
    }
    copy.left_edge_points.splice(insertIndex, 0, [x, y]);
  } else {
    if (!copy.right_edge_points || copy.right_edge_points.length === 0) {
      copy.right_edge_points = [[...copy.top_right], [...copy.bottom_right]];
    }
    copy.right_edge_points.splice(insertIndex, 0, [x, y]);
  }

  return copy;
}

export function removePolylinePoint(
  edges: LaneEdges, side: 'left' | 'right', index: number,
): LaneEdges | null {
  const pts = side === 'left' ? edges.left_edge_points : edges.right_edge_points;
  if (!pts || pts.length === 0) return null;

  // Refuse to remove first or last (corner anchors)
  if (index === 0 || index === pts.length - 1) return null;

  const copy = deepCopyEdges(edges);
  if (side === 'left') {
    copy.left_edge_points!.splice(index, 1);
  } else {
    copy.right_edge_points!.splice(index, 1);
  }
  return copy;
}

function deepCopyEdges(edges: LaneEdges): LaneEdges {
  return {
    top_left: [...edges.top_left],
    top_right: [...edges.top_right],
    bottom_left: [...edges.bottom_left],
    bottom_right: [...edges.bottom_right],
    left_edge_points: edges.left_edge_points?.map(p => [...p] as [number, number]),
    right_edge_points: edges.right_edge_points?.map(p => [...p] as [number, number]),
  };
}

// --- React hook ---

interface UseEdgeEditorOpts {
  annotation: Annotation | null;
  currentFrame: number;
  onSave: (frame: number, edges: LaneEdges) => void;
  onDelete: (frame: number) => void;
}

export function useEdgeEditor({ annotation, currentFrame, onSave, onDelete }: UseEdgeEditorOpts) {
  const [selectedPoint, setSelectedPoint] = useState<PointHit | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragEdges, setDragEdges] = useState<LaneEdges | null>(null);
  const prevFrameRef = useRef<number>(currentFrame);

  // Get effective edges for current frame
  const getEffectiveEdges = useCallback((): LaneEdges | null => {
    if (!annotation) return null;
    const frameOverride = annotation.frame_lane_edges?.[String(currentFrame)];
    if (frameOverride) return frameOverride;
    return annotation.lane_edges ?? null;
  }, [annotation, currentFrame]);

  const effectiveEdges = isDragging && dragEdges ? dragEdges : getEffectiveEdges();

  // Edge propagation: copy edges forward on +1 frame advance
  useEffect(() => {
    const prev = prevFrameRef.current;
    prevFrameRef.current = currentFrame;

    if (!annotation) return;
    // Only propagate on forward +1 navigation
    if (currentFrame !== prev + 1) return;

    // If next frame already has an override, don't propagate
    if (annotation.frame_lane_edges?.[String(currentFrame)]) return;

    // If previous frame had an override, copy it forward
    const prevOverride = annotation.frame_lane_edges?.[String(prev)];
    if (prevOverride) {
      onSave(currentFrame, deepCopyEdges(prevOverride));
    }
  }, [currentFrame, annotation, onSave]);

  const handleMouseDown = useCallback((x: number, y: number) => {
    const edges = getEffectiveEdges();
    if (!edges) return;

    const hit = findPointAt(x, y, edges);
    if (!hit) return;

    setSelectedPoint(hit);
    setIsDragging(true);
    setDragEdges(deepCopyEdges(edges));
  }, [getEffectiveEdges]);

  const handleMouseMove = useCallback((x: number, y: number) => {
    if (!isDragging || !selectedPoint || !dragEdges) return;

    const updated = deepCopyEdges(dragEdges);

    if (selectedPoint.type === 'corner' && selectedPoint.key) {
      // Update the corner
      const key = selectedPoint.key as keyof Pick<LaneEdges, 'top_left' | 'top_right' | 'bottom_left' | 'bottom_right'>;
      updated[key] = [x, y];

      // Also update matching polyline endpoint
      const side = selectedPoint.side;
      const pts = side === 'left' ? updated.left_edge_points : updated.right_edge_points;
      if (pts && pts.length > 0) {
        if (selectedPoint.key.startsWith('top')) {
          pts[0] = [x, y];
        } else {
          pts[pts.length - 1] = [x, y];
        }
      }
    } else if (selectedPoint.type === 'polyline') {
      const pts = selectedPoint.side === 'left' ? updated.left_edge_points : updated.right_edge_points;
      if (pts && pts[selectedPoint.index]) {
        pts[selectedPoint.index] = [x, y];
      }
    }

    setDragEdges(updated);
  }, [isDragging, selectedPoint, dragEdges]);

  const handleMouseUp = useCallback(() => {
    if (!isDragging || !dragEdges) {
      setIsDragging(false);
      setSelectedPoint(null);
      return;
    }

    onSave(currentFrame, dragEdges);
    setIsDragging(false);
    setSelectedPoint(null);
    setDragEdges(null);
  }, [isDragging, dragEdges, currentFrame, onSave]);

  const handleRightClick = useCallback((x: number, y: number) => {
    const edges = getEffectiveEdges();
    if (!edges) return;

    const seg = findNearestSegment(x, y, edges);
    if (!seg) return;

    const updated = addPolylinePoint(edges, seg.side, seg.insertIndex, x, y);
    onSave(currentFrame, updated);
  }, [getEffectiveEdges, currentFrame, onSave]);

  const handleShiftClick = useCallback((x: number, y: number) => {
    const edges = getEffectiveEdges();
    if (!edges) return;

    const hit = findPointAt(x, y, edges);
    if (!hit || hit.type !== 'polyline') return;

    const updated = removePolylinePoint(edges, hit.side, hit.index);
    if (updated) {
      onSave(currentFrame, updated);
    }
  }, [getEffectiveEdges, currentFrame, onSave]);

  const resetEdges = useCallback(() => {
    onDelete(currentFrame);
  }, [currentFrame, onDelete]);

  const ensureFrameEdges = useCallback(() => {
    const edges = getEffectiveEdges();
    if (!edges) return;

    // If there's already a per-frame override, nothing to do
    if (annotation?.frame_lane_edges?.[String(currentFrame)]) return;

    onSave(currentFrame, deepCopyEdges(edges));
  }, [getEffectiveEdges, annotation, currentFrame, onSave]);

  return {
    effectiveEdges,
    selectedPoint,
    isDragging,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleRightClick,
    handleShiftClick,
    resetEdges,
    ensureFrameEdges,
  };
}
