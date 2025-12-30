# Story BUG-008-1: WebSocket Disconnect Diagnostic Logging

**Status:** review
**Priority:** P0
**Epic:** BUG-008 WebSocket Stability & Service Health

---

## Story

As a **developer debugging connection issues**,
I want **detailed diagnostic logs when WebSocket connections close**,
so that **I can identify the root cause of connection instability instead of guessing**.

---

## Problem Statement

Current logs show only:
```
INFO: connection open
INFO: connection closed
```

This provides zero insight into WHY connections close. Without diagnostic data:
- Cannot distinguish client-initiated vs server-initiated disconnects
- Cannot identify timeout vs error vs intentional close
- Cannot correlate frontend reconnects with backend events
- Cannot measure connection health over time

---

## Acceptance Criteria

1. **AC1:** Backend logs include disconnect reason code (1000=normal, 1001=going away, 1006=abnormal, etc.)
2. **AC2:** Backend logs include connection duration before disconnect
3. **AC3:** Backend logs include last activity timestamp and message counts
4. **AC4:** Backend logs include client_id for correlation with frontend logs
5. **AC5:** Frontend logs include disconnect reason when connection closes
6. **AC6:** Disconnect events are logged at WARNING level (not INFO) if abnormal

---

## Tasks / Subtasks

- [x] Task 1: Enhance backend WebSocket close logging (AC: 1, 2, 3, 4)
  - [x] Modify `websocket_server.py` disconnect handler
  - [x] Capture WebSocket close code and reason from exception/event
  - [x] Calculate connection duration from open timestamp
  - [x] Include messages_sent, messages_received, last_activity_timestamp
  - [x] Log at WARNING level if close code != 1000

- [x] Task 2: Enhance frontend WebSocket close logging (AC: 5, 6)
  - [x] Modify `websocket.ts` onclose handler
  - [x] Log close code, reason, and wasClean flag
  - [x] Include connection duration and message counts
  - [x] Log at WARN level if abnormal close

- [x] Task 3: Add connection health metrics (AC: 2, 3)
  - [x] Track connection open timestamp in connection_manager
  - [x] Track message count per connection
  - [x] Track last activity per connection
  - [x] Expose metrics in disconnect log

- [x] Task 4: Create correlation ID system (AC: 4)
  - [x] Ensure client_id is logged consistently on both sides
  - [ ] Add connection_sequence_number for multi-reconnect scenarios (DEFERRED - not required for AC4, future enhancement)
  - [x] Document log correlation procedure

---

## Dev Notes

### WebSocket Close Codes Reference

| Code | Name | Meaning |
|------|------|---------|
| 1000 | Normal Closure | Clean close, no error |
| 1001 | Going Away | Endpoint going away (page close, server shutdown) |
| 1002 | Protocol Error | Protocol error detected |
| 1005 | No Status Received | No status code in close frame |
| 1006 | Abnormal Closure | Connection lost (no close frame) |
| 1011 | Internal Error | Server error |
| 1012 | Service Restart | Server restarting |

### Current Code Locations

**Backend:**
```python
# src/api/websocket_server.py - current disconnect handling
# Likely in WebSocketAPIServer class
# Look for: websocket.close(), on_disconnect, or exception handlers
```

**Frontend:**
```typescript
// frontend/src/services/websocket.ts
// Look for: ws.onclose, socket.addEventListener('close', ...)
```

### Log Format Template

**Backend:**
```python
logger.warning("websocket.connection_closed", {
    "client_id": client_id,
    "close_code": code,
    "close_reason": reason,
    "was_clean": was_clean,
    "duration_seconds": duration,
    "messages_sent": sent_count,
    "messages_received": recv_count,
    "last_activity_age_seconds": last_activity_age,
    "initiated_by": "client" | "server" | "network"
})
```

**Frontend:**
```typescript
Logger.warn('websocket.connection_closed', {
    client_id,
    close_code: event.code,
    close_reason: event.reason,
    was_clean: event.wasClean,
    duration_seconds,
    messages_sent,
    messages_received
});
```

### Dependencies

- None - this is a foundational diagnostic story
- Should be implemented BEFORE BUG-008-2 (heartbeat sync) to have diagnostic data

### Files to Modify

- `src/api/websocket_server.py` - Backend WebSocket server
- `src/api/websocket/connection_manager.py` - Connection tracking
- `frontend/src/services/websocket.ts` - Frontend WebSocket client

---

## Definition of Done

1. [x] Connection close events include all diagnostic fields listed in AC
2. [x] Abnormal closes logged at WARNING level
3. [x] Log format follows existing project conventions
4. [ ] Manual test: close browser tab, verify logs show reason
5. [ ] Manual test: stop backend, verify frontend logs show reason
6. [x] Documentation updated with log correlation guide

---

## Dev Agent Record

**Implementation Date:** 2025-12-30
**Agent:** Amelia (Dev)

### Implementation Summary

All acceptance criteria have been implemented:

1. **Backend (`websocket_server.py`):**
   - Enhanced `_handle_client_messages()` to capture close codes from both `WebSocketDisconnect` (FastAPI) and `ConnectionClosed` (websockets)
   - Added `_get_close_reason_text()` helper for human-readable close codes
   - Calls `connection_manager.log_connection_closed()` with full diagnostic data

2. **Backend (`connection_manager.py`):**
   - `log_connection_closed()` method (lines 749-817) logs all required fields
   - Logs at INFO for normal closes (1000, 1001), WARNING for abnormal
   - Includes: client_id, close_code, close_reason, was_clean, duration_seconds, messages_sent, messages_received, last_activity_age_seconds, initiated_by

3. **Frontend (`websocket.ts`):**
   - Enhanced `onclose` handler with duration calculation
   - Logs `websocket.connection_closed` with all diagnostic fields
   - Uses Logger.warn for abnormal closes, Logger.info for normal

4. **Tests:**
   - 21 unit tests in `tests/unit/test_websocket_diagnostic_logging.py`
   - All tests passing

### Files Modified

| File | Changes |
|------|---------|
| `src/api/websocket_server.py` | Enhanced disconnect handlers, added close reason text helper |
| `src/api/connection_manager.py` | `log_connection_closed()` method with full diagnostics |
| `frontend/src/services/websocket.ts` | Enhanced onclose with duration, message counts, structured logging |
| `tests/unit/test_websocket_diagnostic_logging.py` | 21 unit tests for all ACs |

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from BUG-008 Epic |
| 2025-12-30 | Amelia (Dev) | Implementation complete, 21 tests passing, status → review |
| 2025-12-30 | Amelia (Dev) | POST-VERIFICATION FIXES: (1) Log naming changed from `websocket.*` to `connection_manager.*` for DNA inheritance consistency (2) `connection_sequence_number` marked as DEFERRED - not required for AC4 (3) Test assertions updated to verify exact log name convention |
