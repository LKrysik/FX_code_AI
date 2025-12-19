/**
 * Dashboard Page Object
 * ======================
 *
 * Main trading dashboard with:
 * - Session status display
 * - Real-time indicators
 * - Signal monitoring
 * - Position overview
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class DashboardPage extends BasePage {
  // ============================================
  // LOCATORS
  // ============================================

  // Session controls
  readonly noActiveSessionBanner: Locator;
  readonly startSessionButton: Locator;
  readonly stopSessionButton: Locator;
  readonly sessionConfigDialog: Locator;

  // Session status
  readonly sessionStatusBadge: Locator;
  readonly activeStrategiesCount: Locator;
  readonly activeSymbolsCount: Locator;

  // Real-time data
  readonly indicatorPanel: Locator;
  readonly signalPanel: Locator;
  readonly transactionHistory: Locator;

  // Charts
  readonly priceChart: Locator;
  readonly chartCanvas: Locator;

  // Position
  readonly positionBanner: Locator;
  readonly positionPnL: Locator;

  constructor(page: Page) {
    super(page);

    // Session controls
    this.noActiveSessionBanner = page.locator('text=/No Active Session/i');
    this.startSessionButton = page.getByRole('button', { name: /Start|Configure|New Session/i });
    this.stopSessionButton = page.getByRole('button', { name: /Stop/i });
    this.sessionConfigDialog = page.locator('[role="dialog"]');

    // Session status
    this.sessionStatusBadge = page.locator('[data-testid="session-status"]');
    this.activeStrategiesCount = page.locator('[data-testid="active-strategies-count"]');
    this.activeSymbolsCount = page.locator('[data-testid="active-symbols-count"]');

    // Real-time data
    this.indicatorPanel = page.locator('[data-testid="indicator-panel"]');
    this.signalPanel = page.locator('[data-testid="signal-panel"]');
    this.transactionHistory = page.locator('[data-testid="transaction-history"]');

    // Charts
    this.priceChart = page.locator('[data-testid="price-chart"]');
    this.chartCanvas = page.locator('canvas');

    // Position
    this.positionBanner = page.locator('[data-testid="position-banner"]');
    this.positionPnL = page.locator('[data-testid="position-pnl"]');
  }

  get path(): string {
    return '/dashboard';
  }

  // ============================================
  // ACTIONS
  // ============================================

  async openSessionConfig(): Promise<void> {
    await this.startSessionButton.click();
    await expect(this.sessionConfigDialog).toBeVisible();
  }

  async startSession(): Promise<void> {
    // Click start/confirm in dialog
    const startButton = this.sessionConfigDialog.getByRole('button', { name: /Start|Confirm/i });
    await startButton.click();
    await this.waitForSessionStart();
  }

  async stopSession(): Promise<void> {
    await this.stopSessionButton.click();
    // Confirm stop if dialog appears
    const confirmButton = this.page.getByRole('button', { name: /Confirm|Yes/i });
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
    await this.waitForSessionStop();
  }

  async selectTradingMode(mode: 'Live' | 'Paper' | 'Backtest'): Promise<void> {
    const modeButton = this.page.getByRole('button', { name: new RegExp(mode, 'i') });
    await modeButton.click();
  }

  async selectStrategy(strategyName: string): Promise<void> {
    const strategyCheckbox = this.page.locator(`input[type="checkbox"]`).filter({
      has: this.page.locator(`text="${strategyName}"`),
    });
    await strategyCheckbox.check();
  }

  async selectSymbol(symbol: string): Promise<void> {
    const symbolCheckbox = this.page.locator(`input[type="checkbox"]`).filter({
      has: this.page.locator(`text="${symbol}"`),
    });
    await symbolCheckbox.check();
  }

  // ============================================
  // WAIT CONDITIONS
  // ============================================

  async waitForSessionStart(timeout = 30000): Promise<void> {
    await expect(this.noActiveSessionBanner).toBeHidden({ timeout });
  }

  async waitForSessionStop(timeout = 30000): Promise<void> {
    await expect(this.noActiveSessionBanner).toBeVisible({ timeout });
  }

  async waitForIndicatorData(timeout = 30000): Promise<void> {
    await expect(this.indicatorPanel).toBeVisible({ timeout });
  }

  async waitForChartRender(timeout = 10000): Promise<void> {
    await expect(this.chartCanvas.first()).toBeVisible({ timeout });
  }

  // ============================================
  // ASSERTIONS
  // ============================================

  async expectNoActiveSession(): Promise<void> {
    await expect(this.noActiveSessionBanner).toBeVisible();
  }

  async expectActiveSession(): Promise<void> {
    await expect(this.noActiveSessionBanner).toBeHidden();
  }

  async expectSessionStatus(status: string): Promise<void> {
    await expect(this.sessionStatusBadge).toContainText(status);
  }

  async expectChartVisible(): Promise<void> {
    await expect(this.chartCanvas.first()).toBeVisible();
  }

  async expectIndicatorPanelVisible(): Promise<void> {
    await expect(this.indicatorPanel).toBeVisible();
  }

  async expectSignalPanelVisible(): Promise<void> {
    await expect(this.signalPanel).toBeVisible();
  }

  // ============================================
  // DATA EXTRACTION
  // ============================================

  async getSessionStatus(): Promise<string | null> {
    if (await this.sessionStatusBadge.isVisible()) {
      return this.sessionStatusBadge.textContent();
    }
    return null;
  }

  async getActiveStrategiesCount(): Promise<number> {
    const text = await this.activeStrategiesCount.textContent();
    return parseInt(text || '0', 10);
  }

  async getActiveSymbolsCount(): Promise<number> {
    const text = await this.activeSymbolsCount.textContent();
    return parseInt(text || '0', 10);
  }

  async getPositionPnL(): Promise<number | null> {
    if (await this.positionPnL.isVisible()) {
      const text = await this.positionPnL.textContent();
      return parseFloat(text?.replace(/[^0-9.-]/g, '') || '0');
    }
    return null;
  }
}
