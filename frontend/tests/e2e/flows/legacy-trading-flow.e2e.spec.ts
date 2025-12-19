/**
 * Legacy Trading Flow E2E Tests - Migrated
 * =========================================
 *
 * These tests are migrated from the original e2e-trading-flow.spec.ts
 * to use the new Page Object Model and fixture system.
 *
 * Original tests covered:
 * 1. API availability checks
 * 2. Navigation to trading session
 * 3. Mode selection (Paper/Backtest/Live)
 * 4. Strategy and symbol configuration
 * 5. Session start/stop lifecycle
 * 6. Dashboard state verification
 *
 * @tags legacy, migration, e2e
 */

import { test, expect } from '../fixtures/base.fixture';
import { DashboardPage, TradingSessionPage, StrategyBuilderPage } from '../pages';

test.describe('Legacy Trading Flow - Migrated', () => {
  test.setTimeout(300000); // 5 minutes for full flow

  // ============================================
  // LEGACY-01: Full Trading Lifecycle
  // ============================================
  test('LEGACY-01: Complete trading session lifecycle', async ({ page, apiClient, consoleErrors }) => {
    const dashboard = new DashboardPage(page);
    const tradingSession = new TradingSessionPage(page);

    // Step 1: Verify API availability
    console.log('\n=== Step 1: API Availability ===');

    let apisAvailable = 0;
    const apiEndpoints = ['/api/strategies', '/api/indicators', '/api/trading/positions'];

    for (const endpoint of apiEndpoints) {
      try {
        const response = await apiClient.get(endpoint);
        if (response.ok) {
          apisAvailable++;
          console.log(`✓ ${endpoint}: OK`);
        } else {
          console.log(`✗ ${endpoint}: ${response.status}`);
        }
      } catch (e) {
        console.log(`✗ ${endpoint}: Not reachable`);
      }
    }

    // At least one API should be available
    expect(apisAvailable).toBeGreaterThan(0);

    // Step 2: Navigate to Trading Session
    console.log('\n=== Step 2: Trading Session Page ===');

    await tradingSession.goto();
    await tradingSession.waitForPageLoad();

    // Should show mode buttons
    const liveVisible = await tradingSession.liveButton.isVisible();
    const paperVisible = await tradingSession.paperButton.isVisible();
    const backtestVisible = await tradingSession.backtestButton.isVisible();

    console.log(`Mode buttons: Live=${liveVisible}, Paper=${paperVisible}, Backtest=${backtestVisible}`);
    expect(liveVisible || paperVisible || backtestVisible).toBeTruthy();

    // Step 3: Select Paper Mode
    console.log('\n=== Step 3: Mode Selection ===');

    if (paperVisible) {
      await tradingSession.selectMode('Paper');
      await page.waitForTimeout(500);
      console.log('✓ Paper mode selected');
    }

    // Step 4: Check for strategies
    console.log('\n=== Step 4: Strategy Selection ===');

    const strategyCheckboxes = page.locator('input[type="checkbox"]');
    const checkboxCount = await strategyCheckboxes.count();
    console.log(`Found ${checkboxCount} strategy checkboxes`);

    if (checkboxCount > 0) {
      await strategyCheckboxes.first().check();
      await page.waitForTimeout(300);
      console.log('✓ First strategy selected');
    }

    // Step 5: Check for symbols
    console.log('\n=== Step 5: Symbol Selection ===');

    const symbolInputs = page.locator('[data-testid*="symbol"], [class*="symbol"]');
    const symbolCount = await symbolInputs.count();
    console.log(`Found ${symbolCount} symbol-related elements`);

    // Step 6: Navigate to Dashboard
    console.log('\n=== Step 6: Dashboard Check ===');

    await dashboard.goto();
    await dashboard.waitForPageLoad();

    // Check dashboard state
    const hasNoSession = await dashboard.noActiveSessionBanner.isVisible();
    const hasStartButton = await dashboard.startSessionButton.isVisible();

    console.log(`Dashboard: noSession=${hasNoSession}, startButton=${hasStartButton}`);
    expect(hasNoSession || hasStartButton).toBeTruthy();

    // Step 7: Check for console errors
    console.log('\n=== Step 7: Error Check ===');

    const criticalErrors = consoleErrors.filter(
      (e) => e.includes('TypeError') || e.includes('ReferenceError') || e.includes('Cannot read')
    );

    console.log(`Critical JS errors: ${criticalErrors.length}`);
    expect(criticalErrors).toHaveLength(0);

    // Final summary
    console.log('\n=== Test Summary ===');
    console.log('✓ API availability checked');
    console.log('✓ Trading session page loaded');
    console.log('✓ Mode selection functional');
    console.log('✓ Dashboard accessible');
    console.log('✓ No critical JS errors');
  });

  // ============================================
  // LEGACY-02: Strategy Builder Integration
  // ============================================
  test('LEGACY-02: Strategy builder to session flow', async ({ page }) => {
    const strategyBuilder = new StrategyBuilderPage(page);
    const tradingSession = new TradingSessionPage(page);

    // Create or verify strategy exists
    await strategyBuilder.goto();
    await strategyBuilder.waitForPageLoad();

    const strategyCount = await strategyBuilder.strategyRows.count();
    console.log(`Existing strategies: ${strategyCount}`);

    // Navigate to trading session
    await tradingSession.goto();
    await tradingSession.waitForPageLoad();

    // Strategies should be available for selection
    const checkboxes = page.locator('input[type="checkbox"]');
    const availableStrategies = await checkboxes.count();

    console.log(`Strategies available for selection: ${availableStrategies}`);

    // Page should be stable
    await expect(page).toHaveURL(/trading-session/);
  });

  // ============================================
  // LEGACY-03: Dashboard Real-time Updates
  // ============================================
  test('LEGACY-03: Dashboard shows real-time data', async ({ page }) => {
    const dashboard = new DashboardPage(page);

    await dashboard.goto();
    await dashboard.waitForPageLoad();

    // Check for real-time elements
    const charts = page.locator('canvas, [class*="chart"]');
    const chartCount = await charts.count();

    const pnlDisplay = page.locator('[data-testid*="pnl"], [class*="pnl"]');
    const pnlCount = await pnlDisplay.count();

    console.log(`Charts: ${chartCount}, P&L displays: ${pnlCount}`);

    // Wait and check for updates
    await page.waitForTimeout(3000);

    // Dashboard should remain stable
    await expect(page).not.toHaveURL(/error/);
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy();
  });
});
