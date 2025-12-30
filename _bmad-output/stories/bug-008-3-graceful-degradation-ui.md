# Story BUG-008-3: Graceful Degradation UI

**Status:** backlog
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

- [ ] Task 1: Create ConnectionStatusIndicator component (AC: 1)
  - [ ] Create `frontend/src/components/ConnectionStatusIndicator.tsx`
  - [ ] States: Connected (green), Connecting (yellow pulse), Reconnecting (orange), Disconnected (red)
  - [ ] Position: top-right corner of dashboard (non-intrusive)
  - [ ] Tooltip shows detailed connection info

- [ ] Task 2: Enhance reconnection feedback (AC: 2)
  - [ ] Show reconnection attempt number (1/5, 2/5, etc.)
  - [ ] Show countdown to next retry
  - [ ] Show exponential backoff time

- [ ] Task 3: Add data freshness indicators (AC: 3, 4)
  - [ ] Create `useDataFreshness` hook
  - [ ] Track last update timestamp per data stream
  - [ ] Show "Updated X seconds ago" in panel headers
  - [ ] Apply visual degradation (opacity 0.7) for stale data (>60s)
  - [ ] Add "STALE" badge for very old data (>120s)

- [ ] Task 4: Implement connection notifications (AC: 5)
  - [ ] Toast on connection lost: "Connection lost. Reconnecting..."
  - [ ] Toast on reconnection: "Connection restored"
  - [ ] Toast on permanent failure: "Unable to connect. Check network."
  - [ ] Use existing toast/notification system

- [ ] Task 5: Add manual reconnect button (AC: 6)
  - [ ] Add "Reconnect" button in disconnected state
  - [ ] Add "Reconnect" option in settings/menu
  - [ ] Keyboard shortcut: Ctrl+Shift+R (optional)

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

1. [ ] Connection status indicator visible on dashboard
2. [ ] Reconnection shows progress (attempt X/Y)
3. [ ] Stale data visually marked
4. [ ] Toast notifications work correctly
5. [ ] Manual reconnect button functional
6. [ ] Mobile responsive (indicator doesn't block content)
7. [ ] Accessibility: screen reader announces connection changes

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from BUG-008 Epic |
