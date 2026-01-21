# BUG-008 Follow-up Items

**Created:** 2025-12-30
**Source:** Code review of BUG-008-4 and BUG-008-7
**Priority:** P2 (Non-blocking enhancements)

---

## From BUG-008-4: MEXC Pong Timeout Handling

### Security Improvements

| ID | Severity | Issue | File:Line |
|----|----------|-------|-----------|
| F-004-1 | MEDIUM | Race condition: `_do_unsubscribe()` modifies `_subscribed_symbols` WITHOUT `_subscription_lock` | mexc_websocket_adapter.py:1893,1941 |
| F-004-2 | MEDIUM | Race condition: `_close_connection()` modifies `_subscribed_symbols` WITHOUT lock | mexc_websocket_adapter.py:1993 |

### Testing Gaps

| ID | Severity | Issue | Notes |
|----|----------|-------|-------|
| F-004-3 | HIGH | No E2E test for reconnect → resubscribe → verify data flow | Manual test scenario |
| F-004-4 | HIGH | No test for race conditions (concurrent subscribe/unsubscribe/close) | Complex async testing |
| F-004-5 | MEDIUM | No test for multiple connections with different pong ages | Edge case |
| F-004-6 | LOW | No test for CancelledError handling | mexc_websocket_adapter.py:912-916 |
| F-004-7 | LOW | No test for wait_for_pong fallback for older websockets | mexc_websocket_adapter.py:877-880 |

### Reliability Improvements

| ID | Severity | Issue | File:Line |
|----|----------|-------|-----------|
| F-004-8 | HIGH | Resubscription failures silently ignored - could lose ALL subscriptions after reconnect | mexc_websocket_adapter.py:388-391 |
| F-004-9 | MEDIUM | No verification that resubscription actually succeeded - fire-and-forget | mexc_websocket_adapter.py:2105-2109 |
| F-004-10 | LOW | Cleanup order: subscriptions removed BEFORE waiting for in-flight messages | mexc_websocket_adapter.py:1991 vs 1996 |

### Performance Improvements

| ID | Severity | Issue | File:Line |
|----|----------|-------|-----------|
| F-004-11 | LOW | JSON re-serialization on every ping - consider pre-serialized constant | mexc_websocket_adapter.py:817-818,855 |
| F-004-12 | LOW | WARNING log emitted every 1s in degraded state - could flood logs | mexc_websocket_adapter.py:804-810 |

---

## From BUG-008-7: QuestDB Connection Resilience

| ID | Severity | Issue | File:Line |
|----|----------|-------|-----------|
| F-007-1 | MEDIUM | Add asyncpg.PostgresError to retry_on tuple for DB-specific errors | dashboard_cache_service.py:88 |
| F-007-2 | MEDIUM | Apply circuit breaker to helper methods `_get_session_symbols()`, `_get_latest_price()`, `_get_position_data()` | dashboard_cache_service.py:378-446 |
| F-007-3 | LOW | Remove TODO comments or create follow-up tasks | dashboard_cache_service.py:416,480 |
| F-007-4 | LOW | Extract `LIMIT 50` to configurable constant | dashboard_cache_service.py:257 |

---

## Recommended Epic

Consider creating **Epic BUG-010: WebSocket & Database Resilience Hardening** to address these items in a future sprint.

### Suggested Stories:

1. **BUG-010-1: MEXC Subscription Lock Safety** (F-004-1, F-004-2)
   - Add proper locking to subscription modifications
   - Effort: S

2. **BUG-010-2: Resubscription Verification** (F-004-8, F-004-9)
   - Verify subscriptions succeed after reconnect
   - Add retry logic for failed resubscriptions
   - Effort: M

3. **BUG-010-3: Circuit Breaker Coverage Expansion** (F-007-1, F-007-2)
   - Apply circuit breaker to all DB helper methods
   - Add PostgresError to retry conditions
   - Effort: S

4. **BUG-010-4: E2E Reconnection Test Suite** (F-004-3, F-004-4)
   - Integration tests for full reconnect flow
   - Effort: M

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | Amelia (Dev) | Created from BUG-008-4 and BUG-008-7 code review |
