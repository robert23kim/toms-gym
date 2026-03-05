import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { StatusBar } from '../StatusBar';
import type { BallAnnotation, FrameMarkers } from '../../lib/types';

const defaultProps = {
  currentFrame: 0,
  totalFrames: 60,
  ball: undefined as BallAnnotation | null | undefined,
  markers: {} as FrameMarkers,
  annotatedCount: 0,
  noBallCount: 0,
  editMode: 'NORMAL',
  saving: false,
};

describe('StatusBar', () => {
  test('renders frame counter correctly (1-indexed)', () => {
    render(<StatusBar {...defaultProps} currentFrame={4} totalFrames={60} />);
    expect(screen.getByText('Frame 5 / 60')).toBeInTheDocument();
  });

  test('shows ball coordinates when annotated', () => {
    const ball: BallAnnotation = { x: 150, y: 300, radius: 25 };
    render(<StatusBar {...defaultProps} ball={ball} />);
    expect(screen.getByText('(150, 300) r=25')).toBeInTheDocument();
  });

  test('shows dash when unannotated (undefined)', () => {
    render(<StatusBar {...defaultProps} ball={undefined} />);
    expect(screen.getByText('\u2014')).toBeInTheDocument();
  });

  test('shows "no ball" when ball is null', () => {
    render(<StatusBar {...defaultProps} ball={null} />);
    expect(screen.getByText('no ball')).toBeInTheDocument();
  });

  test('shows marker summary with frame numbers', () => {
    const markers: FrameMarkers = { pin_hit: 42, breakpoint: 15 };
    render(<StatusBar {...defaultProps} markers={markers} />);
    expect(screen.getByText(/PIN:42/)).toBeInTheDocument();
    expect(screen.getByText(/BRE:15/)).toBeInTheDocument();
  });

  test('shows saving indicator when saving=true', () => {
    render(<StatusBar {...defaultProps} saving={true} />);
    expect(screen.getByText('Saving...')).toBeInTheDocument();
  });

  test('does not show saving indicator when saving=false', () => {
    render(<StatusBar {...defaultProps} saving={false} />);
    expect(screen.queryByText('Saving...')).not.toBeInTheDocument();
  });

  test('shows NORMAL mode badge', () => {
    render(<StatusBar {...defaultProps} editMode="NORMAL" />);
    const badge = screen.getByText('NORMAL');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('bg-blue-600');
  });

  test('shows EDGE EDIT mode badge', () => {
    render(<StatusBar {...defaultProps} editMode="EDGE_EDIT" />);
    const badge = screen.getByText('EDGE EDIT');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('bg-yellow-500');
  });

  test('shows DRAW EDGES mode badge', () => {
    render(<StatusBar {...defaultProps} editMode="EDGE_DRAW" />);
    const badge = screen.getByText('DRAW EDGES');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('bg-orange-500');
  });
});
