# Frontend Trading Components - Developer Guide

Quick reference for using the Agent 6 trading components.

---

## 🚀 Quick Start

### 1. Import Components

```typescript
import TradingChart from '@/components/trading/TradingChart';
import OrderHistory from '@/components/trading/OrderHistory';
import SignalLog from '@/components/trading/SignalLog';
import RiskAlerts from '@/components/trading/RiskAlerts';
import PositionMonitor from '@/components/trading/PositionMonitor';
```

### 2. Use in Your Page

```tsx
export default function MyTradingPage() {
  const [sessionId, setSessionId] = useState<string>('live_session_123');

  return (
    <div className="h-screen flex">
      {/* Left: Chart */}
      <div className="w-2/3">
        <TradingChart
          session_id={sessionId}
          initialSymbol="BTC_USDT"
          className="h-full"
        />
      </div>

      {/* Right: Orders & Positions */}
      <div className="w-1/3 flex flex-col">
        <PositionMonitor
          session_id={sessionId}
          className="h-1/2"
        />
        <OrderHistory
          session_id={sessionId}
          className="h-1/2"
        />
      </div>
    </div>
  );
}
```

---

## 📦 Component Reference

### TradingChart

**Purpose:** Real-time candlestick chart with signal markers.

**Props:**
```typescript
interface TradingChartProps {
  session_id?: string;         // Optional: Filter data by session
  initialSymbol?: string;       // Default: 'BTC_USDT'
  className?: string;           // Optional: Tailwind classes
}
```

**Example:**
```tsx
<TradingChart
  session_id="live_session_123"
  initialSymbol="ETH_USDT"
  className="h-96 w-full"
/>
```

**WebSocket Messages:**
- Listens: `market_data`, `signal_generated`

**REST API Calls:**
- `GET /api/market-data/ohlcv?symbol={symbol}&timeframe={timeframe}&limit=500`

**Features:**
- Timeframe selector (1m, 5m, 15m, 1h, 4h, 1d)
- Symbol selector
- Signal markers (S1, Z1, ZE1, E1)
- Volume histogram
- Auto-scroll

---

### OrderHistory

**Purpose:** Display order execution history with filters.

**Props:**
```typescript
interface OrderHistoryProps {
  session_id?: string;          // Optional: Filter orders by session
  className?: string;           // Optional: Tailwind classes
}
```

**Example:**
```tsx
<OrderHistory
  session_id="live_session_123"
  className="h-full"
/>
```

**WebSocket Messages:**
- Listens: `order_created`, `order_filled`, `order_cancelled`

**REST API Calls:**
- `GET /api/trading/orders?session_id={id}&limit=500`

**Features:**
- Status filter (all, pending, filled, cancelled)
- Symbol filter
- Pagination (20 orders/page)
- Slippage calculation
- Export to CSV

---

### SignalLog

**Purpose:** Display trading signals with indicator values.

**Props:**
```typescript
interface SignalLogProps {
  session_id?: string;          // Optional: Filter signals by session
  className?: string;           // Optional: Tailwind classes
}
```

**Example:**
```tsx
<SignalLog
  session_id="live_session_123"
  className="h-full"
/>
```

**WebSocket Messages:**
- Listens: `signal_generated`

**REST API Calls:**
- None (real-time only, unless backend adds `/api/signals/history`)

**Features:**
- Signal type filter (S1, Z1, ZE1, E1)
- Symbol filter
- Confidence filter (min %)
- Collapsible indicator values
- Execution result display
- Auto-scroll

---

### PositionMonitor

**Purpose:** Display open positions with margin tracking.

**Props:**
```typescript
interface PositionMonitorProps {
  session_id?: string;          // Optional: Filter positions by session
  className?: string;           // Optional: Tailwind classes
}
```

**Example:**
```tsx
<PositionMonitor
  session_id="live_session_123"
  className="h-full"
/>
```

**WebSocket Messages:**
- Listens: `position_updated`

**REST API Calls:**
- `GET /api/trading/positions?session_id={id}&status=OPEN`
- `POST /api/trading/positions/{position_id}/close`

**Features:**
- Real-time P&L updates
- Margin ratio gauge (< 15% = red alert)
- Liquidation price display
- Close position button
- Total P&L summary

---

### RiskAlerts

**Purpose:** Display risk alerts with sound notifications.

**Props:**
```typescript
interface RiskAlertsProps {
  session_id?: string;          // Optional: Filter alerts by session
  maxAlerts?: number;           // Default: 50
  playSound?: boolean;          // Default: true
  className?: string;           // Optional: Tailwind classes
}
```

**Example:**
```tsx
<RiskAlerts
  session_id="live_session_123"
  maxAlerts={100}
  playSound={true}
  className="h-full"
/>
```

**WebSocket Messages:**
- Listens: `risk_alert`

**REST API Calls:**
- None (real-time only)

**Features:**
- Severity color coding (CRITICAL, WARNING, INFO)
- Sound notification for CRITICAL alerts
- Acknowledge/dismiss functionality
- Auto-scroll to new alerts
- Alert history (last N alerts)

---

## 🔌 WebSocket Integration

All components use the `useWebSocket` hook for real-time updates.

**Hook Usage:**
```typescript
import { useWebSocket, WebSocketMessage } from '@/hooks/useWebSocket';

const { lastMessage, isConnected, sendMessage } = useWebSocket({
  onMessage: (message: WebSocketMessage) => {
    if (message.type === 'market_data') {
      // Handle market data
      console.log('Price:', message.data.price);
    }
  }
});

// Check connection status
if (!isConnected) {
  return <div>Connecting to WebSocket...</div>;
}
```

**WebSocket Message Format:**
```typescript
interface WebSocketMessage {
  type: string;           // Message type (e.g., 'market_data', 'signal_generated')
  stream?: string;        // Stream name (alternative to type)
  data: any;              // Payload
  timestamp?: string;     // ISO timestamp
}
```

---

## 🌐 REST API Integration

All components use the `tradingAPI` service for REST calls.

**Service Usage:**
```typescript
import { tradingAPI } from '@/services/TradingAPI';

// Fetch positions
const positions = await tradingAPI.getPositions({
  session_id: 'live_session_123',
  status: 'OPEN'
});

// Fetch orders
const orders = await tradingAPI.getOrders({
  session_id: 'live_session_123',
  limit: 50
});

// Close position
const result = await tradingAPI.closePosition(
  'session_123:BTC_USDT',
  'USER_REQUESTED'
);
```

**Error Handling:**
```typescript
try {
  const orders = await tradingAPI.getOrders({ session_id });
} catch (err) {
  if (err instanceof TradingAPIError) {
    console.error('API Error:', err.message, err.statusCode);
  } else {
    console.error('Unknown error:', err);
  }
}
```

---

## 🎨 Styling Guide

All components use Tailwind CSS for styling.

**Color Palette:**
```css
/* Success (Green) */
text-green-600 bg-green-50 border-green-300

/* Warning (Yellow) */
text-yellow-600 bg-yellow-50 border-yellow-300

/* Error (Red) */
text-red-600 bg-red-50 border-red-300

/* Info (Blue) */
text-blue-600 bg-blue-50 border-blue-300

/* Neutral (Gray) */
text-gray-600 bg-gray-50 border-gray-300
```

**Responsive Design:**
```tsx
{/* Desktop: 3-column layout */}
<div className="hidden md:flex md:space-x-4">
  <div className="md:w-1/3">...</div>
  <div className="md:w-1/3">...</div>
  <div className="md:w-1/3">...</div>
</div>

{/* Mobile: Single column */}
<div className="md:hidden space-y-4">
  <div>...</div>
  <div>...</div>
  <div>...</div>
</div>
```

---

## 🧪 Testing Examples

### Unit Test (Jest + React Testing Library)

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import TradingChart from '@/components/trading/TradingChart';

describe('TradingChart', () => {
  it('renders chart with initial symbol', () => {
    render(<TradingChart initialSymbol="BTC_USDT" />);
    expect(screen.getByText('Trading Chart')).toBeInTheDocument();
    expect(screen.getByText('BTC_USDT')).toBeInTheDocument();
  });

  it('fetches historical data on mount', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: [] })
      } as Response)
    );

    render(<TradingChart initialSymbol="ETH_USDT" />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/market-data/ohlcv')
      );
    });
  });
});
```

### E2E Test (Playwright)

```typescript
import { test, expect } from '@playwright/test';

test('Trading page displays all components', async ({ page }) => {
  // Navigate to trading page
  await page.goto('http://localhost:3000/live-trading');

  // Check TradingChart
  await expect(page.locator('text=Trading Chart')).toBeVisible();

  // Check OrderHistory
  await expect(page.locator('text=Order History')).toBeVisible();

  // Check SignalLog
  await expect(page.locator('text=Signal Log')).toBeVisible();

  // Check PositionMonitor
  await expect(page.locator('text=Open Positions')).toBeVisible();

  // Check RiskAlerts
  await expect(page.locator('text=Risk Alerts')).toBeVisible();
});

test('Start session and verify components update', async ({ page }) => {
  await page.goto('http://localhost:3000/live-trading');

  // Start session
  await page.click('button:has-text("Start Session")');

  // Wait for session to be active
  await expect(page.locator('text=Session Active')).toBeVisible({ timeout: 5000 });

  // Verify WebSocket connection
  await expect(page.locator('text=Connected')).toBeVisible();

  // Verify chart displays data (check for canvas element)
  await expect(page.locator('canvas')).toBeVisible();
});
```

---

## 🐛 Troubleshooting

### Issue: Components not updating in real-time

**Check:**
1. WebSocket connection status: Look for "Disconnected" badge
2. Browser console for WebSocket errors
3. Backend WebSocket server is running on correct port
4. Environment variable `NEXT_PUBLIC_WS_URL` is set correctly

**Solution:**
```bash
# Check .env.local
cat frontend/.env.local

# Should contain:
# NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8080/ws

# Test WebSocket manually
wscat -c ws://127.0.0.1:8080/ws
```

---

### Issue: TradingChart not displaying

**Check:**
1. `lightweight-charts` package installed: `npm list lightweight-charts`
2. No TypeScript errors in browser console
3. Historical data API endpoint returns valid OHLCV data

**Solution:**
```bash
# Reinstall lightweight-charts
cd frontend
npm install lightweight-charts --save

# Verify package.json
grep "lightweight-charts" package.json

# Test API endpoint
curl "http://localhost:8080/api/market-data/ohlcv?symbol=BTC_USDT&timeframe=5m&limit=100"
```

---

### Issue: "Failed to load orders" error

**Check:**
1. Backend REST API endpoint exists: `GET /api/trading/orders`
2. Session ID is valid (if filtering by session)
3. CORS headers allow frontend origin

**Solution:**
```bash
# Test API endpoint
curl -X GET "http://localhost:8080/api/trading/orders?limit=10"

# Check CORS headers
curl -X OPTIONS "http://localhost:8080/api/trading/orders" -H "Origin: http://localhost:3000" -v

# Expected response should include:
# Access-Control-Allow-Origin: http://localhost:3000
```

---

## 📚 Additional Resources

- **TradingView Lightweight Charts Docs:** https://tradingview.github.io/lightweight-charts/
- **Next.js 14 Docs:** https://nextjs.org/docs
- **Tailwind CSS Docs:** https://tailwindcss.com/docs
- **TypeScript Handbook:** https://www.typescriptlang.org/docs/

---

## 🤝 Contributing

When modifying components:

1. Follow TypeScript strict mode
2. Use existing hooks (`useWebSocket`, `tradingAPI`)
3. Follow Tailwind CSS color palette
4. Add JSDoc comments for public props
5. Update this guide if adding new props or features

---

**Last Updated:** 2025-11-07
**Agent:** Agent 6 (Frontend & API)
**Status:** Production Ready ✅
