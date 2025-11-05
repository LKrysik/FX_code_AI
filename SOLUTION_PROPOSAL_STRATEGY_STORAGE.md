# Solution Proposal - QuestDB-Only Strategy Storage Architecture

**Date:** 2025-11-05
**Approach:** Option B - Complete refactoring to QuestDB-only (no fallback)
**Justification:** Aligns with CLAUDE.md principles and project's database-only direction

---

## 🎯 Executive Summary

**CHOSEN SOLUTION:** Make QuestDB the **single required dependency** for strategy storage

**Key Actions:**
1. ✅ DELETE strategy_storage_resilient.py (300 lines of dead code)
2. ✅ UPDATE unified_server.py to use QuestDBStrategyStorage directly
3. ✅ MIGRATE 5 existing JSON files to QuestDB
4. ✅ UPDATE documentation to state QuestDB is required
5. ✅ ADD fail-fast validation with clear error messages
6. ✅ NO tests need updating (API contract unchanged)

**Result:** Clean, single-source-of-truth architecture with no parallel solutions

---

## 📖 Justification (Full Context)

### Alignment with CLAUDE.md Principles

**Principle 1: "NO backward compatibility workarounds"**
```
User requirement: "nie chce backward compatible, chce docelowy kod"
Solution: Remove resilient wrapper entirely, make QuestDB required
```

**Principle 2: "NO parallel solutions"**
```
User requirement: "nie chce żeby istniały równoległe rozwiązania"
Current state: QuestDB storage + file-based storage (parallel)
Solution: Single storage implementation (QuestDB only)
```

**Principle 3: "QuestDB as single source of truth"**
```
From CLAUDE.md:
"CRITICAL ARCHITECTURAL DECISION: CSV storage is being phased out.
QuestDB is now the primary database:
- Data collection writes directly to QuestDB (no CSV fallback)
- Backtests read exclusively from QuestDB"

Solution: Strategy storage follows same pattern as other data
```

**Principle 4: "Eliminate code duplication"**
```
Current: 300-line ResilientStrategyStorage wrapper + QuestDBStrategyStorage
Solution: QuestDBStrategyStorage only (498 lines, no wrapper)
Removed: 300 lines of wrapper code, 150 lines of fallback logic
```

### Alignment with Project Architecture

**Existing Database-Only Patterns:**

1. **Data Collection** → QuestDB only (no CSV fallback)
   - tick_prices table
   - data_collection_sessions table
   - CLAUDE.md explicitly states "NO CSV fallback"

2. **Indicators** → QuestDB only
   - indicators table
   - indicator_variants table (from variant_repository)
   - No fallback storage

3. **Paper Trading** → QuestDB only
   - paper_positions table
   - paper_trades table
   - No fallback mentioned

4. **Backtesting Results** → QuestDB expected
   - backtest_results table (planned)

**Strategy Storage SHOULD follow same pattern** - QuestDB only, no fallback

### Why NOT Resilient Fallback?

**Argument AGAINST file-based fallback:**

1. **Complexity without benefit**
   - 300 lines of wrapper code
   - Two storage implementations to maintain
   - Complex cache invalidation logic
   - Synchronization challenges

2. **False sense of resilience**
   - If QuestDB is down, REST of the system is ALSO broken (tick_prices, indicators, etc.)
   - Fallback doesn't make system functional, just hides the real problem
   - Better to fail-fast and show clear error: "QuestDB required"

3. **Inconsistent with other components**
   - Data collection doesn't have fallback
   - Indicators don't have fallback
   - Why should strategies be special?

4. **Maintenance burden**
   - Must maintain two storage implementations
   - Must test both code paths
   - Must handle synchronization issues

5. **CLAUDE.md explicitly forbids this pattern**
   - "NO backward compatibility workarounds"
   - "NO parallel solutions"
   - Resilient wrapper IS a parallel solution

---

## 🔧 Implementation Plan

### Step 1: Update unified_server.py (Remove wrapper usage)

**Current Code (Lines 44, 148-167):**
```python
from src.domain.services.strategy_storage_resilient import ResilientStrategyStorage

# Initialize strategy storage with resilient fallback
# Primary: QuestDB (preferred), Fallback: File-based (config/strategies/*.json)
strategy_storage = ResilientStrategyStorage(
    questdb_host="127.0.0.1",
    questdb_port=8812,
    questdb_user="admin",
    questdb_password="quest",
    questdb_database="qdb",
    logger=logger
)
await strategy_storage.initialize()
app.state.strategy_storage = strategy_storage

# Log backend status
backend_status = strategy_storage.get_backend_status()
logger.info("Strategy storage initialized with resilient fallback", {
    "primary": backend_status["primary_backend"],
    "fallback": backend_status["fallback_backend"],
    "active": backend_status["current_backend"]
})
```

**New Code:**
```python
from src.domain.services.strategy_storage_questdb import (
    QuestDBStrategyStorage,
    StrategyStorageError,
    StrategyNotFoundError,
    StrategyValidationError
)

# Initialize strategy storage (QuestDB required)
strategy_storage = QuestDBStrategyStorage(
    host="127.0.0.1",
    port=8812,
    user="admin",
    password="quest",
    database="qdb"
)

# Fail-fast validation - QuestDB must be available
try:
    await strategy_storage.initialize()
    app.state.strategy_storage = strategy_storage
    logger.info("Strategy storage initialized", {
        "backend": "QuestDB",
        "host": "127.0.0.1",
        "port": 8812,
        "status": "connected"
    })
except Exception as e:
    logger.error("strategy_storage.initialization_failed", {
        "backend": "QuestDB",
        "error": str(e),
        "solution": "Ensure QuestDB is running on port 8812. Run: python database/questdb/install_questdb.py"
    })
    # Re-raise to prevent server start with broken storage
    raise RuntimeError(
        "Strategy storage initialization failed. QuestDB is required. "
        f"Error: {e}. "
        "Solution: Ensure QuestDB is running (port 8812). "
        "See: docs/database/QUESTDB.md"
    )
```

**Changes:**
- ✅ Direct import of QuestDBStrategyStorage
- ✅ Remove ResilientStrategyStorage wrapper
- ✅ Fail-fast with clear error message
- ✅ Provide solution in error message
- ✅ Prevent server start if database unavailable

**Justification:**
- Aligns with CLAUDE.md: "Fail-fast validation"
- Clear error message guides user to solution
- No silent failures or unclear states

### Step 2: Delete strategy_storage_resilient.py

**File:** `src/domain/services/strategy_storage_resilient.py`
**Status:** 300 lines of dead code (with broken import)
**Action:** DELETE completely

**Justification:**
- File serves no purpose without fallback storage
- Just an expensive wrapper around QuestDBStrategyStorage
- CLAUDE.md: "Przy każdej okazji weryfikuj... dead code"
- Simplifies codebase by 300 lines

### Step 3: Migrate Existing JSON Files to QuestDB

**Files to migrate:**
```bash
config/strategies/
├── 2ac06bbd-80a7-4f0a-8f9f-7a0686c834c3.json (748 bytes)
├── 923f38d3-b0b4-493b-9c36-c090b91dafaa.json (1079 bytes)
├── d360ad53-aa8f-46d8-8fa2-0b8add532d05.json (559 bytes)
├── f4b09c4f-259f-465e-b6f7-e0a398ed9de0.json (751 bytes)
└── short_selling_pump_dump_v1.json (4611 bytes)
```

**Migration Script:**
```python
# scripts/migrate_strategy_json_to_questdb.py
"""
One-time migration: Load JSON strategy files → Insert into QuestDB
"""
import asyncio
import json
from pathlib import Path
from src.domain.services.strategy_storage_questdb import QuestDBStrategyStorage

async def migrate_strategies():
    storage = QuestDBStrategyStorage(
        host="127.0.0.1",
        port=8812,
        user="admin",
        password="quest",
        database="qdb"
    )

    await storage.initialize()

    json_dir = Path("config/strategies")
    migrated = 0
    skipped = 0
    errors = 0

    for json_file in json_dir.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                strategy_data = json.load(f)

            # Check if already exists in QuestDB (by ID)
            strategy_id = strategy_data.get("id")
            if strategy_id:
                try:
                    existing = await storage.read_strategy(strategy_id)
                    print(f"⏭️  SKIP {json_file.name}: Already in QuestDB (ID: {strategy_id})")
                    skipped += 1
                    continue
                except:
                    pass  # Not found, proceed with migration

            # Insert into QuestDB
            new_id = await storage.create_strategy(strategy_data)
            print(f"✅ MIGRATED {json_file.name} → QuestDB (ID: {new_id})")
            migrated += 1

        except Exception as e:
            print(f"❌ ERROR {json_file.name}: {e}")
            errors += 1

    await storage.close()

    print(f"\n📊 Migration Summary:")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")

    if errors == 0:
        print(f"\n✅ All strategies successfully in QuestDB")
        print(f"ℹ️  JSON files in config/strategies/ can now be deleted (backup first!)")

if __name__ == "__main__":
    asyncio.run(migrate_strategies())
```

**Usage:**
```bash
# Ensure QuestDB is running
python database/questdb/install_questdb.py  # If not already running

# Run migration
python scripts/migrate_strategy_json_to_questdb.py

# Backup JSON files
tar -czf config/strategies_backup.tar.gz config/strategies/

# (Optional) Delete JSON files after verification
# rm config/strategies/*.json
```

### Step 4: Update Documentation

**Files to update:**

**4a. CLAUDE.md**

Add to "Database Architecture" section:
```markdown
### Strategy Storage

**Storage:** QuestDB `strategies` table (see migration 012)
**Access:** Via QuestDBStrategyStorage service
**Required:** QuestDB must be running for backend to start

⚠️ **BREAKING CHANGE (2025-11-05):** File-based strategy storage removed.
- Old: config/strategies/*.json files (DEPRECATED)
- New: QuestDB strategies table only
- Migration: Run `scripts/migrate_strategy_json_to_questdb.py`
```

**4b. docs/database/QUESTDB.md**

Add to "Required Tables" section:
```markdown
### strategies (Strategy Configuration)

**Purpose:** Trading strategy persistence
**Created by:** Migration 012_create_strategies_table.sql
**Access:** Via QuestDBStrategyStorage

**Schema:**
- id: UUID string (primary key)
- strategy_name: User-defined name
- direction: LONG/SHORT/BOTH
- enabled: Boolean
- strategy_json: Full config as JSON string
- author, category, tags: Metadata
- created_at, updated_at, last_activated_at: Timestamps
- is_deleted, deleted_at: Soft delete support (migration 014)

**Required:** Backend will not start without this table.
```

**4c. README.md**

Update "Quick Start" section:
```markdown
### Prerequisites

**QuestDB (Required):**
```bash
# Install and start QuestDB
python database/questdb/install_questdb.py

# Verify QuestDB is running
# Web UI: http://127.0.0.1:9000
# PostgreSQL port: 8812

# Run migrations (creates required tables)
python database/questdb/run_migrations.py
```

**Backend will fail to start if QuestDB is not running.**
```

### Step 5: NO Test Updates Required

**Analysis of tests_e2e/api/test_strategies.py:**
```python
# All tests use API endpoints, not storage directly:
def test_create_strategy_success(self, authenticated_client, valid_strategy_config):
    response = authenticated_client.post("/api/strategies", json=valid_strategy_config)
    # Tests API contract, not storage implementation
```

**Justification for NO updates:**
1. ✅ Tests interact via API endpoints, not storage layer directly
2. ✅ API contract unchanged (same endpoints, same responses)
3. ✅ QuestDB is already required for E2E tests (conftest.py setup)
4. ✅ Tests already assume database is available
5. ✅ No tests verify resilient fallback behavior (it was never tested)

**Verification:**
```bash
# Tests will pass after fix (assuming QuestDB running)
pytest tests_e2e/api/test_strategies.py -v
```

**No changes needed to:**
- tests_e2e/api/test_strategies.py (API tests)
- tests_e2e/conftest.py (fixtures)
- run_tests.py (test runner)

---

## 📊 Change Summary

### Files Modified

| File | Action | Lines Changed | Justification |
|------|--------|---------------|---------------|
| src/api/unified_server.py | MODIFY | ~30 | Direct QuestDB usage, fail-fast error handling |
| src/domain/services/strategy_storage_resilient.py | DELETE | -300 | Dead code, wrapper no longer needed |
| CLAUDE.md | MODIFY | +15 | Document breaking change |
| docs/database/QUESTDB.md | MODIFY | +20 | Document strategy storage requirements |
| README.md | MODIFY | +10 | Add QuestDB as required prerequisite |
| scripts/migrate_strategy_json_to_questdb.py | CREATE | +60 | One-time migration script |

**Total:** 1 file deleted, 4 modified, 1 created
**Net Lines:** -300 deleted, +105 added = **-195 lines** (code reduction)

### Files NOT Modified (Verification)

| File | Reason |
|------|--------|
| src/domain/services/strategy_storage_questdb.py | ✅ Already correct, no changes needed |
| tests_e2e/api/test_strategies.py | ✅ API contract unchanged |
| tests_e2e/conftest.py | ✅ Already assumes QuestDB available |
| run_tests.py | ✅ No test changes needed |
| frontend/src/**/*.tsx | ✅ API contract unchanged |

---

## ✅ Verification Plan

### Step 1: Backend Starts Successfully

```bash
# Ensure QuestDB running
python database/questdb/install_questdb.py

# Start backend
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080

# Expected log output:
# ✅ "Strategy storage initialized" (backend="QuestDB", status="connected")
# ✅ Server starts on port 8080
```

**If QuestDB not running:**
```
❌ RuntimeError: Strategy storage initialization failed. QuestDB is required.
   Solution: Ensure QuestDB is running (port 8812). See: docs/database/QUESTDB.md
```

### Step 2: API Endpoints Work

```bash
# List strategies
curl -X GET http://localhost:8080/api/strategies \
  -H "Authorization: Bearer <token>"

# Expected: 200 OK, list of strategies from QuestDB
```

### Step 3: Frontend Works

1. Open http://localhost:3000/backtesting
2. Strategy dropdown loads
3. Select strategy → works
4. Create backtest → works

### Step 4: Tests Pass

```bash
# Run strategy API tests
pytest tests_e2e/api/test_strategies.py -v

# Expected: All 20+ tests PASS
```

### Step 5: Migrated Data Accessible

```bash
# Run migration
python scripts/migrate_strategy_json_to_questdb.py

# Verify via API
curl -X GET http://localhost:8080/api/strategies | jq '.data.strategies | length'

# Expected: 5 (or more if new strategies created)
```

---

## 🎯 Success Criteria

**CRITICAL (Must Pass):**
1. ✅ Backend starts successfully (no ModuleNotFoundError)
2. ✅ All 7 strategy API endpoints return 200 OK
3. ✅ Frontend strategy pages load without errors
4. ✅ All E2E tests pass (test_strategies.py)
5. ✅ No dead code remains (resilient wrapper deleted)

**IMPORTANT (Should Pass):**
1. ✅ Clear error message if QuestDB unavailable
2. ✅ All 5 JSON files migrated to QuestDB
3. ✅ Documentation updated
4. ✅ Code reduction (-195 lines net)

**NICE TO HAVE:**
1. ⚪ Migration script handles edge cases gracefully
2. ⚪ README clearly states QuestDB is required

---

## 🚀 Implementation Order

**Order matters** - follow this sequence to avoid breaking changes:

1. ✅ **FIRST:** Create migration script (doesn't break anything)
2. ✅ **SECOND:** Run migration (JSON → QuestDB, safe operation)
3. ✅ **THIRD:** Modify unified_server.py (fixes import error)
4. ✅ **FOURTH:** Delete strategy_storage_resilient.py (cleanup)
5. ✅ **FIFTH:** Update documentation (informational)
6. ✅ **SIXTH:** Test everything (verification)

**Reasoning:**
- Migration first ensures data safety
- Server fix allows backend to start
- Deletion removes dead code after fix works
- Docs updated last (no code impact)

---

## ⚠️ Risks and Mitigations

### Risk 1: QuestDB Not Running

**Risk:** User tries to start backend but QuestDB not running
**Impact:** Backend fails to start
**Mitigation:**
- ✅ Clear error message with solution
- ✅ README states QuestDB is required
- ✅ Fail-fast prevents unclear runtime errors

### Risk 2: Data Loss from JSON Files

**Risk:** JSON files deleted before migration
**Impact:** Historical strategies lost
**Mitigation:**
- ✅ Migration script checks for duplicates (skip if exists)
- ✅ Backup command in migration instructions
- ✅ JSON files NOT deleted automatically

### Risk 3: Tests Fail After Change

**Risk:** API contract changed inadvertently
**Impact:** Frontend broken, tests fail
**Mitigation:**
- ✅ API contract unchanged (same endpoints, same responses)
- ✅ Tests verify this automatically
- ✅ Only storage implementation changed (transparent to API)

---

## 📋 Conclusion

**This solution:**
1. ✅ Fixes ModuleNotFoundError (backend will start)
2. ✅ Aligns with CLAUDE.md (no parallel solutions, no backward compatibility)
3. ✅ Simplifies architecture (single source of truth)
4. ✅ Reduces code (-195 lines net)
5. ✅ Maintains API contract (no breaking changes for consumers)
6. ✅ Provides migration path (JSON → QuestDB)
7. ✅ Fail-fast validation (clear errors)
8. ✅ No test updates needed

**Ready to implement in Phase 7.**
