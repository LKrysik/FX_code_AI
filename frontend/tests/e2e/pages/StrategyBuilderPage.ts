/**
 * Strategy Builder Page Object
 * =============================
 *
 * Visual strategy builder with:
 * - 5-section condition system using Accordions (S1→Z1→O1→ZE1→Emergency)
 * - Strategy list and management
 * - Condition configuration
 * - Import/Export functionality
 *
 * NOTE: The StrategyBuilder5Section component uses MUI Accordions,
 * not Tabs. Each section is an expandable accordion panel.
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export type StrategySection = 'S1' | 'Z1' | 'O1' | 'ZE1' | 'Emergency';

export class StrategyBuilderPage extends BasePage {
  // ============================================
  // LOCATORS
  // ============================================

  // Strategy list
  readonly strategyTable: Locator;
  readonly strategyRows: Locator;
  readonly createStrategyButton: Locator;
  readonly importStrategyButton: Locator;

  // Strategy editor
  readonly strategyNameInput: Locator;
  readonly strategyDescriptionInput: Locator;
  readonly sectionAccordions: Locator;
  readonly activeSection: Locator;

  // Section accordions (5-section system - MUI Accordions)
  readonly s1Accordion: Locator;
  readonly z1Accordion: Locator;
  readonly o1Accordion: Locator;
  readonly ze1Accordion: Locator;
  readonly emergencyAccordion: Locator;

  // Condition builder
  readonly addConditionButton: Locator;
  readonly conditionBlocks: Locator;
  readonly indicatorSelect: Locator;
  readonly operatorSelect: Locator;
  readonly valueInput: Locator;

  // Actions
  readonly saveButton: Locator;
  readonly deleteButton: Locator;
  readonly duplicateButton: Locator;
  readonly testButton: Locator;

  // State machine
  readonly stateMachineDiagram: Locator;

  constructor(page: Page) {
    super(page);

    // Strategy list
    this.strategyTable = page.locator('table');
    this.strategyRows = page.locator('tbody tr');
    this.createStrategyButton = page.getByRole('button', { name: /Create|New Strategy/i });
    this.importStrategyButton = page.getByRole('button', { name: /Import/i });

    // Strategy editor
    this.strategyNameInput = page.locator('[data-testid="strategy-name"]');
    this.strategyDescriptionInput = page.locator('[data-testid="strategy-description"]');
    this.sectionAccordions = page.locator('[class*="MuiAccordion"]');
    this.activeSection = page.locator('[class*="MuiAccordionDetails"], [class*="MuiCollapse-entered"]');

    // Section accordions (MUI Accordion components)
    // These match the AccordionSummary text patterns from StrategyBuilder5Section.tsx
    this.s1Accordion = page.locator('[class*="MuiAccordion"]').filter({ hasText: /S1.*Signal|Signal.*Detection/i });
    this.z1Accordion = page.locator('[class*="MuiAccordion"]').filter({ hasText: /Z1.*Entry|Order.*Entry/i });
    this.o1Accordion = page.locator('[class*="MuiAccordion"]').filter({ hasText: /O1.*Cancel|Signal.*Cancel/i });
    this.ze1Accordion = page.locator('[class*="MuiAccordion"]').filter({ hasText: /ZE1.*Close|Order.*Closing/i });
    this.emergencyAccordion = page.locator('[class*="MuiAccordion"]').filter({ hasText: /Emergency/i });

    // Condition builder
    this.addConditionButton = page.getByRole('button', { name: /Add Condition/i });
    this.conditionBlocks = page.locator('[data-testid="condition-block"]');
    this.indicatorSelect = page.locator('[data-testid="indicator-select"]');
    this.operatorSelect = page.locator('[data-testid="operator-select"]');
    this.valueInput = page.locator('[data-testid="value-input"]');

    // Actions
    this.saveButton = page.getByRole('button', { name: /Save/i });
    this.deleteButton = page.getByRole('button', { name: /Delete/i });
    this.duplicateButton = page.getByRole('button', { name: /Duplicate|Clone/i });
    this.testButton = page.getByRole('button', { name: /Test|Validate/i });

    // State machine
    this.stateMachineDiagram = page.locator('[data-testid="state-machine-diagram"]');
  }

  get path(): string {
    return '/strategy-builder';
  }

  // ============================================
  // ACTIONS
  // ============================================

  async createNewStrategy(): Promise<void> {
    await this.createStrategyButton.click();
  }

  async selectStrategy(strategyName: string): Promise<void> {
    const row = this.strategyRows.filter({ hasText: strategyName });
    await row.click();
  }

  async setStrategyName(name: string): Promise<void> {
    await this.strategyNameInput.fill(name);
  }

  async setStrategyDescription(description: string): Promise<void> {
    await this.strategyDescriptionInput.fill(description);
  }

  async selectSection(section: StrategySection): Promise<void> {
    const accordionMap = {
      S1: this.s1Accordion,
      Z1: this.z1Accordion,
      O1: this.o1Accordion,
      ZE1: this.ze1Accordion,
      Emergency: this.emergencyAccordion,
    };
    // Click on the accordion summary to expand/collapse
    const accordion = accordionMap[section];
    const summary = accordion.locator('[class*="MuiAccordionSummary"]');
    await summary.click();
    // Wait for expansion animation
    await this.page.waitForTimeout(300);
  }

  async addCondition(): Promise<void> {
    await this.addConditionButton.click();
  }

  async configureCondition(
    index: number,
    config: {
      indicator: string;
      operator: string;
      value: string;
    }
  ): Promise<void> {
    const block = this.conditionBlocks.nth(index);

    // Select indicator
    await block.locator('[data-testid="indicator-select"]').click();
    await this.page.locator(`[role="option"]:has-text("${config.indicator}")`).click();

    // Select operator
    await block.locator('[data-testid="operator-select"]').click();
    await this.page.locator(`[role="option"]:has-text("${config.operator}")`).click();

    // Set value
    await block.locator('[data-testid="value-input"]').fill(config.value);
  }

  async saveStrategy(): Promise<void> {
    // Wait for save API response
    const savePromise = this.page.waitForResponse(
      (resp) => resp.url().includes('/api/strategies') && resp.request().method() === 'POST'
    ).catch(() => null);

    await this.saveButton.click();
    await savePromise;

    // Wait for success feedback
    await this.page.waitForLoadState('domcontentloaded');
  }

  async deleteStrategy(): Promise<void> {
    await this.deleteButton.click();
    // Confirm deletion
    const confirmButton = this.page.getByRole('button', { name: /Confirm|Yes|Delete/i });
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  async duplicateStrategy(): Promise<void> {
    await this.duplicateButton.click();
  }

  // ============================================
  // COMPOSITE ACTIONS
  // ============================================

  async createBasicStrategy(config: {
    name: string;
    description?: string;
    conditions: Array<{
      section: StrategySection;
      indicator: string;
      operator: string;
      value: string;
    }>;
  }): Promise<void> {
    await this.createNewStrategy();
    await this.setStrategyName(config.name);

    if (config.description) {
      await this.setStrategyDescription(config.description);
    }

    for (const condition of config.conditions) {
      await this.selectSection(condition.section);
      await this.addCondition();
      const conditionIndex = (await this.conditionBlocks.count()) - 1;
      await this.configureCondition(conditionIndex, {
        indicator: condition.indicator,
        operator: condition.operator,
        value: condition.value,
      });
    }

    await this.saveStrategy();
  }

  // ============================================
  // ASSERTIONS
  // ============================================

  async expectStrategyListVisible(): Promise<void> {
    await expect(this.strategyTable).toBeVisible();
  }

  async expectStrategyCount(count: number): Promise<void> {
    await expect(this.strategyRows).toHaveCount(count);
  }

  async expectStrategyInList(strategyName: string): Promise<void> {
    await expect(this.strategyRows.filter({ hasText: strategyName })).toBeVisible();
  }

  async expectSectionAccordionsVisible(): Promise<void> {
    await expect(this.sectionAccordions.first()).toBeVisible();
    await expect(this.s1Accordion).toBeVisible();
    await expect(this.emergencyAccordion).toBeVisible();
  }

  async expectConditionBlockCount(count: number): Promise<void> {
    await expect(this.conditionBlocks).toHaveCount(count);
  }

  async expectSaveButtonEnabled(): Promise<void> {
    await expect(this.saveButton).toBeEnabled();
  }

  async expectStateMachineDiagramVisible(): Promise<void> {
    await expect(this.stateMachineDiagram).toBeVisible();
  }

  // ============================================
  // DATA EXTRACTION
  // ============================================

  async getStrategyNames(): Promise<string[]> {
    const names: string[] = [];
    const count = await this.strategyRows.count();

    for (let i = 0; i < count; i++) {
      const row = this.strategyRows.nth(i);
      const nameCell = row.locator('td').first();
      const text = await nameCell.textContent();
      if (text) names.push(text.trim());
    }

    return names;
  }

  async getConditionCount(): Promise<number> {
    return this.conditionBlocks.count();
  }

  async getExpandedSections(): Promise<string[]> {
    // Find all expanded accordions (MUI uses aria-expanded or class Mui-expanded)
    const expandedAccordions = this.page.locator('[class*="MuiAccordion"][class*="Mui-expanded"], [class*="MuiAccordion"][aria-expanded="true"]');
    const count = await expandedAccordions.count();
    const sections: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await expandedAccordions.nth(i).locator('[class*="MuiAccordionSummary"]').textContent();
      if (text) sections.push(text.trim());
    }

    return sections;
  }

  async getAccordionCount(): Promise<number> {
    return this.sectionAccordions.count();
  }
}
