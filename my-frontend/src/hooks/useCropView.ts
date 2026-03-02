import { useMemo } from 'react';
import type { LaneEdges } from '../lib/types';

export interface CropRegion {
  cropX: number;
  cropY: number;
  cropW: number;
  cropH: number;
  frameToDisplay: (fx: number, fy: number, canvasW: number, canvasH: number) => { x: number; y: number };
  displayToFrame: (dx: number, dy: number, canvasW: number, canvasH: number) => { x: number; y: number };
}

export function computeCropRegion(
  laneEdges: LaneEdges | null | undefined,
  frameWidth: number,
  frameHeight: number,
): CropRegion | null {
  if (!laneEdges) return null;

  // Collect all points: 4 corners + optional polylines
  const points: [number, number][] = [
    laneEdges.top_left,
    laneEdges.top_right,
    laneEdges.bottom_left,
    laneEdges.bottom_right,
  ];
  if (laneEdges.left_edge_points) {
    points.push(...laneEdges.left_edge_points);
  }
  if (laneEdges.right_edge_points) {
    points.push(...laneEdges.right_edge_points);
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const [px, py] of points) {
    if (px < minX) minX = px;
    if (py < minY) minY = py;
    if (px > maxX) maxX = px;
    if (py > maxY) maxY = py;
  }

  const bboxW = maxX - minX;
  const bboxH = maxY - minY;

  // 20% padding on each side
  const padX = bboxW * 0.2;
  const padY = bboxH * 0.2;

  // Clamp to frame bounds
  const cropX = Math.max(0, minX - padX);
  const cropY = Math.max(0, minY - padY);
  const cropRight = Math.min(frameWidth, maxX + padX);
  const cropBottom = Math.min(frameHeight, maxY + padY);
  const cropW = cropRight - cropX;
  const cropH = cropBottom - cropY;

  const frameToDisplay = (fx: number, fy: number, canvasW: number, canvasH: number) => ({
    x: (fx - cropX) * (canvasW / cropW),
    y: (fy - cropY) * (canvasH / cropH),
  });

  const displayToFrame = (dx: number, dy: number, canvasW: number, canvasH: number) => ({
    x: cropX + dx * (cropW / canvasW),
    y: cropY + dy * (cropH / canvasH),
  });

  return { cropX, cropY, cropW, cropH, frameToDisplay, displayToFrame };
}

export function useCropView(
  laneEdges: LaneEdges | null | undefined,
  frameWidth: number,
  frameHeight: number,
): CropRegion | null {
  return useMemo(
    () => computeCropRegion(laneEdges, frameWidth, frameHeight),
    [laneEdges, frameWidth, frameHeight],
  );
}
