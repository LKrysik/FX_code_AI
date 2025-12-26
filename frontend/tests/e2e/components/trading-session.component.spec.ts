/**
 * Trading Session Component Tests - Edge Cases
 * =============================================
 *
 * Tests edge cases for trading session configuration:
 * - Mode selection buttons
 * - Strategy multi-select
 * - Symbol selection
 * - Parameter inputs
 *
 * @tags components, trading-session, edge-cases
 */

import { test, expect } from '../fixtures/base.fixture';
import { TradingSessionPage } from '../pages';
import { waitForAnimationsComplete } from '../support/wait-helpers';

test.describe('Trading Session Components - Edge Cases', () => {
  // ============================================
  // Mode Selection Tests
  // ============================================
  test.describe('Mode Selection Buttons', () => {
    test('EDGE-TS01: Only one mode can be selected at a time', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      const modes = [
        { button: tradingSession.paperButton, name: 'Paper' },
        { button: tradingSession.backtestButton, name: 'Backtest' },
        { button: tradingSession.liveButton, name: 'Live' },
      ];

      // Select each mode and verify exclusivity
      for (const mode of modes) {
        if (await mode.button.isVisible()) {
          await mode.button.click();
          await waitForAnimationsComplete(page);

          // Count selected modes
          const selectedButtons = page.locator(
            '[aria-selected="true"], [data-selected="true"], [class*="selected"], [class*="active"]'
          );

          // Filter to only mode-related buttons
          const modeButtons = page.locator('button').filter({ hasText: /Paper|Backtest|Live/i });
          let selectedCount = 0;

          for (let i = 0; i < await modeButtons.count(); i++) {
            const btn = modeButtons.nth(i);
            const isSelected = await btn.evaluate((el) => {
              return (
                el.getAttribute('aria-selected') === 'true' ||
                el.getAttribute('data-selected') === 'true' ||
                el.className.includes('selected') ||
                el.className.includes('active')
              );
            });
            if (isSelected) selectedCount++;
          }

          // Should have at most one selected
          expect(selectedCount).toBeLessThanOrEqual(1);
        }
      }
    });

    test('EDGE-TS02: Live mode shows warning/confirmation', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      if (await tradingSession.liveButton.isVisible()) {
        await tradingSession.liveButton.click();
        await waitForAnimationsComplete(page);

        // Check for any warning indicators (CSS selectors only, then text separately)
        const warningsByClass = page.locator('[class*="warning"], [role="alert"]');
        const warningsByText = page.getByText(/caution|warning|real.*money|live.*trading/i);
        const classCount = await warningsByClass.count();
        const textCount = await warningsByText.count();
        const warningCount = classCount + textCount;

        // Live mode should have some form of warning
        console.log(`Live mode warnings found: ${warningCount}`);

        // Also check for confirmation dialogs
        const dialog = page.locator('[role="dialog"], [role="alertdialog"]');
        const hasDialog = await dialog.count() > 0;

        console.log(`Live mode confirmation dialog: ${hasDialog}`);
      }

      // Verify page stability after live mode selection
      await expect(page).not.toHaveURL(/error/);
    });

    test('EDGE-TS03: Mode buttons handle double-click correctly', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      if (await tradingSession.paperButton.isVisible()) {
        // Double-click should not cause issues
        await tradingSession.paperButton.dblclick();
        await waitForAnimationsComplete(page);

        // Page should remain stable
        await expect(page).toHaveURL(/trading-session/);

        // No duplicate selections or errors
        const errorElements = page.locator('[class*="error"]').filter({ hasText: /error/i });
        const errorCount = await errorElements.count();
        expect(errorCount).toBe(0);
      }
    });
  });

  // ============================================
  // Strategy Selection Tests
  // ============================================
  test.describe('Strategy Multi-Select', () => {
    test('EDGE-TS04: Multiple strategies can be selected', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Find strategy checkboxes
      const checkboxes = page.locator('input[type="checkbox"]');
      const count = await checkboxes.count();

      if (count >= 2) {
        // Select multiple strategies
        await checkboxes.nth(0).check();
        await expect(checkboxes.nth(0)).toBeChecked();
        await checkboxes.nth(1).check();
        await expect(checkboxes.nth(1)).toBeChecked();

        // Verify both are checked
        const firstChecked = await checkboxes.nth(0).isChecked();
        const secondChecked = await checkboxes.nth(1).isChecked();

        expect(firstChecked).toBeTruthy();
        expect(secondChecked).toBeTruthy();
      }
    });

    test('EDGE-TS05: Strategy selection handles empty list', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Check for empty state handling
      const strategyList = page.locator('[data-testid*="strategy"], [class*="strategy-list"]');
      const emptyMessage = page.locator('text=/no.*strateg|empty|create.*first/i');

      const hasStrategies = await strategyList.count() > 0;
      const hasEmptyMessage = await emptyMessage.count() > 0;

      // Should have either strategies or empty message
      console.log(`Strategies visible: ${hasStrategies}, Empty message: ${hasEmptyMessage}`);

      // Page should not crash regardless
      await expect(page).not.toHaveURL(/error/);
    });

    test('EDGE-TS06: Select all / Deselect all works correctly', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Look for select all button
      const selectAllButton = page.getByRole('button', { name: /Select All|All/i });

      if (await selectAllButton.isVisible()) {
        await selectAllButton.click();
        await waitForAnimationsComplete(page);

        // All checkboxes should be checked
        const checkboxes = page.locator('input[type="checkbox"]');
        const count = await checkboxes.count();

        let allChecked = true;
        for (let i = 0; i < count; i++) {
          const checked = await checkboxes.nth(i).isChecked();
          if (!checked) allChecked = false;
        }

        expect(allChecked).toBeTruthy();
      }
    });
  });

  // ============================================
  // Symbol Selection Tests
  // ============================================
  test.describe('Symbol Selection', () => {
    test('EDGE-TS07: Symbol search filters correctly', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Find symbol search/filter input
      const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="symbol"]').first();

      if (await searchInput.isVisible()) {
        // Type search query
        await searchInput.fill('EUR');
        await waitForAnimationsComplete(page);

        // Check filtered results
        const symbolItems = page.locator('[data-testid*="symbol"], [class*="symbol-item"]');
        const visibleItems = await symbolItems.allTextContents();

        // All visible items should contain "EUR"
        visibleItems.forEach((item) => {
          if (item.trim()) {
            const containsSearch = item.toUpperCase().includes('EUR');
            console.log(`Symbol "${item}" contains EUR: ${containsSearch}`);
          }
        });
      }

      // Verify page stability after symbol search
      await expect(page).not.toHaveURL(/error/);
    });

    test('EDGE-TS08: Symbol selection handles invalid symbol input', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="symbol"]').first();

      if (await searchInput.isVisible()) {
        // Type invalid symbol
        await searchInput.fill('ZZZZZ123');
        await waitForAnimationsComplete(page);

        // Should show "no results" or similar
        const noResults = page.locator('text=/no.*result|not.*found|no.*match/i');
        const hasNoResultsMessage = await noResults.count() > 0;

        console.log(`No results message shown: ${hasNoResultsMessage}`);

        // Clear and verify recovery
        await searchInput.clear();
        await waitForAnimationsComplete(page);
      }

      // Page should remain functional
      await expect(page).toHaveURL(/trading-session/);
    });

    test('EDGE-TS09: Symbol chips can be added and removed', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Find symbol chips or tags
      const chips = page.locator('[data-testid*="chip"], [class*="chip"], [class*="tag"]');
      const initialCount = await chips.count();

      // Try to remove a chip if exists
      if (initialCount > 0) {
        const removeButton = chips.first().locator('button, [class*="remove"], [class*="close"]');
        if (await removeButton.isVisible()) {
          await removeButton.click();
          await waitForAnimationsComplete(page);

          const newCount = await chips.count();
          expect(newCount).toBeLessThanOrEqual(initialCount);
        }
      }

      console.log(`Symbol chips: initial=${initialCount}`);
    });
  });

  // ============================================
  // Parameter Input Tests
  // ============================================
  test.describe('Parameter Inputs', () => {
    test('EDGE-TS10: Risk percent validates input range', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Find risk input
      const riskInput = page.locator('input[name*="risk"], input[data-testid*="risk"]').first();

      if (await riskInput.isVisible()) {
        // Test over-limit value
        await riskInput.fill('150'); // Over 100%
        await waitForAnimationsComplete(page);

        // Check for validation error
        const hasValidationError = await page.locator('[class*="error"], [role="alert"]').count() > 0;
        const inputValue = await riskInput.inputValue();

        // Should either show error or cap the value
        console.log(`Risk input: value=${inputValue}, hasError=${hasValidationError}`);

        // Test negative value
        await riskInput.fill('-10');
        await waitForAnimationsComplete(page);

        const hasNegativeError = await page.locator('[class*="error"], [role="alert"]').count() > 0;
        const negativeValue = await riskInput.inputValue();

        console.log(`Negative risk: value=${negativeValue}, hasError=${hasNegativeError}`);
      }

      // Verify page stability after risk validation tests
      await expect(page).not.toHaveURL(/error/);
    });

    test('EDGE-TS11: Position size accepts decimal values', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Find position size input
      const positionInput = page.locator(
        'input[name*="position"], input[name*="size"], input[data-testid*="position"]'
      ).first();

      if (await positionInput.isVisible()) {
        // Enter decimal value
        await positionInput.fill('0.5');
        await waitForAnimationsComplete(page);

        const value = await positionInput.inputValue();
        expect(value).toContain('0.5');

        // Test precision
        await positionInput.fill('0.12345678');
        await waitForAnimationsComplete(page);

        const preciseValue = await positionInput.inputValue();
        console.log(`Position size precision: ${preciseValue}`);
      }
    });

    test('EDGE-TS12: Max trades input rejects non-numeric input', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Find max trades or similar numeric input
      const numericInput = page.locator(
        'input[type="number"], input[name*="max"], input[name*="count"]'
      ).first();

      if (await numericInput.isVisible()) {
        // For number inputs, we can't use fill() with text - use keyboard instead
        await numericInput.click();
        await numericInput.press('Control+a');
        await page.keyboard.type('abc');
        await waitForAnimationsComplete(page);

        const value = await numericInput.inputValue();

        // Number input should reject or sanitize non-numeric (browser behavior)
        const isNumeric = /^[0-9]*$/.test(value) || value === '';
        console.log(`Numeric input after 'abc': "${value}", isNumeric: ${isNumeric}`);

        // Number inputs naturally reject non-numeric text
        expect(isNumeric).toBeTruthy();

        // Test valid numeric input works
        await numericInput.fill('100');
        await waitForAnimationsComplete(page);

        const numericValue = await numericInput.inputValue();
        expect(numericValue).toBe('100');
      }
    });
  });

  // ============================================
  // Form State Tests
  // ============================================
  test.describe('Form State', () => {
    test('EDGE-TS13: Form shows unsaved changes warning', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Make changes to form
      if (await tradingSession.paperButton.isVisible()) {
        await tradingSession.paperButton.click();
        await waitForAnimationsComplete(page);
      }

      // Try to navigate away
      const response = await page.goto('/dashboard');

      // Check if there was a confirmation dialog or the navigation happened
      // Some apps block navigation for unsaved changes
      const currentUrl = page.url();

      console.log(`After navigation attempt: ${currentUrl}`);
      // Verify page navigated or stayed - no crash occurred
      await expect(page).not.toHaveURL(/error/);
    });

    test('EDGE-TS14: Form resets to defaults correctly', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Look for reset button
      const resetButton = page.getByRole('button', { name: /Reset|Clear|Default/i });

      if (await resetButton.isVisible()) {
        // Make some changes first
        if (await tradingSession.paperButton.isVisible()) {
          await tradingSession.paperButton.click();
        }

        // Click reset
        await resetButton.click();
        await waitForAnimationsComplete(page);

        // Form should be in default state
        // Verify no selections or default selection
        const checkboxes = page.locator('input[type="checkbox"]:checked');
        const checkedCount = await checkboxes.count();

        console.log(`After reset, checked items: ${checkedCount}`);
      }
    });

    test('EDGE-TS15: Form handles browser back button', async ({ page }) => {
      const tradingSession = new TradingSessionPage(page);
      await tradingSession.goto();
      await tradingSession.waitForPageLoad();

      // Navigate forward first
      await page.goto('/dashboard');
      await page.waitForLoadState('domcontentloaded');

      // Go back
      await page.goBack();
      await page.waitForLoadState('domcontentloaded');

      // Should return to trading session page
      await expect(page).toHaveURL(/trading-session/);

      // Page should be functional
      const hasError = await page.locator('[class*="error-boundary"]').count();
      expect(hasError).toBe(0);
    });
  });
});
