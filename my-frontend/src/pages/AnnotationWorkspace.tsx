import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config';
import { FrameCanvas } from '../components/FrameCanvas';
import { Timeline } from '../components/Timeline';
import { MarkerPanel } from '../components/MarkerPanel';
import { useAnnotation } from '../hooks/useAnnotation';
import { useFrameNavigation } from '../hooks/useFrameNavigation';
import type { FrameData, FrameMarkers } from '../lib/types';

export default function AnnotationWorkspace() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const [frameData, setFrameData] = useState<FrameData | null>(null);
  const [resultId, setResultId] = useState<string>('');
  const [radius, setRadius] = useState(25);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // Fetch result ID from attempt ID
  useEffect(() => {
    if (!attemptId) return;
    axios.get(`${API_URL}/bowling/result/${attemptId}`)
      .then(res => setResultId(res.data.id))
      .catch(err => setError(`Failed to load result: ${err.message}`));
  }, [attemptId]);

  // Fetch frame data once we have result ID
  useEffect(() => {
    if (!resultId) return;
    setLoading(true);
    axios.get(`${API_URL}/bowling/result/${resultId}/frames`)
      .then(res => {
        setFrameData(res.data);
        setLoading(false);
      })
      .catch(err => {
        setError(`Failed to extract frames: ${err.message}`);
        setLoading(false);
      });
  }, [resultId]);

  const { annotation, saving, setBall, clearBall, setMarkers } = useAnnotation(resultId);
  const { currentFrame, currentImage, imageLoading, frameError, goTo, next, prev, jumpForward, jumpBack } =
    useFrameNavigation(resultId, frameData?.total_frames || 0);

  const handleSetMarker = useCallback((name: string, frame: number) => {
    setMarkers({ ...annotation?.frame_markers, [name]: frame } as FrameMarkers);
  }, [annotation, setMarkers]);

  const handleClearMarker = useCallback((name: string) => {
    const { [name]: _, ...rest } = annotation?.frame_markers || {};
    setMarkers(rest as FrameMarkers);
  }, [annotation, setMarkers]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;

      switch (e.key) {
        case 'd': case 'ArrowRight': next(); break;
        case 'a': case 'ArrowLeft': prev(); break;
        case 'w': case 'ArrowUp': e.preventDefault(); jumpForward(); break;
        case 's': case 'ArrowDown': e.preventDefault(); jumpBack(); break;
        case 'n':
          setBall(currentFrame, null); // Mark "no ball visible"
          break;
        case 'Delete': case 'Backspace':
          clearBall(currentFrame); // Remove annotation entirely
          break;
        case 'c': {
          // Copy ball from previous frame
          if (currentFrame > 0) {
            const prevBall = annotation?.ball_annotations[String(currentFrame - 1)];
            if (prevBall) setBall(currentFrame, prevBall);
          }
          break;
        }
        case 'p': handleSetMarker('pin_hit', currentFrame); break;
        case 'b': handleSetMarker('breakpoint', currentFrame); break;
        case 'g': handleSetMarker('ball_down', currentFrame); break;
        case 'o': handleSetMarker('ball_off_deck', currentFrame); break;
      }
    };

    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [currentFrame, annotation, next, prev, jumpForward, jumpBack, setBall, clearBall, handleSetMarker]);

  const handleBallClick = useCallback((x: number, y: number) => {
    setBall(currentFrame, { x, y, radius });
  }, [currentFrame, radius, setBall]);

  const handleRadiusChange = useCallback((delta: number) => {
    setRadius(r => Math.max(5, Math.min(100, r + delta)));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-2 border-white border-t-transparent rounded-full mx-auto mb-4" />
          <p>Extracting frames...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  const ballForFrame = annotation?.ball_annotations[String(currentFrame)];
  const annotatedCount = annotation
    ? Object.values(annotation.ball_annotations).filter(v => v !== null && v !== undefined).length
    : 0;

  return (
    <div className="h-screen bg-gray-900 text-white flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <a href={`/bowling/result/${attemptId}`} className="text-gray-400 hover:text-white text-sm">
            &larr; Back to result
          </a>
          <h1 className="text-lg font-bold">Annotation</h1>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span>Radius: {radius}</span>
          <span>{annotatedCount} / {frameData?.total_frames} annotated</span>
          {saving && <span className="text-yellow-400">Saving...</span>}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex">
        {/* Canvas area */}
        <div className="flex-1 flex items-center justify-center p-1 min-h-0">
          {frameError ? (
            <div className="text-center">
              <p className="text-red-400 mb-2">{frameError}</p>
              <p className="text-gray-500 text-sm">If this persists, GCS CORS may need configuration.</p>
            </div>
          ) : imageLoading ? (
            <div className="animate-spin h-8 w-8 border-2 border-white border-t-transparent rounded-full" />
          ) : (
            <FrameCanvas
              image={currentImage}
              ball={ballForFrame}
              laneEdges={annotation?.lane_edges}
              radius={radius}
              onBallClick={handleBallClick}
              onRadiusChange={handleRadiusChange}
            />
          )}
        </div>

        {/* Side panel */}
        <div className="w-64 p-3 bg-gray-800 border-l border-gray-700 space-y-3">
          <MarkerPanel
            markers={annotation?.frame_markers || {}}
            currentFrame={currentFrame}
            onSetMarker={handleSetMarker}
            onClearMarker={handleClearMarker}
            onGoToFrame={goTo}
          />
        </div>
      </div>

      {/* Timeline */}
      <Timeline
        totalFrames={frameData?.total_frames || 0}
        currentFrame={currentFrame}
        annotation={annotation}
        onFrameClick={goTo}
      />

      {/* Keyboard help */}
      <div className="px-4 py-2 text-xs text-gray-500 bg-gray-800 border-t border-gray-700">
        D/A: next/prev | W/S: +/-10 | Click: mark ball | Scroll: radius | N: no ball | Del: clear | P/B/G/O: markers | C: copy prev
      </div>
    </div>
  );
}
