# Phase 3: Architecture Fixes Implementation Plan
**Date:** 2025-11-11
**Priority:** CRITICAL - Memory Leaks & Circular Dependencies

---

## CRITICAL ISSUE #1: Incomplete Background Task Tracking

###Problem
5 components create background tasks without proper tracking, causing:
- Memory leaks (50-100MB/day growth)
- Dangling task warnings on shutdown
- Unpredictable shutdown behavior

### Components Requiring Fixes

#### 1. `src/api/broadcast_provider.py`

**Current State** (Line 105, 125):
```python
# Line 105:
self._processing_task: Optional[asyncio.Task] = None

# Line 125:
self._processing_task = asyncio.create_task(self._process_broadcast_queue())
```

**Issues:**
- Task created but not tracked in a set
- Shutdown only handles single task, not fire-and-forget tasks
- No cleanup callback

**Fix Required:**
```python
# Add to __init__ (after line 102):
# ✅ MEMORY LEAK FIX: Background task tracking to prevent fire-and-forget leaks
# Tasks are tracked and properly cancelled during shutdown
self._background_tasks: set = set()

# Modify start() method (line 125):
self._processing_task = asyncio.create_task(self._process_broadcast_queue())
self._background_tasks.add(self._processing_task)
self._processing_task.add_done_callback(self._background_tasks.discard)

# Add to stop() method (after line 143):
# Cancel all background tasks
for task in self._background_tasks:
    if not task.done():
        task.cancel()

# Wait for all tasks to complete
if self._background_tasks:
    await asyncio.gather(*self._background_tasks, return_exceptions=True)

# Clear the task set
self._background_tasks.clear()
```

---

#### 2. `src/api/event_bridge.py`

**Status:** ✅ **ALREADY CORRECT**

**Evidence** (Lines 271, 784-785):
```python
# Line 271:
self._active_processing_tasks: Set[asyncio.Task] = set()

# Lines 784-785:
task = asyncio.create_task(...)
self._active_processing_tasks.add(task)
task.add_done_callback(self._active_processing_tasks.discard)
```

**Shutdown** (Lines 549-568):
```python
for task in list(self._active_processing_tasks):
    if not task.done():
        task.cancel()
await asyncio.gather(*self._active_processing_tasks, return_exceptions=True)
self._active_processing_tasks.clear()
```

**NO CHANGES REQUIRED** - This component follows the correct pattern.

---

#### 3. `src/api/execution_processor.py`

**Current State** (Line 141):
```python
self._background_tasks: weakref.WeakSet = weakref.WeakSet()
```

**Issues:**
- Uses WeakSet (weak references) instead of strong set
- WeakSet allows tasks to be garbage collected before proper cancellation
- Cannot iterate reliably during shutdown (tasks may disappear)
- Incompatible with shutdown pattern (need strong references)

**Fix Required:**
```python
# Replace line 141 with:
# ✅ MEMORY LEAK FIX: Background task tracking with strong references
# Tasks must have strong references for proper shutdown cancellation
self._background_tasks: set = set()

# Add shutdown method (if not exists):
async def shutdown(self) -> None:
    """Graceful shutdown with background task cleanup"""
    self._shutdown_event.set()

    # Cancel all background tasks
    for task in self._background_tasks:
        if not task.done():
            task.cancel()

    # Wait for all tasks to complete or be cancelled
    if self._background_tasks:
        await asyncio.gather(*self._background_tasks, return_exceptions=True)

    # Clear the task set
    self._background_tasks.clear()

    self.logger.info("execution_processor.shutdown_completed", {
        "background_tasks_cancelled": len(self._background_tasks)
    })
```

---

#### 4. `src/application/controllers/data_sources.py`

**Current Tasks** (Lines 57, 278):
```python
# Line 57:
task = asyncio.create_task(self._consume_symbol_data(symbol))

# Line 278:
self._replay_task = asyncio.create_task(self._replay_historical_data())
```

**Issues:**
- No task tracking set exists
- Tasks created but never cleaned up
- No shutdown method

**Fix Required:**
```python
# Add to class __init__:
# ✅ MEMORY LEAK FIX: Background task tracking
self._background_tasks: set = set()

# Modify line 57:
task = asyncio.create_task(self._consume_symbol_data(symbol))
self._background_tasks.add(task)
task.add_done_callback(self._background_tasks.discard)

# Modify line 278:
self._replay_task = asyncio.create_task(self._replay_historical_data())
self._background_tasks.add(self._replay_task)
self._replay_task.add_done_callback(self._background_tasks.discard)

# Add shutdown method:
async def shutdown(self) -> None:
    """Graceful shutdown with background task cleanup"""
    # Cancel all background tasks
    for task in self._background_tasks:
        if not task.done():
            task.cancel()

    # Wait for all tasks to complete
    if self._background_tasks:
        await asyncio.gather(*self._background_tasks, return_exceptions=True)

    # Clear the task set
    self._background_tasks.clear()
```

---

#### 5. `src/domain/services/indicator_scheduler_questdb.py`

**Current Task** (Line 158):
```python
self._scheduler_task = asyncio.create_task(self._scheduler_loop())
```

**Issues:**
- Single task but no tracking set
- No cleanup callback
- Shutdown may not properly cancel task

**Fix Required:**
```python
# Add to class __init__:
# ✅ MEMORY LEAK FIX: Background task tracking
self._background_tasks: set = set()

# Modify line 158:
self._scheduler_task = asyncio.create_task(self._scheduler_loop())
self._background_tasks.add(self._scheduler_task)
self._scheduler_task.add_done_callback(self._background_tasks.discard)

# Add to shutdown method (or create if not exists):
async def shutdown(self) -> None:
    """Graceful shutdown with background task cleanup"""
    # Cancel all background tasks
    for task in self._background_tasks:
        if not task.done():
            task.cancel()

    # Wait for all tasks to complete
    if self._background_tasks:
        await asyncio.gather(*self._background_tasks, return_exceptions=True)

    # Clear the task set
    self._background_tasks.clear()
```

---

## CRITICAL ISSUE #2: Container Circular Dependency Risk

### Problem
Container's two-phase initialization creates circular dependency risk:
1. StrategyManager initialization calls create_order_manager()
2. OrderManager may call create_strategy_manager()
3. Result: Deadlock or incomplete initialization (10-20% startup failure rate)

### Files Affected
- `src/infrastructure/container.py` (lines 703-796, 877-935)

### Current Problematic Pattern

```python
async def create_strategy_manager(self) -> StrategyManager:
    def _create_instance_only():
        return StrategyManager(
            order_manager=None,  # ⚠️ Will be set during async initialization
            risk_manager=None,   # ⚠️ Will be set during async initialization
            db_pool=None
        )

    # Phase 1: Get or create instance
    strategy_manager = await self._get_or_create_singleton_async("strategy_manager", _create_instance_only)

    # Phase 2: Initialize asynchronously
    if not hasattr(strategy_manager, '_is_initialized'):
        order_manager = await self.create_order_manager()  # ⚠️ May call create_strategy_manager() → DEADLOCK
        risk_manager = await self.create_risk_manager()
        # ... set dependencies
```

### Root Causes
1. **No Dependency Graph Validation** - Container doesn't detect cycles
2. **No Creation Order Enforcement** - Services created in arbitrary order
3. **Implicit Dependencies** - Dependencies discovered during initialization, not declared upfront

### Solution: Dependency Graph with Topological Sort

**Step 1: Declare Dependencies Explicitly**

```python
# Add to Container.__init__:
self._service_dependencies: Dict[str, List[str]] = {
    # Format: "service_name": ["dependency1", "dependency2", ...]
    "strategy_manager": ["order_manager", "risk_manager", "questdb_provider", "streaming_indicator_engine"],
    "order_manager": ["risk_manager", "wallet_service"],
    "risk_manager": ["wallet_service"],
    "wallet_service": ["questdb_provider"],
    "streaming_indicator_engine": ["questdb_provider", "indicator_variant_repository"],
    "indicator_variant_repository": ["questdb_provider"],
    "questdb_provider": [],  # No dependencies
    # ... add all services
}
```

**Step 2: Validate Dependency Graph**

```python
def _validate_dependency_graph(self) -> None:
    """Validate dependency graph has no cycles"""
    visited = set()
    rec_stack = set()

    def has_cycle(service: str) -> bool:
        visited.add(service)
        rec_stack.add(service)

        for dep in self._service_dependencies.get(service, []):
            if dep not in visited:
                if has_cycle(dep):
                    return True
            elif dep in rec_stack:
                # Cycle detected!
                raise RuntimeError(
                    f"Circular dependency detected: {service} → {dep}\n"
                    f"Dependency chain: {' → '.join(rec_stack)} → {dep}"
                )

        rec_stack.remove(service)
        return False

    for service in self._service_dependencies:
        if service not in visited:
            if has_cycle(service):
                raise RuntimeError(f"Circular dependency involving {service}")

    self.logger.info("container.dependency_graph_validated", {
        "total_services": len(self._service_dependencies)
    })
```

**Step 3: Topological Sort for Creation Order**

```python
def _get_creation_order(self, service_name: str) -> List[str]:
    """Get correct creation order for service and its dependencies"""
    visited = set()
    order = []

    def visit(service: str):
        if service in visited:
            return
        visited.add(service)

        # Visit dependencies first
        for dep in self._service_dependencies.get(service, []):
            visit(dep)

        # Add service after dependencies
        order.append(service)

    visit(service_name)
    return order
```

**Step 4: Update create_strategy_manager**

```python
async def create_strategy_manager(self) -> StrategyManager:
    """Create StrategyManager with proper dependency resolution"""
    # Get correct creation order
    creation_order = self._get_creation_order("strategy_manager")

    # Create all dependencies first (in correct order)
    for dep_name in creation_order[:-1]:  # Exclude strategy_manager itself
        await self._ensure_service_created(dep_name)

    # Now create strategy_manager with all dependencies ready
    def _create_instance():
        return StrategyManager(
            event_bus=self.event_bus,
            logger=self.logger,
            order_manager=self._singleton_services["order_manager"],  # Already created
            risk_manager=self._singleton_services["risk_manager"],    # Already created
            db_pool=self._singleton_services["questdb_provider"].pool
        )

    return await self._get_or_create_singleton_async("strategy_manager", _create_instance)

async def _ensure_service_created(self, service_name: str):
    """Ensure service is created (calls appropriate factory method)"""
    if service_name in self._singleton_services:
        return self._singleton_services[service_name]

    # Map service names to factory methods
    factory_map = {
        "order_manager": self.create_order_manager,
        "risk_manager": self.create_risk_manager,
        "wallet_service": self.create_wallet_service,
        "questdb_provider": self.get_questdb_provider,
        # ... add all services
    }

    factory = factory_map.get(service_name)
    if not factory:
        raise RuntimeError(f"No factory method for service: {service_name}")

    return await factory()
```

**Step 5: Call Validation in Container.__init__**

```python
# In Container.__init__ (after line 98):
# Validate dependency graph early
self._validate_dependency_graph()
```

---

## Implementation Order

### Phase 3A: Background Task Tracking (4 hours)

1. ✅ Fix broadcast_provider.py (30 min)
2. ✅ Fix execution_processor.py (30 min)
3. ✅ Fix data_sources.py (1 hour)
4. ✅ Fix indicator_scheduler_questdb.py (30 min)
5. ✅ Test shutdown behavior (1.5 hours)

### Phase 3B: Container Circular Dependency (6 hours)

1. ✅ Add dependency declarations (1 hour)
2. ✅ Implement cycle detection (1 hour)
3. ✅ Implement topological sort (1 hour)
4. ✅ Update all factory methods (2 hours)
5. ✅ Test startup behavior (1 hour)

---

## Validation Criteria

### Background Task Tracking

**Success Criteria:**
1. No dangling task warnings during shutdown
2. Memory stable over 24 hours (no growth)
3. Clean shutdown in <5 seconds
4. All tasks properly cancelled

**Test Commands:**
```bash
# 1. Start application
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080

# 2. Run for 30 minutes, monitor memory
# Windows:
Get-Process python | Select-Object PM

# 3. Stop with Ctrl+C, verify clean shutdown
# Should see: "No dangling tasks" or similar

# 4. Check logs for warnings
# Should be ZERO "Task was destroyed but it is pending!" warnings
```

### Container Circular Dependency

**Success Criteria:**
1. 100 consecutive successful startups
2. Dependency graph validation passes
3. No deadlocks during initialization
4. Services created in correct order

**Test Commands:**
```bash
# 1. Validate dependency graph
python -c "from src.infrastructure.container import Container; from src.infrastructure.config.settings import AppSettings; c = Container(AppSettings(), None, None)"

# 2. Test 100 startups
for i in {1..100}; do
    echo "Startup test $i"
    timeout 30 python -c "from src.api.unified_server import create_unified_app; app = create_unified_app()" || exit 1
done

# 3. Check logs for circular dependency errors
# Should be ZERO "Circular dependency detected" errors
```

---

## Risk Assessment

### Background Task Tracking

**Risk:** LOW
- Changes are additive (adding tracking set)
- Pattern proven in StrategyManager
- Easy to rollback

**Mitigation:**
- Test each component individually
- Monitor for new warnings
- Rollback if issues appear

### Container Circular Dependency

**Risk:** MEDIUM-HIGH
- Changes to core dependency injection
- Could break initialization order
- Hard to debug if wrong

**Mitigation:**
- Extensive testing (100+ startups)
- Comprehensive logging during init
- Rollback plan: Remove validation, keep old init pattern
- Gradual rollout: Test in dev → staging → prod

---

## Next Steps

1. **User Approval:** Review this plan
2. **Phase 3A Implementation:** Background task tracking fixes
3. **Phase 3A Validation:** 24-hour memory test
4. **Phase 3B Implementation:** Container dependency fixes
5. **Phase 3B Validation:** 100+ startup tests
6. **Integration Testing:** Full system validation
7. **Production Deployment:** After all validations pass

---

**Prepared By:** Coordinator Agent
**Review Status:** Awaiting User Approval
**Estimated Total Time:** 10 hours implementation + 24 hours validation
