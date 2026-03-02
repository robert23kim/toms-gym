import { useState, useCallback, useRef, useEffect } from 'react';
import { API_URL } from '../config';

const PRELOAD_COUNT = 5;
const MAX_CACHE_SIZE = 50;

export function useFrameNavigation(resultId: string, totalFrames: number) {
  const [currentFrame, setCurrentFrame] = useState(0);  // 0-indexed
  const [currentImage, setCurrentImage] = useState<HTMLImageElement | null>(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [frameError, setFrameError] = useState<string>('');
  const cacheRef = useRef<Map<number, HTMLImageElement>>(new Map());

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

    for (let i = 1; i <= PRELOAD_COUNT; i++) {
      const next = currentFrame + i;
      if (next < totalFrames) loadFrame(next).catch(() => {});
    }
  }, [currentFrame, totalFrames, loadFrame]);

  const goTo = useCallback((frame: number) => {
    setCurrentFrame(Math.max(0, Math.min(frame, totalFrames - 1)));
  }, [totalFrames]);

  const next = useCallback(() => goTo(currentFrame + 1), [currentFrame, goTo]);
  const prev = useCallback(() => goTo(currentFrame - 1), [currentFrame, goTo]);
  const jumpForward = useCallback(() => goTo(currentFrame + 10), [currentFrame, goTo]);
  const jumpBack = useCallback(() => goTo(currentFrame - 10), [currentFrame, goTo]);

  return { currentFrame, currentImage, imageLoading, frameError, goTo, next, prev, jumpForward, jumpBack };
}
