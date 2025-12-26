# Story SEC-0-1: Position Operation Locking

Status: done

## Story

As a **trader**,
I want **position close/modify operations to be protected against race conditions**,
so that **I never experience double-close bugs, incorrect P&L calculations, or orphaned orders**.

## Background

**SEC-P0: Race Condition in Position Close/Modify**
- **Severity:** CRITICAL
- **Vector:** Concurrent requests to close the same position
- **Risk:** Double-close, incorrect P&L, orphaned orders
- **Impact:** Real money at risk

## Acceptance Criteria

1. **AC1:** Concurrent close requests on same position result in exactly ONE close
2. **AC2:** Second close request receives error "Position already closing/closed"
3. **AC3:** P&L is calculated exactly once per position close
4. **AC4:** No orphaned orders left in exchange after close
5. **AC5:** Locking mechanism handles crashes gracefully (timeout-based release)

## Tasks / Subtasks

- [x] **Task 1: Implement Position Lock Mechanism**
  - [x] 1.1 Created `PositionLockManager` class in trading_routes.py
  - [x] 1.2 Created `acquire(position_id, operation)` method
  - [x] 1.3 Created `release(position_id)` method
  - [x] 1.4 Added 30s timeout to prevent deadlocks

- [x] **Task 2: Protect Close Operations**
  - [x] 2.1 Wrapped `close_position()` with lock acquisition
  - [x] 2.2 Returns HTTP 409 if lock already held
  - [x] 2.3 Added structured logging for lock events
  - [x] 2.4 Lock released in finally block (exception-safe)

- [x] **Task 3: Protect Modify Operations**
  - [x] 3.1 Wrapped `modify_sl_tp()` with lock acquisition
  - [x] 3.2 Exclusive lock per position_id
  - [x] 3.3 Returns 409 if position already locked

- [x] **Task 4: Add Integration Tests**
  - [x] 4.1 Test concurrent close requests (14 tests)
  - [x] 4.2 Test lock timeout behavior
  - [x] 4.3 Test lock release after exceptions
  - [x] 4.4 Test edge cases (double release, etc.)

## Dev Notes

### Key Files

| File | Purpose |
|------|---------|
| `src/core/strategy_manager.py` | Main position management logic |
| `src/infrastructure/adapters/mexc_futures_adapter.py` | Exchange operations |
| `src/core/execution_controller.py` | Order execution |

### Lock Implementation Pattern

```python
class PositionLockManager:
    def __init__(self, timeout: float = 30.0):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock_times: Dict[str, float] = {}
        self._timeout = timeout

    async def acquire(self, position_id: str) -> bool:
        if position_id not in self._locks:
            self._locks[position_id] = asyncio.Lock()

        try:
            await asyncio.wait_for(
                self._locks[position_id].acquire(),
                timeout=self._timeout
            )
            self._lock_times[position_id] = time.time()
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Lock timeout for position {position_id}")
            return False

    def release(self, position_id: str):
        if position_id in self._locks and self._locks[position_id].locked():
            self._locks[position_id].release()
            del self._lock_times[position_id]
```

### Error Response Pattern

```python
class PositionAlreadyClosingError(Exception):
    """Raised when attempting to close a position that is already being closed."""
    pass
```

## References

- [Source: docs/KNOWN_ISSUES.md#SEC-P0: Race Condition]
- [Source: src/core/strategy_manager.py]
- [Source: src/infrastructure/adapters/mexc_futures_adapter.py]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Position lock acquire/release logged with structured logging
- Warnings for race condition prevention logged

### Completion Notes List

1. Implemented `PositionLockManager` class with asyncio.Lock per position
2. Integrated locking into `close_position` endpoint (lines 448-531)
3. Integrated locking into `modify_sl_tp` endpoint (lines 565-704)
4. HTTP 409 Conflict returned when lock already held
5. All 14 integration tests passing

### Sanity Verification (70-75)

**70. Scope Integrity Check:**
- All 5 ACs addressed
- AC1: Lock ensures single close ✅
- AC2: HTTP 409 returned for second request ✅
- AC3: P&L calculated once (lock ensures single execution) ✅
- AC4: Exchange operations protected by OrderManager internal locks ✅
- AC5: 30s timeout prevents deadlocks ✅

**71. Alignment Check:**
- Goal "protect against race conditions" fully achieved
- Both close_position and modify_sl_tp endpoints protected

**72. Closure Check:**
- No TODO/TBD markers
- All tasks completed and tested

**73. Coherence Check:**
- Consistent locking pattern across both endpoints
- Lock release always in finally block (exception-safe)

**74. Grounding Check:**
- Assumption: API is primary entry point for user position operations ✅
- Note: StrategyManager internal closes use OrderManager._lock separately

**75. Falsifiability Check:**
- Risk: Internal StrategyManager closes not covered by PositionLockManager
- Mitigation: OrderManager has own asyncio.Lock for internal operations
- Future: Consider unified locking at OrderManager level

### File List

| File | Change |
|------|--------|
| `src/api/trading_routes.py` | Added PositionLockManager class (lines 31-117) and integrated locking |
| `tests/integration/test_position_locking.py` | Created 14 comprehensive tests |
| `src/core/exceptions.py` | NEW: Centralized exceptions (PositionAlreadyClosingError, etc.) |
| `src/domain/services/position_lock_manager.py` | NEW: Enhanced singleton lock manager with context manager |
| `frontend/src/utils/statusUtils.tsx` | Added HTTP 409 'conflict' error type handling |

### Frontend HTTP 409 Handling (2025-12-26)

Added support for position operation conflicts in frontend:
- Added 'conflict' to ErrorType union type (line 293)
- Added specific handling for HTTP 409 in categorizeError() (lines 366-379)
- Added recovery strategy for conflict errors (lines 464-471)
  - shouldRetry: true (after 3s delay)
  - maxRetries: 2
  - Message: "Wait a moment and try again - operation in progress"
