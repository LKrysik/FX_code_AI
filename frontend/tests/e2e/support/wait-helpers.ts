/**
 * Deterministic Wait Helpers
 * ===========================
 *
 * Replace hard waits (waitForTimeout) with deterministic waiting strategies.
 * These helpers wait for actual conditions rather than arbitrary time delays.
 *
 * Usage:
 *   import { waitForElementStable, waitForAnimationComplete } from '../support/wait-helpers';
 *
 * @see TEA Knowledge Base: test-quality.md, network-first.md
 */

import { Page, Locator, expect } from '@playwright/test';

/**
 * Wait for an element to become stable (no position/size changes)
 * Replaces: await page.waitForTimeout(300-500) after clicks
 */
export async function waitForElementStable(
  locator: Locator,
  options: { timeout?: number } = {}
): Promise<void> {
  const { timeout = 5000 } = options;
  await locator.waitFor({ state: 'visible', timeout });

  // Wait for element to stop moving (animations complete)
  let lastBox = await locator.boundingBox();
  let stable = false;
  const startTime = Date.now();

  while (!stable && Date.now() - startTime < timeout) {
    await new Promise((r) => setTimeout(r, 50));
    const currentBox = await locator.boundingBox();

    if (
      lastBox &&
      currentBox &&
      lastBox.x === currentBox.x &&
      lastBox.y === currentBox.y &&
      lastBox.width === currentBox.width &&
      lastBox.height === currentBox.height
    ) {
      stable = true;
    }
    lastBox = currentBox;
  }
}

/**
 * Wait for any CSS animations/transitions to complete on page
 * Replaces: await page.waitForTimeout(200-500) after UI changes
 * Includes timeout to prevent hanging on infinite animations
 */
export async function waitForAnimationsComplete(page: Page): Promise<void> {
  await page.evaluate(() => {
    const animations = document.getAnimations();
    if (animations.length === 0) return Promise.resolve();
    // Wait max 2 seconds for animations, then proceed anyway
    return Promise.race([
      Promise.all(animations.map((a) => a.finished)),
      new Promise((resolve) => setTimeout(resolve, 2000)),
    ]);
  }).catch(() => {
    // Ignore errors from aborted animations or navigation
  });
}

/**
 * Wait for network to be idle (no pending requests)
 * Replaces: await page.waitForTimeout(1000-3000) after navigation
 */
export async function waitForNetworkSettled(
  page: Page,
  options: { timeout?: number; idleTime?: number } = {}
): Promise<void> {
  const { timeout = 10000, idleTime = 500 } = options;

  await page.waitForLoadState('domcontentloaded', { timeout });

  // Wait for no network activity for idleTime ms
  let lastActivity = Date.now();
  const startTime = Date.now();

  const requestHandler = () => {
    lastActivity = Date.now();
  };

  page.on('request', requestHandler);
  page.on('response', requestHandler);

  try {
    while (Date.now() - startTime < timeout) {
      if (Date.now() - lastActivity >= idleTime) {
        return;
      }
      await new Promise((r) => setTimeout(r, 100));
    }
  } finally {
    page.off('request', requestHandler);
    page.off('response', requestHandler);
  }
}

/**
 * Wait for a specific element to appear after an action
 * Replaces: action(); await page.waitForTimeout(X); expect(element)
 */
export async function waitForElementAfterAction(
  action: () => Promise<void>,
  locator: Locator,
  options: { timeout?: number; state?: 'visible' | 'attached' | 'hidden' } = {}
): Promise<void> {
  const { timeout = 10000, state = 'visible' } = options;
  await action();
  await locator.waitFor({ state, timeout });
}

/**
 * Wait for dialog/modal to appear and stabilize
 * Replaces: click(); await page.waitForTimeout(500);
 */
export async function waitForDialogOpen(
  page: Page,
  options: { timeout?: number } = {}
): Promise<Locator> {
  const { timeout = 5000 } = options;
  const dialog = page.locator('[role="dialog"]');
  await dialog.waitFor({ state: 'visible', timeout });
  await waitForAnimationsComplete(page);
  return dialog;
}

/**
 * Wait for dialog/modal to close
 * Replaces: closeDialog(); await page.waitForTimeout(300);
 */
export async function waitForDialogClose(
  page: Page,
  options: { timeout?: number } = {}
): Promise<void> {
  const { timeout = 5000 } = options;
  const dialog = page.locator('[role="dialog"]');
  await dialog.waitFor({ state: 'hidden', timeout });
}

/**
 * Wait for button/element to be interactive after action
 * Replaces: await page.waitForTimeout(200-300) between clicks
 */
export async function waitForInteractive(
  locator: Locator,
  options: { timeout?: number } = {}
): Promise<void> {
  const { timeout = 5000 } = options;
  await expect(locator).toBeEnabled({ timeout });
  await expect(locator).toBeVisible({ timeout });
}

/**
 * Wait for mode/tab switch to complete
 * Replaces: click(mode); await page.waitForTimeout(500);
 */
export async function waitForModeSwitch(
  page: Page,
  modeLocator: Locator,
  options: { timeout?: number } = {}
): Promise<void> {
  const { timeout = 5000 } = options;

  // Wait for aria-selected or similar indicator
  await expect(modeLocator).toHaveAttribute('aria-selected', 'true', { timeout }).catch(() => {
    // Fallback: wait for visual indication (class change)
    return expect(modeLocator).toHaveClass(/selected|active|current/i, { timeout });
  });

  await waitForAnimationsComplete(page);
}

/**
 * Wait for checkbox/toggle state change
 * Replaces: check(checkbox); await page.waitForTimeout(300);
 */
export async function waitForCheckboxState(
  checkbox: Locator,
  checked: boolean,
  options: { timeout?: number } = {}
): Promise<void> {
  const { timeout = 5000 } = options;

  if (checked) {
    await expect(checkbox).toBeChecked({ timeout });
  } else {
    await expect(checkbox).not.toBeChecked({ timeout });
  }
}

/**
 * Wait for form validation to complete
 * Replaces: submit(); await page.waitForTimeout(300);
 */
export async function waitForFormValidation(
  page: Page,
  options: { timeout?: number } = {}
): Promise<{ hasErrors: boolean; errorCount: number }> {
  const { timeout = 5000 } = options;

  // Wait for any validation UI to appear
  await page.waitForLoadState('domcontentloaded');

  const errorLocator = page.locator('[class*="error"], [role="alert"], [aria-invalid="true"]');
  const errorCount = await errorLocator.count();

  return {
    hasErrors: errorCount > 0,
    errorCount,
  };
}

/**
 * Click and wait for response pattern (network-first)
 * Replaces: click(); await page.waitForTimeout(X);
 */
export async function clickAndWaitForResponse(
  locator: Locator,
  page: Page,
  urlPattern: string | RegExp,
  options: { timeout?: number } = {}
): Promise<Response | null> {
  const { timeout = 10000 } = options;

  const responsePromise = page.waitForResponse(urlPattern, { timeout });
  await locator.click();

  try {
    const response = await responsePromise;
    return response;
  } catch {
    return null;
  }
}

/**
 * Navigate and wait for specific API response (network-first)
 * Replaces: goto(); await page.waitForTimeout(X);
 */
export async function gotoAndWaitForApi(
  page: Page,
  url: string,
  apiPattern: string | RegExp,
  options: { timeout?: number } = {}
): Promise<void> {
  const { timeout = 30000 } = options;

  const responsePromise = page.waitForResponse(apiPattern, { timeout });
  await page.goto(url);
  await responsePromise;
}

// Type for Response to use in the helper above
type Response = Awaited<ReturnType<Page['waitForResponse']>>;
