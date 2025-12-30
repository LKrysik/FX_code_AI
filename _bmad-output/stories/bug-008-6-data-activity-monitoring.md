# Story BUG-008-6: Data Activity Monitoring Tuning

**Status:** backlog
**Priority:** P1
**Epic:** BUG-008 WebSocket Stability & Service Health

---

## Story

As a **data reliability engineer**,
I want **properly tuned data activity monitoring thresholds**,
so that **stale connections are detected appropriately without false positives**.

---

## Problem Statement

Log evidence shows connection closed due to inactivity:
```json
{
  "event_type": "mexc_adapter.no_data_activity",
  "data": {
    "connection_id": 1,
    "last_activity": 1767061299.0082047,
    "max_age_seconds": 120.0,
    "action": "closing_connection"
  }
}
```

**Questions to Answer:**
1. Is 120 seconds the right threshold for "no data activity"?
2. Should threshold vary by symbol (low-volume vs high-volume)?
3. Is closing connection the right action, or should we first try health check?
4. How do we distinguish "no data because market is quiet" vs "no data because connection is dead"?

---

## Acceptance Criteria

1. **AC1:** Data activity threshold is configurable per symbol type (high/low volume)
2. **AC2:** Before closing, send a subscription refresh to verify connection
3. **AC3:** Low-volume symbols have higher threshold (300s) vs high-volume (120s)
4. **AC4:** Activity monitoring distinguishes between "no trades" and "dead connection"
5. **AC5:** Log includes context: symbol volume category, last N messages received
6. **AC6:** False positive rate < 5% (connections closed that were actually healthy)

---

## Tasks / Subtasks

- [ ] Task 1: Analyze current activity monitoring (AC: 4)
  - [ ] Document what counts as "activity" (trades, orderbook updates, pings?)
  - [ ] Document current threshold logic
  - [ ] Collect metrics on false positive rate

- [ ] Task 2: Implement symbol-aware thresholds (AC: 1, 3)
  - [ ] Create symbol volume classification (HIGH, MEDIUM, LOW)
  - [ ] HIGH volume: 60s threshold (active symbols like BTC, ETH)
  - [ ] MEDIUM volume: 120s threshold (default)
  - [ ] LOW volume: 300s threshold (less active altcoins)
  - [ ] Make thresholds configurable in config

- [ ] Task 3: Implement pre-close health check (AC: 2)
  - [ ] Before closing for inactivity, send subscription refresh
  - [ ] Wait 10s for response
  - [ ] If response received, reset activity timer
  - [ ] If no response, then close connection

- [ ] Task 4: Enhance activity distinction (AC: 4, 5)
  - [ ] Track message types separately (trade, orderbook, heartbeat)
  - [ ] "No trades" but "orderbook updates" = connection OK
  - [ ] "No trades" and "no orderbook" = potential issue
  - [ ] Log last 5 message types when closing

- [ ] Task 5: Implement monitoring metrics (AC: 6)
  - [ ] Count connections closed for inactivity
  - [ ] Count false positives (closed then immediately reconnected with data)
  - [ ] Log metrics for analysis

---

## Dev Notes

### Activity Types

| Activity Type | Weight | Resets Timer |
|---------------|--------|--------------|
| Trade data | HIGH | Yes |
| Orderbook update | HIGH | Yes |
| Depth snapshot | HIGH | Yes |
| Ping/Pong | LOW | No (separate timer) |
| System message | MEDIUM | Yes |

### Symbol Volume Classification

```python
class SymbolVolumeCategory(Enum):
    HIGH = "high"      # Top 20 by volume
    MEDIUM = "medium"  # Top 100
    LOW = "low"        # Everything else

ACTIVITY_THRESHOLDS = {
    SymbolVolumeCategory.HIGH: 60,
    SymbolVolumeCategory.MEDIUM: 120,
    SymbolVolumeCategory.LOW: 300,
}
```

### Pre-Close Health Check Flow

```
Activity timer expires
        │
        ▼
Send subscription refresh
        │
        ├──response in 10s──► Reset timer, log INFO "false_alarm"
        │
        └──no response──► Close connection, log WARNING
```

### Enhanced Log Message

```python
logger.warning("mexc_adapter.closing_for_inactivity", {
    "connection_id": conn_id,
    "symbol": symbol,
    "volume_category": category.value,
    "threshold_seconds": threshold,
    "last_activity_age_seconds": age,
    "last_message_types": ["trade", "orderbook", "orderbook", "trade", "ping"],
    "health_check_attempted": True,
    "health_check_response": False
})
```

### Files to Modify

- `src/adapters/mexc_adapter.py` - Activity monitoring logic
- Create: `src/adapters/symbol_classifier.py` - Symbol volume classification

### Dependencies

- Should be implemented after BUG-008-4 and BUG-008-5 (foundation for connection health)

---

## Definition of Done

1. [ ] Activity thresholds vary by symbol volume
2. [ ] Pre-close health check implemented
3. [ ] Logs include context about activity types
4. [ ] False positive rate measured and < 5%
5. [ ] Configuration documented
6. [ ] Unit tests for threshold logic

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from BUG-008 Epic |
