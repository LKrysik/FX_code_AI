# BUG-008-1a Manual Test Execution Checklist

**Story:** Chaos Monkey Manual Testing
**Date:** ____________________
**Tester:** ____________________

---

## Pre-Test Setup

### Terminal 1: Backend Server
```bash
cd C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --log-level debug
```

### Terminal 2: Frontend Dev Server
```bash
cd C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2\frontend
npm run dev
```

### Terminal 3: Log Monitoring (Backend)
```bash
# Watch backend logs for WebSocket events
# On Windows PowerShell:
Get-Content -Path logs\backend.log -Wait -Tail 50 | Select-String "connection_closed|connection_opened"

# Or use grep if available:
tail -f logs/backend.log | grep -E "connection_closed|connection_opened"
```

### Browser Setup
1. Open Chrome/Edge at `http://localhost:3000`
2. Open DevTools (F12) > Console tab
3. Filter console by: `websocket`

---

## Test Scenarios

### Scenario 1: Browser Tab Close (AC1)
**Expected:** Backend log with `close_code: 1001`

| Step | Action | Done |
|------|--------|------|
| 1 | Verify WebSocket connected (console shows `websocket.connection_opened`) | [ ] |
| 2 | Close browser tab (Ctrl+W or click X) | [ ] |
| 3 | Check backend logs | [ ] |

**Backend Log Expected:**
```json
{
  "event_type": "connection_manager.connection_closed",
  "level": "INFO",
  "close_code": 1001,
  "close_reason": "Going away",
  "was_clean": true
}
```

**Actual Result:**
```
close_code: ______
close_reason: ______________________
was_clean: ______
level: ______
```

**Pass/Fail:** [ ] PASS  [ ] FAIL

---

### Scenario 2: Backend Shutdown (AC2)
**Expected:** Frontend log with `close_code: 1006`

| Step | Action | Done |
|------|--------|------|
| 1 | Verify WebSocket connected | [ ] |
| 2 | Stop backend server (Ctrl+C in Terminal 1) | [ ] |
| 3 | Check browser console logs | [ ] |

**Frontend Console Expected:**
```
[WARN] websocket.connection_closed {
  close_code: 1006,
  close_reason: "Abnormal closure",
  was_clean: false
}
```

**Actual Result:**
```
close_code: ______
close_reason: ______________________
was_clean: ______
level: ______
```

**Pass/Fail:** [ ] PASS  [ ] FAIL

---

### Scenario 3: Network Disconnect (AC3)
**Expected:** Both logs show `close_code: 1006`, `initiated_by: network`

| Step | Action | Done |
|------|--------|------|
| 1 | Verify WebSocket connected | [ ] |
| 2 | Open DevTools > Network tab | [ ] |
| 3 | Click "Offline" checkbox (or throttle to "Offline") | [ ] |
| 4 | Wait 30-60 seconds for timeout | [ ] |
| 5 | Check both frontend and backend logs | [ ] |

**Frontend Console Expected:**
```
[WARN] websocket.connection_closed { close_code: 1006 }
```

**Backend Log Expected:**
```json
{
  "close_code": 1006,
  "initiated_by": "network"
}
```

**Actual Result:**
- Frontend close_code: ______
- Backend close_code: ______
- initiated_by: ______

**Pass/Fail:** [ ] PASS  [ ] FAIL

---

### Scenario 4: Heartbeat Timeout (AC4)
**Expected:** Frontend shows missed pong progression, then reconnect

| Step | Action | Done |
|------|--------|------|
| 1 | Verify WebSocket connected | [ ] |
| 2 | Pause backend process (don't kill, just pause - Ctrl+Z on Linux) | [ ] |
| 3 | Wait for 3 missed pongs (~90 seconds with default config) | [ ] |
| 4 | Check frontend console for progression | [ ] |

**Frontend Console Expected:**
```
[WARN] websocket.heartbeat_missed_pong { missedPongs: 1 }
[WARN] websocket.heartbeat_missed_pong { missedPongs: 2 }
[WARN] websocket.heartbeat_missed_pong { missedPongs: 3 }
[ERROR] websocket.heartbeat_reconnect { reason: "too_many_missed_pongs" }
```

**Actual Result:**
```
missedPongs progression: ______________________
reconnect triggered: [ ] YES  [ ] NO
```

**Pass/Fail:** [ ] PASS  [ ] FAIL

---

### Scenario 5: Manual Disconnect (AC5)
**Expected:** `close_code: 1000` with clean closure

| Step | Action | Done |
|------|--------|------|
| 1 | Verify WebSocket connected | [ ] |
| 2 | Open browser console | [ ] |
| 3 | Run: `wsService.disconnect()` | [ ] |
| 4 | Check logs | [ ] |

**Frontend Console Expected:**
```
[INFO] websocket.connection_closed {
  close_code: 1000,
  close_reason: "Client disconnect" or "Normal closure",
  was_clean: true
}
```

**Actual Result:**
```
close_code: ______
close_reason: ______________________
was_clean: ______
```

**Pass/Fail:** [ ] PASS  [ ] FAIL

---

## Summary

| Scenario | AC | Expected Code | Actual Code | Result |
|----------|-----|---------------|-------------|--------|
| Browser Tab Close | AC1 | 1001 | | [ ] PASS [ ] FAIL |
| Backend Shutdown | AC2 | 1006 | | [ ] PASS [ ] FAIL |
| Network Disconnect | AC3 | 1006 | | [ ] PASS [ ] FAIL |
| Heartbeat Timeout | AC4 | reconnect | | [ ] PASS [ ] FAIL |
| Manual Disconnect | AC5 | 1000 | | [ ] PASS [ ] FAIL |

**Overall Result:** [ ] ALL PASS  [ ] SOME FAILURES

---

## Notes / Issues Found

_Document any discrepancies, bugs, or observations:_

```




```

---

## Sign-off

**Tester Signature:** ____________________
**Date:** ____________________
**BUG-008-1 Ready for Done:** [ ] YES  [ ] NO
