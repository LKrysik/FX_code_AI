# CSRF Token Implementation - Frontend

## Overview

CSRF (Cross-Site Request Forgery) protection has been fully implemented in the frontend to work with the backend CSRF validation middleware.

## Architecture

### Components

1. **csrfService** (`src/services/csrfService.ts`)
   - Singleton service managing CSRF token lifecycle
   - Fetches tokens from `GET /csrf-token` endpoint
   - Stores tokens in memory (not localStorage for security)
   - Automatically refreshes expired tokens
   - Thread-safe with request deduplication

2. **CsrfInitializer** (`src/components/common/CsrfInitializer.tsx`)
   - React component that initializes CSRF service on app startup
   - Non-blocking initialization (app continues even if initial fetch fails)
   - Added to root layout

3. **Axios Interceptors** (`src/services/api.ts`)
   - Request interceptor: Automatically adds `X-CSRF-Token` header to POST/PUT/PATCH/DELETE requests
   - Response interceptor: Handles 403 csrf_expired/csrf_invalid errors with automatic retry

## Implementation Details

### 1. CSRF Token Fetching

```typescript
// Automatic on app initialization
await csrfService.initialize();

// Get token (fetches if missing/expired)
const token = await csrfService.getToken();

// Force refresh
await csrfService.refreshToken();

// Clear token (on logout)
csrfService.clearToken();
```

### 2. Automatic Header Injection

All state-changing requests (POST/PUT/PATCH/DELETE) automatically include the `X-CSRF-Token` header:

```typescript
// axios.interceptors.request
if (['post', 'put', 'patch', 'delete'].includes(method)) {
  const token = await csrfService.getToken();
  request.headers['X-CSRF-Token'] = token;
}
```

### 3. Token Refresh on Expiry

When backend returns 403 with `csrf_expired` or `csrf_invalid`:

```typescript
// axios.interceptors.response
if (errorCode === 'csrf_expired' || errorCode === 'csrf_invalid') {
  await csrfService.refreshToken();
  return axios(originalRequest); // Retry with new token
}
```

### 4. Integration with Authentication

CSRF tokens are refreshed automatically:
- After successful login
- On logout (token is cleared)

## Files Modified

### New Files
1. `frontend/src/services/csrfService.ts` - CSRF token service
2. `frontend/src/components/common/CsrfInitializer.tsx` - Initialization component
3. `frontend/CSRF_IMPLEMENTATION.md` - This documentation

### Modified Files
1. `frontend/src/services/api.ts`
   - Added CSRF import
   - Added request interceptor for token injection
   - Updated response interceptor for token refresh
   - Added token refresh after login
   - Added token clear on logout

2. `frontend/src/services/TradingAPI.ts`
   - Added CSRF import
   - Added `getHeadersWithCsrf()` helper method
   - Updated `closePosition()` to use CSRF headers
   - Updated `cancelOrder()` to use CSRF headers

3. `frontend/src/services/authService.ts`
   - Added CSRF import
   - Added token refresh after login
   - Added token clear on logout
   - Updated `apiCall()` to include CSRF token for state-changing requests

4. `frontend/src/stores/authStore.ts`
   - Added CSRF import
   - Added token refresh after login
   - Added token clear on logout

5. `frontend/src/app/layout.tsx`
   - Added CsrfInitializer component

## Testing

### Manual Testing

1. **Start backend and frontend**:
   ```bash
   # Backend (port 8080)
   python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload

   # Frontend (port 3000)
   cd frontend && npm run dev
   ```

2. **Open browser DevTools** → Network tab

3. **Login to application**
   - Check that after login, a request to `/csrf-token` is made
   - Verify response contains `{"status":"success","data":{"token":"...","expires_at":...}}`

4. **Perform state-changing operation** (e.g., create strategy, start session)
   - Check request headers include `X-CSRF-Token: <token>`
   - Verify request succeeds (200 OK)

5. **Wait for token expiry** (15 minutes)
   - Perform another state-changing operation
   - Verify 403 response with `error_code: "csrf_expired"`
   - Verify automatic token refresh
   - Verify request retry with new token

### Automated Testing

The existing E2E test suite (`tests_e2e/`) already includes CSRF token handling via `conftest.py`:

```python
# tests_e2e/conftest.py automatically includes CSRF tokens
csrf_response = client.get("/csrf-token")
csrf_token = csrf_data.get("data", {}).get("token")
kwargs['headers']['X-CSRF-Token'] = csrf_token
```

Run tests:
```bash
python run_tests.py --api
```

## Security Considerations

1. **Token Storage**: Tokens stored in memory only (not localStorage/sessionStorage)
   - Prevents XSS attacks from stealing tokens
   - Tokens lost on page refresh (automatically re-fetched)

2. **Token Expiry**: 15-minute expiry enforced by backend
   - Reduces window for token theft
   - Automatic refresh on expiry

3. **HTTPS Requirement**: CSRF protection works best with HTTPS
   - Prevents MITM attacks from intercepting tokens
   - Production deployment should enforce HTTPS

4. **SameSite Cookies**: Backend uses SameSite=Lax for session cookies
   - Additional CSRF protection layer
   - Complements CSRF token validation

## Future Enhancements

1. **Redis-backed Token Storage** (backend)
   - Move from in-memory to Redis for multi-server deployments
   - Enables horizontal scaling

2. **Token Rotation**
   - Rotate tokens on each use
   - Further reduces replay attack window

3. **Rate Limiting**
   - Limit CSRF token generation per client
   - Prevents token exhaustion attacks

## Troubleshooting

### Issue: "CSRF token required" error

**Cause**: Token not fetched or expired

**Solution**:
1. Check browser console for CSRF initialization logs
2. Verify `/csrf-token` endpoint is accessible
3. Check that CsrfInitializer is mounted in layout

### Issue: Requests fail with 403 csrf_invalid

**Cause**: Token mismatch between frontend and backend

**Solution**:
1. Clear browser cache and refresh
2. Logout and login again
3. Check backend logs for token validation errors

### Issue: Token not auto-refreshing

**Cause**: Response interceptor not triggering

**Solution**:
1. Verify error response includes `error_code: "csrf_expired"`
2. Check that axios interceptor is registered
3. Ensure request retry logic is not blocked by other interceptors

## References

- Backend CSRF Implementation: `docs/security/SECURITY_FIXES_AGENT_2.md`
- Backend Endpoint: `src/api/unified_server.py` - `/csrf-token`
- Backend Middleware: `src/api/unified_server.py` - `csrf_middleware()`
- E2E Tests: `tests_e2e/api/test_misc.py` - `TestCsrfToken`
