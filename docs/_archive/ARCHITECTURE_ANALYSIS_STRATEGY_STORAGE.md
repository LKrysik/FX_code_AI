# Architecture Analysis - Missing strategy_storage Module

**Date:** 2025-11-05
**Analyzer:** Claude
**Scope:** ModuleNotFoundError for src.domain.services.strategy_storage
**Methodology:** Strict architectural analysis per user requirements

---

## 📋 Executive Summary

**CRITICAL RUNTIME ERROR:**
```
ModuleNotFoundError: No module named 'src.domain.services.strategy_storage'
```

**ROOT CAUSE:** Incomplete refactoring - module deleted but imports not updated

**IMPACT:** Complete backend failure - server cannot start

**AFFECTED COMPONENTS:**
- ❌ Backend API (7 strategy endpoints broken)
- ❌ Frontend (backtesting page, paper trading page)
- ❌ Tests (test_strategies.py cannot run)
- ❌ Existing strategy data (5 JSON files inaccessible)

---

## 🔍 Phase 1: Detailed Architecture Analysis

### Current File Structure

**FILES THAT EXIST:**
```
✅ src/domain/services/strategy_storage_questdb.py (498 lines)
   - QuestDBStrategyStorage class
   - CRUD operations for strategies table
   - Uses asyncpg for PostgreSQL protocol
   - Soft delete support (is_deleted flag)

✅ src/domain/services/strategy_storage_resilient.py (300 lines)
   - ResilientStrategyStorage class
   - Wrapper providing primary + fallback pattern
   - Primary: QuestDB (preferred)
   - Fallback: File-based JSON storage
   - Auto-switching on connection failures

❌ src/domain/services/strategy_storage.py (DELETED)
   - Was: 311 lines of file-based StrategyStorage
   - Deleted in commit 7a6890b as "unused"
   - Status: COMPLETELY REMOVED from repository
```

### Architecture Pattern: Resilient Storage

```
┌──────────────────────────────────────────┐
│   API Layer (unified_server.py)          │
│   - 7 strategy endpoints                 │
│   - Uses app.state.strategy_storage      │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────┐
│   ResilientStrategyStorage               │  ← BROKEN (Line 30 import fails)
│   (strategy_storage_resilient.py)       │
│                                          │
│   ┌──────────────┬──────────────┐      │
│   │   Primary    │   Fallback   │      │
│   │   (QuestDB)  │  (File JSON) │      │
│   │      ✅      │      ❌      │      │  ← Fallback missing
│   └──────────────┴──────────────┘      │
└──────────────────────────────────────────┘
```

**Design Intent:**
- **Primary backend:** QuestDB - preferred for production
- **Fallback backend:** File-based JSON - used when QuestDB unavailable
- **Transparent switching:** Automatic failover with caching (30s interval)
- **Single interface:** Same methods for both backends

---

## 🕵️ Phase 2: Complete Dependency Trace

### Direct Dependencies

**strategy_storage_resilient.py (BROKEN FILE):**
```python
Line 24-29: from src.domain.services.strategy_storage_questdb import (
                QuestDBStrategyStorage,                    # ✅ EXISTS
                StrategyStorageError,                      # ✅ EXISTS
                StrategyNotFoundError,                     # ✅ EXISTS
                StrategyValidationError                    # ✅ EXISTS
            )
Line 30:    from src.domain.services.strategy_storage import StrategyStorage  # ❌ MISSING

Line 73-79: self._primary = QuestDBStrategyStorage(...)   # ✅ WORKS
Line 84:    self._fallback = StrategyStorage(...)          # ❌ BREAKS AT IMPORT (never reaches here)
```

**unified_server.py (API Layer):**
```python
Line 44:  from src.domain.services.strategy_storage_resilient import ResilientStrategyStorage
Line 150: strategy_storage = ResilientStrategyStorage(...)
Line 158: await strategy_storage.initialize()
Line 159: app.state.strategy_storage = strategy_storage
Line 493: await app.state.strategy_storage.close()

# 7 API Endpoints that use it:
Line 578: POST   /api/strategies              - create_strategy()
Line 643: GET    /api/strategies              - list_strategies()
Line 662: GET    /api/strategies/{id}         - read_strategy()
Line 683: PUT    /api/strategies/{id}         - update_strategy()
Line 759: DELETE /api/strategies/{id}         - delete_strategy()
Line 803: POST   /api/strategies/validate     - validate_strategy()
Line 1481: GET   /strategies/status           - get_strategy_status()
```

### Indirect Dependencies (Downstream Impact)

**Frontend Components:**
- `frontend/src/app/backtesting/page.tsx` - Strategy selection dropdown
- `frontend/src/app/paper-trading/page.tsx` - Strategy management UI
- `frontend/src/services/strategiesApi.ts` - API client wrapper
- `frontend/src/services/api.ts` - HTTP client

**Test Suite:**
- `tests_e2e/api/test_strategies.py` - 20+ strategy CRUD tests
- `tests_e2e/integration/test_complete_flow.py` - Integration tests
- `tests_e2e/conftest.py` - Test fixtures

**Data Files:**
```bash
config/strategies/
├── 2ac06bbd-80a7-4f0a-8f9f-7a0686c834c3.json (748 bytes)
├── 923f38d3-b0b4-493b-9c36-c090b91dafaa.json (1079 bytes)
├── d360ad53-aa8f-46d8-8fa2-0b8add532d05.json (559 bytes)
├── f4b09c4f-259f-465e-b6f7-e0a398ed9de0.json (751 bytes)
└── short_selling_pump_dump_v1.json (4611 bytes)
```
**Status:** 5 JSON files exist but are INACCESSIBLE due to broken fallback

---

## ✅ Phase 3: Assumption Verification (Git History)

### Timeline of Changes

**Commit 394e296 (2025-11-05 07:06:31 UTC) - 5 minutes before deletion:**
```
fix(backtesting): Restore strategy selection with resilient storage fallback

Created: strategy_storage_resilient.py (299 lines)
Purpose: Add resilient fallback for QuestDB failures
Fallback: strategy_storage.py (file-based JSON)

Justification from commit message:
"PROBLEM: Backend required QuestDB which wasn't running, causing API failures"
"SOLUTION: Fallback: File-based JSON storage (config/strategies/*.json)"
"IMPACT: System remains functional even when QuestDB is down"
```

**Commit 7a6890b (2025-11-05 07:11:30 UTC) - THE BREAKING CHANGE:**
```
fix: Strategy storage UPDATE/DELETE errors (QuestDB TIMESTAMP + soft delete)

Deleted: src/domain/services/strategy_storage.py
Reason: "311 lines of unused file-based storage"
Files changed:
  D src/domain/services/strategy_storage.py
  M src/domain/services/strategy_storage_questdb.py

FORGOT TO UPDATE: strategy_storage_resilient.py still imports deleted file
```

### Verified Facts

✅ **VERIFIED:** strategy_storage.py existed before commit 7a6890b
✅ **VERIFIED:** strategy_storage.py was deleted IN commit 7a6890b
✅ **VERIFIED:** Deletion reason stated "unused file-based storage"
✅ **VERIFIED:** strategy_storage_resilient.py was NOT updated
✅ **VERIFIED:** unified_server.py STILL uses ResilientStrategyStorage
✅ **VERIFIED:** Comment in unified_server.py still mentions "Fallback: File-based"
✅ **VERIFIED:** 5 strategy JSON files exist on disk

### Contradiction in Architecture

**5 minutes apart, two contradictory decisions:**

1. **07:06 - ADD resilient fallback** for QuestDB failures
2. **07:11 - REMOVE fallback** as "unused"

**Conclusion:** This is a **BROKEN REFACTORING**, not intentional design change.

---

## ⚠️ Phase 4: Architectural Issues Identified

### Issue #1: Incomplete Refactoring (CRITICAL)

**Problem:** Module deleted but imports not updated

**Evidence:**
- Line 30 of strategy_storage_resilient.py imports deleted module
- Import fails at module load time (not runtime)
- Backend cannot start at all

**Impact Severity:** 🔴 **BLOCKER** - Complete system failure

**CLAUDE.md Violation:** "Zweryfikuj swoje założenia, nie może być założeń bez weryfikacji"
- Refactoring assumed file was unused
- Did not verify all import references
- Did not test that backend starts after deletion

### Issue #2: Conflicting Architectural Patterns

**Problem:** Two contradictory patterns exist simultaneously

**Pattern A - "Resilient Storage" (Current Code):**
- ResilientStrategyStorage provides QuestDB + fallback
- Graceful degradation when database down
- Used by unified_server.py
- Comment: "Fallback: File-based (config/strategies/*.json)"

**Pattern B - "QuestDB Only" (Intent from deletion?):**
- Direct QuestDBStrategyStorage without fallback
- Hard dependency on QuestDB availability
- Fail-fast when database unavailable

**Current State:** Neither pattern is functional - code references Pattern A but Pattern B was partially applied

**CLAUDE.md Violation:** "nie chce żeby istniały równoległe rozwiązania"
- Two patterns exist (resilient wrapper vs direct storage)
- Neither is complete
- No clear architectural direction

### Issue #3: Dead Code in strategy_storage_resilient.py

**Problem:** Entire 300-line file is now dead code if fallback deleted intentionally

**Analysis:**
```python
# If StrategyStorage doesn't exist, entire file is pointless:
class ResilientStrategyStorage:
    def __init__(self, ...):
        self._primary = QuestDBStrategyStorage(...)  # Could use directly
        self._fallback = StrategyStorage(...)        # BROKEN

    async def _execute_with_fallback(self, ...):
        # Entire fallback logic is dead code if fallback never works
        # Should just use self._primary directly
```

**If fallback removed intentionally:**
- ResilientStrategyStorage is now just expensive wrapper
- unified_server.py could use QuestDBStrategyStorage directly
- 300 lines of unnecessary complexity

**CLAUDE.md Violation:** "Przy każdej okazji weryfikuj czy w danym obszarze analizy występują jakieś problemy z kodem... albo dead code"

### Issue #4: Frontend Expects Resilience

**Problem:** Frontend built expecting fallback to work

**Evidence from commit 394e296:**
- Backtesting page restored to use strategy selection
- Assumed strategies always accessible (QuestDB OR files)
- No error handling for "QuestDB required but unavailable"

**If QuestDB is now required:**
- Frontend needs update to show clear error
- Users need instructions to start QuestDB
- Graceful degradation is lost

### Issue #5: Existing Data Orphaned

**Problem:** 5 strategy JSON files exist but cannot be accessed

**Current State:**
```bash
config/strategies/
├── 2ac06bbd-*.json  # Created before QuestDB migration
├── 923f38d3-*.json  # These files exist but...
├── d360ad53-*.json  # ...no code can read them anymore
├── f4b09c4f-*.json
└── short_selling_pump_dump_v1.json (4.6KB - largest file)
```

**Questions:**
1. Should these files be migrated to QuestDB?
2. Should these files be deleted?
3. Should file-based storage be restored?

**CLAUDE.md Violation:** "Śledź powiązane obiekty"
- Deletion didn't consider existing data files
- No migration path provided
- Data is now orphaned

### Issue #6: Test Coverage Gap

**Problem:** No tests verify resilient fallback actually works

**Evidence:**
```python
# tests_e2e/api/test_strategies.py
# Tests CRUD operations but assumes storage always works
# No tests for:
# - QuestDB unavailable scenario
# - Fallback switching
# - Resilient recovery
```

**Impact:** This is why broken refactoring wasn't caught by tests

---

## 📊 Impact Assessment

### Components Broken

| Component | Status | Impact |
|-----------|--------|--------|
| Backend API | ❌ Won't start | Complete failure |
| Strategy CRUD endpoints | ❌ Unreachable | 7 endpoints down |
| Frontend (backtesting) | ❌ Can't load strategies | Page non-functional |
| Frontend (paper trading) | ❌ Can't manage strategies | Feature broken |
| Test suite | ❌ Can't run | 20+ tests fail to start |
| Existing JSON files | ⚠️ Orphaned | Data inaccessible |

### User Impact

**If QuestDB is running:**
- Users MIGHT not notice if they only use QuestDB
- But backend won't start due to import error

**If QuestDB is not running:**
- Fallback was designed for this case
- Now system is completely non-functional
- No graceful degradation

---

## 🎯 Architectural Decision Required

### Option A: Restore File-Based Fallback (Resilient Architecture)

**Approach:** Fix the broken refactoring by restoring file-based storage

**Actions:**
1. Restore `strategy_storage.py` from commit 394e296^
2. Keep ResilientStrategyStorage wrapper
3. Maintain graceful degradation design

**Pros:**
✅ Honors original design intent (commit 394e296)
✅ System works even when QuestDB down
✅ Existing JSON files accessible
✅ Frontend expectations met
✅ Minimal code changes

**Cons:**
❌ Maintains parallel storage implementations
❌ Violates CLAUDE.md: "nie chce żeby istniały równoległe rozwiązania"
❌ Adds complexity with dual-storage pattern

**Alignment with CLAUDE.md:** ❌ **POOR**
- Creates parallel solutions
- Maintains backward compatibility workaround
- Not target architecture

### Option B: Remove Resilient Wrapper (QuestDB-Only Architecture)

**Approach:** Complete the refactoring by making QuestDB required

**Actions:**
1. DELETE strategy_storage_resilient.py (300 lines dead code)
2. UPDATE unified_server.py to use QuestDBStrategyStorage directly
3. MIGRATE existing JSON files to QuestDB (5 files)
4. UPDATE documentation to state QuestDB is required
5. UPDATE frontend error handling for missing database

**Pros:**
✅ Single source of truth (QuestDB only)
✅ No parallel solutions
✅ No backward compatibility workarounds
✅ Aligns with CLAUDE.md principles perfectly
✅ Simplifies architecture
✅ Matches existing pattern (QuestDB is primary DB for all other data)

**Cons:**
❌ System won't work if QuestDB unavailable
❌ No graceful degradation
❌ More changes required (but cleaner result)

**Alignment with CLAUDE.md:** ✅ **EXCELLENT**
- Single source of truth
- No parallel solutions
- Target architecture only
- No backward compatibility hacks

### Option C: In-Memory Fallback (Hybrid Architecture)

**Approach:** Keep resilient wrapper but use in-memory cache instead of files

**Actions:**
1. Replace StrategyStorage with in-memory dict fallback
2. Keep ResilientStrategyStorage pattern
3. Fallback loads from JSON files once on startup

**Pros:**
✅ Maintains resilience pattern
✅ No file I/O on every operation
✅ Simpler than dual persistence

**Cons:**
❌ Still has parallel solutions
❌ In-memory cache can go stale
❌ More complex than Option B

**Alignment with CLAUDE.md:** ⚠️ **MODERATE**
- Reduces duplication but doesn't eliminate it

---

## 📋 Summary for User Decision

**Question for User:**

The code has **two contradictory architectural patterns**:

1. **Resilient Storage** (7:06am commit) - QuestDB + file-based fallback
2. **QuestDB Only** (7:11am commit) - deleted fallback as "unused"

**Neither pattern is functional** - import fails and backend won't start.

**My Recommendation (based on CLAUDE.md):**

**Option B - QuestDB-Only Architecture**

**Reasons:**
1. ✅ Matches CLAUDE.md: "nie chce żeby istniały równoległe rozwiązania"
2. ✅ Matches CLAUDE.md: "nie chce backward compatible, chce docelowy kod"
3. ✅ Single source of truth
4. ✅ Aligns with project architecture (QuestDB is already primary DB)
5. ✅ Simpler, cleaner code
6. ✅ No dead code (removes 300-line wrapper)

**Justification:**

From CLAUDE.md:
> **CRITICAL ARCHITECTURAL DECISION:** CSV storage is being phased out. QuestDB is now the primary database:
> - Data collection writes **directly** to QuestDB (no CSV fallback)
> - Backtests read **exclusively** from QuestDB

This shows the project is already moving to **database-only** architecture. Strategy storage should follow the same pattern.

**What this means:**
- QuestDB becomes REQUIRED dependency (already is for other features)
- Users must run QuestDB to use the system (already documented)
- Fail-fast with clear error if database unavailable
- 5 existing JSON files will be migrated to QuestDB

---

## ❓ User Decision Point

Before proceeding to Phase 5 (Proposal), I need your architectural direction:

**Option A:** Restore file-based fallback (resilient but parallel solutions)
**Option B:** Make QuestDB required (clean single-source but no fallback) ⭐ **RECOMMENDED**
**Option C:** In-memory fallback (hybrid approach)

Which option aligns with your vision for the target architecture?
