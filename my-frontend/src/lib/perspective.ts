import type { LaneEdges } from './types';

/**
 * Solve an 8x8 linear system via Gaussian elimination with partial pivoting.
 * A is modified in place. Returns solution vector x.
 */
function solveLinearSystem(A: number[][], b: number[]): number[] {
  const n = A.length;
  // Augment matrix
  for (let i = 0; i < n; i++) {
    A[i].push(b[i]);
  }

  // Forward elimination with partial pivoting
  for (let col = 0; col < n; col++) {
    // Find pivot
    let maxRow = col;
    let maxVal = Math.abs(A[col][col]);
    for (let row = col + 1; row < n; row++) {
      const val = Math.abs(A[row][col]);
      if (val > maxVal) {
        maxVal = val;
        maxRow = row;
      }
    }
    // Swap rows
    if (maxRow !== col) {
      [A[col], A[maxRow]] = [A[maxRow], A[col]];
    }

    const pivot = A[col][col];
    if (Math.abs(pivot) < 1e-12) {
      throw new Error('Singular matrix in homography computation');
    }

    // Eliminate below
    for (let row = col + 1; row < n; row++) {
      const factor = A[row][col] / pivot;
      for (let j = col; j <= n; j++) {
        A[row][j] -= factor * A[col][j];
      }
    }
  }

  // Back substitution
  const x = new Array(n).fill(0);
  for (let i = n - 1; i >= 0; i--) {
    let sum = A[i][n];
    for (let j = i + 1; j < n; j++) {
      sum -= A[i][j] * x[j];
    }
    x[i] = sum / A[i][i];
  }

  return x;
}

/**
 * Compute a 3x3 homography matrix H such that for each point pair
 * (sx,sy) -> (dx,dy):
 *   dx = (h1*sx + h2*sy + h3) / (h7*sx + h8*sy + 1)
 *   dy = (h4*sx + h5*sy + h6) / (h7*sx + h8*sy + 1)
 *
 * src and dst are arrays of 4 points: [[x,y], [x,y], [x,y], [x,y]]
 */
export function computeHomography(src: number[][], dst: number[][]): number[][] {
  if (src.length !== 4 || dst.length !== 4) {
    throw new Error('computeHomography requires exactly 4 point pairs');
  }

  // Build 8x8 system: Ah = b
  // For each point pair (sx,sy) -> (dx,dy):
  //   sx*h1 + sy*h2 + h3 + 0 + 0 + 0 - dx*sx*h7 - dx*sy*h8 = dx
  //   0 + 0 + 0 + sx*h4 + sy*h5 + h6 - dy*sx*h7 - dy*sy*h8 = dy
  const A: number[][] = [];
  const b: number[] = [];

  for (let i = 0; i < 4; i++) {
    const [sx, sy] = src[i];
    const [dx, dy] = dst[i];

    A.push([sx, sy, 1, 0, 0, 0, -dx * sx, -dx * sy]);
    b.push(dx);

    A.push([0, 0, 0, sx, sy, 1, -dy * sx, -dy * sy]);
    b.push(dy);
  }

  const h = solveLinearSystem(A, b);

  // Build 3x3 matrix (h9 = 1)
  return [
    [h[0], h[1], h[2]],
    [h[3], h[4], h[5]],
    [h[6], h[7], 1],
  ];
}

/**
 * Apply homography H to point (x, y).
 * [x', y', w'] = H * [x, y, 1]
 * Returns (x'/w', y'/w')
 */
export function transformPoint(H: number[][], x: number, y: number): { x: number; y: number } {
  const xp = H[0][0] * x + H[0][1] * y + H[0][2];
  const yp = H[1][0] * x + H[1][1] * y + H[1][2];
  const wp = H[2][0] * x + H[2][1] * y + H[2][2];

  return { x: xp / wp, y: yp / wp };
}

/**
 * Build a homography from lane edge corners to a rectangular lane coordinate system.
 * src: [top_left, top_right, bottom_right, bottom_left]
 * dst: [(laneWidth,0), (0,0), (0,laneHeight), (laneWidth,laneHeight)]
 *
 * The dst mapping means:
 *   top_left (camera left at top/foul line) -> (laneWidth, 0) = board 39 side, distance 0
 *   top_right (camera right at top/foul line) -> (0, 0) = board 1 side, distance 0
 *   bottom_right -> (0, laneHeight) = board 1 side, pins
 *   bottom_left -> (laneWidth, laneHeight) = board 39 side, pins
 */
export function laneEdgesToTransform(
  edges: LaneEdges,
  laneWidthPx: number = 390,
  laneHeightPx: number = 720,
): number[][] {
  const src = [
    edges.top_left,
    edges.top_right,
    edges.bottom_right,
    edges.bottom_left,
  ];

  const dst = [
    [laneWidthPx, 0],
    [0, 0],
    [0, laneHeightPx],
    [laneWidthPx, laneHeightPx],
  ];

  return computeHomography(src, dst);
}

/**
 * Convert a lane X coordinate to board number (1-39).
 * Board 1 = right gutter (laneX=0), Board 39 = left gutter (laneX=laneWidth).
 * Clamped to 0-40 range.
 */
export function laneXToBoard(laneX: number, laneWidth: number): number {
  const board = Math.round((laneX / laneWidth) * 38 + 1);
  return Math.max(0, Math.min(40, board));
}

/**
 * Transform a camera-space point to lane coordinates and compute board/distance.
 */
export function cameraToLane(
  H: number[][],
  cameraX: number,
  cameraY: number,
  laneWidth: number,
  laneHeight: number,
): { laneX: number; laneY: number; board: number; distanceRatio: number } {
  const { x: laneX, y: laneY } = transformPoint(H, cameraX, cameraY);
  const board = laneXToBoard(laneX, laneWidth);
  const distanceRatio = Math.max(0, Math.min(1, laneY / laneHeight));

  return { laneX, laneY, board, distanceRatio };
}
