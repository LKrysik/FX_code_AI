# BUG-007 Epic: WebSocket Connection Stability & Logging Fix

## Epic Overview

**Epic ID:** EPIC-007
**Title:** Fix WebSocket Connection Instability and Frontend Data Flow
**Priority:** Critical (P1)
**Estimated Effort:** 8 Story Points (revised after elicitation)
**Created:** 2025-12-29
**Updated:** 2025-12-29 (Advanced Elicitation Review)
**Reporter:** Mr Lu

## Problem Statement

The trading dashboard experiences critical issues:
1. WebSocket connections continuously disconnect/reconnect
2. Frontend displays no data despite active trading sessions
3. Debug logs pollute error log files
4. Console shows `stream: undefined` warnings

These issues prevent users from monitoring their trading sessions in real-time.

---

## Advanced Elicitation Findings

### Pre-mortem Analysis Results

| Failure Scenario | Probability | Status |
|------------------|-------------|--------|
| Backend doesn't broadcast state_machines | 40% | **CONFIRMED - NO BROADCASTER EXISTS** |
| Other components have same dual-WS issue | 25% | **CONFIRMED - 3 more components found** |
| wsService doesn't route state_machines | 15% | Addressed in Story 3 |

### Critical Discoveries

1. **NO BACKEND BROADCASTER:** Backend has no code to broadcast `state_change`, `instance_added`, `instance_removed`, `full_update` messages. Frontend subscription will work but NO DATA WILL FLOW.

2. **4 COMPONENTS WITH DUAL WEBSOCKET ANTI-PATTERN:**
   - `StateOverviewTable.integration.tsx:90` - in original scope
   - `LiquidationAlert.tsx:84` - **NOT IN ORIGINAL SCOPE**
   - `ConditionProgress.integration.tsx:237` - **NOT IN ORIGINAL SCOPE**
   - `PumpIndicatorsPanel.tsx:514` - **NOT IN ORIGINAL SCOPE**

### Hidden Assumptions (CUI BONO Analysis)

| Assumption | Type | If False... | Benefit |
|------------|------|-------------|---------|
| Backend broadcasts state_machines | HIDDEN | Entire plan fails | AGENT |
| Only 1 component has dual-WS | HIDDEN | 3 more still broken | AGENT |
| No auth needed for state_machines | HIDDEN | Subscription rejected | AGENT |

---

## Root Cause Summary (Final)

| Bug | Root Cause | Severity |
|-----|-----------|----------|
| Connection instability | **Dual WebSocket anti-pattern** in 4 components | CRITICAL |
| Missing data | **No backend broadcaster** + wrong field name | CRITICAL |
| Debug in error logs | No level filtering in flush | MEDIUM |
| stream: undefined | Status messages lack stream field | LOW |

---

## Architectural Decision Records

### ADR-001: Use Shared WebSocket Singleton

**Decision:** All components must use `wsService` singleton instead of creating own WebSocket connections.

**Rationale:** Single connection with proper auth, heartbeat, reconnection, and state sync.

### ADR-002: Backend Must Broadcast State Machine Events

**Decision:** Backend must implement broadcaster for state_machines stream.

**Rationale:** Frontend subscription is useless without data source. This was missing from original analysis.

---

## Stories (Final - Post Elicitation)

### Story 0: Implement Backend state_machines Broadcaster

**Story ID:** BUG-007-S0
**Title:** Create backend broadcaster for state machine events
**Priority:** CRITICAL (BLOCKING)
**Points:** 2

#### Description
The backend has NO code to broadcast state machine updates. Without this, all frontend fixes are useless - data will never flow.

#### Acceptance Criteria
- [ ] AC1: Create state_machines broadcaster service
- [ ] AC2: Emit `state_change` when strategy state changes
- [ ] AC3: Emit `instance_added` when new strategy instance starts
- [ ] AC4: Emit `instance_removed` when strategy instance stops
- [ ] AC5: Emit `full_update` on client subscription (initial state)
- [ ] AC6: Subscribe to state_machines triggers broadcast to subscribed clients

#### Technical Details

**Required Implementation:**
```python
# New file: src/api/websocket/broadcasters/state_machine_broadcaster.py

class StateMachineBroadcaster:
    def __init__(self, subscription_manager, connection_manager):
        self.subscription_manager = subscription_manager
        self.connection_manager = connection_manager

    async def broadcast_state_change(self, session_id: str, data: dict):
        """Broadcast state change to all subscribed clients"""
        subscribers = self.subscription_manager.get_subscribers("state_machines")
        message = {
            "type": "state_change",
            "stream": "state_machines",
            "session_id": session_id,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        for client_id in subscribers:
            await self.connection_manager.send_to_client(client_id, message)
```

#### Files to Create/Modify
- `src/api/websocket/broadcasters/state_machine_broadcaster.py` (NEW)
- `src/api/websocket_server.py` - register broadcaster
- `src/trading/trading_coordinator.py` - emit events on state changes

#### Dependencies
- Must be completed BEFORE Story 1 can be verified

---

### Story 1: Refactor StateOverviewTable to Use Shared WebSocket

**Story ID:** BUG-007-S1
**Title:** Eliminate dual WebSocket anti-pattern in StateOverviewTable
**Priority:** CRITICAL
**Points:** 1.5

#### Description
StateOverviewTable.integration.tsx creates its own WebSocket connection instead of using wsService singleton.

#### Acceptance Criteria
- [ ] AC1: StateOverviewTable uses `wsService` singleton
- [ ] AC2: Component uses `addSessionUpdateListener()` for receiving updates
- [ ] AC3: Component uses `wsService.subscribe('state_machines', params)`
- [ ] AC4: Remove all standalone WebSocket management code (~80 lines)
- [ ] AC5: Connection remains stable with proper heartbeat

#### Technical Details

**Fixed Code:**
```typescript
import { wsService, WSMessage } from '@/services/websocket';
import { useWebSocketStore } from '@/stores/websocketStore';

// In component:
const wsConnected = useWebSocketStore((state) => state.isConnected);

useEffect(() => {
  wsService.subscribe('state_machines', { session_id: sessionId });

  const cleanup = wsService.addSessionUpdateListener((message: WSMessage) => {
    if (message.stream === 'state_machines' || message.type === 'state_change') {
      handleStateChange(message.data);
    } else if (message.type === 'instance_added') {
      handleInstanceAdded(message.data);
    } else if (message.type === 'instance_removed') {
      handleInstanceRemoved(message.data);
    } else if (message.type === 'full_update') {
      setInstances(message.data?.instances || []);
    }
  }, 'StateOverviewTable');

  return () => {
    cleanup();
    wsService.unsubscribe('state_machines');
  };
}, [sessionId]);
```

#### Files to Modify
- `frontend/src/components/dashboard/StateOverviewTable.integration.tsx`

---

### Story 1b: Refactor LiquidationAlert to Use Shared WebSocket

**Story ID:** BUG-007-S1b
**Title:** Eliminate dual WebSocket in LiquidationAlert
**Priority:** HIGH
**Points:** 0.5

#### Description
LiquidationAlert.tsx:84 creates its own WebSocket connection.

#### Files to Modify
- `frontend/src/components/trading/LiquidationAlert.tsx`

---

### Story 1c: Refactor ConditionProgress to Use Shared WebSocket

**Story ID:** BUG-007-S1c
**Title:** Eliminate dual WebSocket in ConditionProgress
**Priority:** HIGH
**Points:** 0.5

#### Description
ConditionProgress.integration.tsx:237 creates its own WebSocket connection.

#### Files to Modify
- `frontend/src/components/dashboard/ConditionProgress.integration.tsx`

---

### Story 1d: Refactor PumpIndicatorsPanel to Use Shared WebSocket

**Story ID:** BUG-007-S1d
**Title:** Eliminate dual WebSocket in PumpIndicatorsPanel
**Priority:** HIGH
**Points:** 0.5

#### Description
PumpIndicatorsPanel.tsx:514 creates its own WebSocket connection.

#### Files to Modify
- `frontend/src/components/dashboard/PumpIndicatorsPanel.tsx`

---

### Story 2: Add state_machines to Valid Streams

**Story ID:** BUG-007-S2
**Title:** Register state_machines as valid stream type in backend
**Priority:** HIGH
**Points:** 0.5

#### Description
Add `state_machines` to the valid_streams whitelist in message_router.py.

#### Files to Modify
- `src/api/message_router.py` (line 403-408)

---

### Story 3: Extend wsService for state_machines Message Handling

**Story ID:** BUG-007-S3
**Title:** Add state_machines message type handling to wsService
**Priority:** HIGH
**Points:** 1

#### Description
The wsService needs to handle `state_machines` stream messages and route them to session update listeners.

#### Technical Details

**Add to websocket.ts - isRelevantMessage():**
```typescript
const relevantTypes = [
  // ... existing types ...
  'state_change',
  'instance_added',
  'instance_removed',
  'full_update'
];
```

**Add to handleMessage() switch:**
```typescript
case 'state_change':
case 'instance_added':
case 'instance_removed':
case 'full_update':
  this.emitSessionUpdate(message);
  break;
```

#### Files to Modify
- `frontend/src/services/websocket.ts`

---

### Story 4: Filter Debug Logs from Error Log File

**Story ID:** BUG-007-S4
**Title:** Implement log level filtering in frontend log service
**Priority:** MEDIUM
**Points:** 1

#### Description
Only send ERROR and WARN level logs to backend, not DEBUG/INFO.

#### Files to Modify
- `frontend/src/services/frontendLogService.ts`

---

### Story 5: Clean Up stream:undefined Log Noise

**Story ID:** BUG-007-S5
**Title:** Handle missing stream field gracefully in logging
**Priority:** LOW
**Points:** 0.5

#### Files to Modify
- `frontend/src/services/websocket.ts` (line 1033)

---

## Implementation Plan (Revised)

### Phase 0: Backend Infrastructure (BLOCKING)
1. **Story 0**: Implement backend state_machines broadcaster (1h)

### Phase 1: Critical WebSocket Fixes
2. **Story 2**: Add state_machines to valid_streams (10 min)
3. **Story 3**: Extend wsService for state_machines (20 min)
4. **Story 1**: Refactor StateOverviewTable (30 min)
5. **Story 1b**: Refactor LiquidationAlert (20 min)
6. **Story 1c**: Refactor ConditionProgress (20 min)
7. **Story 1d**: Refactor PumpIndicatorsPanel (20 min)

### Phase 2: Quality Improvements
8. **Story 4**: Filter debug logs (20 min)
9. **Story 5**: Clean up log noise (10 min)

---

## Files Summary (Final)

| File | Changes | Story | Priority |
|------|---------|-------|----------|
| `src/api/websocket/broadcasters/state_machine_broadcaster.py` | **NEW FILE** | S0 | CRITICAL |
| `src/api/websocket_server.py` | Register broadcaster | S0 | CRITICAL |
| `src/trading/trading_coordinator.py` | Emit state events | S0 | CRITICAL |
| `src/api/message_router.py` | Add state_machines | S2 | HIGH |
| `frontend/src/services/websocket.ts` | Add message handling | S3, S5 | HIGH |
| `frontend/src/components/dashboard/StateOverviewTable.integration.tsx` | Refactor to wsService | S1 | CRITICAL |
| `frontend/src/components/trading/LiquidationAlert.tsx` | Refactor to wsService | S1b | HIGH |
| `frontend/src/components/dashboard/ConditionProgress.integration.tsx` | Refactor to wsService | S1c | HIGH |
| `frontend/src/components/dashboard/PumpIndicatorsPanel.tsx` | Refactor to wsService | S1d | HIGH |
| `frontend/src/services/frontendLogService.ts` | Filter log levels | S4 | MEDIUM |

---

## Architecture Diagram (Final)

```
BEFORE (Broken - 5 connections!):
┌─────────────────────────────────────────────────────────────────┐
│ Dashboard                                                       │
│ ├── wsService ──────────────────────► ws://127.0.0.1:8080/ws   │
│ ├── StateOverviewTable ─────────────► ws://127.0.0.1:8080/ws   │ ← DUPLICATE
│ ├── LiquidationAlert ───────────────► ws://127.0.0.1:8080/ws   │ ← DUPLICATE
│ ├── ConditionProgress ──────────────► ws://127.0.0.1:8080/ws   │ ← DUPLICATE
│ └── PumpIndicatorsPanel ────────────► ws://127.0.0.1:8080/ws   │ ← DUPLICATE
│                                                                 │
│ Backend: NO BROADCASTER FOR state_machines!                     │
└─────────────────────────────────────────────────────────────────┘

AFTER (Fixed - 1 connection, full data flow):
┌─────────────────────────────────────────────────────────────────┐
│ Dashboard                                                       │
│ └── wsService (singleton) ──────────► ws://127.0.0.1:8080/ws   │
│     ├── StateOverviewTable (listener)                           │
│     ├── LiquidationAlert (listener)                             │
│     ├── ConditionProgress (listener)                            │
│     └── PumpIndicatorsPanel (listener)                          │
│                                                                 │
│ Backend: StateMachineBroadcaster → broadcasts to subscribers    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Risk Assessment (Updated)

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Backend broadcaster complex to implement | HIGH | 30% | Use existing broadcast patterns |
| Refactoring 4 components causes regressions | HIGH | 40% | Test each component individually |
| State events not emitted from trading coordinator | MEDIUM | 25% | Add event hooks in coordinator |
| Log filtering breaks error tracking | LOW | 10% | Keep WARN level |

---

## Definition of Done

- [ ] Story 0: Backend broadcasts state_machines events
- [ ] All 4 components use wsService singleton
- [ ] Only ONE WebSocket connection in browser Network tab
- [ ] State overview table shows real-time updates
- [ ] Error logs contain only ERROR/WARN entries
- [ ] E2E test: start session → verify state updates flow
- [ ] No regressions in market data, signals, etc.

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | Mary (Analyst) | Initial Epic creation |
| 2025-12-29 | Winston (Architect) | Added ADR-001, restructured stories |
| 2025-12-29 | Advanced Elicitation | **Added Story 0 (backend broadcaster), Stories 1b-1d (3 more components), ADR-002** |
