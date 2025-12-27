# Epic BUG-003: Paper Trading Session Critical Fixes

**Status:** backlog
**Priority:** P0 - Critical (Blocks Trading Functionality)
**Created:** 2025-12-27
**Reporter:** mr lu
**Source:** docs/bug_003.md

---

## Overview

Critical bugs discovered during Paper Trading session that prevent proper use of the trading interface. Session was started but displayed incorrect data, wrong strategies, wrong symbols, and multiple API errors.

**Session Context:**
- Session ID: exec_20251227_135849_2148c489
- Mode: PAPER
- Selected: 1 strategy ("Test Momentum Strategy")
- Selected Symbols: BLOCK/USDT, CAMP/USDT

**Observed Issues:** System showed multiple wrong strategies, wrong symbols, API errors, and severe UX problems.

---

## Goal

Fix all critical data flow and display issues so Paper Trading session correctly shows only the selected strategy and symbols with accurate indicator values.

**User Value:** "When I start a Paper Trading session with specific strategy and symbols, the dashboard shows ONLY what I selected, with real indicator values and no errors."

---

## Stories

### BUG-003-1: Session Strategy Filtering (P0)
**Problem:** State Machine Overview shows multiple strategies (7 items) when only 1 was selected. All show "Watching" state incorrectly.

**Observed:**
- E2E Pump Test (2x)
- Pump Detection Strategy (2x)
- Test Momentum Strategy (2x)
- Updated Strategy Name

**Expected:** Only "Test Momentum Strategy" should appear.

**Root Cause Investigation:**
- Check session initialization - strategy_id filtering
- Check state machine registration
- Check WebSocket subscription filtering

---

### BUG-003-2: Session Symbol Filtering (P0)
**Problem:** Chart shows BTC_USDT when session was configured for BLOCK/USDT and CAMP/USDT only.

**Expected:** Only BLOCK/USDT and CAMP/USDT charts should appear.

**Related:** Symbol Watchlist shows "No symbols in watchlist" but should show selected symbols.

**Root Cause Investigation:**
- Check session configuration persistence
- Check symbol subscription logic
- Check chart initialization

---

### BUG-003-3: Pump Indicators API 500 Error (P0)
**Problem:** Pump Indicators section shows "API error: 500" for BLOCK/USDT.

**Expected:** Real-time pump indicator values should display.

**Root Cause Investigation:**
- Check API endpoint for pump indicators
- Check backend error logs
- Check data availability for symbol

---

### BUG-003-4: Indicator Values Missing (P0)
**Problem:** Indicator Values panel shows "--" for all indicators instead of actual values.

**Expected:** Real calculated indicator values should display.

**Related:** This may be connected to WebSocket data flow or API 500 errors.

**Root Cause Investigation:**
- Check indicator calculation service
- Check WebSocket message delivery
- Check frontend state updates

---

### BUG-003-5: Live Indicators Duplicates (P1)
**Problem:** Live Indicators shows duplicate entries: "Live Indicators: AEVO_USDT" appears twice.

**Expected:** Each symbol should appear once.

**Root Cause Investigation:**
- Check subscription deduplication
- Check component rendering logic

---

### BUG-003-6: Active Positions Display Issue (P1)
**Problem:** ACTIVE POSITIONS tab shows oversized symbol - UI layout broken.

**Expected:** Normal-sized, properly formatted position display.

**Root Cause Investigation:**
- Check CSS/styling
- Check data format passed to component

---

### BUG-003-7: Page Refresh Flickering (P1)
**Problem:** Page refresh causes severe flickering and jumping. Elements "blink" during data updates. Described as "okropne" (terrible) and "nieprzyjemne" (unpleasant).

**Expected:** Smooth updates without layout shifts or flickering.

**Solution Areas:**
- Add loading states/skeletons
- Prevent layout shifts (CSS)
- Batch DOM updates
- Use React.memo / useMemo appropriately

---

### BUG-003-8: Condition Progress Auto-Collapse (P2)
**Problem:** When expanding a signal in Condition Progress to see details, it auto-collapses on data refresh. Only S1 stays expanded.

**Expected:** Expanded state should persist through data updates.

**Solution:** Store expanded state in component state, not derive from data.

---

### BUG-003-9: UX Designer Review (P2)
**Problem:** User states interface is "nieczytelny" (unreadable) and needs UX review.

**Task:** UX Designer agent to review trading interface (paper, live, backtesting) and provide improvement recommendations.

---

### BUG-003-10: E2E Test Coverage (P1)
**Task:** TEA agent to prepare comprehensive e2e tests for all trading interface functionality:
- Paper trading session flow
- Live trading session flow
- Backtesting session flow
- Symbol selection persistence
- Strategy selection persistence
- Indicator value display
- Error handling scenarios

---

## Acceptance Criteria

1. **AC1:** Paper Trading session shows ONLY the selected strategy in State Machine Overview
2. **AC2:** Chart displays ONLY selected symbols (not BTC_USDT when not selected)
3. **AC3:** Symbol Watchlist shows selected symbols
4. **AC4:** Pump Indicators displays actual values (no API 500 error)
5. **AC5:** Indicator Values panel shows calculated values (not "--")
6. **AC6:** No duplicate entries in Live Indicators
7. **AC7:** Active Positions displays correctly formatted
8. **AC8:** Page updates are smooth (no flickering/jumping)
9. **AC9:** Condition Progress expanded state persists
10. **AC10:** E2E tests exist for session flows

---

## Priority Order

**P0 (Must Fix First - Blocking):**
1. BUG-003-1: Session Strategy Filtering
2. BUG-003-2: Session Symbol Filtering
3. BUG-003-3: Pump Indicators API 500
4. BUG-003-4: Indicator Values Missing

**P1 (Important):**
5. BUG-003-7: Page Refresh Flickering
6. BUG-003-10: E2E Test Coverage
7. BUG-003-5: Live Indicators Duplicates
8. BUG-003-6: Active Positions Display

**P2 (Polish):**
9. BUG-003-8: Condition Progress Auto-Collapse
10. BUG-003-9: UX Designer Review

---

## Log Analysis Evidence

### Frontend Errors (frontend_error.log)

| Error Type | Count | Source File |
|------------|-------|-------------|
| Positions API 404 | 249 | ActivePositionBanner.tsx:92 |
| Pump Indicators API 500 | 236 | PumpIndicatorsPanel.tsx:522 |
| Live Indicators API 500 | 95 | LiveIndicatorPanel.tsx:68 |
| WebSocket pong timeout | 20 | useWebSocket hook |

### Backend Errors (backend.log)

**ERROR: Order Persistence Failure**
```
event_type: trading_persistence.order_create_save_failed
error: [Errno 22] Invalid argument
error_type: OSError
```

**CONFIRMED: Multiple Strategies Active**
```
active_count: 4 (should be 1)
Strategies running: "Updated Strategy Name", "E2E Pump Test", etc.
```

### Additional Story Required

**BUG-003-11: Order Persistence OSError (P0)**
- **Problem:** Backend fails to save orders with OSError: `[Errno 22] Invalid argument`
- **Impact:** Paper trading orders not persisted
- **Location:** trading_persistence service
- **Root Cause:** Likely file path or timestamp issue on Windows

---

## Technical Investigation Required

Before implementation, dev agent should:

1. **Check session initialization flow:**
   - How is session created with strategy/symbol selection?
   - Where is filtering applied?

2. **Check WebSocket subscriptions:**
   - Are subscriptions filtered by session config?
   - Why are wrong symbols subscribed?

3. **Check API endpoints:**
   - Why is Pump Indicators returning 500?
   - Check backend logs for errors

4. **Check frontend state management:**
   - Is session config stored correctly in Zustand?
   - Are components reading correct state?

---

## Files to Investigate

- Session initialization: `src/api/` or `src/services/`
- WebSocket subscriptions: `src/api/websocket/`
- Frontend state: `frontend/src/stores/`
- Pump Indicators API: Backend API handlers
- Trading dashboard: `frontend/src/pages/` or `frontend/src/components/trading/`

---

*Generated by PM Agent - BMAD Framework*
*Source: docs/bug_003.md*
