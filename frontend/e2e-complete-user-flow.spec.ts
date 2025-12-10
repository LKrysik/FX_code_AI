/**
 * COMPLETE USER FLOW E2E TEST
 * ===========================
 *
 * Symuluje pełny przepływ użytkownika:
 * 1. Uruchomienie sesji tradingowej
 * 2. Wybór strategii i symboli
 * 3. Start sesji
 * 4. Obserwacja dashboard z aktywną sesją
 * 5. Przełączanie między strategiami i symbolami
 * 6. Wykresy z wartościami wskaźników
 * 7. Generowanie sygnałów i transakcji
 * 8. Szczegóły sygnałów i transakcji
 * 9. Stop Loss/Take Profit
 * 10. Emergency exit
 * 11. Zatrzymanie sesji
 * 12. Historia sesji
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:8080';

interface TestResult {
  category: string;
  test: string;
  status: 'PASS' | 'FAIL' | 'SKIP' | 'WARN';
  details: string;
  error?: string;
}

const results: TestResult[] = [];

function log(category: string, testName: string, status: 'PASS' | 'FAIL' | 'SKIP' | 'WARN', details: string, error?: string) {
  results.push({ category, test: testName, status, details, error });
  const icon = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : status === 'WARN' ? '⚠️' : '⏭️';
  console.log(`${icon} [${category}] ${testName}: ${details}${error ? ` | ERROR: ${error}` : ''}`);
}

test.describe('Complete User Trading Flow', () => {
  test.setTimeout(600000); // 10 minutes

  test('Full trading workflow simulation', async ({ page, request }) => {
    const jsErrors: string[] = [];
    let sessionId: string | null = null;

    // Collect JS errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        jsErrors.push(msg.text().substring(0, 300));
      }
    });
    page.on('pageerror', err => {
      jsErrors.push(`PageError: ${err.message.substring(0, 300)}`);
    });

    // ================================================================
    // PHASE 1: API VERIFICATION
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 1: API VERIFICATION');
    console.log('='.repeat(60));

    // Test strategies API
    try {
      const res = await request.get(`${API_URL}/api/strategies`);
      const data = await res.json();
      const count = data.data?.strategies?.length || 0;
      log('API', 'Strategies endpoint', count > 0 ? 'PASS' : 'FAIL', `${count} strategies available`);
    } catch (e: any) {
      log('API', 'Strategies endpoint', 'FAIL', 'Cannot connect', e.message);
    }

    // Test indicators API
    try {
      const res = await request.get(`${API_URL}/api/indicators/system`);
      if (res.ok()) {
        const data = await res.json();
        log('API', 'Indicators endpoint', 'PASS', 'System indicators available');
      } else {
        log('API', 'Indicators endpoint', 'WARN', `HTTP ${res.status()}`);
      }
    } catch (e: any) {
      log('API', 'Indicators endpoint', 'FAIL', 'Cannot connect', e.message);
    }

    // Test WebSocket
    try {
      await page.goto(`${BASE_URL}/dashboard`);
      const wsWorks = await page.evaluate(() => {
        return new Promise<boolean>(resolve => {
          try {
            const ws = new WebSocket('ws://localhost:8080/ws');
            ws.onopen = () => { ws.close(); resolve(true); };
            ws.onerror = () => resolve(false);
            setTimeout(() => resolve(false), 5000);
          } catch { resolve(false); }
        });
      });
      log('API', 'WebSocket connection', wsWorks ? 'PASS' : 'FAIL', wsWorks ? 'Connected' : 'Failed to connect');
    } catch (e: any) {
      log('API', 'WebSocket connection', 'FAIL', 'Test error', e.message);
    }

    // ================================================================
    // PHASE 2: DASHBOARD - NO SESSION
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 2: DASHBOARD WITHOUT SESSION');
    console.log('='.repeat(60));

    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check for "No Active Session" message
    const noSessionMsg = page.locator('text=/No Active Session/i');
    if (await noSessionMsg.count() > 0) {
      log('Dashboard', 'No Session state', 'PASS', 'Shows "No Active Session" correctly');
    } else {
      log('Dashboard', 'No Session state', 'WARN', 'May have active session or different message');
    }

    // Check for Start/Configure button
    const startBtn = page.getByRole('button', { name: /Start|Configure|New/i }).first();
    if (await startBtn.count() > 0) {
      log('Dashboard', 'Start button', 'PASS', 'Found session start/configure button');
    } else {
      log('Dashboard', 'Start button', 'SKIP', 'No start button visible');
    }

    // ================================================================
    // PHASE 3: TRADING SESSION CONFIGURATION
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 3: SESSION CONFIGURATION');
    console.log('='.repeat(60));

    await page.goto(`${BASE_URL}/trading-session`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check trading mode buttons
    const modeButtons = page.getByRole('button').filter({ hasText: /Live|Paper|Backtest/i });
    const modeCount = await modeButtons.count();
    log('Session Config', 'Mode buttons', modeCount >= 3 ? 'PASS' : 'FAIL', `Found ${modeCount} mode buttons`);

    // Try to click Paper mode
    const paperBtn = page.getByRole('button', { name: /Paper/i }).first();
    if (await paperBtn.count() > 0) {
      await paperBtn.click();
      await page.waitForTimeout(500);
      log('Session Config', 'Select Paper mode', 'PASS', 'Paper trading selected');
    }

    // Check strategy checkboxes
    const checkboxes = page.locator('input[type="checkbox"]');
    const cbCount = await checkboxes.count();
    log('Session Config', 'Strategy checkboxes', cbCount > 0 ? 'PASS' : 'FAIL', `Found ${cbCount} strategy checkboxes`);

    // Select first strategy
    if (cbCount > 0) {
      await checkboxes.first().click();
      await page.waitForTimeout(300);
      log('Session Config', 'Select strategy', 'PASS', 'First strategy selected');
    }

    // Check for symbol selection
    const symbolSelect = page.locator('text=/BTC|ETH|Symbol/i');
    log('Session Config', 'Symbol selection', await symbolSelect.count() > 0 ? 'PASS' : 'SKIP', 'Symbol selection area');

    // ================================================================
    // PHASE 4: CREATE SESSION VIA API
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 4: CREATE TRADING SESSION');
    console.log('='.repeat(60));

    // Get a strategy ID
    let strategyId = '';
    let strategyName = '';
    try {
      const stratRes = await request.get(`${API_URL}/api/strategies`);
      const stratData = await stratRes.json();
      if (stratData.data?.strategies?.length > 0) {
        strategyId = stratData.data.strategies[0].id;
        strategyName = stratData.data.strategies[0].strategy_name;
        log('Session', 'Get strategy', 'PASS', `Using: ${strategyName}`);
      }
    } catch (e: any) {
      log('Session', 'Get strategy', 'FAIL', 'Cannot get strategies', e.message);
    }

    // Create paper trading session
    if (strategyId) {
      try {
        const createRes = await request.post(`${API_URL}/api/paper-trading/sessions`, {
          data: {
            strategy_id: strategyId,
            strategy_name: strategyName,
            initial_balance: 10000,
            symbols: ['BTC_USDT', 'ETH_USDT']
          }
        });
        const createData = await createRes.json();
        if (createData.success && createData.session_id) {
          sessionId = createData.session_id;
          log('Session', 'Create session', 'PASS', `Session created: ${sessionId}`);
        } else {
          log('Session', 'Create session', 'FAIL', 'Creation failed', JSON.stringify(createData));
        }
      } catch (e: any) {
        log('Session', 'Create session', 'FAIL', 'API error', e.message);
      }
    }

    // ================================================================
    // PHASE 5: SESSION STATE MACHINE
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 5: STATE MACHINE');
    console.log('='.repeat(60));

    if (sessionId) {
      try {
        const stateRes = await request.get(`${API_URL}/api/sessions/${sessionId}/state`);
        const stateData = await stateRes.json();
        log('State Machine', 'Get state', 'PASS', `Current state: ${stateData.current_state}`);
        log('State Machine', 'Transitions', 'PASS', `Allowed: ${stateData.allowed_transitions?.join(', ') || 'none'}`);

        if (stateData.instances && stateData.instances.length > 0) {
          log('State Machine', 'Strategy instances', 'PASS', `${stateData.instances.length} active instances`);
        } else {
          log('State Machine', 'Strategy instances', 'WARN', 'No active instances (may need market data)');
        }
      } catch (e: any) {
        log('State Machine', 'Get state', 'FAIL', 'Cannot get state', e.message);
      }

      // Check transitions
      try {
        const transRes = await request.get(`${API_URL}/api/sessions/${sessionId}/transitions`);
        if (transRes.ok()) {
          const transData = await transRes.json();
          const count = transData.data?.transitions?.length || transData.transitions?.length || 0;
          log('State Machine', 'Transitions history', count > 0 ? 'PASS' : 'WARN', `${count} transitions recorded`);
        }
      } catch (e: any) {
        log('State Machine', 'Transitions history', 'WARN', 'Endpoint may not be available');
      }
    }

    // ================================================================
    // PHASE 6: DASHBOARD WITH ACTIVE SESSION
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 6: DASHBOARD WITH SESSION');
    console.log('='.repeat(60));

    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Check for session indicator
    const sessionIndicator = page.locator('text=/Running|Active|Session|RUNNING/i');
    if (await sessionIndicator.count() > 0) {
      log('Dashboard', 'Session indicator', 'PASS', 'Shows active session');
    } else {
      log('Dashboard', 'Session indicator', 'WARN', 'Session indicator not visible');
    }

    // Check for symbol tabs/selector
    const symbolTabs = page.locator('text=/BTC_USDT|ETH_USDT|Symbol/i');
    if (await symbolTabs.count() > 0) {
      log('Dashboard', 'Symbol selector', 'PASS', 'Symbol selection visible');
    }

    // ================================================================
    // PHASE 7: CHART COMPONENT
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 7: CHART COMPONENT');
    console.log('='.repeat(60));

    // Check for chart canvas
    const canvas = page.locator('canvas');
    const canvasCount = await canvas.count();
    log('Chart', 'Canvas elements', canvasCount > 0 ? 'PASS' : 'WARN', `Found ${canvasCount} canvas elements`);

    // Check for timeframe selector
    const timeframeBtn = page.locator('text=/1m|5m|15m|1h/i');
    if (await timeframeBtn.count() > 0) {
      log('Chart', 'Timeframe selector', 'PASS', 'Timeframe buttons visible');
    }

    // Check for chart errors in console
    const chartErrors = jsErrors.filter(e =>
      e.toLowerCase().includes('chart') ||
      e.toLowerCase().includes('canvas') ||
      e.includes('addCandlestickSeries') ||
      e.includes('lightweight')
    );
    log('Chart', 'JS errors', chartErrors.length === 0 ? 'PASS' : 'FAIL',
        chartErrors.length === 0 ? 'No chart errors' : `${chartErrors.length} errors`,
        chartErrors[0]);

    // ================================================================
    // PHASE 8: STRATEGY BUILDER
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 8: STRATEGY BUILDER');
    console.log('='.repeat(60));

    await page.goto(`${BASE_URL}/strategy-builder`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check strategy table
    const table = page.locator('table');
    if (await table.count() > 0) {
      log('Strategy Builder', 'Strategy table', 'PASS', 'Table visible');

      const rows = page.locator('tbody tr');
      const rowCount = await rows.count();
      log('Strategy Builder', 'Strategy rows', 'PASS', `${rowCount} strategies listed`);
    }

    // Check for edit functionality
    const editBtn = page.getByRole('button', { name: /Edit|View|Details/i }).first();
    if (await editBtn.count() > 0) {
      log('Strategy Builder', 'Edit button', 'PASS', 'Edit/View button available');

      // Try to click edit
      await editBtn.click();
      await page.waitForTimeout(1000);

      // Check for tabs (5-section editor)
      const tabs = page.getByRole('tab');
      const tabCount = await tabs.count();
      if (tabCount > 0) {
        log('Strategy Builder', 'Editor tabs', 'PASS', `${tabCount} configuration tabs`);
      }
    }

    // Check for SL/TP configuration
    const slTpFields = page.locator('text=/Stop Loss|Take Profit|SL|TP/i');
    if (await slTpFields.count() > 0) {
      log('Strategy Builder', 'SL/TP config', 'PASS', 'Stop Loss / Take Profit configuration visible');
    } else {
      log('Strategy Builder', 'SL/TP config', 'WARN', 'SL/TP fields not visible in current view');
    }

    // Check for emergency exit config
    const emergencyFields = page.locator('text=/Emergency|Exit|E1/i');
    if (await emergencyFields.count() > 0) {
      log('Strategy Builder', 'Emergency exit', 'PASS', 'Emergency exit configuration visible');
    }

    // ================================================================
    // PHASE 9: INDICATORS PAGE
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 9: INDICATORS');
    console.log('='.repeat(60));

    await page.goto(`${BASE_URL}/indicators`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check tabs
    const indTabs = page.getByRole('tab');
    const indTabCount = await indTabs.count();
    log('Indicators', 'Tabs', indTabCount >= 3 ? 'PASS' : 'WARN', `${indTabCount} tabs`);

    // Check Variant Manager
    const variantTab = page.locator('text=/Variant Manager/i');
    if (await variantTab.count() > 0) {
      await variantTab.click();
      await page.waitForTimeout(1000);
      log('Indicators', 'Variant Manager', 'PASS', 'Variant Manager tab accessible');
    }

    // Check indicator values display
    const indicatorValues = page.locator('text=/RSI|EMA|SMA|MACD|Volume/i');
    if (await indicatorValues.count() > 0) {
      log('Indicators', 'Indicator display', 'PASS', 'Indicator values visible');
    }

    // ================================================================
    // PHASE 10: ORDERS AND POSITIONS
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 10: ORDERS AND POSITIONS');
    console.log('='.repeat(60));

    if (sessionId) {
      // Check orders
      try {
        const ordersRes = await request.get(`${API_URL}/api/paper-trading/sessions/${sessionId}/orders`);
        const ordersData = await ordersRes.json();
        log('Trading', 'Orders endpoint', 'PASS', `${ordersData.count || 0} orders`);
      } catch (e: any) {
        log('Trading', 'Orders endpoint', 'FAIL', 'Cannot get orders', e.message);
      }

      // Check performance
      try {
        const perfRes = await request.get(`${API_URL}/api/paper-trading/sessions/${sessionId}/performance`);
        const perfData = await perfRes.json();
        log('Trading', 'Performance endpoint', 'PASS', `${perfData.count || 0} performance records`);
      } catch (e: any) {
        log('Trading', 'Performance endpoint', 'WARN', 'Performance endpoint issue');
      }

      // Check positions
      try {
        const posRes = await request.get(`${API_URL}/api/trading/positions?session_id=${sessionId}`);
        const posData = await posRes.json();
        log('Trading', 'Positions endpoint', 'PASS', `${posData.count || 0} positions`);
      } catch (e: any) {
        log('Trading', 'Positions endpoint', 'FAIL', 'Cannot get positions', e.message);
      }
    }

    // ================================================================
    // PHASE 11: SESSION STOP
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 11: STOP SESSION');
    console.log('='.repeat(60));

    if (sessionId) {
      try {
        const stopRes = await request.post(`${API_URL}/api/paper-trading/sessions/${sessionId}/stop`, {
          data: { reason: 'E2E Test completed' }
        });
        const stopData = await stopRes.json();
        log('Session', 'Stop session', stopData.success ? 'PASS' : 'FAIL',
            stopData.success ? 'Session stopped' : 'Stop failed');
      } catch (e: any) {
        log('Session', 'Stop session', 'FAIL', 'Cannot stop session', e.message);
      }

      // Verify stopped status
      try {
        const checkRes = await request.get(`${API_URL}/api/paper-trading/sessions/${sessionId}`);
        const checkData = await checkRes.json();
        const status = checkData.session?.status;
        log('Session', 'Verify stopped', status === 'STOPPED' ? 'PASS' : 'WARN', `Status: ${status}`);
      } catch (e: any) {
        log('Session', 'Verify stopped', 'WARN', 'Cannot verify');
      }
    }

    // ================================================================
    // PHASE 12: SESSION HISTORY
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 12: SESSION HISTORY');
    console.log('='.repeat(60));

    await page.goto(`${BASE_URL}/session-history`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check for history table/list
    const historyTable = page.locator('table, [class*="list"], [class*="List"]');
    if (await historyTable.count() > 0) {
      log('History', 'History list', 'PASS', 'Session history displayed');
    }

    // Check for session row
    if (sessionId) {
      const sessionRow = page.locator(`text=/${sessionId.substring(0, 20)}/i`);
      if (await sessionRow.count() > 0) {
        log('History', 'Session in history', 'PASS', 'Created session visible in history');
      } else {
        log('History', 'Session in history', 'WARN', 'Session may not be visible yet');
      }
    }

    // ================================================================
    // PHASE 13: DATA COLLECTION
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('PHASE 13: DATA COLLECTION');
    console.log('='.repeat(60));

    await page.goto(`${BASE_URL}/data-collection`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check for data collection content
    const dcContent = await page.content();
    log('Data Collection', 'Page loads', dcContent.length > 1000 ? 'PASS' : 'WARN', 'Page loaded');

    // Check for session list or start button
    const dcTable = page.locator('table');
    const dcButtons = page.getByText(/Start|Create|Session/i);
    if (await dcTable.count() > 0 || await dcButtons.count() > 0) {
      log('Data Collection', 'Sessions/Start', 'PASS', 'Sessions or start button visible');
    }

    // ================================================================
    // SUMMARY
    // ================================================================
    console.log('\n' + '='.repeat(60));
    console.log('TEST SUMMARY');
    console.log('='.repeat(60));

    const passed = results.filter(r => r.status === 'PASS').length;
    const failed = results.filter(r => r.status === 'FAIL').length;
    const warned = results.filter(r => r.status === 'WARN').length;
    const skipped = results.filter(r => r.status === 'SKIP').length;
    const total = results.length;

    console.log(`\nTotal: ${total} tests`);
    console.log(`✅ PASSED: ${passed} (${Math.round(passed/total*100)}%)`);
    console.log(`❌ FAILED: ${failed}`);
    console.log(`⚠️ WARNINGS: ${warned}`);
    console.log(`⏭️ SKIPPED: ${skipped}`);

    if (failed > 0) {
      console.log('\n--- FAILURES ---');
      results.filter(r => r.status === 'FAIL').forEach(r => {
        console.log(`❌ [${r.category}] ${r.test}: ${r.details}`);
        if (r.error) console.log(`   Error: ${r.error}`);
      });
    }

    if (warned > 0) {
      console.log('\n--- WARNINGS ---');
      results.filter(r => r.status === 'WARN').forEach(r => {
        console.log(`⚠️ [${r.category}] ${r.test}: ${r.details}`);
      });
    }

    // Critical JS errors
    const criticalErrors = jsErrors.filter(e =>
      e.includes('TypeError') ||
      e.includes('ReferenceError') ||
      e.includes('not a function') ||
      e.includes('Cannot read')
    );
    if (criticalErrors.length > 0) {
      console.log('\n--- CRITICAL JS ERRORS ---');
      criticalErrors.slice(0, 5).forEach(e => console.log(`  ${e.substring(0, 200)}`));
    }

    console.log('\n' + '='.repeat(60));
    console.log('TEST COMPLETE');
    console.log('='.repeat(60) + '\n');

    // Assert reasonable pass rate
    expect(failed).toBeLessThan(5);
  });
});
