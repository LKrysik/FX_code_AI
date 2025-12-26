# Story 0.2: E2E Signal Flow Verification

Status: ready-for-dev

## Story

As a **developer**,
I want **visual proof that signals flow from backend to frontend and appear in the browser console**,
so that **I can confirm the entire pipeline is connected before building UI components**.

## Acceptance Criteria

1. **AC1:** When backend generates a signal, it appears in browser console within 500ms
2. **AC2:** Browser console log includes: signal_type, symbol, timestamp, section, indicator values
3. **AC3:** Zustand dashboardStore receives signal and updates `activeSignals` state
4. **AC4:** Integration test exists that proves E2E flow works
5. **AC5:** Test can be run manually or in CI to verify pipeline integrity

## Tasks / Subtasks

- [ ] **Task 1: Add Debug Logging to Frontend** (AC: 1, 2)
  - [ ] 1.1 Add console.log in `websocket.ts` when signal message received (line ~277-288)
  - [ ] 1.2 Log full signal payload with timestamp for latency measurement
  - [ ] 1.3 Use distinct log prefix (e.g., `[SIGNAL-FLOW]`) for easy filtering

- [ ] **Task 2: Verify Zustand Store Integration** (AC: 3)
  - [ ] 2.1 Confirm `onSignals` callback connects to `dashboardStore.addSignal()`
  - [ ] 2.2 Add logging when signal added to store
  - [ ] 2.3 Verify signal appears in React DevTools Zustand panel

- [ ] **Task 3: Create Manual Verification Test** (AC: 4, 5)
  - [ ] 3.1 Create test script that triggers StrategyManager signal
  - [ ] 3.2 Document manual verification steps
  - [ ] 3.3 Add to developer documentation

- [ ] **Task 4: Create Integration Test** (AC: 4, 5)
  - [ ] 4.1 Create `tests/integration/test_e2e_signal_flow.py`
  - [ ] 4.2 Test: trigger signal → assert WebSocket receives message
  - [ ] 4.3 Measure and assert latency < 500ms
  - [ ] 4.4 Add test to CI pipeline

- [ ] **Task 5: Create Frontend E2E Test** (AC: 1, 3)
  - [ ] 5.1 Create Playwright test in `frontend/tests/e2e/`
  - [ ] 5.2 Test: connect → wait for signal → verify console log
  - [ ] 5.3 Verify dashboardStore state update

## Dev Notes

### Dependency on Story 0-1

This story assumes Story 0-1 (Fix EventBridge Signal Subscription) is complete. The EventBridge `signal_generated` handler at `event_bridge.py:638-644` must be working.

### Current Signal Flow (from Story 0-1)

```
Backend:
StrategyManager._publish_signal_generated()
    ↓
event_bus.publish("signal_generated", signal_event)  [strategy_manager.py:2248]
    ↓
EventBridge.handle_signal_generated()                [event_bridge.py:639-641]
    ↓
WebSocket broadcast to "signals" stream

Frontend:
websocket.ts.handleMessage()                         [websocket.ts:277-288]
    ↓
callbacks.onSignals(message)
    ↓
dashboardStore.addSignal(signal)                     [dashboardStore.ts:52-58]
```

### Key Frontend Files

| File | Purpose | Lines |
|------|---------|-------|
| `frontend/src/services/websocket.ts` | WebSocket client, message routing | 277-288, 393-394 |
| `frontend/src/stores/dashboardStore.ts` | Signal state management | 46-58 |
| `frontend/src/hooks/useWebSocket.ts` | React hook for WebSocket | - |

### WebSocket Message Format

**Incoming signal message:**
```typescript
{
  type: "signal" | "signals",
  stream: "signals",
  data: {
    signal_type: "S1" | "O1" | "Z1" | "ZE1" | "E1",
    symbol: "BTCUSDT",
    section: "S1",  // Same as signal_type
    timestamp: "2025-01-01T00:00:00.000Z",
    indicators: {
      pump_magnitude_pct: 7.5,
      volume_surge_ratio: 4.2,
      price_velocity: 0.8
    },
    metadata: {...}
  },
  timestamp: "2025-01-01T00:00:00.000Z"
}
```

### Zustand Store Signal Handling

**dashboardStore.ts:52-58:**
```typescript
addSignal: (signal: ActiveSignal) => {
  if (!signal) return;
  const currentSignals = get().activeSignals;
  // Keep only latest 10 signals to prevent memory bloat
  const updatedSignals = [signal, ...currentSignals.slice(0, 9)];
  set({ activeSignals: updatedSignals });
},
```

### Debug Logging Pattern

**Add to websocket.ts (~line 278):**
```typescript
case 'signal':
case 'signals':
  console.log('[SIGNAL-FLOW] Signal received:', {
    type: message.type,
    signal_type: message.data?.signal_type,
    symbol: message.data?.symbol,
    timestamp: message.timestamp,
    latency_ms: Date.now() - new Date(message.timestamp).getTime()
  });
  this.callbacks.onSignals?.(message);
  break;
```

### Testing Approach

**Backend Integration Test (pytest):**
```python
# tests/integration/test_e2e_signal_flow.py
async def test_signal_reaches_websocket():
    # 1. Setup EventBridge with mock WebSocket
    # 2. Trigger StrategyManager.evaluate()
    # 3. Assert signal message sent to WebSocket
    # 4. Measure latency
```

**Frontend E2E Test (Playwright):**
```typescript
// frontend/tests/e2e/signal-flow.spec.ts
test('signal appears in console', async ({ page }) => {
  const logs: string[] = [];
  page.on('console', msg => logs.push(msg.text()));

  await page.goto('/dashboard');
  // Trigger signal from backend (API call or mock)
  await page.waitForTimeout(1000);

  expect(logs.some(l => l.includes('[SIGNAL-FLOW]'))).toBe(true);
});
```

### Manual Verification Steps

1. Start backend: `python -m src.api.unified_server`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser DevTools Console
4. Filter by `[SIGNAL-FLOW]`
5. Trigger strategy evaluation (via API or backtest)
6. Verify signal appears in console with latency < 500ms

### Pattern Requirements (from Architecture)

- Use consistent log prefix `[SIGNAL-FLOW]` for filtering
- Log structured data (object, not string concatenation)
- Include latency measurement in logs
- Follow existing test patterns in `tests/integration/`

### Success Verification

**Visual proof required:**
- Screenshot of browser console showing signal with latency
- Test passing in CI log

### Previous Story Intelligence

From Story 0-1:
- EventBridge handler exists at `event_bridge.py:638-644`
- Signal schema defined in `core/event_bus.py:40`
- WebSocket message routing in `websocket.ts:277-288`

### References

- [Source: _bmad-output/architecture.md#Signal Pipeline Integration]
- [Source: _bmad-output/prd.md#FR18: View generated signals]
- [Source: _bmad-output/epics.md#Epic 0 Story 2]
- [Source: frontend/src/services/websocket.ts:277-288]
- [Source: frontend/src/stores/dashboardStore.ts:46-58]
- [Source: _bmad-output/stories/0-1-fix-eventbridge-signal-subscription.md]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
