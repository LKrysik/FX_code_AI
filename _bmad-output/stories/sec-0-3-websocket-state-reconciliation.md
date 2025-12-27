# Story SEC-0-3: WebSocket State Reconciliation

Status: completed

## Story

As a **trader**,
I want **the UI to sync with the actual backend state after WebSocket reconnection**,
so that **I never make trading decisions based on stale or outdated information**.

## Background

**SEC-P0: WebSocket State Desync**
- **Severity:** CRITICAL
- **Vector:** Disconnect/reconnect without state sync (no Redis = in-memory state)
- **Risk:** User sees outdated positions, makes incorrect trading decisions
- **Impact:** Financial loss due to stale data

**Related:** KI2 (WebSocket reconnection not always working)

## Acceptance Criteria

1. **AC1:** On reconnect, frontend requests full state snapshot from backend
2. **AC2:** Backend provides complete current state (positions, signals, indicators)
3. **AC3:** Frontend replaces stale state with fresh snapshot
4. **AC4:** User sees visual confirmation of state sync ("State synchronized")
5. **AC5:** If sync fails, user is warned to refresh manually

## Tasks / Subtasks

- [x] **Task 1: Implement State Snapshot Endpoint** *(Already implemented)*
  - [x] 1.1 Create GET /api/state/snapshot endpoint - unified_server.py:3056
  - [x] 1.2 Include: positions, active_signals, state_machine_state, indicators
  - [x] 1.3 Add timestamp for staleness detection
  - [x] 1.4 Support filtering by session_id

- [x] **Task 2: Implement WebSocket State Request** *(Using REST approach instead)*
  - [x] 2.1 Frontend uses REST endpoint instead of WS message
  - [x] 2.2 Backend provides state via /api/state/snapshot
  - [x] 2.3 Frontend handles response in requestStateSync()

- [x] **Task 3: Frontend State Reconciliation**
  - [x] 3.1 On WS reconnect, request state sync - websocket.ts:507
  - [x] 3.2 Replace Zustand store state with snapshot - websocket.ts:579-594
  - [x] 3.3 Show toast "State synchronized" on success - websocket.ts:597-598
  - [x] 3.4 Show error banner if sync fails - websocket.ts:619-620

- [x] **Task 4: Handle Edge Cases**
  - [x] 4.1 Handle slow network (timeout + retry) - websocket.ts:528-611
  - [x] 4.2 Handle partial sync failure - syncStatus set to 'failed'
  - [x] 4.3 Handle backend restart during sync - retry logic handles this
  - [x] 4.4 Provide manual "Force Sync" button - ConnectionStatusIndicator.tsx:349-362

- [x] **Task 5: Add Tests**
  - [x] 5.1 Test reconnect triggers state sync - websocket.test.ts
  - [x] 5.2 Test state replacement is complete - websocket.test.ts
  - [x] 5.3 Test user notification works - websocket.test.ts
  - [x] 5.4 Test failure handling - websocket.test.ts, test_websocket_api.py

## Dev Notes

### Key Files

| File | Purpose |
|------|---------|
| `src/api/unified_server.py` | State snapshot endpoint |
| `src/api/event_bridge.py` | WebSocket message handling |
| `frontend/src/services/websocket.ts` | WS client |
| `frontend/src/stores/*.ts` | Zustand stores |

### State Snapshot Schema

```python
@dataclass
class StateSnapshot:
    timestamp: datetime
    session_id: Optional[str]
    positions: List[Position]
    active_signals: List[Signal]
    state_machine_state: str  # 'MONITORING', 'SIGNAL_DETECTED', etc.
    indicator_values: Dict[str, float]
    pending_orders: List[Order]
```

### WebSocket Protocol

```typescript
// Request
{type: "state_sync_request", session_id: "abc123"}

// Response
{
  type: "state_sync_response",
  success: true,
  data: {
    timestamp: "2025-12-26T10:00:00Z",
    positions: [...],
    active_signals: [...],
    state_machine_state: "MONITORING",
    indicator_values: {...}
  }
}
```

### Frontend Reconnect Handler

```typescript
wsService.setCallbacks({
  onConnect: async () => {
    console.log('[WS] Connected, requesting state sync...');
    const snapshot = await wsService.requestStateSync();
    if (snapshot.success) {
      // Replace all stores
      usePositionStore.setState(snapshot.data.positions);
      useSignalStore.setState(snapshot.data.active_signals);
      useIndicatorStore.setState(snapshot.data.indicator_values);
      toast.success('State synchronized');
    } else {
      toast.error('State sync failed - please refresh');
    }
  }
});
```

## References

- [Source: docs/KNOWN_ISSUES.md#SEC-P0: WebSocket State Desync]
- [Source: docs/KNOWN_ISSUES.md#KI2: WebSocket reconnection]
- [Source: src/api/event_bridge.py]
- [Source: frontend/src/services/websocket.ts]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Console logs added: `[WS] Requesting state sync...`, `[WS] State snapshot received:`, `[WS] State sync completed successfully`
- Error logs added: `[WS] State sync error:`, `[WS] Retrying state sync`

### Completion Notes List

1. Task 1: Backend endpoint `/api/state/snapshot` already existed - verified implementation
2. Task 2: Used REST approach instead of WebSocket message (simpler, more reliable)
3. Task 3: Enhanced `requestStateSync()` with notifications via uiStore
4. Task 4: Added 10s timeout, 3 retries with exponential backoff, Force Sync button
5. Task 5: Added comprehensive tests in websocket.test.ts and test_websocket_api.py

### File List

| File | Changes |
|------|---------|
| `frontend/src/services/websocket.ts:522-652` | Enhanced requestStateSync(), added forceStateSync(), showStateSyncNotification() |
| `frontend/src/components/common/ConnectionStatusIndicator.tsx` | Added sync status display and Force Sync button |
| `frontend/src/services/__tests__/websocket.test.ts:343-588` | Added SEC-0-3 state sync test suite |
| `tests/e2e/test_websocket_api.py:425-616` | Added TestStateSnapshot class |
| `src/api/unified_server.py:3053-3130` | Already existed (verified) |
| `frontend/src/stores/websocketStore.ts:28-103` | Already had syncStatus/lastSyncTime (verified) |
