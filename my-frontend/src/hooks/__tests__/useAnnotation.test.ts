import { renderHook, act, waitFor } from '@testing-library/react';
import axios from 'axios';
import { useAnnotation } from '../useAnnotation';

jest.mock('axios');
jest.mock('../../config', () => ({ API_URL: 'https://test-api' }));

const mockedAxios = axios as jest.Mocked<typeof axios>;

const MOCK_ANNOTATION = {
  version: '1.0',
  video_metadata: { fps: 30, total_frames: 60, width: 1920, height: 1080 },
  ball_annotations: { '5': { x: 100, y: 200, radius: 25 } },
  frame_markers: {},
};

describe('useAnnotation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    mockedAxios.get.mockResolvedValue({ data: MOCK_ANNOTATION });
    mockedAxios.put.mockResolvedValue({ data: { status: 'saved' } });
    mockedAxios.delete.mockResolvedValue({ data: { status: 'deleted' } });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('loads annotation on mount', async () => {
    const { result } = renderHook(() => useAnnotation('result-1'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockedAxios.get).toHaveBeenCalledWith(
      'https://test-api/bowling/result/result-1/annotation'
    );
    expect(result.current.annotation?.version).toBe('1.0');
  });

  test('setBall stores correct 0-indexed key', async () => {
    const { result } = renderHook(() => useAnnotation('result-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.setBall(0, { x: 50, y: 60, radius: 20 });
    });

    // Optimistic update: key "0" in local state
    expect(result.current.annotation?.ball_annotations['0']).toEqual({
      x: 50, y: 60, radius: 20,
    });

    // Flush debounce timer
    act(() => { jest.advanceTimersByTime(500); });

    await waitFor(() => {
      expect(mockedAxios.put).toHaveBeenCalledWith(
        'https://test-api/bowling/result/result-1/annotation/ball/0',
        { x: 50, y: 60, radius: 20 }
      );
    });
  });

  test('clearBall calls DELETE (not PUT null)', async () => {
    const { result } = renderHook(() => useAnnotation('result-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.clearBall(5);
    });

    // Key should be removed from local state
    expect(result.current.annotation?.ball_annotations).not.toHaveProperty('5');

    act(() => { jest.advanceTimersByTime(500); });

    await waitFor(() => {
      expect(mockedAxios.delete).toHaveBeenCalledWith(
        'https://test-api/bowling/result/result-1/annotation/ball/5'
      );
      // Must NOT have called PUT
      expect(mockedAxios.put).not.toHaveBeenCalledWith(
        expect.stringContaining('/annotation/ball/5'),
        null
      );
    });
  });

  test('setBall with null calls PUT (not DELETE)', async () => {
    const { result } = renderHook(() => useAnnotation('result-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.setBall(3, null);  // "no ball visible"
    });

    act(() => { jest.advanceTimersByTime(500); });

    await waitFor(() => {
      expect(mockedAxios.put).toHaveBeenCalledWith(
        'https://test-api/bowling/result/result-1/annotation/ball/3',
        null
      );
      // Must NOT have called DELETE
      expect(mockedAxios.delete).not.toHaveBeenCalledWith(
        expect.stringContaining('/annotation/ball/3')
      );
    });
  });

  test('saveLaneEdges calls PUT with correct URL and body', async () => {
    const { result } = renderHook(() => useAnnotation('result-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    const edges = {
      top_left: [10, 20] as [number, number],
      top_right: [300, 20] as [number, number],
      bottom_left: [50, 400] as [number, number],
      bottom_right: [260, 400] as [number, number],
    };

    act(() => {
      result.current.saveLaneEdges(7, edges);
    });

    act(() => { jest.advanceTimersByTime(500); });

    await waitFor(() => {
      expect(mockedAxios.put).toHaveBeenCalledWith(
        'https://test-api/bowling/result/result-1/annotation/lane-edges/7',
        edges
      );
    });
  });

  test('saveLaneEdges updates local annotation.frame_lane_edges optimistically', async () => {
    const { result } = renderHook(() => useAnnotation('result-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    const edges = {
      top_left: [10, 20] as [number, number],
      top_right: [300, 20] as [number, number],
      bottom_left: [50, 400] as [number, number],
      bottom_right: [260, 400] as [number, number],
    };

    act(() => {
      result.current.saveLaneEdges(7, edges);
    });

    expect(result.current.annotation?.frame_lane_edges?.['7']).toEqual(edges);
  });

  test('deleteLaneEdges calls DELETE with correct URL', async () => {
    const { result } = renderHook(() => useAnnotation('result-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    // First save lane edges so there's something to delete
    const edges = {
      top_left: [10, 20] as [number, number],
      top_right: [300, 20] as [number, number],
      bottom_left: [50, 400] as [number, number],
      bottom_right: [260, 400] as [number, number],
    };
    act(() => {
      result.current.saveLaneEdges(3, edges);
    });
    act(() => { jest.advanceTimersByTime(500); });

    act(() => {
      result.current.deleteLaneEdges(3);
    });

    act(() => { jest.advanceTimersByTime(500); });

    await waitFor(() => {
      expect(mockedAxios.delete).toHaveBeenCalledWith(
        'https://test-api/bowling/result/result-1/annotation/lane-edges/3'
      );
    });
  });

  test('deleteLaneEdges removes key from local annotation.frame_lane_edges', async () => {
    const { result } = renderHook(() => useAnnotation('result-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    // First save lane edges
    const edges = {
      top_left: [10, 20] as [number, number],
      top_right: [300, 20] as [number, number],
      bottom_left: [50, 400] as [number, number],
      bottom_right: [260, 400] as [number, number],
    };
    act(() => {
      result.current.saveLaneEdges(3, edges);
    });
    expect(result.current.annotation?.frame_lane_edges?.['3']).toEqual(edges);

    act(() => {
      result.current.deleteLaneEdges(3);
    });

    expect(result.current.annotation?.frame_lane_edges).not.toHaveProperty('3');
  });

  test('setLaneEdges calls PUT with lane_edges in body', async () => {
    const { result } = renderHook(() => useAnnotation('result-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    const edges = { top_left: [100, 100], top_right: [200, 100], bottom_left: [100, 500], bottom_right: [200, 500] };
    act(() => { result.current.setLaneEdges(edges as any); });

    // Optimistic update
    expect(result.current.annotation?.lane_edges).toEqual(edges);

    act(() => { jest.advanceTimersByTime(500); });
    await waitFor(() => {
      expect(mockedAxios.put).toHaveBeenCalledWith(
        'https://test-api/bowling/result/result-1/annotation',
        expect.objectContaining({ lane_edges: edges })
      );
    });
  });

  test('debounce: rapid calls result in single network request', async () => {
    const { result } = renderHook(() => useAnnotation('result-1'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    // Rapid-fire 5 setBall calls within debounce window
    act(() => {
      result.current.setBall(0, { x: 1, y: 1, radius: 10 });
    });
    act(() => { jest.advanceTimersByTime(100); });
    act(() => {
      result.current.setBall(0, { x: 2, y: 2, radius: 10 });
    });
    act(() => { jest.advanceTimersByTime(100); });
    act(() => {
      result.current.setBall(0, { x: 3, y: 3, radius: 10 });
    });

    // Flush final debounce
    act(() => { jest.advanceTimersByTime(500); });

    await waitFor(() => {
      // Only ONE network call should have been made (the last one)
      const putCalls = mockedAxios.put.mock.calls.filter(
        c => (c[0] as string).includes('/annotation/ball/')
      );
      expect(putCalls.length).toBe(1);
      expect(putCalls[0][1]).toEqual({ x: 3, y: 3, radius: 10 });
    });
  });
});
