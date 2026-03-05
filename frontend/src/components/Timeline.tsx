import { useCallback } from 'react';
import type { Annotation } from '../lib/types';

interface Props {
  totalFrames: number;
  currentFrame: number;  // 0-indexed
  annotation: Annotation | null;
  onFrameClick: (frame: number) => void;  // 0-indexed
}

const MARKER_COLORS: Record<string, string> = {
  ball_down: '#3b82f6',
  breakpoint: '#eab308',
  pin_hit: '#ef4444',
  ball_off_deck: '#a855f7',
};

export function Timeline({ totalFrames, currentFrame, annotation, onFrameClick }: Props) {
  const getFrameColor = useCallback((frame: number): string => {
    if (!annotation) return 'bg-gray-700';
    const key = String(frame);
    if (key in annotation.ball_annotations) {
      return annotation.ball_annotations[key] !== null ? 'bg-green-500' : 'bg-gray-500';
    }
    return 'bg-gray-700';
  }, [annotation]);

  return (
    <div className="w-full px-2 py-3">
      {/* Marker flags */}
      <div className="relative h-6 mb-1">
        {annotation?.frame_markers && Object.entries(annotation.frame_markers).map(([name, frame]) => (
          frame != null && (
            <div
              key={name}
              className="absolute top-0 text-xs font-bold cursor-pointer"
              style={{
                left: `${(frame / Math.max(totalFrames - 1, 1)) * 100}%`,
                color: MARKER_COLORS[name] || '#fff',
              }}
              onClick={() => onFrameClick(frame)}
              title={`${name}: frame ${frame + 1}`}
            >
              |
            </div>
          )
        ))}
      </div>
      {/* Frame bar (0-indexed internally) */}
      <div className="flex gap-px h-4">
        {Array.from({ length: totalFrames }, (_, i) => i).map(frame => (
          <div
            key={frame}
            className={`flex-1 min-w-[2px] cursor-pointer ${getFrameColor(frame)} ${
              frame === currentFrame ? 'ring-2 ring-white' : ''
            }`}
            onClick={() => onFrameClick(frame)}
            title={`Frame ${frame + 1}`}
          />
        ))}
      </div>
      <div className="text-xs text-gray-400 mt-1 text-center">
        Frame {currentFrame + 1} / {totalFrames}
      </div>
    </div>
  );
}
