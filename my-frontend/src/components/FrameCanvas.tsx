import { useRef, useEffect, useCallback } from 'react';
import type { BallAnnotation, LaneEdges } from '../lib/types';
import type { PointHit } from '../hooks/useEdgeEditor';

interface EdgeState {
  edges: LaneEdges | null;
  selectedPoint: PointHit | null;
  isDragging: boolean;
}

export interface CropRegionProp {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface Props {
  image: HTMLImageElement | null;
  ball: BallAnnotation | null | undefined; // null = "no ball", undefined = not annotated
  laneEdges?: LaneEdges;
  radius: number;
  onBallClick: (x: number, y: number) => void;
  onRadiusChange: (delta: number) => void;
  editMode?: 'NORMAL' | 'EDGE_EDIT' | 'EDGE_DRAW';
  edgeState?: EdgeState;
  onEdgeMouseDown?: (x: number, y: number) => void;
  onEdgeMouseMove?: (x: number, y: number) => void;
  onEdgeMouseUp?: () => void;
  onEdgeRightClick?: (x: number, y: number) => void;
  onEdgeShiftClick?: (x: number, y: number) => void;
  cropRegion?: CropRegionProp;
  drawCorners?: [number, number][];
  onDrawClick?: (x: number, y: number) => void;
}

export function FrameCanvas({
  image, ball, laneEdges, radius, onBallClick, onRadiusChange,
  editMode = 'NORMAL', edgeState, onEdgeMouseDown, onEdgeMouseMove, onEdgeMouseUp,
  onEdgeRightClick, onEdgeShiftClick, cropRegion, drawCorners, onDrawClick,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Convert frame coordinate to display (canvas) coordinate
  const frameToDisplay = useCallback((fx: number, fy: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: fx, y: fy };
    if (cropRegion) {
      return {
        x: (fx - cropRegion.x) * (canvas.width / cropRegion.w),
        y: (fy - cropRegion.y) * (canvas.height / cropRegion.h),
      };
    }
    if (!image) return { x: fx, y: fy };
    const scale = canvas.width / image.naturalWidth;
    return { x: fx * scale, y: fy * scale };
  }, [image, cropRegion]);

  // Scale factor for sizes (radius, font, etc.)
  const getDisplayScale = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return 1;
    if (cropRegion) return canvas.width / cropRegion.w;
    if (!image) return 1;
    return canvas.width / image.naturalWidth;
  }, [image, cropRegion]);

  // Render frame + overlays
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !image) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const container = containerRef.current;
    if (container) {
      const maxW = container.clientWidth;
      const maxH = container.clientHeight || window.innerHeight * 0.85;
      const scale = Math.min(maxW / image.naturalWidth, maxH / image.naturalHeight);
      canvas.width = image.naturalWidth * scale;
      canvas.height = image.naturalHeight * scale;
    }

    const scale = getDisplayScale();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw image (cropped or full)
    if (cropRegion) {
      ctx.drawImage(image, cropRegion.x, cropRegion.y, cropRegion.w, cropRegion.h, 0, 0, canvas.width, canvas.height);
    } else {
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    }

    // Helper to convert frame coords to display coords
    const toD = (fx: number, fy: number) => frameToDisplay(fx, fy);

    // Determine which edges to draw
    const edgesToDraw = (editMode === 'EDGE_EDIT' && edgeState?.edges) ? edgeState.edges : laneEdges;

    // Draw lane edges
    if (edgesToDraw) {
      ctx.strokeStyle = 'rgba(0, 100, 255, 0.6)';
      ctx.lineWidth = 2;
      ctx.beginPath();

      // Top edge: top_left -> top_right
      const tl = toD(edgesToDraw.top_left[0], edgesToDraw.top_left[1]);
      const tr = toD(edgesToDraw.top_right[0], edgesToDraw.top_right[1]);
      ctx.moveTo(tl.x, tl.y);
      ctx.lineTo(tr.x, tr.y);

      // Right edge: top_right -> bottom_right (polyline if available)
      if (edgesToDraw.right_edge_points?.length) {
        for (const [px, py] of edgesToDraw.right_edge_points) {
          const d = toD(px, py);
          ctx.lineTo(d.x, d.y);
        }
      } else {
        const br = toD(edgesToDraw.bottom_right[0], edgesToDraw.bottom_right[1]);
        ctx.lineTo(br.x, br.y);
      }

      // Bottom edge: bottom_right -> bottom_left
      const bl = toD(edgesToDraw.bottom_left[0], edgesToDraw.bottom_left[1]);
      ctx.lineTo(bl.x, bl.y);

      // Left edge: bottom_left -> top_left (polyline if available, reversed)
      if (edgesToDraw.left_edge_points?.length) {
        for (const [px, py] of [...edgesToDraw.left_edge_points].reverse()) {
          const d = toD(px, py);
          ctx.lineTo(d.x, d.y);
        }
      } else {
        ctx.lineTo(tl.x, tl.y);
      }

      ctx.closePath();
      ctx.stroke();
    }

    // Draw edge handles in EDGE_EDIT mode
    if (editMode === 'EDGE_EDIT' && edgesToDraw) {
      const selected = edgeState?.selectedPoint;

      // Draw corner handles (8px radius)
      const corners: { key: string; pt: [number, number] }[] = [
        { key: 'top_left', pt: edgesToDraw.top_left },
        { key: 'top_right', pt: edgesToDraw.top_right },
        { key: 'bottom_left', pt: edgesToDraw.bottom_left },
        { key: 'bottom_right', pt: edgesToDraw.bottom_right },
      ];

      for (const corner of corners) {
        const isSelected = selected?.type === 'corner' && selected.key === corner.key;
        const d = toD(corner.pt[0], corner.pt[1]);

        ctx.beginPath();
        ctx.arc(d.x, d.y, 8, 0, Math.PI * 2);
        ctx.fillStyle = isSelected ? 'yellow' : 'cyan';
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Draw polyline handles (6px radius, cyan)
      for (const side of ['left', 'right'] as const) {
        const pts = side === 'left' ? edgesToDraw.left_edge_points : edgesToDraw.right_edge_points;
        if (!pts) continue;
        for (let i = 0; i < pts.length; i++) {
          const d = toD(pts[i][0], pts[i][1]);

          ctx.beginPath();
          ctx.arc(d.x, d.y, 6, 0, Math.PI * 2);
          ctx.fillStyle = 'cyan';
          ctx.fill();
        }
      }
    }

    // Draw ball annotation
    if (ball) {
      const contact = toD(ball.x, ball.y);
      const br = ball.radius * scale;
      const centerY = contact.y - br; // Circle center above contact point

      // Ball circle (green outline)
      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(contact.x, centerY, br, 0, Math.PI * 2);
      ctx.stroke();

      // Contact point dot (solid red, 3px)
      ctx.fillStyle = '#ff0000';
      ctx.beginPath();
      ctx.arc(contact.x, contact.y, 3, 0, Math.PI * 2);
      ctx.fill();

      // Contact point crosshairs (red, ±10px)
      ctx.strokeStyle = '#ff0000';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(contact.x - 10, contact.y);
      ctx.lineTo(contact.x + 10, contact.y);
      ctx.moveTo(contact.x, contact.y - 10);
      ctx.lineTo(contact.x, contact.y + 10);
      ctx.stroke();
    } else if (ball === null) {
      ctx.fillStyle = 'rgba(255, 0, 0, 0.5)';
      ctx.font = `${20 * scale}px sans-serif`;
      ctx.fillText('NO BALL', 10 * scale, 30 * scale);
    }

    // Draw EDGE_DRAW overlays
    if (editMode === 'EDGE_DRAW' && drawCorners) {
      const cornerDescs = [
        'Top Left (near pins, left side)',
        'Top Right (near pins, right side)',
        'Bottom Right (near bowler, right side)',
        'Bottom Left (near bowler, left side)',
      ];

      // Draw placed corners
      for (let i = 0; i < drawCorners.length; i++) {
        const d = toD(drawCorners[i][0], drawCorners[i][1]);

        // Yellow circle
        ctx.beginPath();
        ctx.arc(d.x, d.y, 12, 0, Math.PI * 2);
        ctx.fillStyle = 'yellow';
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 2;
        ctx.stroke();

        // White number label
        ctx.fillStyle = 'white';
        ctx.font = 'bold 14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(i + 1), d.x, d.y);
      }

      // Draw green dashed lines connecting placed corners
      if (drawCorners.length > 1) {
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 4]);
        ctx.beginPath();
        const first = toD(drawCorners[0][0], drawCorners[0][1]);
        ctx.moveTo(first.x, first.y);
        for (let i = 1; i < drawCorners.length; i++) {
          const d = toD(drawCorners[i][0], drawCorners[i][1]);
          ctx.lineTo(d.x, d.y);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Prompt text
      const nextIdx = drawCorners.length;
      if (nextIdx < 4) {
        const prompt = `Click corner ${nextIdx + 1}: ${cornerDescs[nextIdx]}`;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.fillRect(0, 0, canvas.width, 30);
        ctx.fillStyle = 'white';
        ctx.font = 'bold 14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(prompt, canvas.width / 2, 15);
      }

      // Reset text alignment
      ctx.textAlign = 'start';
      ctx.textBaseline = 'alphabetic';
    }
  }, [image, ball, laneEdges, getDisplayScale, frameToDisplay, editMode, edgeState, cropRegion, drawCorners]);

  // Convert mouse event to image (frame) coordinates
  const toImageCoords = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !image) return null;
    const rect = canvas.getBoundingClientRect();
    const displayX = e.clientX - rect.left;
    const displayY = e.clientY - rect.top;
    if (cropRegion) {
      return {
        x: Math.round(cropRegion.x + (displayX / canvas.width) * cropRegion.w),
        y: Math.round(cropRegion.y + (displayY / canvas.height) * cropRegion.h),
      };
    }
    const scale = canvas.width / image.naturalWidth;
    return {
      x: Math.round(displayX / scale),
      y: Math.round(displayY / scale),
    };
  }, [image, cropRegion]);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (editMode === 'EDGE_EDIT') return; // handled by mousedown/up
    const coords = toImageCoords(e);
    if (!coords) return;
    if (editMode === 'EDGE_DRAW' && onDrawClick) {
      onDrawClick(coords.x, coords.y);
      return;
    }
    onBallClick(coords.x, coords.y);
  }, [editMode, toImageCoords, onBallClick, onDrawClick]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (editMode !== 'EDGE_EDIT') return;
    if (e.shiftKey) return; // shift+click handled separately
    const coords = toImageCoords(e);
    if (coords) onEdgeMouseDown?.(coords.x, coords.y);
  }, [editMode, toImageCoords, onEdgeMouseDown]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (editMode !== 'EDGE_EDIT') return;
    const coords = toImageCoords(e);
    if (coords) onEdgeMouseMove?.(coords.x, coords.y);
  }, [editMode, toImageCoords, onEdgeMouseMove]);

  const handleMouseUp = useCallback(() => {
    if (editMode !== 'EDGE_EDIT') return;
    onEdgeMouseUp?.();
  }, [editMode, onEdgeMouseUp]);

  const handleContextMenu = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (editMode !== 'EDGE_EDIT') return;
    e.preventDefault();
    const coords = toImageCoords(e);
    if (coords) onEdgeRightClick?.(coords.x, coords.y);
  }, [editMode, toImageCoords, onEdgeRightClick]);

  const handleShiftClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (editMode !== 'EDGE_EDIT') return;
    if (!e.shiftKey) return;
    const coords = toImageCoords(e);
    if (coords) onEdgeShiftClick?.(coords.x, coords.y);
  }, [editMode, toImageCoords, onEdgeShiftClick]);

  // Register wheel handler imperatively with { passive: false } to allow preventDefault
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      onRadiusChange(e.deltaY > 0 ? -1 : 1);
    };
    canvas.addEventListener('wheel', handler, { passive: false });
    return () => canvas.removeEventListener('wheel', handler);
  }, [onRadiusChange]);

  const isEdgeEdit = editMode === 'EDGE_EDIT';
  const cursorClass = isEdgeEdit
    ? (edgeState?.isDragging ? 'cursor-grabbing' : 'cursor-grab')
    : 'cursor-crosshair'; // crosshair for both NORMAL and EDGE_DRAW

  return (
    <div ref={containerRef} className="w-full h-full flex justify-center items-center bg-black">
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        onMouseDown={(e) => { handleMouseDown(e); handleShiftClick(e); }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onContextMenu={handleContextMenu}
        className={cursorClass}
      />
    </div>
  );
}
