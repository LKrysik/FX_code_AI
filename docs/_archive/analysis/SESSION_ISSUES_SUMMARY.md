# Session Management Issues - Executive Summary
## Agent 2 Analysis - 2025-11-09

---

## 🔴 CRITICAL FINDINGS

### Root Cause: Three-Way Session Storage Chaos

Sessions are stored in **THREE SEPARATE LOCATIONS** with no synchronization:

1. **ExecutionController._current_session** → Single active session in memory
2. **DataCollectionPersistenceService._active_sessions** → Dict cache in memory
3. **QuestDB data_collection_sessions** → Persistent database

**Impact**: "Session not found" errors occur because:
- Session exists in memory but not in DB yet (50-200ms race window)
- Session exists in DB but controller shows "no_active_session"
- Session cleanup fails in one location but succeeds in others

---

## 📊 Critical Issues (Priority Order)

| ID | Severity | Issue | Impact | Files Affected |
|----|----------|-------|--------|----------------|
| SESSION-001 | CRITICAL | Three-way storage inconsistency | Core functionality broken | execution_controller.py:331, data_collection_persistence_service.py:54 |
| SESSION-002 | CRITICAL | Race condition: creation vs persistence | 404 errors on immediate queries | execution_controller.py:443-713 |
| SESSION-003 | HIGH | Inconsistent session lookup logic | Different results per endpoint | unified_server.py:2036, data_analysis_routes.py:302 |
| SESSION-004 | HIGH | No atomic cleanup | Orphaned/zombie sessions | execution_controller.py:1495-1535 |
| SESSION-005 | MEDIUM | Returns command_id instead of session_id | Client lookup failures | unified_trading_controller.py:365-421 |

---

## 🎯 Quick Fix Recommendations

### Fix #1: Make QuestDB Single Source of Truth (SESSION-001)

**Current Problem**:
```python
# Three separate stores!
ExecutionController._current_session = session
DataCollectionPersistenceService._active_sessions[id] = session
QuestDB INSERT INTO data_collection_sessions
```

**Fix**:
```python
# Single source of truth
QuestDB as only storage
→ Remove _active_sessions cache
→ Query DB for all lookups
→ Cache only for performance (with TTL)
```

**Files to Change**:
- `execution_controller.py`: Remove _current_session, query DB
- `data_collection_persistence_service.py`: Remove _active_sessions dict
- All endpoints: Use unified SessionService for lookups

---

### Fix #2: Persist BEFORE Returning (SESSION-002)

**Current Problem**:
```python
# Race condition window
session_id = create_session_in_memory()  # 10ms
# ⚠️ 50-200ms gap where session exists in memory only
await persist_to_questdb(session_id)     # 150ms
return session_id  # Client can query before DB write completes!
```

**Fix**:
```python
# Atomic creation
session_id = generate_id()
await persist_to_questdb(session_id)  # DB FIRST
create_session_in_memory(session_id)   # Memory after
return session_id  # Safe - exists in DB
```

**Files to Change**:
- `execution_controller.py:690-713`: Move DB write before memory creation
- Add retry logic with exponential backoff

---

### Fix #3: Unified Session Lookup (SESSION-003)

**Current Problem**:
```python
# Three different lookup strategies!
GET /sessions/{id}                    → Checks controller only
POST /sessions/stop                   → Checks QuestDB first
GET /api/data-collection/sessions     → Checks QuestDB only
```

**Fix**:
```python
# Single lookup service
class SessionService:
    async def get_session(self, id: str) -> Session:
        # Strategy: controller → QuestDB → None
        session = await self._check_controller(id)
        if session:
            return session
        return await self._query_questdb(id)
```

**Files to Change**:
- Create new `src/domain/services/session_service.py`
- Update all endpoints to use SessionService

---

### Fix #4: Atomic Cleanup with Rollback (SESSION-004)

**Current Problem**:
```python
# Independent operations - can fail separately
self._current_session = None                      # ✅ SUCCESS
await db.update_status('stopped')                 # ❌ FAILS
# Session cleared from memory but DB shows 'running'!
```

**Fix**:
```python
# Transaction with rollback
session_backup = self._current_session
try:
    await db.update_status('stopped')  # DB FIRST
    self._current_session = None        # Memory after
except Exception:
    self._current_session = session_backup  # ROLLBACK
    raise
```

**Files to Change**:
- `execution_controller.py:1500-1535`: Add try-finally rollback

---

### Fix #5: Return session_id, Not command_id (SESSION-005)

**Current Problem**:
```python
try:
    result = await execute_with_result(timeout=5.0)
    session_id = result.get("session_id")
    if not session_id:
        # ❌ WRONG: Return command_id instead
        return await execute_command()  # Returns command_id!
```

**Fix**:
```python
try:
    result = await execute_with_result(timeout=15.0)  # Longer timeout
    session_id = result.get("session_id")
    if not session_id:
        raise ValueError("Session creation failed")
    return session_id  # Always return session_id
except TimeoutError:
    raise RuntimeError("Session creation timed out")
```

**Files to Change**:
- `unified_trading_controller.py:365-421`: Remove command_id fallback

---

## 🔬 Testing Strategy

### Critical Tests to Add

```python
# Test 1: Immediate retrieval after creation
session_id = await create_session()
session = await get_session(session_id)  # Must not be None!

# Test 2: Consistency across all stores
session_id = await create_session()
assert controller.get_session(session_id) is not None
assert await db.get_session(session_id) is not None

# Test 3: Cleanup rollback on DB failure
session_id = await create_session()
mock_db_error()
await stop_session(session_id)  # Should rollback
assert controller.get_session(session_id) is not None  # Still exists

# Test 4: No orphaned sessions
session_id = await create_session()
await stop_session(session_id)
assert controller.get_session(session_id) is None
assert (await db.get_session(session_id))['status'] == 'stopped'
```

---

## 📈 Success Metrics

After fixes, monitor:

| Metric | Current | Target |
|--------|---------|--------|
| Session lookup success rate | ~60% | 100% |
| "Session not found" errors | ~40% | 0% |
| Session creation latency P95 | 250ms | <100ms |
| Orphaned sessions | Unknown | 0 |
| Zombie sessions | Unknown | 0 |

---

## 📋 Implementation Checklist

### Sprint 16 Phase 3 (This Week)

- [ ] **Fix SESSION-002**: Persist to DB before returning session_id
  - [ ] Move QuestDB write to before in-memory creation
  - [ ] Add retry logic with exponential backoff
  - [ ] Update error handling

- [ ] **Fix SESSION-003**: Create unified SessionService
  - [ ] Create `session_service.py` with unified lookup
  - [ ] Update all endpoints to use SessionService
  - [ ] Add integration tests

- [ ] **Fix SESSION-004**: Add atomic cleanup with rollback
  - [ ] Wrap cleanup in try-finally
  - [ ] Add session backup before cleanup
  - [ ] Restore on DB failure

### Sprint 17 (Next Week)

- [ ] **Fix SESSION-001**: Make QuestDB single source of truth
  - [ ] Remove _active_sessions dict
  - [ ] Remove _current_session (or make it cache)
  - [ ] Query QuestDB for all lookups
  - [ ] Add caching layer with TTL

- [ ] **Fix SESSION-005**: Remove command_id fallback
  - [ ] Increase timeout to 15s
  - [ ] Remove execute_command fallback
  - [ ] Add proper error messages

---

## 🎯 Expected Impact

**Before Fixes**:
```
User: POST /sessions/start → session_id="exec_123"
User: GET /sessions/exec_123 → 404 "Session not found" ❌
```

**After Fixes**:
```
User: POST /sessions/start → session_id="exec_123"
User: GET /sessions/exec_123 → 200 OK with session data ✅
```

**Estimated Effort**: 2-3 days for Priority 1 fixes (SESSION-001 to SESSION-003)

---

## 📞 Next Steps

1. Review this analysis with team
2. Prioritize fixes (recommend: SESSION-002, SESSION-003, SESSION-004 first)
3. Create implementation tickets
4. Run E2E tests after each fix
5. Monitor metrics in production

---

**Full Analysis**: See `SESSION_LIFECYCLE_ANALYSIS.md` for complete details with code examples and line numbers.
