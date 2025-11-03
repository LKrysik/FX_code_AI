# MEXC WebSocket Adapter - Refactoring Analysis & Implementation Plan

**Date:** 2025-11-03
**Status:** READY FOR REVIEW
**Priority:** P2 (Medium) - Per refactoring analysis documents
**File:** `src/infrastructure/exchanges/mexc_websocket_adapter.py` (3,014 lines)

---

## 📊 **EXECUTIVE SUMMARY**

The MEXC WebSocket Adapter is a **critically overloaded** component with **3,014 lines** in a single file. Analysis reveals:

- **CRITICAL**: One method contains **358 lines** with 90% code duplication
- **7 distinct responsibilities** violating Single Responsibility Principle
- **Memory leak risks** in unbounded tracking structures
- **Maintainability Index**: Estimated ~20 (very poor)

**Recommendation**: Refactor into 10 focused modules following Clean Architecture and program patterns.

**Estimated Time**: 10 days (as per OVERLOADED_FILES_ANALYSIS.md)

---

## 🔍 **DETAILED ARCHITECTURE ANALYSIS**

### Current State

**File Structure:**
```
mexc_websocket_adapter.py (3,014 lines)
└── class MexcWebSocketAdapter(IMarketDataProvider)
    ├── 47 methods (23 public, 24 private)
    ├── Longest method: 358 lines (_handle_futures_subscription_response)
    └── 7 distinct responsibilities (SRP violation)
```

**Method Size Analysis:**
```
Longest Methods (>100 lines):
  1. _handle_futures_subscription_response: 358 lines ⚠️ CRITICAL
  2. _heartbeat_monitor:                    135 lines
  3. _message_loop:                         117 lines
  4. _process_orderbook_data:               107 lines
  5. _do_subscribe:                          99 lines
  6. _process_orderbook_delta:               97 lines
  7. _reconnect_connection:                  96 lines
```

### Architectural Violations Identified

#### **1. CRITICAL: Code Duplication in `_handle_futures_subscription_response`**

**Problem**: 358-line method with **90% duplicated logic** across 3 subscription handlers.

**Evidence**:
```python
# Lines 985-1078: rs.sub.deal handler (94 lines)
if channel == "rs.sub.deal":
    if response_data == "success":
        # Find symbol, update status, check if all confirmed, remove from pending
        # ... 60 lines of logic ...
    else:
        # Handle failure
        # ... 28 lines of logic ...

# Lines 1079-1171: rs.sub.depth handler (93 lines) - DUPLICATE!
elif channel == "rs.sub.depth":
    if response_data == "success":
        # SAME LOGIC as above, just different channel name
        # ... 60 lines of logic ...
    else:
        # SAME FAILURE HANDLING
        # ... 28 lines of logic ...

# Lines 1172-1316: rs.sub.depth.full handler (145 lines) - DUPLICATE!
elif channel == "rs.sub.depth.full":
    # SAME LOGIC AGAIN + extra snapshot refresh
    # ... 100+ lines of duplicated logic ...
```

**Impact**:
- **Maintainability**: Adding a new subscription type requires ~120 lines of copy-paste code
- **Bug Risk**: Bug fixes must be replicated 3x (high chance of missing one)
- **Testing**: Same logic tested 3x instead of once
- **Code Smell**: Violates DRY (Don't Repeat Yourself) principle

**Quantified Duplication**: ~270 lines of the 358 lines are duplicated (75%+)

#### **2. Single Responsibility Principle Violation**

**Problem**: MexcWebSocketAdapter has 7 distinct responsibilities:

1. **Connection Pool Management** (5 methods, ~200 lines)
   - `_create_new_connection()`, `_get_available_connection()`, `_close_connection()`

2. **Subscription Coordination** (5 methods, ~350 lines)
   - `subscribe_to_symbol()`, `_do_subscribe()`, `_send_subscription()`
   - `unsubscribe_from_symbol()`, `_handle_futures_subscription_response()`

3. **Message Routing** (3 methods, ~220 lines)
   - `_message_loop()`, `_handle_message()`, `_safe_publish_event()`

4. **Message Processing** (8 methods, ~450 lines)
   - `_handle_futures_deal_data()`, `_handle_futures_depth_data()`
   - `_process_deals_data()`, `_process_orderbook_data()`
   - `_process_orderbook_snapshot()`, `_process_orderbook_delta()`

5. **Reconnection Management** (3 methods, ~240 lines)
   - `_handle_connection_error()`, `_reconnect_connection()`
   - `_cleanup_old_reconnection_attempts()`

6. **Health Monitoring** (6 methods, ~300 lines)
   - `health_check()`, `_heartbeat_monitor()`, `get_connection_stats()`
   - `get_detailed_metrics()`, `_calculate_connection_health()`

7. **Orderbook Caching** (5 methods, ~350 lines)
   - `_refresh_orderbook_from_rest()`, `_publish_orderbook_from_cache()`
   - `_start_orderbook_refresh_task()`, `_start_snapshot_refresh_task()`

**Impact**: Changes in one area can accidentally break others, testing is difficult, code is hard to understand.

#### **3. Memory Leak Risks**

**Problem**: Unbounded growth in tracking structures.

**Evidence**:
```python
# Line 124: No max size
self._pending_subscriptions: Dict[int, Dict[str, Dict[str, str]]] = {}

# Line 154: No max size
self._orderbook_cache = {}

# Line 160: Tasks accumulate without cleanup
self._snapshot_refresh_tasks = {}

# Line 150: Debug log rates can grow indefinitely
self._debug_log_rates = {}
```

**Mitigations Exist** (but insufficient):
- `_cleanup_tracking_structures()` runs every 10 minutes (lines 219-268)
- Hard limits on `_reconnection_attempts` (50 items) and `_debug_log_rates` (1000 items)
- **BUT**: No limits on `_pending_subscriptions`, `_orderbook_cache`, or `_snapshot_refresh_tasks`

**Risk**: In production with 100+ symbols, these structures can grow unbounded causing memory exhaustion.

---

## 📊 **IMPACT ANALYSIS - Dependency Trace**

### Consumers of MexcWebSocketAdapter

**Direct Consumers:**
1. `src/data/live_market_adapter.py` (line 90):
   ```python
   self.adapter = MexcWebSocketAdapter(settings, event_bus, logger, data_types=data_types)
   ```

2. `src/infrastructure/factories/market_data_factory.py` (line 96):
   ```python
   provider = MexcWebSocketAdapter(settings, event_bus, logger, data_types=data_types)
   ```

**Interface Contract:**
MexcWebSocketAdapter implements `IMarketDataProvider` (11 required methods):
- `connect()`, `disconnect()`, `subscribe_to_symbol()`, `unsubscribe_from_symbol()`
- `get_market_data_stream()`, `get_latest_price()`, `get_24h_volume()`
- `get_symbol_info()`, `is_symbol_active()`, `get_exchange_name()`, `health_check()`

### Critical Finding: **Public API is STABLE**

**Analysis**:
- Consumers only use the `IMarketDataProvider` interface
- Refactoring will ONLY touch **private methods** (prefixed with `_`)
- **Public methods will delegate to new components** (no signature changes)
- Constructor signature will remain identical: `__init__(settings, event_bus, logger, data_types=None)`

**Evidence of Safety**:
```python
# Before refactoring
async def subscribe_to_symbol(self, symbol: str) -> None:
    async with self._subscription_lock:
        await self._do_subscribe(symbol)

# After refactoring (same signature, different implementation)
async def subscribe_to_symbol(self, symbol: str) -> None:
    await self._subscription_coordinator.subscribe(symbol)
```

**Conclusion**: Refactoring is **LOW RISK** for consumers because:
1. Public API remains unchanged
2. Only internal implementation changes
3. Behavior is preserved (verified by tests)

---

## 🎯 **PROPOSED SOLUTION**

### Architecture Design

Following Clean Architecture and program patterns (Container DI, EventBus, etc.):

```
src/infrastructure/exchanges/mexc/
├── __init__.py                              # Public API (MexcWebSocketAdapter)
├── adapter.py                               # Main orchestrator (300-400 lines)
│
├── connection/
│   ├── __init__.py
│   ├── connection_pool.py                   # Multi-connection management (300 lines)
│   ├── connection_handler.py                # Single connection lifecycle (200 lines)
│   └── reconnection_manager.py              # Reconnection logic (200 lines)
│
├── subscription/
│   ├── __init__.py
│   ├── subscription_coordinator.py          # Subscription orchestration (200 lines)
│   ├── subscription_confirmer.py            # ✅ FIX: 358-line method → (150 lines)
│   └── subscription_tracker.py              # State tracking (150 lines)
│
├── messaging/
│   ├── __init__.py
│   ├── message_router.py                    # Message routing (150 lines)
│   ├── deal_message_processor.py            # Deal data processing (200 lines)
│   ├── depth_message_processor.py           # Orderbook processing (200 lines)
│   └── subscription_message_processor.py    # Alias to subscription_confirmer
│
├── monitoring/
│   ├── __init__.py
│   ├── health_tracker.py                    # Connection health (150 lines)
│   └── metrics_reporter.py                  # Metrics aggregation (100 lines)
│
└── cache/
    ├── __init__.py
    └── orderbook_cache_manager.py           # Orderbook caching + refresh (200 lines)
```

**Total**: ~2,600 lines across 17 files (vs 3,014 in one file)
**Reduction**: ~400 lines removed (duplication + dead code)

### Key Components

#### **1. SubscriptionConfirmer** (Solves 358-line method problem)

**Responsibility**: Process subscription confirmations from MEXC.

**Refactoring Strategy**: Extract common logic into helper methods.

**Before** (358 lines of duplication):
```python
async def _handle_futures_subscription_response(self, data: dict, connection_id: int) -> None:
    channel = data.get("channel", "")
    response_data = data.get("data", "")

    # Handle rs.sub.deal (94 lines)
    if channel == "rs.sub.deal":
        if response_data == "success":
            # ... 60 lines of logic ...
        else:
            # ... 28 lines of logic ...

    # Handle rs.sub.depth (93 lines) - DUPLICATE!
    elif channel == "rs.sub.depth":
        if response_data == "success":
            # ... 60 lines of SAME logic ...
        else:
            # ... 28 lines of SAME logic ...

    # Handle rs.sub.depth.full (145 lines) - DUPLICATE!
    elif channel == "rs.sub.depth.full":
        # ... 100+ lines of SAME logic + extra ...
```

**After** (150 lines, no duplication):
```python
class SubscriptionConfirmer:
    """Handles subscription confirmation messages from MEXC"""

    async def handle_confirmation(
        self,
        channel: str,
        response_data: str,
        connection_id: int
    ) -> None:
        # Parse channel to determine subscription type
        sub_type = self._parse_channel_type(channel)  # "deal", "depth", "depth_full"
        is_success = (response_data == "success")

        if is_success:
            await self._handle_success(sub_type, connection_id)
        else:
            await self._handle_failure(sub_type, connection_id, response_data)

    async def _handle_success(
        self,
        sub_type: str,
        connection_id: int
    ) -> None:
        """Common success handling for ALL subscription types"""
        # Find symbol (30 lines) - SHARED LOGIC
        symbol = await self._find_pending_symbol(sub_type, connection_id)
        if not symbol:
            return

        # Update status (10 lines) - SHARED LOGIC
        await self._update_subscription_status(symbol, connection_id, sub_type, "confirmed")

        # Check if all confirmed (20 lines) - SHARED LOGIC
        if await self._all_subscriptions_confirmed(symbol, connection_id):
            await self._finalize_subscription(symbol, connection_id)

        # Type-specific actions (10 lines) - ONLY DIFFERENT PART
        if sub_type == "depth_full":
            await self._orderbook_cache.start_snapshot_refresh(symbol)

    async def _handle_failure(
        self,
        sub_type: str,
        connection_id: int,
        error: str
    ) -> None:
        """Common failure handling for ALL subscription types"""
        # Shared failure logic (40 lines)
        symbol = await self._find_pending_symbol(sub_type, connection_id)
        await self._update_subscription_status(symbol, connection_id, sub_type, "failed")
        await self._log_failure(sub_type, symbol, connection_id, error)

    def _parse_channel_type(self, channel: str) -> str:
        """Parse channel name to subscription type"""
        # "rs.sub.deal" → "deal"
        # "rs.sub.depth" → "depth"
        # "rs.sub.depth.full" → "depth_full"
        return channel.replace("rs.sub.", "").replace(".", "_")
```

**Benefits**:
- **75% code reduction**: 358 lines → 150 lines
- **Zero duplication**: Common logic extracted once
- **Easier testing**: Test `_handle_success()` once, not 3x
- **Easier maintenance**: Add new subscription type with ~10 lines, not ~120 lines
- **Bug fixes propagate**: Fix once, fixed for all subscription types

#### **2. ConnectionPool** (Multi-connection management)

**Responsibility**: Manage multiple WebSocket connections.

**Extracted Methods**:
- `_create_new_connection()` (429-430 lines)
- `_get_available_connection()` (431-478 lines)
- `_close_connection()` (2167-2254 lines)

**Interface**:
```python
class ConnectionPool:
    def __init__(self, config: dict, event_bus: EventBus, logger: StructuredLogger):
        self._connections: Dict[int, ConnectionHandler] = {}
        self._max_connections = config.get("max_connections", 5)
        self._max_subscriptions_per_connection = config.get("max_subscriptions_per_connection", 30)

    async def create_connection(self) -> int:
        """Create new connection, return connection_id"""

    async def get_available_connection(self) -> Optional[int]:
        """Find connection with capacity for more subscriptions"""

    async def close_connection(self, connection_id: int) -> None:
        """Close and cleanup connection"""

    def get_connection_handler(self, connection_id: int) -> Optional[ConnectionHandler]:
        """Get handler for specific connection"""

    def get_all_connections(self) -> Dict[int, ConnectionHandler]:
        """Get all active connections"""
```

#### **3. ReconnectionManager** (Reconnection logic)

**Responsibility**: Handle connection failures and reconnection attempts.

**Extracted Methods**:
- `_handle_connection_error()` (625-668 lines)
- `_reconnect_connection()` (2255-2350 lines)
- `_cleanup_old_reconnection_attempts()` (2351-2386 lines)

**Interface**:
```python
class ReconnectionManager:
    async def handle_connection_error(
        self,
        connection_id: int,
        error: Exception
    ) -> None:
        """Central error handling with reconnection strategy"""

    async def attempt_reconnect(
        self,
        connection_id: int,
        failed_symbols: Set[str]
    ) -> bool:
        """Attempt to reconnect with exponential backoff"""

    def calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate delay for nth reconnection attempt"""
```

#### **4. MessageRouter** (Message routing)

**Responsibility**: Route incoming messages to appropriate processors.

**Extracted Methods**:
- `_message_loop()` (508-624 lines)
- `_handle_message()` (891-978 lines)

**Interface**:
```python
class MessageRouter:
    def __init__(
        self,
        deal_processor: DealMessageProcessor,
        depth_processor: DepthMessageProcessor,
        subscription_confirmer: SubscriptionConfirmer,
        logger: StructuredLogger
    ):
        # Dependency injection of processors
        pass

    async def process_message(self, message: str, connection_id: int) -> None:
        """Parse and route message to appropriate processor"""

    async def start_message_loop(self, connection_id: int, websocket) -> None:
        """Main message reception loop"""
```

#### **5. DealMessageProcessor & DepthMessageProcessor**

**Responsibility**: Process deal/depth market data messages.

**Extracted Methods**:
- `_handle_futures_deal_data()` (1337-1421 lines)
- `_handle_futures_depth_data()` (1422-1471 lines)
- `_process_deals_data()` (1519-1557 lines)
- `_process_orderbook_data()` (1595-1701 lines)
- `_process_orderbook_snapshot()` (1702-1753 lines)
- `_process_orderbook_delta()` (1754-1850 lines)

#### **6. HealthTracker & MetricsReporter**

**Responsibility**: Monitor connection health and export metrics.

**Extracted Methods**:
- `health_check()` (2502-2503 lines, 3000-3014 lines)
- `_heartbeat_monitor()` (669-803 lines)
- `get_connection_stats()` (2514-2534 lines)
- `get_detailed_metrics()` (2535-2578 lines)
- `_calculate_connection_health()` (2579-2605 lines)

#### **7. OrderbookCacheManager**

**Responsibility**: Manage orderbook cache and periodic refreshes.

**Extracted Methods**:
- `_refresh_orderbook_from_rest()` (2738-2824 lines)
- `_publish_orderbook_from_cache()` (1851-1892 lines)
- `_start_orderbook_refresh_task()` (2825-2859 lines)
- `_start_snapshot_refresh_task()` (2866-2918 lines)
- `_stop_snapshot_refresh_task()` (2919-2933 lines)

---

## 🛡️ **RISK MITIGATION STRATEGY**

### Risk #1: Breaking Public API Contract

**Likelihood**: LOW
**Impact**: CRITICAL (all consumers break)

**Mitigation**:
1. **API Compatibility Tests**: Create tests that verify all IMarketDataProvider methods work identically.
   ```python
   async def test_public_api_compatibility():
       """Ensure refactored adapter has same public interface"""
       adapter = MexcWebSocketAdapter(settings, event_bus, logger)

       # Verify all interface methods exist
       assert hasattr(adapter, 'connect')
       assert hasattr(adapter, 'disconnect')
       assert hasattr(adapter, 'subscribe_to_symbol')
       # ... all 11 methods

       # Verify signatures unchanged
       import inspect
       sig = inspect.signature(adapter.subscribe_to_symbol)
       assert list(sig.parameters.keys()) == ['symbol']
   ```

2. **Behavioral Tests**: Test that behavior is identical to baseline.
   ```python
   async def test_subscription_behavior_unchanged():
       """Ensure subscription flow works identically"""
       # Old implementation baseline
       baseline_events = await run_with_old_adapter(symbols)

       # New implementation
       refactored_events = await run_with_new_adapter(symbols)

       # Compare
       assert baseline_events == refactored_events
   ```

3. **Backward Compatibility Layer**: Main adapter delegates to components.
   ```python
   class MexcWebSocketAdapter(IMarketDataProvider):
       def __init__(self, settings, event_bus, logger, data_types=None):
           # Preserve exact signature
           self.settings = settings
           self.event_bus = event_bus
           self.logger = logger

           # Inject new components
           self._connection_pool = ConnectionPool(...)
           self._subscription_coordinator = SubscriptionCoordinator(...)
           # ...

       async def subscribe_to_symbol(self, symbol: str) -> None:
           # Delegate to component (behavior preserved)
           await self._subscription_coordinator.subscribe(symbol)
   ```

**Verification**:
- Run all existing integration tests
- No consumer code changes required
- Constructor signature identical
- All 11 interface methods work identically

### Risk #2: Message Processing Behavior Changes

**Likelihood**: MEDIUM
**Impact**: HIGH (incorrect market data)

**Mitigation**:
1. **Golden Master Testing**: Capture 1000+ messages from production, replay through both versions.
   ```python
   def test_message_processing_golden_master():
       messages = load_production_messages("mexc_messages_1000.json")

       for msg in messages:
           old_result = old_adapter.process_message(msg)
           new_result = new_adapter.process_message(msg)
           assert old_result == new_result, f"Mismatch on message {msg['id']}"
   ```

2. **Event Stream Comparison**: Ensure EventBus receives identical events.
   ```python
   async def test_eventbus_events_identical():
       old_events = []
       new_events = []

       event_bus.subscribe("market_data", lambda e: old_events.append(e))
       await old_adapter.subscribe_to_symbol("BTC_USDT")

       event_bus.subscribe("market_data", lambda e: new_events.append(e))
       await new_adapter.subscribe_to_symbol("BTC_USDT")

       # Wait for events
       await asyncio.sleep(5)

       assert len(old_events) == len(new_events)
       for old, new in zip(old_events, new_events):
           assert old == new
   ```

3. **Live Comparison Mode** (if feasible): Run both versions in parallel during staging.

**Verification**:
- All golden master tests pass (100%)
- EventBus receives identical events
- No data loss or corruption

### Risk #3: Memory Leaks in New Architecture

**Likelihood**: MEDIUM
**Impact**: HIGH (production crash)

**Mitigation**:
1. **Memory Profiling**: Compare memory usage before/after.
   ```python
   async def test_memory_leak_prevention():
       import tracemalloc
       tracemalloc.start()

       # Simulate 24h operation
       for hour in range(24):
           await simulate_hour_of_trading(adapter)
           snapshot = tracemalloc.take_snapshot()
           memory_mb = sum(stat.size for stat in snapshot.statistics('lineno')) / (1024 * 1024)
           assert memory_mb < 500, f"Memory leak detected: {memory_mb}MB at hour {hour}"
   ```

2. **Explicit Cleanup**: All components implement cleanup methods.
   ```python
   class SubscriptionCoordinator:
       async def cleanup(self) -> None:
           """Explicit cleanup to prevent leaks"""
           self._pending_subscriptions.clear()
           self._subscription_tasks.clear()
   ```

3. **Max Size Limits**: Add hard limits to ALL tracking structures.
   ```python
   class SubscriptionTracker:
       MAX_PENDING_SUBSCRIPTIONS = 1000

       def add_pending(self, symbol: str, connection_id: int) -> None:
           if len(self._pending) >= self.MAX_PENDING_SUBSCRIPTIONS:
               # Remove oldest entries
               self._evict_oldest_pending()
           self._pending[symbol] = connection_id
   ```

**Verification**:
- 24h memory profiling test passes
- All tracking structures have max sizes
- Cleanup methods called during shutdown

### Risk #4: Reconnection Logic Breaks

**Likelihood**: MEDIUM
**Impact**: HIGH (lost connections in production)

**Mitigation**:
1. **Reconnection Flow Tests**: Simulate connection failures.
   ```python
   async def test_reconnection_flow():
       adapter = MexcWebSocketAdapter(...)
       await adapter.connect()
       await adapter.subscribe_to_symbol("BTC_USDT")

       # Force disconnect
       await force_disconnect(adapter._connection_pool)

       # Verify reconnection
       await asyncio.sleep(10)  # Wait for reconnect
       assert adapter.health_check() == True
       assert "BTC_USDT" in adapter.get_subscribed_symbols()
   ```

2. **Subscription Restoration**: Ensure subscriptions are restored after reconnect.

3. **Backoff Logic Verification**: Test exponential backoff calculations.

**Verification**:
- Reconnection tests pass
- Subscriptions restored correctly
- No data loss during reconnect

### Risk #5: Performance Degradation

**Likelihood**: LOW
**Impact**: MEDIUM (slower message processing)

**Mitigation**:
1. **Benchmark Tests**: Compare message processing speed.
   ```python
   async def test_message_processing_performance():
       messages = generate_test_messages(10000)

       # Baseline
       start = time.time()
       for msg in messages:
           await old_adapter.process_message(msg)
       old_time = time.time() - start

       # Refactored
       start = time.time()
       for msg in messages:
           await new_adapter.process_message(msg)
       new_time = time.time() - start

       # Allow 5% degradation
       assert new_time <= old_time * 1.05, f"Performance degraded: {new_time}s vs {old_time}s"
   ```

2. **Profiling**: Identify hot paths and optimize.

**Verification**:
- Performance degradation < 5%
- No added latency in critical paths

---

## 📋 **IMPLEMENTATION CHECKLIST**

### Phase 1: Preparation (2 hours)

- [ ] Create feature branch: `refactor/mexc-websocket-adapter-{session_id}`
- [ ] Setup baseline tests
  - [ ] Capture 1000+ production messages for golden master
  - [ ] Baseline memory profiling (24h run)
  - [ ] Baseline performance benchmarks
- [ ] Create directory structure
  - [ ] `src/infrastructure/exchanges/mexc/`
  - [ ] All subdirectories (connection/, subscription/, messaging/, monitoring/, cache/)
- [ ] Document current behavior
  - [ ] API contracts
  - [ ] Message flows
  - [ ] State transitions

**Checkpoint #1**: All baseline tests running, directory structure ready

### Phase 2: Extract SubscriptionConfirmer (3 hours)

**Priority: HIGHEST** (solves 358-line method problem)

- [ ] Create `subscription/subscription_confirmer.py`
- [ ] Extract common logic
  - [ ] `_find_pending_symbol()` helper
  - [ ] `_update_subscription_status()` helper
  - [ ] `_all_subscriptions_confirmed()` helper
  - [ ] `_finalize_subscription()` helper
- [ ] Implement `handle_confirmation()` main method
- [ ] Unit tests
  - [ ] Test all subscription types (deal, depth, depth_full)
  - [ ] Test success/failure paths
  - [ ] Test edge cases (orphaned confirmations, late arrivals)
  - [ ] Coverage > 90%
- [ ] Integration with main adapter
  - [ ] Replace 358-line method with delegation
  - [ ] Verify behavior identical
- [ ] Golden master tests pass

**Checkpoint #2**: SubscriptionConfirmer working, tests green, 358-line method eliminated

### Phase 3: Extract Connection Management (3 hours)

- [ ] Create `connection/connection_pool.py`
- [ ] Create `connection/connection_handler.py`
- [ ] Create `connection/reconnection_manager.py`
- [ ] Extract methods
  - [ ] `_create_new_connection()` → ConnectionPool
  - [ ] `_get_available_connection()` → ConnectionPool
  - [ ] `_close_connection()` → ConnectionPool
  - [ ] `_handle_connection_error()` → ReconnectionManager
  - [ ] `_reconnect_connection()` → ReconnectionManager
- [ ] Unit tests (>85% coverage)
- [ ] Integration tests
  - [ ] Multi-connection creation
  - [ ] Reconnection flow
  - [ ] Subscription restoration
- [ ] Reconnection tests pass

**Checkpoint #3**: Connection management working, all tests green

### Phase 4: Extract Message Processing (3 hours)

- [ ] Create `messaging/message_router.py`
- [ ] Create `messaging/deal_message_processor.py`
- [ ] Create `messaging/depth_message_processor.py`
- [ ] Extract methods
  - [ ] `_message_loop()` → MessageRouter
  - [ ] `_handle_message()` → MessageRouter
  - [ ] `_handle_futures_deal_data()` → DealMessageProcessor
  - [ ] `_handle_futures_depth_data()` → DepthMessageProcessor
  - [ ] All orderbook processing methods → DepthMessageProcessor
- [ ] Unit tests (>90% coverage)
- [ ] Golden master tests for message processing
- [ ] Event stream comparison tests pass

**Checkpoint #4**: Message processing working, all tests green

### Phase 5: Extract Monitoring & Caching (2 hours)

- [ ] Create `monitoring/health_tracker.py`
- [ ] Create `monitoring/metrics_reporter.py`
- [ ] Create `cache/orderbook_cache_manager.py`
- [ ] Extract methods
  - [ ] All health check methods → HealthTracker
  - [ ] All metrics methods → MetricsReporter
  - [ ] All orderbook cache methods → OrderbookCacheManager
- [ ] Unit tests (>85% coverage)
- [ ] Integration tests

**Checkpoint #5**: Monitoring and caching working, all tests green

### Phase 6: Main Adapter Orchestration (2 hours)

- [ ] Update `mexc/adapter.py` to orchestrate components
- [ ] Implement dependency injection in `__init__`
- [ ] All public methods delegate to components
- [ ] Remove old code from original file
- [ ] Update imports throughout codebase
- [ ] API compatibility tests pass
- [ ] All integration tests pass

**Checkpoint #6**: Main adapter working, all tests green

### Phase 7: Final Verification (2 hours)

- [ ] All unit tests pass (>90% coverage)
- [ ] All integration tests pass
- [ ] Golden master tests pass (100%)
- [ ] Memory profiling test passes (24h run)
- [ ] Performance benchmarks (< 5% degradation)
- [ ] Reconnection tests pass
- [ ] Load test (100+ symbols, 1000+ messages/sec)
- [ ] API compatibility tests pass
- [ ] Consumer integration tests pass (LiveMarketAdapter, factory)

**Checkpoint #7**: All tests green, ready for merge

### Phase 8: Documentation & Cleanup (1 hour)

- [ ] Update documentation
  - [ ] Architecture diagrams (before/after)
  - [ ] Component interaction diagrams
  - [ ] Update CLAUDE.md
  - [ ] Migration notes for developers
- [ ] Remove dead code
- [ ] Remove old mexc_websocket_adapter.py
- [ ] Update all imports
- [ ] Code review by peer
- [ ] Merge to main branch

---

## ✅ **SUCCESS CRITERIA (KPIs)**

### Code Quality Metrics

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| **File Count** | 1 file | 17 files | Count files in mexc/ |
| **Largest File** | 3,014 lines | <400 lines | `wc -l adapter.py` |
| **Longest Method** | 358 lines | <100 lines | Manual inspection |
| **Code Duplication** | ~270 lines | 0 lines | Visual inspection |
| **Maintainability Index** | ~20 | >60 | Radon or similar |
| **Test Coverage** | ~70% | >90% | pytest --cov |

### Functional Metrics

| Metric | Baseline | Acceptable | Measurement |
|--------|----------|------------|-------------|
| **API Compatibility** | 11/11 methods | 11/11 methods | Interface tests |
| **Golden Master Tests** | N/A | 100% pass | Test suite |
| **Event Stream Identical** | Baseline | 100% match | Event comparison |
| **Message Processing Speed** | X ms | <X*1.05 ms | Benchmark |
| **Memory Usage (24h)** | Y MB | <Y*1.1 MB | Profiler |
| **Memory Growth Rate** | Z MB/h | <10 MB/h | 24h profiling |
| **Reconnection Success** | Baseline | 100% | Reconnection tests |

### Business Metrics

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| **Development Velocity** | Baseline | +30% | Time to add feature |
| **Bug Fix Time** | X hours | X/2 hours | Incident tracking |
| **Onboarding Time** | Y days | Y/2 days | HR tracking |
| **Code Review Time** | Z hours | Z/2 hours | PR metrics |

---

## 🚨 **ROLLBACK PROCEDURE**

If critical issues are encountered:

### Trigger Conditions (Execute Rollback If):
- ❌ More than 2 checkpoints fail
- ❌ Golden master tests <95% pass rate
- ❌ Performance degradation >10%
- ❌ Memory leaks detected
- ❌ Reconnection failure rate >5%
- ❌ Consumer integration breaks

### Rollback Steps:
1. **STOP** - Do not continue refactoring
2. **Assess Severity**:
   - P0 (Production broken): Immediate rollback
   - P1 (Major feature broken): Fix forward if < 4 hours, else rollback
   - P2 (Minor issues): Fix forward
3. **Execute Rollback**:
   ```bash
   git checkout main
   git branch -D refactor/mexc-websocket-adapter-{session_id}
   # Revert any merged changes if already in main
   git revert <commit-hash>
   ```
4. **Document Root Cause**: Add to lessons learned
5. **Re-plan**: Address issues before re-attempting

---

## 📊 **ARCHITECTURAL DIAGRAMS**

### Before Refactoring

```
┌─────────────────────────────────────────────────────────────┐
│             MexcWebSocketAdapter (3,014 lines)              │
│  ─────────────────────────────────────────────────────────  │
│  Single giant class with 7 responsibilities:                │
│                                                              │
│  1. Connection Pool (5 methods)                             │
│  2. Subscription Coordination (5 methods)                   │
│  3. Message Routing (3 methods)                             │
│  4. Message Processing (8 methods)                          │
│  5. Reconnection (3 methods)                                │
│  6. Health Monitoring (6 methods)                           │
│  7. Orderbook Caching (5 methods)                           │
│                                                              │
│  Problems:                                                   │
│  ⚠️ 358-line method with 90% duplication                     │
│  ⚠️ 7 responsibilities (SRP violation)                       │
│  ⚠️ Memory leak risks                                        │
│  ⚠️ Hard to test, maintain, extend                           │
└─────────────────────────────────────────────────────────────┘
```

### After Refactoring

```
┌──────────────────────────────────────────────────────────────┐
│         MexcWebSocketAdapter (300-400 lines)                 │
│  ──────────────────────────────────────────────────────────  │
│  Orchestrator that delegates to focused components:          │
│                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │  ConnectionPool     │  │ ReconnectionManager │           │
│  │  (300 lines)        │  │ (200 lines)         │           │
│  └─────────────────────┘  └─────────────────────┘           │
│                                                               │
│  ┌──────────────────────┐ ┌──────────────────────┐          │
│  │ SubscriptionCoord.   │ │ SubscriptionConfirmer│          │
│  │ (200 lines)          │ │ (150 lines)          │          │
│  └──────────────────────┘ └──────────────────────┘          │
│                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │ MessageRouter       │  │ DealMessageProcessor│           │
│  │ (150 lines)         │  │ (200 lines)         │           │
│  └─────────────────────┘  └─────────────────────┘           │
│                                                               │
│  ┌──────────────────────┐ ┌──────────────────────┐          │
│  │ DepthMessageProc.    │ │ HealthTracker        │          │
│  │ (200 lines)          │ │ (150 lines)          │          │
│  └──────────────────────┘ └──────────────────────┘          │
│                                                               │
│  ┌──────────────────────┐ ┌──────────────────────┐          │
│  │ MetricsReporter      │ │ OrderbookCacheMgr    │          │
│  │ (100 lines)          │ │ (200 lines)          │          │
│  └──────────────────────┘ └──────────────────────┘          │
│                                                               │
│  Benefits:                                                    │
│  ✅ Single Responsibility: Each component has ONE job         │
│  ✅ No duplication: 358-line method → 150 lines               │
│  ✅ Testable: Each component unit tested                      │
│  ✅ Maintainable: Changes localized to specific components    │
│  ✅ Extensible: Add features by adding/extending components   │
└──────────────────────────────────────────────────────────────┘
```

### Component Interaction

```
┌─────────────────┐
│ LiveMarketAdapter│ (Consumer)
└────────┬─────────┘
         │ uses IMarketDataProvider interface
         ▼
┌─────────────────────────────────────────────────────────┐
│        MexcWebSocketAdapter (Orchestrator)              │
│                                                          │
│  __init__(settings, event_bus, logger, data_types):     │
│    self._connection_pool = ConnectionPool(...)          │
│    self._subscription_coordinator = SubCoordinator(...) │
│    self._message_router = MessageRouter(...)            │
│    self._reconnection_manager = ReconnectionManager(...)│
│    self._health_tracker = HealthTracker(...)            │
│    # Dependency Injection - NO service locator          │
│                                                          │
│  async def subscribe_to_symbol(symbol):                 │
│    # Delegate to component                              │
│    await self._subscription_coordinator.subscribe(...)  │
└──────────┬──────────────────────────────────────────────┘
           │
           ├──► ConnectionPool
           │      ├─► Creates/manages WebSocket connections
           │      ├─► Assigns symbols to connections
           │      └─► Enforces subscription limits
           │
           ├──► SubscriptionCoordinator
           │      ├─► Orchestrates subscription flow
           │      ├─► Uses SubscriptionConfirmer
           │      └─► Tracks subscription state
           │
           ├──► MessageRouter
           │      ├─► Receives WebSocket messages
           │      ├─► Routes to DealMessageProcessor
           │      ├─► Routes to DepthMessageProcessor
           │      └─► Routes to SubscriptionConfirmer
           │
           ├──► ReconnectionManager
           │      ├─► Handles connection errors
           │      ├─► Implements backoff strategy
           │      └─► Restores subscriptions
           │
           ├──► HealthTracker
           │      ├─► Monitors connection health
           │      ├─► Tracks heartbeats
           │      └─► Reports metrics
           │
           └──► OrderbookCacheManager
                  ├─► Maintains orderbook state
                  ├─► Processes snapshots/deltas
                  └─► Periodic REST refresh
```

---

## 📝 **JUSTIFICATION FOR EACH CHANGE**

### Change #1: Extract SubscriptionConfirmer from 358-line method

**Justification**:
- **Problem**: 90% code duplication across 3 subscription handlers
- **Evidence**: Lines 985-1078, 1079-1171, 1172-1316 have nearly identical logic
- **Impact**: Adding new subscription type requires ~120 lines of copy-paste
- **Solution**: Extract common logic into helper methods, eliminate duplication
- **Benefits**: 75% code reduction, zero duplication, easier testing/maintenance
- **Risk**: LOW - Pure refactoring, no behavior change
- **Proof of Safety**: Golden master tests ensure identical behavior

### Change #2: Extract ConnectionPool

**Justification**:
- **Problem**: Connection management mixed with 6 other responsibilities
- **Evidence**: 5 methods (~200 lines) handle connection lifecycle
- **Impact**: Connection logic scattered across adapter, hard to test in isolation
- **Solution**: Dedicated ConnectionPool class with clear interface
- **Benefits**: Isolated testing, easier to add connection pooling strategies
- **Risk**: LOW - Clear interface, well-defined responsibility
- **Proof of Safety**: Integration tests verify connection behavior unchanged

### Change #3: Extract ReconnectionManager

**Justification**:
- **Problem**: Reconnection logic intertwined with error handling
- **Evidence**: 3 methods (~240 lines) handle reconnection
- **Impact**: Hard to test reconnection scenarios, backoff logic not reusable
- **Solution**: Dedicated ReconnectionManager with strategy pattern
- **Benefits**: Testable reconnection logic, configurable backoff strategies
- **Risk**: MEDIUM - Complex logic, critical for production stability
- **Proof of Safety**: Reconnection flow tests, subscription restoration tests

### Change #4: Extract Message Processors

**Justification**:
- **Problem**: Message processing logic (8 methods, ~450 lines) mixed with routing
- **Evidence**: Deal/depth processing are independent but in same class
- **Impact**: Cannot test processors in isolation, cannot reuse for other exchanges
- **Solution**: Separate DealMessageProcessor and DepthMessageProcessor
- **Benefits**: Isolated testing, reusable for other exchanges (e.g., Binance)
- **Risk**: LOW - Clear separation, well-defined inputs/outputs
- **Proof of Safety**: Golden master tests ensure identical event publishing

### Change #5: Extract Health & Monitoring

**Justification**:
- **Problem**: Health monitoring (6 methods, ~300 lines) mixed with core logic
- **Evidence**: Health checks, metrics, heartbeats in main adapter
- **Impact**: Cannot monitor in isolation, hard to add new metrics
- **Solution**: Dedicated HealthTracker and MetricsReporter
- **Benefits**: Isolated monitoring, easier to add Prometheus integration
- **Risk**: LOW - Independent concern, minimal coupling
- **Proof of Safety**: Health check tests verify monitoring unchanged

### Change #6: Extract OrderbookCacheManager

**Justification**:
- **Problem**: Orderbook caching (5 methods, ~350 lines) mixed with processing
- **Evidence**: Cache management, refresh tasks, REST fallback in main adapter
- **Impact**: Cache logic hard to test, potential memory leaks
- **Solution**: Dedicated OrderbookCacheManager with size limits
- **Benefits**: Testable cache, configurable refresh strategy, memory leak prevention
- **Risk**: MEDIUM - Critical for orderbook accuracy
- **Proof of Safety**: Orderbook comparison tests, memory profiling

---

## 🎯 **NEXT STEPS**

### Immediate Actions (Today)

1. **Review this document** with stakeholders
2. **GO/NO-GO decision**: Proceed with refactoring?
3. **Assign ownership**: Who will lead the refactoring?
4. **Schedule**: When to start? (Coordinate with other sprints)

### If GO (Week 1)

**Day 1-2: Preparation**
- Create feature branch
- Setup baseline tests
- Create directory structure
- Capture production messages for golden master

**Day 3-5: Phase 2 (SubscriptionConfirmer)**
- Extract 358-line method
- Unit tests
- Golden master tests
- **Checkpoint #2** by end of Day 5

### If NO-GO

1. **Document reasons** for deferring
2. **Plan interim measures**:
   - Add comments to clarify 358-line method
   - Add max size limits to tracking structures
   - Improve test coverage for critical paths
3. **Revisit timeline**: When will refactoring be feasible?

---

## 📚 **REFERENCES**

- **Refactoring Analysis**: `docs/refactoring/OVERLOADED_FILES_ANALYSIS.md` (lines 757-1055)
- **Refactoring Checklist**: `docs/refactoring/REFACTORING_CHECKLIST.md` (lines 421-444)
- **Architecture Principles**: `docs/architecture/CONTAINER.md`
- **Coding Standards**: `docs/development/CODING_STANDARDS.md`
- **Interface Contract**: `src/domain/interfaces/market_data.py`
- **Consumer Code**: `src/data/live_market_adapter.py`

---

**Prepared By**: Claude AI Assistant
**Date**: 2025-11-03
**Status**: READY FOR STAKEHOLDER REVIEW
**Decision Required**: GO/NO-GO for refactoring

---

## ❓ **Q&A - Anticipated Questions**

### Q1: "Why refactor now? Can't this wait?"

**A**: The 358-line method with 90% duplication is a ticking time bomb. Every bug fix or new feature requires changing 3 places. Recently we added `depth_full` subscriptions - it required copy-pasting ~100 lines. Next subscription type will be the same. Technical debt compounds - better to fix now than in 6 months when it's 500+ lines.

### Q2: "Will this break production?"

**A**: Risk is LOW because:
1. We only change PRIVATE methods (not public API)
2. Consumers use IMarketDataProvider interface (unchanged)
3. Golden master tests ensure identical behavior
4. 7 checkpoints - rollback at any sign of issues

### Q3: "How long will this take?"

**A**: 10 days (as estimated in OVERLOADED_FILES_ANALYSIS.md). Can be done in parallel with other work since it's in a feature branch.

### Q4: "What if we find bugs during refactoring?"

**A**: That's a GOOD thing! Clean architecture makes bugs more visible. We'll document and fix them. Better to find bugs now than in production.

### Q5: "Can we just split the 358-line method without the full refactoring?"

**A**: That's Phase 2 (SubscriptionConfirmer). We can do Phase 2 first, see benefits, then decide on Phases 3-8. Incremental approach is valid.

### Q6: "How will we test this in production?"

**A**: Phased rollout:
1. Staging environment first (1 week)
2. Canary deployment (10% traffic)
3. Gradual rollout to 100%
4. Rollback plan ready at each stage

---

**END OF DOCUMENT**
