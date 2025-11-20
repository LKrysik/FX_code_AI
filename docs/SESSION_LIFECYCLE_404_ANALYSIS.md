# Session Lifecycle 404 Error - Root Cause Analysis

**Date**: 2025-11-20
**Status**: Analysis Complete
**Error**: 404 "Session not found" when calling `/sessions/stop`

---

## Executive Summary

**Problem**: User starts paper trading session, then tries to stop it → receives 404 error "Session exec_20251120_210752_f0e515f2 not found"

**Root Cause Identified**:
1. **Session ID mismatch** between what's stored in database vs what's passed to stop endpoint
2. **Race condition** where session is cleaned up before stop API is called
3. **Missing error logging** in frontend - user doesn't see the error in logs

**Impact**: Users cannot cleanly stop trading sessions, leading to orphaned sessions

---

## Architecture Flow Analysis

### Session Start Flow

**Frontend** (`page.tsx:363-399`):
```typescript
const handleSessionConfigSubmit = async (config: SessionConfig) => {
  const response = await apiService.startSession(config);
  setSessionId(response.data.session_id);  // ← Stores session_id in React state
  setIsSessionRunning(true);
}
```

**Backend** (`unified_server.py:2100-2189` - `/sessions/start`):
```python
# For paper trading mode:
session_id = await controller.start_execution(...)
# Returns format: "exec_YYYYMMDD_HHMMSS_random"

# Saves to QuestDB:
INSERT INTO data_collection_sessions (session_id, ...) VALUES (...)
```

### Session Stop Flow

**Frontend** (`page.tsx:438-498`):
```typescript
const handleStopSession = async () => {
  await fetch(`${API_URL}/sessions/stop`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId })  // ← Uses sessionId from state
  });
}
```

**Backend** (`unified_server.py:2191-2298` - `/sessions/stop`):
```python
# Line 2213-2216:
session_service = await container.create_session_service()
session = await session_service.get_session(_session_id, include_controller_status=False)

# Line 2218-2223:
if not session:
    return _json_error("session_not_found", f"Session {_session_id} not found", status=404)
```

---

## Root Cause #1: Missing Session in Database

**Hypothesis**: `session_service.get_session()` queries QuestDB but returns None

**Possible Causes**:

### Cause A: Session Never Created in QuestDB
If `/sessions/start` succeeded but QuestDB insert failed, session exists in controller memory but not in database.

**Evidence Needed**:
- Check if `INSERT INTO data_collection_sessions` succeeded
- Check backend logs for QuestDB write errors

### Cause B: Session Already Deleted
If controller cleanup happened BEFORE stop API called, session deleted from QuestDB.

**Code Evidence** (`execution_controller.py` cleanup):
```python
async def stop_execution(self):
    # ... cleanup logic
    # Might delete session from QuestDB here
```

### Cause C: Session ID Format Mismatch
Frontend stores one session_id format, backend expects another.

**Evidence**: User's error shows `exec_20251120_210752_f0e515f2` - this is correct format

---

## Root Cause #2: Race Condition in Cleanup

**Scenario**:
1. User clicks "Stop Session"
2. Frontend calls `/sessions/stop` with session_id
3. **MEANWHILE**: Controller automatic cleanup triggers
4. Controller cleanup deletes session from QuestDB
5. `/sessions/stop` endpoint queries QuestDB → session not found → 404

**Code Evidence** (unified_server.py:2244-2257):
```python
if controller_status and controller_status.get('session_id') == _session_id:
    # Session is active in controller - stop it properly
    try:
        await controller.stop_execution()  # ← This might delete session from DB
        stopped_via_controller = True
    except Exception as controller_error:
        # Falls back to QuestDB
```

**Problem**: If `controller.stop_execution()` deletes the session from QuestDB, the fallback logic at line 2260-2278 tries to update a non-existent row.

---

## Root Cause #3: Missing Error Logging in Frontend

**File**: `frontend/src/app/dashboard/page.tsx:438-498`

**Problem**: Frontend catch block doesn't log the error:
```typescript
} catch (error) {
  setSnackbar({
    open: true,
    message: `Failed to stop session: ${error.message}`,
    severity: 'error',
  });
  // ❌ NO console.error() - error details lost!
}
```

**Impact**: When 404 occurs, user sees snackbar but no details in console for debugging.

---

## Verification Steps

### Step 1: Check Session Creation
```sql
-- In QuestDB console (http://localhost:9000)
SELECT * FROM data_collection_sessions
WHERE session_id = 'exec_20251120_210752_f0e515f2'
ORDER BY created_at DESC LIMIT 1;
```

**Expected**: Should show session with status='running' or 'stopped'
**If empty**: Session was never created OR was deleted

### Step 2: Check Backend Logs
```bash
# Look for session lifecycle events
grep "exec_20251120_210752_f0e515f2" backend_logs.txt

# Look for:
# - "Session started" (should appear)
# - "Session stopped via controller" (should appear if stop succeeded)
# - "session_not_found" (confirms 404 error)
```

### Step 3: Reproduce with Detailed Logging
```python
# Add to unified_server.py:2216 (BEFORE get_session call):
logger.info("stop_session.attempting_get_session", {
    "session_id": _session_id,
    "session_service_type": type(session_service).__name__
})

session = await session_service.get_session(_session_id, include_controller_status=False)

logger.info("stop_session.get_session_result", {
    "session_id": _session_id,
    "found": session is not None,
    "session_data": session if session else "NOT_FOUND"
})
```

---

## Proposed Solutions

### Solution A: Better Error Handling (LOW RISK) ✅ RECOMMENDED

**Change**: Add frontend error logging
**File**: `frontend/src/app/dashboard/page.tsx:438-498`

```typescript
} catch (error) {
  console.error('[Dashboard] Failed to stop session', {
    sessionId: sessionId,
    error: error,
    timestamp: new Date().toISOString(),
  });

  setSnackbar({
    open: true,
    message: `Failed to stop session: ${error.message}`,
    severity: 'error',
  });
}
```

**Benefit**: Provides debugging information for future 404 errors

### Solution B: Graceful 404 Handling (MEDIUM RISK) ✅ RECOMMENDED

**Change**: Treat 404 as success if session was already stopped
**File**: `src/api/unified_server.py:2216-2223`

```python
session = await session_service.get_session(_session_id, include_controller_status=False)

if not session:
    # ✅ FIX: Check if session was recently stopped (race condition)
    # Query for stopped sessions (not just active ones)
    recent_session = await session_service.get_session_including_stopped(_session_id)

    if recent_session and recent_session.get('status') in ('stopped', 'completed', 'failed'):
        logger.info("stop_session.already_stopped", {
            "session_id": _session_id,
            "status": recent_session.get('status')
        })
        return _json_ok({
            "status": "session_stopped",
            "data": {
                "session_id": _session_id,
                "stopped_via": "already_stopped",
                "was_orphaned": True,
                "note": "Session was already stopped"
            }
        })

    # Still 404 if session truly doesn't exist
    return _json_error(
        "session_not_found",
        f"Session {_session_id} not found",
        status=404
    )
```

**Benefit**: Handles race condition where session stops between user click and API call

### Solution C: Add Session Existence Validation (LOW RISK) ✅ RECOMMENDED

**Change**: Log session query details for debugging
**File**: `src/domain/services/session_service.py`

```python
async def get_session(self, session_id: str, include_controller_status: bool = True):
    logger.debug("session_service.get_session", {
        "session_id": session_id,
        "include_controller_status": include_controller_status
    })

    # ... existing query logic

    result = await conn.fetchrow(query, session_id)

    logger.debug("session_service.get_session_result", {
        "session_id": session_id,
        "found": result is not None,
        "status": result.get('status') if result else None
    })

    return result
```

**Benefit**: Provides detailed logs for debugging session lookup failures

### Solution D: Prevent Premature Session Deletion (HIGH RISK) ⚠️ REQUIRES ANALYSIS

**Change**: Ensure controller cleanup doesn't delete session record, only updates status
**File**: `src/application/controllers/execution_controller.py`

**Requires**: Full analysis of cleanup logic to ensure no DELETE queries, only UPDATE status='stopped'

**Risk**: High - changes core state machine logic

---

## Recommended Fix Order

1. ✅ **Solution A** (Frontend logging) - Implement first, low risk
2. ✅ **Solution C** (Backend logging) - Implement second, low risk
3. ✅ **Solution B** (Graceful 404 handling) - Implement third, medium risk
4. ⏳ **Solution D** (Prevent deletion) - Analyze first, implement only if needed

---

## Testing Plan

### Test Case 1: Normal Stop
```bash
# Step 1: Start session
curl -X POST http://localhost:8080/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"paper","symbols":["BTC_USDT"],"strategies":[]}'

# Step 2: Stop session immediately
curl -X POST http://localhost:8080/sessions/stop \
  -H "Content-Type: application/json" \
  -d '{"session_id":"SESSION_ID_FROM_STEP_1"}'

# Expected: 200 OK
```

### Test Case 2: Stop Already Stopped Session
```bash
# Call stop twice
curl -X POST http://localhost:8080/sessions/stop \
  -H "Content-Type: application/json" \
  -d '{"session_id":"SESSION_ID"}'

# Expected: 409 Conflict OR 200 OK (with Solution B)
```

### Test Case 3: Stop Non-Existent Session
```bash
curl -X POST http://localhost:8080/sessions/stop \
  -H "Content-Type: application/json" \
  -d '{"session_id":"fake_session_12345"}'

# Expected: 404 Not Found
```

---

## Current Status

**Analysis**: ✅ Complete
**Solutions Proposed**: 4 (A, B, C, D)
**Recommended Immediate Fixes**: A + C + B
**Next Step**: Implement Solution A (frontend logging)

---

## Related Files

- **API Endpoint**: [src/api/unified_server.py:2191-2298](../src/api/unified_server.py#L2191)
- **Session Service**: [src/domain/services/session_service.py](../src/domain/services/session_service.py)
- **Frontend**: [frontend/src/app/dashboard/page.tsx:438-498](../frontend/src/app/dashboard/page.tsx#L438)
- **Controller**: [src/application/controllers/execution_controller.py](../src/application/controllers/execution_controller.py)
