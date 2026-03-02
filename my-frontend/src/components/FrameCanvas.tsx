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
      ctx.moveTo(laneEdges.top_left[0] * scale, laneEdges.top_left[1] * scale);
      ctx.lineTo(laneEdges.top_right[0] * scale, laneEdges.top_right[1] * scale);
      ctx.lineTo(laneEdges.bottom_right[0] * scale, laneEdges.bottom_right[1] * scale);
      ctx.lineTo(laneEdges.bottom_left[0] * scale, laneEdges.bottom_left[1] * scale);
      ctx.closePath();
      ctx.stroke();
    }

    // Draw ball annotation
    if (ball) {
      const bx = ball.x * scale;
      const by = ball.y * scale;
      const br = ball.radius * scale;

      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(bx, by, br, 0, Math.PI * 2);
      ctx.stroke();

      // Crosshair
      ctx.beginPath();
      ctx.moveTo(bx - br, by);
      ctx.lineTo(bx + br, by);
      ctx.moveTo(bx, by - br);
      ctx.lineTo(bx, by + br);
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
