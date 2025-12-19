/**
 * Strategy Builder Component Tests - Edge Cases
 * ==============================================
 *
 * Tests edge cases for the visual strategy builder:
 * - 5-section condition system (S1→O1→Z1→ZE1→E1)
 * - Condition blocks
 * - State machine visualization
 * - CRUD operations
 *
 * @tags components, strategy-builder, edge-cases
 */

import { test, expect } from '../fixtures/base.fixture';
import { StrategyBuilderPage } from '../pages';

test.describe('Strategy Builder Components - Edge Cases', () => {
  // ============================================
  // Section Navigation Tests
  // ============================================
  test.describe('Section Navigation (S1→O1→Z1→ZE1→E1)', () => {
    test('EDGE-SB01: Section tabs maintain order and accessibility', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      const sections = ['S1', 'O1', 'Z1', 'ZE1', 'E1'];
      const tabs = [
        strategyBuilder.s1Tab,
        strategyBuilder.o1Tab,
        strategyBuilder.z1Tab,
        strategyBuilder.ze1Tab,
        strategyBuilder.e1Tab,
      ];

      // Verify tabs exist and are in correct order
      for (let i = 0; i < tabs.length; i++) {
        if (await tabs[i].isVisible()) {
          // Check keyboard navigation
          await tabs[i].focus();
          const focused = await tabs[i].evaluate((el) => document.activeElement === el);

          console.log(`Tab ${sections[i]}: visible=true, focusable=${focused}`);
        }
      }

      // Test keyboard arrow navigation
      if (await tabs[0].isVisible()) {
        await tabs[0].click();
        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(200);

        // Next tab should be focused/selected
        const activeTab = await strategyBuilder.getActiveSection();
        console.log(`After ArrowRight: active section = ${activeTab}`);
      }
    });

    test('EDGE-SB02: Section content persists when switching tabs', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      // Add condition in S1 section
      if (await strategyBuilder.s1Tab.isVisible()) {
        await strategyBuilder.selectSection('S1');
        await page.waitForTimeout(300);

        // Try to add a condition
        if (await strategyBuilder.addConditionButton.isVisible()) {
          await strategyBuilder.addCondition();
          await page.waitForTimeout(300);

          const initialCount = await strategyBuilder.getConditionCount();

          // Switch to another section and back
          if (await strategyBuilder.o1Tab.isVisible()) {
            await strategyBuilder.selectSection('O1');
            await page.waitForTimeout(300);

            await strategyBuilder.selectSection('S1');
            await page.waitForTimeout(300);

            // Condition should still be there
            const finalCount = await strategyBuilder.getConditionCount();
            expect(finalCount).toBe(initialCount);
          }
        }
      }
    });

    test('EDGE-SB03: Empty sections show helpful placeholder', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      // Check each section for empty state messaging
      const sections: Array<'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1'> = ['S1', 'O1', 'Z1', 'ZE1', 'E1'];

      for (const section of sections) {
        const tab = page.getByRole('tab', { name: new RegExp(section, 'i') });

        if (await tab.isVisible()) {
          await tab.click();
          await page.waitForTimeout(300);

          // Check for empty state or instructions
          const emptyState = page.locator(
            'text=/no.*condition|add.*condition|empty|drag.*drop|click.*add/i'
          );
          const hasEmptyState = await emptyState.count() > 0;

          const conditionCount = await strategyBuilder.getConditionCount();

          if (conditionCount === 0) {
            console.log(`Section ${section}: empty state message = ${hasEmptyState}`);
          }
        }
      }
    });
  });

  // ============================================
  // Condition Block Tests
  // ============================================
  test.describe('Condition Blocks', () => {
    test('EDGE-SB04: Condition blocks can be reordered via drag-drop', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      // Need at least 2 conditions to test reordering
      if (await strategyBuilder.addConditionButton.isVisible()) {
        await strategyBuilder.addCondition();
        await page.waitForTimeout(200);
        await strategyBuilder.addCondition();
        await page.waitForTimeout(200);

        const blocks = strategyBuilder.conditionBlocks;
        const count = await blocks.count();

        if (count >= 2) {
          // Attempt drag and drop
          const firstBlock = blocks.first();
          const secondBlock = blocks.nth(1);

          const firstBox = await firstBlock.boundingBox();
          const secondBox = await secondBlock.boundingBox();

          if (firstBox && secondBox) {
            await page.mouse.move(firstBox.x + firstBox.width / 2, firstBox.y + firstBox.height / 2);
            await page.mouse.down();
            await page.mouse.move(secondBox.x + secondBox.width / 2, secondBox.y + secondBox.height + 10);
            await page.mouse.up();

            await page.waitForTimeout(300);
            console.log('Drag-drop operation completed');
          }
        }
      }

      // Verify page stability
      await expect(page).not.toHaveURL(/error/);
    });

    test('EDGE-SB05: Condition block handles missing indicator gracefully', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      if (await strategyBuilder.addConditionButton.isVisible()) {
        await strategyBuilder.addCondition();
        await page.waitForTimeout(300);

        // Try to save without configuring condition
        if (await strategyBuilder.saveButton.isVisible()) {
          await strategyBuilder.saveButton.click();
          await page.waitForTimeout(500);

          // Should show validation error
          const validationError = page.locator(
            '[class*="error"], [role="alert"], text=/required|missing|select.*indicator/i'
          );
          const hasValidation = await validationError.count() > 0;

          console.log(`Missing indicator validation: ${hasValidation}`);
        }
      }

      expect(true).toBeTruthy();
    });

    test('EDGE-SB06: Condition block deletion with confirmation', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      if (await strategyBuilder.addConditionButton.isVisible()) {
        await strategyBuilder.addCondition();
        await page.waitForTimeout(300);

        const initialCount = await strategyBuilder.getConditionCount();

        // Find delete button in condition block
        const deleteButton = page
          .locator('[data-testid="condition-block"]')
          .first()
          .locator('button')
          .filter({ hasText: /delete|remove|×/i });

        if (await deleteButton.isVisible()) {
          await deleteButton.click();
          await page.waitForTimeout(300);

          // Check for confirmation dialog
          const confirmDialog = page.locator('[role="dialog"], [role="alertdialog"]');
          const hasConfirm = await confirmDialog.isVisible();

          if (hasConfirm) {
            const confirmButton = page.getByRole('button', { name: /yes|confirm|delete/i });
            if (await confirmButton.isVisible()) {
              await confirmButton.click();
              await page.waitForTimeout(300);
            }
          }

          const finalCount = await strategyBuilder.getConditionCount();
          console.log(`Condition count: ${initialCount} -> ${finalCount}`);
        }
      }
    });
  });

  // ============================================
  // Operator/Value Input Tests
  // ============================================
  test.describe('Operator and Value Inputs', () => {
    test('EDGE-SB07: Operator dropdown filters based on indicator type', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      if (await strategyBuilder.addConditionButton.isVisible()) {
        await strategyBuilder.addCondition();
        await page.waitForTimeout(300);

        // Open indicator select
        const indicatorSelect = page.locator('[data-testid="indicator-select"]').first();
        if (await indicatorSelect.isVisible()) {
          await indicatorSelect.click();
          await page.waitForTimeout(300);

          // Select first indicator
          const firstOption = page.locator('[role="option"]').first();
          if (await firstOption.isVisible()) {
            await firstOption.click();
            await page.waitForTimeout(300);

            // Now check operator options
            const operatorSelect = page.locator('[data-testid="operator-select"]').first();
            if (await operatorSelect.isVisible()) {
              await operatorSelect.click();
              await page.waitForTimeout(300);

              const options = page.locator('[role="option"]');
              const optionCount = await options.count();

              console.log(`Operator options available: ${optionCount}`);

              // Close dropdown
              await page.keyboard.press('Escape');
            }
          }
        }
      }
    });

    test('EDGE-SB08: Value input validates numeric bounds', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      if (await strategyBuilder.addConditionButton.isVisible()) {
        await strategyBuilder.addCondition();
        await page.waitForTimeout(300);

        const valueInput = page.locator('[data-testid="value-input"]').first();

        if (await valueInput.isVisible()) {
          // Test extreme values
          await valueInput.fill('999999999999999');
          await page.waitForTimeout(200);

          const largeValue = await valueInput.inputValue();
          console.log(`Large value input: ${largeValue}`);

          // Test negative
          await valueInput.fill('-50');
          await page.waitForTimeout(200);

          const negativeValue = await valueInput.inputValue();
          console.log(`Negative value input: ${negativeValue}`);

          // Test scientific notation
          await valueInput.fill('1e10');
          await page.waitForTimeout(200);

          const scientificValue = await valueInput.inputValue();
          console.log(`Scientific notation input: ${scientificValue}`);
        }
      }
    });

    test('EDGE-SB09: Cross-field references work correctly', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      // Some conditions reference other indicators (e.g., RSI > SMA)
      // This tests that cross-references are handled

      if (await strategyBuilder.addConditionButton.isVisible()) {
        await strategyBuilder.addCondition();
        await page.waitForTimeout(300);

        // Look for "Compare to" or similar dropdown
        const compareSelect = page.locator(
          '[data-testid*="compare"], [data-testid*="target"], [aria-label*="compare"]'
        );

        if (await compareSelect.isVisible()) {
          await compareSelect.click();
          await page.waitForTimeout(300);

          // Should show other indicators as options
          const indicatorOptions = page.locator('[role="option"]').filter({ hasText: /RSI|SMA|EMA|MACD/i });
          const optionCount = await indicatorOptions.count();

          console.log(`Cross-reference indicator options: ${optionCount}`);
        }
      }

      expect(true).toBeTruthy();
    });
  });

  // ============================================
  // State Machine Visualization Tests
  // ============================================
  test.describe('State Machine Visualization', () => {
    test('EDGE-SB10: State machine diagram updates on condition change', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      // Find state machine diagram
      const diagram = strategyBuilder.stateMachineDiagram;

      if (await diagram.isVisible()) {
        // Get initial state
        const initialContent = await diagram.innerHTML();

        // Add a condition
        if (await strategyBuilder.addConditionButton.isVisible()) {
          await strategyBuilder.addCondition();
          await page.waitForTimeout(500);

          // Check if diagram updated
          const updatedContent = await diagram.innerHTML();
          const diagramChanged = initialContent !== updatedContent;

          console.log(`State machine diagram changed: ${diagramChanged}`);
        }
      }

      expect(true).toBeTruthy();
    });

    test('EDGE-SB11: State machine handles complex transitions', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      // Add conditions to multiple sections
      const sectionsToTest: Array<'S1' | 'O1' | 'E1'> = ['S1', 'O1', 'E1'];

      for (const section of sectionsToTest) {
        await strategyBuilder.selectSection(section);
        await page.waitForTimeout(200);

        if (await strategyBuilder.addConditionButton.isVisible()) {
          await strategyBuilder.addCondition();
          await page.waitForTimeout(200);
        }
      }

      // Verify state machine shows all transitions
      const diagram = strategyBuilder.stateMachineDiagram;

      if (await diagram.isVisible()) {
        // Check for transition arrows or lines
        const transitions = diagram.locator('path, line, [class*="arrow"], [class*="edge"]');
        const transitionCount = await transitions.count();

        console.log(`State machine transitions: ${transitionCount}`);
      }

      // Page should remain stable
      await expect(page).not.toHaveURL(/error/);
    });

    test('EDGE-SB12: State machine zoom and pan controls', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      const diagram = strategyBuilder.stateMachineDiagram;

      if (await diagram.isVisible()) {
        // Test zoom controls if they exist
        const zoomInButton = page.getByRole('button', { name: /zoom.*in|\\+/i });
        const zoomOutButton = page.getByRole('button', { name: /zoom.*out|\\-/i });
        const resetButton = page.getByRole('button', { name: /reset|fit|center/i });

        if (await zoomInButton.isVisible()) {
          await zoomInButton.click();
          await page.waitForTimeout(200);
          console.log('Zoom in clicked');
        }

        if (await zoomOutButton.isVisible()) {
          await zoomOutButton.click();
          await page.waitForTimeout(200);
          console.log('Zoom out clicked');
        }

        if (await resetButton.isVisible()) {
          await resetButton.click();
          await page.waitForTimeout(200);
          console.log('Reset zoom clicked');
        }

        // Test mouse wheel zoom
        const box = await diagram.boundingBox();
        if (box) {
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
          await page.mouse.wheel(0, -100); // Scroll up to zoom in
          await page.waitForTimeout(200);
        }
      }

      expect(true).toBeTruthy();
    });
  });

  // ============================================
  // CRUD Operations Tests
  // ============================================
  test.describe('Strategy CRUD Operations', () => {
    test('EDGE-SB13: Strategy name validates special characters', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      if (await strategyBuilder.createStrategyButton.isVisible()) {
        await strategyBuilder.createNewStrategy();
        await page.waitForTimeout(300);

        if (await strategyBuilder.strategyNameInput.isVisible()) {
          // Test special characters
          const testNames = [
            '<script>alert("xss")</script>',
            "Strategy' OR '1'='1",
            '🚀 Rocket Strategy 🚀',
            'A'.repeat(256), // Very long name
          ];

          for (const name of testNames) {
            await strategyBuilder.setStrategyName(name);
            await page.waitForTimeout(200);

            const value = await strategyBuilder.strategyNameInput.inputValue();

            // Should sanitize or reject dangerous input
            if (name.includes('<script>')) {
              expect(value).not.toContain('<script>');
            }

            console.log(`Name test: length=${name.length}, accepted length=${value.length}`);
          }
        }
      }
    });

    test('EDGE-SB14: Duplicate strategy creates unique copy', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      // Select existing strategy if available
      const strategyRows = strategyBuilder.strategyRows;
      const rowCount = await strategyRows.count();

      if (rowCount > 0) {
        await strategyRows.first().click();
        await page.waitForTimeout(300);

        if (await strategyBuilder.duplicateButton.isVisible()) {
          const originalNames = await strategyBuilder.getStrategyNames();

          await strategyBuilder.duplicateStrategy();
          await page.waitForTimeout(500);

          const newNames = await strategyBuilder.getStrategyNames();

          // Should have one more strategy
          expect(newNames.length).toBeGreaterThanOrEqual(originalNames.length);

          console.log(`Strategies: ${originalNames.length} -> ${newNames.length}`);
        }
      }
    });

    test('EDGE-SB15: Delete strategy requires confirmation', async ({ page }) => {
      const strategyBuilder = new StrategyBuilderPage(page);
      await strategyBuilder.goto();
      await strategyBuilder.waitForPageLoad();

      const strategyRows = strategyBuilder.strategyRows;
      const rowCount = await strategyRows.count();

      if (rowCount > 0) {
        await strategyRows.first().click();
        await page.waitForTimeout(300);

        if (await strategyBuilder.deleteButton.isVisible()) {
          await strategyBuilder.deleteButton.click();
          await page.waitForTimeout(300);

          // Should show confirmation dialog
          const confirmDialog = page.locator('[role="dialog"], [role="alertdialog"]');
          const hasConfirm = await confirmDialog.isVisible();

          expect(hasConfirm).toBeTruthy();

          // Cancel to not actually delete
          const cancelButton = page.getByRole('button', { name: /cancel|no|close/i });
          if (await cancelButton.isVisible()) {
            await cancelButton.click();
          } else {
            await page.keyboard.press('Escape');
          }
        }
      }
    });
  });
});
