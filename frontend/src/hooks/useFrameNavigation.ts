import { useState, useCallback, useRef, useEffect } from 'react';
import { API_URL } from '../config';

const PRELOAD_COUNT = 5;
const PLAYBACK_PRELOAD = 30;
const MAX_CACHE_SIZE = 200;

export function useFrameNavigation(resultId: string, totalFrames: number, fps: number = 30) {
  const [currentFrame, setCurrentFrame] = useState(0);  // 0-indexed
  const [currentImage, setCurrentImage] = useState<HTMLImageElement | null>(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [frameError, setFrameError] = useState<string>('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const cacheRef = useRef<Map<number, HTMLImageElement>>(new Map());
  const playingRef = useRef(false);
  const lastFrameTimeRef = useRef(0);
  const rafRef = useRef<number>(0);

  const getFrameUrl = useCallback((frame: number) => {
    // frame is 0-indexed; backend handles +1 for ffmpeg filenames
    return `${API_URL}/bowling/result/${resultId}/frames/${frame}`;
  }, [resultId]);

  const loadFrame = useCallback((frame: number): Promise<HTMLImageElement> => {
    const cached = cacheRef.current.get(frame);
    if (cached) return Promise.resolve(cached);

    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        if (cacheRef.current.size >= MAX_CACHE_SIZE) {
          const firstKey = cacheRef.current.keys().next().value;
          if (firstKey !== undefined) cacheRef.current.delete(firstKey);
        }
        cacheRef.current.set(frame, img);
        resolve(img);
      };
      img.onerror = reject;
      img.src = getFrameUrl(frame);
    });
  }, [getFrameUrl]);

  // Load current frame and preload neighbors
  useEffect(() => {
    if (totalFrames === 0) return;
    setImageLoading(true);
    setFrameError('');
    loadFrame(currentFrame)
      .then(img => {
        setCurrentImage(img);
        setImageLoading(false);
      })
      .catch(() => {
        setImageLoading(false);
        setFrameError(`Failed to load frame ${currentFrame + 1}. Check GCS CORS configuration.`);
      });

    const preloadCount = playingRef.current ? PLAYBACK_PRELOAD : PRELOAD_COUNT;
    for (let i = 1; i <= preloadCount; i++) {
      const next = currentFrame + i;
      if (next < totalFrames) loadFrame(next).catch(() => {});
    }
  }, [currentFrame, totalFrames, loadFrame]);

  // Playback loop
  useEffect(() => {
    if (!isPlaying || totalFrames === 0) return;
    playingRef.current = true;
    lastFrameTimeRef.current = performance.now();

    const frameDuration = 1000 / (fps * playbackSpeed);

    const tick = (now: number) => {
      if (!playingRef.current) return;
      const elapsed = now - lastFrameTimeRef.current;
      if (elapsed >= frameDuration) {
        lastFrameTimeRef.current = now - (elapsed % frameDuration);
        setCurrentFrame(prev => {
          const nextFrame = prev + 1;
          if (nextFrame >= totalFrames) {
            // Stop at end
            playingRef.current = false;
            setIsPlaying(false);
            return prev;
          }
          return nextFrame;
        });
      }
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      playingRef.current = false;
      cancelAnimationFrame(rafRef.current);
    };
  }, [isPlaying, totalFrames, fps, playbackSpeed]);

  const goTo = useCallback((frame: number) => {
    setCurrentFrame(Math.max(0, Math.min(frame, totalFrames - 1)));
  }, [totalFrames]);

  const next = useCallback(() => goTo(currentFrame + 1), [currentFrame, goTo]);
  const prev = useCallback(() => goTo(currentFrame - 1), [currentFrame, goTo]);
  const jumpForward = useCallback(() => goTo(currentFrame + 10), [currentFrame, goTo]);
  const jumpBack = useCallback(() => goTo(currentFrame - 10), [currentFrame, goTo]);

  const pause = useCallback(() => {
    playingRef.current = false;
    setIsPlaying(false);
  }, []);

  const play = useCallback(() => {
    if (currentFrame >= totalFrames - 1) {
      setCurrentFrame(0); // restart from beginning if at end
    }
    setIsPlaying(true);
  }, [currentFrame, totalFrames]);

  const togglePlay = useCallback(() => {
    if (isPlaying) pause();
    else play();
  }, [isPlaying, pause, play]);

  const cycleSpeed = useCallback(() => {
    setPlaybackSpeed(s => {
      if (s >= 1) return 0.5;
      if (s >= 0.5) return 0.25;
      return 1;
    });
  }, []);

  return {
    currentFrame, currentImage, imageLoading, frameError,
    goTo, next, prev, jumpForward, jumpBack,
    isPlaying, playbackSpeed, play, pause, togglePlay, cycleSpeed,
  };
}
