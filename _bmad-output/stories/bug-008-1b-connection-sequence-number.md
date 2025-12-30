# Story BUG-008-1b: Connection Sequence Number for Log Correlation

**Status:** backlog
**Priority:** P2 (Nice-to-have)
**Epic:** BUG-008 WebSocket Stability & Service Health
**Parent Story:** BUG-008-1 (WebSocket Disconnect Diagnostic Logging)

---

## Story

As a **developer debugging reconnection issues**,
I want **a connection sequence number that increments on each reconnect**,
so that **I can correlate logs across multiple reconnection cycles for the same client**.

---

## Background

During BUG-008-1 verification, the Dev Agent noted that `connection_sequence_number` was mentioned in Task 4 but not implemented because it wasn't in the Acceptance Criteria. This is a nice-to-have enhancement for debugging multi-reconnect scenarios.

**Current state:**
- `client_id` is unique per connection
- On reconnect, client gets NEW `client_id`
- Hard to correlate "client A reconnected 5 times in 10 minutes"

**Proposed enhancement:**
- Add `connection_sequence_number` that increments each reconnect
- Maintain across reconnects using `reconnect_token` or session storage
- Enables log queries like: "show all connections for this session"

---

## Acceptance Criteria

1. **AC1:** Frontend tracks `connectionSequence` counter starting at 1
2. **AC2:** Counter increments on each reconnect attempt
3. **AC3:** Counter is included in connection_closed logs
4. **AC4:** Counter survives page refresh (use sessionStorage)
5. **AC5:** Backend receives and logs the sequence number

---

## Implementation Notes

### Frontend (websocket.ts)
```typescript
private connectionSequence: number = 1;

constructor() {
  // Restore from sessionStorage on init
  const stored = sessionStorage.getItem('ws_connection_sequence');
  this.connectionSequence = stored ? parseInt(stored, 10) : 1;
}

private connect(): void {
  // Increment on connect
  this.connectionSequence++;
  sessionStorage.setItem('ws_connection_sequence', String(this.connectionSequence));
  // Include in handshake...
}
```

### Log format enhancement
```json
{
  "client_id": "abc123",
  "connection_sequence": 3,
  "close_code": 1006,
  "duration_seconds": 45.2
}
```

### Query example
```sql
-- Find all connections for a session
SELECT * FROM websocket_logs
WHERE session_id = 'xyz'
ORDER BY connection_sequence;
```

---

## Tasks / Subtasks

- [ ] Task 1: Add connectionSequence to frontend
  - [ ] Add private field with sessionStorage persistence
  - [ ] Increment on connect()
  - [ ] Include in handshake message

- [ ] Task 2: Update backend to receive sequence
  - [ ] Parse from handshake
  - [ ] Store in connection object
  - [ ] Include in log_connection_closed

- [ ] Task 3: Update log formats
  - [ ] Backend: add connection_sequence to log_data
  - [ ] Frontend: add connection_sequence to logData

- [ ] Task 4: Add tests
  - [ ] Test sequence increments
  - [ ] Test persistence across reconnect
  - [ ] Test log output includes field

---

## Definition of Done

1. [ ] Sequence number tracks correctly across reconnects
2. [ ] Logs include connection_sequence field
3. [ ] Unit tests pass
4. [ ] Documentation updated

---

## Notes

- This is **low priority** - only useful for debugging complex reconnect scenarios
- Can be deferred until we actually encounter multi-reconnect debugging needs
- No user-facing impact

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from Dev Agent verification report |
