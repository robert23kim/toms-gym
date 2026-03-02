import type { BallAnnotation, FrameMarkers } from '../lib/types';

interface StatusBarProps {
  currentFrame: number;
  totalFrames: number;
  ball: BallAnnotation | null | undefined;
  markers: FrameMarkers;
  annotatedCount: number;
  noBallCount: number;
  editMode: string;
  saving: boolean;
}

const MARKER_ABBREV: Record<string, string> = {
  pin_hit: 'PIN',
  breakpoint: 'BRE',
  ball_down: 'BAL',
  ball_off_deck: 'OFF',
};

export function StatusBar({ currentFrame, totalFrames, ball, markers, annotatedCount, noBallCount, editMode, saving }: StatusBarProps) {
  const ballInfo = ball
    ? `(${ball.x}, ${ball.y}) r=${ball.radius}`
    : ball === null
    ? 'no ball'
    : '\u2014';

  const markerSummary = Object.entries(MARKER_ABBREV)
    .map(([key, abbrev]) => {
      const val = markers[key as keyof FrameMarkers];
      return `${abbrev}:${val !== undefined ? val : '\u2014'}`;
    })
    .join(' ');

  const modeBadgeClass = editMode === 'EDGE_EDIT'
    ? 'px-2 py-0.5 rounded text-xs font-bold bg-yellow-500 text-black'
    : 'px-2 py-0.5 rounded text-xs font-bold bg-blue-600';

  return (
    <div className="flex items-center justify-between px-4 py-1 bg-gray-800 border-b border-gray-700 text-sm text-gray-300" data-testid="status-bar">
      <div className="flex items-center gap-2">
        <span>Frame {currentFrame + 1} / {totalFrames}</span>
        <span className="text-gray-600">|</span>
        <span>{ballInfo}</span>
      </div>
      <div>
        <span className={modeBadgeClass}>{editMode === 'EDGE_EDIT' ? 'EDGE EDIT' : 'NORMAL'}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs">{markerSummary}</span>
        <span className="text-gray-600">|</span>
        <span>Annotated: {annotatedCount} | No ball: {noBallCount}</span>
        {saving && <span className="text-yellow-400 ml-2">Saving...</span>}
      </div>
    </div>
  );
}
