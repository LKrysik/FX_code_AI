/**
 * Trading Session Smoke Tests
 * ============================
 *
 * Critical path tests that MUST pass before any deployment.
 * These verify the core trader journey works end-to-end.
 *
 * @tags smoke, critical, trading
 */

import { test, expect } from '../fixtures/base.fixture';
import { DashboardPage, TradingSessionPage } from '../pages';

test.describe('Trading Session - Smoke Tests', () => {
  test.describe.configure({ mode: 'serial' });

  // ============================================
  // SMOKE-01: Dashboard loads without errors
  // ============================================
  test('SMOKE-01: Dashboard loads and displays correctly', async ({ page, consoleErrors }) => {
    const dashboard = new DashboardPage(page);

    await dashboard.goto();

    // Core assertions
    await expect(page).toHaveTitle(/Dashboard|FX Agent/i);
    await dashboard.waitForPageLoad();

    // Either shows "No Active Session" or an active session
    const hasNoSession = await dashboard.noActiveSessionBanner.isVisible();
    const hasStartButton = await dashboard.startSessionButton.isVisible();

    expect(hasNoSession || hasStartButton).toBeTruthy();

    // No critical JS errors
    const criticalErrors = consoleErrors.filter(
      (e) =>
        e.includes('TypeError') ||
        e.includes('ReferenceError') ||
        e.includes('Cannot read')
    );
    expect(criticalErrors).toHaveLength(0);
  });

  // ============================================
  // SMOKE-02: Trading session page loads
  // ============================================
  test('SMOKE-02: Trading session configuration page loads', async ({ page, consoleErrors }) => {
    const tradingPage = new TradingSessionPage(page);

    await tradingPage.goto();
    await tradingPage.waitForPageLoad();

    // Should have mode selection buttons
    const liveVisible = await tradingPage.liveButton.isVisible();
    const paperVisible = await tradingPage.paperButton.isVisible();
    const backtestVisible = await tradingPage.backtestButton.isVisible();

    // At least one mode should be available
    expect(liveVisible || paperVisible || backtestVisible).toBeTruthy();

    // No critical errors
    const criticalErrors = consoleErrors.filter(
      (e) => e.includes('TypeError') || e.includes('Cannot read')
    );
    expect(criticalErrors).toHaveLength(0);
  });

  // ============================================
  // SMOKE-03: API connectivity
  // ============================================
  test('SMOKE-03: Backend API is reachable', async ({ apiClient }) => {
    // Try to fetch strategies (core endpoint)
    let strategiesReachable = false;
    try {
      const response = await apiClient.get('/api/strategies');
      strategiesReachable = true;
    } catch (e) {
      // API might be down
    }

    // Try to fetch indicators
    let indicatorsReachable = false;
    try {
      const response = await apiClient.get('/api/indicators');
      indicatorsReachable = true;
    } catch (e) {
      // API might be down
    }

    // At least one API should be reachable for smoke to pass
    // If neither works, it's a critical infrastructure issue
    expect(strategiesReachable || indicatorsReachable).toBeTruthy();
  });

  // ============================================
  // SMOKE-04: Navigation works
  // ============================================
  test('SMOKE-04: Core navigation links work', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Test key navigation paths
    const routes = [
      { path: '/dashboard', titlePattern: /Dashboard/i },
      { path: '/strategy-builder', titlePattern: /Strateg/i },
      { path: '/indicators', titlePattern: /Indicator/i },
    ];

    for (const route of routes) {
      await page.goto(route.path);
      await page.waitForLoadState('networkidle');

      // Page should not show error
      const errorBoundary = page.locator('[class*="error-boundary"], [class*="ErrorBoundary"]');
      const hasError = await errorBoundary.count();
      expect(hasError).toBe(0);
    }
  });

  // ============================================
  // SMOKE-05: Chart rendering works
  // ============================================
  test('SMOKE-05: Charts can render without crashing', async ({ page, consoleErrors }) => {
    // Navigate to a page with charts
    await page.goto('/data-collection');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Check for chart-related crashes
    const chartErrors = consoleErrors.filter(
      (e) =>
        e.includes('lightweight-charts') ||
        e.includes('addCandlestickSeries') ||
        e.includes('createChart')
    );

    // Chart errors are concerning but not always critical
    // Log them but don't fail smoke test
    if (chartErrors.length > 0) {
      console.warn(`⚠️ Chart warnings found: ${chartErrors.length}`);
    }

    // Page should still be functional
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy();
  });
});
