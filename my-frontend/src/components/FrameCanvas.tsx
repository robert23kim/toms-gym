import { useRef, useEffect, useCallback } from 'react';
import type { BallAnnotation, LaneEdges } from '../lib/types';

interface Props {
  image: HTMLImageElement | null;
  ball: BallAnnotation | null | undefined; // null = "no ball", undefined = not annotated
  laneEdges?: LaneEdges;
  radius: number;
  onBallClick: (x: number, y: number) => void;
  onRadiusChange: (delta: number) => void;
}

export function FrameCanvas({ image, ball, laneEdges, radius, onBallClick, onRadiusChange }: Props) {
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

    // Draw lane edges
    if (laneEdges) {
      ctx.strokeStyle = 'rgba(0, 100, 255, 0.6)';
      ctx.lineWidth = 2;
      ctx.beginPath();

      // Top edge: top_left -> top_right
      ctx.moveTo(laneEdges.top_left[0] * scale, laneEdges.top_left[1] * scale);
      ctx.lineTo(laneEdges.top_right[0] * scale, laneEdges.top_right[1] * scale);

      // Right edge: top_right -> bottom_right (polyline if available)
      if (laneEdges.right_edge_points?.length) {
        for (const [px, py] of laneEdges.right_edge_points) {
          ctx.lineTo(px * scale, py * scale);
        }
      } else {
        ctx.lineTo(laneEdges.bottom_right[0] * scale, laneEdges.bottom_right[1] * scale);
      }

      // Bottom edge: bottom_right -> bottom_left
      ctx.lineTo(laneEdges.bottom_left[0] * scale, laneEdges.bottom_left[1] * scale);

      // Left edge: bottom_left -> top_left (polyline if available, reversed)
      if (laneEdges.left_edge_points?.length) {
        for (const [px, py] of [...laneEdges.left_edge_points].reverse()) {
          ctx.lineTo(px * scale, py * scale);
        }
      } else {
        ctx.lineTo(laneEdges.top_left[0] * scale, laneEdges.top_left[1] * scale);
      }

      ctx.closePath();
      ctx.stroke();
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
  }, [image, ball, laneEdges, getScale]);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !image) return;
    const rect = canvas.getBoundingClientRect();
    const scale = getScale();
    const x = Math.round((e.clientX - rect.left) / scale);
    const y = Math.round((e.clientY - rect.top) / scale);
    onBallClick(x, y);
  }, [image, getScale, onBallClick]);

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

  return (
    <div ref={containerRef} className="w-full h-full flex justify-center items-center bg-black">
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        className="cursor-crosshair"
      />
    </div>
  );
}
