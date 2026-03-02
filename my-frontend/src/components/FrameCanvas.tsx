import { useRef, useEffect, useCallback } from 'react';
import type { BallAnnotation, LaneEdges } from '../lib/types';
import type { PointHit } from '../hooks/useEdgeEditor';

interface EdgeState {
  edges: LaneEdges | null;
  selectedPoint: PointHit | null;
  isDragging: boolean;
}

interface Props {
  image: HTMLImageElement | null;
  ball: BallAnnotation | null | undefined; // null = "no ball", undefined = not annotated
  laneEdges?: LaneEdges;
  radius: number;
  onBallClick: (x: number, y: number) => void;
  onRadiusChange: (delta: number) => void;
  editMode?: 'NORMAL' | 'EDGE_EDIT';
  edgeState?: EdgeState;
  onEdgeMouseDown?: (x: number, y: number) => void;
  onEdgeMouseMove?: (x: number, y: number) => void;
  onEdgeMouseUp?: () => void;
  onEdgeRightClick?: (x: number, y: number) => void;
  onEdgeShiftClick?: (x: number, y: number) => void;
}

export function FrameCanvas({
  image, ball, laneEdges, radius, onBallClick, onRadiusChange,
  editMode = 'NORMAL', edgeState, onEdgeMouseDown, onEdgeMouseMove, onEdgeMouseUp,
  onEdgeRightClick, onEdgeShiftClick,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const getScale = useCallback(() => {
    if (!image || !canvasRef.current) return 1;
    return canvasRef.current.width / image.naturalWidth;
  }, [image]);

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

    const scale = getScale();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

    // Determine which edges to draw
    const edgesToDraw = (editMode === 'EDGE_EDIT' && edgeState?.edges) ? edgeState.edges : laneEdges;

    // Draw lane edges
    if (edgesToDraw) {
      ctx.strokeStyle = 'rgba(0, 100, 255, 0.6)';
      ctx.lineWidth = 2;
      ctx.beginPath();

      // Top edge: top_left -> top_right
      ctx.moveTo(edgesToDraw.top_left[0] * scale, edgesToDraw.top_left[1] * scale);
      ctx.lineTo(edgesToDraw.top_right[0] * scale, edgesToDraw.top_right[1] * scale);

      // Right edge: top_right -> bottom_right (polyline if available)
      if (edgesToDraw.right_edge_points?.length) {
        for (const [px, py] of edgesToDraw.right_edge_points) {
          ctx.lineTo(px * scale, py * scale);
        }
      } else {
        ctx.lineTo(edgesToDraw.bottom_right[0] * scale, edgesToDraw.bottom_right[1] * scale);
      }

      // Bottom edge: bottom_right -> bottom_left
      ctx.lineTo(edgesToDraw.bottom_left[0] * scale, edgesToDraw.bottom_left[1] * scale);

      // Left edge: bottom_left -> top_left (polyline if available, reversed)
      if (edgesToDraw.left_edge_points?.length) {
        for (const [px, py] of [...edgesToDraw.left_edge_points].reverse()) {
          ctx.lineTo(px * scale, py * scale);
        }
      } else {
        ctx.lineTo(edgesToDraw.top_left[0] * scale, edgesToDraw.top_left[1] * scale);
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
        const cx = corner.pt[0] * scale;
        const cy = corner.pt[1] * scale;

        ctx.beginPath();
        ctx.arc(cx, cy, 8, 0, Math.PI * 2);
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
          const px = pts[i][0] * scale;
          const py = pts[i][1] * scale;

          ctx.beginPath();
          ctx.arc(px, py, 6, 0, Math.PI * 2);
          ctx.fillStyle = 'cyan';
          ctx.fill();
        }
      }
    }

    // Draw ball annotation
    if (ball) {
      const contactX = ball.x * scale;
      const contactY = ball.y * scale;
      const br = ball.radius * scale;
      const centerY = contactY - br; // Circle center above contact point

      // Ball circle (green outline)
      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(contactX, centerY, br, 0, Math.PI * 2);
      ctx.stroke();

      // Contact point dot (solid red, 3px)
      ctx.fillStyle = '#ff0000';
      ctx.beginPath();
      ctx.arc(contactX, contactY, 3, 0, Math.PI * 2);
      ctx.fill();

      // Contact point crosshairs (red, ±10px)
      ctx.strokeStyle = '#ff0000';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(contactX - 10, contactY);
      ctx.lineTo(contactX + 10, contactY);
      ctx.moveTo(contactX, contactY - 10);
      ctx.lineTo(contactX, contactY + 10);
      ctx.stroke();
    } else if (ball === null) {
      ctx.fillStyle = 'rgba(255, 0, 0, 0.5)';
      ctx.font = `${20 * scale}px sans-serif`;
      ctx.fillText('NO BALL', 10 * scale, 30 * scale);
    }
  }, [image, ball, laneEdges, getScale, editMode, edgeState]);

  // Convert mouse event to image coordinates
  const toImageCoords = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !image) return null;
    const rect = canvas.getBoundingClientRect();
    const scale = getScale();
    return {
      x: Math.round((e.clientX - rect.left) / scale),
      y: Math.round((e.clientY - rect.top) / scale),
    };
  }, [image, getScale]);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (editMode === 'EDGE_EDIT') return; // handled by mousedown/up
    const coords = toImageCoords(e);
    if (coords) onBallClick(coords.x, coords.y);
  }, [editMode, toImageCoords, onBallClick]);

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
    : 'cursor-crosshair';

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
