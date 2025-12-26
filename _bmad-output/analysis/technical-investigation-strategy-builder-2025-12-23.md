# Technical Investigation: Strategy Builder Execution Failure

**Date:** 2025-12-23
**Investigators:** Mary (Analyst), Winston (Architect), Amelia (Dev), Murat (Test Architect)
**Status:** Root Cause Identified
**Severity:** Critical

---

## Executive Summary

Investigation into why Strategy Builder strategies are not executing during trading sessions revealed a **critical race condition** in the session startup flow. Strategies created via the frontend REST API are saved to QuestDB but are not loaded into the StrategyManager's in-memory cache before activation is attempted, causing activation to fail silently.

---

## 1. System Architecture Overview

### 1.1 Strategy Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STRATEGY SYSTEM ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────────────┐    ┌─────────────────────┐     │
│  │  Frontend   │───▶│  REST API           │───▶│  QuestDB            │     │
│  │  Strategy   │    │  /api/strategies    │    │  strategies table   │     │
│  │  Builder    │    │  (CRUD operations)  │    │                     │     │
│  └─────────────┘    └─────────────────────┘    └─────────────────────┘     │
│                                                          │                  │
│                                                          ▼                  │
│  ┌─────────────┐    ┌─────────────────────┐    ┌─────────────────────┐     │
│  │  WebSocket  │───▶│  StrategyManager    │◀───│  load_strategies_   │     │
│  │  Session    │    │  (in-memory cache)  │    │  from_db()          │     │
│  │  Start      │    │  self.strategies    │    │                     │     │
│  └─────────────┘    └─────────────────────┘    └─────────────────────┘     │
│         │                    │                                              │
│         ▼                    ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │  active_strategies[symbol] = [Strategy, Strategy, ...]          │       │
│  │  (strategies activated for specific symbols)                    │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │  _evaluate_strategies_for_symbol(symbol)                        │       │
│  │  (called on every indicator.updated event)                      │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Strategy Builder UI | `frontend/src/components/strategy/StrategyBuilder5Section.tsx` | 5-section strategy configuration interface |
| REST API | `src/api/unified_server.py` | CRUD endpoints for strategies |
| Strategy Storage | `src/domain/services/strategy_storage_questdb.py` | QuestDB persistence layer |
| Strategy Manager | `src/domain/services/strategy_manager.py` | In-memory strategy cache + evaluation engine |
| Strategy Schema | `src/domain/services/strategy_schema.py` | Validation for 5-section format |
| WebSocket Server | `src/api/websocket_server.py` | Session management + strategy activation |
| Trading Controller | `src/application/controllers/unified_trading_controller.py` | Session lifecycle orchestration |

---

## 2. Root Cause Analysis

### 2.1 Primary Issue: Race Condition in Session Startup

**Location:** `src/api/websocket_server.py` lines 2107-2130

**The Problem:**

When a WebSocket client requests a session start, the following sequence occurs:

```python
# websocket_server.py _handle_session_start():

# Step 1: Activate strategies (HAPPENS FIRST)
activation_results = await self._activate_strategies_with_symbols(strategy_config)
#         ↑
#         └── Checks self.strategy_manager.get_all_strategies()
#             Returns strategies from self.strategies (IN-MEMORY CACHE)
#             If strategy was created AFTER server startup → NOT FOUND!

# Step 2: Start session (HAPPENS SECOND)
command_id = await self.controller.start_live_trading(...)
#         ↑
#         └── Eventually calls load_strategies_from_db()
#             But by this point, activation already FAILED!
```

**Impact:**
- Strategies created via the UI after server startup cannot be activated
- Session starts without any active strategies
- No trading signals are generated
- Users see no errors in the UI (silent failure)

### 2.2 Secondary Issue: Two Separate Storage Systems

The system has two independent strategy storage mechanisms that are not synchronized:

| Storage | Updated By | Read By |
|---------|-----------|---------|
| QuestDB (via `strategy_storage_questdb.py`) | REST API `/api/strategies` | REST API list/get operations |
| In-memory (`StrategyManager.strategies`) | `load_strategies_from_db()` | Session activation, evaluation |

**Gap:** When a strategy is created via REST API:
1. It's saved to QuestDB ✓
2. It's NOT added to `StrategyManager.strategies` ✗
3. Until `load_strategies_from_db()` is explicitly called, the strategy doesn't exist for trading

### 2.3 Tertiary Issue: Empty active_strategies Dict

Even if strategies ARE in `self.strategies`, they must be explicitly activated for specific symbols:

```python
# strategy_manager.py line 1591
async def _evaluate_strategies_for_symbol(self, symbol: str) -> None:
    if symbol not in self.active_strategies:
        return  # ← EXITS IMMEDIATELY - NO EVALUATION!
```

**Flow:**
1. `add_strategy()` → adds to `self.strategies` only
2. `activate_strategy_for_symbol()` → adds to `self.active_strategies[symbol]`
3. If activation fails, `active_strategies` remains empty
4. All indicator events are ignored

---

## 3. Evidence

### 3.1 Code Evidence

**Activation check (websocket_server.py:2281):**
```python
if strategy_name not in available_strategy_names:
    results["success"] = False
    results["errors"].append(f"Strategy '{strategy_name}' not found")
```

**DB reload timing (unified_trading_controller.py:905):**
```python
# This happens AFTER activation is attempted
loaded_count = await self.strategy_manager.load_strategies_from_db()
```

**Evaluation guard (strategy_manager.py:1591):**
```python
if symbol not in self.active_strategies:
    return  # Silent exit - no strategies to evaluate
```

### 3.2 Expected Logs During Failure

When this bug occurs, you should see:
```
ERROR strategy_activation_failed: Strategy 'xxx' not found
```
or
```
DEBUG strategy_manager.skipping_evaluation: symbol not in active_strategies
```

---

## 4. 5-Section Strategy Architecture

For reference, this is the complete strategy structure being used:

### 4.1 Section Overview

| Section | Code | Purpose | Triggers |
|---------|------|---------|----------|
| S1 | `signal_detection` | Detect trading opportunity | Entry to SIGNAL_DETECTED state |
| O1 | `signal_cancellation` | Cancel stale/invalid signals | Return to MONITORING, cooldown starts |
| Z1 | `entry_conditions` | Confirm entry timing | Move to ENTRY_EVALUATION state |
| ZE1 | `close_order_detection` | Exit position conditions | Close position, return to MONITORING |
| E1 | `emergency_exit` | Emergency override | Immediate exit, long cooldown |

### 4.2 State Machine

```
MONITORING ─[S1 true]──▶ SIGNAL_DETECTED ─[O1 true]──▶ SIGNAL_CANCELLED
                              │                              │
                              │                              ▼
                              │                         (cooldown)
                              │                              │
                              ▼                              ▼
                    [Z1 true] ENTRY_EVALUATION ────────▶ MONITORING
                              │
                              ▼
                       POSITION_ACTIVE ─[ZE1 true]──▶ EXITED ──▶ MONITORING
                              │
                              └─[E1 true]──▶ EMERGENCY_EXIT ──▶ (long cooldown)
```

### 4.3 JSON Schema (Frontend → Backend)

```json
{
  "strategy_name": "my_pump_strategy",
  "s1_signal": {
    "conditions": [
      { "id": "cond1", "indicatorId": "pump_magnitude_pct", "operator": ">=", "value": 5 }
    ]
  },
  "z1_entry": {
    "conditions": [...],
    "positionSize": { "type": "percentage", "value": 2 },
    "stopLoss": { "enabled": true, "offsetPercent": 5 },
    "takeProfit": { "enabled": true, "offsetPercent": 10 }
  },
  "ze1_close": { "conditions": [...] },
  "o1_cancel": { "timeoutSeconds": 300, "conditions": [...] },
  "emergency_exit": { "conditions": [...], "cooldownMinutes": 30, "actions": {...} },
  "global_limits": {
    "base_position_pct": 0.02,
    "max_leverage": 3,
    "stop_loss_buffer_pct": 10
  }
}
```

---

## 5. Recommended Fixes

### 5.1 Fix 1: Reload Strategies Before Activation (Quick Fix)

**File:** `src/api/websocket_server.py`
**Location:** `_handle_session_start()` method, before line 2107

```python
# Add this BEFORE activation:
if self.strategy_manager:
    await self.strategy_manager.load_strategies_from_db()

# Then activate
activation_results = await self._activate_strategies_with_symbols(strategy_config)
```

**Pros:** Simple, minimal code change
**Cons:** Adds latency to session start, doesn't solve real-time sync

### 5.2 Fix 2: Notify StrategyManager on Strategy CRUD (Recommended)

**Approach:** When REST API creates/updates/deletes a strategy, notify StrategyManager

**File:** `src/api/unified_server.py`

```python
@app.post("/api/strategies")
async def create_strategy(request: Request, ...):
    # ... existing code to save to QuestDB ...

    # NEW: Notify StrategyManager
    strategy_manager = getattr(app.state, 'websocket_api_server', None)
    if strategy_manager and hasattr(strategy_manager, 'strategy_manager'):
        await strategy_manager.strategy_manager.load_strategies_from_db()

    return _json_ok({"strategy": {...}})
```

**Pros:** Real-time sync, strategies immediately available
**Cons:** More complex, needs careful error handling

### 5.3 Fix 3: Add Strategy Directly to Manager (Alternative)

**Approach:** When REST API creates a strategy, add it directly to StrategyManager

**File:** `src/api/unified_server.py`

```python
# After saving to QuestDB, also add to in-memory manager
strategy_manager.upsert_strategy_from_config(strategy_data)
```

**Pros:** Fastest option, no DB reload needed
**Cons:** Need to handle update/delete cases, potential consistency issues

---

## 6. Additional Issues Identified

### 6.1 Indicator Type Case Sensitivity

**Location:** `strategy_manager.py:1567`

```python
storage_key = indicator_type if indicator_type else indicator_name.lower()
```

The code lowercases indicator types for storage, but condition evaluation may not match if the strategy uses different casing.

**Recommendation:** Ensure all indicator type comparisons are case-insensitive.

### 6.2 Hardcoded Symbol in StrategyEvaluator

**Location:** `src/engine/strategy_evaluator.py:156`

```python
def _extract_symbol_from_indicator(self, indicator_name: str) -> str:
    return "BTC_USDT"  # Default for now ← HARDCODED!
```

This legacy evaluator (different from StrategyManager) has a hardcoded symbol.

**Recommendation:** Remove or fix this legacy code if it's still in use.

### 6.3 No UI Feedback on Activation Failure

When strategy activation fails, the error is logged but not surfaced to the UI in a clear way.

**Recommendation:** Return activation errors in WebSocket response and display in frontend.

---

## 7. Testing Recommendations

### 7.1 Unit Tests Needed

1. `test_strategy_created_after_startup_can_be_activated`
2. `test_load_strategies_from_db_refreshes_cache`
3. `test_activation_fails_gracefully_with_unknown_strategy`
4. `test_indicator_type_matching_is_case_insensitive`

### 7.2 Integration Tests Needed

1. Create strategy via REST API → Start session → Verify strategy is active
2. Create strategy → Start session → Verify signals are generated
3. Update strategy → Verify changes take effect without restart

### 7.3 E2E Test Scenario

```gherkin
Feature: Strategy Execution
  Scenario: Newly created strategy executes during session
    Given I create a new strategy via the Strategy Builder
    And the strategy has valid S1 conditions for pump detection
    When I start a paper trading session with that strategy
    And a pump event occurs matching S1 conditions
    Then a signal should be generated
    And the signal should appear in the UI
```

---

## 8. Files Modified for Fix

| File | Change Required |
|------|-----------------|
| `src/api/websocket_server.py` | Add `load_strategies_from_db()` before activation |
| `src/api/unified_server.py` | (Optional) Notify manager on strategy CRUD |
| `src/domain/services/strategy_manager.py` | (Optional) Add real-time sync method |

---

## 9. Conclusion

The Strategy Builder frontend is working correctly. The backend storage (QuestDB) is working correctly. The issue is a **synchronization gap** between the REST API storage layer and the StrategyManager's in-memory cache, combined with a **race condition** where activation is attempted before the cache is refreshed.

**Priority:** This is a P0 bug that completely blocks strategy execution for any strategy created after server startup.

**Estimated Fix Time:**
- Quick fix (5.1): 30 minutes
- Recommended fix (5.2): 2-4 hours including testing

---

## Appendix A: Key File Locations

```
src/
├── api/
│   ├── unified_server.py          # REST API endpoints
│   └── websocket_server.py        # Session management, activation
├── domain/services/
│   ├── strategy_manager.py        # In-memory cache, evaluation engine
│   ├── strategy_schema.py         # Validation
│   └── strategy_storage_questdb.py # QuestDB persistence
├── application/controllers/
│   └── unified_trading_controller.py # Session lifecycle
└── engine/
    └── strategy_evaluator.py      # Legacy evaluator (may be unused)

frontend/src/
├── components/strategy/
│   └── StrategyBuilder5Section.tsx # UI component
└── services/
    ├── api.ts                     # REST client
    └── strategiesApi.ts           # Strategy-specific API
```

---

*Report generated by BMAD Party Mode - Technical Investigation Team*
