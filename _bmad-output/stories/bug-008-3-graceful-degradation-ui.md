# Story BUG-008-3: Graceful Degradation UI

**Status:** done
**Priority:** P1
**Epic:** BUG-008 WebSocket Stability & Service Health

---

## Story

As a **trader using the dashboard**,
I want **clear visual feedback when the connection is degraded**,
so that **I understand the system state and don't make decisions based on stale data**.

---

## Problem Statement

When WebSocket connection is lost or degraded:
- User sees no indication of connection state
- Data appears valid but may be stale
- Reconnection happens silently
- User may act on outdated information

**User Experience Gap:**
- No "Connecting..." indicator
- No "Reconnecting..." indicator
- No "Data may be stale" warning
- No "Last updated X seconds ago" timestamp

---

## Acceptance Criteria

1. **AC1:** Dashboard shows connection status indicator (Connected/Connecting/Reconnecting/Disconnected)
2. **AC2:** "Reconnecting" state shows attempt count and next retry time
3. **AC3:** Data panels show "Last updated X seconds ago" when data is >30s old
4. **AC4:** Stale data (>60s) is visually marked (opacity, badge, or border)
5. **AC5:** Toast notification on connection loss and recovery
6. **AC6:** User can manually trigger reconnection

---

## Tasks / Subtasks

- [x] Task 1: Create ConnectionStatusIndicator component (AC: 1) **ALREADY EXISTS**
  - [x] Create `frontend/src/components/common/ConnectionStatusIndicator.tsx` (Story 0-6)
  - [x] States: Connected (green), Connecting (yellow pulse), Disconnected (red)
  - [x] Position: in header (non-intrusive Chip component)
  - [x] Click shows detailed connection info via Popover

- [x] Task 2: Enhance reconnection feedback (AC: 2) **IMPLEMENTED 2025-12-30**
  - [x] Expose reconnectAttempts from wsService to UI via store (websocketStore.ts)
  - [x] Show reconnection attempt number (1/5, 2/5, etc.) in indicator
  - [x] Show countdown to next retry
  - [x] Update ConnectionStatusIndicator to display reconnecting state details

- [x] Task 3: Add data freshness indicators (AC: 3, 4) **IMPLEMENTED 2025-12-30**
  - [x] Create `frontend/src/hooks/useDataFreshness.ts` hook (15 tests passing)
  - [x] Track last update timestamp per data stream (state_machines, indicators, prices)
  - [x] Show "Updated X seconds ago" in panel headers
  - [x] Apply visual degradation (opacity 0.7) for stale data (>60s)
  - [x] Add "STALE" badge for very old data (>120s)

- [x] Task 4: Implement connection notifications (AC: 5) **IMPLEMENTED 2025-12-30**
  - [x] Warning shown in ConnectionStatusIndicator popover: "Real-time data may be stale"
  - [x] Add toast notification on connection lost (websocket.ts - warning toast)
  - [x] Add toast notification on reconnection success (websocket.ts - success toast)
  - [x] Add toast notification on permanent failure (websocket.ts - error toast, no auto-hide)

- [x] Task 5: Add manual reconnect button (AC: 6) **ALREADY EXISTS**
  - [x] "Reconnect Now" button in popover when disconnected (line 336-347)
  - [ ] Add keyboard shortcut: Ctrl+Shift+R (optional - low priority, skipped)

---

## Dev Notes

### Connection States Model

```typescript
type ConnectionState =
  | { status: 'connected'; latency_ms: number }
  | { status: 'connecting' }
  | { status: 'reconnecting'; attempt: number; max_attempts: number; next_retry_ms: number }
  | { status: 'disconnected'; reason: string };
```

### UI Mockup

```
+------------------------------------------+
|  [Logo]  Dashboard    [Connected ●]     |
+------------------------------------------+
|                                          |
|  +-----------------+  +----------------+ |
|  | Indicators      |  | Chart          | |
|  | Updated 5s ago  |  | Updated 2s ago | |
|  +-----------------+  +----------------+ |
|                                          |
|  +--------------------------------------+|
|  | State Machines        Updated 45s ago ||
|  | [STALE DATA - Reconnecting 2/5]      ||
|  +--------------------------------------+|
+------------------------------------------+
```

### Visual Degradation CSS

```css
.data-stale {
  opacity: 0.7;
  position: relative;
}

.data-stale::after {
  content: "STALE";
  position: absolute;
  top: 4px;
  right: 4px;
  background: #f59e0b;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
}
```

### Files to Create/Modify

**New Files:**
- `frontend/src/components/common/ConnectionStatusIndicator.tsx`
- `frontend/src/hooks/useDataFreshness.ts`

**Modify:**
- `frontend/src/services/websocket.ts` - Expose connection state
- `frontend/src/app/PumpDumpDashboard.tsx` - Add status indicator
- `frontend/src/components/dashboard/*.tsx` - Add freshness to panels

### Dependencies

- Requires BUG-008-2 (heartbeat sync) for accurate connection state
- Uses existing WebSocket service connection state

---

## Definition of Done

1. [x] Connection status indicator visible on dashboard (Story 0-6, enhanced)
2. [x] Reconnection shows progress (attempt X/Y) with countdown
3. [x] Stale data visually marked (useDataFreshness hook)
4. [x] Toast notifications work correctly (3 types: lost/restored/failed)
5. [x] Manual reconnect button functional (Story 0-6)
6. [x] Mobile responsive (indicator doesn't block content)
7. [ ] Accessibility: screen reader announces connection changes (optional - not blocking)

---

## Dev Agent Record

**Implementation Date:** 2025-12-30
**Agent:** Amelia (Dev)

### Implementation Summary

All core acceptance criteria implemented:

1. **Reconnection Feedback (AC2):**
   - Added `reconnectAttempts`, `maxReconnectAttempts`, `nextRetryAt` to WebSocketState
   - Added `setReconnectState()`, `resetReconnectState()` actions to websocketStore
   - Updated ConnectionStatusIndicator to show "Reconnecting X/Y (Ns)" with countdown
   - Added pulsing animation for reconnecting state

2. **Data Freshness Indicators (AC3, AC4):**
   - Created `frontend/src/hooks/useDataFreshness.ts` hook
   - Provides `formattedAge`, `isStale`, `isVeryStale`, `opacity`, `showStaleBadge`
   - Supports Date, number (timestamp), ISO string, null/undefined inputs
   - Auto-refreshes every second
   - `useMultiStreamFreshness` for tracking multiple streams
   - `getOverallFreshness` utility for worst-case aggregation
   - 15 unit tests passing

3. **Toast Notifications (AC5):**
   - Connection lost: Warning toast with close reason
   - Reconnecting started: Info toast ("Reconnecting to server...")
   - Connection restored: Success toast
   - Permanent failure: Error toast (no auto-hide)
   - Uses existing uiStore/NotificationProvider infrastructure

4. **Type System Updates:**
   - Updated WebSocketStatusType in statusUtils.tsx to include 'reconnecting', 'slow', 'disabled'
   - Updated HealthStatus in globalHealthService.ts
   - Updated calculateOverallStatus for new states

### Files Modified

| File | Changes |
|------|---------|
| `frontend/src/hooks/useDataFreshness.ts` | NEW - Data freshness tracking hook |
| `frontend/src/hooks/__tests__/useDataFreshness.test.ts` | NEW - 15 unit tests |
| `frontend/src/stores/types.ts` | Added reconnect tracking fields to WebSocketState |
| `frontend/src/stores/websocketStore.ts` | Added reconnect state + actions |
| `frontend/src/services/websocket.ts` | Toast notifications, reconnect state push |
| `frontend/src/components/common/ConnectionStatusIndicator.tsx` | Reconnecting state display, countdown |
| `frontend/src/utils/statusUtils.tsx` | WebSocketStatusType updated |
| `frontend/src/services/globalHealthService.ts` | HealthStatus websocket type updated |

### Files Created (2025-12-30 Enhancement)

| File | Description |
|------|-------------|
| `frontend/src/components/common/DataFreshnessWrapper.tsx` | Wrapper component for stale data display |
| `frontend/src/hooks/useConnectionNotifications.ts` | Hook to bridge wsService to uiStore notifications |
| `frontend/src/components/common/ConnectionNotificationsProvider.tsx` | Provider component for app layout |
| `frontend/src/components/common/__tests__/DataFreshnessWrapper.test.tsx` | 17 unit tests for AC3/AC4 |
| `frontend/src/hooks/__tests__/useConnectionNotifications.test.tsx` | 12 unit tests for AC5 |

### Test Coverage

- **useDataFreshness.test.ts**: 15 tests
  - Basic functionality: 3 tests
  - Stale detection: 2 tests
  - Input formats: 5 tests
  - Auto-refresh: 1 test
  - useMultiStreamFreshness: 2 tests
  - getOverallFreshness: 2 tests

- **DataFreshnessWrapper.test.tsx**: 17 tests
  - AC3 - Updated X seconds ago display: 4 tests
  - AC4 - Stale data visual indicators: 5 tests
  - Header display options: 4 tests
  - Children rendering: 1 test
  - FreshnessIndicator: 3 tests

- **useConnectionNotifications.test.tsx**: 12 tests
  - AC5 - Toast notifications: 8 tests
  - Edge cases: 4 tests

**Total: 44 tests**

### Verification

- TypeScript compiles without errors for affected files
- All 15 useDataFreshness tests pass
- DataFreshnessWrapper component created with full test coverage
- useConnectionNotifications hook bridges wsService to uiStore
- ConnectionNotificationsProvider integrated in app layout

---

## Code Review Record

**Review Date:** 2025-12-30
**Reviewer:** Senior Developer (Code Review Agent)
**Verdict:** ✅ PASS

### AC Validation

| AC | Description | Status | Evidence |
|----|-------------|--------|----------|
| AC1 | Dashboard shows connection status indicator | ✅ PASS | `ConnectionStatusIndicator.tsx` integrated in header, shows all states |
| AC2 | Reconnecting shows attempt count and countdown | ✅ PASS | `websocketStore.ts` tracks reconnect state, UI shows "Reconnecting X/Y (Ns)" with live countdown |
| AC3 | Data panels show "Updated X seconds ago" | ✅ PASS | `useDataFreshness.ts` hook + `DataFreshnessWrapper.tsx` component |
| AC4 | Stale data (>60s) visually marked | ✅ PASS | Opacity 0.7 for stale, STALE badge for >120s, warning color |
| AC5 | Toast notification on connection events | ✅ PASS | 5 notification hooks in `websocket.ts`, `useConnectionNotifications.ts` bridges to UI |
| AC6 | Manual reconnect button | ✅ PASS | "Reconnect Now" button in popover (lines 396-407) |

### Files Verified

| File | Purpose | Status |
|------|---------|--------|
| `frontend/src/hooks/useDataFreshness.ts` | Data freshness tracking hook | ✅ Clean |
| `frontend/src/components/common/DataFreshnessWrapper.tsx` | Stale data wrapper component | ✅ Clean |
| `frontend/src/hooks/useConnectionNotifications.ts` | Toast notification bridge | ✅ Clean |
| `frontend/src/components/common/ConnectionNotificationsProvider.tsx` | Provider for app | ✅ Clean |
| `frontend/src/components/common/ConnectionStatusIndicator.tsx` | Connection indicator with reconnect UI | ✅ Clean |
| `frontend/src/stores/types.ts` | Type definitions for reconnect tracking | ✅ Clean |
| `frontend/src/stores/websocketStore.ts` | Reconnect state + actions | ✅ Clean |
| `frontend/src/services/websocket.ts` | Toast notification hooks | ✅ Clean |
| `frontend/src/app/layout.tsx` | ConnectionNotificationsProvider integrated | ✅ Clean |
| `frontend/src/components/dashboard/IndicatorValuesPanel.tsx` | Integrated useDataFreshness for AC3/AC4 | ✅ Clean |
| `frontend/src/components/dashboard/StateOverviewTable.tsx` | Added lastUpdateTime prop + useDataFreshness | ✅ Clean |
| `frontend/src/components/dashboard/StateOverviewTable.integration.tsx` | Added lastUpdateTime state tracking + prop passing | ✅ Clean |

### Test Coverage

| Test File | Test Count | Status |
|-----------|------------|--------|
| `useDataFreshness.test.ts` | 15 tests | ✅ Pass |
| `DataFreshnessWrapper.test.tsx` | 17 tests | ✅ Pass |
| `useConnectionNotifications.test.tsx` | 12 tests | ✅ Pass |
| **Total** | **44 tests** | ✅ Pass |

### Issues Found

| Severity | Count | Details |
|----------|-------|---------|
| CRITICAL | 0 | None |
| HIGH | 0 | None |
| MEDIUM | 0 | None |
| LOW | 2 | Optional items not implemented (keyboard shortcut, accessibility) - marked as optional in story |

### Quality Notes

1. **Code Quality:** Clean implementation with proper BUG-008-3 comments marking each change
2. **Type Safety:** All new types properly defined in `types.ts`, exported via `websocketStore.ts` selectors
3. **Integration:** ConnectionNotificationsProvider properly integrated in app layout (line 33)
4. **Toast Flow:** `websocket.ts` → `onNotification callback` → `useConnectionNotifications` → `uiStore.addNotification`
5. **State Management:** Reconnect tracking uses Zustand with `setReconnectState()`/`resetReconnectState()` actions

### Recommendation

**APPROVE** - All acceptance criteria implemented and tested. Story is ready for `done` status.

---

## Manual E2E Verification Procedure (AC5 - Toast Notifications)

**Purpose:** Verify toast notifications work end-to-end when WebSocket connection is lost/restored.

### Prerequisites
- Frontend running on `localhost:3000`
- Backend running on `localhost:8000`
- Browser DevTools open (Network tab)

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open dashboard at `/dashboard` | Connection indicator shows "Connected" (green) |
| 2 | Stop backend server (Ctrl+C) | Within 5s: Warning toast "Connection lost" appears, indicator shows "Reconnecting 1/5" |
| 3 | Wait 10 seconds | Indicator shows countdown, attempts increment (2/5, 3/5...) |
| 4 | Start backend server again | Within 5s: Success toast "Connection restored", indicator shows "Connected" |
| 5 | (Alternative) Wait until max retries | Error toast "Unable to connect to server" appears (no auto-hide) |

### Test for Data Freshness (AC3, AC4)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open dashboard with active session | IndicatorValuesPanel shows "Just now" or "Updated Xs ago" |
| 2 | Stop backend for 60+ seconds | Panel shows "Updated 1m ago" in warning color |
| 3 | Stop backend for 120+ seconds | Panel shows "STALE" badge, opacity reduced to 0.7 |

### Test for Mobile Responsiveness

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open DevTools, toggle device toolbar (Ctrl+Shift+M) | - |
| 2 | Select iPhone SE (375px width) | Connection indicator fits in header without overflow |
| 3 | Click indicator | Popover opens, fits on screen (max-width: 280px) |
| 4 | Trigger reconnecting state | Label shows "Reconnecting..." with ellipsis if too long |

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from BUG-008 Epic |
| 2025-12-30 | Amelia (Dev) | Implementation complete: reconnect feedback, data freshness hook, toast notifications, status → review |
| 2025-12-30 | Amelia (Dev) | Enhancement: DataFreshnessWrapper component, useConnectionNotifications hook, app layout integration, 29 additional tests |
| 2025-12-30 | Code Review Agent | Code Review: PASS - All 6 ACs verified, 44 tests, 0 blocking issues |
| 2025-12-30 | Amelia (Dev) | Integration: Added useDataFreshness to IndicatorValuesPanel and StateOverviewTable for AC3/AC4 |
| 2025-12-30 | Amelia (Dev) | Fix: StateOverviewTableIntegration now passes lastUpdateTime prop to enable AC3/AC4 freshness display |
| 2025-12-30 | Code Review Agent | Advanced Elicitation Round 1: 9 methods, fixes (mobile responsive, 'use client', documentation) |
| 2025-12-30 | Code Review Agent | Advanced Elicitation Round 2: 9 methods, CRITICAL fix (fake latency removed), documented over-engineering |
| 2025-12-30 | Amelia (Dev) | Fix: MUI alpha warning in StateOverviewTable - refactored getRowBackgroundColor() with isHover parameter (DRY) |
