# Epic BUG-005: DEFINITIVE FIX - Strategy Activation Pipeline + WebSocket Stability

**Status:** ready
**Priority:** P0 - CRITICAL (Complete System Failure)
**Created:** 2025-12-27
**Reporter:** mr lu
**Source:** docs/bug_005.md
**Supersedes:** Partially supersedes BUG-003, BUG-004 (addresses root causes not symptoms)

---

## Executive Summary

**Why This Fix Is Different**: Previous bug fixes (BUG-003, BUG-004) treated SYMPTOMS without finding ROOT CAUSES. Deep code analysis reveals:

1. **Paper Trading Routes BYPASS the entire strategy activation pipeline** - they only create database records
2. **WebSocket has asymmetric ping/pong with aggressive 10s timeout** - causes constant reconnects
3. **Duplicate heartbeat implementations** conflict and cause race conditions

**This is not a "fix and hope" approach** - this is a definitive architectural correction.

---

## ROOT CAUSE ANALYSIS (Code Evidence)

### Critical Gap #1: Strategy Activation Pipeline Bypassed

**Location**: `src/api/paper_trading_routes.py:125-178`

```
User selects strategy → POST /api/paper-trading/sessions
                             ↓
            PaperTradingPersistenceService.create_session()
                             ↓
            Database record created with status="RUNNING"
                             ↓
            *** MISSING: _activate_strategies_for_session() ***
            *** MISSING: StrategyManager.load_strategies_from_db() ***
            *** MISSING: StrategyManager.activate_strategy_for_symbol() ***
            *** MISSING: _create_indicator_variants_for_strategy() ***
                             ↓
            State Machine Overview queries StrategyManager → EMPTY
                             ↓
            Result: "No active instances"
```

**Contrast with Backtest Flow (WORKS)**:
```
start_backtest() → ExecutionController.create_session()
                → _activate_strategies_for_session() ✓
                → StrategyManager populated ✓
                → State Machine Overview shows instances ✓
```

### Critical Gap #2: Asymmetric Ping/Pong Protocol

**Frontend** (`hooks/useWebSocket.ts`):
- Sends: `{ type: 'heartbeat', timestamp, client_time }`
- Expects: `{ type: 'pong' }` or `{ type: 'status', status: 'pong' }`
- Timeout: **10 seconds** (too aggressive)
- After 3 missed pongs: Force reconnect

**Backend** (`heartbeat_service.py`):
- Sends PING every 30 seconds
- Expects PONG within 10 seconds
- After 3 missed: Close connection

**Problem**: Frontend sends 'heartbeat', backend expects specific protocol. Frontend expects response within 10s, normal network latency causes "missed pong" counts to accumulate.

### Critical Gap #3: Duplicate Heartbeat Implementations

Two separate heartbeat services exist:
1. `frontend/src/hooks/useWebSocket.ts` - Standalone heartbeat
2. `frontend/src/services/websocket.ts` - Another heartbeat

These conflict, causing race conditions and double-counting missed pongs.

### Critical Gap #4: No Stream Field Validation

`sendMessage()` can be called directly, bypassing `sendSubscription()` which validates the required `stream` field. Malformed messages cause backend validation errors.

---

## Stories

### BUG-005-1: Fix Strategy Activation Pipeline (P0-CRITICAL)

**Problem**: `paper_trading_routes.py` creates session but NEVER activates strategies.

**Root Cause**: Direct call to persistence service bypasses `UnifiedTradingController.start_live_trading()`.

**Solution**: Refactor paper trading session creation to use proper controller flow:

```python
# paper_trading_routes.py create_session()
# MUST call:
await unified_controller.start_live_trading(
    symbols=request.symbols,
    mode="paper",
    selected_strategies=[request.strategy_id],
    session_id=session_id
)
```

**OR create integration method** that:
1. Calls `execution_controller.create_session()`
2. Calls `_activate_strategies_for_session()`
3. Calls `_create_indicator_variants_for_strategy()` for each strategy
4. Registers StrategyManager with EventBus

**Files to Change**:
- `src/api/paper_trading_routes.py` - Add proper activation flow
- `src/application/controllers/unified_trading_controller.py` - May need method extraction

**Acceptance Criteria**:
- [ ] Starting paper trading session activates strategies in StrategyManager
- [ ] State Machine Overview shows active strategy instance
- [ ] Indicator variants are created for strategy conditions
- [ ] EventBus receives strategy state updates

---

### BUG-005-2: Unify & Fix WebSocket Heartbeat (P0-CRITICAL)

**Problem**: Duplicate heartbeat implementations + aggressive 10s timeout.

**Solution**:

1. **Remove duplicate**: Use ONLY `WebSocketService` heartbeat, remove from `useWebSocket` hook
2. **Increase timeout**: Change from 10s to 30s
3. **Symmetric protocol**: Ensure frontend sends what backend expects
4. **Reset counter on success**: After successful pong, reset missed counter to 0

**Files to Change**:
- `frontend/src/hooks/useWebSocket.ts:205-208` - Remove heartbeat or increase to 30s
- `frontend/src/services/websocket.ts:865-874` - Keep as single source
- Ensure pong handling resets counter properly

**Acceptance Criteria**:
- [ ] Single heartbeat implementation (no duplicates)
- [ ] Pong timeout is 30 seconds minimum
- [ ] WebSocket stable for 10+ minutes without reconnect
- [ ] Missed pong counter properly resets on success

---

### BUG-005-3: Add Message Validation in Frontend (P1-HIGH)

**Problem**: `sendMessage()` allows malformed subscription messages without `stream` field.

**Solution**:
```typescript
private sendMessage(message: WSMessage): void {
  // Validate required fields for subscription messages
  if (message.type === 'subscribe' && !message.stream) {
    errorLog('Subscription message missing required "stream" field');
    return;
  }
  // ... existing code
}
```

**Files to Change**:
- `frontend/src/services/websocket.ts:700` - Add validation

**Acceptance Criteria**:
- [ ] Subscription messages without `stream` field are rejected at client side
- [ ] Error logged with helpful message
- [ ] No "Missing required field: stream" errors in backend logs

---

### BUG-005-4: Add Subscription Restoration on Reconnect (P1-HIGH)

**Problem**: When WebSocket reconnects, previous subscriptions are lost.

**Solution**:
1. Store active subscriptions before disconnect
2. On reconnect, re-subscribe to all stored subscriptions
3. Implement subscription queue that flushes after handshake

**Files to Change**:
- `frontend/src/services/websocket.ts` - Add subscription persistence/restoration

**Acceptance Criteria**:
- [ ] Subscriptions persist across reconnection
- [ ] Data flow resumes automatically after reconnect
- [ ] No manual re-subscription required

---

### BUG-005-5: TEA Integration Tests (P0-MANDATORY)

**MANDATORY**: No fix is complete without comprehensive tests.

**Test Requirements**:

1. **Unit Tests**:
   - Strategy activation flow creates StrategyManager entries
   - Indicator variants created for strategy conditions
   - WebSocket message validation rejects malformed messages

2. **Integration Tests**:
   - Paper trading session creation → State Machine populated
   - WebSocket connection survives 5 minutes without reconnect
   - Subscription restoration after forced disconnect

3. **E2E Tests**:
   - Full paper trading flow: select strategy → start session → see in State Machine Overview
   - Dashboard maintains data after WebSocket reconnect
   - All dashboard panels display correct data

**Files to Create/Update**:
- `tests/integration/test_paper_trading_activation.py`
- `tests/integration/test_websocket_stability.py`
- `frontend/src/services/__tests__/websocket.test.ts`
- `tests/e2e/test_paper_trading_dashboard.py`

**Acceptance Criteria**:
- [ ] Integration test: session creation activates strategy
- [ ] Integration test: WebSocket stable for 5+ minutes
- [ ] E2E test: full paper trading flow works
- [ ] All tests pass in CI

---

## VERIFICATION PARADOXES APPLIED

### Barber Paradox (#55): Alternative Approaches

**Rejected Alternative**: Polling fallback when WebSocket fails
**Why Reconsidered**: If WebSocket is fundamentally broken, polling provides data reliability. Consider implementing as fallback for critical data (session state, alerts).

**Decision**: Add polling fallback for session state endpoint as backup. WebSocket for real-time, HTTP poll every 30s as safety net.

### Sorites Paradox (#56): Single Point of Failure

**Question**: Which single removal DESTROYS the solution?
**Answer**: `_activate_strategies_for_session()` - without this call, NOTHING works.
**Priority**: This method call is THE critical fix. BUG-005-1 is non-negotiable.

### Newcomb's Paradox (#57): Surprising Solution

**Expected Approach**: Fix WebSocket timing, add error handling
**Surprising Alternative**: The issue isn't WebSocket - it's that strategies were NEVER activated.
**Result**: This analysis found the TRUE root cause that previous bug fixes missed.

### Braess Paradox (#58): Helpful Element That Hurts

**Identified**: Aggressive 10s pong timeout "seems helpful" (fast failure detection)
**Actually Hurts**: Normal network latency causes false positives → unnecessary reconnects → subscription loss
**Action**: Increase timeout to 30s (less "helpful" but more stable)

### Simpson's Paradox (#59): Hidden Variable

**Parts Analysis**: Each component (session, strategies, indicators) seems OK individually
**Hidden Variable**: Integration between paper trading routes and controller flow is MISSING
**Integration Check**: Added BUG-005-1 to fix this integration gap

### Bootstrap Paradox (#61): Circular Dependency

**Identified Cycle**:
- Frontend needs data → requires WebSocket stable
- WebSocket stable → requires proper subscriptions
- Proper subscriptions → requires session active
- Session active → requires strategies loaded
- Strategies loaded → requires proper activation flow

**Resolution**: Fix BUG-005-1 first (breaks the cycle at strategy activation)

### Theseus Paradox (#62): Core Problem Alignment

**Core Problem**: "Strategy doesn't appear, nothing works"
**Core Solution**: Ensure strategy activation pipeline executes

**Alignment Check**: BUG-005-1 directly addresses core problem. Other stories support but this is THE fix.

### Godel's Incompleteness (#69): Fundamental Limits

**What This Analysis CANNOT Check**:
- Production network conditions
- Real-time performance under load
- User behavior edge cases

**Acknowledged Gaps**: Recommend staging environment testing before production deploy.

### Scope Integrity Check (#70): Original Task Coverage

**Original Task**: "Strategy monitoring doesn't work, nothing starts"

| Element | Status |
|---------|--------|
| Strategy activation | ADDRESSED (BUG-005-1) |
| State Machine display | ADDRESSED (BUG-005-1) |
| WebSocket stability | ADDRESSED (BUG-005-2) |
| Connection reconnects | ADDRESSED (BUG-005-2) |
| Subscription validation | ADDRESSED (BUG-005-3) |
| Subscription restoration | ADDRESSED (BUG-005-4) |
| Tests to prevent regression | ADDRESSED (BUG-005-5) |

**SIMPLIFIED WITHOUT DECISION**: None found. All elements addressed.

---

## Implementation Order

**Phase 1: Core Fix (MUST DO)**
1. BUG-005-1: Strategy Activation Pipeline ← THE critical fix
2. BUG-005-2: WebSocket Heartbeat Unification

**Phase 2: Stability (SHOULD DO)**
3. BUG-005-3: Message Validation
4. BUG-005-4: Subscription Restoration

**Phase 3: Verification (MANDATORY)**
5. BUG-005-5: TEA Integration Tests ← Required before merge

---

## Definition of Done

1. **Functional**: Paper trading session shows strategy in State Machine Overview
2. **Stable**: WebSocket stable for 10+ minutes
3. **Tested**: All TEA tests pass
4. **Verified**: Manual test of full flow succeeds
5. **Documented**: Root cause and fix documented in bug_005.md

---

## Files Summary

| File | Change |
|------|--------|
| `src/api/paper_trading_routes.py` | Add strategy activation calls |
| `src/application/controllers/unified_trading_controller.py` | May extract activation method |
| `frontend/src/hooks/useWebSocket.ts` | Remove duplicate heartbeat OR increase timeout |
| `frontend/src/services/websocket.ts` | Keep single heartbeat, add validation |
| `tests/integration/test_paper_trading_activation.py` | NEW - Integration test |
| `tests/integration/test_websocket_stability.py` | NEW - Stability test |
| `tests/e2e/test_paper_trading_dashboard.py` | NEW - E2E test |

---

*Generated by PM Agent (John) - BMAD Framework*
*Deep Analysis Applied - Root Causes Identified*
*Verification Paradoxes: #55-62, #69-70 Applied*
*Source: docs/bug_005.md*
