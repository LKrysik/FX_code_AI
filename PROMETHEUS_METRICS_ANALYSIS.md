# Prometheus Metrics Dependency Analysis

**Date:** 2025-11-08
**Issue:** ModuleNotFoundError: No module named 'prometheus_client'
**Severity:** CRITICAL - Application cannot start

---

## EXECUTIVE SUMMARY

**Found 2 CRITICAL Issues:**

1. **Missing Dependency:** `prometheus-client` not in requirements.txt (PRIMARY CAUSE)
2. **Async/Await Bug:** Container calls `subscribe_to_events()` sync but method is now async (SECONDARY BUG - introduced in PHASE 2)

**Impact:** Application startup fails completely

**Root Cause:** Incomplete dependency management + async refactoring bug

---

## DETAILED ARCHITECTURE ANALYSIS

### Issue #1: Missing prometheus-client Dependency (CRITICAL)

**File:** `requirements.txt`

**Problem:**
- `src/infrastructure/monitoring/prometheus_metrics.py` imports from `prometheus_client`
- Package `prometheus-client` is **NOT** in requirements.txt
- When Python tries to import, raises ModuleNotFoundError

**Evidence:**

**requirements.txt (Current):**
```txt
asyncio
aiohttp
aiofiles
websockets
pandas
pydantic
pydantic-settings
python-dotenv
plotly
protobuf
dash
psutil
fastapi
uvicorn
PyYAML
PyJWT
redis

# QuestDB dependencies
asyncpg
psycopg2-binary
questdb>=4.0.0,<5.0.0
requests
```

**Missing:** `prometheus-client`

**Import Statement (prometheus_metrics.py:23):**
```python
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
```

**Actual Error:**
```python
ModuleNotFoundError: No module named 'prometheus_client'
```

**Impact:**
- Application cannot start
- Container.create_prometheus_metrics() fails
- unified_server.py lifespan startup aborted

**Affected Files:**
1. `src/infrastructure/monitoring/prometheus_metrics.py` - Uses prometheus_client
2. `tests_e2e/unit/test_prometheus_metrics.py` - Tests prometheus_metrics

**Dependency Chain:**
```
unified_server.py:269
  → container.create_prometheus_metrics()
  → from ..infrastructure.monitoring.prometheus_metrics import PrometheusMetrics
  → from prometheus_client import ...
  → ModuleNotFoundError ❌
```

---

### Issue #2: Async/Await Bug in Container (CRITICAL)

**File:** `src/infrastructure/container.py:683`

**Problem:**
- In PHASE 2, I changed `PrometheusMetrics.subscribe_to_events()` from sync to async
- Container.create_prometheus_metrics() still calls it synchronously (no await)
- This is an async function called without await - won't execute correctly

**Evidence:**

**Container.create_prometheus_metrics() (Line 683):**
```python
def _create():
    try:
        from ..infrastructure.monitoring.prometheus_metrics import (
            PrometheusMetrics,
            set_metrics_instance
        )

        metrics = PrometheusMetrics(event_bus=self.event_bus)

        # Subscribe to EventBus topics for automatic metric collection
        metrics.subscribe_to_events()  # ❌ WRONG - sync call to async method

        # ... rest of code
```

**PrometheusMetrics.subscribe_to_events() (Changed in PHASE 2):**
```python
async def subscribe_to_events(self) -> None:  # ✅ Now async
    """
    Subscribe to EventBus topics for metric collection.
    """
    if self._subscribed:
        logger.warning("PrometheusMetrics already subscribed to EventBus")
        return

    # Subscribe to all relevant EventBus topics
    await self.event_bus.subscribe("order_created", self._handle_order_created)  # Needs await
    await self.event_bus.subscribe("order_filled", self._handle_order_filled)
    # ... 12 more await calls
```

**Impact:**
- Even if prometheus_client is installed, subscribe_to_events() won't execute
- Subscriptions never complete (coroutine not awaited)
- PrometheusMetrics won't receive any events
- Metrics won't be collected
- Silent failure (no exception, but doesn't work)

**Root Cause:**
- In PHASE 2 (commit `99be9c5`), I changed subscribe_to_events() to async
- I updated all TEST files to await it
- **But I FORGOT to update Container.create_prometheus_metrics()**
- This is my bug from PHASE 2

---

## IMPACT ASSESSMENT

### Impact on Application Startup

**Current Flow (Broken):**
```
1. uvicorn starts → unified_server.py
2. lifespan() → container.create_prometheus_metrics()
3. Container._create() → from prometheus_client import ...
4. ModuleNotFoundError ❌
5. Application startup FAILS
```

**After Fix #1 (prometheus-client installed):**
```
1. uvicorn starts → unified_server.py
2. lifespan() → container.create_prometheus_metrics()
3. Container._create() → imports succeed ✅
4. metrics.subscribe_to_events() called (sync) ❌
5. Coroutine created but not awaited (warning)
6. Subscriptions NEVER complete
7. Application starts but metrics DON'T WORK
```

**After Fix #1 + Fix #2 (both fixed):**
```
1. uvicorn starts → unified_server.py
2. lifespan() → container.create_prometheus_metrics()
3. Container._create_async() → imports succeed ✅
4. await metrics.subscribe_to_events() ✅
5. All 12 subscriptions complete ✅
6. PrometheusMetrics ready to collect ✅
7. Application starts successfully ✅
8. Metrics endpoint /metrics works ✅
```

### Impact on Other Modules

**Modules that depend on PrometheusMetrics:**
1. `src/api/monitoring_routes.py` - /metrics endpoint
2. `src/api/unified_server.py` - startup initialization
3. `tests_e2e/unit/test_prometheus_metrics.py` - unit tests
4. `tests_e2e/integration/test_container_multi_agent_integration.py` - integration tests

**All will fail if PrometheusMetrics initialization fails.**

### Impact on Tests

**Test Files Affected:**
1. `tests_e2e/unit/test_prometheus_metrics.py`
   - Requires prometheus-client to import
   - Will fail with ModuleNotFoundError

2. `tests_e2e/unit/test_prometheus_metrics_standalone.py`
   - Requires prometheus-client to import
   - Will fail with ModuleNotFoundError

3. `tests_e2e/integration/test_container_multi_agent_integration.py`
   - Tests container.create_prometheus_metrics()
   - Will fail on import

**All prometheus metrics tests will fail until fixed.**

---

## ARCHITECTURAL ISSUES DISCOVERED

### Issue #1: Incomplete Dependency Management

**Problem:**
- requirements.txt doesn't match actual code dependencies
- PrometheusMetrics was added (Agent 5) but prometheus-client not added to requirements.txt
- No automated dependency validation

**Evidence:**
- prometheus_metrics.py exists since multi-agent integration
- Imports prometheus_client
- But requirements.txt never updated

**Architectural Flaw:**
- Manual dependency management prone to errors
- No CI/CD check for missing imports

**Recommendation:**
- Add prometheus-client to requirements.txt
- Consider: pip-compile or poetry for dependency management
- Consider: CI/CD check with `pip-compile --dry-run` or mypy import validation

---

### Issue #2: Sync/Async Mismatch After Refactoring

**Problem:**
- PHASE 2 refactored subscribe_to_events() to async
- Updated all test calls with await
- **Forgot to update Container factory call**
- No automated detection of this bug

**Evidence:**
- prometheus_metrics.py:141 - `async def subscribe_to_events()`
- All tests updated with await (PHASE 4)
- Container.create_prometheus_metrics():683 - still calls sync

**Architectural Flaw:**
- Factory method _create() is sync, calls async method
- No type checking catches this
- Manual search-and-replace missed this call site

**Recommendation:**
- Convert Container._create() to async _create_async()
- Add mypy or pylance type checking to CI/CD
- Use async factory pattern consistently

---

### Issue #3: Container Factory Pattern Inconsistency

**Problem:**
- Some Container factories are async, some are sync
- create_prometheus_metrics() uses sync factory _create()
- But needs to call async subscribe_to_events()
- Pattern doesn't support async initialization

**Evidence:**

**Current Pattern (Broken):**
```python
async def create_prometheus_metrics(self):
    def _create():  # ❌ Sync factory
        metrics = PrometheusMetrics(...)
        metrics.subscribe_to_events()  # ❌ Async method called sync
        return metrics
    return await self._get_or_create_singleton_async("prometheus_metrics", _create)
```

**Other factories use async pattern:**
```python
async def create_trading_persistence_service(self):
    async def _create():  # ✅ Async factory
        service = TradingPersistenceService(...)
        await service.start()  # ✅ Awaited
        return service
    return await self._get_or_create_singleton_async("...", _create)
```

**Inconsistency:**
- Some services use `async def _create()` - CORRECT
- PrometheusMetrics uses `def _create()` - INCORRECT (needs async)

**Recommendation:**
- Standardize on async factories for all services that need async initialization
- Update PrometheusMetrics factory to async pattern
- Document pattern in Container docstring

---

## ASSUMPTION VERIFICATION

### Assumption #1: prometheus-client is required

**Verification:**
```bash
grep -r "prometheus_client" src/
```

**Result:**
- Only used in prometheus_metrics.py
- NOT optional - imports at module level
- Cannot be made optional without major refactoring

**Conclusion:** ✅ Assumption CORRECT - prometheus-client is required

---

### Assumption #2: PrometheusMetrics is required for startup

**Verification:**
```python
# unified_server.py:269
prometheus_metrics = await container.create_prometheus_metrics()
app.state.prometheus_metrics = prometheus_metrics
```

**Result:**
- Called in lifespan startup (required)
- No try/except wrapper
- If fails, startup aborts

**Conclusion:** ✅ Assumption CORRECT - PrometheusMetrics is required

---

### Assumption #3: subscribe_to_events() must be awaited

**Verification:**
```python
# prometheus_metrics.py:141
async def subscribe_to_events(self) -> None:
    # ... 12 await calls inside
    await self.event_bus.subscribe("order_created", ...)
```

**Result:**
- Method is async
- Contains 12 await calls
- Must be awaited or subscriptions never complete

**Conclusion:** ✅ Assumption CORRECT - must be awaited

---

### Assumption #4: Factory _create() can be made async

**Verification:**
- Check _get_or_create_singleton_async() implementation
- Check if it supports async factories

**Code:**
```python
async def _get_or_create_singleton_async(self, service_name: str, factory_func: Callable):
    # ...
    if asyncio.iscoroutinefunction(factory_func):
        service = await factory_func()  # ✅ Supports async factories
    else:
        service = factory_func()  # Supports sync factories
```

**Conclusion:** ✅ Assumption CORRECT - _get_or_create_singleton_async() supports both sync and async factories

---

## RELATED OBJECTS AND DEPENDENCIES

### Direct Dependencies

**PrometheusMetrics depends on:**
1. prometheus_client (external package) - ❌ MISSING
2. EventBus (internal) - ✅ Available
3. StructuredLogger (internal) - ✅ Available

**Container.create_prometheus_metrics() depends on:**
1. EventBus singleton - ✅ Created first
2. prometheus_client package - ❌ MISSING

### Reverse Dependencies

**Who depends on PrometheusMetrics:**
1. `src/api/monitoring_routes.py` - /metrics endpoint
2. `src/api/unified_server.py` - app.state.prometheus_metrics
3. Tests (3 files)

**Impact if not fixed:**
- Application won't start
- /metrics endpoint unavailable
- No monitoring/metrics
- All prometheus tests fail

---

## PROPOSED SOLUTION

### Solution Overview

**Two fixes required:**

1. **Fix #1: Add prometheus-client to requirements.txt** (PRIMARY)
   - Severity: CRITICAL
   - Effort: 1 minute
   - Risk: NONE

2. **Fix #2: Make Container factory async** (SECONDARY)
   - Severity: CRITICAL
   - Effort: 5 minutes
   - Risk: LOW (well-tested pattern)

### Fix #1: Add prometheus-client to requirements.txt

**File:** `requirements.txt`

**Change:**
```diff
asyncio
aiohttp
aiofiles
websockets
pandas
pydantic
pydantic-settings
python-dotenv
plotly
protobuf
dash
psutil
fastapi
uvicorn
PyYAML
PyJWT
redis
+prometheus-client>=0.19.0,<1.0.0

# QuestDB dependencies
asyncpg
psycopg2-binary
questdb>=4.0.0,<5.0.0
requests
```

**Justification:**
- prometheus_metrics.py requires prometheus_client
- Should have been added when PrometheusMetrics was introduced
- Standard prometheus Python client library
- Version 0.19.0+ for Python 3.11+ compatibility

**Impact:**
- Users must run: `pip install -r requirements.txt`
- Or: `pip install prometheus-client`
- No code changes needed

**Risk:** NONE - just adding missing dependency

---

### Fix #2: Make Container Factory Async

**File:** `src/infrastructure/container.py`

**Current Code (Line 672-701):**
```python
async def create_prometheus_metrics(self):
    def _create():  # ❌ Sync factory
        try:
            from ..infrastructure.monitoring.prometheus_metrics import (
                PrometheusMetrics,
                set_metrics_instance
            )

            metrics = PrometheusMetrics(event_bus=self.event_bus)

            # Subscribe to EventBus topics
            metrics.subscribe_to_events()  # ❌ No await

            set_metrics_instance(metrics)
            self.logger.info("container.prometheus_metrics_created", {...})

            return metrics
        except Exception as e:
            self.logger.error("container.prometheus_metrics_creation_failed", {...})
            raise RuntimeError(f"Failed to create Prometheus metrics: {str(e)}") from e

    return await self._get_or_create_singleton_async("prometheus_metrics", _create)
```

**Fixed Code:**
```python
async def create_prometheus_metrics(self):
    async def _create():  # ✅ Async factory
        try:
            from ..infrastructure.monitoring.prometheus_metrics import (
                PrometheusMetrics,
                set_metrics_instance
            )

            metrics = PrometheusMetrics(event_bus=self.event_bus)

            # Subscribe to EventBus topics
            await metrics.subscribe_to_events()  # ✅ Awaited

            set_metrics_instance(metrics)
            self.logger.info("container.prometheus_metrics_created", {...})

            return metrics
        except Exception as e:
            self.logger.error("container.prometheus_metrics_creation_failed", {...})
            raise RuntimeError(f"Failed to create Prometheus metrics: {str(e)}") from e

    return await self._get_or_create_singleton_async("prometheus_metrics", _create)
```

**Changes:**
1. Line 672: `def _create():` → `async def _create():`
2. Line 683: `metrics.subscribe_to_events()` → `await metrics.subscribe_to_events()`

**Justification:**
- subscribe_to_events() is now async (PHASE 2 change)
- Must be awaited for subscriptions to complete
- _get_or_create_singleton_async() supports async factories
- Matches pattern used by other Container factories (e.g., create_trading_persistence_service)

**Impact:**
- PrometheusMetrics will correctly subscribe to EventBus
- All 12 event subscriptions will complete
- Metrics will be collected
- No breaking changes (async factory is transparent to caller)

**Risk:** LOW
- Pattern already used in Container (proven)
- _get_or_create_singleton_async() supports async factories
- No API changes

---

## TESTING STRATEGY

### Test Fix #1: prometheus-client Installation

**Steps:**
1. Add prometheus-client to requirements.txt
2. Run: `pip install prometheus-client`
3. Verify: `python -c "import prometheus_client; print('OK')"`
4. Expected: "OK" (no ModuleNotFoundError)

---

### Test Fix #2: Container Factory

**Steps:**
1. Fix Container.create_prometheus_metrics()
2. Start application: `python -m uvicorn src.api.unified_server:create_unified_app --factory`
3. Check logs for: "container.prometheus_metrics_created"
4. Verify EventBus subscriptions: should see 12 subscribers

**Expected Log:**
```
container.prometheus_metrics_created: {
    "subscribed_to_eventbus": True,
    "metrics_endpoint": "/metrics"
}
```

**Verification:**
```bash
curl http://localhost:8080/metrics
```

**Expected:** Prometheus metrics output (not empty)

---

### Test Integration

**Steps:**
1. Apply both fixes
2. Start application
3. Trigger order event (mock)
4. Check /metrics endpoint
5. Verify order counter incremented

**Full Test:**
```python
# Start app
# Send order_created event
await event_bus.publish("order_created", {...})

# Check metrics
response = requests.get("http://localhost:8080/metrics")
assert "orders_submitted_total" in response.text
```

---

## UPDATE TESTS (If Needed)

### Current Test Status

**All prometheus metrics tests will FAIL until Fix #1 applied:**
- `tests_e2e/unit/test_prometheus_metrics.py`
- `tests_e2e/unit/test_prometheus_metrics_standalone.py`
- `tests_e2e/integration/test_container_multi_agent_integration.py` (prometheus tests)

**After Fix #1 + Fix #2:**
- All tests should PASS
- No test code changes needed (already fixed in PHASE 4)

**Test Changes Required:** NONE

**Justification:**
- Tests already updated in PHASE 4 to await subscribe_to_events()
- Tests already correct
- Only production code (Container) needs fix

---

## FINAL RECOMMENDATIONS

### Immediate Actions (Required)

1. **Add prometheus-client to requirements.txt**
   - Version: `prometheus-client>=0.19.0,<1.0.0`
   - User must install: `pip install prometheus-client`
   - Effort: 1 minute
   - Risk: NONE

2. **Fix Container.create_prometheus_metrics()**
   - Change _create() to async
   - Add await to subscribe_to_events()
   - Effort: 5 minutes
   - Risk: LOW

### Long-Term Actions (Recommended)

1. **Add CI/CD Dependency Check**
   - Use pip-compile or poetry
   - Automated import validation
   - Prevent future missing dependencies

2. **Add Type Checking**
   - Enable mypy in CI/CD
   - Catch async/await bugs automatically
   - Prevent sync calls to async methods

3. **Standardize Container Factories**
   - Document async factory pattern
   - Convert all factories to async where needed
   - Consistency check

---

## CONCLUSION

**Root Cause:** Incomplete dependency management + async refactoring bug

**Found Issues:**
1. prometheus-client missing from requirements.txt (PRIMARY)
2. Container calls async method sync (SECONDARY - my bug from PHASE 2)

**Both issues are CRITICAL** - application cannot start and work correctly.

**Fixes are straightforward:**
- Add 1 line to requirements.txt
- Change 2 lines in container.py

**Estimated Total Fix Time:** 10 minutes

**Risk Level:** VERY LOW - both fixes are simple and proven patterns

**Test Impact:** NONE - tests already correct (fixed in PHASE 4)

---

**END OF ANALYSIS**
