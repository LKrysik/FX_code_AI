# Story SEC-0-3: WebSocket State Reconciliation

Status: ready-for-dev

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

- [ ] **Task 1: Implement State Snapshot Endpoint**
  - [ ] 1.1 Create GET /api/state/snapshot endpoint
  - [ ] 1.2 Include: positions, active_signals, state_machine_state, indicators
  - [ ] 1.3 Add timestamp for staleness detection
  - [ ] 1.4 Support filtering by session_id

- [ ] **Task 2: Implement WebSocket State Request**
  - [ ] 2.1 Add "state_sync_request" WebSocket message type
  - [ ] 2.2 Backend responds with full state snapshot
  - [ ] 2.3 Frontend handles "state_sync_response" message

- [ ] **Task 3: Frontend State Reconciliation**
  - [ ] 3.1 On WS reconnect, request state sync
  - [ ] 3.2 Replace Zustand store state with snapshot
  - [ ] 3.3 Show toast "State synchronized" on success
  - [ ] 3.4 Show error banner if sync fails

- [ ] **Task 4: Handle Edge Cases**
  - [ ] 4.1 Handle slow network (timeout + retry)
  - [ ] 4.2 Handle partial sync failure
  - [ ] 4.3 Handle backend restart during sync
  - [ ] 4.4 Provide manual "Force Sync" button

- [ ] **Task 5: Add Tests**
  - [ ] 5.1 Test reconnect triggers state sync
  - [ ] 5.2 Test state replacement is complete
  - [ ] 5.3 Test user notification works
  - [ ] 5.4 Test failure handling

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

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
