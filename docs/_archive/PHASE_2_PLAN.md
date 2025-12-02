# Phase 2 - UI Improvements PLAN

**Branch:** `claude/analyze-data-collection-011CUUKaSfAhFt14iHqyw5qi`
**Start Date:** 2025-10-26
**Estimated Time:** 4-6 weeks (broken into sprints)

## Overview

Improve Strategy Builder UX based on user feedback and system analysis.

From **COMPLETE_SYSTEM_ANALYSIS.md** - Problems to solve:
- **Problem 4:** No OR/NOT logic in Strategy Builder (only AND)
- **Problem 5:** No strategy templates (users can't save/load common patterns)
- **Problem 6:** No inline parameter validation
- **Problem 7:** Poor real-time feedback (no indicator preview)

### ⚡ Database Migration: TimescaleDB → QuestDB

**QuestDB 9.1.0** is available and running:
- URL: `http://127.0.0.1:9000` and `http://192.168.1.40:9000`
- Platform: Windows x86-64
- **Advantages over TimescaleDB:**
  - 🚀 **10x faster ingestion** for high-frequency data
  - 💾 **Lower memory footprint** (better for Windows)
  - 🔌 **Multiple protocols:** PostgreSQL wire, InfluxDB line, REST API
  - 📊 **Built-in Web UI** at port 9000
  - ⚡ **Native time-series optimization** (no extensions needed)
  - 🪟 **Windows native** (TimescaleDB requires Docker/WSL2)

**Migration planned for Sprint 3** - Will migrate all time-series data (prices, indicators, backtests)

---

## Current State Analysis

### Existing Code Structure

**Frontend (React + TypeScript):**
- `frontend/src/components/strategy/StrategyBuilder5Section.tsx` - Main builder
- `frontend/src/components/strategy/ConditionBlock.tsx` - Individual conditions
- `frontend/src/types/strategy.ts` - Type definitions

**Current Condition Logic:**
```typescript
// ConditionBlock.tsx line 22, 31
logicType?: 'AND';  // ONLY AND supported!

// Conditions are evaluated as:
// condition1 AND condition2 AND condition3 ...
```

**Current Limitations:**
1. ❌ No OR logic: Can't do "RSI < 30 OR Price < EMA"
2. ❌ No NOT logic: Can't do "NOT (Volume > threshold)"
3. ❌ No grouping: Can't do "(A AND B) OR (C AND D)"
4. ❌ No templates: Users rebuild common strategies from scratch
5. ❌ No validation: Invalid params accepted until backend errors
6. ❌ No preview: No live indicator values during config

---

## Phase 2 Implementation Plan

### Sprint 1: OR/NOT Logic (Week 1-2)

**Goal:** Add support for OR and NOT logical operators.

**Tasks:**

1. **Update type definitions** (`frontend/src/types/strategy.ts`)
```typescript
// Current
interface Condition {
  indicatorId: string;
  operator: '>' | '<' | '>=' | '<=' | '==';
  value: number;
}

// NEW - Add logic field
interface Condition {
  indicatorId: string;
  operator: '>' | '<' | '>=' | '<=' | '==';
  value: number;
  logic?: 'AND' | 'OR' | 'NOT';  // NEW: Logic connector
}

// NEW - Condition groups
interface ConditionGroup {
  logic: 'AND' | 'OR';
  conditions: (Condition | ConditionGroup)[];  // Recursive groups
}
```

2. **Update ConditionBlock component**
   - Add logic selector dropdown (AND/OR/NOT)
   - Visual indicator of logic type
   - Color coding: AND=blue, OR=green, NOT=red

3. **Add ConditionGroup component**
   - Visual grouping with borders
   - Nested groups support
   - Drag-and-drop reordering

4. **Update backend evaluation**
   - Modify strategy evaluator to handle OR/NOT
   - Add unit tests for complex logic

**Files to modify:**
- `frontend/src/types/strategy.ts`
- `frontend/src/components/strategy/ConditionBlock.tsx`
- `frontend/src/components/strategy/ConditionGroup.tsx` (NEW)
- `src/strategy_graph/evaluator.py` (backend logic)

**Expected result:**
```
Strategy: "Buy when oversold OR trend breakout"
  Condition 1: RSI < 30          [OR]
  Condition 2: Price > EMA_50    [AND]
  Condition 3: Volume > 1000000  [AND]

Evaluates as: (RSI < 30) OR (Price > EMA_50 AND Volume > 1000000)
```

---

### Sprint 2: Strategy Templates (Week 3-4)

**Goal:** Save/load common strategy patterns.

**Tasks:**

1. **Create template storage backend**
```python
# src/domain/services/strategy_template_service.py
class StrategyTemplate:
    id: str
    name: str
    description: str
    category: str  # "trend_following", "mean_reversion", "breakout", etc.
    strategy: Strategy5Section
    author: str
    created_at: datetime
    is_public: bool
```

2. **Add template database table**
```sql
CREATE TABLE strategy_templates (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    strategy_json JSONB NOT NULL,
    author TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_public BOOLEAN DEFAULT false,
    version INT DEFAULT 1
);
```

3. **Create template UI components**
   - Template browser dialog
   - Template preview
   - Save as template button
   - Load from template button
   - Template categories

4. **Pre-built templates**
   - "RSI Oversold/Overbought"
   - "EMA Crossover"
   - "Bollinger Band Breakout"
   - "VWAP Mean Reversion"
   - "Trend Following (Multi-timeframe)"

**Files to create:**
- `src/domain/services/strategy_template_service.py` (NEW)
- `frontend/src/components/strategy/TemplateDialog.tsx` (NEW)
- `frontend/src/components/strategy/TemplateCard.tsx` (NEW)
- `database/migrations/002_strategy_templates.sql` (NEW)

**Expected result:**
```
User clicks "Templates" button
  → Shows dialog with 10+ pre-built templates
  → User selects "RSI Oversold"
  → Strategy Builder auto-fills with:
      S1: RSI_14 < 30
      Z1: Buy with 2% position size
      ZE1: RSI_14 > 70
  → User customizes and saves
```

---

### Sprint 3: QuestDB Migration (Week 5-6) 🔥 NEW

**Goal:** Migrate from TimescaleDB (Docker) to QuestDB (native Windows) for better performance.

**Why QuestDB?**
- ✅ Already running: `http://127.0.0.1:9000` and `http://192.168.1.40:9000`
- ✅ 10x faster ingestion (1M+ rows/sec vs 100K rows/sec)
- ✅ Native Windows binary (no Docker overhead)
- ✅ Multiple protocols: PostgreSQL wire, InfluxDB line protocol, REST API
- ✅ Better for high-frequency trading data (1-second updates)
- ✅ Built-in Web UI for data visualization
- ✅ Lower memory usage (500MB vs 2GB for TimescaleDB)

**Tasks:**

1. **Create QuestDB schemas**
```sql
-- prices table (time-series)
CREATE TABLE prices (
    symbol SYMBOL,
    timestamp TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE
) timestamp(timestamp) PARTITION BY DAY;

-- indicators table (time-series)
CREATE TABLE indicators (
    symbol SYMBOL,
    indicator_id SYMBOL,
    timestamp TIMESTAMP,
    value DOUBLE,
    metadata STRING
) timestamp(timestamp) PARTITION BY DAY;

-- strategy_templates table (relational)
-- Use PostgreSQL wire protocol for this
CREATE TABLE strategy_templates (
    id UUID,
    name STRING,
    category STRING,
    strategy_json STRING,
    created_at TIMESTAMP
);
```

2. **Update data providers**
   - Modify `src/data_feed/questdb_provider.py` (NEW)
   - Use InfluxDB line protocol for fast inserts
   - Keep PostgreSQL protocol for queries

```python
# Fast bulk insert (InfluxDB line protocol)
sender = Sender('localhost', 9009)
sender.row(
    'prices',
    symbols={'symbol': 'BTC/USD'},
    columns={'open': 50000, 'close': 50100, 'volume': 1000},
    at=timestamp_nanos
)
sender.flush()

# Query with SQL (PostgreSQL wire protocol)
conn = psycopg2.connect(
    host='localhost',
    port=8812,
    user='admin',
    password='quest',
    database='qdb'
)
```

3. **Migrate existing data**
   - Export from TimescaleDB (COPY to CSV)
   - Import to QuestDB (InfluxDB line protocol)
   - Script: `scripts/migrate_timescale_to_questdb.py`
   - Estimated time: 10 minutes for 1M rows

4. **Update indicator scheduler**
   - Change connection from TimescaleDB to QuestDB
   - Use InfluxDB line protocol for 1-second inserts
   - Expected: 10x faster writes

5. **Update backtesting engine**
   - Change data provider to QuestDB
   - Use SQL queries via PostgreSQL protocol
   - Keep same API interface

6. **Update strategy template service**
   - Store templates in QuestDB (or keep in SQLite for simplicity)
   - Templates are relational, not time-series

7. **Performance testing**
   - Benchmark: Insert 1M price records
   - Benchmark: Query indicators for backtest
   - Compare: TimescaleDB vs QuestDB
   - Expected: 5-10x faster overall

**Files to create/modify:**
- `src/data_feed/questdb_provider.py` (NEW)
- `scripts/migrate_timescale_to_questdb.py` (NEW)
- `src/config/database.py` (update connection string)
- `src/scheduler/indicator_scheduler.py` (update DB connection)
- `src/backtesting/data_provider.py` (update DB connection)
- `docs/QUESTDB_MIGRATION_GUIDE.md` (NEW)

**QuestDB Configuration:**
```ini
# server.conf
http.bind.to=0.0.0.0:9000        # Web UI
pg.net.bind.to=0.0.0.0:8812      # PostgreSQL wire protocol
line.tcp.net.bind.to=0.0.0.0:9009  # InfluxDB line protocol (fast writes)

# Performance settings
shared.worker.count=2
http.worker.count=2
cairo.sql.copy.buffer.size=2m
```

**Expected results:**
```
Before (TimescaleDB):
  - Docker container: 2GB RAM
  - Insert rate: 100K rows/sec
  - Query time: 50ms for 1 hour of data
  - Startup: 10 seconds (Docker)

After (QuestDB):
  - Native process: 500MB RAM
  - Insert rate: 1M+ rows/sec (10x faster)
  - Query time: 20ms for 1 hour of data (2.5x faster)
  - Startup: 1 second (native binary)
```

**Migration checklist:**
- [ ] Install QuestDB 9.1.0 (✅ Already installed!)
- [ ] Create schemas (prices, indicators)
- [ ] Update config files (database.py)
- [ ] Create migration script
- [ ] Test data insertion (InfluxDB protocol)
- [ ] Test data querying (PostgreSQL protocol)
- [ ] Migrate existing data
- [ ] Update indicator scheduler
- [ ] Update backtesting engine
- [ ] Update strategy template service
- [ ] Performance benchmarks
- [ ] Documentation

**Testing:**
```python
# Test 1: Fast bulk insert
import time
from questdb.ingress import Sender, Protocol

with Sender(Protocol.Tcp, 'localhost', 9009) as sender:
    start = time.time()
    for i in range(100000):
        sender.row(
            'prices',
            symbols={'symbol': 'BTC/USD'},
            columns={'close': 50000 + i, 'volume': 1000},
            at=pd.Timestamp.now().value
        )
    sender.flush()
    elapsed = time.time() - start
    print(f"Inserted 100K rows in {elapsed:.2f}s = {100000/elapsed:.0f} rows/sec")

# Expected: ~0.1s = 1M rows/sec (vs TimescaleDB: 1s = 100K rows/sec)
```

---

### Sprint 4: Inline Validation (Week 7)

**Goal:** Real-time parameter validation with helpful error messages.

**Tasks:**

1. **Add validation rules**
```typescript
// frontend/src/utils/strategyValidation.ts
interface ValidationRule {
  field: string;
  validate: (value: any) => boolean;
  message: string;
}

const validationRules: ValidationRule[] = [
  {
    field: 'z1_entry.positionSize.value',
    validate: (v) => v > 0 && v <= 100,
    message: 'Position size must be between 0-100%'
  },
  {
    field: 'z1_entry.timeoutSeconds',
    validate: (v) => v >= 0 && v <= 3600,
    message: 'Timeout must be 0-3600 seconds'
  },
  // ... more rules
];
```

2. **Add real-time validation UI**
   - Red border on invalid fields
   - Error message below field
   - Warning icon
   - "Fix all errors" summary

3. **Add contextual help**
   - Tooltips on hover
   - Info icons with explanations
   - Example values
   - Links to documentation

4. **Add validation API endpoint**
```python
# src/api/routes/strategy.py
@router.post("/validate")
async def validate_strategy(strategy: Strategy5Section):
    """
    Validate strategy and return detailed errors.
    """
    errors = []

    # Check position size
    if strategy.z1_entry.positionSize.value > 100:
        errors.append({
            "field": "z1_entry.positionSize.value",
            "message": "Position size cannot exceed 100%"
        })

    # Check indicator conflicts
    # Check timeout ranges
    # etc.

    return {"valid": len(errors) == 0, "errors": errors}
```

**Files to create/modify:**
- `frontend/src/utils/strategyValidation.ts` (NEW)
- `frontend/src/components/strategy/ValidationSummary.tsx` (NEW)
- `src/api/routes/strategy.py` (add validation endpoint)

**Expected result:**
```
User types "150" in position size field
  → Field turns red immediately
  → Error message: "Position size must be between 0-100%"
  → Save button disabled
  → Validation summary shows: "1 error to fix"

User hovers over "Timeout" field
  → Tooltip: "Time to wait for order fill (0 = no timeout)"
  → Example: "Typical: 30-300 seconds"
```

---

### Sprint 5: Real-time Indicator Preview (Week 8)

**Goal:** Show live indicator values during strategy configuration.

**Tasks:**

1. **Add indicator preview API**
```python
# src/api/routes/indicators.py
@router.get("/preview/{symbol}/{indicator_id}")
async def get_indicator_preview(
    symbol: str,
    indicator_id: str,
    timeframe: str = "1m",
    points: int = 100
):
    """
    Get recent indicator values for preview chart.
    """
    # Query from indicators table (Phase 1B)
    values = await db.get_indicator_range(
        symbol,
        indicator_id,
        start_time=now - timedelta(hours=1),
        end_time=now
    )

    return {
        "indicator_id": indicator_id,
        "current_value": values[-1] if values else None,
        "timeseries": values,
        "statistics": {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values)
        }
    }
```

2. **Create preview chart component**
   - Mini chart next to indicator selector
   - Current value highlighted
   - Threshold line overlay
   - Last 100 data points

3. **Real-time updates**
   - WebSocket connection for live data
   - Update every 1 second
   - Visual pulse when value changes

**Files to create:**
- `frontend/src/components/strategy/IndicatorPreview.tsx` (NEW)
- `frontend/src/hooks/useIndicatorPreview.ts` (NEW)
- `src/api/routes/indicators.py` (add preview endpoint)

**Expected result:**
```
User selects "RSI_14" indicator
  → Mini chart appears showing last 100 values
  → Current RSI: 45.2 (highlighted)
  → User sets threshold: RSI < 30
  → Threshold line shown on chart (red horizontal line at 30)
  → User sees: "Currently 15.2 points above threshold"
  → Chart updates every second with live data
```

---

## Phase 2 Success Metrics

### Code Quality
- [ ] TypeScript strict mode enabled
- [ ] 90%+ test coverage for new components
- [ ] No console errors in browser
- [ ] Accessibility score 95+ (Lighthouse)

### Performance
- [ ] Template load time < 200ms
- [ ] Validation response < 100ms
- [ ] Preview chart renders in < 50ms
- [ ] No UI freezing during typing

### User Experience
- [ ] Reduced time to build strategy: 10 min → 2 min
- [ ] Validation errors caught before save: 100%
- [ ] Template usage: 60%+ of strategies start from template
- [ ] User satisfaction: 8+/10

### Features
- [ ] OR/NOT logic working in production
- [ ] 10+ pre-built templates available
- [ ] All parameter fields validated
- [ ] Real-time indicator preview functional

---

## Testing Plan

### Unit Tests
```typescript
// frontend/tests/strategyValidation.test.ts
describe('Strategy Validation', () => {
  it('rejects position size > 100%', () => {
    const result = validatePositionSize(150);
    expect(result.valid).toBe(false);
    expect(result.error).toContain('100%');
  });

  it('allows position size 1-100%', () => {
    const result = validatePositionSize(50);
    expect(result.valid).toBe(true);
  });
});

// src/tests/test_condition_logic.py
def test_or_logic():
    """Test OR condition evaluation"""
    strategy = Strategy5Section(
        s1_signal={
            "conditions": [
                {"indicatorId": "RSI_14", "operator": "<", "value": 30},
                {"indicatorId": "RSI_14", "operator": ">", "value": 70, "logic": "OR"}
            ]
        }
    )

    # RSI = 25 (< 30)
    assert evaluate_strategy(strategy, {"RSI_14": 25}) == True

    # RSI = 75 (> 70)
    assert evaluate_strategy(strategy, {"RSI_14": 75}) == True

    # RSI = 50 (neither condition)
    assert evaluate_strategy(strategy, {"RSI_14": 50}) == False
```

### Integration Tests
1. Load template → Modify → Save → Backtest
2. Create complex strategy with OR/NOT → Validate → Execute
3. Real-time preview → Change parameters → See updates

### E2E Tests (Playwright)
```typescript
test('User creates strategy from template', async ({ page }) => {
  await page.goto('/strategy-builder');
  await page.click('button:has-text("Templates")');
  await page.click('text=RSI Oversold');
  await page.click('button:has-text("Use Template")');

  // Verify strategy loaded
  await expect(page.locator('input[name="strategy-name"]'))
    .toHaveValue('RSI Oversold');

  // Modify and save
  await page.fill('input[name="rsi-threshold"]', '25');
  await page.click('button:has-text("Save Strategy")');

  await expect(page.locator('.success-message'))
    .toBeVisible();
});
```

---

## Implementation Order

### Week 1-2: OR/NOT Logic ✅ COMPLETE
- Day 1-2: Update type definitions, backend logic
- Day 3-5: Update ConditionBlock UI
- Day 6-8: Add ConditionGroup component
- Day 9-10: Testing and bug fixes

### Week 3-4: Strategy Templates ✅ COMPLETE
- Day 1-2: Database schema, backend service
- Day 3-5: Template browser UI
- Day 6-7: Create 10+ pre-built templates
- Day 8-10: Testing and polish

### Week 5-6: QuestDB Migration 🔥 NEXT
- Day 1: Create QuestDB schemas (prices, indicators)
- Day 2: Create migration script (TimescaleDB → QuestDB)
- Day 3: Update data providers (InfluxDB line protocol)
- Day 4: Update indicator scheduler (1-second inserts)
- Day 5: Update backtesting engine (queries)
- Day 6: Migrate existing data
- Day 7-8: Performance benchmarks and testing
- Day 9: Documentation
- Day 10: Cleanup and optimization

### Week 7: Inline Validation
- Day 1-2: Validation rules and logic
- Day 3-4: UI components for errors
- Day 5: API endpoint and integration

### Week 8: Indicator Preview
- Day 1-2: Preview API endpoint (using QuestDB)
- Day 3-4: Chart component
- Day 5: WebSocket integration
- Day 6: Testing and performance optimization

---

## Dependencies

**Frontend:**
- React 18+
- Material-UI 5+
- Recharts (for preview charts)
- React Hook Form (for validation)

**Backend:**
- FastAPI
- asyncpg (for PostgreSQL wire protocol)
- questdb (Python client for InfluxDB line protocol)
- Pydantic (for validation)

**Database:**
- **QuestDB 9.1.0** ✅ (native Windows, running on ports 9000, 8812, 9009)
  - Replaces TimescaleDB (Docker) from Phase 1A
  - 10x faster ingestion for high-frequency data
  - Better for 1-second indicator updates
  - Built-in Web UI at http://127.0.0.1:9000

---

## Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| OR/NOT logic breaks existing strategies | High | Low | Backward compatibility mode, migration script |
| Templates not useful | Medium | Medium | User research first, iterate based on feedback |
| Performance issues with real-time preview | Medium | Medium | Debouncing, caching, lazy loading |
| Complex UI confuses users | High | Low | User testing, progressive disclosure, help tooltips |
| QuestDB migration data loss | High | Low | Full backup before migration, validation script |
| QuestDB incompatibility | Medium | Low | Keep TimescaleDB code for rollback, test thoroughly |
| QuestDB performance issues | Low | Very Low | QuestDB is proven faster, but have rollback plan |

---

## Post-Phase 2 (Future)

After Phase 2, consider:
- **Phase 3:** Parameter optimization (grid search, genetic algorithms)
- **Phase 4:** Multi-strategy portfolios
- **Phase 5:** Machine learning integration

---

Generated: 2025-10-26
Author: Claude AI
Branch: `claude/analyze-data-collection-011CUUKaSfAhFt14iHqyw5qi`
