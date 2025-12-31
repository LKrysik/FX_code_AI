# BUG-009: System Stability and Error Fixes

**Created:** 2025-12-30
**Priority:** P0-P2 (Mixed)
**Status:** Ready for Implementation

---

## Executive Summary

Analysis of bug-009.md revealed **4 distinct problem areas** requiring separate epics. The most critical is the State Machine blocker preventing paper trading sessions from showing active instances.

### Priority Matrix

| Epic | Priority | Impact | Effort |
|------|----------|--------|--------|
| Epic 1: State Machine Blocker | **P0 - CRITICAL** | Blocks entire paper trading workflow | Medium |
| Epic 2: WebSocket Stability | **P1 - HIGH** | Poor UX, reconnection loops | Medium |
| Epic 3: Message Router Validation | **P2 - MEDIUM** | Console warnings, failed subscriptions | Low |
| Epic 4: Algorithm Registry Cleanup | **P2 - LOW** | Log noise only | Low |

---

## Epic 1: State Machine Blocker Fix

**Priority:** P0 - CRITICAL BLOCKER
**Goal:** Fix State Machine Overview showing "No active instances" after starting paper trading session

### Root Cause Analysis

The BUG-005-1 fix exists but has a failure path: when `unified_controller` is `None`, `_activate_strategies_for_session()` is never called. This means:
1. StrategyManager is never populated
2. State Machine API returns empty instances array
3. UI shows "No active instances"

**Key Finding:** No error is logged when this happens - silent failure.

### Affected Files

- `src/api/paper_trading_routes.py` (lines 206-245)
- `src/application/controllers/unified_trading_controller.py` (lines 875-977)
- `src/api/state_machine_routes.py` (lines 84-194)
- `src/api/unified_server.py` (lines 424-428)

---

### Story 1.1: Add Diagnostic Logging for Strategy Activation Pipeline

**Priority:** P0
**Estimate:** S

**Description:**
Add comprehensive logging to diagnose why state machines are not starting. Currently the failure is silent.

**Acceptance Criteria:**
- [ ] Log when `unified_controller` is None at session creation
- [ ] Log when `_activate_strategies_for_session()` is called (with params)
- [ ] Log when `_activate_strategies_for_session()` completes (with results count)
- [ ] Log when `StrategyManager.activate_strategy_for_symbol()` succeeds/fails for each symbol
- [ ] Error log if strategy activation returns 0 active strategies

**Technical Notes:**
```python
# paper_trading_routes.py - Add logging at line 206
if controller is None:
    logger.error("paper_trading_api.critical_missing_controller", {
        "session_id": session_id,
        "impact": "state_machines_will_not_start",
        "action_required": "check_unified_server_initialization"
    })
```

**Files to Modify:**
- `src/api/paper_trading_routes.py`
- `src/application/controllers/unified_trading_controller.py`

---

### Story 1.2: Ensure UnifiedController is Always Injected

**Priority:** P0
**Estimate:** M

**Description:**
Investigate why `unified_controller` may be None and fix the initialization chain.

**Acceptance Criteria:**
- [ ] Trace `unified_server.py` initialization to verify `ws_controller` is passed to `paper_trading_routes`
- [ ] Add startup validation that `unified_controller` is not None
- [ ] If None, fail fast with clear error message instead of silent failure
- [ ] Add integration test that verifies state machine instances appear after session creation

**Technical Notes:**
Check `unified_server.py` line 424-428:
```python
paper_trading_routes_module.initialize_paper_trading_dependencies(
    persistence_service=paper_trading_persistence,
    unified_controller=ws_controller  # MUST NOT BE None
)
```

**Files to Modify:**
- `src/api/unified_server.py`
- `src/api/paper_trading_routes.py`

---

### Story 1.3: Verify Strategy Activation Flow End-to-End

**Priority:** P0
**Estimate:** M

**Description:**
Create a test that validates the entire flow from session creation to state machine display.

**Acceptance Criteria:**
- [ ] Test creates paper trading session
- [ ] Test verifies `_activate_strategies_for_session()` was called
- [ ] Test verifies StrategyManager has active strategies
- [ ] Test verifies `/api/sessions/{id}/state` returns non-empty instances
- [ ] Test runs in CI pipeline

**Files to Create:**
- `tests/integration/test_paper_trading_state_machine_flow.py`

---

## Epic 2: WebSocket Stability Improvements

**Priority:** P1 - HIGH
**Goal:** Fix WebSocket errors causing poor UX and reconnection loops

### Root Cause Analysis

Multiple issues identified:
1. **undefined object in connection_unhealthy** - Accessing snapshot properties without null checks
2. **missed_pong reconnection loops** - 30s timeout, 3 missed = reconnect (aggressive)
3. **Invalid state snapshot response** - API returns malformed data structure
4. **invalidMarketDataResponse** - Market data response validation failures

### Affected Files

- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/services/websocket.ts` (lines 656-749)
- `frontend/src/stores/dashboardStore.ts` (lines 145-164)

---

### Story 2.1: Fix Undefined Object in State Sync

**Priority:** P1
**Estimate:** S

**Description:**
Add null safety to state snapshot handling to prevent "undefined" objects in logs.

**Acceptance Criteria:**
- [ ] Add null coalescing for all snapshot properties in `websocket.ts` lines 700-716
- [ ] Validate snapshot structure before accessing nested properties
- [ ] Log actual response structure when validation fails (for debugging)
- [ ] No more "undefined" in connection_unhealthy logs

**Technical Notes:**
```typescript
// websocket.ts line 700-706 - Add null safety
const snapshot = result.data ?? {};
Logger.info('websocket.state_snapshot_received', {
  timestamp: snapshot.timestamp ?? 'unknown',
  positions: snapshot.positions?.length ?? 0,
  signals: snapshot.active_signals?.length ?? 0,
  state: snapshot.state_machine_state ?? 'unknown'
});
```

**Files to Modify:**
- `frontend/src/services/websocket.ts`

---

### Story 2.2: Investigate State Snapshot API Response

**Priority:** P1
**Estimate:** M

**Description:**
The "Invalid state snapshot response" error indicates the `/api/state/snapshot` endpoint returns malformed data.

**Acceptance Criteria:**
- [ ] Add request/response logging to `/api/state/snapshot` endpoint
- [ ] Identify what exact response structure is returned
- [ ] Fix API to return proper `{ success: true, data: {...} }` structure
- [ ] Ensure `data` contains required fields: timestamp, positions, active_signals, state_machine_state
- [ ] No more "Invalid state snapshot response" errors

**Files to Investigate:**
- Backend endpoint handling `/api/state/snapshot`
- `frontend/src/services/websocket.ts` (line 697)

---

### Story 2.3: Fix Market Data Response Validation

**Priority:** P2
**Estimate:** S

**Description:**
Fix `dashboardStore.invalidMarketDataResponse` warnings.

**Acceptance Criteria:**
- [ ] Log the actual response structure when validation fails
- [ ] Identify which API endpoint returns invalid structure
- [ ] Fix API to return `{ data: { market_data: [...] } }` structure
- [ ] Validate market data items have required fields: symbol, price, priceChange24h, volume24h

**Files to Modify:**
- `frontend/src/stores/dashboardStore.ts`
- Backend market data endpoint

---

### Story 2.4: Review WebSocket Heartbeat Aggressiveness

**Priority:** P2
**Estimate:** S

**Description:**
Review if 3 missed pongs (30s each = 90s) forcing reconnect is too aggressive.

**Acceptance Criteria:**
- [ ] Document current heartbeat configuration
- [ ] Consider increasing to 4-5 missed pongs before reconnect
- [ ] Consider increasing pong timeout from 30s to 45s
- [ ] Make heartbeat parameters configurable via config
- [ ] Reduce reconnection frequency

**Files to Modify:**
- `frontend/src/services/websocket.ts` (lines 62-67)
- `frontend/src/config/` (add websocket config)

---

## Epic 3: Message Router Validation Fixes

**Priority:** P2 - MEDIUM
**Goal:** Fix validation errors for stream subscriptions

### Root Cause Analysis

1. **"conditions" stream not supported** - Frontend tries to subscribe to non-existent stream
2. **Missing symbol for indicators** - Some indicator subscriptions lack required symbol param

### Affected Files

- `src/api/message_router.py` (lines 402-436)
- `frontend/src/components/dashboard/ConditionProgress.integration.tsx` (line 248)
- `frontend/src/services/websocket.ts`

---

### Story 3.1: Add "conditions" Stream Type or Remove Subscription

**Priority:** P2
**Estimate:** S

**Description:**
Frontend `ConditionProgress.integration.tsx` subscribes to "conditions" stream which doesn't exist.

**Acceptance Criteria:**
- [ ] OPTION A: Add "conditions" to valid_streams in message_router.py and implement handler
- [ ] OPTION B: Remove WebSocket subscription from ConditionProgress and use REST-only approach
- [ ] No more "Invalid stream type: conditions" warnings

**Technical Notes:**
```python
# Option A - message_router.py line 403
valid_streams = [
    "market_data", "indicators", "signals", "orders", "positions",
    "portfolio", "execution_status", "system_health",
    "health_check", "comprehensive_health_check", "state_machines",
    "conditions"  # ADD THIS
]
```

```typescript
// Option B - Remove line 248 from ConditionProgress.integration.tsx
// wsService.subscribe('conditions', { session_id: sessionId, symbol });
```

**Files to Modify:**
- `src/api/message_router.py` OR
- `frontend/src/components/dashboard/ConditionProgress.integration.tsx`

---

### Story 3.2: Fix Missing Symbol in Indicator Subscriptions

**Priority:** P2
**Estimate:** S

**Description:**
Some indicator subscription calls don't include required symbol/symbols parameter.

**Acceptance Criteria:**
- [ ] Audit all `wsService.subscribe('indicators', ...)` calls in frontend
- [ ] Ensure all calls include `symbol` or `symbols` in params
- [ ] No more "Indicator subscription must specify symbol or symbols" warnings

**Files to Audit:**
- All frontend components using indicator subscriptions
- `frontend/src/services/websocket.ts`

---

## Epic 4: Algorithm Registry Cleanup

**Priority:** P2 - LOW
**Goal:** Eliminate duplicate algorithm registration warnings

### Root Cause Analysis

Auto-discovery process finds BOTH:
1. Class definition (e.g., `VolumeSurgeRatioAlgorithm`)
2. Module-level instance (e.g., `volume_surge_ratio_algorithm`)

This results in registering each algorithm twice, causing "algorithm_overwrite" warning on every startup.

### Affected Files

- `src/domain/services/indicators/algorithm_registry.py` (lines 136-166)
- All 16+ indicator algorithm files

---

### Story 4.1: Fix Double Registration in Algorithm Registry

**Priority:** P2
**Estimate:** S

**Description:**
Modify auto-discovery to avoid registering both class and instance.

**Acceptance Criteria:**
- [ ] Modify `_load_algorithms_from_module()` to prefer instances over classes
- [ ] Skip class registration if module-level instance already exists
- [ ] No more "algorithm_overwrite" warnings on startup
- [ ] All 16+ algorithms still registered correctly

**Technical Notes:**
```python
# algorithm_registry.py - Modify lines 136-166
def _load_algorithms_from_module(self, module_name: str) -> int:
    # First pass: collect all instances
    instances = {}
    for name, obj in inspect.getmembers(module):
        if self._is_algorithm_instance(obj):
            indicator_type = obj.get_indicator_type()
            instances[indicator_type] = obj

    # Register instances (skip classes if instance exists)
    for name, obj in inspect.getmembers(module):
        if self._is_algorithm_class(obj):
            indicator_type = obj().get_indicator_type()
            if indicator_type in instances:
                continue  # Skip class, instance already found
            algorithm = obj()
            self.register_algorithm(algorithm)
        elif self._is_algorithm_instance(obj):
            self.register_algorithm(obj)
```

**Files to Modify:**
- `src/domain/services/indicators/algorithm_registry.py`

---

## Implementation Order

1. **Epic 1 (P0)** - Must be done first, blocks paper trading
   - Story 1.1 (diagnose) -> Story 1.2 (fix) -> Story 1.3 (verify)

2. **Epic 2 (P1)** - Improves UX significantly
   - Story 2.1 and 2.2 can be parallel
   - Story 2.3 and 2.4 can be parallel after 2.1/2.2

3. **Epic 3 (P2)** - Quick wins, cleans up console
   - Story 3.1 and 3.2 can be parallel

4. **Epic 4 (P2)** - Log cleanup, lowest priority
   - Story 4.1 standalone

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] No regressions in existing functionality
- [ ] Code review passed
- [ ] Tests added where applicable
- [ ] No new warnings/errors in console or backend logs
