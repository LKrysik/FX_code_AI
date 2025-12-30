# Epic BUG-008: WebSocket Stability & Service Health

**Status:** backlog
**Priority:** P0 - Critical (Causes Continuous Reconnections)
**Created:** 2025-12-30
**Reporter:** Mr Lu
**Source:** docs/bug-008.md

---

## Overview

Production logs reveal systemic WebSocket stability issues across multiple layers: frontend-backend heartbeat failures, MEXC adapter connection drops, and service connectivity problems. The system experiences continuous connect/disconnect cycles without proper root cause identification.

**Impact:**
- Users experience frequent WebSocket reconnections (every few minutes)
- Data stream interruptions cause stale indicator values
- Dashboard cache service fails to retrieve sessions
- Trading signals may be delayed or lost during reconnection windows

---

## Goal

Achieve stable WebSocket connections with proper error handling, clear diagnostic logging, and graceful degradation when external services (MEXC, QuestDB) experience issues.

**User Value:** "The trading dashboard maintains stable real-time data feed. When connection issues occur, I see clear status indicators and the system recovers automatically without losing critical data."

---

## Log Evidence Summary

### Backend Logs (backend.log)

| Event Type | Severity | Frequency | Impact |
|------------|----------|-----------|--------|
| `mexc_adapter.no_recent_pong_detected` | WARNING | High | Connection health unknown |
| `mexc_adapter.no_data_activity` | ERROR | Medium | Forced connection close |
| `mexc_adapter.pending_subscription_expired` | WARNING | Medium | Subscriptions lost |
| `streaming_indicator_engine.data_anomalies_detected` | WARNING | Medium | Stale data served |
| `dashboard_cache_service.get_active_sessions_failed` | ERROR | Medium | Dashboard broken |
| `questdb_data_provider.session_not_found` | WARNING | High | Session queries fail |

### Frontend Logs (frontend.log)

| Event Type | Severity | Frequency | Impact |
|------------|----------|-----------|--------|
| `websocket.heartbeat_missed_pong` | WARNING | High | Reconnection triggered |
| `websocket.heartbeat_reconnect` | ERROR | Medium | Connection reset |
| `CandlestickChart.loadData` | WARNING | Medium | Chart data gaps |

### Backend Error Log (backend_error.log)

Continuous WebSocket connect/disconnect cycle observed:
```
INFO: connection open
INFO: connection closed
INFO: connection open
INFO: connection closed
(repeating pattern)
```

**Critical Gap:** No diagnostic information about WHY connections close.

---

## Stories

### Sub-Epic 1: WebSocket Connection Stability (FE + BE)

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| BUG-008-1 | WebSocket Disconnect Diagnostic Logging | P0 | backlog |
| BUG-008-2 | Heartbeat Synchronization FE-BE | P0 | backlog |
| BUG-008-3 | Graceful Degradation UI | P1 | backlog |

### Sub-Epic 2: MEXC Adapter Resilience

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| BUG-008-4 | MEXC Pong Timeout Handling | P0 | backlog |
| BUG-008-5 | Subscription Lifecycle Management | P1 | backlog |
| BUG-008-6 | Data Activity Monitoring Tuning | P1 | backlog |

### Sub-Epic 3: Service Health & Data Quality

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| BUG-008-7 | QuestDB Connection Resilience | P0 | backlog |
| BUG-008-8 | Session Lifecycle Tracking | P1 | backlog |
| BUG-008-9 | Stale Data Detection & Handling | P2 | backlog |

---

## Acceptance Criteria (Epic Level)

1. **AC1:** WebSocket connections remain stable for 1+ hour under normal conditions
2. **AC2:** Connection close events include diagnostic reason codes in logs
3. **AC3:** Frontend heartbeat timeouts match backend pong response times
4. **AC4:** MEXC adapter pong age never exceeds 60 seconds without alert/action
5. **AC5:** Subscription TTL expiration triggers automatic resubscription (not just warning)
6. **AC6:** QuestDB connection failures trigger retry with exponential backoff
7. **AC7:** Session queries handle missing sessions gracefully (not just log warning)
8. **AC8:** Stale data (>60s old) is marked/filtered before display
9. **AC9:** Dashboard shows connection health status indicator

---

## Priority Order

**P0 (Must Fix First - Root Causes):**
1. BUG-008-1: WebSocket Disconnect Diagnostic Logging
2. BUG-008-2: Heartbeat Synchronization FE-BE
3. BUG-008-4: MEXC Pong Timeout Handling
4. BUG-008-7: QuestDB Connection Resilience

**P1 (Important - Recovery & Handling):**
5. BUG-008-3: Graceful Degradation UI
6. BUG-008-5: Subscription Lifecycle Management
7. BUG-008-6: Data Activity Monitoring Tuning
8. BUG-008-8: Session Lifecycle Tracking

**P2 (Polish - Data Quality):**
9. BUG-008-9: Stale Data Detection & Handling

---

## Architecture Considerations

### Connection Health Model

```
Frontend <--heartbeat--> Backend <--pong--> MEXC Exchange
   |                        |                    |
   v                        v                    v
Timeout: 30s?          Timeout: 30s?       Timeout: 120s?
   |                        |                    |
   +--> MUST BE SYNCHRONIZED <--+
```

**Problem:** Timeouts are not aligned. Frontend may reconnect before backend has time to detect MEXC issue.

### Proposed Solution Pattern

1. **Single Source of Truth:** Backend owns connection health state
2. **Proactive Heartbeat:** Backend sends heartbeat status to frontend
3. **Layered Timeouts:** MEXC > Backend > Frontend (decreasing)
4. **Graceful Degradation:** Frontend shows "Reconnecting..." instead of breaking

---

## Technical Investigation Required

Before implementation:

1. **Document current timeout values:**
   - Frontend: heartbeat interval, max missed pongs
   - Backend: WebSocket ping interval, pong timeout
   - MEXC Adapter: pong check interval, max age threshold

2. **Trace connection lifecycle:**
   - What triggers connection close?
   - Is it frontend, backend, or MEXC initiated?

3. **Measure latency:**
   - Average pong response time
   - Variance during high load

---

## Files to Investigate

**Frontend:**
- `frontend/src/services/websocket.ts` - WebSocket client
- `frontend/src/hooks/useWebSocket.ts` - React hook (if exists)

**Backend:**
- `src/api/websocket_server.py` - WebSocket server
- `src/api/websocket/` - WebSocket handlers
- `src/adapters/mexc_adapter.py` - MEXC connection

**Services:**
- `src/services/dashboard_cache_service.py` - Dashboard cache
- `src/data/questdb_data_provider.py` - QuestDB provider

---

## Dependencies

- Stories BUG-008-1 and BUG-008-2 should be completed together (same investigation)
- Story BUG-008-3 depends on BUG-008-2 (needs health status data)
- Story BUG-008-7 independent - can be parallelized

---

*Generated by PM Agent (John) - BMAD Framework*
*Source: docs/bug-008.md*
