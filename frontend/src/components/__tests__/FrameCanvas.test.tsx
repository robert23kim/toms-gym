import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FrameCanvas } from '../FrameCanvas';

// Track style/property assignments
let styleLog: Record<string, string | number> = {};

const mockCtx: Record<string, any> = {
  clearRect: jest.fn(),
  drawImage: jest.fn(),
  beginPath: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  arc: jest.fn(),
  stroke: jest.fn(),
  fill: jest.fn(),
  fillText: jest.fn(),
  closePath: jest.fn(),
  set strokeStyle(v: string) { styleLog.strokeStyle = v; },
  get strokeStyle() { return styleLog.strokeStyle as string ?? ''; },
  set fillStyle(v: string) { styleLog.fillStyle = v; },
  get fillStyle() { return styleLog.fillStyle as string ?? ''; },
  set lineWidth(v: number) { styleLog.lineWidth = v; },
  get lineWidth() { return styleLog.lineWidth as number ?? 0; },
  set font(v: string) { styleLog.font = v; },
  get font() { return styleLog.font as string ?? ''; },
};

beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = jest.fn().mockReturnValue(mockCtx) as any;
});

beforeEach(() => {
  jest.clearAllMocks();
  styleLog = {};

  // Mock container dimensions so scale is computable.
  // clientWidth=960, clientHeight=540 with 1920x1080 image => scale = 0.5
  Object.defineProperty(HTMLDivElement.prototype, 'clientWidth', { value: 960, configurable: true });
  Object.defineProperty(HTMLDivElement.prototype, 'clientHeight', { value: 540, configurable: true });
});

function createMockImage(width = 1920, height = 1080): HTMLImageElement {
  const img = new Image();
  Object.defineProperty(img, 'naturalWidth', { value: width });
  Object.defineProperty(img, 'naturalHeight', { value: height });
  return img;
}

const noop = () => {};

describe('FrameCanvas', () => {
  test('ball circle Y center = contactY - radius', () => {
    const image = createMockImage();
    // scale = min(960/1920, 540/1080) = 0.5
    const ball = { x: 500, y: 800, radius: 25 };

    render(
      <FrameCanvas
        image={image}
        ball={ball}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
      />
    );

    // Two arc calls: ball circle then contact dot
    const arcCalls = mockCtx.arc.mock.calls;
    expect(arcCalls.length).toBeGreaterThanOrEqual(2);

    // Ball circle: arc(contactX, contactY - br, br, 0, 2*PI)
    // contactX = 500*0.5 = 250, contactY = 800*0.5 = 400, br = 25*0.5 = 12.5
    // centerY = 400 - 12.5 = 387.5
    const ballCircleCall = arcCalls[0];
    expect(ballCircleCall[0]).toBe(250);     // x = contactX
    expect(ballCircleCall[1]).toBe(387.5);   // y = contactY - br
    expect(ballCircleCall[2]).toBe(12.5);    // radius = br
  });

  test('ball circle Y center = contactY when radius is 0', () => {
    const image = createMockImage();
    const ball = { x: 500, y: 800, radius: 0 };

    render(
      <FrameCanvas
        image={image}
        ball={ball}
        radius={0}
        onBallClick={noop}
        onRadiusChange={noop}
      />
    );

    const arcCalls = mockCtx.arc.mock.calls;
    expect(arcCalls.length).toBeGreaterThanOrEqual(2);

    // Ball circle: radius=0 => centerY = contactY - 0 = contactY
    // contactY = 800*0.5 = 400
    const ballCircleCall = arcCalls[0];
    expect(ballCircleCall[0]).toBe(250);   // contactX = 500*0.5
    expect(ballCircleCall[1]).toBe(400);   // contactY (no offset)
    expect(ballCircleCall[2]).toBe(0);     // radius = 0
  });

  test('contact dot position = (x, y) unchanged', () => {
    const image = createMockImage();
    const ball = { x: 500, y: 800, radius: 25 };

    render(
      <FrameCanvas
        image={image}
        ball={ball}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
      />
    );

    const arcCalls = mockCtx.arc.mock.calls;
    // Second arc call = contact dot (radius 3)
    const dotCall = arcCalls[1];
    expect(dotCall[0]).toBe(250);   // contactX = 500*0.5
    expect(dotCall[1]).toBe(400);   // contactY = 800*0.5 (not shifted)
    expect(dotCall[2]).toBe(3);     // fixed 3px radius
  });

  test('crosshair lines span +/-10px from contact point', () => {
    const image = createMockImage();
    const ball = { x: 500, y: 800, radius: 25 };

    render(
      <FrameCanvas
        image={image}
        ball={ball}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
      />
    );

    // contactX = 250, contactY = 400 (scaled)
    const moveToCalls = mockCtx.moveTo.mock.calls;
    const lineToCalls = mockCtx.lineTo.mock.calls;

    // Crosshair horizontal: moveTo(contactX-10, contactY), lineTo(contactX+10, contactY)
    // Crosshair vertical: moveTo(contactX, contactY-10), lineTo(contactX, contactY+10)
    // These are the LAST moveTo/lineTo pairs (after lane edges if any, but no lane edges here)
    const lastMoves = moveToCalls.slice(-2);
    const lastLines = lineToCalls.slice(-2);

    // Horizontal crosshair
    expect(lastMoves[0]).toEqual([240, 400]);  // contactX-10, contactY
    expect(lastLines[0]).toEqual([260, 400]);  // contactX+10, contactY

    // Vertical crosshair
    expect(lastMoves[1]).toEqual([250, 390]);  // contactX, contactY-10
    expect(lastLines[1]).toEqual([250, 410]);  // contactX, contactY+10
  });

  test('"NO BALL" rendered when ball is null', () => {
    const image = createMockImage();

    render(
      <FrameCanvas
        image={image}
        ball={null}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
      />
    );

    expect(mockCtx.fillText).toHaveBeenCalledWith('NO BALL', expect.any(Number), expect.any(Number));
    // No arc calls for ball
    expect(mockCtx.arc).not.toHaveBeenCalled();
  });

  test('no ball overlay when ball is undefined', () => {
    const image = createMockImage();

    render(
      <FrameCanvas
        image={image}
        ball={undefined}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
      />
    );

    // No arc calls (no ball circle, no contact dot)
    expect(mockCtx.arc).not.toHaveBeenCalled();
    // No fillText (no "NO BALL" text)
    expect(mockCtx.fillText).not.toHaveBeenCalled();
  });

  test('handles rendered when editMode=EDGE_EDIT, not when NORMAL', () => {
    const image = createMockImage();
    const edges = {
      top_left: [100, 50] as [number, number],
      top_right: [300, 50] as [number, number],
      bottom_left: [50, 500] as [number, number],
      bottom_right: [350, 500] as [number, number],
    };

    // NORMAL mode: no handle arc calls (no ball either)
    render(
      <FrameCanvas
        image={image}
        ball={undefined}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
        editMode="NORMAL"
        edgeState={{ edges, selectedPoint: null, isDragging: false }}
      />
    );
    expect(mockCtx.arc).not.toHaveBeenCalled();

    jest.clearAllMocks();

    // EDGE_EDIT mode: should draw corner handle arcs (4 corners x 8px radius)
    render(
      <FrameCanvas
        image={image}
        ball={undefined}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
        editMode="EDGE_EDIT"
        edgeState={{ edges, selectedPoint: null, isDragging: false }}
      />
    );
    const arcCalls = mockCtx.arc.mock.calls;
    // 4 corner handles at radius 8
    const handleCalls = arcCalls.filter((c: number[]) => c[2] === 8);
    expect(handleCalls.length).toBe(4);
  });

  test('drawImage called with crop source rect when cropRegion set', () => {
    const image = createMockImage();
    const cropRegion = { x: 100, y: 50, w: 400, h: 300 };

    render(
      <FrameCanvas
        image={image}
        ball={undefined}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
        cropRegion={cropRegion}
      />
    );

    // drawImage should be called with 9 args (source rect + dest rect)
    const drawCalls = mockCtx.drawImage.mock.calls;
    expect(drawCalls.length).toBe(1);
    const call = drawCalls[0];
    // drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh)
    expect(call[0]).toBe(image);
    expect(call[1]).toBe(100);  // sx = cropRegion.x
    expect(call[2]).toBe(50);   // sy = cropRegion.y
    expect(call[3]).toBe(400);  // sw = cropRegion.w
    expect(call[4]).toBe(300);  // sh = cropRegion.h
    expect(call[5]).toBe(0);    // dx
    expect(call[6]).toBe(0);    // dy
  });

  test('drawImage called with full image when cropRegion not set', () => {
    const image = createMockImage();

    render(
      <FrameCanvas
        image={image}
        ball={undefined}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
      />
    );

    // drawImage should be called with 4 args (img, 0, 0, canvasW, canvasH)
    const drawCalls = mockCtx.drawImage.mock.calls;
    expect(drawCalls.length).toBe(1);
    const call = drawCalls[0];
    expect(call[0]).toBe(image);
    expect(call[1]).toBe(0);
    expect(call[2]).toBe(0);
    // drawImage(img, 0, 0, canvasW, canvasH) = 5 args (no source rect)
    expect(call.length).toBe(5);
  });

  test('cursor class is cursor-crosshair in normal mode, cursor-grab in edge mode', () => {
    const image = createMockImage();

    // Normal mode
    const { container: c1 } = render(
      <FrameCanvas
        image={image}
        ball={undefined}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
        editMode="NORMAL"
      />
    );
    const canvas1 = c1.querySelector('canvas');
    expect(canvas1?.className).toContain('cursor-crosshair');

    // Edge edit mode (not dragging)
    const { container: c2 } = render(
      <FrameCanvas
        image={image}
        ball={undefined}
        radius={25}
        onBallClick={noop}
        onRadiusChange={noop}
        editMode="EDGE_EDIT"
        edgeState={{ edges: null, selectedPoint: null, isDragging: false }}
      />
    );
    const canvas2 = c2.querySelector('canvas');
    expect(canvas2?.className).toContain('cursor-grab');
  });
});
