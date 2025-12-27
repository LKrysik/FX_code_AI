# Epic BUG-004: WebSocket & Dashboard Real-Time Data Critical Fixes

**Status:** backlog
**Priority:** P0 - Critical (Blocks Dashboard Real-Time Functionality)
**Created:** 2025-12-27
**Reporter:** mr lu
**Source:** docs/bug_004.md

---

## Overview

Critical bugs discovered during Paper Trading session that prevent dashboard real-time data display. WebSocket connection is unstable, backend returns "Invalid column: side" error, and dashboard components show empty/inactive states despite active session with selected strategy and symbols.

**Session Context:**
- Session ID: exec_20251227_165822_fe61be26
- Mode: PAPER
- Selected: 1 strategy
- Selected Symbols: 3 symbols
- Status: Running (but dashboard shows nothing)

**Observed Issues:**
- WebSocket constantly reconnecting ("Too many missed pongs")
- Backend error "Invalid column: side" on signals endpoint
- State Machine Overview: "No active instances"
- Symbol Watchlist: "No symbols in watchlist"
- Indicator Values: All "--"
- Condition Progress: "INACTIVE"

---

## Goal

Fix WebSocket stability and backend query errors so Paper Trading dashboard displays real-time data correctly when a session is active.

**User Value:** "When I start a Paper Trading session, the dashboard maintains stable WebSocket connection and shows real-time state machine instances, symbols, indicator values, and condition progress."

---

## Stories

### BUG-004-0: Pre-Flight Data Verification (P0) [ADDED BY PARADOX ANALYSIS]
**Problem:** We cannot fix display issues if no data exists in database.

**Task:** Before fixing any component, verify:
1. Session exists in database with correct config
2. Strategy is registered and active
3. Symbols are subscribed
4. Indicator calculation is running
5. Data is being written to QuestDB

**Expected:** Baseline confirmation that data pipeline is functional.

**Why Added:** Theseus Paradox revealed gap - we're fixing display when data might not exist.

---

### BUG-004-1: Fix "Invalid column: side" Backend Error (P0)
**Problem:** Backend returns 500 error with "Invalid column: side" when fetching signals.

**Error Log:**
```json
{"event_type": "dashboard_routes.get_signals_failed", "error": "Invalid column: side"}
```

**Expected:** Signals endpoint returns data without error.

**Root Cause Investigation:**
- Check signals database schema - does "side" column exist?
- Check QuestDB query syntax
- May be schema mismatch after recent changes

---

### BUG-004-2: WebSocket Ping/Pong Stability (P0)
**Problem:** WebSocket connection constantly reconnects with "Too many missed pongs" error.

**Frontend Error:**
```
[useWebSocket] Too many missed pongs, forcing reconnect
```

**Backend Log:**
```
INFO: connection open
INFO: connection closed
(repeating rapidly)
```

**Expected:** Stable WebSocket connection without frequent reconnects.

**Root Cause Investigation:**
- Check ping/pong interval timing
- Check if backend is responding to ping with pong
- Check if heavy data load causes delays
- May need to increase pong timeout threshold
- [PARADOX] Check if backend closes connection intentionally (exception, memory pressure)
- [PARADOX] Implement polling fallback when WebSocket fails 3+ times
- [PARADOX] Consider if aggressive health check CAUSES instability (increase tolerance)

---

### BUG-004-3: State Machine Instance Registration (P0)
**Problem:** State Machine Overview shows "No active instances" despite active session with strategy.

**Expected:** Selected strategy should appear as active state machine instance.

**Root Cause Investigation:**
- Check if state machine instances are created on session start
- Check WebSocket subscription for state machine updates
- Check if backend is publishing state machine events
- Check frontend state store for instances

---

### BUG-004-4: Symbol Watchlist Population (P1)
**Problem:** Symbol Watchlist shows "No symbols in watchlist" despite 3 symbols selected.

**Expected:** All 3 selected symbols should appear in watchlist.

**Root Cause Investigation:**
- Check session symbols configuration
- Check frontend component reading session state
- May be related to WebSocket subscription not delivering symbol data

---

### BUG-004-5: Indicator Values Data Flow (P1)
**Problem:** Indicator Values show "--" for all indicators.

**Expected:** Real-time indicator values from calculation service.

**Root Cause Investigation:**
- Likely consequence of WebSocket instability (BUG-004-2)
- Check if indicator calculation service is running
- Check WebSocket message types for indicators

---

### BUG-004-6: Condition Progress Inactive State (P1)
**Problem:** Condition Progress shows "INACTIVE" despite running session.

**Expected:** Active condition monitoring with real-time updates.

**Root Cause Investigation:**
- Dependent on state machine instances (BUG-004-3)
- Dependent on indicator values (BUG-004-5)
- Check condition evaluation engine status

---

## Acceptance Criteria

1. **AC1:** Signals endpoint returns valid data (no "Invalid column: side" error)
2. **AC2:** WebSocket connection stable for 5+ minutes without reconnect
3. **AC3:** State Machine Overview shows active strategy instance
4. **AC4:** Symbol Watchlist displays selected symbols
5. **AC5:** Indicator Values panel shows calculated values (not "--")
6. **AC6:** Condition Progress shows active monitoring status

---

## Priority Order

**P0 (Must Fix First - Root Causes):**
1. BUG-004-1: Fix "Invalid column: side" Backend Error
2. BUG-004-2: WebSocket Ping/Pong Stability
3. BUG-004-3: State Machine Instance Registration

**P1 (Dependent - Should Auto-Resolve):**
4. BUG-004-4: Symbol Watchlist Population
5. BUG-004-5: Indicator Values Data Flow
6. BUG-004-6: Condition Progress Inactive State

---

## Technical Analysis

### Dependency Graph

```
BUG-004-1 (Invalid column: side)
    └─→ Signals not loading

BUG-004-2 (WebSocket instability)
    └─→ BUG-004-3 (No state machine instances)
        └─→ BUG-004-6 (Condition Progress inactive)
    └─→ BUG-004-5 (Indicator Values --)
    └─→ BUG-004-4 (Symbol Watchlist empty)
```

### Key Insight

The WebSocket instability (BUG-004-2) is likely the **root cause** for most dashboard display issues. When WebSocket keeps reconnecting, subscription data is lost. The "Invalid column: side" (BUG-004-1) is a separate database schema issue.

**Fix Order Strategy:**
1. Fix BUG-004-1 first (isolated database fix)
2. Fix BUG-004-2 (core infrastructure)
3. BUG-004-3 through BUG-004-6 should auto-resolve or require minor fixes

---

## Files to Investigate

**Backend:**
- `src/api/dashboard_routes.py` - signals endpoint
- `src/api/websocket/` - WebSocket handler
- Database schema for signals table

**Frontend:**
- `frontend/src/hooks/useWebSocket.ts` - ping/pong logic
- `frontend/src/stores/` - state machine state
- `frontend/src/components/dashboard/` - affected panels

---

*Generated by PM Agent - BMAD Framework*
*Source: docs/bug_004.md*
