// Add any global setup needed for Jest tests here
// For example, configure testing libraries, set up mocks, etc.

// Mock fetch for all tests
global.fetch = jest.fn();

// Create a minimal localStorage mock
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
    },
    writable: true,
  });
} 