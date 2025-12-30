# Story BUG-007.1: Refactor StateOverviewTable to Use Shared WebSocket

Status: done

## Story

As a **frontend developer**,
I want **StateOverviewTable to use the shared wsService singleton**,
so that **there is only one WebSocket connection with proper auth, heartbeat, and reconnection**.

## Acceptance Criteria

1. **AC1:** StateOverviewTable uses `wsService` singleton instead of `new WebSocket()`
2. **AC2:** Component uses `addSessionUpdateListener()` for receiving updates
3. **AC3:** Component uses `wsService.subscribe('state_machines', params)` for subscription
4. **AC4:** Remove all standalone WebSocket management code (~80 lines)
5. **AC5:** Connection remains stable with proper heartbeat (no disconnect/reconnect cycle)

## Tasks / Subtasks

- [x] Task 1: Remove standalone WebSocket code (AC: 4)
  - [x] Remove `wsUrl` state and construction
  - [x] Remove `connectWebSocket` callback function (lines 83-166)
  - [x] Remove WebSocket-related useEffect hooks (lines 253-267)
  - [x] Remove `wsConnectedState` local state

- [x] Task 2: Add wsService integration (AC: 1, 2, 3)
  - [x] Import `wsService` and `WSMessage` from `@/services/websocket`
  - [x] Import `useWebSocketStore` from `@/stores/websocketStore`
  - [x] Use `useWebSocketStore` for connection status
  - [x] Add subscription via `wsService.subscribe('state_machines', { session_id })`
  - [x] Add listener via `wsService.addSessionUpdateListener()`

- [x] Task 3: Implement message handlers (AC: 2)
  - [x] Handle `state_change` messages → update state
  - [x] Handle `instance_added` messages → add to instances
  - [x] Handle `instance_removed` messages → remove from instances
  - [x] Handle `full_update` messages → replace all instances

- [x] Task 4: Cleanup on unmount (AC: 1)
  - [x] Call cleanup function from listener
  - [x] Call `wsService.unsubscribe('state_machines')`

- [x] Task 5: Test integration
  - [x] Verify single WebSocket connection in Network tab
  - [x] Verify state updates flow correctly
  - [x] Verify no memory leaks on unmount

## Dev Notes

### Architecture Requirements

- **ADR-001:** All components must use `wsService` singleton
- Current anti-pattern creates DUPLICATE WebSocket connections
- Component has ~80 lines of WebSocket management code to remove

### Technical Specification

**Current Code (REMOVE):**
```typescript
// Lines 83-166 - entire connectWebSocket function
const connectWebSocket = useCallback(() => {
  const socket = new WebSocket(wsUrl);
  socket.onopen = () => {
    socket.send(JSON.stringify({
      type: 'subscribe',
      channel: 'state_machines',  // WRONG field name
      session_id: sessionId
    }));
  };
  // ... 80+ lines
}, [sessionId, wsUrl]);
```

**New Code (ADD):**
```typescript
import { wsService, WSMessage } from '@/services/websocket';
import { useWebSocketStore } from '@/stores/websocketStore';

// In component:
const wsConnected = useWebSocketStore((state) => state.isConnected);

useEffect(() => {
  if (!sessionId) return;

  wsService.subscribe('state_machines', { session_id: sessionId });

  const cleanup = wsService.addSessionUpdateListener((message: WSMessage) => {
    if (message.stream === 'state_machines' || message.type === 'state_change') {
      handleStateChange(message.data);
    } else if (message.type === 'instance_added') {
      handleInstanceAdded(message.data);
    } else if (message.type === 'instance_removed') {
      handleInstanceRemoved(message.data);
    } else if (message.type === 'full_update') {
      setInstances(message.data?.instances || []);
    }
  }, 'StateOverviewTable');

  return () => {
    cleanup();
    wsService.unsubscribe('state_machines');
  };
}, [sessionId]);
```

### Dependencies

- Depends on: **BUG-007-S0** (backend broadcaster) - for data to flow
- Depends on: **BUG-007-S2** (valid_streams) - for subscription validation
- Depends on: **BUG-007-S3** (wsService handling) - for message routing

### Project Structure Notes

- File: `frontend/src/components/dashboard/StateOverviewTable.integration.tsx`
- Lines to remove: 43 (wsUrl import?), 83-166, 253-267
- Lines to add: wsService imports, new useEffect

### References

- [Source: _bmad-output/bug-007-epic-stories.md#Story-1]
- [ADR-001: Use Shared WebSocket Singleton]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required.

### Completion Notes List

1. Removed ~80 lines of standalone WebSocket code (connectWebSocket, ws state, wsUrl)
2. Added wsService integration with subscribe() and addSessionUpdateListener()
3. Replaced local wsConnected state with useWebSocketStore selector
4. All message handlers (state_change, instance_added, instance_removed, full_update) implemented
5. Proper cleanup on unmount with listener cleanup and unsubscribe()

### File List

**Modified Files:**
- `frontend/src/components/dashboard/StateOverviewTable.integration.tsx` - Complete refactor to wsService

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | Bob (SM) | Story created from BUG-007 Epic |
| 2025-12-29 | Amelia (Dev) | Story implemented - all 5 ACs met, ~80 lines removed |
