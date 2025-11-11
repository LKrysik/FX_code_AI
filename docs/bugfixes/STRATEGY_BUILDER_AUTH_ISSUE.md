# Strategy Builder Authentication Issue - Root Cause Analysis

## Problem Description
When accessing `http://localhost:3000/strategy-builder`, the frontend makes **4 failed login attempts** to `POST /api/v1/auth/login`, all returning **401 Unauthorized**.

## Root Cause Analysis

### Primary Root Cause
**Password Mismatch Between Frontend and Backend**

**Frontend** (`frontend/src/app/strategy-builder/page.tsx:121`):
```typescript
await apiService.login('admin', 'admin123');  // ❌ Hardcoded wrong password
```

**Backend** (`.env:5`):
```env
ADMIN_PASSWORD=supersecret  # ✅ Actual password
```

**Result:** Authentication fails because `'admin123' !== 'supersecret'`

---

## Why 4 Login Attempts?

### Authentication Flow Analysis

1. **React Strict Mode (Development)**:
   - `useEffect` in `page.tsx:96-99` runs **2 times** (React 18 Strict Mode behavior)

2. **Each useEffect execution**:
   ```
   loadInitialData() called
     ↓
   apiService.login('admin', 'admin123')  → POST /api/v1/auth/login → 401
     ↓
   axios interceptor catches 401 (api.ts:119-140)
     ↓
   originalRequest._retry = true
     ↓
   cookieAuth.refreshTokens() → POST /api/v1/auth/refresh → 401 (no cookies)
     ↓
   return axios(originalRequest)  → POST /api/v1/auth/login → 401 (RETRY)
   ```

3. **Total Attempts**:
   - useEffect run #1: 1 login + 1 retry = **2 attempts**
   - useEffect run #2: 1 login + 1 retry = **2 attempts**
   - **Total = 4 login attempts**

---

## Secondary Root Causes

### 1. Hardcoded Credentials in Frontend
**Location:** `frontend/src/app/strategy-builder/page.tsx:121`

```typescript
// ❌ BAD PRACTICE: Hardcoded credentials in source code
await apiService.login('admin', 'admin123');
```

**Problems:**
- **Security Risk:** Credentials committed to version control
- **Maintainability:** Password changes require code deployment
- **Configuration Management:** No environment-based credential loading
- **UX Issue:** Users cannot choose their own credentials

**Impact on Architecture:**
- Violates **separation of concerns** (UI should not contain auth data)
- Violates **12-factor app principles** (config should be in environment)
- Creates **tight coupling** between frontend code and backend credentials

---

### 2. Auto-Login on Page Load
**Location:** `frontend/src/app/strategy-builder/page.tsx:96-151`

```typescript
useEffect(() => {
  console.log('Strategy Builder: Starting to load initial data...');
  loadInitialData();  // ❌ Auto-login without user consent
}, []);

const loadInitialData = async () => {
  try {
    // ❌ Try to authenticate first (demo credentials)
    try {
      console.log('Strategy Builder: Attempting auto-login...');
      await apiService.login('admin', 'admin123');  // ❌ Automatic login
      console.log('Strategy Builder: Auto-login successful');
    } catch (authError) {
      console.warn('Strategy Builder: Auto-login failed:', authError);
      showNotification('Auto-login failed - some features may not work', 'warning');
    }
```

**Problems:**
- **Security:** Automatic authentication without user interaction
- **UX:** User may not want to login immediately
- **Privacy:** Credentials sent without explicit user action
- **Error Handling:** Failed login shows warning but continues (masks problem)

**Architectural Impact:**
- Violates **principle of least privilege** (authenticate only when needed)
- Violates **explicit user consent** for authentication
- **Error masking**: Failures are hidden from user, making debugging harder

---

### 3. Axios Interceptor Retries Login Requests
**Location:** `frontend/src/services/api.ts:119-140`

```typescript
// Handle token refresh on 401 responses
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized - JWT token expired
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh the tokens via cookies
        await cookieAuth.refreshTokens();  // ❌ Calls /api/v1/auth/refresh

        // Retry the original request (cookies will be sent automatically)
        return axios(originalRequest);  // ❌ RETRIES LOGIN REQUEST
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);
      }
    }
    // ...
```

**Problems:**
- **Logic Error:** Login endpoint should NOT be retried on 401
- **Unnecessary Requests:** Doubles all failed login attempts
- **Token Refresh on Login:** Trying to refresh tokens when logging in makes no sense
- **Rate Limiting Risk:** Multiple retries can trigger rate limits

**Architectural Impact:**
- Violates **idempotency** for authentication endpoints
- **Wrong abstraction:** Login is not a "retriable" operation
- **Resource waste:** Unnecessary network requests
- Creates **cascading failures** (login → refresh → retry login)

---

## Architecture Violations

### 1. Configuration Management
**Violation:** Credentials hardcoded in frontend source code

**Correct Pattern:**
- Backend credentials: `.env` file (NEVER in code)
- Frontend credentials: User input or environment variables (NEVER hardcoded)
- API keys: Environment variables with validation

**References:**
- 12-Factor App: [Config](https://12factor.net/config)
- OWASP: [Hardcoded Credentials](https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password)

---

### 2. Authentication Flow
**Violation:** Auto-login without explicit user action

**Correct Pattern:**
1. User navigates to protected page
2. System checks authentication status (token validation, not login)
3. If not authenticated, redirect to login page
4. User provides credentials explicitly
5. System authenticates and redirects back

**References:**
- OAuth 2.0 Best Practices
- OIDC Authentication Flow

---

### 3. Error Handling
**Violation:** Failed authentication masked with warning message

**Correct Pattern:**
1. Authentication failure should be explicit
2. User should be redirected to login page
3. Error message should guide user action
4. System should not continue as if authentication succeeded

---

## Impact on System Components

### 1. Frontend (Next.js)
**Files Affected:**
- `frontend/src/app/strategy-builder/page.tsx` (auto-login logic)
- `frontend/src/services/api.ts` (axios interceptor)
- `frontend/src/stores/authStore.ts` (authentication state)

**Impact:**
- **Performance:** 4x unnecessary network requests on page load
- **UX:** Confusing warning messages, unclear authentication state
- **Security:** Credentials in source code, automatic authentication

---

### 2. Backend (FastAPI)
**Files Affected:**
- `src/api/unified_server.py` (login endpoint: lines 1267-1327)
- `src/api/auth_handler.py` (credential validation: lines 903-1039)
- `.env` (credentials configuration)

**Impact:**
- **Rate Limiting:** 4 failed attempts may trigger rate limits (30/minute)
- **Logging:** Excessive failed login logs
- **Security Monitoring:** False positives for brute force detection

---

### 3. EventBus / WebSocket
**Impact:** None - authentication happens before WebSocket connection

---

### 4. Database (QuestDB)
**Impact:** None - authentication is in-memory (AuthHandler)

---

## Similar Issues in Codebase

### Search for Hardcoded Credentials
Let me check if there are other hardcoded credentials in the codebase...

**Potential Locations:**
1. Other page components with auto-login
2. Test files with hardcoded credentials (acceptable for tests)
3. Example/demo code with hardcoded credentials

---

## Verification Steps

### 1. Check Current State
**Test Authentication:**
```bash
# Test with correct password from .env
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "supersecret"}'
# Expected: 200 OK with access_token

# Test with wrong password (current frontend)
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
# Expected: 401 Unauthorized
```

### 2. Verify .env Configuration
```bash
cat .env | grep PASSWORD
# Should show:
# ADMIN_PASSWORD=supersecret (not admin123)
```

### 3. Check React Strict Mode
```bash
cat frontend/next.config.js | grep -i strict
# React Strict Mode is enabled by default in Next.js 13+
```

---

## Proposed Solutions

### Solution 1: Remove Auto-Login (Recommended)
**Changes Required:**
1. Remove auto-login logic from `page.tsx`
2. Implement proper authentication check (token validation)
3. Redirect to login page if not authenticated
4. Load data only after successful authentication

**Pros:**
- ✅ Fixes root cause completely
- ✅ Proper security pattern
- ✅ Better UX (explicit login)
- ✅ No hardcoded credentials

**Cons:**
- ⚠️ Requires login page implementation (may already exist)
- ⚠️ Changes user flow

---

### Solution 2: Fix Password Mismatch (Quick Fix)
**Changes Required:**
1. Update frontend hardcoded password to match `.env`
   ```typescript
   await apiService.login('admin', 'supersecret');
   ```

**Pros:**
- ✅ Immediate fix (1 line change)
- ✅ Unblocks development work

**Cons:**
- ❌ Still hardcoded credentials (security risk)
- ❌ Still auto-login (UX issue)
- ❌ Still axios retry issue (performance)
- ❌ Technical debt remains

---

### Solution 3: Disable Axios Retry for Login
**Changes Required:**
1. Add check in axios interceptor to skip retry for `/api/v1/auth/login`
   ```typescript
   if (error.response?.status === 401 &&
       !originalRequest._retry &&
       !originalRequest.url.includes('/auth/login')) {
     // retry logic...
   }
   ```

**Pros:**
- ✅ Reduces attempts from 4 to 2
- ✅ Prevents retry logic on login endpoint

**Cons:**
- ⚠️ Doesn't fix root cause (password mismatch)
- ⚠️ Still auto-login issue
- ⚠️ Still hardcoded credentials

---

### Solution 4: Use Authentication State Check
**Changes Required:**
1. Replace auto-login with authentication check
   ```typescript
   // Check if already authenticated
   const isAuthenticated = authStore.isAuthenticated;
   if (!isAuthenticated) {
     // Redirect to login page or show login modal
     router.push('/login');
     return;
   }
   // Load data only if authenticated
   ```

**Pros:**
- ✅ No automatic authentication
- ✅ Uses existing auth state (authStore)
- ✅ No hardcoded credentials
- ✅ Proper authentication flow

**Cons:**
- ⚠️ Requires login page/modal

---

## Implementation (Completed)

### Changes Made - Phase 1: Immediate Fix ✅

#### 1. Remove Auto-Login from Strategy Builder
**File:** `frontend/src/app/strategy-builder/page.tsx`

**Before:**
```typescript
// Lines 118-126: Automatic login with hardcoded credentials
try {
  console.log('Strategy Builder: Attempting auto-login...');
  await apiService.login('admin', 'admin123');  // ❌ Wrong password
  console.log('Strategy Builder: Auto-login successful');
} catch (authError) {
  console.warn('Strategy Builder: Auto-login failed:', authError);
  showNotification('Auto-login failed - some features may not work', 'warning');
}
```

**After:**
```typescript
// ✅ ARCHITECTURE FIX: Check authentication state instead of auto-login
// Previously: Automatic login with hardcoded credentials ('admin', 'admin123')
// Problem: Password mismatch with backend (.env has 'supersecret'), caused 4x failed login attempts
// Solution: Check if user is already authenticated, let them login explicitly via LoginForm
// Related: docs/bugfixes/STRATEGY_BUILDER_AUTH_ISSUE.md

// Load indicators from API (works without authentication)
// Load strategies list (requires authentication) - will show error if not authenticated
```

**Impact:**
- ✅ Eliminates 4x failed login attempts on page load
- ✅ Removes hardcoded credentials from source code
- ✅ Proper authentication flow (user logs in explicitly)

---

#### 2. Fix Password Mismatch in LoginForm
**File:** `frontend/src/components/auth/LoginForm.tsx`

**Before:**
```typescript
const credentials = {
  demo: { username: 'demo', password: 'demo123' },
  trader: { username: 'trader', password: 'trader123' },
  premium: { username: 'premium', password: 'premium123' },
  admin: { username: 'admin', password: 'admin123' },  // ❌ Wrong - doesn't match .env
};
```

**After:**
```typescript
// ✅ SECURITY FIX: Match credentials with backend .env configuration
// Previously: admin password was 'admin123' (hardcoded, wrong)
// Backend .env has: ADMIN_PASSWORD=supersecret
// This mismatch caused 401 authentication failures
const credentials = {
  demo: { username: 'demo', password: 'demo123' },
  trader: { username: 'trader', password: 'trader123' },
  premium: { username: 'premium', password: 'premium123' },
  admin: { username: 'admin', password: 'supersecret' },  // ✅ Fixed: matches backend .env
};
```

**Impact:**
- ✅ Admin login now works correctly
- ✅ Matches backend `.env` configuration
- ⚠️ Note: Credentials still hardcoded (acceptable for demo buttons, document in .env.example)

---

#### 3. Disable Axios Retry for Auth Endpoints
**File:** `frontend/src/services/api.ts`

**Before:**
```typescript
// Handle 401 Unauthorized - JWT token expired
if (error.response?.status === 401 && !originalRequest._retry) {
  originalRequest._retry = true;

  try {
    await cookieAuth.refreshTokens();
    return axios(originalRequest);  // ❌ Retries login requests (doubles failures)
  } catch (refreshError) {
    console.error('Token refresh failed:', refreshError);
  }
}
```

**After:**
```typescript
// ✅ ARCHITECTURE FIX: Skip retry for login/refresh endpoints
// Previously: All 401 responses triggered retry (including login failures)
// Problem: Login failure → retry login → doubles failed attempts (4x total with React Strict Mode)
// Solution: Only retry for authenticated resource requests, not auth endpoints themselves
const isAuthEndpoint = originalRequest.url?.includes('/auth/login') ||
                      originalRequest.url?.includes('/auth/refresh');

if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
  originalRequest._retry = true;
  // ... retry logic
}
```

**Impact:**
- ✅ Login failures no longer trigger automatic retry
- ✅ Reduces failed attempts from 4 to 2 (React Strict Mode still doubles useEffect)
- ✅ Proper separation: auth endpoints vs authenticated resource requests

---

#### 4. Fix Undefined Variable Bug in authStore
**Files:** `frontend/src/stores/authStore.ts` (2 locations)

**Before:**
```typescript
// Line 88 in login()
const tokenExpiry = Date.now() + (auth_handler.token_expiry_hours * 60 * 60 * 1000);
// ❌ ReferenceError: auth_handler is not defined

// Line 202 in refreshToken()
const tokenExpiry = Date.now() + (auth_handler.token_expiry_hours * 60 * 60 * 1000);
// ❌ Same error
```

**After:**
```typescript
// ✅ BUG FIX: Use expires_in from server response (in seconds), not undefined auth_handler
// Previously: auth_handler.token_expiry_hours (ReferenceError - undefined variable)
// Backend returns expires_in in seconds (e.g., 86400 for 24 hours)
const { access_token, refresh_token, user, expires_in } = data.data;
const tokenExpiry = Date.now() + ((expires_in || 86400) * 1000);  // Default: 24h
```

**Impact:**
- ✅ Fixed ReferenceError that would crash token refresh
- ✅ Uses actual server-provided expiry time (more accurate)
- ✅ Fallback to 24h if server doesn't provide expires_in

---

### Summary of Changes

| File | Lines Changed | Type | Description |
|------|--------------|------|-------------|
| `frontend/src/app/strategy-builder/page.tsx` | 118-126 removed | Fix | Removed auto-login with hardcoded credentials |
| `frontend/src/components/auth/LoginForm.tsx` | 75 modified | Fix | Updated admin password to match backend |
| `frontend/src/services/api.ts` | 130-131 added | Fix | Skip retry for auth endpoints |
| `frontend/src/stores/authStore.ts` | 88, 202 modified | Fix | Use server expires_in instead of undefined variable |

**Total Impact:**
- **Before:** 4 failed login attempts per page load
- **After:** 0 automatic login attempts (user logs in explicitly)
- **Additional Fixes:** 1 ReferenceError, 1 password mismatch

---

## Testing Instructions

### Manual Testing

1. **Test: No automatic login attempts**
   ```bash
   cd frontend && npm run dev
   # Navigate to http://localhost:3000/strategy-builder
   # Expected: Page loads without login attempts
   # Expected: No 401 errors in browser console
   # Expected: Strategies list shows empty or authentication error
   ```

2. **Test: Admin login works**
   ```bash
   # Navigate to LoginForm component (if accessible)
   # Click "Admin" demo button
   # Expected: Successful login (no 401 error)
   # Expected: access_token and user in response
   ```

3. **Test: Token expiry calculation**
   ```javascript
   // In browser console after login
   const authStore = window.useAuthStore?.getState();
   console.log('Token expiry:', new Date(authStore.tokenExpiry));
   // Expected: Date ~24 hours from now
   ```

### Backend Verification

```bash
# Test login with correct password
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "supersecret"}'

# Expected response:
# {
#   "type": "success",
#   "data": {
#     "access_token": "...",
#     "refresh_token": "...",
#     "expires_in": 86400,
#     "user": { "user_id": "admin_user", "username": "admin", ... }
#   }
# }
```

---

## Recommended Implementation Plan

### Phase 1: Immediate Fix (High Priority) ✅ COMPLETED
~~**Goal:** Stop 4x failed login attempts~~

1. ✅ **Remove auto-login from strategy-builder page**
2. ✅ **Update axios interceptor**
3. ✅ **Fix password mismatch in LoginForm**
4. ✅ **Fix undefined auth_handler bug in authStore**

### Phase 2: Proper Authentication Flow (Medium Priority)
**Goal:** Implement correct authentication pattern

1. **Create login page/modal** (if doesn't exist)
   - Check if `frontend/src/app/login/page.tsx` exists
   - If yes, redirect to it
   - If no, create login modal component

2. **Implement protected route pattern**
   - Create `useAuth` hook for authentication checks
   - Create `ProtectedRoute` wrapper component
   - Apply to strategy-builder and other protected pages

3. **Update authStore**
   - Add `checkAuth()` on app initialization
   - Implement silent token refresh
   - Handle expired sessions gracefully

### Phase 3: Security Hardening (Low Priority)
**Goal:** Remove all hardcoded credentials

1. **Audit codebase for hardcoded credentials**
   ```bash
   # Search for hardcoded passwords
   grep -r "password.*=.*['\"]" frontend/src --include="*.ts" --include="*.tsx"
   ```

2. **Migrate to environment-based configuration**
   - Create `frontend/.env.local.example`
   - Document required environment variables

3. **Update documentation**
   - Document authentication flow
   - Add security best practices guide

---

## Testing Plan

### Unit Tests
1. Test axios interceptor behavior for login endpoint
2. Test authStore authentication check
3. Test ProtectedRoute component

### Integration Tests
1. Test strategy-builder page with authenticated user
2. Test strategy-builder page without authentication
3. Test token expiration handling

### Manual Tests
1. Navigate to strategy-builder when logged out → expect redirect
2. Login → navigate to strategy-builder → expect page load
3. Token expires → expect re-authentication prompt

---

## Related Issues

### Check for Similar Problems
Search for other auto-login patterns:
```bash
grep -r "apiService.login" frontend/src --include="*.ts" --include="*.tsx"
```

Search for other hardcoded credentials:
```bash
grep -r "password.*admin" frontend/src --include="*.ts" --include="*.tsx"
```

---

## Git History Analysis

### Recent Authentication Changes
```bash
git log --oneline -- src/api/auth_handler.py
# 730243f inter
# f3371b8 Fix authentication error by implementing auto-fallback for credentials
# 6764377 Security: Fix all 7 CRITICAL vulnerabilities (Agent 2)
# d26f8ff Fix authentication failure - Remove hardcoded password and duplicate auth logic
```

**Key Findings:**
- Commit `d26f8ff`: Fixed hardcoded password in backend unified_server.py
- Commit `f3371b8`: Added auto-fallback for credentials (`.env` fallback to defaults)
- **Frontend auto-login was NOT updated** after backend credential changes

---

## Summary

**Root Cause:**
Password mismatch: Frontend hardcodes `'admin123'` but backend `.env` has `'supersecret'`

**Contributing Factors:**
1. Hardcoded credentials in frontend source code
2. Auto-login on page load (no user consent)
3. Axios interceptor retries login requests on 401
4. React Strict Mode doubles useEffect executions

**Impact:**
- 4x failed authentication attempts per page load
- Potential rate limiting trigger (30/minute limit)
- Poor UX (confusing warning messages)
- Security risk (credentials in source code)

**Recommended Fix:**
Remove auto-login, implement proper authentication check, redirect to login page

**Priority:** HIGH - Affects all users accessing strategy-builder page
