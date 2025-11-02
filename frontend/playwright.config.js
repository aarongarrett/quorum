/**
 * Playwright configuration for Quorum E2E tests
 *
 * These tests require:
 * 1. Backend running on http://localhost:8000
 * 2. Frontend running on http://localhost:3000
 *
 * To run tests:
 *   npm run test:e2e
 *
 * To run with UI:
 *   npm run test:e2e:ui
 */

// Load environment variables from .env file
require('dotenv').config({ path: '../.env' });

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',

  // Timeout for each test
  timeout: 60 * 1000,

  // Number of retries (0 for strict testing)
  retries: 0,

  // Number of workers (parallel tests)
  workers: 1,  // Run sequentially to avoid database conflicts

  // Reporter
  reporter: [
    ['list'],
    ['html', { outputFolder: '../test-reports/playwright', open: 'never' }]
  ],

  use: {
    // Base URL for tests
    baseURL: 'http://localhost:3000',

    // Browser options
    headless: true,

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Trace on failure (for debugging)
    trace: 'retain-on-failure',
  },

  // Test only in Chromium for speed (can add more browsers later)
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Don't start servers automatically (assume they're already running)
  // If you want Playwright to start servers, uncomment and configure:
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
