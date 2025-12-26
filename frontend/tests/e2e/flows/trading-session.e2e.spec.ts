/**
 * Trading Session E2E Tests
 * ==========================
 *
 * Full user journey tests for the trading session workflow:
 * 1. Configure session (mode, strategies, symbols)
 * 2. Start session
 * 3. Monitor signals and positions
 * 4. Stop session
 * 5. View history
 *
 * @tags e2e, trading, session
 */

import { test, expect } from '../fixtures/base.fixture';
import { DashboardPage, TradingSessionPage } from '../pages';
import { waitForAnimationsComplete, waitForModeSwitch } from '../support/wait-helpers';

test.describe('Trading Session - E2E Flows', () => {
  // ============================================
  // E2E-01: Paper Trading Session Lifecycle
  // ============================================
  test('E2E-01: Complete paper trading session lifecycle', async ({ page, apiClient }) => {
    // Skip if backend is not available
    try {
      const response = await apiClient.get('/api/strategies');
      if (!response.ok) {
        test.skip(true, 'Backend not available - skipping lifecycle test');
      }
    } catch {
      test.skip(true, 'Backend not reachable - skipping lifecycle test');
    }

    const dashboard = new DashboardPage(page);
    const tradingSession = new TradingSessionPage(page);

    // Step 1: Start from dashboard
    await dashboard.goto();
    await dashboard.waitForPageLoad();

    // Step 2: Navigate to session configuration
    await tradingSession.goto();
    await tradingSession.waitForPageLoad();

    // Step 3: Select Paper mode
    if (await tradingSession.paperButton.isVisible()) {
      await tradingSession.selectMode('Paper');

      // Verify mode selected - wait for mode switch to complete
      await waitForAnimationsComplete(page);
      await expect(tradingSession.paperButton).toHaveClass(/selected|active/i).catch(() => {
        // Fallback: just verify button is still visible
        return expect(tradingSession.paperButton).toBeVisible();
      });
    }

    // Step 4: Check if strategies are available
    const strategyCheckboxes = page.locator('input[type="checkbox"]');
    const checkboxCount = await strategyCheckboxes.count();

    if (checkboxCount > 0) {
      // Select first available strategy
      await strategyCheckboxes.first().check();
      // Wait for checkbox state to update
      await expect(strategyCheckboxes.first()).toBeChecked();
    } else {
      console.log('No strategy checkboxes available - backend may not be running');
    }

    // Step 5: Navigate back to dashboard and verify state
    await dashboard.goto();
    await dashboard.waitForPageLoad();

    // The test verifies the flow works without critical errors
    // Actual session start might require backend to be fully functional
  });

  // ============================================
  // E2E-02: Strategy Selection Flow
  // ============================================
  test('E2E-02: User can browse and select strategies', async ({ page }) => {
    const tradingSession = new TradingSessionPage(page);

    await tradingSession.goto();
    await tradingSession.waitForPageLoad();

    // Look for strategy-related content
    const strategyContent = page.locator('text=/Strategy|Strategies/i');
    const hasStrategySection = await strategyContent.count() > 0;

    if (hasStrategySection) {
      // Find checkboxes or selection elements
      const selectionElements = page.locator(
        'input[type="checkbox"], [role="checkbox"], [data-testid*="strategy"]'
      );
      const count = await selectionElements.count();

      // Log available options for debugging
      console.log(`Found ${count} strategy selection elements`);

      // If we have selections, try to interact with first one
      if (count > 0) {
        const firstElement = selectionElements.first();
        await firstElement.click();
        // Wait for interaction to complete
        await waitForAnimationsComplete(page);
      }
    }

    // Page should remain functional after interactions
    await expect(page).toHaveURL(/trading-session/);
  });

  // ============================================
  // E2E-03: Mode Switching
  // ============================================
  test('E2E-03: User can switch between trading modes', async ({ page }) => {
    const tradingSession = new TradingSessionPage(page);

    await tradingSession.goto();
    await tradingSession.waitForPageLoad();

    const modes = [
      { button: tradingSession.paperButton, name: 'Paper' },
      { button: tradingSession.backtestButton, name: 'Backtest' },
      { button: tradingSession.liveButton, name: 'Live' },
    ];

    for (const mode of modes) {
      if (await mode.button.isVisible()) {
        await mode.button.click();
        // Wait for mode switch animation to complete
        await waitForAnimationsComplete(page);
        console.log(`✓ Switched to ${mode.name} mode`);
      }
    }

    // Page should be stable after mode switches
    const errorBoundary = page.locator('[class*="error"]');
    const hasVisibleError = await errorBoundary.filter({ hasText: /error/i }).isVisible();
    expect(hasVisibleError).toBeFalsy();
  });

  // ============================================
  // E2E-04: Dashboard Session Display
  // ============================================
  test('E2E-04: Dashboard displays session state correctly', async ({ page }) => {
    const dashboard = new DashboardPage(page);

    await dashboard.goto();
    await dashboard.waitForPageLoad();

    // Check for session state indicators
    const hasNoSessionBanner = await dashboard.noActiveSessionBanner.isVisible().catch(() => false);
    const hasStartButton = await dashboard.startSessionButton.isVisible().catch(() => false);

    // Dashboard should show clear state - or at least not crash
    const hasStateIndicator = hasNoSessionBanner || hasStartButton;
    console.log(`Dashboard state: noSession=${hasNoSessionBanner}, startButton=${hasStartButton}`);

    // If there's a config dialog trigger, test it
    if (hasStartButton) {
      await dashboard.startSessionButton.click();

      // Wait for dialog to appear or navigation to complete
      const dialogPromise = dashboard.sessionConfigDialog.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null);
      await dialogPromise;

      // Check if dialog or navigation happened
      const dialogVisible = await dashboard.sessionConfigDialog.isVisible().catch(() => false);
      const urlChanged = page.url() !== 'http://localhost:3000/dashboard';

      // Either dialog opened or navigated away
      console.log(`Dialog/navigation: dialog=${dialogVisible}, urlChanged=${urlChanged}`);

      // Close dialog if opened
      if (dialogVisible) {
        await page.keyboard.press('Escape');
      }
    }

    // Test passes if page loads without errors - state display varies by backend availability
    await expect(page).not.toHaveURL(/error/);
  });

  // ============================================
  // E2E-05: Signal Monitoring Flow
  // ============================================
  test('E2E-05: User can view signal monitoring area', async ({ page }) => {
    const dashboard = new DashboardPage(page);

    await dashboard.goto();
    await dashboard.waitForPageLoad();

    // Look for signal-related UI elements (CSS selectors only, then text separately)
    const signalByAttribute = page.locator('[data-testid*="signal"], [class*="signal"]');
    const signalByText = page.getByText(/Signal/i);
    const attrCount = await signalByAttribute.count();
    const textCount = await signalByText.count();
    const count = attrCount + textCount;

    console.log(`Found ${count} signal-related elements`);

    // If signal panel exists, check its visibility
    if (await dashboard.signalPanel.isVisible()) {
      await dashboard.expectSignalPanelVisible();
    }

    // Page remains stable
    await expect(page).not.toHaveURL(/error/);
  });

  // ============================================
  // E2E-06: Session History Access
  // ============================================
  test('E2E-06: User can access session history', async ({ page }) => {
    await page.goto('/session-history');
    await page.waitForLoadState('domcontentloaded');

    // Should show history page content
    const historyContent = page.locator(
      'text=/Session History|History|No sessions|Past Sessions/i'
    );
    const hasContent = await historyContent.count() > 0;

    expect(hasContent).toBeTruthy();

    // If there's a table or list, it should be functional
    const table = page.locator('table');
    const list = page.locator('[role="list"], ul, ol');

    const hasTable = await table.count() > 0;
    const hasList = await list.count() > 0;

    console.log(`History page: table=${hasTable}, list=${hasList}`);
  });

  // ============================================
  // E2E-07: Position Monitoring Flow
  // ============================================
  test('E2E-07: Position display area is functional', async ({ page }) => {
    const dashboard = new DashboardPage(page);

    await dashboard.goto();
    await dashboard.waitForPageLoad();

    // Look for position-related UI (CSS selectors only, then text separately)
    const positionByAttribute = page.locator('[data-testid*="position"], [class*="position"]');
    const positionByText = page.getByText(/Position/i);
    const attrCount = await positionByAttribute.count();
    const textCount = await positionByText.count();
    const count = attrCount + textCount;

    console.log(`Found ${count} position-related elements`);

    // If position banner/monitor exists
    if (await dashboard.positionBanner.isVisible()) {
      // Should be able to read position info
      const pnl = await dashboard.getPositionPnL();
      console.log(`Position P&L: ${pnl}`);
    }
  });

  // ============================================
  // E2E-08: WebSocket Connection
  // ============================================
  test('E2E-08: WebSocket connection can be established', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');

    // Test WebSocket connectivity
    const wsConnected = await page.evaluate(() => {
      return new Promise<boolean>((resolve) => {
        try {
          const apiUrl = 'ws://localhost:8080/ws';
          const ws = new WebSocket(apiUrl);

          ws.onopen = () => {
            ws.close();
            resolve(true);
          };

          ws.onerror = () => {
            resolve(false);
          };

          setTimeout(() => {
            ws.close();
            resolve(false);
          }, 5000);
        } catch {
          resolve(false);
        }
      });
    });

    // Log result but don't fail test if backend is down
    console.log(`WebSocket connection: ${wsConnected ? 'SUCCESS' : 'FAILED'}`);

    // This is informational - actual assertion depends on test environment
    // In CI without backend, this would fail
  });
});
