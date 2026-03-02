import { useState, useCallback, useRef, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../config';
import type { Annotation, BallAnnotation, FrameMarkers, LaneEdges } from '../lib/types';

export function useAnnotation(resultId: string) {
  const [annotation, setAnnotation] = useState<Annotation | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  // Load annotation on mount
  useEffect(() => {
    if (!resultId) return;
    axios.get(`${API_URL}/bowling/result/${resultId}/annotation`)
      .then(res => setAnnotation(res.data?.version ? res.data : null))
      .catch(err => console.error('Failed to load annotation:', err))
      .finally(() => setLoading(false));
  }, [resultId]);

  // Set ball position (or null for "no ball visible")
  const setBall = useCallback((frame: number, ball: BallAnnotation | null) => {
    setAnnotation(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        ball_annotations: { ...prev.ball_annotations, [String(frame)]: ball },
      };
    });

    clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      setSaving(true);
      axios.put(`${API_URL}/bowling/result/${resultId}/annotation/ball/${frame}`, ball)
        .catch(err => console.error('Failed to save ball annotation:', err))
        .finally(() => setSaving(false));
    }, 500);
  }, [resultId]);

  // Remove annotation entirely (back to "not yet annotated")
  const clearBall = useCallback((frame: number) => {
    setAnnotation(prev => {
      if (!prev) return prev;
      const { [String(frame)]: _, ...rest } = prev.ball_annotations;
      return { ...prev, ball_annotations: rest };
    });

    clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      setSaving(true);
      axios.delete(`${API_URL}/bowling/result/${resultId}/annotation/ball/${frame}`)
        .catch(err => console.error('Failed to clear ball annotation:', err))
        .finally(() => setSaving(false));
    }, 500);
  }, [resultId]);

  const setMarkers = useCallback((markers: FrameMarkers) => {
    setAnnotation(prev => {
      if (!prev) return prev;
      return { ...prev, frame_markers: markers };
    });

    clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      setSaving(true);
      axios.put(`${API_URL}/bowling/result/${resultId}/annotation/markers`, markers)
        .catch(err => console.error('Failed to save markers:', err))
        .finally(() => setSaving(false));
    }, 500);
  }, [resultId]);

  const saveLaneEdges = useCallback((frame: number, edges: LaneEdges) => {
    setAnnotation(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        frame_lane_edges: { ...prev.frame_lane_edges, [String(frame)]: edges },
      };
    });

    clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      setSaving(true);
      axios.put(`${API_URL}/bowling/result/${resultId}/annotation/lane-edges/${frame}`, edges)
        .catch(err => console.error('Failed to save lane edges:', err))
        .finally(() => setSaving(false));
    }, 500);
  }, [resultId]);

  const deleteLaneEdges = useCallback((frame: number) => {
    setAnnotation(prev => {
      if (!prev) return prev;
      const { [String(frame)]: _, ...rest } = prev.frame_lane_edges || {};
      return { ...prev, frame_lane_edges: rest };
    });

    clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      setSaving(true);
      axios.delete(`${API_URL}/bowling/result/${resultId}/annotation/lane-edges/${frame}`)
        .catch(err => console.error('Failed to delete lane edges:', err))
        .finally(() => setSaving(false));
    }, 500);
  }, [resultId]);

  return { annotation, loading, saving, setBall, clearBall, setMarkers, saveLaneEdges, deleteLaneEdges };
}
