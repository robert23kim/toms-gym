import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config';
import { FrameCanvas } from '../components/FrameCanvas';
import { Timeline } from '../components/Timeline';
import { MarkerPanel } from '../components/MarkerPanel';
import { StatusBar } from '../components/StatusBar';
import { useAnnotation } from '../hooks/useAnnotation';
import { useEdgeEditor } from '../hooks/useEdgeEditor';
import { useFrameNavigation } from '../hooks/useFrameNavigation';
import type { FrameData, FrameMarkers } from '../lib/types';

export default function AnnotationWorkspace() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const [frameData, setFrameData] = useState<FrameData | null>(null);
  const [resultId, setResultId] = useState<string>('');
  const [radius, setRadius] = useState(25);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [showHelp, setShowHelp] = useState(false);
  const [editMode, setEditMode] = useState<'NORMAL' | 'EDGE_EDIT'>('NORMAL');

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
    axios.get(`${API_URL}/bowling/result/${resultId}/frames?refresh=true`)
      .then(res => {
        setFrameData(res.data);
        setLoading(false);
      })
      .catch(err => {
        setError(`Failed to extract frames: ${err.message}`);
        setLoading(false);
      });
  }, [resultId]);

  const { annotation, saving, setBall, clearBall, setMarkers, saveLaneEdges, deleteLaneEdges } = useAnnotation(resultId);
  const {
    currentFrame, currentImage, imageLoading, frameError,
    goTo, next, prev, jumpForward, jumpBack,
    isPlaying, playbackSpeed, pause, togglePlay, cycleSpeed,
  } = useFrameNavigation(resultId, frameData?.total_frames || 0, frameData?.fps || 30);

  const edgeEditor = useEdgeEditor({
    annotation,
    currentFrame,
    onSave: saveLaneEdges,
    onDelete: deleteLaneEdges,
  });

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
        case ' ': e.preventDefault(); togglePlay(); break;
        case 'd': case 'ArrowRight': pause(); next(); break;
        case 'a': case 'ArrowLeft': pause(); prev(); break;
        case 'w': case 'ArrowUp': e.preventDefault(); pause(); jumpForward(); break;
        case 's': case 'ArrowDown': e.preventDefault(); pause(); jumpBack(); break;
        case 'n':
          pause();
          setBall(currentFrame, null); // Mark "no ball visible"
          break;
        case 'Delete': case 'Backspace':
          pause();
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
        case 'p': pause(); handleSetMarker('pin_hit', currentFrame); break;
        case 'b': pause(); handleSetMarker('breakpoint', currentFrame); break;
        case 'g': pause(); handleSetMarker('ball_down', currentFrame); break;
        case 'o': pause(); handleSetMarker('ball_off_deck', currentFrame); break;
        case 'e':
          setEditMode(m => {
            const next = m === 'NORMAL' ? 'EDGE_EDIT' : 'NORMAL';
            if (next === 'EDGE_EDIT' && isPlaying) pause();
            return next;
          });
          break;
        case 'r':
          if (editMode === 'EDGE_EDIT') edgeEditor.resetEdges();
          break;
        case 'f': cycleSpeed(); break;
        case 'h': setShowHelp(prev => !prev); break;
      }
    };

    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [currentFrame, annotation, next, prev, jumpForward, jumpBack, setBall, clearBall, handleSetMarker, togglePlay, pause, cycleSpeed, isPlaying, editMode, edgeEditor]);

  const handleBallClick = useCallback((x: number, y: number) => {
    pause();
    setBall(currentFrame, { x, y, radius });
  }, [currentFrame, radius, setBall, pause]);

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
  const noBallCount = annotation
    ? Object.values(annotation.ball_annotations).filter(v => v === null).length
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
          <button
            onClick={togglePlay}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm font-medium"
          >
            {isPlaying ? '⏸ Pause' : '▶ Play'}
          </button>
          <button
            onClick={cycleSpeed}
            className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs"
            title="Playback speed"
          >
            {playbackSpeed}x
          </button>
          <span>Radius: {radius}</span>
        </div>
      </div>

      <StatusBar
        currentFrame={currentFrame}
        totalFrames={frameData?.total_frames || 0}
        ball={ballForFrame}
        markers={annotation?.frame_markers || {}}
        annotatedCount={annotatedCount}
        noBallCount={noBallCount}
        editMode={editMode}
        saving={saving}
      />

      {/* Main content */}
      <div className="flex-1 flex min-h-0">
        {/* Canvas area */}
        <div className="flex-1 flex items-center justify-center p-1 min-h-0 h-full">
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
              editMode={editMode}
              edgeState={{
                edges: edgeEditor.effectiveEdges,
                selectedPoint: edgeEditor.selectedPoint,
                isDragging: edgeEditor.isDragging,
              }}
              onEdgeMouseDown={edgeEditor.handleMouseDown}
              onEdgeMouseMove={edgeEditor.handleMouseMove}
              onEdgeMouseUp={edgeEditor.handleMouseUp}
              onEdgeRightClick={edgeEditor.handleRightClick}
              onEdgeShiftClick={edgeEditor.handleShiftClick}
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
        Space: play/pause | F: speed | D/A: next/prev | W/S: +/-10 | Click: mark ball | Scroll: radius | N: no ball | Del: clear | P/B/G/O: markers | C: copy prev | H: help
      </div>

      {showHelp && (
        <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center" onClick={() => setShowHelp(false)} onKeyDown={() => setShowHelp(false)} data-testid="help-overlay">
          <div className="max-w-2xl text-white space-y-6 p-8">
            <h2 className="text-2xl font-bold text-center">Keyboard Shortcuts</h2>
            <div>
              <h3 className="text-lg font-semibold text-blue-400 mb-2">Navigation</h3>
              <div className="grid grid-cols-2 gap-1 text-sm">
                <span className="text-gray-400">D / ArrowRight</span><span>Next frame</span>
                <span className="text-gray-400">A / ArrowLeft</span><span>Previous frame</span>
                <span className="text-gray-400">W / ArrowUp</span><span>Jump +10 frames</span>
                <span className="text-gray-400">S / ArrowDown</span><span>Jump -10 frames</span>
                <span className="text-gray-400">Home</span><span>First frame</span>
                <span className="text-gray-400">End</span><span>Last frame</span>
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-green-400 mb-2">Ball Annotation</h3>
              <div className="grid grid-cols-2 gap-1 text-sm">
                <span className="text-gray-400">Click</span><span>Place ball at cursor</span>
                <span className="text-gray-400">Scroll</span><span>Adjust radius</span>
                <span className="text-gray-400">N</span><span>Mark "no ball visible"</span>
                <span className="text-gray-400">Delete / Backspace</span><span>Clear annotation</span>
                <span className="text-gray-400">C</span><span>Copy from previous frame</span>
                <span className="text-gray-400">+/- or [/]</span><span>Adjust radius by 3</span>
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-yellow-400 mb-2">Markers</h3>
              <div className="grid grid-cols-2 gap-1 text-sm">
                <span className="text-gray-400">P</span><span>Set pin hit</span>
                <span className="text-gray-400">B</span><span>Set breakpoint</span>
                <span className="text-gray-400">G</span><span>Set ball down</span>
                <span className="text-gray-400">O</span><span>Set ball off deck</span>
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-purple-400 mb-2">Playback</h3>
              <div className="grid grid-cols-2 gap-1 text-sm">
                <span className="text-gray-400">Space</span><span>Play / Pause</span>
                <span className="text-gray-400">F</span><span>Cycle speed (1x / 0.5x / 0.25x)</span>
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-orange-400 mb-2">Edge Editing</h3>
              <div className="grid grid-cols-2 gap-1 text-sm">
                <span className="text-gray-400">E</span><span>Toggle edge edit mode</span>
                <span className="text-gray-400">Z</span><span>Toggle cropped lane view</span>
                <span className="text-gray-400">H</span><span>Show/hide this help</span>
              </div>
            </div>
            <p className="text-center text-gray-500 text-sm">Press any key or click to dismiss</p>
          </div>
        </div>
      )}
    </div>
  );
}
