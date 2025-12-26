# Story SEC-0-1: Position Operation Locking

Status: ready-for-dev

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

- [ ] **Task 1: Implement Position Lock Mechanism**
  - [ ] 1.1 Add `position_locks: Dict[str, asyncio.Lock]` to StrategyManager
  - [ ] 1.2 Create `acquire_position_lock(position_id)` method
  - [ ] 1.3 Create `release_position_lock(position_id)` method
  - [ ] 1.4 Add timeout to prevent deadlocks (30s default)

- [ ] **Task 2: Protect Close Operations**
  - [ ] 2.1 Wrap `close_position()` with lock acquisition
  - [ ] 2.2 Return error if lock already held
  - [ ] 2.3 Log lock acquisition/release for debugging
  - [ ] 2.4 Handle lock timeout gracefully

- [ ] **Task 3: Protect Modify Operations**
  - [ ] 3.1 Wrap `modify_position()` with lock acquisition
  - [ ] 3.2 Allow concurrent reads but exclusive writes
  - [ ] 3.3 Validate position state before modification

- [ ] **Task 4: Add Integration Tests**
  - [ ] 4.1 Test concurrent close requests
  - [ ] 4.2 Test lock timeout behavior
  - [ ] 4.3 Test P&L calculation accuracy
  - [ ] 4.4 Verify no orphaned orders

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

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
