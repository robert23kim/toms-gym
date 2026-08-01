// Pin the timezone so date-formatting assertions are deterministic. A western
// zone is deliberate: bare ISO dates ("2026-07-31") parse as UTC midnight and
// render a day early only west of Greenwich, so a UTC runner would pass that
// bug (see TrophyCase.test.tsx).
process.env.TZ = 'America/Los_Angeles';

module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    // Handle module aliases
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testMatch: ['**/?(*.)+(spec|test).(js|ts|tsx)'],
  // e2e/ holds Playwright specs — they cannot run under jest.
  testPathIgnorePatterns: ['/node_modules/', '<rootDir>/e2e/'],
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', { tsconfig: 'tsconfig.app.json' }],
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  transformIgnorePatterns: ['/node_modules/'],
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/main.tsx',
    '!src/vite-env.d.ts',
  ],
}; 