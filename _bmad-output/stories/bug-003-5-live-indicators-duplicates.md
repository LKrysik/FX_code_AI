# Story BUG-003-5: Live Indicators Duplicates

**Status:** done
**Priority:** P1
**Epic:** BUG-003 Paper Trading Session Critical Fixes

## Problem Statement

The dashboard shows duplicate "Live Indicators: AEVO_USDT" panels.

From bug report:
> "W Live Indicators jest 'Live Indicators: AEVO_USDT' oraz 'Live Indicators: AEVO_USDT'"

## Story

**As a** trader,
**I want** each symbol to appear only once in the Live Indicators panel,
**So that** I don't see confusing duplicate data.

## Acceptance Criteria

1. **AC1:** Each symbol appears only once in watchlist/indicators
2. **AC2:** Duplicate entries are automatically filtered
3. **AC3:** No React key warnings from duplicate symbols

## Root Cause Analysis

Two issues combined:
1. **Database:** `LATEST BY` syntax was incorrect in dashboard_routes.py queries
2. **Data duplication:** Backend could return duplicate symbol entries

## Dev Agent Record

### Changes Made

**File 1:** `src/api/dashboard_routes.py`

Fixed 3 `LATEST BY` queries to use correct QuestDB syntax:
- Line 222: `LATEST ON last_updated PARTITION BY symbol`
- Line 284: `LATEST ON last_updated PARTITION BY session_id`
- Line 335: `LATEST ON last_updated PARTITION BY symbol`

**File 2:** `frontend/src/app/dashboard/page.tsx`

Added symbol deduplication in `loadDashboardData`:
```typescript
// ✅ FIX (BUG-003-5): Deduplicate symbols to prevent duplicate LiveIndicatorPanel rendering
if (data.symbols && Array.isArray(data.symbols)) {
  const seen = new Set<string>();
  data.symbols = data.symbols.filter((s: { symbol: string }) => {
    if (seen.has(s.symbol)) {
      console.log('[BUG-003-5] Removed duplicate symbol:', s.symbol);
      return false;
    }
    seen.add(s.symbol);
    return true;
  });
}
```

## Paradox Verification (Methods 55-69)

### 55. Barber Paradox - Alternative Approaches
**Alternative rejected:** Fix only backend deduplication
**Why rejected:** Frontend should be defensive against any data source
**Reconsideration:** Both layers protected is safer

### 56. Sorites Paradox - Critical Elements
**Element that destroys solution if removed:** `Set` deduplication logic
**Does it have most attention?** YES - Simple and effective
**Check:** O(n) time complexity, handles any number of duplicates

### 57. Newcomb's Paradox - Surprising Solutions
**Expected approach:** Fix database query to not return duplicates
**Surprising alternative:** Frontend deduplication as defense
**Status:** Both approaches applied for robustness

### 58. Braess Paradox - Potentially Harmful Elements
**Element that SEEMS helpful but might HURT:** Removing duplicates silently
**Analysis:** Logging removed duplicates helps debugging
**Decision:** Added console.log for visibility

### 59. Simpson's Paradox - Hidden Variables
**Hidden variable:** Order of duplicates matters (first one kept)
**Integration check:** First occurrence preserved
**Status:** VERIFIED - consistent behavior

### 60. Surprise Exam Paradox - Overconfidence
**Area of overconfidence:** Assuming database always returns duplicates
**Surprise scenario:** Database is correct, frontend has bug elsewhere
**Mitigation:** Fixed both database queries AND frontend deduplication

### 61. Bootstrap Paradox - Circular Dependencies
**Dependency chain:** API → Data Transform → State → UI
**Cycles found:** None
**Status:** Linear flow

### 62. Theseus Paradox - Core Problem Alignment
**Core problem:** "Duplicate Live Indicators panels"
**Core solution:** Deduplicate symbols from API response
**Alignment:** DIRECT

### 63. Observer Paradox - Authenticity Check
**Is this analysis genuine?** YES
**Evidence:** Bug report clearly shows duplicate AEVO_USDT entries

### 64. Goodhart's Law Check
**Goal:** No duplicate panels
**Metric:** Each symbol appears once
**Alignment:** ALIGNED

### 65. Abilene Paradox - Problem Existence
**Is there a real problem?** YES
**Evidence:** User screenshot/description

### 66. Fredkin's Paradox - Value from Rejected
**Rejected idea:** Only database fix
**Extracted value:** Frontend defense is good practice

### 67. Tolerance Paradox - Absolute Limits
**Absolute constraint:** Each symbol must appear exactly once
**Enforced by:** Set-based deduplication

### 68. Kernel Paradox - User Verification Required
**Cannot self-verify:**
1. Duplicates no longer appear after fix
2. Correct symbol data is preserved
3. No performance impact

### 69. Godel's Incompleteness - Analysis Limits
**Cannot check:**
1. All possible sources of duplication
2. Edge cases with empty symbol names
3. Race conditions in concurrent updates

## Definition of Done

- [x] Dashboard routes fixed with correct LATEST ON syntax
- [x] Frontend deduplication added
- [x] Duplicate removal logged for debugging
- [ ] No duplicate panels visible (user verification)
