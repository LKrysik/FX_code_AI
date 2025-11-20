# Autonomous Fix Plan - Critical Bug Resolution

**Date**: 2025-11-20
**Status**: IN PROGRESS
**Approach**: Autonomous implementation with comprehensive analysis

---

## Executive Summary

**Identified Issues**: 7 critical bugs requiring immediate attention
**P0 Fixes Completed**: 2/5 (MEXCRestFallback import, /api/strategies auth)
**Estimated Time**: 2-3 hours for all P0 fixes
**Testing Strategy**: Individual fix verification + full E2E suite

---

## Issue Inventory

### P0 - CRITICAL (System Blocking) 🔴

#### ✅ P0-1: Import Case-Sensitivity Bug (COMPLETED)
**File**: [src/api/unified_server.py:1817,1821](../src/api/unified_server.py#L1817)
**Error**: `cannot import name 'MEXCRestFallback'`
**Status**: ✅ Fixed - awaiting backend restart verification
**Impact**: 100% failure rate on `/api/exchange/symbols`
**Fix Applied**: Changed `MEXCRestFallback` → `MexcRestFallback`

#### ✅ P0-2: Authentication Requirement Bug (COMPLETED)
**File**: [src/api/unified_server.py:886](../src/api/unified_server.py#L886)
**Error**: 401 Unauthorized on `/api/strategies`
**Status**: ✅ Fixed - awaiting backend restart verification
**Impact**: 100% failure rate on strategy loading
**Fix Applied**: Removed `current_user` dependency

#### ⏳ P0-3: Missing DateTime Import
**File**: [src/api/indicators_routes.py:2619](../src/api/indicators_routes.py#L2619)
**Error**: `NameError: name 'datetime' is not defined`
**Impact**: 500 error on `/api/indicators/current`
**Blocking**: Indicator data loading in dashboard
**Dependencies**: None - isolated fix
**Testing**: curl test + manual indicator fetch

#### ⏳ P0-4: Session Lifecycle 404 Error
**File**: Multiple files (session management)
**Error**: `{"error_code":"session_not_found","error_message":"Session exec_20251120_210752_f0e515f2 not found"}`
**Impact**: Session stop fails, no error logging
**Blocking**: Clean session shutdown
**Dependencies**: Requires architecture analysis
**Testing**: Start/stop session flow

#### ⏳ P0-5: HTML Validation Error
**File**: [frontend/src/components/dashboard/SessionConfigDialog.tsx](../frontend/src/components/dashboard/SessionConfigDialog.tsx)
**Error**: "In HTML, <h5> cannot be a child of <h2>. This will cause a hydration error."
**Impact**: Hydration errors, poor accessibility
**Blocking**: Frontend rendering stability
**Dependencies**: None - isolated fix
**Testing**: Frontend build + validation

### P1 - HIGH (Poor UX) 🟠

#### P1-1: No Error Recovery UI
**File**: [frontend/src/app/dashboard/page.tsx:177-224](../frontend/src/app/dashboard/page.tsx#L177)
**Issue**: Infinite "Loading dashboard data..." on fetch failure
**Impact**: User cannot retry failed operations
**Solution**: Add timeout + Retry button
**Dependencies**: Sprint 17 goals, fetchWithRetry integration
**Testing**: Kill backend, verify timeout and retry

#### P1-2: Logging Architecture Inconsistency
**Files**: Multiple (event_bus.jsonl, unified_server logs)
**Issue**:
- DEBUG level in production files
- Missing error logs for user-facing failures
- Duplicate logging in multiple locations
**Impact**: Difficult debugging, log pollution
**Solution**: Standardize on INFO level, add missing error logs
**Dependencies**: Requires audit of all log statements
**Testing**: Manual log review after fixes

### P2 - MEDIUM (Code Quality) 🟡

#### P2-1: Duplicate Symbols Endpoints
**Files**: [src/api/unified_server.py:1741,1764](../src/api/unified_server.py#L1741)
**Issue**: Two endpoints read same config file (DRY violation)
**Solution**: Extract `get_configured_symbols()` shared function
**Dependencies**: None
**Testing**: curl both endpoints

#### P2-2: Silent Fallback Error Masking
**File**: [src/api/unified_server.py:1800-1804](../src/api/unified_server.py#L1800)
**Issue**: Config errors hidden by silent fallbacks
**Solution**: Add warning logs for all fallbacks
**Dependencies**: None
**Testing**: Remove config.json, verify warning logged

#### P2-3: No Frontend Error Logging
**File**: [frontend/src/components/dashboard/SessionConfigDialog.tsx:230-239](../frontend/src/components/dashboard/SessionConfigDialog.tsx#L230)
**Issue**: Catch blocks don't log errors (only show to user)
**Solution**: Add console.error() with structured data
**Dependencies**: None
**Testing**: Trigger error, verify console log

---

## Dependency Mapping

```
P0-3 (datetime import) ← No dependencies (safe to fix first)
    ↓
P0-4 (session lifecycle) ← Depends on architecture analysis
    ↓
P0-5 (HTML validation) ← No dependencies (safe to fix anytime)
    ↓
P1-1 (error recovery UI) ← Depends on P0 fixes working
    ↓
P1-2 (logging) ← Depends on understanding error patterns from P0 fixes
    ↓
P2-* (code quality) ← Can be done independently after P0/P1
```

---

## Architecture Impact Analysis

### Fix P0-3: Missing datetime Import

**Files Affected**:
- `src/api/indicators_routes.py` (direct)

**Impact on Other Modules**:
- ✅ NO impact - purely additive import
- ✅ NO breaking changes
- ✅ NO dependency changes

**Architecture Principles**:
- Follows existing import patterns
- No architectural changes needed

**Rollback Plan**: Remove import if issues arise (unlikely)

### Fix P0-4: Session Lifecycle

**Files Potentially Affected**:
- `src/api/unified_server.py` (session endpoints)
- `src/application/controllers/execution_controller.py` (state machine)
- `src/domain/services/session_manager.py` (if exists)
- Database tables: `data_collection_sessions`, `backtest_sessions`

**Impact on Other Modules**:
- ⚠️ HIGH impact - session management is core functionality
- ⚠️ Requires careful state machine analysis
- ⚠️ May affect active sessions

**Architecture Principles**:
- Must maintain state machine integrity (IDLE → STARTING → RUNNING → STOPPING → STOPPED)
- Must preserve session data in database
- Must handle concurrent stop requests

**Rollback Plan**: Git checkpoint before changes

### Fix P0-5: HTML Validation

**Files Affected**:
- `frontend/src/components/dashboard/SessionConfigDialog.tsx` (direct)

**Impact on Other Modules**:
- ✅ NO impact - UI-only change
- ✅ NO prop changes
- ✅ NO state changes

**Architecture Principles**:
- Must maintain MUI component hierarchy rules
- Must preserve accessibility

**Rollback Plan**: Revert component structure

---

## Testing Strategy

### Individual Fix Testing

**P0-3 (datetime import)**:
```bash
# Step 1: Verify syntax
python -m py_compile src/api/indicators_routes.py

# Step 2: Start backend
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload

# Step 3: Test endpoint
curl "http://localhost:8080/api/indicators/current?session_id=test"

# Expected: Valid JSON response (not 500 error)
```

**P0-4 (session lifecycle)**:
```bash
# Step 1: Start session
curl -X POST http://localhost:8080/api/sessions/start -H "Content-Type: application/json" -d '{"mode":"paper","symbols":["BTC_USDT"]}'

# Step 2: Get session_id from response

# Step 3: Stop session
curl -X POST http://localhost:8080/api/sessions/stop -H "Content-Type: application/json" -d '{"session_id":"SESSION_ID"}'

# Expected: 200 OK (not 404)
```

**P0-5 (HTML validation)**:
```bash
# Step 1: Build frontend
cd frontend && npm run build

# Expected: No validation warnings

# Step 2: TypeScript check
npx tsc --noEmit

# Expected: No errors
```

### Full E2E Testing

After all P0 fixes:
```bash
# Run complete test suite
python run_tests.py

# Expected: All tests passing (224 tests)
```

### Git Checkpoint Strategy

```bash
# Before each P0 fix
git add .
git commit -m "checkpoint: before P0-X fix"

# After each P0 fix (if successful)
git add .
git commit -m "fix: P0-X description

- Detailed changes
- Testing results
- Impact analysis

🤖 Generated with Claude Code"
```

---

## Implementation Order

### Phase 1: Isolated Fixes (No Dependencies) ✅

1. ✅ **P0-1**: MEXCRestFallback import (COMPLETED)
2. ✅ **P0-2**: /api/strategies auth (COMPLETED)
3. ⏳ **P0-3**: datetime import (NEXT)
4. ⏳ **P0-5**: HTML validation (AFTER P0-3)

### Phase 2: Architecture-Dependent Fixes ⏳

5. ⏳ **P0-4**: Session lifecycle (REQUIRES ANALYSIS)

### Phase 3: Backend Restart & Verification ⏳

6. ⏳ Restart backend server
7. ⏳ Verify P0-1, P0-2, P0-3 fixes
8. ⏳ Test dashboard data loading

### Phase 4: UX Improvements (P1) 📋

9. 📋 **P1-1**: Error recovery UI
10. 📋 **P1-2**: Logging standardization

### Phase 5: Code Quality (P2) 📋

11. 📋 **P2-1**: Extract duplicate code
12. 📋 **P2-2**: Add fallback logging
13. 📋 **P2-3**: Frontend error logging

---

## Risk Assessment

### High Risk Changes
- **P0-4** (Session lifecycle): Affects core state machine
  - Mitigation: Comprehensive architecture analysis first
  - Mitigation: Git checkpoint before changes
  - Mitigation: Test with all session types (paper, backtest, live)

### Medium Risk Changes
- **P1-2** (Logging architecture): Touches many files
  - Mitigation: Change one log level at a time
  - Mitigation: Verify no performance impact

### Low Risk Changes
- **P0-3** (datetime import): Isolated, additive
- **P0-5** (HTML validation): UI-only
- **P2-1, P2-2, P2-3** (Code quality): Non-breaking

---

## Success Criteria

### P0 Fixes Complete When:
- ✅ All 5 P0 bugs fixed
- ✅ Backend starts without errors
- ✅ All API endpoints return 200 OK
- ✅ Dashboard loads successfully
- ✅ Frontend builds without warnings
- ✅ E2E tests pass (224/224)

### P1 Fixes Complete When:
- ✅ Retry buttons functional
- ✅ Loading timeout implemented (10s)
- ✅ All logs use consistent level (INFO)
- ✅ User-facing errors logged to console

### P2 Fixes Complete When:
- ✅ No code duplication in symbols endpoints
- ✅ All fallbacks log warnings
- ✅ Frontend errors logged with structured data

---

## Timeline Estimation

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1 | P0-3, P0-5 | 30 min |
| Phase 2 | P0-4 analysis + fix | 60 min |
| Phase 3 | Testing & verification | 30 min |
| **Total P0** | **All critical fixes** | **2 hours** |
| Phase 4 | P1 fixes | 60 min |
| Phase 5 | P2 fixes | 45 min |
| **Total** | **All fixes** | **3h 45min** |

---

## Current Status

**Phase**: 1 - Isolated Fixes
**Current Task**: P0-3 (datetime import)
**Completed**: 2/7 P0+P1 fixes (29%)
**Next Steps**:
1. Fix datetime import
2. Verify with syntax check
3. Fix HTML validation
4. Analyze session lifecycle architecture

**Last Update**: 2025-11-20 21:30

---

## Related Documentation

- **Bug Analysis**: [CRITICAL_API_BUGS_ANALYSIS.md](CRITICAL_API_BUGS_ANALYSIS.md)
- **Dashboard Analysis**: [LOADING_DASHBOARD_DATA_ANALYSIS.md](LOADING_DASHBOARD_DATA_ANALYSIS.md)
- **Sprint Plan**: [sprints/SPRINT_17_PLAN.md](sprints/SPRINT_17_PLAN.md)
- **Testing Guide**: [../README_TESTS.md](../README_TESTS.md)
- **Process**: [development/AUTONOMOUS_DELIVERY_PROCESS.md](development/AUTONOMOUS_DELIVERY_PROCESS.md)
