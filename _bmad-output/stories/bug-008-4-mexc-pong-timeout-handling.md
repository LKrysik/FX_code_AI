# Story BUG-008-4: MEXC Pong Timeout Handling

**Status:** backlog
**Priority:** P0
**Epic:** BUG-008 WebSocket Stability & Service Health

---

## Story

As a **backend service**,
I want **proper handling of MEXC WebSocket pong timeouts**,
so that **stale connections are detected quickly and reconnected before data loss**.

---

## Problem Statement

Log evidence shows extreme pong delays without action:
```json
{
  "event_type": "mexc_adapter.no_recent_pong_detected",
  "data": {
    "connection_id": 0,
    "last_pong_age": 3356.3878767490387,  // 55+ MINUTES!
    "consecutive_timeouts": 1
  }
}
```

**Issues:**
1. `last_pong_age` of 3356 seconds (55+ minutes) indicates connection was effectively dead for nearly an hour
2. `consecutive_timeouts: 1` suggests only first warning, no escalation
3. Connection was not proactively closed and reconnected
4. All data during this period was either stale or lost

---

## Acceptance Criteria

1. **AC1:** Pong age > 60s triggers WARNING log and health check
2. **AC2:** Pong age > 120s triggers connection close and reconnect
3. **AC3:** Consecutive timeout counter escalates action severity
4. **AC4:** Reconnection uses exponential backoff (1s, 2s, 4s, 8s, max 30s)
5. **AC5:** Maximum reconnection attempts configurable (default: 10)
6. **AC6:** After max attempts, escalate to ERROR and notify (optional: alert system)

---

## Tasks / Subtasks

- [ ] Task 1: Implement pong timeout thresholds (AC: 1, 2)
  - [ ] Add configurable thresholds: WARN_THRESHOLD=60s, RECONNECT_THRESHOLD=120s
  - [ ] Modify pong check loop to compare against thresholds
  - [ ] Log at appropriate levels based on age

- [ ] Task 2: Implement escalating actions (AC: 3)
  - [ ] consecutive_timeouts = 1: Log WARNING, trigger health check
  - [ ] consecutive_timeouts = 2: Log WARNING, prepare for reconnect
  - [ ] consecutive_timeouts = 3: Log ERROR, force close and reconnect
  - [ ] Reset counter on successful pong

- [ ] Task 3: Implement reconnection with backoff (AC: 4, 5)
  - [ ] Create `reconnect_with_backoff()` method
  - [ ] Implement exponential backoff: 1, 2, 4, 8, 16, 30, 30, 30...
  - [ ] Track attempt count per connection
  - [ ] Add jitter to prevent thundering herd

- [ ] Task 4: Implement max attempts handling (AC: 6)
  - [ ] After max_attempts, stop reconnecting
  - [ ] Log CRITICAL error
  - [ ] Emit event for potential alerting
  - [ ] Mark connection as "permanently failed"

- [ ] Task 5: Add health check on timeout (AC: 1)
  - [ ] On first timeout, send ping and wait for pong
  - [ ] If pong received, reset timeout counter
  - [ ] If no pong in 10s, increment counter

---

## Dev Notes

### Current vs Proposed Behavior

```
Current:
pong_age=3356s → log WARNING → do nothing → data lost for 55 minutes

Proposed:
pong_age=60s → log WARNING → send health check ping
pong_age=120s → log ERROR → close connection
pong_age=121s → start reconnect with backoff
pong_age=...  → reconnect attempts 1,2,3...10
pong_age=...  → after 10 failures → CRITICAL alert, stop trying
```

### Configuration

```python
# mexc_adapter.py
PONG_WARN_THRESHOLD_SECONDS = 60
PONG_RECONNECT_THRESHOLD_SECONDS = 120
MAX_RECONNECT_ATTEMPTS = 10
BACKOFF_BASE_SECONDS = 1
BACKOFF_MAX_SECONDS = 30
```

### Exponential Backoff Implementation

```python
def get_backoff_delay(attempt: int) -> float:
    """Calculate backoff delay with jitter."""
    base_delay = min(
        BACKOFF_BASE_SECONDS * (2 ** attempt),
        BACKOFF_MAX_SECONDS
    )
    # Add 0-25% jitter
    jitter = base_delay * random.uniform(0, 0.25)
    return base_delay + jitter
```

### State Machine for Connection

```
[CONNECTED] --pong_timeout--> [CHECKING]
[CHECKING] --pong_received--> [CONNECTED]
[CHECKING] --no_pong--> [RECONNECTING]
[RECONNECTING] --success--> [CONNECTED]
[RECONNECTING] --max_attempts--> [FAILED]
[FAILED] --manual_reset--> [RECONNECTING]
```

### Files to Modify

- `src/adapters/mexc_adapter.py` - Main adapter with pong handling
- `src/adapters/mexc_websocket.py` - WebSocket connection (if separate)

### Log Messages

```python
# WARNING at 60s
logger.warning("mexc_adapter.pong_timeout_warning", {
    "connection_id": conn_id,
    "last_pong_age_seconds": age,
    "action": "health_check_initiated"
})

# ERROR at 120s
logger.error("mexc_adapter.pong_timeout_reconnecting", {
    "connection_id": conn_id,
    "last_pong_age_seconds": age,
    "action": "connection_closed_for_reconnect"
})

# CRITICAL after max attempts
logger.critical("mexc_adapter.connection_permanently_failed", {
    "connection_id": conn_id,
    "reconnect_attempts": attempts,
    "action": "manual_intervention_required"
})
```

---

## Definition of Done

1. [ ] Pong timeout triggers reconnect within 2 minutes
2. [ ] Reconnection uses exponential backoff
3. [ ] Max attempts limit prevents infinite loops
4. [ ] Logs clearly show timeout progression
5. [ ] Unit tests cover all timeout scenarios
6. [ ] Integration test: simulate network partition, verify recovery

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from BUG-008 Epic |
