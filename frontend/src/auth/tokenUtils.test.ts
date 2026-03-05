/// <reference types="jest" />

import {
  getAccessToken,
  getRefreshToken,
  getUserId,
  setTokens,
  clearTokens
} from './tokenUtils';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
})();

// Replace the global localStorage with our mock
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('TokenUtils', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    window.localStorage.clear();
  });

  test('should store and retrieve tokens from localStorage', () => {
    const testAccessToken = 'test-access-token';
    const testRefreshToken = 'test-refresh-token';
    const testUserId = 'test-user-id';

    // Initially, tokens should be null
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(getUserId()).toBeNull();

    // Set tokens and verify they are stored
    setTokens(testAccessToken, testRefreshToken, testUserId);
    
    // Verify tokens are retrieved correctly
    expect(getAccessToken()).toBe(testAccessToken);
    expect(getRefreshToken()).toBe(testRefreshToken);
    expect(getUserId()).toBe(testUserId);
  });

  test('should clear tokens from localStorage', () => {
    // Set some tokens first
    setTokens('test-access', 'test-refresh', 'test-user');
    
    // Verify tokens are set
    expect(getAccessToken()).toBe('test-access');
    
    // Clear tokens
    clearTokens();
    
    // Verify tokens are cleared
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(getUserId()).toBeNull();
  });

  test('should handle overwriting existing tokens', () => {
    // Set initial tokens
    setTokens('initial-access', 'initial-refresh', 'initial-user');
    
    // Verify they are set
    expect(getAccessToken()).toBe('initial-access');
    
    // Overwrite with new tokens
    setTokens('new-access', 'new-refresh', 'new-user');
    
    // Verify the new tokens are in place
    expect(getAccessToken()).toBe('new-access');
    expect(getRefreshToken()).toBe('new-refresh');
    expect(getUserId()).toBe('new-user');
  });
}); 