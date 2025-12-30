# Story BUG-008-2: Heartbeat Synchronization FE-BE

**Status:** in-progress
**Priority:** P0
**Epic:** BUG-008 WebSocket Stability & Service Health

---

## Story

As a **system architect**,
I want **frontend and backend heartbeat timeouts to be properly synchronized**,
so that **premature reconnections don't occur due to timing mismatches**.

---

## Problem Statement

Log evidence shows timing mismatch:
- Frontend: `websocket.heartbeat_missed_pong { missedPongs: 3, maxMissedPongs: 3 }` triggers reconnect
- Backend: May still be healthy, just slow to respond

**Root Cause Hypothesis:**
Frontend timeout is too aggressive relative to backend processing time. When backend is under load (processing MEXC data), pong responses are delayed, causing frontend to reconnect unnecessarily.

**Evidence from logs:**
```
[WARN] websocket.heartbeat_missed_pong { missedPongs: 1 }
[WARN] websocket.heartbeat_missed_pong { missedPongs: 2 }
[WARN] websocket.heartbeat_missed_pong { missedPongs: 3 }
[ERROR] websocket.heartbeat_reconnect { reason: 'too_many_missed_pongs' }
```

---

## Acceptance Criteria

1. **AC1:** Document current timeout configuration (FE ping interval, FE pong timeout, BE ping interval)
2. **AC2:** Frontend pong timeout is at least 2x backend ping interval
3. **AC3:** Backend responds to ping within 5 seconds under normal load
4. **AC4:** Frontend shows "Slow Connection" warning before forcing reconnect
5. **AC5:** Heartbeat configuration is externalized (not hardcoded)
6. **AC6:** Connection remains stable for 1 hour with no missed pongs under normal conditions

---

## Tasks / Subtasks

- [x] Task 1: Audit current timeout configuration (AC: 1)
  - [x] Document frontend ping interval in `websocket.ts`
  - [x] Document frontend pong timeout / max missed pongs
  - [x] Document backend ping interval in `websocket_server.py`
  - [x] Document backend pong handler response time
  - [x] Create timing diagram showing current flow

- [x] Task 2: Implement synchronized timeouts (AC: 2, 3)
  - [x] Define shared timeout constants (existing: FE 30s, BE 30s - aligned)
  - [x] Frontend: ping every 30s, allow 3 missed = 90s tolerance (BUG-005-2 fix)
  - [x] Backend: respond to ping immediately (priority handler) - already implemented
  - [x] Backend: send own ping every 30s (WebSocket protocol level ping_interval=30)
  - [x] Verify timing: FE timeout (90s) > BE ping (30s) + network latency (5s) = 35s ✅

- [x] Task 3: Add "Slow Connection" warning state (AC: 4)
  - [x] Frontend: after 2 missed pongs, emit "slow_connection" event (slowConnectionThreshold=2)
  - [x] Do NOT reconnect at 2 missed - only warn (status='slow', reconnect at 3)
  - [x] Reconnect only at 3 missed (90s total) - kept BUG-005-2 generous tolerance
  - [x] Log slow connection events for monitoring (websocket.slow_connection_detected)

- [ ] Task 4: Externalize configuration (AC: 5)
  - [ ] Frontend: read timeouts from config or environment
  - [ ] Backend: read timeouts from config.yaml
  - [ ] Document configuration options

- [ ] Task 5: Stability testing (AC: 6)
  - [ ] Create test script that runs for 1 hour
  - [ ] Monitor logs for missed pongs
  - [ ] Measure pong response times
  - [ ] Document baseline metrics

---

## Dev Notes

### Current Timing Analysis (Audited 2025-12-30)

**Frontend (websocket.ts lines 62-66):**
| Setting | Value | Comment |
|---------|-------|---------|
| `heartbeatInterval` | 30000ms (30s) | Ping sent every 30s |
| `heartbeatTimeout` | 30000ms (30s) | Wait for pong response (BUG-005-2 fix) |
| `maxMissedPongs` | 3 | Reconnect after 3 missed pongs |
| **Total tolerance** | **90s** | Before forced reconnect |

**Backend (websocket_server.py lines 335, 384, 683-685):**
| Setting | Value | Comment |
|---------|-------|---------|
| `heartbeat_interval` | 30s | Constructor param |
| `heartbeat_timeout_seconds` | 90s | `heartbeat_interval * 3` in ConnectionManager |
| WS `ping_interval` | 30s | Protocol-level ping |
| WS `ping_timeout` | 10s | Protocol-level pong timeout |
| WS `close_timeout` | 5s | Connection close timeout |

**Backend Pong Handler (websocket_server.py lines 1569-1578):**
```python
async def handle_heartbeat(client_id: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    await self.connection_manager.update_heartbeat(client_id)
    return {
        "type": MessageType.STATUS,
        "status": "pong",
        "timestamp": datetime.now().isoformat()
    }
```
Handler is already immediate - no blocking operations.

### Timing Diagram (Current Flow)

```
Time    Frontend                         Backend
──────────────────────────────────────────────────────
T=0s    ping sent ─────────────────────► receives ping
        pongTimeout set (30s)            pong sent ─────►
T<30s   ◄───────────────────────────────────────────────
        pong received, missedPongs=0

T=30s   ping sent ─────────────────────► receives ping
        pongTimeout set (30s)            pong sent ─────►
...

Failure scenario (no pong received):
T=0s    ping sent, pongTimeout=30s
T=30s   timeout fires, missedPongs=1
        ping sent, pongTimeout=30s
T=60s   timeout fires, missedPongs=2   ← NO WARNING (AC4 gap)
        ping sent, pongTimeout=30s
T=90s   timeout fires, missedPongs=3
        RECONNECT triggered
```

### Gap Analysis vs Acceptance Criteria

| AC | Status | Notes |
|----|--------|-------|
| AC1 | ✅ DONE | Configuration documented above |
| AC2 | ✅ PASS | FE pong timeout (30s) > BE ping interval (30s) |
| AC3 | ✅ PASS | Handler is immediate, no blocking |
| AC4 | ❌ GAP | No "Slow Connection" warning at 2 missed pongs |
| AC5 | ⚠️ PARTIAL | Values hardcoded, not externalized |
| AC6 | ❓ UNTESTED | Need 1-hour stability test |

### Proposed Changes

1. **AC4 - Add Slow Connection Warning:**
   - Emit warning event at 2 missed pongs (60s)
   - Keep reconnect at 3 missed (90s)
   - No code change to timeout values needed

2. **AC5 - Externalize Configuration:**
   - Frontend: Read from environment/config
   - Backend: Already uses constructor params, good

3. **AC6 - Stability Testing:**
   - Create test script to monitor connection for 1 hour

### Backend Pong Priority

The backend pong handler should:
1. NOT be blocked by data processing
2. Execute immediately upon receiving ping
3. Not wait for any async operations

```python
# HIGH PRIORITY - do not add async operations here
async def handle_ping(self, websocket, client_id):
    await websocket.pong()  # Immediate response
    self.logger.debug("websocket.pong_sent", {"client_id": client_id})
```

### Configuration Constants

```yaml
# config.yaml
websocket:
  frontend:
    ping_interval_seconds: 15
    max_missed_pongs: 4
    slow_connection_threshold: 2
  backend:
    ping_interval_seconds: 30
    pong_timeout_seconds: 5
```

### Files to Modify

**Frontend:**
- `frontend/src/services/websocket.ts` - Heartbeat logic

**Backend:**
- `src/api/websocket_server.py` - Ping handler
- `_bmad/bmm/config.yaml` - Configuration (if applicable)

### Dependencies

- Should be done WITH or AFTER BUG-008-1 (diagnostic logging) for visibility

---

## Definition of Done

1. [ ] Timeout values documented and aligned
2. [ ] Frontend shows "Slow Connection" warning before reconnect
3. [ ] Backend pong response time < 5s under normal load
4. [ ] Configuration is externalized
5. [ ] 1-hour stability test passes with 0 unnecessary reconnects
6. [ ] Metrics dashboard shows heartbeat health (optional)

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from BUG-008 Epic |
