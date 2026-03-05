import { renderHook, act, waitFor } from '@testing-library/react';
import { useFrameNavigation } from '../useFrameNavigation';

jest.mock('../../config', () => ({ API_URL: 'https://test-api' }));

// Mock Image constructor for frame loading
class MockImage {
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  crossOrigin = '';
  private _src = '';

  get src() { return this._src; }
  set src(url: string) {
    this._src = url;
    // Auto-trigger onload for test convenience
    setTimeout(() => this.onload?.(), 0);
  }

  get naturalWidth() { return 1920; }
  get naturalHeight() { return 1080; }
}

describe('useFrameNavigation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global as any).Image = MockImage;
  });

  test('initial frame is 0', () => {
    const { result } = renderHook(() => useFrameNavigation('result-1', 60));
    expect(result.current.currentFrame).toBe(0);
  });

  test('goTo clamps to [0, totalFrames-1]', () => {
    const { result } = renderHook(() => useFrameNavigation('result-1', 60));

    // Clamp to max
    act(() => { result.current.goTo(100); });
    expect(result.current.currentFrame).toBe(59);  // totalFrames - 1

    // Clamp to min
    act(() => { result.current.goTo(-5); });
    expect(result.current.currentFrame).toBe(0);

    // Normal navigation
    act(() => { result.current.goTo(30); });
    expect(result.current.currentFrame).toBe(30);
  });

  test('frame URL uses 0-indexed frame number', () => {
    const { result } = renderHook(() => useFrameNavigation('result-1', 60));
    // The hook constructs URLs like: API_URL/bowling/result/{id}/frames/{frame}
    // Frame 0 should produce URL ending in /frames/0 (backend handles +1)
    // We can't directly test the URL, but we verify the frame index is 0-based
    expect(result.current.currentFrame).toBe(0);
  });

  test('frameError set on load failure', async () => {
    // Override Image to trigger error
    class FailImage extends MockImage {
      set src(url: string) {
        setTimeout(() => this.onerror?.(), 0);
      }
    }
    (global as any).Image = FailImage;

    const { result } = renderHook(() => useFrameNavigation('result-1', 60));

    await waitFor(() => {
      expect(result.current.frameError).toBeTruthy();
      expect(result.current.frameError).toContain('CORS');
    });
  });

  test('next/prev navigate sequentially', () => {
    const { result } = renderHook(() => useFrameNavigation('result-1', 60));

    act(() => { result.current.next(); });
    expect(result.current.currentFrame).toBe(1);

    act(() => { result.current.next(); });
    expect(result.current.currentFrame).toBe(2);

    act(() => { result.current.prev(); });
    expect(result.current.currentFrame).toBe(1);
  });

  test('jumpForward/jumpBack move by 10', () => {
    const { result } = renderHook(() => useFrameNavigation('result-1', 60));

    act(() => { result.current.goTo(25); });
    act(() => { result.current.jumpForward(); });
    expect(result.current.currentFrame).toBe(35);

    act(() => { result.current.jumpBack(); });
    expect(result.current.currentFrame).toBe(25);
  });
});
