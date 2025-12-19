/**
 * Base Page Object
 * =================
 *
 * Shared functionality for all page objects.
 * All pages extend this class.
 */

import { Page, Locator, expect } from '@playwright/test';

export abstract class BasePage {
  readonly page: Page;
  readonly baseURL: string;

  constructor(page: Page) {
    this.page = page;
    this.baseURL = process.env.TEST_BASE_URL || 'http://localhost:3000';
  }

  // ============================================
  // NAVIGATION
  // ============================================

  abstract get path(): string;

  async goto(): Promise<void> {
    await this.page.goto(`${this.baseURL}${this.path}`);
    await this.waitForPageLoad();
  }

  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
  }

  // ============================================
  // COMMON LOCATORS (Test IDs)
  // ============================================

  /**
   * Get element by data-testid attribute
   * Preferred selector strategy for resilience
   */
  getByTestId(testId: string): Locator {
    return this.page.locator(`[data-testid="${testId}"]`);
  }

  /**
   * Get element by role and name
   */
  getButton(name: string | RegExp): Locator {
    return this.page.getByRole('button', { name });
  }

  getLink(name: string | RegExp): Locator {
    return this.page.getByRole('link', { name });
  }

  getTab(name: string | RegExp): Locator {
    return this.page.getByRole('tab', { name });
  }

  getInput(name: string | RegExp): Locator {
    return this.page.getByRole('textbox', { name });
  }

  // ============================================
  // COMMON ACTIONS
  // ============================================

  async clickButton(name: string | RegExp): Promise<void> {
    await this.getButton(name).click();
  }

  async clickTab(name: string | RegExp): Promise<void> {
    await this.getTab(name).click();
  }

  async fillInput(name: string | RegExp, value: string): Promise<void> {
    await this.getInput(name).fill(value);
  }

  // ============================================
  // COMMON ASSERTIONS
  // ============================================

  async expectVisible(locator: Locator, timeout = 10000): Promise<void> {
    await expect(locator).toBeVisible({ timeout });
  }

  async expectHidden(locator: Locator, timeout = 10000): Promise<void> {
    await expect(locator).toBeHidden({ timeout });
  }

  async expectText(locator: Locator, text: string | RegExp): Promise<void> {
    await expect(locator).toContainText(text);
  }

  async expectCount(locator: Locator, count: number): Promise<void> {
    await expect(locator).toHaveCount(count);
  }

  // ============================================
  // ERROR HANDLING
  // ============================================

  async hasNoJSErrors(): Promise<boolean> {
    // Check for critical error indicators in DOM
    const errorBoundary = this.page.locator('[class*="error-boundary"], [class*="ErrorBoundary"]');
    const errorCount = await errorBoundary.count();
    return errorCount === 0;
  }

  async getPageTitle(): Promise<string> {
    return this.page.title();
  }

  async getCurrentURL(): Promise<string> {
    return this.page.url();
  }

  // ============================================
  // WAITING UTILITIES
  // ============================================

  async waitForSelector(selector: string, timeout = 10000): Promise<Locator> {
    const locator = this.page.locator(selector);
    await locator.waitFor({ timeout });
    return locator;
  }

  async waitForResponse(urlPattern: string | RegExp): Promise<void> {
    await this.page.waitForResponse(urlPattern);
  }

  async waitForNavigation(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
  }

  // ============================================
  // SCREENSHOT
  // ============================================

  async screenshot(name: string): Promise<void> {
    await this.page.screenshot({ path: `./test-results/screenshots/${name}.png` });
  }
}
