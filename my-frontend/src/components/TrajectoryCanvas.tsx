import { useRef, useEffect } from 'react';
import type { BallAnnotation, LaneEdges, FrameMarkers } from '../lib/types';
import { laneEdgesToTransform, cameraToLane } from '../lib/perspective';

interface TrajectoryCanvasProps {
  annotations: Record<string, BallAnnotation | null>;
  laneEdges: LaneEdges | null;
  frameMarkers?: FrameMarkers;
  totalFrames: number;
  currentFrame: number;
  width?: number;
  height?: number;
  canvasRef?: React.RefObject<HTMLCanvasElement>;
}

// Plot coordinate ranges
const PLOT_X_MIN = -2;
const PLOT_X_MAX = 41;
const PLOT_Y_MIN = -0.1;
const PLOT_Y_MAX = 1.1;

const LANE_WIDTH_PX = 390;
const LANE_HEIGHT_PX = 720;

// Colors
const GUTTER_COLOR = '#8B7355';
const LANE_COLOR = '#F5DEB3';
const THIN_LINE_COLOR = '#D2B48C';
const THICK_LINE_COLOR = '#8B4513';
const CENTER_LINE_COLOR = '#CD853F';
const TRAJECTORY_COLOR = '#0066CC';
const START_COLOR = '#66B2FF';
const END_COLOR = '#003366';
const CURRENT_FRAME_COLOR = '#FFD700';

interface LanePoint {
  frame: number;
  board: number;
  distanceRatio: number;
  plotX: number;
  plotY: number;
}

export function TrajectoryCanvas({
  annotations,
  laneEdges,
  frameMarkers: _frameMarkers,
  totalFrames: _totalFrames,
  currentFrame,
  width = 200,
  height = 500,
  canvasRef: externalRef,
}: TrajectoryCanvasProps) {
  const internalRef = useRef<HTMLCanvasElement>(null);
  const ref = externalRef ?? internalRef;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !laneEdges) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;

    // Coordinate mapping: plot coords -> canvas pixels
    const toCanvasX = (px: number) =>
      ((px - PLOT_X_MIN) / (PLOT_X_MAX - PLOT_X_MIN)) * width;
    const toCanvasY = (py: number) =>
      ((py - PLOT_Y_MIN) / (PLOT_Y_MAX - PLOT_Y_MIN)) * height;

    ctx.clearRect(0, 0, width, height);

    // --- Lane background ---
    // Left gutter
    ctx.fillStyle = GUTTER_COLOR;
    ctx.fillRect(toCanvasX(-2), toCanvasY(PLOT_Y_MIN), toCanvasX(0) - toCanvasX(-2), height);

    // Lane surface
    ctx.fillStyle = LANE_COLOR;
    ctx.fillRect(toCanvasX(0), toCanvasY(PLOT_Y_MIN), toCanvasX(39) - toCanvasX(0), height);

    // Right gutter
    ctx.fillStyle = GUTTER_COLOR;
    ctx.fillRect(toCanvasX(39), toCanvasY(PLOT_Y_MIN), toCanvasX(41) - toCanvasX(39), height);

    // --- Board lines ---
    for (let board = 1; board <= 39; board++) {
      const x = toCanvasX(39 - board);

      if (board === 20) {
        // Center line: dashed
        ctx.strokeStyle = CENTER_LINE_COLOR;
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(x, toCanvasY(PLOT_Y_MIN));
        ctx.lineTo(x, toCanvasY(PLOT_Y_MAX));
        ctx.stroke();
        ctx.setLineDash([]);
      } else if (board % 5 === 0) {
        // Every 5 boards: thicker
        ctx.strokeStyle = THICK_LINE_COLOR;
        ctx.globalAlpha = 0.6;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, toCanvasY(PLOT_Y_MIN));
        ctx.lineTo(x, toCanvasY(PLOT_Y_MAX));
        ctx.stroke();
        ctx.globalAlpha = 1;
      } else {
        // Every board: thin
        ctx.strokeStyle = THIN_LINE_COLOR;
        ctx.globalAlpha = 0.4;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(x, toCanvasY(PLOT_Y_MIN));
        ctx.lineTo(x, toCanvasY(PLOT_Y_MAX));
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
    }

    // --- Board numbers at top and bottom ---
    const boardLabels = [1, 5, 10, 15, 20, 25, 30, 35, 39];
    ctx.fillStyle = '#333';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'center';
    for (const b of boardLabels) {
      const x = toCanvasX(39 - b);
      ctx.fillText(String(b), x, toCanvasY(PLOT_Y_MIN) + 10);
      ctx.fillText(String(b), x, toCanvasY(PLOT_Y_MAX) - 3);
    }

    // --- Labels ---
    ctx.fillStyle = '#666';
    ctx.font = 'bold 10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('PINS', toCanvasX(19.5), toCanvasY(PLOT_Y_MIN) + 22);
    ctx.fillText('FOUL LINE', toCanvasX(19.5), toCanvasY(PLOT_Y_MAX) - 12);

    // --- Transform annotations to lane coords ---
    const H = laneEdgesToTransform(laneEdges, LANE_WIDTH_PX, LANE_HEIGHT_PX);
    const points: LanePoint[] = [];

    for (const [frameStr, ball] of Object.entries(annotations)) {
      if (!ball) continue;
      const frame = parseInt(frameStr, 10);
      if (isNaN(frame)) continue;

      const { board, distanceRatio } = cameraToLane(
        H, ball.x, ball.y, LANE_WIDTH_PX, LANE_HEIGHT_PX,
      );
      const plotX = 39 - board;
      const plotY = 1 - distanceRatio;
      points.push({ frame, board, distanceRatio, plotX, plotY });
    }

    points.sort((a, b) => a.frame - b.frame);

    if (points.length > 0) {
      // --- Trajectory polyline ---
      ctx.strokeStyle = TRAJECTORY_COLOR;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(toCanvasX(points[0].plotX), toCanvasY(points[0].plotY));
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(toCanvasX(points[i].plotX), toCanvasY(points[i].plotY));
      }
      ctx.stroke();

      // --- Frame dots every 10 frames ---
      ctx.fillStyle = TRAJECTORY_COLOR;
      for (const pt of points) {
        if (pt.frame % 10 === 0) {
          ctx.beginPath();
          ctx.arc(toCanvasX(pt.plotX), toCanvasY(pt.plotY), 4, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // --- Start marker (light blue circle) ---
      ctx.fillStyle = START_COLOR;
      ctx.beginPath();
      ctx.arc(toCanvasX(points[0].plotX), toCanvasY(points[0].plotY), 6, 0, Math.PI * 2);
      ctx.fill();

      // --- End marker (dark blue square) ---
      const last = points[points.length - 1];
      ctx.fillStyle = END_COLOR;
      const ex = toCanvasX(last.plotX);
      const ey = toCanvasY(last.plotY);
      ctx.fillRect(ex - 6, ey - 6, 12, 12);

      // --- Current frame highlight ---
      const currentStr = String(currentFrame);
      const currentAnnotation = annotations[currentStr];
      if (currentAnnotation) {
        const { board: cBoard, distanceRatio: cDist } = cameraToLane(
          H, currentAnnotation.x, currentAnnotation.y, LANE_WIDTH_PX, LANE_HEIGHT_PX,
        );
        const cpx = 39 - cBoard;
        const cpy = 1 - cDist;
        ctx.fillStyle = CURRENT_FRAME_COLOR;
        ctx.beginPath();
        ctx.arc(toCanvasX(cpx), toCanvasY(cpy), 8, 0, Math.PI * 2);
        ctx.fill();
      }

      // --- Info text ---
      const entryBoard = points[0].board;
      const exitBoard = last.board;
      ctx.fillStyle = '#333';
      ctx.font = '9px sans-serif';
      ctx.textAlign = 'left';
      const infoY = toCanvasY(PLOT_Y_MAX) - 24;
      ctx.fillText(`Entry: Bd ${entryBoard}`, toCanvasX(0) + 2, infoY);
      ctx.fillText(`Exit: Bd ${exitBoard}`, toCanvasX(0) + 2, infoY + 11);
      ctx.fillText(`${points.length} annotated`, toCanvasX(0) + 2, infoY + 22);
    }
  }, [annotations, laneEdges, currentFrame, width, height, ref]);

  if (!laneEdges) {
    return (
      <div
        data-testid="trajectory-placeholder"
        className="flex items-center justify-center text-gray-400 text-sm p-4"
        style={{ width, height }}
      >
        No lane edges available
      </div>
    );
  }

  return (
    <canvas
      ref={ref}
      width={width}
      height={height}
      className="border border-gray-300 rounded"
    />
  );
}
