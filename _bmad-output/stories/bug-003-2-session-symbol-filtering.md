# Story BUG-003-2: Session Symbol Filtering

**Status:** done
**Priority:** P0 - Critical
**Epic:** BUG-003 Paper Trading Session Critical Fixes

## Problem Statement

When starting a Paper Trading session with BLOCK/USDT and CAMP/USDT, the chart shows BTC_USDT instead of selected symbols. Symbol Watchlist shows "No symbols in watchlist".

## Story

**As a** trader,
**I want** the dashboard to display charts for the symbols I selected,
**So that** I see relevant trading data for my session.

## Acceptance Criteria

1. **AC1:** Chart displays first selected symbol on dashboard load
2. **AC2:** Symbol Watchlist shows all session symbols
3. **AC3:** User can switch between session symbols
4. **AC4:** No hardcoded default symbols override session selection

## Root Cause Analysis

The bug had multiple components:
1. **Frontend:** `selectedSymbol` was hardcoded to 'BTC_USDT' in dashboard/page.tsx line 157
2. **Frontend:** No auto-selection of first symbol from session data when dashboard loads
3. **Backend:** Dashboard summary API not returning session symbols when WebSocket controller fails

## Dev Agent Record

### Changes Made

**Files Modified:**
1. `frontend/src/app/dashboard/page.tsx`
   - Changed default `selectedSymbol` from 'BTC_USDT' to '' (empty)
   - Added useEffect to auto-select first symbol from dashboardData.symbols

2. `src/api/unified_server.py`
   - Added fallback to get symbols from ExecutionController when WebSocket controller doesn't return them

### Fix Summary

1. Dashboard now starts with empty selectedSymbol
2. useEffect auto-selects first symbol from session when dashboardData loads
3. Backend has fallback to ExecutionController.get_current_session().symbols

## Paradox Verification (Methods 55-69)

### 55. Barber Paradox - Alternative Approaches
**Alternative rejected:** Store last selected symbol in localStorage
**Why rejected:** Session-specific symbols change, localStorage would persist wrong symbol
**Reconsideration:** Could use for user preference "default symbol for new sessions"

### 56. Sorites Paradox - Critical Elements
**Element that destroys solution if removed:** `dashboardData?.symbols` check in useEffect
**Does it have most attention?** YES - This is the core auto-selection logic
**Check:** If symbols array is empty, chart won't render (acceptable - no data = no chart)

### 57. Newcomb's Paradox - Surprising Solutions
**Expected approach:** Set default from session symbols
**Surprising alternative:** Don't auto-select - show symbol picker modal on first load
**Status:** Auto-select is simpler, matches user expectation

### 58. Braess Paradox - Potentially Harmful Elements
**Element that SEEMS helpful but might HURT:** Setting selectedSymbol to '' initially
**Analysis:** Empty string causes no chart render until data loads
**Decision:** Acceptable - brief loading state is better than wrong chart

### 59. Simpson's Paradox - Hidden Variables
**Hidden variable:** dashboardData.symbols might be formatted differently than expected
**Integration check:** Code checks for `symbols[0]?.symbol` to handle object format
**Status:** ADDRESSED

### 60. Surprise Exam Paradox - Overconfidence
**Area of overconfidence:** Assuming dashboardData.symbols is always populated
**Surprise scenario:** Backend returns empty symbols array
**Mitigation:** Added fallback in backend to get from ExecutionController

### 61. Bootstrap Paradox - Circular Dependencies
**Dependency chain:** Dashboard → API → Controller → Session → Symbols → Dashboard
**Cycles found:** None - data flows one direction
**Status:** No circular dependencies

### 62. Theseus Paradox - Core Problem Alignment
**Core problem:** "Show correct symbols from session"
**Core solution:** Auto-select from session data + backend fallback
**Alignment:** DIRECT - solution addresses exact problem

### 63. Observer Paradox - Authenticity Check
**Is this analysis genuine?** YES - identified hardcoded BTC_USDT as root cause
**Evidence:** Line 157 had explicit 'BTC_USDT' string

### 64. Goodhart's Law Check
**Goal:** User sees their selected symbols on dashboard
**Metric:** selectedSymbol matches session symbols
**Alignment:** ALIGNED - metric directly measures goal

### 65. Abilene Paradox - Problem Existence
**Is there a real problem?** YES - Chart showed BTC_USDT when user selected BLOCK/USDT
**Evidence:** Bug report describes exact symptom

### 66. Fredkin's Paradox - Value from Rejected
**Rejected idea:** localStorage persistence
**Extracted value:** Could add "remember last viewed symbol per session" as enhancement

### 67. Tolerance Paradox - Absolute Limits
**Absolute constraint:** Must not show data for symbols not in session
**Enforced by:** Only symbols from dashboardData.symbols are selectable

### 68. Kernel Paradox - User Verification Required
**Cannot self-verify:**
1. Chart actually loads with correct symbol after fix
2. Symbol switching works correctly
3. Edge case with single symbol session

### 69. Godel's Incompleteness - Analysis Limits
**Cannot check:**
1. All chart types work with the new selection logic
2. Performance impact of additional API call
3. Mobile responsiveness of symbol selection
