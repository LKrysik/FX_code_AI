# Story BUG-008-7: QuestDB Connection Resilience

**Status:** backlog
**Priority:** P0
**Epic:** BUG-008 WebSocket Stability & Service Health

---

## Story

As a **data service**,
I want **resilient QuestDB connection handling with automatic recovery**,
so that **database connectivity issues don't cascade into dashboard failures**.

---

## Problem Statement

Log evidence shows QuestDB connection failures:
```json
{
  "event_type": "dashboard_cache_service.get_active_sessions_failed",
  "data": {
    "error": "[Errno 10061] Connect call failed ('127.0.0.1', 8812)"
  }
}
```

Later log shows empty error (different failure mode):
```json
{
  "event_type": "dashboard_cache_service.get_active_sessions_failed",
  "data": {
    "error": ""
  }
}
```

**Issues:**
1. QuestDB connection failure (Errno 10061) cascades to dashboard cache service
2. No retry mechanism - single failure = service unavailable
3. Empty error message indicates poor error handling
4. No circuit breaker to prevent cascade of failures

---

## Acceptance Criteria

1. **AC1:** QuestDB connection has retry logic with exponential backoff (3 attempts)
2. **AC2:** Circuit breaker pattern: after N failures, stop trying for M seconds
3. **AC3:** Error messages always include meaningful context (never empty)
4. **AC4:** Service returns graceful degradation response when QuestDB unavailable
5. **AC5:** Connection pool with health checks for QuestDB
6. **AC6:** Automatic reconnection when QuestDB becomes available again

---

## Tasks / Subtasks

- [ ] Task 1: Implement connection retry logic (AC: 1)
  - [ ] Add retry decorator/wrapper for QuestDB calls
  - [ ] Retry 3 times with delays: 100ms, 500ms, 1000ms
  - [ ] Log each retry attempt
  - [ ] Only retry on connection errors, not query errors

- [ ] Task 2: Implement circuit breaker (AC: 2)
  - [ ] Track consecutive failures
  - [ ] After 5 failures, enter "open" state
  - [ ] In "open" state, fail fast for 30 seconds
  - [ ] After 30s, try "half-open" (single probe request)
  - [ ] On success, return to "closed" state

- [ ] Task 3: Improve error handling (AC: 3)
  - [ ] Catch all exception types and extract meaningful message
  - [ ] Log full exception traceback at DEBUG level
  - [ ] Include operation context in error: "Failed to get_active_sessions: {error}"
  - [ ] Never log empty error strings

- [ ] Task 4: Implement graceful degradation (AC: 4)
  - [ ] When QuestDB unavailable, return cached data (if available)
  - [ ] Return special response: `{"status": "degraded", "reason": "database_unavailable", "cached_at": "..."}`
  - [ ] Frontend handles degraded response appropriately

- [ ] Task 5: Add connection pool health checks (AC: 5, 6)
  - [ ] Periodic health check query: `SELECT 1`
  - [ ] If health check fails, mark connection as unhealthy
  - [ ] Auto-remove unhealthy connections from pool
  - [ ] Auto-create new connections when needed

---

## Dev Notes

### Circuit Breaker States

```
[CLOSED] ──failure──► [OPEN] ──timeout──► [HALF-OPEN]
    ▲                                          │
    │                                          │
    └────────────success────────────────────────
                                               │
                                          failure
                                               │
                                               ▼
                                           [OPEN]
```

### Circuit Breaker Configuration

```python
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,       # Failures before opening
    "recovery_timeout": 30,       # Seconds in open state
    "half_open_max_calls": 1,     # Probes in half-open state
}
```

### Retry Decorator

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
    retry=retry_if_exception_type(ConnectionError)
)
async def query_questdb(self, query: str):
    # ... implementation
```

### Graceful Degradation Response

```python
class QuestDBResponse:
    status: Literal["ok", "degraded", "error"]
    data: Optional[Any]
    cached_at: Optional[datetime]
    reason: Optional[str]

# When database unavailable:
return QuestDBResponse(
    status="degraded",
    data=self._cache.get("active_sessions"),
    cached_at=self._cache.get_timestamp("active_sessions"),
    reason="database_unavailable"
)
```

### Error Handling Pattern

```python
except Exception as e:
    error_msg = str(e) or type(e).__name__
    self.logger.error("questdb.query_failed", {
        "operation": "get_active_sessions",
        "error": error_msg,
        "error_type": type(e).__name__,
        "query": query[:100]  # Truncated for safety
    })
    self.logger.debug("questdb.query_failed_traceback", exc_info=True)
```

### Files to Modify

- `src/data/questdb_data_provider.py` - QuestDB data provider
- `src/services/dashboard_cache_service.py` - Dashboard cache
- Create: `src/core/circuit_breaker.py` - Reusable circuit breaker

### Dependencies

- Independent story - can be implemented in parallel with others

---

## Definition of Done

1. [ ] Connection retries with exponential backoff
2. [ ] Circuit breaker prevents cascade failures
3. [ ] All error logs have meaningful messages
4. [ ] Degraded response when database unavailable
5. [ ] Health check keeps connection pool healthy
6. [ ] Unit tests for circuit breaker states
7. [ ] Integration test: stop QuestDB, verify graceful degradation

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from BUG-008 Epic |
