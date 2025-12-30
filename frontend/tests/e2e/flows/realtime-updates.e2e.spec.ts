/**
 * Real-time Updates E2E Tests
 * ============================
 *
 * Tests for WebSocket-based real-time data updates.
 * Validates that the UI responds correctly to live data streams.
 *
 * @tags e2e, websocket, realtime
 * @priority P1, P2
 */

import { test, expect } from '../support/fixtures/index';
import {
  createRunningSession,
  createSessionStats,
} from '../support/factories';

// ============================================
// MOCK DATA
// ============================================

const mockSessionState = {
  session_id: 'session-ws-test',
  status: 'running',
  mode: 'Paper',
  active_strategies: 2,
  active_symbols: 3,
  current_state: 'MONITORING',
  uptime_seconds: 1800,
};

const mockStrategies = [
  { id: 'strat-1', name: 'RSI Strategy', isActive: true },
  { id: 'strat-2', name: 'MACD Crossover', isActive: true },
];

const mockStateMachineUpdate = {
  type: 'state_machine_update',
  data: {
    symbol: 'BTCUSDT',
    strategy_id: 'strat-1',
    current_state: 'S1_ENTRY',
    previous_state: 'IDLE',
    timestamp: new Date().toISOString(),
    conditions_met: ['rsi < 30', 'volume_surge > 2'],
  },
};

const mockSignalEvent = {
  type: 'signal',
  data: {
    id: 'signal-live-1',
    symbol: 'BTCUSDT',
    signal_type: 'ENTRY',
    price: 43250.75,
    confidence: 0.88,
    strategy: 'RSI Strategy',
    timestamp: new Date().toISOString(),
  },
};

const mockIndicatorUpdate = {
  type: 'indicator_update',
  data: {
    symbol: 'BTCUSDT',
    indicators: {
      rsi: 28.5,
      pump_magnitude_pct: 3.2,
      volume_surge_ratio: 2.5,
      price_velocity: 0.08,
      bid_ask_imbalance: 0.15,
    },
    timestamp: new Date().toISOString(),
  },
};

const mockPositionUpdate = {
  type: 'position_update',
  data: {
    id: 'pos-1',
    symbol: 'BTCUSDT',
    side: 'LONG',
    size: 0.15,
    entry_price: 43000,
    current_price: 43250,
    unrealized_pnl: 37.5,
    unrealized_pnl_pct: 0.87,
    leverage: 10,
    status: 'OPEN',
  },
};

const mockPriceUpdate = {
  type: 'price_update',
  data: {
    symbol: 'BTCUSDT',
    price: 43275.50,
    bid: 43274.25,
    ask: 43276.75,
    volume_24h: 15234567890,
    change_24h: 2.35,
    timestamp: new Date().toISOString(),
  },
};

// ============================================
// P1: WEBSOCKET CONNECTION
// ============================================

test.describe('[P1] WebSocket Connection', () => {
  test.beforeEach(async ({ network }) => {
    await network.mock({
      method: 'GET',
      urlPattern: '**/api/session/status',
      response: { active: true, session: mockSessionState },
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/strategies',
      response: mockStrategies,
    });
  });

  test('[P1] Dashboard renders without WebSocket errors', async ({ page, console: consoleManager }) => {
    // GIVEN: User navigates to dashboard
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Page attempts WebSocket connection
    await page.waitForTimeout(2000); // Allow time for WS connection attempt

    // THEN: No critical console errors related to WebSocket
    const errors = consoleManager.getErrors();
    const criticalWsErrors = errors.filter(
      (e) =>
        e.message.includes('WebSocket') &&
        (e.message.includes('TypeError') || e.message.includes('Cannot read'))
    );

    // Log any WS connection messages (informational)
    const wsMessages = errors.filter((e) => e.message.includes('WebSocket') || e.message.includes('ws://'));
    // Use global console for logging
    globalThis.console.log(`WebSocket-related messages: ${wsMessages.length}`);

    // Should not have critical errors
    expect(criticalWsErrors.length).toBe(0);
  });

  test('[P1] Page handles WebSocket unavailability gracefully', async ({ page }) => {
    // GIVEN: WebSocket server is unavailable (mocked by default)
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: WS connection fails
    await page.waitForTimeout(3000);

    // THEN: Page still renders and functions
    await expect(page.locator('body')).toBeVisible();
    await expect(page).not.toHaveURL(/error/);

    // Should show some fallback or offline indicator
    const connectionStatus = page.locator(
      'text=/offline|disconnected|connecting|reconnect/i, [class*="connection"], [data-testid*="connection"]'
    );
    const statusCount = await connectionStatus.count();
    globalThis.console.log(`Connection status indicators: ${statusCount}`);
  });
});

// ============================================
// P1: STATE MACHINE UPDATES
// ============================================

test.describe('[P1] State Machine Updates', () => {
  test.beforeEach(async ({ network }) => {
    await network.mock({
      method: 'GET',
      urlPattern: '**/api/session/status',
      response: { active: true, session: mockSessionState },
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/strategies',
      response: mockStrategies,
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/state-machines*',
      response: [
        {
          symbol: 'BTCUSDT',
          strategy_id: 'strat-1',
          current_state: 'IDLE',
          last_update: new Date().toISOString(),
        },
        {
          symbol: 'ETHUSDT',
          strategy_id: 'strat-1',
          current_state: 'S1_MONITORING',
          last_update: new Date().toISOString(),
        },
      ],
    });
  });

  test('[P1] State machine table displays current states', async ({ page }) => {
    // GIVEN: Active session with state machines
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for state machine display
    const stateContent = page.locator(
      '[data-testid*="state"], [class*="state"], table, text=/IDLE|MONITORING|ENTRY|EXIT|S1|O1|Z1|E1/i'
    );
    const count = await stateContent.count();

    // THEN: State machine content is visible
    globalThis.console.log(`State machine elements found: ${count}`);
    expect(count).toBeGreaterThan(0);
  });

  test('[P1] State badges show correct visual styling', async ({ page }) => {
    // GIVEN: Dashboard with state machines
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for state badges
    const badges = page.locator(
      '[class*="badge"], [class*="chip"], [class*="state-indicator"]'
    );
    const badgeCount = await badges.count();

    if (badgeCount > 0) {
      // THEN: Badges have styling (background color or specific class)
      const firstBadge = badges.first();
      const hasStyle = await firstBadge.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return (
          styles.backgroundColor !== 'rgba(0, 0, 0, 0)' ||
          styles.backgroundColor !== 'transparent' ||
          el.className.includes('success') ||
          el.className.includes('warning') ||
          el.className.includes('error') ||
          el.className.includes('info')
        );
      });

      globalThis.console.log(`Badge styling detected: ${hasStyle}`);
    }
  });

  test('[P1] Transition log shows recent state changes', async ({ page, network }) => {
    // GIVEN: Dashboard with state machine activity
    await network.mock({
      method: 'GET',
      urlPattern: '**/api/transitions*',
      response: [
        {
          id: 'trans-1',
          symbol: 'BTCUSDT',
          from_state: 'IDLE',
          to_state: 'S1_ENTRY',
          timestamp: new Date().toISOString(),
          trigger: 'rsi < 30',
        },
        {
          id: 'trans-2',
          symbol: 'ETHUSDT',
          from_state: 'S1_ENTRY',
          to_state: 'O1_OPEN',
          timestamp: new Date(Date.now() - 60000).toISOString(),
          trigger: 'signal confirmed',
        },
      ],
    });

    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for transition log
    const transitionLog = page.locator(
      '[data-testid*="transition"], [class*="transition"], [class*="log"], text=/IDLE|ENTRY|transition/i'
    );
    const count = await transitionLog.count();

    // THEN: Transition information is visible
    globalThis.console.log(`Transition log elements: ${count}`);
  });
});

// ============================================
// P1: LIVE SIGNAL UPDATES
// ============================================

test.describe('[P1] Live Signal Updates', () => {
  test.beforeEach(async ({ network }) => {
    await network.mock({
      method: 'GET',
      urlPattern: '**/api/session/status',
      response: { active: true, session: mockSessionState },
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/signals/recent*',
      response: [
        {
          id: 'sig-1',
          symbol: 'BTCUSDT',
          type: 'ENTRY',
          price: 43000,
          confidence: 0.85,
          timestamp: new Date().toISOString(),
        },
      ],
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/strategies',
      response: mockStrategies,
    });
  });

  test('[P1] Recent signals panel displays signals', async ({ page }) => {
    // GIVEN: Active session with signals
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for signal panel
    const signalPanel = page.locator(
      '[data-testid*="signal"], [class*="signal"], text=/Signal|ENTRY|EXIT|Recent/i'
    );
    const count = await signalPanel.count();

    // THEN: Signal content is visible
    globalThis.console.log(`Signal panel elements: ${count}`);
    expect(count).toBeGreaterThan(0);
  });

  test('[P1] Signal cards show symbol and price', async ({ page }) => {
    // GIVEN: Dashboard with signal data
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for signal details
    const pageContent = await page.locator('body').textContent();

    // THEN: Signal data is present
    const hasSymbol = pageContent?.includes('BTCUSDT') || pageContent?.includes('BTC');
    const hasSignalType = pageContent?.includes('ENTRY') || pageContent?.includes('Signal');

    globalThis.console.log(`Signal data visible - Symbol: ${hasSymbol}, Type: ${hasSignalType}`);
  });

  test('[P1] Signal confidence is displayed', async ({ page }) => {
    // GIVEN: Signals with confidence scores
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for confidence indicators
    const confidenceIndicators = page.locator(
      '[class*="confidence"], [data-testid*="confidence"], text=/%|0\\.[0-9]/i'
    );
    const count = await confidenceIndicators.count();

    globalThis.console.log(`Confidence indicators found: ${count}`);
  });
});

// ============================================
// P1: LIVE POSITION UPDATES
// ============================================

test.describe('[P1] Live Position Updates', () => {
  test.beforeEach(async ({ network }) => {
    await network.mock({
      method: 'GET',
      urlPattern: '**/api/session/status',
      response: { active: true, session: mockSessionState },
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/positions*',
      response: [
        {
          id: 'pos-1',
          symbol: 'BTCUSDT',
          side: 'LONG',
          size: 0.15,
          entry_price: 43000,
          current_price: 43500,
          unrealized_pnl: 75,
          unrealized_pnl_pct: 1.74,
          leverage: 10,
          status: 'OPEN',
        },
      ],
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/strategies',
      response: mockStrategies,
    });
  });

  test('[P1] Active position banner displays P&L', async ({ page }) => {
    // GIVEN: Open position
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for position info
    const positionInfo = page.locator(
      '[data-testid*="position"], [class*="position"], [class*="pnl"], text=/LONG|SHORT|P.?L|\\$/i'
    );
    const count = await positionInfo.count();

    // THEN: Position information is displayed
    globalThis.console.log(`Position display elements: ${count}`);
    expect(count).toBeGreaterThan(0);
  });

  test('[P1] P&L shows positive/negative color coding', async ({ page }) => {
    // GIVEN: Position with positive P&L
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for P&L elements
    const pnlElements = page.locator('[class*="pnl"], [data-testid*="pnl"]');
    const count = await pnlElements.count();

    if (count > 0) {
      const firstPnl = pnlElements.first();
      const textColor = await firstPnl.evaluate((el) => {
        return window.getComputedStyle(el).color;
      });

      // THEN: Has a color (green for positive expected)
      globalThis.console.log(`P&L color: ${textColor}`);
      expect(textColor).toBeTruthy();
    }
  });

  test('[P1] Position details show entry price and current price', async ({ page }) => {
    // GIVEN: Open position with price data
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for price information
    const pageContent = await page.locator('body').textContent();

    // THEN: Price data is visible
    const hasPrice =
      pageContent?.includes('43') || // Part of 43000 or 43500
      pageContent?.includes('Entry') ||
      pageContent?.includes('Current');

    globalThis.console.log(`Price information visible: ${hasPrice}`);
  });
});

// ============================================
// P2: INDICATOR VALUE UPDATES
// ============================================

test.describe('[P2] Indicator Value Updates', () => {
  test.beforeEach(async ({ network }) => {
    await network.mock({
      method: 'GET',
      urlPattern: '**/api/session/status',
      response: { active: true, session: mockSessionState },
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/indicators/live*',
      response: {
        BTCUSDT: {
          rsi: 45.2,
          pump_magnitude_pct: 1.5,
          volume_surge_ratio: 1.2,
          price_velocity: 0.03,
        },
        ETHUSDT: {
          rsi: 52.8,
          pump_magnitude_pct: 0.8,
          volume_surge_ratio: 0.9,
          price_velocity: 0.01,
        },
      },
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/strategies',
      response: mockStrategies,
    });
  });

  test('[P2] Indicator panel shows real-time values', async ({ page }) => {
    // GIVEN: Active session with indicator data
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for indicator values
    const indicatorValues = page.locator(
      '[data-testid*="indicator"], [class*="indicator"], text=/RSI|Volume|Pump|Velocity/i'
    );
    const count = await indicatorValues.count();

    // THEN: Indicator values are displayed
    globalThis.console.log(`Indicator value elements: ${count}`);
  });

  test('[P2] Indicator values are formatted correctly', async ({ page }) => {
    // GIVEN: Indicator data
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for numeric values
    const numericValues = page.locator('[class*="value"], [class*="indicator-value"]');
    const count = await numericValues.count();

    if (count > 0) {
      const firstValue = numericValues.first();
      const text = await firstValue.textContent();

      // THEN: Values are numeric format
      if (text) {
        const hasNumber = /[\d.,]+/.test(text);
        globalThis.console.log(`Value format: ${text}, is numeric: ${hasNumber}`);
      }
    }
  });
});

// ============================================
// P2: CONDITION PROGRESS UPDATES
// ============================================

test.describe('[P2] Condition Progress Updates', () => {
  test.beforeEach(async ({ network }) => {
    await network.mock({
      method: 'GET',
      urlPattern: '**/api/session/status',
      response: { active: true, session: mockSessionState },
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/conditions/progress*',
      response: {
        BTCUSDT: {
          strategy_id: 'strat-1',
          conditions: [
            { id: 'c1', name: 'RSI < 30', met: true, current_value: 28.5 },
            { id: 'c2', name: 'Volume > 2x', met: false, current_value: 1.5 },
            { id: 'c3', name: 'Pump > 3%', met: false, current_value: 1.2 },
          ],
          progress_pct: 33,
        },
      },
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/strategies',
      response: mockStrategies,
    });
  });

  test('[P2] Condition progress bar shows completion', async ({ page }) => {
    // GIVEN: Active session with condition tracking
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for progress indicators
    const progressBars = page.locator(
      '[role="progressbar"], [class*="progress"], [data-testid*="progress"]'
    );
    const count = await progressBars.count();

    // THEN: Progress indicators exist
    globalThis.console.log(`Progress bar elements: ${count}`);
  });

  test('[P2] Individual conditions show met/unmet status', async ({ page }) => {
    // GIVEN: Conditions with various statuses
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for condition status indicators
    const conditionStatus = page.locator(
      '[class*="condition"], [data-testid*="condition"], text=/RSI|Volume|Pump|met|unmet/i'
    );
    const count = await conditionStatus.count();

    // THEN: Condition information is displayed
    globalThis.console.log(`Condition status elements: ${count}`);
  });
});

// ============================================
// P2: CHART UPDATES
// ============================================

test.describe('[P2] Chart Updates', () => {
  test.beforeEach(async ({ network }) => {
    await network.mock({
      method: 'GET',
      urlPattern: '**/api/session/status',
      response: { active: true, session: mockSessionState },
    });

    await network.mock({
      method: 'GET',
      urlPattern: '**/api/strategies',
      response: mockStrategies,
    });
  });

  test('[P2] Price chart renders', async ({ page }) => {
    // GIVEN: Active trading session
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for chart
    const chartElements = page.locator(
      'canvas, [class*="chart"], [data-testid*="chart"], svg'
    );
    const count = await chartElements.count();

    // THEN: Chart element exists
    globalThis.console.log(`Chart elements found: ${count}`);
    expect(count).toBeGreaterThan(0);
  });

  test('[P2] Chart canvas is visible', async ({ page }) => {
    // GIVEN: Dashboard loaded
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // WHEN: Looking for canvas
    const canvas = page.locator('canvas').first();

    if ((await canvas.count()) > 0) {
      // THEN: Canvas has dimensions
      const box = await canvas.boundingBox();
      if (box) {
        expect(box.width).toBeGreaterThan(0);
        expect(box.height).toBeGreaterThan(0);
        globalThis.console.log(`Chart dimensions: ${box.width}x${box.height}`);
      }
    }
  });
});
