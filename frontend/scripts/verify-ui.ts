/**
 * AUTOMATYCZNA WERYFIKACJA UI
 * ============================
 *
 * Uruchamiane przez agentów po każdej zmianie frontend.
 *
 * USAGE: npx ts-node scripts/verify-ui.ts
 *
 * OUTPUT MUSI ZAWIERAĆ "ALL CHECKS PASSED" żeby zmiana była akceptowalna.
 *
 * DLACZEGO TO DZIAŁA:
 * - Używa Playwright (już zainstalowany w devDependencies)
 * - Selektory tekstowe i CSS (nie wymaga data-testid)
 * - Czeka na networkidle przed asercjami (obsługuje loading states)
 * - Sprawdza JS errors w konsoli (wykrywa runtime crashes)
 *
 * POTENCJALNE PROBLEMY:
 * - Backend musi działać na localhost:8080
 * - Frontend musi działać na localhost:3000
 * - Jeśli struktura UI się zmieni - selektory mogą przestać działać
 */

import { chromium, Browser, Page, ConsoleMessage } from 'playwright';

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
  FRONTEND_URL: process.env.FRONTEND_URL || 'http://localhost:3000',
  BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8080',
  TIMEOUT: 15000, // 15s per check
  MAX_LOAD_TIME: 5000, // 5s max acceptable load time
};

// ============================================================================
// Types
// ============================================================================

interface CheckResult {
  name: string;
  passed: boolean;
  error?: string;
  duration: number;
}

// ============================================================================
// Global state
// ============================================================================

const results: CheckResult[] = [];
const jsErrors: string[] = [];

// ============================================================================
// Helpers
// ============================================================================

function log(message: string): void {
  console.log(message);
}

function logCheck(name: string, passed: boolean, duration: number, error?: string): void {
  const status = passed ? '✓' : '✗';
  const durationStr = `(${duration}ms)`;

  if (passed) {
    log(`  ${status} ${name} ${durationStr}`);
  } else {
    log(`  ${status} ${name} ${durationStr}`);
    if (error) {
      log(`    Error: ${error}`);
    }
  }
}

async function check(name: string, fn: () => Promise<void>): Promise<void> {
  const start = Date.now();
  try {
    await fn();
    const duration = Date.now() - start;
    results.push({ name, passed: true, duration });
    logCheck(name, true, duration);
  } catch (e) {
    const duration = Date.now() - start;
    const error = e instanceof Error ? e.message : String(e);
    results.push({ name, passed: false, error, duration });
    logCheck(name, false, duration, error);
  }
}

// ============================================================================
// Pre-checks
// ============================================================================

async function checkBackend(): Promise<boolean> {
  try {
    const response = await fetch(`${CONFIG.BACKEND_URL}/health`);
    if (!response.ok) {
      throw new Error(`Backend returned status ${response.status}`);
    }
    const data = await response.json();
    if (data.status !== 'healthy') {
      throw new Error(`Backend status: ${data.status}`);
    }
    return true;
  } catch (e) {
    const error = e instanceof Error ? e.message : String(e);
    log(`[PRE-CHECK] Backend FAIL: ${error}`);
    return false;
  }
}

async function checkFrontend(): Promise<boolean> {
  try {
    const response = await fetch(CONFIG.FRONTEND_URL);
    if (!response.ok) {
      throw new Error(`Frontend returned status ${response.status}`);
    }
    return true;
  } catch (e) {
    const error = e instanceof Error ? e.message : String(e);
    log(`[PRE-CHECK] Frontend FAIL: ${error}`);
    return false;
  }
}

// ============================================================================
// UI Checks
// ============================================================================

async function runChecks(page: Page): Promise<void> {
  // Setup console error listener
  page.on('console', (msg: ConsoleMessage) => {
    if (msg.type() === 'error') {
      jsErrors.push(msg.text());
    }
  });

  page.on('pageerror', (err: Error) => {
    jsErrors.push(err.message);
  });

  log('\n[LEVEL 1] Dashboard');
  log('─'.repeat(40));

  // L1.1: Dashboard loads without crash
  await check('Dashboard renders without crash', async () => {
    await page.goto(CONFIG.FRONTEND_URL, {
      timeout: CONFIG.TIMEOUT,
      waitUntil: 'networkidle'
    });

    // Check page didn't crash (should have some content)
    const bodyText = await page.locator('body').textContent();
    if (!bodyText || bodyText.trim().length < 10) {
      throw new Error('Page appears empty');
    }
  });

  // L1.2: No JavaScript errors
  await check('No critical JavaScript errors', async () => {
    // Filter out non-critical errors (e.g., failed API calls are OK during test)
    const criticalErrors = jsErrors.filter(err =>
      !err.includes('Failed to fetch') &&
      !err.includes('Network request failed') &&
      !err.includes('ERR_CONNECTION_REFUSED')
    );

    if (criticalErrors.length > 0) {
      throw new Error(`Found ${criticalErrors.length} JS errors: ${criticalErrors[0]}`);
    }
  });

  // L1.3: Dashboard has main content area
  await check('Dashboard has main content area', async () => {
    await page.goto(CONFIG.FRONTEND_URL, { waitUntil: 'networkidle' });

    // Look for common dashboard elements
    const hasContent = await page.locator('.MuiGrid-root, .MuiCard-root, main').first().isVisible();
    if (!hasContent) {
      throw new Error('No main content area found');
    }
  });

  // L1.4: Dashboard shows loading or content (not blank)
  await check('Dashboard shows loading or content (not blank)', async () => {
    await page.goto(CONFIG.FRONTEND_URL);

    // Wait for either loading indicator OR actual content
    const hasLoadingOrContent = await Promise.race([
      page.locator('.MuiSkeleton-root').first().waitFor({ timeout: 3000 }).then(() => true).catch(() => false),
      page.locator('.MuiCircularProgress-root').first().waitFor({ timeout: 3000 }).then(() => true).catch(() => false),
      page.locator('.MuiCard-root').first().waitFor({ timeout: 3000 }).then(() => true).catch(() => false),
      page.getByText(/Dashboard|Trading|Market/i).first().waitFor({ timeout: 3000 }).then(() => true).catch(() => false),
    ]);

    if (!hasLoadingOrContent) {
      throw new Error('Page shows neither loading state nor content');
    }
  });

  log('\n[LEVEL 2] Trading Session Page');
  log('─'.repeat(40));

  // L2.1: Trading session page loads
  await check('Trading session page loads', async () => {
    await page.goto(`${CONFIG.FRONTEND_URL}/trading-session`, {
      timeout: CONFIG.TIMEOUT,
      waitUntil: 'networkidle'
    });

    const bodyText = await page.locator('body').textContent();
    if (!bodyText || bodyText.trim().length < 10) {
      throw new Error('Page appears empty');
    }
  });

  // L2.2: Mode selector visible (Live/Paper/Backtest)
  await check('Mode selector visible (Live/Paper/Backtest)', async () => {
    await page.goto(`${CONFIG.FRONTEND_URL}/trading-session`, { waitUntil: 'networkidle' });

    // Look for mode buttons - they should contain "Live", "Paper", "Backtest"
    const hasLive = await page.getByText(/Live/i).first().isVisible().catch(() => false);
    const hasPaper = await page.getByText(/Paper/i).first().isVisible().catch(() => false);
    const hasBacktest = await page.getByText(/Backtest/i).first().isVisible().catch(() => false);

    if (!hasLive && !hasPaper && !hasBacktest) {
      throw new Error('No mode selector found (expected Live/Paper/Backtest)');
    }
  });

  // L2.3: Start button exists
  await check('Start button exists', async () => {
    await page.goto(`${CONFIG.FRONTEND_URL}/trading-session`, { waitUntil: 'networkidle' });

    // Look for start button - can be "Start", "Start Session", "Start PAPER Session" etc.
    const startButton = page.getByRole('button', { name: /Start/i }).first();
    const isVisible = await startButton.isVisible().catch(() => false);

    if (!isVisible) {
      throw new Error('Start button not found');
    }
  });

  log('\n[LEVEL 3] Strategy Builder Page');
  log('─'.repeat(40));

  // L3.1: Strategy builder page loads
  await check('Strategy builder page loads', async () => {
    await page.goto(`${CONFIG.FRONTEND_URL}/strategy-builder`, {
      timeout: CONFIG.TIMEOUT,
      waitUntil: 'networkidle'
    });

    const bodyText = await page.locator('body').textContent();
    if (!bodyText || bodyText.trim().length < 10) {
      throw new Error('Page appears empty');
    }
  });

  // L3.2: Strategy builder shows tabs or sections
  await check('Strategy builder shows tabs or sections', async () => {
    await page.goto(`${CONFIG.FRONTEND_URL}/strategy-builder`, { waitUntil: 'networkidle' });

    // Look for tabs or strategy sections
    const hasTabs = await page.locator('.MuiTabs-root, .MuiTab-root').first().isVisible().catch(() => false);
    const hasCards = await page.locator('.MuiCard-root').first().isVisible().catch(() => false);
    const hasTable = await page.locator('.MuiTable-root, table').first().isVisible().catch(() => false);

    if (!hasTabs && !hasCards && !hasTable) {
      throw new Error('No tabs, cards, or table found on strategy builder');
    }
  });

  log('\n[PERFORMANCE] Load Times');
  log('─'.repeat(40));

  // PERF.1: Dashboard loads within acceptable time
  await check(`Dashboard loads in < ${CONFIG.MAX_LOAD_TIME}ms`, async () => {
    const start = Date.now();
    await page.goto(CONFIG.FRONTEND_URL, { waitUntil: 'networkidle' });
    const duration = Date.now() - start;

    if (duration > CONFIG.MAX_LOAD_TIME) {
      throw new Error(`Load took ${duration}ms (max ${CONFIG.MAX_LOAD_TIME}ms)`);
    }
  });

  // PERF.2: Trading session page loads within acceptable time
  await check(`Trading session page loads in < ${CONFIG.MAX_LOAD_TIME}ms`, async () => {
    const start = Date.now();
    await page.goto(`${CONFIG.FRONTEND_URL}/trading-session`, { waitUntil: 'networkidle' });
    const duration = Date.now() - start;

    if (duration > CONFIG.MAX_LOAD_TIME) {
      throw new Error(`Load took ${duration}ms (max ${CONFIG.MAX_LOAD_TIME}ms)`);
    }
  });
}

// ============================================================================
// Main
// ============================================================================

async function main(): Promise<void> {
  console.log('');
  console.log('═'.repeat(50));
  console.log('  UI VERIFICATION - AUTOMATED CHECKS');
  console.log('═'.repeat(50));
  console.log('');

  // Pre-checks
  log('[PRE-CHECKS]');
  log('─'.repeat(40));

  const backendOk = await checkBackend();
  log(`  ${backendOk ? '✓' : '✗'} Backend (${CONFIG.BACKEND_URL})`);

  const frontendOk = await checkFrontend();
  log(`  ${frontendOk ? '✓' : '✗'} Frontend (${CONFIG.FRONTEND_URL})`);

  if (!backendOk || !frontendOk) {
    log('');
    log('═'.repeat(50));
    log('  ❌ VERIFICATION ABORTED');
    log('═'.repeat(50));
    log('');
    log('Services not available. Please ensure:');
    log(`  1. Backend is running: curl ${CONFIG.BACKEND_URL}/health`);
    log(`  2. Frontend is running: curl ${CONFIG.FRONTEND_URL}`);
    log('');
    process.exit(1);
  }

  // Launch browser and run checks
  let browser: Browser | null = null;

  try {
    browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();

    await runChecks(page);

  } catch (e) {
    const error = e instanceof Error ? e.message : String(e);
    log(`\nBrowser error: ${error}`);
    results.push({ name: 'Browser launch', passed: false, error, duration: 0 });
  } finally {
    if (browser) {
      await browser.close();
    }
  }

  // Summary
  console.log('');
  console.log('═'.repeat(50));
  console.log('  VERIFICATION SUMMARY');
  console.log('═'.repeat(50));
  console.log('');

  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;
  const total = results.length;

  log(`Passed: ${passed}/${total}`);
  log(`Failed: ${failed}/${total}`);

  if (jsErrors.length > 0) {
    log(`\nJavaScript Errors Detected: ${jsErrors.length}`);
    jsErrors.slice(0, 3).forEach((err, i) => {
      log(`  ${i + 1}. ${err.substring(0, 100)}...`);
    });
  }

  if (failed > 0) {
    log('\nFailed Checks:');
    results.filter(r => !r.passed).forEach(r => {
      log(`  ✗ ${r.name}`);
      if (r.error) {
        log(`    → ${r.error}`);
      }
    });
  }

  console.log('');
  console.log('═'.repeat(50));

  if (failed === 0) {
    console.log('  ✓ ALL CHECKS PASSED');
    console.log('═'.repeat(50));
    process.exit(0);
  } else {
    console.log('  ❌ VERIFICATION FAILED');
    console.log('═'.repeat(50));
    process.exit(1);
  }
}

main().catch(e => {
  console.error('Script crashed:', e);
  process.exit(1);
});
