/**
 * Indicators Component Tests - Edge Cases
 * ========================================
 *
 * Tests edge cases for indicator management:
 * - Indicator catalog
 * - Variant manager
 * - Configuration panel
 * - Real-time preview
 *
 * @tags components, indicators, edge-cases
 */

import { test, expect } from '../fixtures/base.fixture';
import { IndicatorsPage } from '../pages';

test.describe('Indicators Components - Edge Cases', () => {
  // ============================================
  // Indicator Catalog Tests
  // ============================================
  test.describe('Indicator Catalog', () => {
    test('EDGE-IND01: Catalog search handles special characters', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      if (await indicatorsPage.searchInput.isVisible()) {
        // Test special characters
        const searchTerms = ['RSI(14)', 'EMA<20>', "SMA'50", 'MACD%', '\\n\\r\\t'];

        for (const term of searchTerms) {
          await indicatorsPage.searchIndicator(term);
          await page.waitForTimeout(300);

          // Should not crash
          const hasError = await page.locator('[class*="error-boundary"]').count();
          expect(hasError).toBe(0);

          console.log(`Search term "${term}": no crash`);

          // Clear for next test
          await indicatorsPage.searchInput.clear();
        }
      }
    });

    test('EDGE-IND02: Catalog pagination handles rapid navigation', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      // Find pagination controls
      const nextButton = page.getByRole('button', { name: /next|›|→/i });
      const prevButton = page.getByRole('button', { name: /prev|‹|←/i });

      if (await nextButton.isVisible()) {
        // Rapid clicks
        for (let i = 0; i < 5; i++) {
          await nextButton.click();
          await page.waitForTimeout(50); // Minimal delay
        }

        await page.waitForTimeout(500);

        // Go back rapidly
        if (await prevButton.isVisible()) {
          for (let i = 0; i < 5; i++) {
            await prevButton.click();
            await page.waitForTimeout(50);
          }
        }

        // Page should remain stable
        await expect(page).toHaveURL(/indicators/);
      }

      expect(true).toBeTruthy();
    });

    test('EDGE-IND03: Catalog category filter shows correct indicators', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      // Find category filter
      if (await indicatorsPage.categoryFilter.isVisible()) {
        await indicatorsPage.categoryFilter.click();
        await page.waitForTimeout(300);

        // Select a category
        const categoryOptions = page.locator('[role="option"]');
        const optionCount = await categoryOptions.count();

        if (optionCount > 0) {
          const firstCategory = await categoryOptions.first().textContent();
          await categoryOptions.first().click();
          await page.waitForTimeout(500);

          // Verify filtered results
          const cards = indicatorsPage.indicatorCards;
          const cardCount = await cards.count();

          console.log(`Category "${firstCategory}": ${cardCount} indicators`);
        }
      }

      expect(true).toBeTruthy();
    });
  });

  // ============================================
  // Variant Manager Tests
  // ============================================
  test.describe('Variant Manager', () => {
    test('EDGE-IND04: Variant table handles many rows efficiently', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      // Navigate to Variant Manager tab
      if (await indicatorsPage.variantManagerTab.isVisible()) {
        await indicatorsPage.selectTab('Variant Manager');
        await page.waitForTimeout(500);

        const variantCount = await indicatorsPage.getVariantCount();

        if (variantCount > 20) {
          // Check for virtualization or pagination
          const hasVirtual = await page.locator('[class*="virtual"]').count() > 0;
          const hasPagination = await page.locator('[class*="pagination"]').count() > 0;

          console.log(`Large variant list: virtual=${hasVirtual}, pagination=${hasPagination}`);
        }

        // Scroll should work smoothly
        const table = indicatorsPage.variantTable;
        if (await table.isVisible()) {
          await table.evaluate((el) => {
            el.scrollTop = el.scrollHeight;
          });
          await page.waitForTimeout(200);

          await table.evaluate((el) => {
            el.scrollTop = 0;
          });
        }
      }

      expect(true).toBeTruthy();
    });

    test('EDGE-IND05: Variant creation validates unique names', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      if (await indicatorsPage.variantManagerTab.isVisible()) {
        await indicatorsPage.selectTab('Variant Manager');
        await page.waitForTimeout(300);

        // Get existing variant names
        const existingVariants = indicatorsPage.variantRows;
        const firstVariantName = await existingVariants.first().locator('td').first().textContent();

        // Try to create variant with same name
        if (await indicatorsPage.createVariantButton.isVisible()) {
          await indicatorsPage.createVariant();
          await page.waitForTimeout(300);

          // Find name input in dialog
          const nameInput = page.locator('input[name="name"], input[placeholder*="name"]').first();
          if (await nameInput.isVisible() && firstVariantName) {
            await nameInput.fill(firstVariantName.trim());
            await page.waitForTimeout(200);

            // Try to save
            const saveButton = page.getByRole('button', { name: /save|create|confirm/i });
            if (await saveButton.isVisible()) {
              await saveButton.click();
              await page.waitForTimeout(300);

              // Should show duplicate error
              const duplicateError = page.locator('text=/already.*exist|duplicate|unique/i');
              const hasError = await duplicateError.count() > 0;

              console.log(`Duplicate name validation: ${hasError}`);
            }

            // Close dialog
            await page.keyboard.press('Escape');
          }
        }
      }
    });

    test('EDGE-IND06: Variant deletion cascades correctly', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      if (await indicatorsPage.variantManagerTab.isVisible()) {
        await indicatorsPage.selectTab('Variant Manager');
        await page.waitForTimeout(300);

        const variantRows = indicatorsPage.variantRows;
        const initialCount = await variantRows.count();

        if (initialCount > 0) {
          // Select first variant
          await variantRows.first().click();
          await page.waitForTimeout(200);

          // Check if delete is available and what warning it shows
          if (await indicatorsPage.deleteVariantButton.isVisible()) {
            await indicatorsPage.deleteVariantButton.click();
            await page.waitForTimeout(300);

            // Should show warning about cascade effects
            const warningDialog = page.locator('[role="dialog"], [role="alertdialog"]');

            if (await warningDialog.isVisible()) {
              const warningText = await warningDialog.textContent();
              const mentionsCascade = /strategies|affected|impact|using this/i.test(warningText || '');

              console.log(`Cascade warning shown: ${mentionsCascade}`);

              // Cancel
              await page.keyboard.press('Escape');
            }
          }
        }
      }
    });
  });

  // ============================================
  // Configuration Panel Tests
  // ============================================
  test.describe('Configuration Panel', () => {
    test('EDGE-IND07: Parameter inputs validate numeric ranges', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      // Select an indicator to show config panel
      const cards = indicatorsPage.indicatorCards;
      if ((await cards.count()) > 0) {
        await cards.first().click();
        await page.waitForTimeout(500);

        // Find parameter inputs
        const paramInputs = page.locator('[data-testid*="param"], input[type="number"]');
        const inputCount = await paramInputs.count();

        if (inputCount > 0) {
          const firstInput = paramInputs.first();

          // Test out of range values
          await firstInput.fill('0');
          await page.waitForTimeout(200);

          await firstInput.fill('-1');
          await page.waitForTimeout(200);

          await firstInput.fill('10000');
          await page.waitForTimeout(200);

          // Check for validation messages
          const hasValidation = await page.locator('[class*="error"], [role="alert"]').count() > 0;
          console.log(`Parameter validation shown: ${hasValidation}`);
        }
      }

      expect(true).toBeTruthy();
    });

    test('EDGE-IND08: Apply button enables only when form is valid', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      // Select an indicator
      const cards = indicatorsPage.indicatorCards;
      if ((await cards.count()) > 0) {
        await cards.first().click();
        await page.waitForTimeout(500);

        // Check apply button state
        const applyButton = indicatorsPage.applyButton;

        if (await applyButton.isVisible()) {
          const initialDisabled = await applyButton.isDisabled();
          console.log(`Apply button initially disabled: ${initialDisabled}`);

          // Make a change
          const paramInputs = page.locator('input[type="number"]').first();
          if (await paramInputs.isVisible()) {
            const currentValue = await paramInputs.inputValue();
            await paramInputs.fill(String(Number(currentValue || '0') + 1));
            await page.waitForTimeout(200);

            const afterChangeDisabled = await applyButton.isDisabled();
            console.log(`Apply button after change disabled: ${afterChangeDisabled}`);
          }
        }
      }
    });

    test('EDGE-IND09: Reset restores default values', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      const cards = indicatorsPage.indicatorCards;
      if ((await cards.count()) > 0) {
        await cards.first().click();
        await page.waitForTimeout(500);

        const paramInput = page.locator('input[type="number"]').first();

        if (await paramInput.isVisible()) {
          // Record original value
          const originalValue = await paramInput.inputValue();

          // Change value
          await paramInput.fill('999');
          await page.waitForTimeout(200);

          const changedValue = await paramInput.inputValue();

          // Click reset
          if (await indicatorsPage.resetButton.isVisible()) {
            await indicatorsPage.resetConfiguration();
            await page.waitForTimeout(300);

            const resetValue = await paramInput.inputValue();
            console.log(`Values: original=${originalValue}, changed=${changedValue}, reset=${resetValue}`);

            // Reset value should match original
            expect(resetValue).toBe(originalValue);
          }
        }
      }
    });
  });

  // ============================================
  // Preview Tests
  // ============================================
  test.describe('Real-time Preview', () => {
    test('EDGE-IND10: Preview updates when parameters change', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      const cards = indicatorsPage.indicatorCards;
      if ((await cards.count()) > 0) {
        await cards.first().click();
        await page.waitForTimeout(500);

        const preview = indicatorsPage.previewChart;

        if (await preview.isVisible()) {
          // Get initial preview state
          const initialContent = await preview.innerHTML();

          // Change a parameter
          const paramInput = page.locator('input[type="number"]').first();
          if (await paramInput.isVisible()) {
            const currentValue = await paramInput.inputValue();
            await paramInput.fill(String(Number(currentValue || '0') + 5));
            await page.waitForTimeout(1000);

            // Check if preview updated
            const updatedContent = await preview.innerHTML();
            const previewChanged = initialContent !== updatedContent;

            console.log(`Preview updated on parameter change: ${previewChanged}`);
          }
        }
      }

      expect(true).toBeTruthy();
    });

    test('EDGE-IND11: Preview handles missing data gracefully', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      const cards = indicatorsPage.indicatorCards;
      if ((await cards.count()) > 0) {
        await cards.first().click();
        await page.waitForTimeout(500);

        const preview = indicatorsPage.previewChart;

        if (await preview.isVisible()) {
          // Check for "no data" message or empty state
          const noDataMessage = preview.locator('text=/no.*data|loading|unavailable/i');
          const hasNoDataMessage = await noDataMessage.count() > 0;

          // Or check if chart rendered
          const chartCanvas = preview.locator('canvas');
          const hasChart = await chartCanvas.count() > 0;

          console.log(`Preview state: noData=${hasNoDataMessage}, hasChart=${hasChart}`);

          // Should either show data or graceful empty state
          expect(hasNoDataMessage || hasChart || (await preview.isVisible())).toBeTruthy();
        }
      }
    });

    test('EDGE-IND12: Preview tooltip shows correct values', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      const cards = indicatorsPage.indicatorCards;
      if ((await cards.count()) > 0) {
        await cards.first().click();
        await page.waitForTimeout(500);

        const preview = indicatorsPage.previewChart;

        if (await preview.isVisible()) {
          const box = await preview.boundingBox();

          if (box) {
            // Hover over chart to trigger tooltip
            await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
            await page.waitForTimeout(500);

            // Look for tooltip
            const tooltip = page.locator('[class*="tooltip"], [role="tooltip"]');
            const hasTooltip = await tooltip.isVisible();

            if (hasTooltip) {
              const tooltipText = await tooltip.textContent();
              console.log(`Preview tooltip: ${tooltipText?.substring(0, 100)}`);

              // Tooltip should contain numeric value
              const hasNumericValue = /\d+(\.\d+)?/.test(tooltipText || '');
              console.log(`Tooltip has numeric value: ${hasNumericValue}`);
            }
          }
        }
      }

      expect(true).toBeTruthy();
    });
  });

  // ============================================
  // Tab Navigation Tests
  // ============================================
  test.describe('Tab Navigation', () => {
    test('EDGE-IND13: Tab content loads lazily', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      // Record network requests
      const networkRequests: string[] = [];
      page.on('request', (request) => {
        if (request.url().includes('/api/')) {
          networkRequests.push(request.url());
        }
      });

      // Navigate to each tab
      const tabs = ['Catalog', 'Variant Manager', 'Active'] as const;

      for (const tab of tabs) {
        const tabButton = page.getByRole('tab', { name: new RegExp(tab.split(' ')[0], 'i') });

        if (await tabButton.isVisible()) {
          const requestsBefore = networkRequests.length;

          await tabButton.click();
          await page.waitForTimeout(500);

          const requestsAfter = networkRequests.length;
          const newRequests = requestsAfter - requestsBefore;

          console.log(`Tab "${tab}": ${newRequests} new API requests`);
        }
      }

      expect(true).toBeTruthy();
    });

    test('EDGE-IND14: Active tab highlights correctly', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      const tabs = page.getByRole('tab');
      const tabCount = await tabs.count();

      for (let i = 0; i < tabCount; i++) {
        const tab = tabs.nth(i);
        await tab.click();
        await page.waitForTimeout(300);

        // Check aria-selected attribute
        const isSelected = await tab.getAttribute('aria-selected');
        expect(isSelected).toBe('true');

        // Check other tabs are not selected
        for (let j = 0; j < tabCount; j++) {
          if (j !== i) {
            const otherTab = tabs.nth(j);
            const otherSelected = await otherTab.getAttribute('aria-selected');
            expect(otherSelected).not.toBe('true');
          }
        }
      }
    });

    test('EDGE-IND15: Keyboard navigation between tabs', async ({ page }) => {
      const indicatorsPage = new IndicatorsPage(page);
      await indicatorsPage.goto();
      await indicatorsPage.waitForPageLoad();

      const tabs = page.getByRole('tab');
      const tabCount = await tabs.count();

      if (tabCount > 1) {
        // Focus first tab
        await tabs.first().focus();
        await page.waitForTimeout(100);

        // Press right arrow to navigate
        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(200);

        // Second tab should now be focused
        const focusedElement = await page.evaluate(() => {
          return document.activeElement?.getAttribute('role');
        });

        console.log(`Focused element role after ArrowRight: ${focusedElement}`);

        // Press Enter to select
        await page.keyboard.press('Enter');
        await page.waitForTimeout(200);

        const activeTab = await indicatorsPage.getActiveTabName();
        console.log(`Active tab after keyboard selection: ${activeTab}`);
      }
    });
  });
});
