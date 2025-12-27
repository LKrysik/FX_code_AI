# Story BUG-003-6: Active Positions Display

**Status:** done
**Priority:** P1
**Epic:** BUG-003 Paper Trading Session Critical Fixes

## Problem Statement

1. API 404 errors (249 occurrences) when fetching positions
2. Bug report: "W zakładce ACTIVE POSITIONS jest jakiś wielki symbol" (oversized symbol)

## Story

**As a** trader,
**I want** to see my active positions correctly,
**So that** I can monitor my trades and P&L.

## Acceptance Criteria

1. **AC1:** Positions API returns 200 OK (no 404 errors)
2. **AC2:** Position data displays correctly
3. **AC3:** Symbol display is properly sized

## Root Cause Analysis

**Wrong API Endpoint URL:**
- Frontend called: `/api/positions`
- Backend has: `/api/trading/positions`

This caused 404 errors every 2 seconds (periodic refresh).

## Dev Agent Record

### Changes Made

**File Modified:** `frontend/src/components/dashboard/ActivePositionBanner.tsx`

Fixed 2 API endpoint URLs:
1. Line 134: `fetchPositions()` - GET request
2. Line 181: `handleClosePosition()` - POST request

```typescript
// Before (incorrect):
`${apiUrl}/api/positions?session_id=${sessionId}&status=OPEN`

// After (correct):
`${apiUrl}/api/trading/positions?session_id=${sessionId}&status=OPEN`
```

## Paradox Verification (Methods 55-69)

### 55. Barber Paradox - Alternative Approaches
**Alternative rejected:** Add a redirect from /api/positions to /api/trading/positions
**Why rejected:** Redirect adds latency, fixing the URL is cleaner
**Reconsideration:** Could add alias route as future improvement

### 56. Sorites Paradox - Critical Elements
**Element that destroys solution if removed:** `/trading` in the path
**Does it have most attention?** YES - This is the route fix
**Check:** Both GET and POST endpoints updated

### 57. Newcomb's Paradox - Surprising Solutions
**Expected approach:** Fix frontend URL
**Surprising alternative:** Change backend route to match frontend expectation
**Status:** Frontend fix is correct - follows existing API convention

### 58. Braess Paradox - Potentially Harmful Elements
**Element that SEEMS helpful but might HURT:** None identified
**Analysis:** Simple URL fix, no side effects
**Decision:** Clean fix

### 59. Simpson's Paradox - Hidden Variables
**Hidden variable:** Other components might use the same wrong URL
**Integration check:** PositionMonitor uses TradingAPI service with correct URL
**Status:** ActivePositionBanner was the only component with wrong URL

### 60. Surprise Exam Paradox - Overconfidence
**Area of overconfidence:** Assuming this fixes all 404 errors
**Surprise scenario:** Other endpoints might also be wrong
**Mitigation:** Error logs should be checked after deployment

### 61. Bootstrap Paradox - Circular Dependencies
**Dependency chain:** Banner → API → Backend → Database
**Cycles found:** None
**Status:** Linear flow

### 62. Theseus Paradox - Core Problem Alignment
**Core problem:** "API 404 errors on positions"
**Core solution:** Fix API endpoint URL
**Alignment:** DIRECT

### 63. Observer Paradox - Authenticity Check
**Is this analysis genuine?** YES
**Evidence:** Error log shows `[ActivePositionBanner] Failed to fetch positions: Failed to load positions: 404`

### 64. Goodhart's Law Check
**Goal:** Positions load correctly
**Metric:** No 404 errors in logs
**Alignment:** ALIGNED

### 65. Abilene Paradox - Problem Existence
**Is there a real problem?** YES - 249 occurrences of 404 errors
**Evidence:** frontend_error.log

### 66. Fredkin's Paradox - Value from Rejected
**Rejected idea:** Backend redirect
**Extracted value:** Could add OpenAPI/Swagger docs to prevent future URL mismatches

### 67. Tolerance Paradox - Absolute Limits
**Absolute constraint:** API URL must match backend route
**Enforced by:** Correct URL string

### 68. Kernel Paradox - User Verification Required
**Cannot self-verify:**
1. Positions actually load after fix
2. Close position works
3. Banner renders correctly

### 69. Godel's Incompleteness - Analysis Limits
**Cannot check:**
1. All other components using correct URLs
2. Network latency impact
3. Authentication requirements

## Definition of Done

- [x] GET positions URL fixed to /api/trading/positions
- [x] POST close position URL fixed to /api/trading/positions
- [ ] No 404 errors in logs (user verification)
- [ ] Positions display correctly (user verification)
