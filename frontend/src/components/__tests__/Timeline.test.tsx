import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Timeline } from '../Timeline';
import type { Annotation } from '../../lib/types';

const makeAnnotation = (
  ballAnnotations: Record<string, any> = {},
  frameMarkers: Record<string, number> = {},
): Annotation => ({
  version: '1.0',
  video_metadata: { fps: 30, total_frames: 10, width: 1920, height: 1080 },
  ball_annotations: ballAnnotations,
  frame_markers: frameMarkers as any,
});

describe('Timeline', () => {
  const onFrameClick = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders correct number of frame indicators', () => {
    render(
      <Timeline
        totalFrames={10}
        currentFrame={0}
        annotation={makeAnnotation()}
        onFrameClick={onFrameClick}
      />
    );

    // Each frame gets a div with title="Frame N" (1-indexed display)
    for (let i = 1; i <= 10; i++) {
      expect(screen.getByTitle(`Frame ${i}`)).toBeInTheDocument();
    }
    // Should not have frame 11
    expect(screen.queryByTitle('Frame 11')).not.toBeInTheDocument();
  });

  test('displays frame numbers as 1-indexed', () => {
    render(
      <Timeline
        totalFrames={10}
        currentFrame={0}
        annotation={makeAnnotation()}
        onFrameClick={onFrameClick}
      />
    );

    // Status text shows "Frame 1 / 10" (1-indexed for display)
    expect(screen.getByText('Frame 1 / 10')).toBeInTheDocument();
  });

  test('frame 5 shows as "Frame 6 / 10" in display', () => {
    render(
      <Timeline
        totalFrames={10}
        currentFrame={5}
        annotation={makeAnnotation()}
        onFrameClick={onFrameClick}
      />
    );

    expect(screen.getByText('Frame 6 / 10')).toBeInTheDocument();
  });

  test('green for annotated, gray for no-ball, dark for unannotated', () => {
    const annotation = makeAnnotation({
      '0': { x: 100, y: 200, radius: 25 },  // annotated → green
      '1': null,                               // no ball → gray
      // '2' missing → unannotated → dark gray
    });

    const { container } = render(
      <Timeline
        totalFrames={3}
        currentFrame={0}
        annotation={annotation}
        onFrameClick={onFrameClick}
      />
    );

    const frameIndicators = container.querySelectorAll('[title^="Frame"]');
    expect(frameIndicators).toHaveLength(3);

    // Frame 1 (index 0): ball annotated → bg-green-500
    expect(frameIndicators[0].className).toContain('bg-green-500');
    // Frame 2 (index 1): no ball → bg-gray-500
    expect(frameIndicators[1].className).toContain('bg-gray-500');
    // Frame 3 (index 2): unannotated → bg-gray-700
    expect(frameIndicators[2].className).toContain('bg-gray-700');
  });

  test('clicking a frame calls onFrameClick with 0-indexed frame', () => {
    render(
      <Timeline
        totalFrames={10}
        currentFrame={0}
        annotation={makeAnnotation()}
        onFrameClick={onFrameClick}
      />
    );

    // Click "Frame 3" (which is 0-indexed frame 2)
    fireEvent.click(screen.getByTitle('Frame 3'));
    expect(onFrameClick).toHaveBeenCalledWith(2);  // 0-indexed

    // Click "Frame 1" (0-indexed frame 0)
    fireEvent.click(screen.getByTitle('Frame 1'));
    expect(onFrameClick).toHaveBeenCalledWith(0);
  });

  test('current frame has ring highlight', () => {
    const { container } = render(
      <Timeline
        totalFrames={5}
        currentFrame={2}
        annotation={makeAnnotation()}
        onFrameClick={onFrameClick}
      />
    );

    const frameIndicators = container.querySelectorAll('[title^="Frame"]');
    // Frame 3 (index 2) should have ring
    expect(frameIndicators[2].className).toContain('ring-2');
    // Other frames should not
    expect(frameIndicators[0].className).not.toContain('ring-2');
    expect(frameIndicators[1].className).not.toContain('ring-2');
  });
});
