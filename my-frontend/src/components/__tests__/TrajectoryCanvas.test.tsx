import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TrajectoryCanvas } from '../TrajectoryCanvas';
import type { LaneEdges } from '../../lib/types';

const mockCtx: Record<string, any> = {
  clearRect: jest.fn(),
  fillRect: jest.fn(),
  drawImage: jest.fn(),
  beginPath: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  arc: jest.fn(),
  stroke: jest.fn(),
  fill: jest.fn(),
  fillText: jest.fn(),
  closePath: jest.fn(),
  setLineDash: jest.fn(),
  strokeStyle: '',
  fillStyle: '',
  lineWidth: 0,
  font: '',
  textAlign: 'start',
  globalAlpha: 1,
};

beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = jest.fn().mockReturnValue(mockCtx) as any;
});

beforeEach(() => {
  jest.clearAllMocks();
  mockCtx.globalAlpha = 1;
});

const sampleEdges: LaneEdges = {
  top_left: [100, 50],
  top_right: [300, 50],
  bottom_right: [350, 500],
  bottom_left: [50, 500],
};

describe('TrajectoryCanvas', () => {
  test('renders "No lane edges available" when laneEdges is null', () => {
    const { getByText } = render(
      <TrajectoryCanvas
        annotations={{}}
        laneEdges={null}
        totalFrames={100}
        currentFrame={0}
      />
    );
    expect(getByText('No lane edges available')).toBeInTheDocument();
  });

  test('renders canvas element when laneEdges provided', () => {
    const { container } = render(
      <TrajectoryCanvas
        annotations={{ '5': { x: 200, y: 300, radius: 15 } }}
        laneEdges={sampleEdges}
        totalFrames={100}
        currentFrame={5}
      />
    );
    const canvas = container.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
  });

  test('no errors when annotations is empty object', () => {
    expect(() => {
      render(
        <TrajectoryCanvas
          annotations={{}}
          laneEdges={sampleEdges}
          totalFrames={100}
          currentFrame={0}
        />
      );
    }).not.toThrow();
  });

  test('placeholder has correct data-testid', () => {
    const { getByTestId } = render(
      <TrajectoryCanvas
        annotations={{}}
        laneEdges={null}
        totalFrames={100}
        currentFrame={0}
      />
    );
    expect(getByTestId('trajectory-placeholder')).toBeInTheDocument();
  });
});
