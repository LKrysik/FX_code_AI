# BUG-006 Repair Plan: Trading Interface Not Displaying Session Data

**Created**: 2025-12-28
**Status**: READY FOR IMPLEMENTATION
**Priority**: CRITICAL

---

## Executive Summary

The trading interface fails to display strategies, symbols, and chart data after starting a session. Root cause analysis identified a cascade of failures originating from a missing Python import.

---

## Root Cause Analysis

### RC-1: Missing `timezone` Import (CRITICAL)
- **File**: `src/api/unified_server.py`
- **Line 14**: `from datetime import datetime, timedelta` - missing `timezone`
- **Line 3140**: Uses `datetime.now(timezone.utc).isoformat()` which fails
- **Impact**: HTTP 500 on `/api/state/snapshot` endpoint

### RC-2: State Sync Cascade Failure
- **Frontend**: `websocket.ts:558-570` calls `/api/state/snapshot`
- **Result**: 500 error causes "State sync failed: 500"
- **Impact**: Frontend stores never receive session data

### RC-3: Chart Markers API Incompatibility
- **File**: `CandlestickChart.tsx:425-434`
- **Issue**: `setMarkers` method not available on series in lightweight-charts v5
- **Impact**: Warning logged, markers not displayed

### RC-4: WebSocket Message Type Handling
- **File**: `StateOverviewTable.integration.tsx:129`
- **Issue**: "Unknown WebSocket message type: error" - error type not handled
- **Impact**: Error messages not properly propagated to UI

---

## EPIC-1: Critical Backend Fixes (IMMEDIATE)

### Story 1.1: Fix timezone Import
**Priority**: P0 - CRITICAL
**Effort**: 5 minutes
**File**: `src/api/unified_server.py`

**Change**:
```python
# Line 14 - BEFORE:
from datetime import datetime, timedelta

# Line 14 - AFTER:
from datetime import datetime, timedelta, timezone
```

**Acceptance Criteria**:
- [ ] `/api/state/snapshot` returns 200 OK
- [ ] Response includes valid ISO timestamp
- [ ] No "timezone is not defined" errors in logs

### Story 1.2: Add Error Handling to State Snapshot
**Priority**: P1 - HIGH
**Effort**: 30 minutes
**File**: `src/api/unified_server.py`

**Changes**:
1. Add try-catch around timestamp generation
2. Add fallback timestamp if timezone fails
3. Add logging for debugging

---

## EPIC-2: Frontend State Sync Improvements

### Story 2.1: Improve State Sync Error Handling
**Priority**: P1 - HIGH
**Effort**: 1 hour
**File**: `frontend/src/services/websocket.ts`

**Changes**:
1. Add better error messages for 500 errors
2. Add retry with exponential backoff (already implemented but verify)
3. Add user notification for persistent failures

### Story 2.2: Handle "error" WebSocket Message Type
**Priority**: P2 - MEDIUM
**Effort**: 30 minutes
**File**: `frontend/src/components/dashboard/StateOverviewTable.integration.tsx`

**Changes**:
1. Add case for "error" message type in switch statement
2. Display error notification to user
3. Log error details for debugging

---

## EPIC-3: Chart Markers Fix

### Story 3.1: Fix setMarkers Compatibility
**Priority**: P2 - MEDIUM
**Effort**: 2 hours
**File**: `frontend/src/components/dashboard/CandlestickChart.tsx`

**Analysis Needed**:
- Check lightweight-charts version in package.json
- Review v5 API for markers
- In v5, markers should be set via `chart.addLineSeries()` with markers property

**Potential Fixes**:
1. **Option A**: Use v4 compatible API if available
2. **Option B**: Update to v5 API: `series.attachData(data, { markers: [...] })`
3. **Option C**: Create custom marker overlay using HTML elements

---

## EPIC-4: Testing & Verification

### Story 4.1: Create Integration Tests
**Priority**: P1 - HIGH
**Effort**: 2 hours

**Tests to add**:
1. Test `/api/state/snapshot` returns 200 with valid data
2. Test WebSocket state sync flow end-to-end
3. Test session start shows strategies and symbols in UI

### Story 4.2: Manual Verification Checklist
**Priority**: P0 - CRITICAL

**Checklist**:
- [ ] Start paper trading session with 2+ strategies
- [ ] Verify strategies visible in UI
- [ ] Verify symbols visible in watchlist
- [ ] Verify chart displays with data
- [ ] Verify indicators panel shows values
- [ ] Check browser console for errors
- [ ] Check backend logs for errors

---

## Implementation Order

```
Phase 1 (IMMEDIATE - 10 min):
├── Story 1.1: Fix timezone import ← START HERE

Phase 2 (After Phase 1 - 1 hour):
├── Story 4.2: Manual verification
├── Story 1.2: Error handling improvements

Phase 3 (If issues persist - 2 hours):
├── Story 2.1: State sync improvements
├── Story 2.2: WebSocket error handling

Phase 4 (Non-blocking - 2 hours):
├── Story 3.1: Chart markers fix
├── Story 4.1: Integration tests
```

---

## Verification Paradox Checklist

### Applied Paradoxes (per user requirements):

| # | Paradox | Application | Result |
|---|---------|-------------|--------|
| 55 | Barber | Alternative: Rewrite entire state sync? | REJECTED - overkill for import fix |
| 56 | Sorites | Remove timezone import → DESTROYS all. | Correct priority |
| 57 | Newcomb | Surprising solution: timezone was the issue | Confirmed root cause |
| 58 | Braess | timezone.utc SEEMS simple but causes cascade | Noted in plan |
| 60 | Surprise Exam | What could surprise: Other files also missing import? | Checked: logger.py OK |
| 61 | Bootstrap | No circular dependencies found | OK |
| 62 | Theseus | Core problem = import. Core solution = add import | Aligned |
| 63 | Observer | Analysis genuine, not performance | Verified by code reads |
| 68 | Kernel | USER must verify: session works after fix | In checklist |

---

## Quick Fix Command (Story 1.1)

```bash
# In src/api/unified_server.py, line 14
# Change:
#   from datetime import datetime, timedelta
# To:
#   from datetime import datetime, timedelta, timezone
```

---

## Files Modified Summary

| File | Change Type | Lines |
|------|-------------|-------|
| `src/api/unified_server.py` | Import fix | 14 |
| `frontend/src/services/websocket.ts` | Error handling | TBD |
| `frontend/src/components/dashboard/CandlestickChart.tsx` | Markers API | 425-434 |
| `frontend/src/components/dashboard/StateOverviewTable.integration.tsx` | Error handling | 129 |

---

## Notes

- RC-1 is the SINGLE POINT OF FAILURE causing cascade
- Fixing RC-1 should immediately restore basic functionality
- RC-3 (markers) is independent and can be fixed separately
- All fixes are backwards compatible
