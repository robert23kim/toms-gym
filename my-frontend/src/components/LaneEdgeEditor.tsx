import React, { useRef, useEffect, useState, useCallback } from "react";
import { LaneEdges } from "../lib/types";

interface Props {
  frameUrl: string;
  laneEdges: LaneEdges;
  onChange: (edges: LaneEdges) => void;
}

type Corner = "top_left" | "top_right" | "bottom_left" | "bottom_right";

const HANDLE_RADIUS = 8;
const CORNER_COLORS: Record<Corner, string> = {
  top_left: "#ff4444",
  top_right: "#44ff44",
  bottom_left: "#4444ff",
  bottom_right: "#ffff44",
};

const LaneEdgeEditor: React.FC<Props> = ({ frameUrl, laneEdges, onChange }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [dragging, setDragging] = useState<Corner | null>(null);
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 });
  const [edges, setEdges] = useState<LaneEdges>(laneEdges);

  // Load frame image
  useEffect(() => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      imgRef.current = img;
      setImgSize({ w: img.naturalWidth, h: img.naturalHeight });
    };
    img.src = frameUrl;
  }, [frameUrl]);

  // Sync external edge changes
  useEffect(() => {
    setEdges(laneEdges);
  }, [laneEdges]);

  // Draw canvas
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img || !imgSize.w) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const displayW = canvas.clientWidth;
    const displayH = canvas.clientHeight;
    canvas.width = displayW;
    canvas.height = displayH;

    const scaleX = displayW / imgSize.w;
    const scaleY = displayH / imgSize.h;

    // Draw frame
    ctx.drawImage(img, 0, 0, displayW, displayH);

    // Draw trapezoid
    const corners: Corner[] = ["top_left", "top_right", "bottom_right", "bottom_left"];
    ctx.beginPath();
    corners.forEach((c, i) => {
      const [x, y] = edges[c];
      const dx = x * scaleX;
      const dy = y * scaleY;
      if (i === 0) ctx.moveTo(dx, dy);
      else ctx.lineTo(dx, dy);
    });
    ctx.closePath();
    ctx.fillStyle = "rgba(0, 255, 0, 0.15)";
    ctx.fill();
    ctx.strokeStyle = "rgba(0, 255, 0, 0.8)";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw corner handles
    corners.forEach((c) => {
      const [x, y] = edges[c];
      const dx = x * scaleX;
      const dy = y * scaleY;
      ctx.beginPath();
      ctx.arc(dx, dy, HANDLE_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = CORNER_COLORS[c];
      ctx.fill();
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  }, [edges, imgSize]);

  useEffect(() => {
    draw();
  }, [draw]);

  // Find which corner is near a point
  const findCorner = (clientX: number, clientY: number): Corner | null => {
    const canvas = canvasRef.current;
    if (!canvas || !imgSize.w) return null;
    const rect = canvas.getBoundingClientRect();
    const mx = clientX - rect.left;
    const my = clientY - rect.top;
    const scaleX = canvas.clientWidth / imgSize.w;
    const scaleY = canvas.clientHeight / imgSize.h;

    const corners: Corner[] = ["top_left", "top_right", "bottom_left", "bottom_right"];
    for (const c of corners) {
      const [x, y] = edges[c];
      const dx = x * scaleX;
      const dy = y * scaleY;
      const dist = Math.sqrt((mx - dx) ** 2 + (my - dy) ** 2);
      if (dist <= HANDLE_RADIUS * 2) return c;
    }
    return null;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const corner = findCorner(e.clientX, e.clientY);
    if (corner) {
      setDragging(corner);
      e.preventDefault();
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging) return;
    const canvas = canvasRef.current;
    if (!canvas || !imgSize.w) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const scaleX = canvas.clientWidth / imgSize.w;
    const scaleY = canvas.clientHeight / imgSize.h;

    const newX = Math.round(mx / scaleX);
    const newY = Math.round(my / scaleY);
    const clamped: [number, number] = [
      Math.max(0, Math.min(imgSize.w, newX)),
      Math.max(0, Math.min(imgSize.h, newY)),
    ];
    setEdges((prev) => ({ ...prev, [dragging]: clamped }));
  };

  const handleMouseUp = () => {
    if (dragging) {
      onChange(edges);
      setDragging(null);
    }
  };

  return (
    <canvas
      ref={canvasRef}
      className="w-full rounded-lg cursor-crosshair"
      style={{ aspectRatio: imgSize.w && imgSize.h ? `${imgSize.w}/${imgSize.h}` : "16/9" }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    />
  );
};

export default LaneEdgeEditor;
