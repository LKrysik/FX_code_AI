# Manual Signal Flow Verification Guide

**Story:** 0-2-e2e-signal-flow-verification
**Purpose:** Verify E2E signal flow from backend to frontend browser console

## Prerequisites

1. Backend running: `python -m src.api.unified_server`
2. Frontend running: `cd frontend && npm run dev`
3. Browser DevTools open (F12)

## Step-by-Step Verification

### Step 1: Start Services

```bash
# Terminal 1 - Backend
cd C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2
python -m src.api.unified_server

# Terminal 2 - Frontend
cd C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2\frontend
npm run dev
```

### Step 2: Open Browser DevTools

1. Navigate to `http://localhost:3000/dashboard`
2. Press F12 to open DevTools
3. Go to **Console** tab
4. Filter by typing `[SIGNAL-FLOW]` in filter box

### Step 3: Trigger Signal Generation

**Option A: Via API (Recommended)**

```bash
# Trigger strategy evaluation
curl -X POST http://localhost:8080/api/strategies/evaluate \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT", "strategy_name": "test_strategy"}'
```

**Option B: Start Backtest Session**

1. Navigate to `/trading-session`
2. Select "Backtest" mode
3. Select a strategy
4. Click "Start Session"
5. Wait for signal generation

### Step 4: Verify Console Output

Expected console output format:
```
[SIGNAL-FLOW] Signal received: {
  type: "signal" | "signals",
  signal_type: "S1" | "O1" | "Z1" | "ZE1" | "E1",
  symbol: "BTCUSDT",
  section: "S1",
  timestamp: "2025-01-01T00:00:00.000Z",
  latency_ms: <number less than 500>,
  indicators: {...}
}
```

And store update:
```
[SIGNAL-FLOW] Signal added to store: {
  signal_type: "S1",
  symbol: "BTCUSDT",
  timestamp: "...",
  store_count: 1
}
```

### Step 5: Verify Acceptance Criteria

| AC | Verification | Expected Result |
|----|--------------|-----------------|
| AC1 | Check `latency_ms` in console | < 500ms |
| AC2 | Check fields in log | signal_type, symbol, timestamp, section, indicators present |
| AC3 | Check React DevTools | dashboardStore.activeSignals has new entry |
| AC4 | Run pytest | All tests pass |
| AC5 | This document | Exists and is usable |

### Step 6: Verify Zustand Store (Optional)

1. Install React DevTools browser extension
2. Open DevTools > Components > Search for "dashboardStore"
3. Expand `activeSignals` array
4. Verify signal object matches console output

## Troubleshooting

### No `[SIGNAL-FLOW]` logs appearing

1. Check WebSocket connection status (look for `[WebSocket] CONNECTION OPENED`)
2. Verify backend is generating signals (check backend logs for `signal_generated`)
3. Ensure you're subscribed to signals stream

### Latency > 500ms

1. Check network tab for slow WebSocket messages
2. Verify backend processing time
3. Check for JavaScript main thread blocking

### Signal not appearing in store

1. Check for JavaScript errors in console
2. Verify `addSignal` is being called (check `[SIGNAL-FLOW] Signal added to store`)
3. Check that signal has required fields

## Running Tests

### Backend Integration Tests
```bash
cd C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2
pytest tests/integration/test_e2e_signal_flow.py -v
```

### Frontend E2E Tests
```bash
cd C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2\frontend
npx playwright test tests/e2e/flows/signal-flow.e2e.spec.ts
```

## Success Criteria

- [ ] Console shows `[SIGNAL-FLOW] Signal received` with latency < 500ms
- [ ] Console shows `[SIGNAL-FLOW] Signal added to store`
- [ ] React DevTools shows signal in `activeSignals`
- [ ] All pytest tests pass
- [ ] All Playwright tests pass (when backend available)

---
*Generated for Story 0-2: E2E Signal Flow Verification*
