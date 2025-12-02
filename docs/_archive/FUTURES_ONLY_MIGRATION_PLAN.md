# FUTURES-ONLY Migration Plan - Complete System Conversion

**Date**: 2025-11-24
**Requirement**: **SPOT API ZABRONIONY - TYLKO FUTURES**
**Status**: ⚠️ CRITICAL ARCHITECTURAL ISSUE - Comprehensive Analysis Complete

---

## Executive Summary

**CRITICAL FINDING**: System zawiera MIESZANE użycie Spot i Futures API, które musi być wykorzenione.

**Scope**:
- ❌ **10 metod** w `MexcRealAdapter` używa Spot API (`/api/v3/*`)
- ❌ **3 komponenty** używają `MexcRealAdapter` bezpośrednio
- ❌ **1 komponent** (`WalletService`) używa Spot adapter dla balance
- ✅ **`MexcFuturesAdapter` istnieje** ale jest używany TYLKO przez `LiveOrderManager` i `PositionSyncService`

**Impact**: Kompletna refaktoryzacja wymagana - nie ma backward compatibility, to jest clean migration.

---

## Part 1: COMPLETE AUDIT - All Spot API Usage

### A. Files Using Spot API Endpoints (`/api/v3/*`)

| File | Lines | Methods/Endpoints | Status |
|------|-------|-------------------|--------|
| `src/infrastructure/adapters/mexc_adapter.py` | 268, 274 | `get_balances()` → `/api/v3/account` | ❌ SPOT |
| `src/infrastructure/adapters/mexc_adapter.py` | 325, 446, 513 | `create_market_order()`, `create_limit_order()` → `/api/v3/order` | ❌ SPOT |
| `src/infrastructure/adapters/mexc_adapter.py` | 354, 567 | `cancel_order()` → `/api/v3/order` | ❌ SPOT |
| `src/infrastructure/adapters/mexc_adapter.py` | 383 | `get_open_orders()` → `/api/v3/openOrders` | ❌ SPOT |
| `src/infrastructure/adapters/mexc_adapter.py` | 632 | `get_order_status()` → `/api/v3/order` | ❌ SPOT |
| `src/core/health_monitor.py` | 934 | Health check → `/api/v3/time` | ❌ SPOT |

**Total Spot Endpoints**: 6 distinct endpoints, 10 method calls

### B. Components Using `MexcRealAdapter` (Spot Adapter)

| Component | File | Usage | Impact |
|-----------|------|-------|--------|
| **WalletService** | `src/application/services/wallet_service.py:30` | Calls `adapter.get_balances()` | ❌ Returns Spot balance |
| **Container** | `src/infrastructure/container.py:909` | Creates Spot adapter for WalletService | ❌ Factory creates wrong adapter |
| **HealthMonitor** | `src/core/health_monitor.py:922` | Creates Spot adapter for health checks | ❌ Health checks use Spot endpoint |

### C. Components CORRECTLY Using `MexcFuturesAdapter`

| Component | File | Status |
|-----------|------|--------|
| **LiveOrderManager** | `src/domain/services/order_manager_live.py:87` | ✅ Futures (correct) |
| **PositionSyncService** | `src/domain/services/position_sync_service.py:71` | ✅ Futures (correct) |

---

## Part 2: ARCHITECTURAL PROBLEM ANALYSIS

### Problem 1: `MexcRealAdapter` is Parent of `MexcFuturesAdapter`

```
MexcRealAdapter (base_url="https://api.mexc.com")  ← SPOT
    ├─ get_balances() → /api/v3/account  ← SPOT
    ├─ create_market_order() → /api/v3/order  ← SPOT
    ├─ cancel_order() → /api/v3/order  ← SPOT
    └─ ... (all methods use SPOT endpoints)
         ↓ INHERITS
MexcFuturesAdapter (base_url="https://contract.mexc.com")  ← FUTURES
    ├─ place_futures_order() → /fapi/v1/order  ← FUTURES (overridden)
    ├─ set_leverage() → /fapi/v1/leverage  ← FUTURES (new method)
    └─ INHERITS get_balances() → /api/v3/account  ← PROBLEM: Uses parent's SPOT endpoint!
```

**Issue**: `MexcFuturesAdapter` herits ALL Spot methods from parent. When called with Futures `base_url`:
- `https://contract.mexc.com + /api/v3/account` → **INVALID URL** (404 error)

### Problem 2: WalletService Uses Wrong Adapter

```
WalletService
  → calls adapter.get_balances()
  → Container creates via create_mexc_adapter()
  → Returns MexcRealAdapter(base_url="https://api.mexc.com")
  → Calls /api/v3/account (SPOT)
  → Returns SPOT wallet balance (not Futures wallet balance)
```

**Impact**: User has 10,000 USDT in Futures wallet but WalletService shows Spot wallet (maybe 0 USDT) ❌

### Problem 3: No Clear Separation of Spot vs Futures

**Current State**:
- `MexcRealAdapter` = Spot adapter (but name doesn't indicate this!)
- `MexcFuturesAdapter` = Futures adapter (but inherits Spot methods!)
- No explicit "**SPOT ZABRONIONY**" warnings in code

**Confusion**: Developer might use `MexcRealAdapter` thinking it's "real" (vs paper) but it's actually "Spot" (vs Futures)

---

## Part 3: SOLUTION DESIGN - Futures-Only Architecture

### Strategy: RENAME + DEPRECATE + MIGRATE

**Goal**: Make Spot usage impossible at compile/import time.

### Step 1: Rename `MexcRealAdapter` → `MexcSpotAdapter` (DEPRECATED)

**Rationale**:
1. Name clearly indicates it's SPOT (which is forbidden)
2. Any import of `MexcSpotAdapter` will be obvious code smell
3. Easier to grep/search for violations

**Changes**:
```python
# src/infrastructure/adapters/mexc_adapter.py

# ❌ DEPRECATED - SPOT API IS FORBIDDEN
# This adapter uses MEXC Spot API (https://api.mexc.com, /api/v3/* endpoints).
# System requirement: FUTURES ONLY - DO NOT USE THIS ADAPTER.
# Use MexcFuturesAdapter instead.
#
# Kept for reference only. Will be removed in future cleanup.
class MexcSpotAdapter:  # Renamed from MexcRealAdapter
    """
    ❌ DEPRECATED: SPOT API IS FORBIDDEN - DO NOT USE

    This adapter was designed for MEXC Spot API which is not compatible
    with the system's Futures-only architecture.

    Use MexcFuturesAdapter instead.
    """
    def __init__(self, ...):
        raise RuntimeError(
            "SPOT API IS FORBIDDEN. MexcSpotAdapter cannot be used. "
            "System requirement: Futures-only trading. "
            "Use MexcFuturesAdapter instead."
        )
```

### Step 2: Make `MexcFuturesAdapter` Standalone (No Inheritance)

**Rationale**:
1. Remove dependency on Spot parent class
2. Implement ALL methods using Futures endpoints
3. No risk of accidentally calling inherited Spot methods

**Architecture**:
```
OLD (❌ WRONG):
MexcSpotAdapter (Spot endpoints)
     ↓ inherits
MexcFuturesAdapter (mix of Futures + inherited Spot)

NEW (✅ CORRECT):
MexcSpotAdapter (❌ DEPRECATED - raises RuntimeError)
MexcFuturesAdapter (✅ Futures-only, no inheritance)
```

**Implementation**:
```python
# src/infrastructure/adapters/mexc_futures_adapter.py

# ✅ FUTURES ONLY - This is the ONLY allowed adapter
class MexcFuturesAdapter:  # NO INHERITANCE
    """
    MEXC Futures API Adapter - FUTURES ONLY

    ✅ System requirement: This is the ONLY allowed MEXC adapter.
    ❌ DO NOT use MexcSpotAdapter (Spot API is forbidden).

    Base URL: https://contract.mexc.com
    Endpoints: /fapi/v1/*

    Supported operations:
    - Futures account balance (/fapi/v1/account)
    - Futures order placement (/fapi/v1/order)
    - Position management (/fapi/v1/position)
    - Leverage configuration (/fapi/v1/leverage)
    """

    def __init__(self, api_key: str, api_secret: str, logger: StructuredLogger):
        self.api_key = api_key
        self.api_secret = api_secret
        self.logger = logger
        self.base_url = "https://contract.mexc.com"  # ✅ Futures base URL (hardcoded)
        # ... initialize circuit breaker, rate limiter, etc.

    async def get_balances(self) -> Dict[str, Any]:
        """
        Get Futures account balance.

        ✅ Uses Futures endpoint: /fapi/v1/account
        ❌ Does NOT use Spot endpoint: /api/v3/account (forbidden)
        """
        response = await self._make_request("GET", "/fapi/v1/account", signed=True)
        # Transform response to standard format
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "assets": {
                "USDT": {
                    "free": float(response.get("availableBalance", 0)),
                    "locked": float(response.get("frozenBalance", 0))
                }
            },
            "source": "mexc_futures_api"  # ✅ Clearly marked as Futures
        }

    async def create_market_order(self, ...) -> str:
        """Futures market order"""
        return await self._make_request("POST", "/fapi/v1/order", ...)

    async def cancel_order(self, ...) -> bool:
        """Cancel Futures order"""
        return await self._make_request("DELETE", "/fapi/v1/order", ...)

    async def get_open_orders(self, ...) -> List[Dict[str, Any]]:
        """Get open Futures orders"""
        return await self._make_request("GET", "/fapi/v1/openOrders", ...)

    async def get_order_status(self, ...) -> OrderStatusResponse:
        """Get Futures order status"""
        return await self._make_request("GET", "/fapi/v1/order", ...)

    async def get_positions(self) -> List[PositionResponse]:
        """Get Futures positions"""
        return await self._make_request("GET", "/fapi/v1/position/list", ...)

    # ... all other methods using /fapi/v1/* endpoints
```

### Step 3: Update `Container` - Remove Spot Adapter Factory

**Changes**:
```python
# src/infrastructure/container.py

# ❌ REMOVE THIS METHOD (Spot adapter forbidden)
async def create_mexc_adapter(self):
    raise RuntimeError(
        "create_mexc_adapter() is forbidden (creates Spot adapter). "
        "Use create_mexc_futures_adapter() instead."
    )

# ✅ KEEP THIS - The ONLY allowed factory
async def create_mexc_futures_adapter(self):
    """
    Create MEXC Futures adapter.

    ✅ System requirement: Futures-only trading.
    ❌ DO NOT create Spot adapter (forbidden).
    """
    from ..infrastructure.adapters.mexc_futures_adapter import MexcFuturesAdapter

    return MexcFuturesAdapter(
        api_key=self.settings.exchanges.mexc_api_key,
        api_secret=self.settings.exchanges.mexc_api_secret,
        logger=self.logger
    )

# ✅ UPDATE THIS - Use Futures adapter for WalletService
async def create_wallet_service(self):
    """Create wallet service with Futures adapter"""
    # ... (two-phase initialization as before)

    # ✅ Use Futures adapter (NOT Spot)
    adapter = await asyncio.wait_for(
        self.create_mexc_futures_adapter(),  # ✅ Futures adapter
        timeout=10.0
    )

    wallet_service._adapter = adapter
    # ...
```

### Step 4: Update HealthMonitor - Use Futures Endpoint

**Changes**:
```python
# src/core/health_monitor.py:934

# OLD (❌ WRONG):
return await adapter._make_request("GET", "/api/v3/time", signed=False)  # Spot endpoint

# NEW (✅ CORRECT):
return await adapter._make_request("GET", "/fapi/v1/time", signed=False)  # Futures endpoint
```

### Step 5: Add Warnings to All Imports

**Add to files that import adapters**:
```python
# ❌ SPOT API IS FORBIDDEN - DO NOT IMPORT MexcSpotAdapter
# ✅ Use MexcFuturesAdapter instead
from ..infrastructure.adapters.mexc_futures_adapter import MexcFuturesAdapter
```

---

## Part 4: IMPLEMENTATION STEPS (Sequential, Verified)

### Phase 1: Deprecate Spot Adapter (No Breaking Changes Yet)

**Goal**: Mark Spot adapter as forbidden without breaking existing code.

**Tasks**:
1. ✅ Rename `MexcRealAdapter` → `MexcSpotAdapter` (update all imports)
2. ✅ Add `raise RuntimeError()` in `__init__` with clear message
3. ✅ Add deprecation warnings to docstring
4. ✅ Update all imports: `from .mexc_adapter import MexcSpotAdapter`
5. ✅ Git commit: "refactor: deprecate MexcSpotAdapter (Spot API forbidden)"

**Verification**:
- [ ] Backend fails to start (RuntimeError in WalletService init)
- [ ] Error message clearly states "SPOT API FORBIDDEN"

### Phase 2: Implement Standalone MexcFuturesAdapter

**Goal**: Create complete Futures adapter with NO Spot dependencies.

**Tasks**:
1. ✅ Copy all methods from `MexcSpotAdapter` to `MexcFuturesAdapter`
2. ✅ Replace ALL `/api/v3/*` endpoints with `/fapi/v1/*`
3. ✅ Update `base_url` to `https://contract.mexc.com` (hardcoded)
4. ✅ Update response parsing for Futures API format
5. ✅ Add docstrings: "✅ Futures endpoint" / "❌ NOT Spot endpoint"
6. ✅ Remove inheritance: `class MexcFuturesAdapter:` (not extending anything)
7. ✅ Git commit: "feat: implement standalone MexcFuturesAdapter (Futures-only)"

**Verification**:
- [ ] `MexcFuturesAdapter` has NO imports from `mexc_adapter.py`
- [ ] All methods use `/fapi/v1/*` endpoints (grep verification)
- [ ] No `super()` calls or parent class references

### Phase 3: Update Container Factories

**Goal**: Remove Spot adapter factory, keep only Futures.

**Tasks**:
1. ✅ Make `create_mexc_adapter()` raise RuntimeError
2. ✅ Update `create_wallet_service()` to use `create_mexc_futures_adapter()`
3. ✅ Update `create_live_order_manager()` - verify uses Futures adapter (should already be correct)
4. ✅ Update `create_position_sync_service()` - verify uses Futures adapter (should already be correct)
5. ✅ Git commit: "refactor: container uses Futures adapter only"

**Verification**:
- [ ] Grep for `create_mexc_adapter()` → only one location (deprecation stub)
- [ ] All components use `create_mexc_futures_adapter()`

### Phase 4: Update HealthMonitor

**Goal**: Health checks use Futures endpoint.

**Tasks**:
1. ✅ Change `/api/v3/time` → `/fapi/v1/time` in health check
2. ✅ Update `MexcSpotAdapter` → `MexcFuturesAdapter` import
3. ✅ Git commit: "fix: health monitor uses Futures endpoint"

**Verification**:
- [ ] Health check calls Futures API
- [ ] No Spot endpoints in health_monitor.py

### Phase 5: Update Tests

**Goal**: All tests use Futures adapter, no Spot.

**Tasks**:
1. ✅ Update `test_mexc_adapter.py` → `test_mexc_futures_adapter.py`
2. ✅ Replace `MexcRealAdapter` → `MexcFuturesAdapter` in all tests
3. ✅ Update mocked endpoints: `/api/v3/*` → `/fapi/v1/*`
4. ✅ Add new test: `test_spot_adapter_raises_error()` (verify RuntimeError)
5. ✅ Git commit: "test: update all tests for Futures-only architecture"

**Verification**:
- [ ] `pytest tests_e2e/unit/test_mexc_futures_adapter.py` passes
- [ ] No references to `/api/v3/*` in test files (grep verification)

### Phase 6: Backend Startup & Integration Test

**Goal**: Backend starts successfully and all endpoints work.

**Tasks**:
1. ✅ Start backend: `.\start_all.ps1`
2. ✅ Verify port 8080 listening: `Test-NetConnection 127.0.0.1 -Port 8080`
3. ✅ Test health endpoint: `curl http://localhost:8080/health`
4. ✅ Test wallet endpoint: `curl http://localhost:8080/wallet/balance` (with auth token)
5. ✅ Test start session: Paper trading session
6. ✅ Verify dashboard loads
7. ✅ Git commit: "verify: Futures-only system working end-to-end"

**Verification**:
- [ ] Backend starts without errors
- [ ] All API endpoints return 200 (not 500/503)
- [ ] Dashboard shows correct balance (Futures wallet, not Spot)
- [ ] Can create/cancel orders
- [ ] Positions display correctly

### Phase 7: Cleanup & Documentation

**Goal**: Remove dead Spot code, document architecture.

**Tasks**:
1. ✅ Delete `MexcSpotAdapter` class (keep file as reference with deprecation notice)
2. ✅ Update `CLAUDE.md`: "SPOT API FORBIDDEN - Futures Only"
3. ✅ Update `docs/infrastructure/MEXC_INTEGRATION.md`: Document Futures architecture
4. ✅ Add warning comments to all exchange-related files
5. ✅ Git commit: "docs: document Futures-only architecture"

**Verification**:
- [ ] No active code imports `MexcSpotAdapter`
- [ ] Documentation clearly states "Futures-only"
- [ ] All comments reference Futures endpoints

---

## Part 5: TESTING STRATEGY

### Unit Tests (Phase 5)

**File**: `tests_e2e/unit/test_mexc_futures_adapter.py`

**Tests**:
1. `test_get_balances_uses_futures_endpoint()` - Verify `/fapi/v1/account`
2. `test_create_market_order_uses_futures_endpoint()` - Verify `/fapi/v1/order`
3. `test_cancel_order_uses_futures_endpoint()` - Verify `/fapi/v1/order`
4. `test_get_open_orders_uses_futures_endpoint()` - Verify `/fapi/v1/openOrders`
5. `test_get_order_status_uses_futures_endpoint()` - Verify `/fapi/v1/order`
6. `test_base_url_is_futures()` - Verify `base_url == "https://contract.mexc.com"`
7. `test_spot_adapter_raises_error()` - Verify `MexcSpotAdapter()` raises RuntimeError

### Integration Tests (Phase 6)

**Manual Testing Checklist**:
- [ ] Start backend successfully
- [ ] Health check passes
- [ ] Wallet balance endpoint returns Futures balance
- [ ] Start paper trading session
- [ ] Dashboard displays correct data
- [ ] Create market order (paper trading)
- [ ] Cancel order
- [ ] View positions

**Automated E2E Test**:
```python
# tests_e2e/e2e/test_futures_only_flow.py

async def test_futures_only_architecture():
    """Verify system uses ONLY Futures API (no Spot)"""

    # 1. Verify Container creates Futures adapter only
    container = Container(settings, event_bus, logger)
    adapter = await container.create_mexc_futures_adapter()
    assert adapter.base_url == "https://contract.mexc.com"

    # 2. Verify WalletService uses Futures adapter
    wallet_service = await container.create_wallet_service()
    balance = wallet_service.get_balance()
    assert balance["source"] == "mexc_futures_api"  # Not "mexc_api" (Spot)

    # 3. Verify no Spot endpoints called
    # (Mock aiohttp and assert all calls are to contract.mexc.com, not api.mexc.com)

    # 4. Verify Spot adapter raises error
    with pytest.raises(RuntimeError, match="SPOT API IS FORBIDDEN"):
        from src.infrastructure.adapters.mexc_adapter import MexcSpotAdapter
        adapter = MexcSpotAdapter(api_key="test", api_secret="test", logger=logger)
```

---

## Part 6: RISK ANALYSIS & MITIGATION

### Risk 1: Breaking Changes (HIGH)

**Risk**: Renaming `MexcRealAdapter` → `MexcSpotAdapter` breaks existing code.

**Mitigation**:
- Phase 1 updates ALL imports in single commit
- Comprehensive grep search ensures no missed references
- Tests updated simultaneously
- Git allows easy rollback if issues found

### Risk 2: Futures API Differences (MEDIUM)

**Risk**: Futures API response format differs from Spot, causing parsing errors.

**Mitigation**:
- Thorough research of MEXC Futures API documentation
- Unit tests with mocked Futures responses
- Manual testing with real API before deploying
- Detailed error logging for debugging

### Risk 3: Missing Futures Endpoints (LOW)

**Risk**: Some Spot endpoints might not have Futures equivalents.

**Mitigation**:
- Audit ALL Spot endpoints used
- Verify Futures API has equivalents (documentation check)
- If missing, implement workaround or alternative approach

**Verified Futures Endpoints**:
- ✅ `/fapi/v1/account` (balance) - EXISTS
- ✅ `/fapi/v1/order` (create/cancel/status) - EXISTS
- ✅ `/fapi/v1/openOrders` (list orders) - EXISTS
- ✅ `/fapi/v1/position/list` (positions) - EXISTS (already implemented)
- ✅ `/fapi/v1/leverage` (set leverage) - EXISTS (already implemented)
- ⚠️ `/fapi/v1/time` (health check) - NEEDS VERIFICATION

### Risk 4: Test Coverage Gaps (MEDIUM)

**Risk**: Tests don't catch all Futures-specific issues.

**Mitigation**:
- Comprehensive unit test suite (7+ tests)
- Integration tests with real API
- Manual QA testing before declaring success
- Staged rollout (dev → staging → production)

---

## Part 7: SUCCESS CRITERIA (100% Verification Required)

### Code Verification

- [ ] **NO references to `/api/v3/*` in production code** (grep verification)
- [ ] **NO references to `api.mexc.com` in production code** (grep verification)
- [ ] **NO imports of `MexcSpotAdapter` except deprecation stub** (grep verification)
- [ ] **ALL adapters use `contract.mexc.com`** (grep verification)
- [ ] **ALL endpoints use `/fapi/v1/*`** (grep verification)

### Test Verification

- [ ] **Unit tests: 7/7 passing** for `MexcFuturesAdapter`
- [ ] **E2E test passing**: `test_futures_only_architecture()`
- [ ] **No test uses Spot endpoints** (grep verification)
- [ ] **Spot adapter test verifies RuntimeError** (test_spot_adapter_raises_error)

### Runtime Verification

- [ ] **Backend starts without errors**
- [ ] **Port 8080 listening** (`Test-NetConnection` returns True)
- [ ] **Health check passes** (`/health` returns 200)
- [ ] **Wallet endpoint works** (`/wallet/balance` returns Futures balance)
- [ ] **Dashboard loads** (no infinite loading)
- [ ] **Can start paper trading session**
- [ ] **Can create/cancel orders**
- [ ] **Positions display correctly**

### Documentation Verification

- [ ] **CLAUDE.md states "SPOT FORBIDDEN - FUTURES ONLY"**
- [ ] **All adapter files have warning comments**
- [ ] **Container has clear comments about Futures-only**
- [ ] **MEXC_INTEGRATION.md documents Futures architecture**

---

## Part 8: ROLLBACK PLAN

If implementation fails at any phase:

1. **Identify failing phase** (check git log)
2. **Revert to previous commit**: `git reset --hard <commit-before-phase>`
3. **Analyze failure logs**
4. **Fix issue** in isolated branch
5. **Re-test** before attempting migration again

**Critical Commits** (for easy rollback):
- Phase 1: "refactor: deprecate MexcSpotAdapter"
- Phase 2: "feat: implement standalone MexcFuturesAdapter"
- Phase 3: "refactor: container uses Futures adapter only"
- Phase 6: "verify: Futures-only system working end-to-end"

---

## Part 9: TIMELINE ESTIMATE

**Realistic Timeline** (assuming no major API incompatibilities):

- Phase 1 (Deprecate): 30 minutes
- Phase 2 (Implement): 2-3 hours (research + implementation)
- Phase 3 (Container): 30 minutes
- Phase 4 (HealthMonitor): 15 minutes
- Phase 5 (Tests): 1-2 hours
- Phase 6 (Verification): 1 hour (manual testing)
- Phase 7 (Cleanup): 30 minutes

**Total**: 6-8 hours of focused work

---

## NEXT ACTION

**Awaiting your approval to proceed with Phase 1.**

Once approved, I will:
1. Execute Phase 1 (deprecate Spot adapter)
2. Verify it breaks (as expected)
3. Continue through Phases 2-7 sequentially
4. Report results ONLY when 100% verified

**I will NOT claim success until ALL criteria in Part 7 are met and verified with evidence.**
