import { defineConfig, devices } from '@playwright/test';

/**
 * FX Agent AI - Playwright Configuration
 * ======================================
 *
 * Test Architecture Decisions:
 * - Page Object Model for maintainability
 * - Composable fixtures for reuse
 * - Network-first approach (intercept before navigate)
 * - Risk-based test selection via tags
 *
 * @see https://playwright.dev/docs/test-configuration
 */

export default defineConfig({
  // Test directory structure
  testDir: './tests/e2e',

  // Output directories
  outputDir: './test-results',

  // Global timeout for each test
  timeout: 60_000,

  // Expect timeout
  expect: {
    timeout: 10_000,
  },

  // Run tests in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Limit parallel workers on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter configuration
  reporter: [
    ['html', { outputFolder: './test-results/html-report' }],
    ['json', { outputFile: './test-results/results.json' }],
    ['list'],
  ],

  // Global setup/teardown
  globalSetup: './tests/e2e/global-setup.ts',
  globalTeardown: './tests/e2e/global-teardown.ts',

  // Shared settings for all projects
  use: {
    // Base URL for relative navigation
    baseURL: process.env.BASE_URL || 'http://localhost:3000',

    // API URL for backend calls
    extraHTTPHeaders: {
      'X-Test-Mode': 'true',
    },

    // Collect trace on failure
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure (for debugging)
    video: 'on-first-retry',

    // Viewport
    viewport: { width: 1920, height: 1080 },

    // Action timeout
    actionTimeout: 15_000,

    // Navigation timeout
    navigationTimeout: 30_000,
  },

  // Project configurations for different test scenarios
  projects: [
    // ============================================
    // SETUP PROJECT - runs before all tests
    // ============================================
    {
      name: 'setup',
      testMatch: /global-setup\.ts/,
    },

    // ============================================
    // SMOKE TESTS - Critical path, run first
    // ============================================
    {
      name: 'smoke',
      use: {
        ...devices['Desktop Chrome'],
      },
      testMatch: /.*\.smoke\.spec\.ts/,
      dependencies: ['setup'],
    },

    // ============================================
    // E2E TESTS - Full user flows
    // ============================================
    {
      name: 'e2e',
      use: {
        ...devices['Desktop Chrome'],
      },
      testMatch: /.*\.e2e\.spec\.ts/,
      dependencies: ['setup'],
    },

    // ============================================
    // COMPONENT TESTS - UI component behavior
    // ============================================
    {
      name: 'components',
      use: {
        ...devices['Desktop Chrome'],
      },
      testMatch: /.*\.component\.spec\.ts/,
      dependencies: ['setup'],
    },

    // ============================================
    // API TESTS - Backend API validation
    // ============================================
    {
      name: 'api',
      use: {
        ...devices['Desktop Chrome'],
      },
      testMatch: /.*\.api\.spec\.ts/,
      dependencies: ['setup'],
    },

    // ============================================
    // CROSS-BROWSER - Firefox (disabled - run 'npx playwright install firefox' to enable)
    // ============================================
    // {
    //   name: 'firefox',
    //   use: {
    //     ...devices['Desktop Firefox'],
    //   },
    //   testMatch: /.*\.e2e\.spec\.ts/,
    //   dependencies: ['setup'],
    // },

    // ============================================
    // MOBILE - Responsive testing
    // ============================================
    {
      name: 'mobile',
      use: {
        ...devices['iPhone 14'],
      },
      testMatch: /.*\.mobile\.spec\.ts/,
      dependencies: ['setup'],
    },
  ],

  // Web server configuration
  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
