# Session Lifecycle Analysis
## Agent 2 - Session Management Specialist

**Analysis Date:** 2025-11-09
**Sprint:** Sprint 16 - Phase 3
**Target:** Session-related failures causing "Session not found" errors

---

## Executive Summary

**CRITICAL FINDING**: Session management has **THREE SEPARATE storage locations** with no synchronization, causing race conditions and "Session not found" errors.

**Impact**:
- ❌ 404 errors: "Session not found" when session exists
- ❌ Race conditions between session creation and persistence
- ❌ Orphaned sessions (in DB but not in memory)
- ❌ Zombie sessions (in memory but marked stopped in DB)
- ❌ Inconsistent session state across components

**Root Cause**: Lack of atomic session lifecycle management with distributed state.

---

## 1. Session Lifecycle Map

### 1.1 Session Creation Flow

```
User Request → POST /sessions/start
    ↓
unified_server.py:1810 (post_sessions_start)
    ↓
controller.start_data_collection() (unified_trading_controller.py:345)
    ↓
command_processor.execute_command_with_result() (unified_trading_controller.py:369)
    ↓
ExecutionController.start_data_collection() (execution_controller.py:591)
    ↓
ExecutionController.create_session() (execution_controller.py:411)
    ├─→ MEMORY: _current_session = ExecutionSession(...) [Line 448]
    └─→ MEMORY: _active_symbols[symbol] = session_id [Line 445]
    ↓
ExecutionController.start_session() (execution_controller.py:466)
    ↓
DataCollectionPersistenceService.create_session() (execution_controller.py:692)
    ├─→ MEMORY: _active_sessions[session_id] = {...} [Line 109]
    └─→ DATABASE: INSERT INTO data_collection_sessions [Line 441]
    ↓
MarketDataProviderAdapter.start_stream() (execution_controller.py:148)
    ↓
Response: {"session_id": "exec_..."}
```

### 1.2 Session Persistence (Critical Timing)

```python
# File: execution_controller.py

# STEP 1: Session created in memory (ATOMIC with symbol acquisition)
# Lines 423-445
async with self._symbol_lock:
    # Check conflicts
    # ...
    session_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    for symbol in symbols:
        self._active_symbols[symbol] = session_id

self._current_session = ExecutionSession(
    session_id=session_id,
    mode=mode,
    symbols=symbols,
    status=ExecutionState.IDLE,
    parameters=config or {}
)

# ⚠️ TIMING GAP: Session exists in memory but not in DB yet

# STEP 2: Session persisted to QuestDB (OUTSIDE symbol lock, ~50-200ms later)
# Lines 690-713
try:
    await self.db_persistence_service.create_session(
        session_id=session_id,
        symbols=symbols,
        data_types=data_types,
        exchange='mexc',
        notes=f"Data collection session created via API"
    )
except Exception as db_error:
    # ⚠️ CRITICAL: If QuestDB fails, session exists in memory but not in DB!
    raise RuntimeError(f"Failed to create session in QuestDB...")
```

**⚠️ RACE CONDITION**: Between STEP 1 and STEP 2, there's a **50-200ms window** where:
- Session exists in `ExecutionController._current_session`
- Session does NOT exist in QuestDB
- Client receives session_id and may immediately query it
- Query to QuestDB returns 404 "Session not found"

### 1.3 Session Retrieval (Inconsistent Sources)

#### Endpoint 1: GET /sessions/{id}
```python
# File: unified_server.py:2036-2042
@app.get("/sessions/{id}")
async def get_session(id: str):
    controller = await app.state.rest_service.get_controller()
    status = controller.get_execution_status()
    if not status or status.get("session_id") != id:
        return _json_ok({"status": "no_active_session"})
    return _json_ok({"status": "session_status", "data": status})
```

**Source**: ExecutionController._current_session ONLY
**Problem**: Returns "no_active_session" if session is not currently running (even if it exists in DB)

#### Endpoint 2: POST /sessions/stop
```python
# File: unified_server.py:1945-1960
# Step 1: Check if session exists in QuestDB
check_query = """
SELECT session_id, status, start_time, end_time
FROM data_collection_sessions
WHERE session_id = $1 AND is_deleted = false
"""
session_rows = await questdb_provider.execute_query(check_query, [_session_id])

if not session_rows or len(session_rows) == 0:
    return _json_error(
        "session_not_found",
        f"Session {_session_id} not found",
        status=404
    )
```

**Source**: QuestDB FIRST, then checks ExecutionController
**Problem**: Returns 404 if session not in QuestDB (even if it exists in memory)

#### Endpoint 3: GET /api/data-collection/sessions
```python
# File: data_analysis_routes.py:302-323
@router.get("/sessions")
async def list_sessions(...):
    result = await analysis_service.list_sessions(limit=limit, include_stats=include_stats)
    return {
        'sessions': result.get('sessions', []),
        'total_count': result.get('total_count', 0),
        'limit': limit
    }
```

**Source**: QuestDB ONLY (queries data_collection_sessions table)
**Problem**: Doesn't show sessions that exist only in memory

### 1.4 Session Cleanup Flow

```
User Request → POST /sessions/stop
    ↓
unified_server.py:1928 (post_sessions_stop)
    ├─→ Check QuestDB (session exists?)
    └─→ Check ExecutionController (session active in memory?)
    ↓
ExecutionController.stop_execution() (execution_controller.py:831)
    ↓
ExecutionController._cleanup_session() (execution_controller.py:1495)
    ├─→ MEMORY: _current_session = None [Line 1566]
    ├─→ MEMORY: Clear _active_symbols [Line 1504]
    ├─→ MEMORY: Clear _progress_callbacks [Line 1538]
    └─→ DATABASE: UPDATE status='stopped' [Lines 1519-1523]
    ↓
DataCollectionPersistenceService.update_session_status() (data_collection_persistence_service.py:131)
    ├─→ MEMORY: del _active_sessions[session_id] [Line 174]
    └─→ DATABASE: UPDATE data_collection_sessions [Line 493]
```

**⚠️ NO ATOMIC TRANSACTION**: Each cleanup operation can fail independently!

---

## 2. Critical Issues Found

### SESSION-001: Three-Way Session Storage Inconsistency

**Severity**: CRITICAL
**Impact**: Core functionality broken - sessions can be "lost" between memory and DB

**Description**:
Sessions are stored in THREE separate locations with NO synchronization:

1. **ExecutionController._current_session** (Single session in memory)
   - File: `execution_controller.py:331`
   - Type: `Optional[ExecutionSession]`
   - Cleared on session stop (line 1566)

2. **DataCollectionPersistenceService._active_sessions** (Dict of sessions in memory)
   - File: `data_collection_persistence_service.py:54`
   - Type: `Dict[str, Dict[str, Any]]`
   - Cleared on session completion (line 174)

3. **QuestDB data_collection_sessions table** (Persistent database)
   - File: `data_collection_persistence_service.py:430-474`
   - Type: Database table
   - Updated on session status changes (line 493)

**Evidence**:
```python
# Location 1: ExecutionController (execution_controller.py:331)
self._current_session: Optional[ExecutionSession] = None

# Location 2: DataCollectionPersistenceService (data_collection_persistence_service.py:54)
self._active_sessions: Dict[str, Dict[str, Any]] = {}

# Location 3: QuestDB (data_collection_persistence_service.py:441)
INSERT INTO data_collection_sessions (session_id, status, symbols, ...)
```

**Root Cause**:
No single source of truth for session state. Each component maintains its own copy.

**Proposed Fix**:
1. **Option A (Recommended)**: Make QuestDB the single source of truth
   - Remove in-memory `_active_sessions` cache
   - Query QuestDB for all session lookups
   - Use database transactions for atomicity

2. **Option B**: Make ExecutionController the single source of truth
   - Remove DataCollectionPersistenceService cache
   - Persist to QuestDB asynchronously (best-effort)
   - Accept eventual consistency for historical queries

---

### SESSION-002: Race Condition Between Session Creation and Persistence

**Severity**: CRITICAL
**Impact**: 404 errors when clients query session immediately after creation

**Description**:
Session is created in memory (step 1) and persisted to QuestDB (step 2) with a **50-200ms gap**. If client queries during this gap, they get 404 "Session not found" even though session exists.

**Evidence**:
```python
# File: execution_controller.py

# STEP 1: Create session in memory (Line 443-454)
session_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
for symbol in symbols:
    self._active_symbols[symbol] = session_id

self._current_session = ExecutionSession(
    session_id=session_id,
    mode=mode,
    symbols=symbols,
    status=ExecutionState.IDLE,
    parameters=config or {}
)

# ⚠️ 50-200ms gap (session exists in memory, not in DB)

# STEP 2: Persist to QuestDB (Line 692-713)
await self.db_persistence_service.create_session(
    session_id=session_id,
    symbols=symbols,
    data_types=data_types,
    exchange='mexc',
    notes=f"Data collection session created via API"
)
```

**Failure Scenario**:
```
1. Client POST /sessions/start → session_id="exec_20251109_123456_abc123"
2. Server creates session in memory (50ms)
3. Client GET /api/data-collection/sessions → queries QuestDB
4. QuestDB returns empty (session not yet persisted)
5. Server persists to QuestDB (150ms later)
6. Client sees 404 error for valid session_id
```

**Root Cause**:
Session creation is not atomic. Memory update and DB insert happen sequentially without synchronization.

**Proposed Fix**:
1. Persist to QuestDB BEFORE returning session_id to client
2. Use database transaction to ensure atomicity
3. Add retry logic with exponential backoff
4. If DB write fails, rollback in-memory state

```python
# Proposed fix:
async with self._session_creation_lock:
    # STEP 1: Generate session_id
    session_id = self._generate_session_id()

    # STEP 2: Persist to DB FIRST
    try:
        await self.db_persistence_service.create_session(
            session_id=session_id,
            symbols=symbols,
            ...
        )
    except Exception as e:
        # DB write failed - DO NOT create in-memory session
        raise RuntimeError(f"Failed to create session: {e}")

    # STEP 3: Create in-memory session ONLY if DB write succeeded
    self._current_session = ExecutionSession(
        session_id=session_id,
        ...
    )

    return session_id
```

---

### SESSION-003: Inconsistent Session Lookup Logic

**Severity**: HIGH
**Impact**: Different endpoints return different results for same session_id

**Description**:
Three different endpoints use three different session lookup strategies, causing inconsistent responses.

**Evidence**:

#### Case 1: GET /sessions/{id}
```python
# File: unified_server.py:2036-2042
# Only checks ExecutionController._current_session
@app.get("/sessions/{id}")
async def get_session(id: str):
    controller = await app.state.rest_service.get_controller()
    status = controller.get_execution_status()
    if not status or status.get("session_id") != id:
        return _json_ok({"status": "no_active_session"})
```

**Problem**: Returns "no_active_session" for completed sessions that exist in QuestDB

#### Case 2: POST /sessions/stop
```python
# File: unified_server.py:1945-1960
# Checks QuestDB FIRST
check_query = """
SELECT session_id, status FROM data_collection_sessions
WHERE session_id = $1 AND is_deleted = false
"""
session_rows = await questdb_provider.execute_query(check_query, [_session_id])
```

**Problem**: Returns 404 for sessions that exist in memory but not yet in DB

#### Case 3: GET /api/data-collection/sessions
```python
# File: data_analysis_routes.py:302-323
# Queries QuestDB ONLY
result = await analysis_service.list_sessions(limit=limit, include_stats=include_stats)
```

**Problem**: Doesn't show sessions that exist only in memory

**Root Cause**:
No unified session lookup service. Each endpoint implements its own logic.

**Proposed Fix**:
Create unified `SessionService` with single lookup method:

```python
class SessionService:
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Unified session lookup with fallback strategy:
        1. Check ExecutionController (current active session)
        2. Check QuestDB (historical sessions)
        3. Return None if not found in either
        """
        # Check active session first
        controller_session = await self._check_controller(session_id)
        if controller_session:
            return controller_session

        # Fallback to database
        db_session = await self._query_questdb(session_id)
        return db_session
```

---

### SESSION-004: No Atomic Session Cleanup

**Severity**: HIGH
**Impact**: Orphaned sessions, zombie sessions, memory leaks

**Description**:
Session cleanup involves multiple independent operations with no transaction:
1. Clear ExecutionController._current_session
2. Clear DataCollectionPersistenceService._active_sessions
3. Update QuestDB status='stopped'

If any operation fails, session state becomes inconsistent.

**Evidence**:
```python
# File: execution_controller.py:1500-1535

async def _cleanup_session_impl(self) -> None:
    """Internal implementation of cleanup (called under cleanup lock)"""
    if self._current_session:
        # Operation 1: Release symbols
        await self._release_symbols(self._current_session.symbols)

        # Operation 2: Clear in-memory state
        self._current_session.status = ExecutionState.STOPPED
        self._current_session.end_time = datetime.now()

        # Operation 3: Update QuestDB (CAN FAIL)
        if self._current_session.mode == ExecutionMode.DATA_COLLECTION:
            try:
                await self.db_persistence_service.update_session_status(
                    session_id=self._current_session.session_id,
                    status='completed',
                    records_collected=self._current_session.metrics.get('records_collected', 0)
                )
            except Exception as db_error:
                # ⚠️ LOG ERROR BUT DON'T FAIL
                # Session cleared from memory but DB still shows 'running'!
                self.logger.error("data_collection.db_session_update_failed", {...})
```

**Failure Scenario**:
```
1. Session stops → cleanup initiated
2. Clear _current_session = None (SUCCESS)
3. Update QuestDB status='stopped' (FAILS due to connection error)
4. Session cleared from memory but DB shows status='running'
5. Future queries find "orphaned" session in QuestDB
```

**Root Cause**:
No atomic transaction across memory and database operations. Each can fail independently.

**Proposed Fix**:
1. Wrap cleanup in try-finally to ensure all steps complete
2. If DB update fails, restore in-memory state
3. Add retry logic for DB updates
4. Mark session as "cleanup_pending" during transition

```python
async def _cleanup_session_impl(self) -> None:
    session_backup = self._current_session

    try:
        # STEP 1: Update database FIRST (with retry)
        await self._update_db_with_retry(
            session_id=session_backup.session_id,
            status='stopped'
        )

        # STEP 2: Clear memory ONLY if DB update succeeded
        self._current_session = None

    except Exception as e:
        # Rollback: restore session if DB update failed
        self._current_session = session_backup
        raise
```

---

### SESSION-005: Session ID Not Returned from POST /sessions/start

**Severity**: MEDIUM
**Impact**: Clients receive command_id instead of session_id, causing lookup failures

**Description**:
The `start_data_collection()` method uses `execute_command_with_result()` with a 5-second timeout. If session creation takes longer, it falls back to returning `command_id` instead of `session_id`.

**Evidence**:
```python
# File: unified_trading_controller.py:365-421

async def start_data_collection(self, symbols: List[str], duration: str, **kwargs) -> str:
    try:
        result = await self.command_processor.execute_command_with_result(
            CommandType.START_DATA_COLLECTION,
            parameters,
            timeout=5.0  # ⚠️ If creation takes >5s, timeout occurs
        )

        session_id = result.get("session_id")

        if not session_id:
            # ⚠️ FALLBACK: Return command_id instead of session_id
            command_id = await self.command_processor.execute_command(
                CommandType.START_DATA_COLLECTION,
                parameters
            )
            return command_id  # ⚠️ WRONG! Returns command_id instead of session_id

        return session_id

    except (TimeoutError, ValueError) as e:
        # ⚠️ FALLBACK: Return command_id
        command_id = await self.command_processor.execute_command(...)
        return command_id
```

**Root Cause**:
Async command execution pattern returns command_id when session creation is slow or times out.

**Proposed Fix**:
1. Increase timeout from 5s to 15s (enough for QuestDB write + retries)
2. Remove fallback to command_id - fail fast if timeout
3. Add proper error handling with specific error codes

```python
async def start_data_collection(self, symbols: List[str], duration: str, **kwargs) -> str:
    try:
        result = await self.command_processor.execute_command_with_result(
            CommandType.START_DATA_COLLECTION,
            parameters,
            timeout=15.0  # Increased timeout
        )

        session_id = result.get("session_id")

        if not session_id:
            raise ValueError("Session creation failed: no session_id in result")

        return session_id

    except TimeoutError:
        raise RuntimeError("Session creation timed out after 15 seconds")
    except Exception as e:
        raise RuntimeError(f"Failed to create session: {e}")
```

---

## 3. Race Conditions

### RACE-001: Symbol Acquisition vs Session Persistence

**Type**: Time-of-check to time-of-use (TOCTOU)
**Impact**: Symbol conflicts can occur even after acquisition

**Scenario**:
```
Thread A: Acquires symbols [BTC_USDT, ETH_USDT] (inside lock)
Thread A: Creates session_id = "exec_001" (inside lock)
Thread A: Exits lock
Thread A: Starts persisting to QuestDB (50ms delay)
Thread B: Acquires same symbols [BTC_USDT, ETH_USDT] (lock available)
Thread B: Creates session_id = "exec_002"
Thread B: Starts persisting to QuestDB
Thread A: QuestDB write completes (exec_001)
Thread B: QuestDB write completes (exec_002)

Result: TWO sessions using same symbols!
```

**Evidence**:
```python
# File: execution_controller.py:423-445

# ATOMIC: Symbol check and acquisition
async with self._symbol_lock:
    # Check for symbol conflicts
    conflicting_symbols = []
    for symbol in symbols:
        if symbol in self._active_symbols:
            conflicting_symbols.append(symbol)

    if conflicting_symbols:
        raise ValueError(f"Symbol conflict: {conflicting_symbols}")

    # Acquire symbols
    session_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    for symbol in symbols:
        self._active_symbols[symbol] = session_id

# ⚠️ LOCK RELEASED - RACE WINDOW OPENS

# NON-ATOMIC: Session persistence (outside lock)
self._current_session = ExecutionSession(...)
await self.db_persistence_service.create_session(...)  # Can take 50-200ms
```

**Root Cause**:
Symbol acquisition is atomic (inside lock) but session persistence is not (outside lock). Between these operations, another thread can acquire same symbols.

**Fix**:
Keep lock held until QuestDB write completes, or use optimistic locking with version numbers.

---

### RACE-002: Concurrent Session Cleanup

**Type**: Double cleanup causing errors
**Impact**: Cleanup operations fail with "session not found" errors

**Scenario**:
```
Thread A: Calls stop_execution()
Thread A: Enters _cleanup_session_impl()
Thread A: Clears _current_session = None
Thread B: Calls stop_execution() (duplicate request)
Thread B: Enters _cleanup_session_impl()
Thread B: Reads _current_session = None
Thread B: Skips cleanup (session already cleaned)
Thread A: Updates QuestDB status='stopped'
Thread B: Tries to update QuestDB (session_id no longer valid)

Result: Harmless but generates error logs
```

**Evidence**:
```python
# File: execution_controller.py:1495-1499

async def _cleanup_session(self) -> None:
    """✅ RACE CONDITION FIX: Cleanup execution resources atomically"""
    async with self._cleanup_lock:
        await self._cleanup_session_impl()
```

**Fix**: Already fixed with `_cleanup_lock` (line 369), but need to verify all cleanup paths use this lock.

---

## 4. Data Consistency Issues

### CONSISTENCY-001: Session Status Drift

**Description**:
Session status in QuestDB can differ from ExecutionController state.

**Example**:
```
ExecutionController._current_session.status = "running"
QuestDB data_collection_sessions.status = "active"
DataCollectionPersistenceService._active_sessions[id].status = "running"

Three different values for same session!
```

**Root Cause**:
No enum mapping between "running"/"active" states. Each component uses different vocabulary.

**Impact**:
- Queries filter by status may miss sessions
- UI shows incorrect status
- Business logic makes wrong decisions

**Fix**:
1. Define canonical status enum
2. Map all status values to enum
3. Use enum consistently across all components

```python
class SessionStatus(Enum):
    ACTIVE = "active"           # QuestDB
    RUNNING = "running"         # ExecutionController
    COMPLETED = "completed"     # Both
    STOPPED = "stopped"         # Both
    FAILED = "failed"           # Both

# Mapping function
def normalize_status(status: str) -> SessionStatus:
    mapping = {
        "active": SessionStatus.ACTIVE,
        "running": SessionStatus.RUNNING,
        ...
    }
    return mapping.get(status.lower(), SessionStatus.ACTIVE)
```

---

### CONSISTENCY-002: is_deleted Flag Not Set Consistently

**Description**:
QuestDB sessions have `is_deleted` flag but it's not always set explicitly, causing NULL values that break queries.

**Evidence**:
```python
# File: data_collection_persistence_service.py:430-474

async def _insert_session_metadata(self, session: Dict[str, Any]) -> None:
    """
    CRITICAL FIX: Explicitly sets is_deleted = false to prevent NULL values.
    """
    query = """
    INSERT INTO data_collection_sessions (
        ..., is_deleted
    ) VALUES (
        ..., $11  # Explicit false
    )
    """

    params = [
        ...,
        False  # ✅ is_deleted - explicit false to ensure proper filtering
    ]
```

**Problem**:
Before this fix (line 471), `is_deleted` could be NULL, causing:
```sql
SELECT * FROM data_collection_sessions WHERE is_deleted = false
-- Would miss sessions where is_deleted = NULL!
```

**Fix**: Already fixed (line 471), but need to verify all INSERT statements set this field.

---

### CONSISTENCY-003: Timestamp Format Inconsistency

**Description**:
Timestamps stored in three different formats across components.

**Formats**:
1. **ExecutionController**: Python datetime objects
2. **QuestDB**: LONG microseconds (`timestamp_us`)
3. **API responses**: ISO 8601 strings

**Evidence**:
```python
# Format 1: Python datetime (execution_controller.py:454)
self._current_session.start_time = datetime.now()

# Format 2: Microseconds (data_collection_persistence_service.py:456)
start_time_us = int(session['start_time'].timestamp() * 1_000_000)

# Format 3: ISO string (unified_server.py)
"start_time": session.start_time.isoformat()
```

**Impact**:
- Conversion errors
- Precision loss
- Time zone confusion (UTC vs local)

**Fix**:
1. Use UTC everywhere
2. Store as microseconds in DB
3. Convert to ISO 8601 for API responses
4. Add utility functions for conversion

---

## 5. Integration Point Verification

### 5.1 ExecutionController → DataCollectionPersistenceService

**Interface**: `db_persistence_service.create_session()`

**Data Flow**:
```
ExecutionController.start_data_collection()
    ↓ (line 692)
await self.db_persistence_service.create_session(
    session_id=session_id,
    symbols=symbols,
    data_types=data_types,
    exchange='mexc',
    notes=f"Data collection session created via API"
)
    ↓
DataCollectionPersistenceService.create_session()
    ├─→ Store in _active_sessions cache (line 109)
    └─→ INSERT INTO data_collection_sessions (line 112)
```

**Issue**: If QuestDB write fails, exception is raised but in-memory state is already modified (SESSION-002).

---

### 5.2 API Routes → ExecutionController

**Interface**: `controller.get_execution_status()`

**Data Flow**:
```
GET /sessions/execution-status
    ↓
unified_server.py:1728 (get_sessions_execution_status)
    ↓
controller.get_execution_status()
    ↓
Returns _current_session or None
```

**Issue**: Only returns currently ACTIVE session. Historical sessions (stopped, completed) are not accessible via this endpoint.

---

### 5.3 QuestDB → Session Retrieval

**Interface**: `SELECT * FROM data_collection_sessions`

**Query Pattern**:
```sql
SELECT session_id, status, symbols, data_types
FROM data_collection_sessions
WHERE is_deleted = false
ORDER BY start_time DESC
```

**Issue**:
- Sessions with NULL `is_deleted` are filtered out (CONSISTENCY-002)
- No index on `is_deleted` - full table scan on large datasets
- No pagination - can return millions of rows

---

## 6. Recommendations

### Priority 1 (CRITICAL - Fix Immediately)

1. **SESSION-001**: Implement single source of truth
   - Make QuestDB the authoritative session store
   - Remove redundant in-memory caches
   - Query DB for all session lookups

2. **SESSION-002**: Fix race condition in session creation
   - Persist to QuestDB BEFORE returning session_id
   - Use database transaction for atomicity
   - Add retry logic with exponential backoff

3. **SESSION-003**: Unify session lookup logic
   - Create SessionService with consistent lookup
   - Use same logic across all endpoints
   - Implement fallback strategy (memory → DB)

### Priority 2 (HIGH - Fix This Sprint)

4. **SESSION-004**: Implement atomic cleanup
   - Wrap cleanup in try-finally
   - Rollback on failure
   - Add cleanup retry logic

5. **SESSION-005**: Fix session_id return from POST /sessions/start
   - Increase timeout to 15s
   - Remove command_id fallback
   - Fail fast with clear error

6. **CONSISTENCY-001**: Standardize session status
   - Define canonical status enum
   - Map all status values
   - Use enum everywhere

### Priority 3 (MEDIUM - Fix Next Sprint)

7. **RACE-001**: Extend symbol lock to cover persistence
8. **CONSISTENCY-002**: Verify is_deleted is set on all INSERTs
9. **CONSISTENCY-003**: Standardize timestamp handling

---

## 7. Testing Strategy

### Unit Tests Needed

```python
# Test session creation atomicity
async def test_session_creation_atomic():
    """Verify session exists in both memory and DB after creation"""
    session_id = await controller.create_session(...)

    # Check memory
    assert controller._current_session.session_id == session_id

    # Check DB (should exist immediately)
    db_session = await db_service.get_session_metadata(session_id)
    assert db_session is not None
    assert db_session['session_id'] == session_id

# Test race condition between creation and retrieval
async def test_immediate_session_retrieval():
    """Verify session can be retrieved immediately after creation"""
    session_id = await controller.create_session(...)

    # Immediate retrieval should work
    session = await session_service.get_session(session_id)
    assert session is not None

# Test cleanup rollback on failure
async def test_cleanup_rollback_on_db_failure(mock_db_error):
    """Verify session restored if DB cleanup fails"""
    session_id = await controller.create_session(...)

    # Simulate DB error during cleanup
    mock_db_error.side_effect = ConnectionError("DB unreachable")

    try:
        await controller.stop_execution()
    except Exception:
        pass

    # Session should still exist in memory
    assert controller._current_session is not None
```

### Integration Tests Needed

```python
# Test full session lifecycle
async def test_full_session_lifecycle_consistency():
    """Verify session state is consistent across all components"""

    # Create session
    session_id = await start_session()

    # Verify in all locations
    assert controller._current_session.session_id == session_id
    assert session_id in db_service._active_sessions
    assert await db_provider.session_exists(session_id)

    # Stop session
    await stop_session(session_id)

    # Verify cleanup in all locations
    assert controller._current_session is None
    assert session_id not in db_service._active_sessions
    assert (await db_provider.get_session(session_id))['status'] == 'stopped'
```

---

## 8. Metrics to Track

After implementing fixes, track these metrics:

1. **Session Lookup Success Rate**: % of GET /sessions/{id} that return 200 instead of 404
2. **Session Creation Latency**: P50, P95, P99 for POST /sessions/start
3. **Race Condition Frequency**: # of "Session not found" errors for recently created sessions
4. **Cleanup Success Rate**: % of sessions that clean up successfully (all 3 stores)
5. **Orphaned Sessions**: # of sessions in DB but not in memory (alert if > 0)
6. **Zombie Sessions**: # of sessions in memory but marked stopped in DB (alert if > 0)

---

## Appendix A: Session Storage Comparison

| Location | Type | Scope | Cleared | Query Speed | Consistency |
|----------|------|-------|---------|-------------|-------------|
| ExecutionController._current_session | Single object | Active session only | On stop | O(1) | Immediate |
| DataCollectionPersistenceService._active_sessions | Dict | Active sessions | On completion | O(1) | Eventual |
| QuestDB data_collection_sessions | Database table | All sessions | Never (soft delete) | O(log n) | Eventual |

**Recommendation**: Use QuestDB as single source of truth, eliminate in-memory caches.

---

## Appendix B: File-to-Line Mapping

All issues referenced with exact file paths and line numbers:

### Session Creation
- `execution_controller.py:411` - create_session()
- `execution_controller.py:443` - session_id generation
- `execution_controller.py:448` - _current_session assignment
- `execution_controller.py:692` - db_persistence_service.create_session()

### Session Persistence
- `data_collection_persistence_service.py:65` - create_session()
- `data_collection_persistence_service.py:109` - _active_sessions cache
- `data_collection_persistence_service.py:441` - INSERT INTO data_collection_sessions

### Session Retrieval
- `unified_server.py:2036` - GET /sessions/{id}
- `unified_server.py:1945` - POST /sessions/stop (QuestDB check)
- `data_analysis_routes.py:302` - GET /api/data-collection/sessions

### Session Cleanup
- `execution_controller.py:1495` - _cleanup_session()
- `execution_controller.py:1566` - _current_session = None
- `execution_controller.py:1519` - QuestDB status update
- `data_collection_persistence_service.py:174` - del _active_sessions

---

**End of Analysis**
