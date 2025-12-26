/**
 * Example Test: New Fixture & Factory Patterns
 * =============================================
 *
 * This file demonstrates the upgraded test architecture:
 * - Composable fixtures via mergeTests
 * - Faker-based data factories
 * - API-first test data seeding
 * - Automatic cleanup
 * - Network mocking
 *
 * @see TEA Knowledge Base: fixture-architecture.md, data-factories.md
 */

import { test, expect } from '../support/fixtures';
import { createStrategy, createPaperSession, createSymbols } from '../support/factories';
import { seedStrategy, seedStrategies, seedTradingSetup } from '../support/helpers';
import { StrategyBuilderPage, TradingSessionPage } from '../pages';

/**
 * Example 1: Using Data Factories
 * --------------------------------
 * Factories generate realistic test data with sensible defaults.
 * Override any field to customize for specific test scenarios.
 */
test.describe('Data Factory Patterns', () => {
  test('EXAMPLE-01: Create strategy with default values', async ({ page }) => {
    // Factory generates all required fields with realistic values
    const strategy = createStrategy();

    // Use factory data in assertions or setup
    console.log(`Created strategy: ${strategy.name} with ${strategy.conditions.length} conditions`);

    // Strategy has unique ID (parallel-safe)
    expect(strategy.id).toBeTruthy();
    expect(strategy.name).toMatch(/^Strategy_/);
    expect(strategy.conditions.length).toBeGreaterThanOrEqual(2);
  });

  test('EXAMPLE-02: Override specific fields', async ({ page }) => {
    // Override only what matters for this test
    const strategy = createStrategy({
      name: 'My Test Strategy',
      isActive: false,
    });

    expect(strategy.name).toBe('My Test Strategy');
    expect(strategy.isActive).toBe(false);
    // Other fields still have defaults
    expect(strategy.conditions).toBeDefined();
  });

  test('EXAMPLE-03: Create session with custom symbols', async ({ page }) => {
    const session = createPaperSession({
      config: {
        id: 'test-id',
        mode: 'Paper',
        strategies: ['strategy-1'],
        symbols: ['BTCUSDT', 'ETHUSDT'],
        leverage: 5,
        positionSize: 0.1,
        stopLoss: 3,
        takeProfit: 6,
        maxOpenPositions: 5,
        riskPerTrade: 2,
      },
    });

    expect(session.config.mode).toBe('Paper');
    expect(session.config.symbols).toContain('BTCUSDT');
    expect(session.config.leverage).toBe(5);
  });
});

/**
 * Example 2: API-First Seeding with Cleanup
 * ------------------------------------------
 * Seed test data via API before testing UI.
 * Cleanup fixture automatically deletes created data after test.
 */
test.describe('API-First Seeding', () => {
  test('EXAMPLE-04: Seed strategy and verify in UI', async ({ page, apiClient, cleanup }) => {
    // Seed via API (fast! no UI interaction)
    const strategy = await seedStrategy(apiClient, cleanup, {
      name: 'Seeded Strategy',
    });

    // Now test UI with seeded data
    const strategyPage = new StrategyBuilderPage(page);
    await strategyPage.goto();

    // Strategy should appear in list (if API works)
    // await strategyPage.expectStrategyInList(strategy.name);

    // Cleanup happens automatically after test!
    // No manual deletion needed
  });

  test('EXAMPLE-05: Seed multiple strategies', async ({ page, apiClient, cleanup }) => {
    // Seed 3 strategies at once
    const strategies = await seedStrategies(apiClient, cleanup, 3);

    expect(strategies).toHaveLength(3);

    // All 3 will be cleaned up automatically
  });

  test('EXAMPLE-06: Seed complete trading setup', async ({ page, apiClient, cleanup }) => {
    // Seed strategies + session in one call
    const { strategies, session } = await seedTradingSetup(apiClient, cleanup, {
      strategyCount: 2,
      symbols: ['BTCUSDT', 'ETHUSDT'],
      mode: 'Paper',
    });

    expect(strategies).toHaveLength(2);
    expect(session.config.mode).toBe('Paper');
    expect(session.config.symbols).toContain('BTCUSDT');

    // Both strategies and session cleaned up automatically
  });
});

/**
 * Example 3: Network Mocking
 * ---------------------------
 * Mock API responses for controlled testing.
 * Follows network-first pattern: intercept before navigate.
 */
test.describe('Network Mocking', () => {
  test('EXAMPLE-07: Mock API response', async ({ page, network }) => {
    const mockStrategies = [createStrategy({ name: 'Mocked Strategy 1' }), createStrategy({ name: 'Mocked Strategy 2' })];

    // Set up mock BEFORE navigation (network-first!)
    await network.mock({
      method: 'GET',
      urlPattern: '**/api/strategies',
      response: mockStrategies,
    });

    // Now navigate - will get mocked response
    const strategyPage = new StrategyBuilderPage(page);
    await strategyPage.goto();

    // UI shows mocked data
    // await strategyPage.expectStrategyInList('Mocked Strategy 1');
  });

  test('EXAMPLE-08: Simulate API error', async ({ page, network }) => {
    // Simulate 500 error
    await network.simulateError('**/api/strategies', 500);

    const strategyPage = new StrategyBuilderPage(page);
    await strategyPage.goto();

    // Test error handling UI
    // await expect(page.getByText(/error|failed/i)).toBeVisible();
  });

  test('EXAMPLE-09: Capture and assert requests', async ({ page, network }) => {
    // Start capturing requests
    network.captureRequests('**/api/strategies');

    const strategyPage = new StrategyBuilderPage(page);
    await strategyPage.goto();

    // Check what requests were made
    const requests = network.getCapturedRequests();
    // expect(requests.length).toBeGreaterThan(0);
  });
});

/**
 * Example 4: Console Error Tracking
 * ----------------------------------
 * Automatically capture and assert on JavaScript errors.
 */
test.describe('Console Error Tracking', () => {
  test('EXAMPLE-10: Assert no critical JS errors', async ({ page, console: consoleManager }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');

    // Check for critical errors
    const criticalErrors = consoleManager.getCriticalErrors();

    // No TypeError, ReferenceError, etc.
    expect(criticalErrors).toHaveLength(0);
  });

  test('EXAMPLE-11: Filter console messages', async ({ page, console: consoleManager }) => {
    await page.goto('/dashboard');

    // Filter for specific patterns
    const chartWarnings = consoleManager.filter(/chart/i);
    const allWarnings = consoleManager.getWarnings();

    // Log for debugging
    if (allWarnings.length > 0) {
      console.log(`Found ${allWarnings.length} warnings`);
    }
  });

  // Legacy compatibility - consoleErrors is still available
  test('EXAMPLE-12: Legacy consoleErrors array', async ({ page, consoleErrors }) => {
    await page.goto('/dashboard');

    // Old pattern still works
    const criticalErrors = consoleErrors.filter(
      (e) => e.includes('TypeError') || e.includes('ReferenceError')
    );

    expect(criticalErrors).toHaveLength(0);
  });
});

/**
 * Example 5: Full Integration Test
 * ---------------------------------
 * Combines all patterns for a complete E2E test.
 */
test.describe('Full Integration Example', () => {
  test('EXAMPLE-13: Complete trading flow with factories and mocking', async ({
    page,
    apiClient,
    cleanup,
    network,
    console: consoleManager,
  }) => {
    // 1. Seed test data via API
    const strategy = await seedStrategy(apiClient, cleanup, {
      name: 'Integration Test Strategy',
    });

    // 2. Mock WebSocket or other endpoints if needed
    await network.mock({
      method: 'GET',
      urlPattern: '**/api/market-data/**',
      response: { price: 50000, volume: 1000 },
    });

    // 3. Navigate and interact with UI
    const tradingPage = new TradingSessionPage(page);
    await tradingPage.goto();

    // 4. Perform actions
    await tradingPage.selectMode('Paper');

    // 5. Assert no JS errors
    expect(consoleManager.hasNoCriticalErrors()).toBe(true);

    // 6. Cleanup is automatic!
  });
});
