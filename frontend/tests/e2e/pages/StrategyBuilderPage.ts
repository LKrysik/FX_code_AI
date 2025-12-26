/**
 * Strategy Builder Page Object
 * =============================
 *
 * Visual strategy builder with:
 * - 5-section condition system (S1→O1→Z1→ZE1→E1)
 * - Strategy list and management
 * - Condition configuration
 * - State machine visualization
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export type StrategySection = 'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1';

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
  readonly sectionTabs: Locator;
  readonly activeSection: Locator;

  // Section tabs (5-section system)
  readonly s1Tab: Locator;
  readonly o1Tab: Locator;
  readonly z1Tab: Locator;
  readonly ze1Tab: Locator;
  readonly e1Tab: Locator;

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
    this.sectionTabs = page.getByRole('tablist');
    this.activeSection = page.locator('[role="tabpanel"]');

    // Section tabs
    this.s1Tab = page.getByRole('tab', { name: /S1|Start/i });
    this.o1Tab = page.getByRole('tab', { name: /O1|Open/i });
    this.z1Tab = page.getByRole('tab', { name: /Z1|Zone/i });
    this.ze1Tab = page.getByRole('tab', { name: /ZE1|Zone Exit/i });
    this.e1Tab = page.getByRole('tab', { name: /E1|Exit/i });

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
    const tabMap = {
      S1: this.s1Tab,
      O1: this.o1Tab,
      Z1: this.z1Tab,
      ZE1: this.ze1Tab,
      E1: this.e1Tab,
    };
    await tabMap[section].click();
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

  async expectSectionTabsVisible(): Promise<void> {
    await expect(this.sectionTabs).toBeVisible();
    await expect(this.s1Tab).toBeVisible();
    await expect(this.e1Tab).toBeVisible();
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

  async getActiveSection(): Promise<string | null> {
    const activeTab = this.page.locator('[role="tab"][aria-selected="true"]');
    return activeTab.textContent();
  }
}
