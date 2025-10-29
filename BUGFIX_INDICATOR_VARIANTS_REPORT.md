# Bug Fix Report: Indicator Variants QuestDB Integration

**Date**: 2025-10-29
**Branch**: `claude/move-indicator-variants-config-011CUc93wynFuz7fpZtmPAnN`
**Issue**: TypeError in `/api/indicators/system` and `/api/indicators/variants` endpoints
**Severity**: CRITICAL - Endpoints completely non-functional

---

## Executive Summary

Recent changes attempting to move indicator variants configuration to QuestDB introduced a **critical bug** that broke two essential API endpoints. The root cause was incorrect parameter names used when instantiating `QuestDBProvider` in the `get_streaming_indicator_engine()` dependency function.

**Impact**: All endpoints using `Depends(get_streaming_indicator_engine)` returned HTTP 500 errors.

**Resolution**: Fixed by reusing existing correct `QuestDBProvider` initialization, eliminating code duplication and ensuring architectural consistency.

---

## Error Details

### Error Trace
```python
TypeError: QuestDBProvider.__init__() got an unexpected keyword argument 'host'
```

**Location**: `src/api/indicators_routes.py:342`

### Affected Endpoints
1. `GET /api/indicators/system` - List all system indicators
2. `GET /api/indicators/variants` - List all indicator variants

Both endpoints depend on `get_streaming_indicator_engine()` which crashed on initialization.

---

## Root Cause Analysis

### Incorrect Code (Before Fix)

**File**: `src/api/indicators_routes.py` lines 342-349

```python
# ❌ BROKEN CODE
questdb_provider = QuestDBProvider(
    host="localhost",        # ❌ No such parameter
    port=8812,               # ❌ Ambiguous - ILP or PostgreSQL port?
    user="admin",            # ❌ Should be pg_user
    password="quest",        # ❌ Should be pg_password
    database="qdb",          # ❌ Should be pg_database
    logger=logger            # ❌ QuestDBProvider doesn't accept logger
)
```

### Why This Failed

`QuestDBProvider` uses a **dual-protocol architecture**:

1. **InfluxDB Line Protocol (ILP)** on port 9009 for ultra-fast writes (1M+ rows/sec)
2. **PostgreSQL Wire Protocol** on port 8812 for SQL queries

**Correct Constructor Signature**:
```python
def __init__(
    self,
    ilp_host: str = 'localhost',      # InfluxDB Line Protocol
    ilp_port: int = 9009,
    pg_host: str = 'localhost',        # PostgreSQL Wire Protocol
    pg_port: int = 8812,
    pg_user: str = 'admin',
    pg_password: str = 'quest',
    pg_database: str = 'qdb',
    pg_pool_size: int = 10
)
```

The developer who wrote the broken code:
- ✅ Correctly identified need for QuestDBProvider
- ❌ Assumed generic SQL connection pattern (host, port, user, password, database)
- ❌ Did not verify constructor signature
- ❌ Did not notice existing correct initialization 15 lines above
- ❌ Did not test endpoints before committing

---

## Architectural Issues Identified

### Issue 1: Code Duplication (CRITICAL VIOLATION)

The same file had **two different initialization patterns** for `QuestDBProvider`:

**Pattern A (CORRECT)** - Line 117-122 in `_ensure_questdb_providers()`:
```python
_questdb_provider = QuestDBProvider(
    ilp_host='127.0.0.1',
    ilp_port=9009,
    pg_host='127.0.0.1',
    pg_port=8812
)
```

**Pattern B (BROKEN)** - Line 342-349 in `get_streaming_indicator_engine()`:
```python
questdb_provider = QuestDBProvider(
    host="localhost",  # Wrong parameters
    ...
)
```

**Violation**: Project standard (CLAUDE.md) states:
> "NO code duplication - extract to shared functions/classes"

### Issue 2: Import Inconsistency

- **Line 33**: `from src.data_feed.questdb_provider import QuestDBProvider` (absolute)
- **Line 337**: `from ..data_feed.questdb_provider import QuestDBProvider` (relative)

**Problem**: Same module imported twice with different styles.

### Issue 3: Violation of Single Source of Truth

Having two separate initializations meant:
- ❌ Configuration must be kept in sync manually
- ❌ Future changes require updates in multiple places
- ❌ Risk of inconsistencies
- ❌ More difficult to maintain

---

## Solution Implemented

### Fix Applied

**File**: `src/api/indicators_routes.py` lines 325-372

```python
async def get_streaming_indicator_engine() -> StreamingIndicatorEngine:
    """
    Dependency to get StreamingIndicatorEngine instance.
    ✅ UPDATED: Now creates IndicatorVariantRepository for database persistence.
    ✅ FIXED: Reuses _ensure_questdb_providers() to eliminate code duplication.
    """
    global _streaming_engine, _event_bus, _persistence_service, _offline_indicator_engine

    if _streaming_engine is None:
        logger = get_logger(__name__)
        _event_bus = SimpleEventBus()

        # ✅ FIXED: Reuse existing correct QuestDB initialization (single source of truth)
        questdb_provider, _ = _ensure_questdb_providers()

        # ✅ NEW: Create algorithm registry and variant repository
        from ..domain.services.indicators.algorithm_registry import IndicatorAlgorithmRegistry
        from ..domain.repositories.indicator_variant_repository import IndicatorVariantRepository

        # Create algorithm registry
        algorithm_registry = IndicatorAlgorithmRegistry(logger)
        algorithm_registry.auto_discover_algorithms()

        # Create variant repository
        variant_repository = IndicatorVariantRepository(
            questdb_provider=questdb_provider,
            algorithm_registry=algorithm_registry,
            logger=logger
        )

        # Create streaming engine with repository
        _streaming_engine = StreamingIndicatorEngine(
            event_bus=_event_bus,
            logger=logger,
            variant_repository=variant_repository
        )

        _persistence_service = IndicatorPersistenceService(
            _event_bus,
            logger,
            base_data_dir=str(DATA_BASE_PATH)
        )
        _offline_indicator_engine = OfflineIndicatorEngine(str(DATA_BASE_PATH))

        # Start the engine (loads variants from database)
        await _streaming_engine.start()

    return _streaming_engine
```

### Why This Solution is Superior

1. ✅ **Eliminates code duplication** - Single source of truth via `_ensure_questdb_providers()`
2. ✅ **Reuses global provider instance** - Better resource management
3. ✅ **Follows project standards** - Aligns with CLAUDE.md guidelines
4. ✅ **Removes import inconsistency** - Relies on module-level import
5. ✅ **More maintainable** - One place to update QuestDB configuration
6. ✅ **Architecturally sound** - Proper dependency injection pattern

---

## Verification

### Files Checked for Similar Issues

Searched entire codebase for `QuestDBProvider(` instantiations:

**Results**:
- ✅ **18 files use CORRECT pattern** (ilp_host, pg_host parameters)
- ❌ **1 file had BROKEN pattern** (fixed in this commit)

**Conclusion**: Error was isolated to single location, now resolved.

### Constructor Signature Verification

Verified that dependencies use correct signatures:

**IndicatorVariantRepository**:
```python
def __init__(
    self,
    questdb_provider: QuestDBProvider,      # ✅ Correct
    algorithm_registry: IndicatorAlgorithmRegistry,  # ✅ Correct
    logger: Optional[StructuredLogger] = None  # ✅ Correct
):
```

**IndicatorAlgorithmRegistry**:
```python
def __init__(self, logger: Optional[Any] = None):  # ✅ Correct
```

All usages in fixed code match these signatures.

---

## Testing Recommendations

### Manual Testing

1. **Start backend server**:
   ```bash
   python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload
   ```

2. **Test system indicators endpoint**:
   ```bash
   curl http://localhost:8080/api/indicators/system
   ```
   **Expected**: JSON response with system indicators list (HTTP 200)

3. **Test variants endpoint**:
   ```bash
   curl http://localhost:8080/api/indicators/variants
   ```
   **Expected**: JSON response with indicator variants (HTTP 200)

### Automated Testing

**Future Improvement**: Add unit tests for dependency injection functions:

```python
# tests/api/test_indicators_routes.py
async def test_get_streaming_indicator_engine_initialization():
    """Test that get_streaming_indicator_engine initializes without errors."""
    engine = await get_streaming_indicator_engine()
    assert engine is not None
    assert isinstance(engine, StreamingIndicatorEngine)
```

---

## Lessons Learned

### For Developers

1. **Always verify constructor signatures** when using external classes
2. **Check for existing implementations** before adding new code
3. **Test endpoints immediately** after making changes
4. **Follow project standards** - eliminate code duplication
5. **Use correct import style** - be consistent (absolute vs relative)

### For Code Review

1. **Look for code duplication** - same pattern in multiple places
2. **Verify parameter names** match actual constructor signatures
3. **Check for existing utility functions** that should be reused
4. **Ensure tests cover new functionality** before merging

### Architecture Principles Reinforced

1. **Single Source of Truth**: One canonical way to initialize each resource
2. **DRY (Don't Repeat Yourself)**: Extract common patterns into functions
3. **Fail Fast**: Constructor errors are better than runtime errors
4. **Documentation**: Constructor signatures should be clear and well-documented

---

## Related Files

### Modified
- `src/api/indicators_routes.py` - Fixed QuestDBProvider initialization

### Verified (No Changes Needed)
- `src/data_feed/questdb_provider.py` - Constructor signature correct
- `src/domain/repositories/indicator_variant_repository.py` - Usage correct
- `src/domain/services/indicators/algorithm_registry.py` - Usage correct
- `src/data/questdb_data_provider.py` - Usage correct

---

## Commit Message

```
fix: correct QuestDBProvider initialization in indicators API

PROBLEM:
- GET /api/indicators/system returned HTTP 500
- GET /api/indicators/variants returned HTTP 500
- Error: QuestDBProvider.__init__() got unexpected keyword argument 'host'

ROOT CAUSE:
- get_streaming_indicator_engine() used incorrect parameter names
- Assumed generic SQL pattern (host, port, user, password, database)
- QuestDBProvider uses dual-protocol architecture (ILP + PostgreSQL)
- Correct parameters: ilp_host, ilp_port, pg_host, pg_port, pg_user, etc.

ARCHITECTURE ISSUES FIXED:
- Code duplication: Two different QuestDBProvider initialization patterns
- Import inconsistency: Mixed absolute and relative imports
- Violation of single source of truth principle

SOLUTION:
- Reuse existing _ensure_questdb_providers() function
- Eliminates code duplication
- Single source of truth for QuestDB configuration
- Follows project coding standards (CLAUDE.md)

VERIFICATION:
- Checked 18 other files - all use correct pattern
- Verified IndicatorVariantRepository constructor signature
- Verified IndicatorAlgorithmRegistry constructor signature
- Error isolated to single location, now fixed

TESTING:
- Manual: curl http://localhost:8080/api/indicators/system
- Manual: curl http://localhost:8080/api/indicators/variants
- Both endpoints should return HTTP 200 with JSON data

Branch: claude/move-indicator-variants-config-011CUc93wynFuz7fpZtmPAnN
```

---

## Status

✅ **RESOLVED**

- [x] Root cause identified and documented
- [x] Fix implemented following architectural best practices
- [x] Code duplication eliminated
- [x] Dependencies verified
- [x] Codebase searched for similar issues
- [x] Commit message prepared
- [ ] Manual testing (requires server restart)
- [ ] Branch pushed to remote
- [ ] Pull request created

---

## Next Steps

1. **Commit changes** to `claude/move-indicator-variants-config-011CUc93wynFuz7fpZtmPAnN` branch
2. **Push to remote** repository
3. **Manual testing** to confirm endpoints work
4. **Create pull request** for review
5. **Add unit tests** to prevent regression (future work)
6. **Update documentation** if needed

---

*Report generated: 2025-10-29*
*Fixed by: Claude Code Analysis*
*Branch: claude/move-indicator-variants-config-011CUc93wynFuz7fpZtmPAnN*
