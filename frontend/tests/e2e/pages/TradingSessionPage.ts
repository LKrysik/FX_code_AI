/**
 * Trading Session Page Object
 * ============================
 *
 * Page for configuring and starting trading sessions:
 * - Trading mode selection (Live/Paper/Backtest)
 * - Strategy selection
 * - Symbol selection
 * - Session parameters
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export type TradingMode = 'Live' | 'Paper' | 'Backtest';

export class TradingSessionPage extends BasePage {
  // ============================================
  // LOCATORS
  // ============================================

  // Mode selection
  readonly liveButton: Locator;
  readonly paperButton: Locator;
  readonly backtestButton: Locator;
  readonly selectedModeIndicator: Locator;

  // Strategy section
  readonly strategySection: Locator;
  readonly strategyList: Locator;
  readonly strategyCheckboxes: Locator;
  readonly noStrategiesMessage: Locator;

  // Symbol section
  readonly symbolSection: Locator;
  readonly symbolList: Locator;
  readonly symbolCheckboxes: Locator;
  readonly symbolSearch: Locator;

  // Session parameters
  readonly leverageInput: Locator;
  readonly positionSizeInput: Locator;
  readonly stopLossInput: Locator;
  readonly takeProfitInput: Locator;

  // Actions
  readonly startButton: Locator;
  readonly resetButton: Locator;
  readonly validationErrors: Locator;

  constructor(page: Page) {
    super(page);

    // Mode selection - use more specific locators to avoid matching "Start X Session" buttons
    this.liveButton = page.getByRole('button', { name: /Live Trading/i }).or(
      page.locator('[value="live"]')
    );
    this.paperButton = page.getByRole('button', { name: /Paper Trading/i }).or(
      page.locator('[value="paper"]')
    );
    this.backtestButton = page.getByRole('button', { name: /Backtest/i }).first();
    this.selectedModeIndicator = page.locator('[data-testid="selected-mode"]');

    // Strategy section
    this.strategySection = page.locator('[data-testid="strategy-section"]');
    this.strategyList = page.locator('[data-testid="strategy-list"]');
    this.strategyCheckboxes = page.locator('input[type="checkbox"][name*="strategy"]');
    this.noStrategiesMessage = page.locator('text=/No strategies available/i');

    // Symbol section
    this.symbolSection = page.locator('[data-testid="symbol-section"]');
    this.symbolList = page.locator('[data-testid="symbol-list"]');
    this.symbolCheckboxes = page.locator('input[type="checkbox"][name*="symbol"]');
    this.symbolSearch = page.getByPlaceholder(/Search symbols/i);

    // Session parameters
    this.leverageInput = page.locator('[data-testid="leverage-input"]');
    this.positionSizeInput = page.locator('[data-testid="position-size-input"]');
    this.stopLossInput = page.locator('[data-testid="stop-loss-input"]');
    this.takeProfitInput = page.locator('[data-testid="take-profit-input"]');

    // Actions
    this.startButton = page.getByRole('button', { name: /Start Session|Begin/i });
    this.resetButton = page.getByRole('button', { name: /Reset|Clear/i });
    this.validationErrors = page.locator('[class*="error"], [class*="Error"]');
  }

  get path(): string {
    return '/trading-session';
  }

  // ============================================
  // ACTIONS
  // ============================================

  async selectMode(mode: TradingMode): Promise<void> {
    const modeButton = mode === 'Live' ? this.liveButton :
                       mode === 'Paper' ? this.paperButton : this.backtestButton;

    await modeButton.click();

    // Wait for mode switch to complete by checking for visual feedback
    await this.page.evaluate(() => {
      return Promise.all(document.getAnimations().map((a) => a.finished));
    });
  }

  async selectStrategy(strategyName: string): Promise<void> {
    const checkbox = this.page.locator(`[data-testid="strategy-checkbox-${strategyName}"]`);
    if (await checkbox.isVisible()) {
      await checkbox.check();
    } else {
      // Fallback: find checkbox near strategy name text
      const strategyRow = this.page.locator(`text="${strategyName}"`).locator('..').locator('input[type="checkbox"]');
      await strategyRow.check();
    }
  }

  async selectStrategies(strategyNames: string[]): Promise<void> {
    for (const name of strategyNames) {
      await this.selectStrategy(name);
    }
  }

  async selectSymbol(symbol: string): Promise<void> {
    // Search if search box is available
    if (await this.symbolSearch.isVisible()) {
      await this.symbolSearch.fill(symbol);
      // Wait for search results to filter (debounce)
      await this.page.waitForLoadState('domcontentloaded');
    }

    const checkbox = this.page.locator(`[data-testid="symbol-checkbox-${symbol}"]`);
    if (await checkbox.isVisible()) {
      await checkbox.check();
    } else {
      // Fallback
      const symbolRow = this.page.locator(`text="${symbol}"`).locator('..').locator('input[type="checkbox"]');
      await symbolRow.check();
    }
  }

  async selectSymbols(symbols: string[]): Promise<void> {
    for (const symbol of symbols) {
      await this.selectSymbol(symbol);
    }
  }

  async setLeverage(leverage: number): Promise<void> {
    await this.leverageInput.fill(leverage.toString());
  }

  async setPositionSize(size: number): Promise<void> {
    await this.positionSizeInput.fill(size.toString());
  }

  async setStopLoss(percent: number): Promise<void> {
    await this.stopLossInput.fill(percent.toString());
  }

  async setTakeProfit(percent: number): Promise<void> {
    await this.takeProfitInput.fill(percent.toString());
  }

  async startSession(): Promise<void> {
    await this.startButton.click();
  }

  async resetForm(): Promise<void> {
    await this.resetButton.click();
  }

  // ============================================
  // COMPOSITE ACTIONS (Full Flows)
  // ============================================

  async configureAndStartSession(config: {
    mode: TradingMode;
    strategies: string[];
    symbols: string[];
    leverage?: number;
    positionSize?: number;
  }): Promise<void> {
    await this.selectMode(config.mode);
    await this.selectStrategies(config.strategies);
    await this.selectSymbols(config.symbols);

    if (config.leverage) {
      await this.setLeverage(config.leverage);
    }
    if (config.positionSize) {
      await this.setPositionSize(config.positionSize);
    }

    await this.startSession();
  }

  // ============================================
  // ASSERTIONS
  // ============================================

  async expectModeSelected(mode: TradingMode): Promise<void> {
    const modeButton =
      mode === 'Live' ? this.liveButton : mode === 'Paper' ? this.paperButton : this.backtestButton;
    await expect(modeButton).toHaveAttribute('aria-pressed', 'true');
  }

  async expectStrategySelected(strategyName: string): Promise<void> {
    const checkbox = this.page.locator(`[data-testid="strategy-checkbox-${strategyName}"]`);
    await expect(checkbox).toBeChecked();
  }

  async expectSymbolSelected(symbol: string): Promise<void> {
    const checkbox = this.page.locator(`[data-testid="symbol-checkbox-${symbol}"]`);
    await expect(checkbox).toBeChecked();
  }

  async expectNoValidationErrors(): Promise<void> {
    await expect(this.validationErrors).toHaveCount(0);
  }

  async expectValidationError(errorText: string | RegExp): Promise<void> {
    await expect(this.page.locator(`text=${errorText}`)).toBeVisible();
  }

  async expectStartButtonEnabled(): Promise<void> {
    await expect(this.startButton).toBeEnabled();
  }

  async expectStartButtonDisabled(): Promise<void> {
    await expect(this.startButton).toBeDisabled();
  }

  // ============================================
  // DATA EXTRACTION
  // ============================================

  async getAvailableStrategies(): Promise<string[]> {
    const strategies: string[] = [];
    const items = this.strategyList.locator('[data-testid*="strategy-item"]');
    const count = await items.count();

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) strategies.push(text.trim());
    }

    return strategies;
  }

  async getSelectedStrategiesCount(): Promise<number> {
    const checked = this.page.locator('input[type="checkbox"][name*="strategy"]:checked');
    return checked.count();
  }

  async getSelectedSymbolsCount(): Promise<number> {
    const checked = this.page.locator('input[type="checkbox"][name*="symbol"]:checked');
    return checked.count();
  }
}
