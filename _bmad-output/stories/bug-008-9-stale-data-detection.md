# Story BUG-008-9: Stale Data Detection & Handling

**Status:** backlog
**Priority:** P2
**Epic:** BUG-008 WebSocket Stability & Service Health

---

## Story

As a **data quality system**,
I want **automatic detection and handling of stale data**,
so that **users never see outdated information presented as current**.

---

## Problem Statement

Log evidence shows severe data staleness going unhandled:
```json
{
  "event_type": "streaming_indicator_engine.data_anomalies_detected",
  "data": {
    "symbol": "CAMP_USDT",
    "timestamp": 1767057945.564,
    "anomalies": ["stale_timestamp: 1767057945.564 vs 1767061296.8395183"],
    "data_sample": {"price": 0.00698, "volume": 99.0}
  }
}
```

**Analysis:**
- Data timestamp: 1767057945 (02:12:25)
- Current time: 1767061296 (03:08:16)
- **Data is 3351 seconds (55 minutes) old!**

**Issues:**
1. Stale data detected but only logged as WARNING
2. Data continues to be processed and displayed
3. No marker on data to indicate staleness
4. User has no way to know they're seeing 55-minute-old data

---

## Acceptance Criteria

1. **AC1:** Data older than 60s is flagged as "stale" in metadata
2. **AC2:** Data older than 300s (5 min) is rejected/filtered (not displayed)
3. **AC3:** Stale data triggers subscription refresh attempt
4. **AC4:** API responses include `data_age_seconds` field
5. **AC5:** Frontend shows visual indicator for stale data (>30s old)
6. **AC6:** Monitoring metric tracks stale data frequency per symbol

---

## Tasks / Subtasks

- [ ] Task 1: Implement data freshness check (AC: 1, 2)
  - [ ] Add `check_data_freshness(timestamp)` function
  - [ ] Return freshness status: FRESH (<30s), WARN (30-60s), STALE (60-300s), REJECT (>300s)
  - [ ] Apply check to all incoming data points
  - [ ] Log WARNING for STALE, ERROR for REJECT

- [ ] Task 2: Add freshness metadata to data (AC: 1, 4)
  - [ ] Add `data_age_seconds` to all data responses
  - [ ] Add `freshness_status` enum field
  - [ ] Include `source_timestamp` and `processed_timestamp`

- [ ] Task 3: Trigger subscription refresh on stale data (AC: 3)
  - [ ] On STALE status, queue subscription refresh
  - [ ] Rate limit: max 1 refresh per symbol per 30s
  - [ ] Log refresh attempt and result

- [ ] Task 4: Implement data rejection (AC: 2)
  - [ ] Data with REJECT status is not forwarded to consumers
  - [ ] Log rejected data count
  - [ ] Return empty/null with explanation

- [ ] Task 5: Create frontend staleness indicator (AC: 5)
  - [ ] Display "Updated X seconds ago" in data panels
  - [ ] Yellow warning badge for data > 30s old
  - [ ] Red "STALE" badge for data > 60s old
  - [ ] Grey out / dim data > 120s old

- [ ] Task 6: Add staleness monitoring metrics (AC: 6)
  - [ ] Track: stale_data_events_total (counter)
  - [ ] Track: data_age_seconds (histogram)
  - [ ] Labels: symbol, data_type
  - [ ] Create dashboard/alert for high staleness rate

---

## Dev Notes

### Data Freshness Levels

| Level | Age Range | Action | Log Level |
|-------|-----------|--------|-----------|
| FRESH | 0-30s | Normal processing | DEBUG |
| WARN | 30-60s | Add warning flag | INFO |
| STALE | 60-300s | Flag + refresh subscription | WARNING |
| REJECT | >300s | Filter out, don't display | ERROR |

### Freshness Check Implementation

```python
from enum import Enum
from datetime import datetime

class FreshnessStatus(Enum):
    FRESH = "fresh"
    WARN = "warn"
    STALE = "stale"
    REJECT = "reject"

FRESHNESS_THRESHOLDS = {
    FreshnessStatus.FRESH: 30,
    FreshnessStatus.WARN: 60,
    FreshnessStatus.STALE: 300,
}

def check_data_freshness(data_timestamp: float) -> tuple[FreshnessStatus, float]:
    """Check data freshness and return status with age."""
    now = datetime.now().timestamp()
    age = now - data_timestamp

    if age < FRESHNESS_THRESHOLDS[FreshnessStatus.FRESH]:
        return FreshnessStatus.FRESH, age
    elif age < FRESHNESS_THRESHOLDS[FreshnessStatus.WARN]:
        return FreshnessStatus.WARN, age
    elif age < FRESHNESS_THRESHOLDS[FreshnessStatus.STALE]:
        return FreshnessStatus.STALE, age
    else:
        return FreshnessStatus.REJECT, age
```

### Enhanced Data Response

```python
@dataclass
class DataPoint:
    symbol: str
    price: float
    volume: float
    source_timestamp: float
    processed_timestamp: float
    data_age_seconds: float
    freshness_status: FreshnessStatus

    @classmethod
    def from_raw(cls, raw_data: dict) -> "DataPoint":
        source_ts = raw_data["timestamp"]
        processed_ts = datetime.now().timestamp()
        status, age = check_data_freshness(source_ts)

        return cls(
            symbol=raw_data["symbol"],
            price=raw_data["price"],
            volume=raw_data["volume"],
            source_timestamp=source_ts,
            processed_timestamp=processed_ts,
            data_age_seconds=age,
            freshness_status=status
        )
```

### Frontend Staleness Display

```typescript
interface DataFreshness {
  status: 'fresh' | 'warn' | 'stale' | 'reject';
  age_seconds: number;
  source_timestamp: string;
}

function DataAgeIndicator({ freshness }: { freshness: DataFreshness }) {
  const colors = {
    fresh: 'green',
    warn: 'yellow',
    stale: 'red',
    reject: 'gray'
  };

  return (
    <span style={{ color: colors[freshness.status] }}>
      {freshness.age_seconds < 60
        ? `${Math.round(freshness.age_seconds)}s ago`
        : `${Math.round(freshness.age_seconds / 60)}m ago`}
    </span>
  );
}
```

### Files to Modify

**Backend:**
- `src/engine/streaming_indicator_engine.py` - Data processing
- `src/core/data_freshness.py` (new) - Freshness utilities
- `src/api/websocket/` - Add freshness to WebSocket messages

**Frontend:**
- `frontend/src/components/common/DataAgeIndicator.tsx` (new)
- `frontend/src/components/dashboard/*.tsx` - Add indicators to panels

### Dependencies

- Benefits from BUG-008-5 (subscription lifecycle) for refresh capability
- Independent of other stories otherwise

---

## Definition of Done

1. [ ] Data freshness checked on all incoming data
2. [ ] Stale data flagged in metadata
3. [ ] Very old data (>5min) rejected
4. [ ] Subscription refresh triggered on staleness
5. [ ] API responses include age information
6. [ ] Frontend shows freshness indicator
7. [ ] Metrics track staleness rate
8. [ ] Unit tests for all freshness levels
9. [ ] Integration test: simulate stale data, verify handling

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from BUG-008 Epic |
