# Strategy Storage QuestDB Migration - Testing Guide
**Date:** 2025-11-04
**Purpose:** Test strategy persistence migration from CSV files to QuestDB
**Related Commit:** 719e7cc - fix(persistence): Migrate strategy storage from CSV files to QuestDB

---

## 📋 Overview

Strategies are now saved to **QuestDB** table `strategies` instead of CSV/JSON files in `config/strategies/`.

**What Changed:**
- ❌ OLD: File-based storage (`StrategyStorage` → `config/strategies/*.json`)
- ✅ NEW: Database storage (`QuestDBStrategyStorage` → `strategies` table)

**Why:**
- ACID guarantees (no file corruption)
- Concurrent access (connection pooling)
- Fast queries (indexed fields)
- Consistent with architecture (everything in QuestDB)

---

## 🔧 Prerequisites

### 1. QuestDB Must Be Running
```bash
# Check if QuestDB is running
curl -s http://127.0.0.1:9000/exec?query=SELECT+1 || echo "QuestDB NOT running!"

# If not running, start it:
cd database/questdb
python install_questdb.py  # First time only
# Then start QuestDB instance (follow install_questdb.py output)
```

**Expected:** HTTP 200 response from http://127.0.0.1:9000

**Ports:**
- Web UI: http://127.0.0.1:9000
- PostgreSQL: localhost:8812 (used by strategy storage)
- InfluxDB Line Protocol: localhost:9009

### 2. Run Migration 012
```sql
-- Open http://127.0.0.1:9000 (QuestDB Web UI)
-- Click "SQL Editor"
-- Paste and execute:

-- Check if table already exists
SELECT table_name FROM tables() WHERE table_name = 'strategies';

-- If empty result, run migration:
-- Copy contents of database/questdb/migrations/012_create_strategies_table.sql
-- Paste and execute
```

**Expected Output:**
```
table_name
strategies
```

### 3. Verify Table Schema
```sql
-- In QuestDB Web UI, run:
SELECT column, type FROM table_columns('strategies');
```

**Expected Columns:**
```
column              | type
--------------------|----------
id                  | STRING
strategy_name       | STRING
description         | STRING
direction           | STRING
enabled             | BOOLEAN
strategy_json       | STRING
author              | STRING
category            | STRING
tags                | STRING
template_id         | STRING
created_at          | TIMESTAMP
updated_at          | TIMESTAMP
last_activated_at   | TIMESTAMP
```

---

## 🧪 Test Suite

### TEST 1: Backend Initialization
**Purpose:** Verify backend connects to QuestDB and initializes strategy storage

**Steps:**
```bash
# Start backend
cd /home/user/FX_code_AI
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload
```

**Expected Logs:**
```
INFO: Strategy storage initialized with QuestDB persistence
INFO: Executing unified server startup logic...
INFO: Uvicorn running on http://0.0.0.0:8080
```

**If Error: "Connection refused"**
- QuestDB not running → Start QuestDB first
- Wrong port → Check QuestDB PostgreSQL port (should be 8812)

**Pass Criteria:** Backend starts without errors, log shows "Strategy storage initialized with QuestDB persistence"

---

### TEST 2: Create Strategy (POST /api/strategies)
**Purpose:** Test strategy creation writes to QuestDB

**Steps:**
```bash
# 1. Create a test strategy via API
curl -X POST http://localhost:8080/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "TEST_QuestDB_Storage_v1",
    "direction": "SHORT",
    "description": "Test strategy for QuestDB persistence",
    "enabled": true,
    "s1_signal": {"conditions": []},
    "z1_entry": {
      "conditions": [],
      "leverage": 3,
      "positionSize": {"type": "percentage", "value": 10}
    },
    "o1_cancel": {
      "timeoutSeconds": 60,
      "conditions": []
    },
    "ze1_close": {"conditions": []},
    "emergency_exit": {
      "conditions": [],
      "cooldownMinutes": 30,
      "actions": {
        "cancelPending": true,
        "closePosition": true,
        "logEvent": true
      }
    }
  }'
```

**Expected Response:**
```json
{
  "type": "response",
  "data": {
    "strategy": {
      "id": "UUID-HERE",
      "strategy_name": "TEST_QuestDB_Storage_v1",
      "created_at": "2025-11-04T..."
    }
  }
}
```

**Verification in QuestDB:**
```sql
-- Open http://127.0.0.1:9000
-- Run:
SELECT id, strategy_name, direction, enabled, created_at
FROM strategies
WHERE strategy_name = 'TEST_QuestDB_Storage_v1';
```

**Expected:**
- 1 row returned
- id: UUID (e.g., "a1b2c3...")
- strategy_name: "TEST_QuestDB_Storage_v1"
- direction: "SHORT"
- enabled: true
- created_at: timestamp

**Pass Criteria:**
- ✅ API returns 200 OK with UUID
- ✅ Strategy visible in QuestDB
- ✅ strategy_json contains full config

---

### TEST 3: List Strategies (GET /api/strategies)
**Purpose:** Test listing strategies from QuestDB

**Steps:**
```bash
curl http://localhost:8080/api/strategies
```

**Expected Response:**
```json
{
  "type": "response",
  "data": {
    "strategies": [
      {
        "id": "UUID",
        "strategy_name": "TEST_QuestDB_Storage_v1",
        "direction": "SHORT",
        "enabled": true,
        "created_at": "2025-11-04T...",
        "updated_at": "2025-11-04T...",
        "last_activated_at": null
      }
    ]
  }
}
```

**Pass Criteria:** Returns array with at least 1 strategy (the one created in TEST 2)

---

### TEST 4: Read Strategy (GET /api/strategies/{id})
**Purpose:** Test reading full strategy config from QuestDB

**Steps:**
```bash
# Get UUID from TEST 2 response, then:
STRATEGY_ID="paste-uuid-here"
curl http://localhost:8080/api/strategies/$STRATEGY_ID
```

**Expected Response:**
```json
{
  "type": "response",
  "data": {
    "strategy": {
      "id": "UUID",
      "strategy_name": "TEST_QuestDB_Storage_v1",
      "direction": "SHORT",
      "enabled": true,
      "s1_signal": {"conditions": []},
      "z1_entry": {
        "leverage": 3,
        "positionSize": {"type": "percentage", "value": 10},
        ...
      },
      ...
      "created_at": "2025-11-04T...",
      "updated_at": "2025-11-04T..."
    }
  }
}
```

**Verification:**
- ✅ All 5 sections present (s1_signal, z1_entry, o1_cancel, ze1_close, emergency_exit)
- ✅ leverage: 3 (from TEST 2 input)
- ✅ positionSize matches

**Pass Criteria:** Full strategy config returned, all fields present

---

### TEST 5: Update Strategy (PUT /api/strategies/{id})
**Purpose:** Test updating strategy in QuestDB

**Steps:**
```bash
# Update the test strategy
STRATEGY_ID="paste-uuid-here"
curl -X PUT http://localhost:8080/api/strategies/$STRATEGY_ID \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "TEST_QuestDB_Storage_v1_UPDATED",
    "direction": "SHORT",
    "description": "UPDATED description",
    "enabled": false,
    "s1_signal": {"conditions": []},
    "z1_entry": {
      "conditions": [],
      "leverage": 5,
      "positionSize": {"type": "percentage", "value": 20}
    },
    "o1_cancel": {"timeoutSeconds": 60, "conditions": []},
    "ze1_close": {"conditions": []},
    "emergency_exit": {
      "conditions": [],
      "cooldownMinutes": 30,
      "actions": {"cancelPending": true, "closePosition": true, "logEvent": true}
    }
  }'
```

**Expected Response:**
```json
{
  "type": "response",
  "data": {
    "strategy": {
      "id": "SAME_UUID",
      "strategy_name": "TEST_QuestDB_Storage_v1_UPDATED",
      "updated_at": "2025-11-04T... (NEWER timestamp)"
    }
  }
}
```

**Verification in QuestDB:**
```sql
SELECT strategy_name, enabled, strategy_json
FROM strategies
WHERE id = 'PASTE_UUID_HERE';
```

**Expected:**
- strategy_name: "TEST_QuestDB_Storage_v1_UPDATED"
- enabled: false (changed from true)
- strategy_json contains leverage=5 (changed from 3)
- updated_at > created_at

**Pass Criteria:**
- ✅ API returns updated strategy
- ✅ Changes persisted in QuestDB
- ✅ updated_at timestamp changed

---

### TEST 6: Delete Strategy (DELETE /api/strategies/{id})
**Purpose:** Test deleting strategy from QuestDB

**Steps:**
```bash
# Delete the test strategy
STRATEGY_ID="paste-uuid-here"
curl -X DELETE http://localhost:8080/api/strategies/$STRATEGY_ID
```

**Expected Response:**
```json
{
  "type": "response",
  "data": {
    "message": "Strategy deleted successfully",
    "strategy_name": "TEST_QuestDB_Storage_v1_UPDATED"
  }
}
```

**Verification in QuestDB:**
```sql
SELECT COUNT(*) as count
FROM strategies
WHERE id = 'PASTE_UUID_HERE';
```

**Expected:** count = 0 (strategy deleted)

**Pass Criteria:**
- ✅ API returns success message
- ✅ Strategy no longer in database
- ✅ Subsequent GET returns 404

---

### TEST 7: Error Handling - Duplicate Strategy Name
**Purpose:** Test unique constraint on strategy_name

**Steps:**
```bash
# 1. Create first strategy
curl -X POST http://localhost:8080/api/strategies \
  -H "Content-Type: application/json" \
  -d '{"strategy_name": "DUPLICATE_TEST", "s1_signal": {"conditions": []}, ...}'

# 2. Try to create second strategy with same name
curl -X POST http://localhost:8080/api/strategies \
  -H "Content-Type: application/json" \
  -d '{"strategy_name": "DUPLICATE_TEST", "s1_signal": {"conditions": []}, ...}'
```

**Expected Response (second call):**
```json
{
  "type": "error",
  "error_code": "storage_error",
  "error_message": "Strategy with name 'DUPLICATE_TEST' already exists"
}
```

**Pass Criteria:** Second creation fails with clear error message

---

### TEST 8: Leverage Mapping Integration Test
**Purpose:** Verify leverage from UI reaches database correctly (Bug #1 fix verification)

**Steps:**
```bash
# Create strategy with leverage=3 in z1_entry
curl -X POST http://localhost:8080/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "LEVERAGE_MAPPING_TEST",
    "z1_entry": {"leverage": 3, "positionSize": {"type": "percentage", "value": 10}},
    ...
  }'

# Get the created strategy
curl http://localhost:8080/api/strategies | jq '.data.strategies[] | select(.strategy_name=="LEVERAGE_MAPPING_TEST")'
```

**Verification in QuestDB:**
```sql
SELECT
    strategy_name,
    strategy_json::json->>'z1_entry'::json->>'leverage' as z1_leverage,
    strategy_json::json->>'global_limits'::json->>'max_leverage' as gl_leverage
FROM strategies
WHERE strategy_name = 'LEVERAGE_MAPPING_TEST';
```

**Expected:**
- z1_leverage: "3"
- gl_leverage: "3" ← CRITICAL: This must be set (from unified_server.py mapping)

**Pass Criteria:**
- ✅ Both z1_entry.leverage AND global_limits.max_leverage are 3
- ✅ Leverage mapping from Bug #1 fix works correctly

---

### TEST 9: Frontend Integration Test
**Purpose:** Test full workflow from UI to database

**Prerequisites:** Frontend running on http://localhost:3000

**Steps:**
1. Navigate to http://localhost:3000/strategy-builder
2. Click "Create New Strategy"
3. Fill in:
   - Name: "UI_TO_DB_TEST"
   - Direction: SHORT
   - S1: Add at least 1 condition
   - Z1: Set leverage = 3x, position size = 10%
   - O1: Timeout 60s
   - ZE1: Add at least 1 condition
   - E1: Cooldown 30 min
4. Click "Save Strategy"
5. Wait for success message
6. Reload page
7. Verify strategy appears in list

**Verification in QuestDB:**
```sql
SELECT id, strategy_name, direction, enabled
FROM strategies
WHERE strategy_name = 'UI_TO_DB_TEST';
```

**Expected:**
- 1 row with matching name
- direction: "SHORT"
- enabled: true

**Pass Criteria:**
- ✅ Strategy saves without errors
- ✅ Strategy appears in frontend list after reload
- ✅ Strategy visible in QuestDB

---

### TEST 10: Connection Pool Lifecycle
**Purpose:** Test connection pool initialization and cleanup

**Steps:**
```bash
# 1. Start backend (watch logs)
python -m uvicorn src.api.unified_server:create_unified_app --factory --port 8080

# Expected logs:
# "Strategy storage initialized with QuestDB persistence"

# 2. Make some API calls
curl http://localhost:8080/api/strategies

# 3. Stop backend (Ctrl+C)

# Expected logs:
# "Strategy storage connection pool closed successfully"
# "Unified server shutdown complete."
```

**Pass Criteria:**
- ✅ No connection errors during startup
- ✅ API calls work correctly
- ✅ Clean shutdown with pool closure

---

## 📊 Test Results Template

```markdown
## Strategy Storage QuestDB Testing Results
**Date:** [YYYY-MM-DD]
**Tester:** [Name]
**Environment:** [Local/Staging/Production]

### Results Summary

| Test | Description | Status | Notes |
|------|-------------|--------|-------|
| TEST 1 | Backend Initialization | PASS/FAIL | |
| TEST 2 | Create Strategy | PASS/FAIL | |
| TEST 3 | List Strategies | PASS/FAIL | |
| TEST 4 | Read Strategy | PASS/FAIL | |
| TEST 5 | Update Strategy | PASS/FAIL | |
| TEST 6 | Delete Strategy | PASS/FAIL | |
| TEST 7 | Error Handling | PASS/FAIL | |
| TEST 8 | Leverage Mapping | PASS/FAIL | |
| TEST 9 | Frontend Integration | PASS/FAIL | |
| TEST 10 | Connection Pool | PASS/FAIL | |

**Total:** __ / 10 passed

### Critical Tests (Must Pass):
- [ ] TEST 1: Backend Initialization
- [ ] TEST 2: Create Strategy
- [ ] TEST 4: Read Strategy
- [ ] TEST 8: Leverage Mapping

### Issues Found:
1. [Description]
   - Severity: CRITICAL/HIGH/MEDIUM/LOW
   - Reproduction steps: ...
   - Expected: ...
   - Actual: ...
```

---

## 🚨 Common Issues and Solutions

### Issue 1: "Connection refused" error
**Symptom:** Backend fails to start with "Connection refused" error

**Solution:**
```bash
# Check if QuestDB is running
curl http://127.0.0.1:9000 || echo "QuestDB not running"

# Start QuestDB
cd database/questdb
# Follow install_questdb.py output to start QuestDB
```

### Issue 2: "Table 'strategies' does not exist"
**Symptom:** API returns "relation 'strategies' does not exist"

**Solution:**
```sql
-- Run migration 012 in QuestDB Web UI
-- Copy contents of: database/questdb/migrations/012_create_strategies_table.sql
-- Paste and execute in http://127.0.0.1:9000
```

### Issue 3: Strategies not appearing after migration
**Symptom:** Old strategies from config/strategies/*.json not visible

**Expected Behavior:** This is correct - no migration of old files.

**Solution:** Recreate strategies via UI/API (they will save to QuestDB).

### Issue 4: "Strategy with name 'X' already exists"
**Symptom:** Can't create strategy with existing name

**Solution:** This is correct behavior (unique constraint). Choose different name or delete old strategy.

---

## 🎯 Success Criteria

**Minimum Criteria (Must Pass to Proceed):**
- ✅ TEST 1: Backend initializes without errors
- ✅ TEST 2: Can create strategies
- ✅ TEST 4: Can read strategies
- ✅ TEST 8: Leverage mapping works

**Recommended Criteria (Should Pass):**
- ✅ All 10 tests pass
- ✅ No connection errors
- ✅ Clean shutdown

**Production Ready:**
- ✅ All tests pass
- ✅ Frontend integration works
- ✅ Error handling correct
- ✅ Connection pool stable

---

## 📝 Next Steps After Testing

### If All Tests PASS:
1. ✅ Mark strategy persistence migration as COMPLETE
2. ✅ Remove old file-based StrategyStorage code (optional cleanup)
3. ✅ Update documentation
4. ✅ Consider deployment to staging

### If Tests FAIL:
1. ❌ Document failure in test results
2. ❌ Create bug report with reproduction steps
3. ❌ Fix bugs before proceeding
4. ❌ Re-run failed tests
5. ❌ DO NOT deploy until all critical tests pass

---

## 🔗 Related Documentation

- **Implementation:** `src/domain/services/strategy_storage_questdb.py`
- **API Integration:** `src/api/unified_server.py`
- **Migration:** `database/questdb/migrations/012_create_strategies_table.sql`
- **Old Implementation:** `src/domain/services/strategy_storage.py` (file-based, deprecated)
- **TIER 1 Testing:** `docs/testing/TIER_1_VERIFICATION_PLAN.md`

---

**Testing Plan Prepared By:** Claude Code System
**Date:** 2025-11-04
**Version:** 1.0
**Estimated Testing Time:** 1-2 hours
