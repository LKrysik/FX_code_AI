/**
 * Indicators Page Object
 * =======================
 *
 * Indicator management page with:
 * - Indicator catalog
 * - Variant management
 * - Configuration
 * - Real-time preview
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class IndicatorsPage extends BasePage {
  // ============================================
  // LOCATORS
  // ============================================

  // Tabs
  readonly catalogTab: Locator;
  readonly variantManagerTab: Locator;
  readonly activeIndicatorsTab: Locator;
  readonly tabs: Locator;

  // Indicator list
  readonly indicatorList: Locator;
  readonly indicatorCards: Locator;
  readonly searchInput: Locator;
  readonly categoryFilter: Locator;

  // Variant manager
  readonly variantTable: Locator;
  readonly variantRows: Locator;
  readonly createVariantButton: Locator;
  readonly deleteVariantButton: Locator;

  // Configuration panel
  readonly configPanel: Locator;
  readonly parameterInputs: Locator;
  readonly applyButton: Locator;
  readonly resetButton: Locator;

  // Preview
  readonly previewChart: Locator;
  readonly previewValues: Locator;

  constructor(page: Page) {
    super(page);

    // Tabs - use first() to handle multiple tab groups, and flexible matching
    this.tabs = page.getByRole('tablist').first();
    this.catalogTab = page.getByRole('tab', { name: /Catalog/i }).first();
    // Try exact match first, fallback to partial match
    this.variantManagerTab = page.getByRole('tab', { name: 'Variant Manager' }).or(
      page.getByRole('tab', { name: /^Variant Manager$/i })
    ).first();
    this.activeIndicatorsTab = page.getByRole('tab', { name: /Active/i }).first();

    // Indicator list
    this.indicatorList = page.locator('[data-testid="indicator-list"]');
    this.indicatorCards = page.locator('[data-testid="indicator-card"]');
    this.searchInput = page.getByPlaceholder(/Search indicator/i);
    this.categoryFilter = page.locator('[data-testid="category-filter"]');

    // Variant manager
    this.variantTable = page.locator('[data-testid="variant-table"]');
    this.variantRows = page.locator('[data-testid="variant-row"]');
    this.createVariantButton = page.getByRole('button', { name: /Create Variant|Add/i });
    this.deleteVariantButton = page.getByRole('button', { name: /Delete/i });

    // Configuration panel
    this.configPanel = page.locator('[data-testid="config-panel"]');
    this.parameterInputs = page.locator('[data-testid="parameter-input"]');
    this.applyButton = page.getByRole('button', { name: /Apply/i });
    this.resetButton = page.getByRole('button', { name: /Reset/i });

    // Preview
    this.previewChart = page.locator('[data-testid="indicator-preview"]');
    this.previewValues = page.locator('[data-testid="preview-values"]');
  }

  get path(): string {
    return '/indicators';
  }

  // ============================================
  // ACTIONS
  // ============================================

  async selectTab(tab: 'Catalog' | 'Variant Manager' | 'Active'): Promise<void> {
    switch (tab) {
      case 'Catalog':
        await this.catalogTab.click();
        break;
      case 'Variant Manager':
        await this.variantManagerTab.click();
        break;
      case 'Active':
        await this.activeIndicatorsTab.click();
        break;
    }
  }

  async searchIndicator(query: string): Promise<void> {
    await this.searchInput.fill(query);
    // Wait for search results to update (debounce handled by waiting for content change)
    await this.page.waitForLoadState('domcontentloaded');
  }

  async selectIndicator(indicatorName: string): Promise<void> {
    const card = this.indicatorCards.filter({ hasText: indicatorName });
    await card.click();
  }

  async selectCategory(category: string): Promise<void> {
    await this.categoryFilter.click();
    await this.page.locator(`[role="option"]:has-text("${category}")`).click();
  }

  async createVariant(): Promise<void> {
    await this.createVariantButton.click();
  }

  async configureParameter(paramName: string, value: string): Promise<void> {
    const input = this.page.locator(`[data-testid="param-${paramName}"]`);
    await input.fill(value);
  }

  async applyConfiguration(): Promise<void> {
    await this.applyButton.click();
  }

  async resetConfiguration(): Promise<void> {
    await this.resetButton.click();
  }

  // ============================================
  // ASSERTIONS
  // ============================================

  async expectTabsVisible(): Promise<void> {
    await expect(this.tabs).toBeVisible();
  }

  async expectTabCount(count: number): Promise<void> {
    const tabs = this.page.getByRole('tab');
    await expect(tabs).toHaveCount(count);
  }

  async expectIndicatorCardCount(count: number): Promise<void> {
    await expect(this.indicatorCards).toHaveCount(count);
  }

  async expectIndicatorVisible(indicatorName: string): Promise<void> {
    const card = this.indicatorCards.filter({ hasText: indicatorName });
    await expect(card).toBeVisible();
  }

  async expectVariantTableVisible(): Promise<void> {
    await expect(this.variantTable).toBeVisible();
  }

  async expectConfigPanelVisible(): Promise<void> {
    await expect(this.configPanel).toBeVisible();
  }

  async expectPreviewVisible(): Promise<void> {
    await expect(this.previewChart).toBeVisible();
  }

  // ============================================
  // DATA EXTRACTION
  // ============================================

  async getIndicatorNames(): Promise<string[]> {
    const names: string[] = [];
    const count = await this.indicatorCards.count();

    for (let i = 0; i < count; i++) {
      const card = this.indicatorCards.nth(i);
      const title = card.locator('[data-testid="indicator-name"]');
      const text = await title.textContent();
      if (text) names.push(text.trim());
    }

    return names;
  }

  async getVariantCount(): Promise<number> {
    return this.variantRows.count();
  }

  async getActiveTabName(): Promise<string | null> {
    const activeTab = this.page.locator('[role="tab"][aria-selected="true"]');
    return activeTab.textContent();
  }
}
