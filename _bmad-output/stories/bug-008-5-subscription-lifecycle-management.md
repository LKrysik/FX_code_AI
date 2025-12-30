# Story BUG-008-5: Subscription Lifecycle Management

**Status:** backlog
**Priority:** P1
**Epic:** BUG-008 WebSocket Stability & Service Health

---

## Story

As a **trading system**,
I want **robust subscription lifecycle management for MEXC channels**,
so that **expired or failed subscriptions are automatically recovered without data loss**.

---

## Problem Statement

Log evidence shows subscriptions expiring without recovery:
```json
{
  "event_type": "mexc_adapter.pending_subscription_expired",
  "data": {
    "connection_id": 1,
    "symbol": "AEVO_USDT",
    "reason": "TTL_exceeded"
  }
}
```

And late/duplicate confirmations causing confusion:
```json
{
  "event_type": "mexc_adapter.depth_full_confirmation_no_pending",
  "data": {
    "channel": "rs.sub.depth.full",
    "scenario": "late_or_duplicate_depth_full_confirmation",
    "recovery_action": "starting_snapshot_tasks_if_missing"
  }
}
```

**Issues:**
1. Subscriptions expire but are not automatically resubscribed
2. Late confirmations arrive after cleanup, causing state confusion
3. No retry mechanism for failed subscriptions
4. Symbol may be silently unsubscribed without user awareness

---

## Acceptance Criteria

1. **AC1:** Expired subscriptions trigger automatic resubscription attempt
2. **AC2:** Subscription has retry logic: 3 attempts with backoff (1s, 2s, 4s)
3. **AC3:** After max retries, subscription marked as "failed" and logged at ERROR
4. **AC4:** Late confirmations handled gracefully (no error, just log info)
5. **AC5:** Subscription state machine: PENDING → ACTIVE → EXPIRED → RETRYING → FAILED
6. **AC6:** Active subscriptions list is always accurate and queryable

---

## Tasks / Subtasks

- [ ] Task 1: Implement subscription state machine (AC: 5)
  - [ ] Define SubscriptionState enum: PENDING, ACTIVE, EXPIRED, RETRYING, FAILED
  - [ ] Track state per (connection_id, symbol, channel) tuple
  - [ ] Log state transitions

- [ ] Task 2: Implement auto-resubscribe on expiration (AC: 1)
  - [ ] On TTL_exceeded, don't just log - initiate resubscription
  - [ ] Transition state: EXPIRED → RETRYING
  - [ ] Call subscription method with same parameters

- [ ] Task 3: Implement retry logic with backoff (AC: 2, 3)
  - [ ] Track retry_count per subscription
  - [ ] Delays: 1s, 2s, 4s (configurable)
  - [ ] After 3 retries, transition to FAILED
  - [ ] Log ERROR on final failure

- [ ] Task 4: Handle late confirmations (AC: 4)
  - [ ] If confirmation arrives for non-pending subscription, log INFO (not warning)
  - [ ] If subscription was expired, treat confirmation as success and activate
  - [ ] Update state machine accordingly

- [ ] Task 5: Create subscription registry (AC: 6)
  - [ ] `get_active_subscriptions()` method returns current subscriptions
  - [ ] `get_subscription_state(symbol, channel)` returns current state
  - [ ] Expose via API endpoint for debugging (optional)

---

## Dev Notes

### Subscription State Machine

```
                    ┌───────────────┐
                    │               │
        ┌──────────►│    PENDING    │
        │           │               │
        │           └───────┬───────┘
        │                   │
        │           confirmation received
        │                   │
        │                   ▼
        │           ┌───────────────┐
        │           │               │
 resubscribe        │    ACTIVE     │
        │           │               │
        │           └───────┬───────┘
        │                   │
        │              TTL expired
        │                   │
        │                   ▼
        │           ┌───────────────┐
        │           │               │
        └───────────┤   EXPIRED     │
                    │               │
                    └───────┬───────┘
                            │
                     retry initiated
                            │
                            ▼
                    ┌───────────────┐
                    │               │
        ┌──────────►│   RETRYING    │────success───►[ACTIVE]
        │           │               │
        │           └───────┬───────┘
        │                   │
    more retries       max retries
        │                   │
        │                   ▼
        │           ┌───────────────┐
        │           │               │
        └───────────┤    FAILED     │
                    │               │
                    └───────────────┘
```

### Configuration

```python
SUBSCRIPTION_TTL_SECONDS = 30  # Time to wait for confirmation
SUBSCRIPTION_MAX_RETRIES = 3
SUBSCRIPTION_RETRY_DELAYS = [1, 2, 4]  # seconds
```

### Subscription Registry Data Structure

```python
@dataclass
class SubscriptionInfo:
    symbol: str
    channel: str
    connection_id: int
    state: SubscriptionState
    created_at: datetime
    confirmed_at: Optional[datetime]
    retry_count: int = 0
    last_error: Optional[str] = None

class SubscriptionRegistry:
    _subscriptions: Dict[Tuple[str, str], SubscriptionInfo]  # (symbol, channel) -> info

    def get_active_subscriptions(self) -> List[SubscriptionInfo]
    def get_subscription_state(self, symbol: str, channel: str) -> SubscriptionState
    def transition(self, symbol: str, channel: str, new_state: SubscriptionState)
```

### Files to Modify

- `src/adapters/mexc_adapter.py` - Subscription handling
- Create: `src/adapters/subscription_registry.py` - New registry class

### Dependencies

- Should be implemented after BUG-008-4 (pong handling) since reconnection affects subscriptions

---

## Definition of Done

1. [ ] Expired subscriptions auto-retry up to 3 times
2. [ ] Subscription state machine implemented and logged
3. [ ] Late confirmations don't cause errors
4. [ ] `get_active_subscriptions()` returns accurate data
5. [ ] Unit tests for all state transitions
6. [ ] Integration test: simulate subscription timeout, verify recovery

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from BUG-008 Epic |
