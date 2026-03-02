import type { FrameMarkers } from '../lib/types';

interface Props {
  markers: FrameMarkers;
  currentFrame: number;  // 0-indexed
  onSetMarker: (name: string, frame: number) => void;
  onClearMarker: (name: string) => void;
  onGoToFrame: (frame: number) => void;
}

const MARKER_DEFS = [
  { key: 'ball_down', label: 'Ball Down', color: 'text-blue-400', hotkey: 'G' },
  { key: 'breakpoint', label: 'Breakpoint', color: 'text-yellow-400', hotkey: 'B' },
  { key: 'pin_hit', label: 'Pin Hit', color: 'text-red-400', hotkey: 'P' },
  { key: 'ball_off_deck', label: 'Off Deck', color: 'text-purple-400', hotkey: 'O' },
];

export function MarkerPanel({ markers, currentFrame, onSetMarker, onClearMarker, onGoToFrame }: Props) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3">
      <h3 className="text-sm font-semibold text-gray-300 mb-2">Frame Markers</h3>
      <div className="space-y-2">
        {MARKER_DEFS.map(({ key, label, color, hotkey }) => {
          const frame = markers[key as keyof FrameMarkers];
          return (
            <div key={key} className="flex items-center justify-between text-sm">
              <span className={`${color} font-medium w-24`}>{label}</span>
              <span className="text-gray-400 w-16 text-center">
                {frame != null ? (
                  <button
                    className="hover:text-white"
                    onClick={() => onGoToFrame(frame)}
                  >
                    {frame + 1}
                  </button>
                ) : '---'}
              </span>
              <div className="flex gap-1">
                <button
                  className="px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 rounded"
                  onClick={() => onSetMarker(key, currentFrame)}
                  title={`Set to current frame (${hotkey})`}
                >
                  Set ({hotkey})
                </button>
                {frame != null && (
                  <button
                    className="px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 rounded text-red-400"
                    onClick={() => onClearMarker(key)}
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
