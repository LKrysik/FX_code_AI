# Story BUG-008-1a: Chaos Monkey Manual Testing

**Status:** in-progress
**Priority:** P0 (Blocker for BUG-008-1 closure)
**Epic:** BUG-008 WebSocket Stability & Service Health
**Parent Story:** BUG-008-1 (WebSocket Disconnect Diagnostic Logging)

---

## Story

As a **QA engineer**,
I want **to manually verify all WebSocket disconnect scenarios produce correct logs**,
so that **we can confirm the diagnostic logging works in real-world conditions before closing BUG-008-1**.

---

## Background

Story BUG-008-1 implemented WebSocket disconnect diagnostic logging with 21 passing unit tests. However, the Definition of Done includes manual testing requirements that were not completed:

- **DoD 4:** Manual test: close browser tab, verify logs show reason
- **DoD 5:** Manual test: stop backend, verify frontend logs show reason

The Dev Agent (Amelia) verification using Chaos Monkey method (#38) confirmed code handles all scenarios, but real-world testing is required.

---

## Acceptance Criteria

1. **AC1:** Browser tab close produces backend log with `close_code: 1001` (Going away)
2. **AC2:** Backend shutdown produces frontend log with `close_code: 1006` (Abnormal)
3. **AC3:** Network disconnect produces logs with `close_code: 1006` and `initiated_by: network`
4. **AC4:** Heartbeat timeout (wait 3+ missed pongs) produces reconnect logs
5. **AC5:** Manual disconnect via `wsService.disconnect()` produces `close_code: 1000`
6. **AC6:** All scenarios show correct log level (INFO for 1000/1001, WARN for others)

---

## Test Scenarios

### Scenario 1: Browser Tab Close (AC1)
**Steps:**
1. Start backend server
2. Open frontend dashboard in browser
3. Verify WebSocket connection established (check console for `websocket.connection_opened`)
4. Close the browser tab (Ctrl+W or click X)
5. Check backend logs

**Expected Result:**
```
level: INFO
event_type: websocket.connection_closed
close_code: 1001
close_reason: Going away
was_clean: true
```

### Scenario 2: Backend Shutdown (AC2)
**Steps:**
1. Start backend server
2. Open frontend dashboard
3. Verify connection established
4. Stop backend (Ctrl+C)
5. Check browser console logs

**Expected Result:**
```
level: WARN
event_type: websocket.connection_closed
close_code: 1006
close_reason: Abnormal closure
was_clean: false
```

### Scenario 3: Network Disconnect (AC3)
**Steps:**
1. Establish connection
2. Disable network adapter (or use browser DevTools to throttle to "Offline")
3. Wait for timeout
4. Check both frontend and backend logs

**Expected Result:**
- Backend: `initiated_by: network`, `close_code: 1006`
- Frontend: `close_code: 1006`

### Scenario 4: Heartbeat Timeout (AC4)
**Steps:**
1. Establish connection
2. In backend, add artificial delay to pong handler (or pause backend process)
3. Wait for 3 missed pongs (90+ seconds with default config)
4. Check frontend logs

**Expected Result:**
```
websocket.heartbeat_missed_pong { missedPongs: 1 }
websocket.heartbeat_missed_pong { missedPongs: 2 }
websocket.heartbeat_missed_pong { missedPongs: 3 }
websocket.connection_closed { close_code: 1006 }
```

### Scenario 5: Manual Disconnect (AC5)
**Steps:**
1. Establish connection
2. Open browser console
3. Run: `window.wsService.disconnect()` (or equivalent)
4. Check logs

**Expected Result:**
```
level: INFO
close_code: 1000
close_reason: Client disconnect
was_clean: true
```

### Scenario 6: Protocol Error (AC6 - optional)
**Steps:**
1. Establish connection
2. Use WebSocket testing tool to send malformed message
3. Check logs

**Expected Result:**
```
close_code: 1002 or 1003
level: WARN
```

---

## Tasks / Subtasks

- [ ] Task 1: Setup test environment
  - [ ] Ensure backend logging is set to DEBUG level
  - [ ] Enable browser console logging
  - [ ] Prepare log collection method (tail -f, browser DevTools)

- [ ] Task 2: Execute Scenario 1 - Browser Tab Close
  - [ ] Run test steps
  - [ ] Capture backend logs
  - [ ] Verify close_code 1001
  - [ ] Document result with screenshot

- [ ] Task 3: Execute Scenario 2 - Backend Shutdown
  - [ ] Run test steps
  - [ ] Capture frontend console logs
  - [ ] Verify close_code 1006
  - [ ] Document result with screenshot

- [ ] Task 4: Execute Scenario 3 - Network Disconnect
  - [ ] Run test steps
  - [ ] Capture both logs
  - [ ] Verify initiated_by field
  - [ ] Document result

- [ ] Task 5: Execute Scenario 4 - Heartbeat Timeout
  - [ ] Run test steps
  - [ ] Verify missed pong progression
  - [ ] Document result

- [ ] Task 6: Execute Scenario 5 - Manual Disconnect
  - [ ] Run test steps
  - [ ] Verify close_code 1000
  - [ ] Document result

- [ ] Task 7: Create test report
  - [ ] Compile all results
  - [ ] Note any discrepancies
  - [ ] Update BUG-008-1 DoD items 4 & 5

---

## Definition of Done

1. [ ] All 5 mandatory scenarios executed
2. [ ] All scenarios produce expected log output
3. [ ] Screenshots/log captures documented
4. [ ] BUG-008-1 DoD items 4 & 5 marked complete
5. [ ] BUG-008-1 status changed from `review` to `done`

---

## Notes

- This story is a **testing task**, not implementation
- Should be quick (30-60 min) if environment is ready
- Any failing scenarios should create bug tickets, not block this story
- Can be parallelized with other BUG-008 work

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from Dev Agent verification report |
| 2025-12-30 | Amelia (Dev) | Verified logging configuration (FE+BE), created test checklist |

---

## Dev Agent Record

### Pre-Test Verification (2025-12-30)

**Logging Configuration Verified:**

| Component | Event Type | File:Line |
|-----------|------------|-----------|
| Frontend | `websocket.connection_opened` | `websocket.ts:169-173` |
| Frontend | `websocket.connection_closed` | `websocket.ts:196-211` |
| Backend | `connection_manager.connection_closed` | `connection_manager.py:815-817` |
| Backend | Close code capture | `websocket_server.py:1004-1016` |

**Fields Logged:**
- `close_code` (1000, 1001, 1006, etc.)
- `close_reason` (human-readable text)
- `was_clean` (boolean)
- `duration_seconds`
- `messages_sent` / `messages_received`
- `initiated_by` (client/server/network)

**Log Level Selection:**
- INFO for normal closes (1000, 1001)
- WARN for abnormal closes (1006, etc.)

### Test Execution Checklist

Created `bug-008-1a-test-checklist.md` with:
- Pre-test setup commands (backend, frontend, log monitoring)
- 5 test scenarios with step-by-step instructions
- Expected vs actual result capture forms
- Summary table for all ACs

---

## File List

**New Files:**
- `_bmad-output/stories/bug-008-1a-test-checklist.md` - Manual test execution checklist

**Verified Files (no changes):**
- `frontend/src/services/websocket.ts` - Frontend logging OK
- `src/api/websocket_server.py` - Backend close code capture OK
- `src/api/connection_manager.py` - Backend logging OK
