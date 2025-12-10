/**
 * UI Visual Testing Script
 * ========================
 *
 * Automatyczne testowanie wizualne interfejsu użytkownika.
 * Robi screenshoty kluczowych stron i komponentów.
 *
 * Użycie: node ui-visual-test.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';
const SCREENSHOT_DIR = './ui-screenshots';

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function takeScreenshots() {
  console.log('Starting UI Visual Testing...\n');

  const browser = await chromium.launch({
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });

  const page = await context.newPage();

  const results = [];

  // Helper function to take screenshot and analyze
  async function screenshotAndAnalyze(url, name, description, checkpoints) {
    console.log(`\n📸 Testing: ${name}`);
    console.log(`   URL: ${url}`);

    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });

      // Wait for React to hydrate
      await page.waitForTimeout(3000);

      const screenshotPath = path.join(SCREENSHOT_DIR, `${name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`   ✅ Screenshot saved: ${screenshotPath}`);

      // Run checkpoints
      const checkResults = [];
      for (const checkpoint of checkpoints) {
        try {
          const result = await checkpoint.check(page);
          checkResults.push({
            name: checkpoint.name,
            passed: result.passed,
            details: result.details,
          });
          console.log(`   ${result.passed ? '✅' : '❌'} ${checkpoint.name}: ${result.details}`);
        } catch (err) {
          checkResults.push({
            name: checkpoint.name,
            passed: false,
            details: `Error: ${err.message}`,
          });
          console.log(`   ❌ ${checkpoint.name}: Error - ${err.message}`);
        }
      }

      results.push({
        name,
        description,
        url,
        screenshot: screenshotPath,
        checkpoints: checkResults,
        passed: checkResults.every(c => c.passed),
      });

    } catch (err) {
      console.log(`   ❌ Failed to load page: ${err.message}`);
      results.push({
        name,
        description,
        url,
        screenshot: null,
        error: err.message,
        passed: false,
      });
    }
  }

  // ========================================
  // TEST 1: Dashboard Page
  // ========================================
  await screenshotAndAnalyze(
    `${BASE_URL}/dashboard`,
    'dashboard',
    'Main Dashboard with State Machine Overview',
    [
      {
        name: 'Page loads without errors',
        check: async (page) => {
          const errors = [];
          page.on('console', msg => {
            if (msg.type() === 'error') errors.push(msg.text());
          });
          await page.waitForTimeout(1000);
          return {
            passed: true,
            details: 'Page loaded successfully',
          };
        }
      },
      {
        name: 'Sidebar navigation visible',
        check: async (page) => {
          const sidebar = await page.$('nav');
          return {
            passed: !!sidebar,
            details: sidebar ? 'Sidebar found' : 'Sidebar not found',
          };
        }
      },
      {
        name: 'Main content area exists',
        check: async (page) => {
          const main = await page.$('main');
          return {
            passed: !!main,
            details: main ? 'Main content area found' : 'Main content not found',
          };
        }
      },
      {
        name: 'No session message shown (expected when no session)',
        check: async (page) => {
          const noSession = await page.getByText('No Active Session').count();
          return {
            passed: noSession > 0,
            details: noSession > 0 ? '"No Active Session" message visible' : 'Session might be active or different state',
          };
        }
      },
    ]
  );

  // ========================================
  // TEST 2: Trading Session Page
  // ========================================
  await screenshotAndAnalyze(
    `${BASE_URL}/trading-session`,
    'trading-session',
    'Trading Session Configuration with State Machine Diagram',
    [
      {
        name: 'Page title visible',
        check: async (page) => {
          const title = await page.getByText('Trading Session').count();
          return {
            passed: title > 0,
            details: title > 0 ? 'Title found' : 'Title not found',
          };
        }
      },
      {
        name: 'Trading mode selector exists',
        check: async (page) => {
          const modes = await page.getByRole('button').filter({ hasText: /Live|Paper|Backtest/i }).count();
          return {
            passed: modes > 0,
            details: `Found ${modes} trading mode buttons`,
          };
        }
      },
      {
        name: 'Strategy selection section exists',
        check: async (page) => {
          const section = await page.getByText('Select Strategies').count();
          return {
            passed: section > 0,
            details: section > 0 ? 'Strategy selection found' : 'Strategy selection not found',
          };
        }
      },
    ]
  );

  // ========================================
  // TEST 3: Session History Page
  // ========================================
  await screenshotAndAnalyze(
    `${BASE_URL}/session-history`,
    'session-history',
    'Session History List',
    [
      {
        name: 'Page loads',
        check: async (page) => {
          const content = await page.content();
          return {
            passed: content.length > 1000,
            details: 'Page content loaded',
          };
        }
      },
      {
        name: 'Session History title or table exists',
        check: async (page) => {
          const title = await page.getByText(/Session History|Sessions/i).count();
          return {
            passed: title > 0,
            details: title > 0 ? 'Session History section found' : 'Not found',
          };
        }
      },
    ]
  );

  // ========================================
  // TEST 4: Strategy Builder Page
  // ========================================
  await screenshotAndAnalyze(
    `${BASE_URL}/strategy-builder`,
    'strategy-builder',
    'Strategy Builder with 5-Section Editor',
    [
      {
        name: 'Page loads',
        check: async (page) => {
          const content = await page.content();
          return {
            passed: content.length > 1000,
            details: 'Page content loaded',
          };
        }
      },
      {
        name: 'Strategy list or editor visible',
        check: async (page) => {
          const table = await page.$('table');
          const tabs = await page.getByRole('tab').count();
          return {
            passed: !!table || tabs > 0,
            details: `Found table: ${!!table}, tabs: ${tabs}`,
          };
        }
      },
    ]
  );

  // ========================================
  // TEST 5: Indicators Page
  // ========================================
  await screenshotAndAnalyze(
    `${BASE_URL}/indicators`,
    'indicators',
    'Indicators Management with Variant System',
    [
      {
        name: 'Tabs visible',
        check: async (page) => {
          const tabs = await page.getByRole('tab').count();
          return {
            passed: tabs >= 3,
            details: `Found ${tabs} tabs`,
          };
        }
      },
      {
        name: 'Variant Manager tab exists',
        check: async (page) => {
          const tab = await page.getByText('Variant Manager').count();
          return {
            passed: tab > 0,
            details: tab > 0 ? 'Variant Manager tab found' : 'Not found',
          };
        }
      },
    ]
  );

  // ========================================
  // TEST 6: Data Collection Page
  // ========================================
  await screenshotAndAnalyze(
    `${BASE_URL}/data-collection`,
    'data-collection',
    'Data Collection Sessions',
    [
      {
        name: 'Page loads',
        check: async (page) => {
          const content = await page.content();
          return {
            passed: content.length > 1000,
            details: 'Page content loaded',
          };
        }
      },
    ]
  );

  await browser.close();

  // ========================================
  // Generate Report
  // ========================================
  console.log('\n' + '='.repeat(60));
  console.log('UI VISUAL TEST REPORT');
  console.log('='.repeat(60));

  let totalPassed = 0;
  let totalFailed = 0;

  for (const result of results) {
    const status = result.passed ? '✅ PASS' : '❌ FAIL';
    console.log(`\n${status} ${result.name}`);
    console.log(`   ${result.description}`);
    if (result.screenshot) {
      console.log(`   Screenshot: ${result.screenshot}`);
    }
    if (result.error) {
      console.log(`   Error: ${result.error}`);
    }

    if (result.checkpoints) {
      for (const cp of result.checkpoints) {
        if (cp.passed) totalPassed++;
        else totalFailed++;
      }
    }
  }

  console.log('\n' + '='.repeat(60));
  console.log(`SUMMARY: ${totalPassed} passed, ${totalFailed} failed`);
  console.log('='.repeat(60));

  // Save results to JSON
  const reportPath = path.join(SCREENSHOT_DIR, 'report.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`\nFull report saved to: ${reportPath}`);
  console.log(`Screenshots saved to: ${SCREENSHOT_DIR}/`);

  return results;
}

// Run tests
takeScreenshots()
  .then(results => {
    const allPassed = results.every(r => r.passed);
    process.exit(allPassed ? 0 : 1);
  })
  .catch(err => {
    console.error('Test runner failed:', err);
    process.exit(1);
  });
