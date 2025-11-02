# Phase 1B - Incremental Indicator System Tests

## Overview

Integration tests for Phase 1B implementation:
- ✓ Incremental indicators (EMA/SMA/VWAP/RSI/TWPA)
- ✓ Ring buffers and O(1) accumulators
- ✓ 1-second asyncio scheduler
- ✓ COPY bulk insert to TimescaleDB

## Prerequisites

### 1. Start TimescaleDB

```bash
# Start TimescaleDB container
docker-compose -f docker-compose.timescaledb.yml up -d

# Verify it's running
docker ps | grep timescale

# Initialize schema
docker exec -i fx_code_ai-timescaledb-1 psql -U trading_user -d trading < database/init/01_init_schema.sql
```

### 2. Install Python dependencies

```bash
pip install pytest pytest-asyncio asyncpg
```

## Running Tests

### Option 1: Quick Manual Test (Recommended)

```bash
python scripts/test_incremental_system.py
```

This runs a simple 10-second integration test that:
1. Verifies database connection
2. Tests incremental indicators
3. Runs scheduler for 10 seconds
4. Verifies COPY bulk insert performance

**Expected output:**
```
======================================================================
MANUAL TEST - Phase 1B: Incremental Indicator System
======================================================================

[Test 1] Database Connection
------------------------------------------------------------
✓ Connected to TimescaleDB successfully
✓ Pool size: 2/5

[Test 2] Incremental Indicators
------------------------------------------------------------
Testing with 15 price updates...
  # 1 | Price: $50,000 | EMA:        N/A | SMA:        N/A | RSI:   N/A | VWAP:  50000.00
  ...
  #15 | Price: $50,650 | EMA:  50515.38 | SMA:  50550.00 | RSI:  72.45 | VWAP:  50375.50
✓ All indicators calculated correctly

[Test 3] Scheduler + Database Integration
------------------------------------------------------------
✓ Database cleaned
✓ Inserting test market data for BTC_USDT_MANUAL_TEST...
✓ Inserted 30 market data points via COPY
✓ Registered 4 indicators
✓ Starting scheduler (will run for 10s)...
  [ 1s] Ticks:  1 | Updates:   4 | Writes:   0 | Errors: 0
  [ 4s] Ticks:  4 | Updates:  16 | Writes:  15 | Errors: 0
  [ 7s] Ticks:  7 | Updates:  28 | Writes:  25 | Errors: 0
  [10s] Ticks: 10 | Updates:  40 | Writes:  40 | Errors: 0

Final Statistics:
  Total ticks:    10
  Total updates:  40
  Total writes:   40
  Errors:         0

✓ Scheduler + Database integration successful

[Test 4] COPY Bulk Insert Performance
------------------------------------------------------------
Preparing 1000 indicator values...
✓ Inserted 1000 values via COPY in 25.43ms
  Throughput: 39324 records/second
  Per-record: 0.0254ms
✓ COPY bulk insert performance acceptable

======================================================================
TEST SUMMARY
======================================================================
  ✓ PASS - Database Connection
  ✓ PASS - Incremental Indicators
  ✓ PASS - Scheduler + Database
  ✓ PASS - COPY Performance
======================================================================

🎉 ALL TESTS PASSED - Phase 1B implementation verified!
```

### Option 2: Full pytest Suite

```bash
# Run all integration tests
pytest tests/test_incremental_system_integration.py -v -s

# Run specific test
pytest tests/test_incremental_system_integration.py::test_database_connection -v -s
```

**Test coverage:**
1. `test_database_connection` - Verify TimescaleDB connectivity
2. `test_incremental_indicators_correctness` - Math correctness of indicators
3. `test_scheduler_ticking` - 1-second tick verification
4. `test_copy_bulk_insert` - COPY performance
5. `test_end_to_end_integration` - Complete flow
6. `test_performance_o1_complexity` - O(1) complexity verification

## What's Being Tested

### Incremental Indicators (O(1) Updates)

All indicators update in constant time without recalculation:

- **IncrementalEMA**: `EMA(t) = α * Price(t) + (1 - α) * EMA(t-1)`
- **IncrementalSMA**: Ring buffer with running sum
- **IncrementalVWAP**: `Σ(price × volume) / Σ(volume)`
- **IncrementalRSI**: Wilder's smoothing for avg gain/loss
- **IncrementalTWPA**: Time-weighted with ring buffer

### Scheduler Requirements

Per user specifications:
- ✓ Fixed 1-second tick rate (asyncio)
- ✓ Updates all registered indicators per tick
- ✓ Batch writes to TimescaleDB
- ✓ Uses COPY for bulk insert (100x faster than INSERT)

### Database Requirements

Per user specifications:
- ✓ TimescaleDB with hypertables
- ✓ SEGMENT BY symbol
- ✓ Columnar compression
- ✓ COPY bulk insert

## Performance Expectations

### COPY Bulk Insert
- **1,000 records**: < 100ms (~10,000 records/sec)
- **10,000 records**: < 500ms (~20,000 records/sec)

### Indicator Updates
- **O(1) complexity**: Time per update should be constant
- **EMA/SMA/RSI**: < 0.1ms per update
- **VWAP/TWPA**: < 0.2ms per update

### Scheduler
- **Tick rate**: 1 tick/second (±10ms)
- **100 indicators**: Should complete in < 100ms per tick
- **Database flush**: < 50ms for batch of 100 values

## Troubleshooting

### Database Connection Failed

```bash
# Check if TimescaleDB is running
docker ps | grep timescale

# Check logs
docker logs fx_code_ai-timescaledb-1

# Restart if needed
docker-compose -f docker-compose.timescaledb.yml restart
```

### Schema Not Initialized

```bash
# Initialize schema
docker exec -i fx_code_ai-timescaledb-1 psql -U trading_user -d trading < database/init/01_init_schema.sql
```

### Import Errors

```bash
# Make sure you're in project root
cd /home/user/FX_code_AI

# Verify Python path
python -c "import sys; print('\\n'.join(sys.path))"
```

## Next Steps

After Phase 1B is verified:
1. Phase 1C: Fix backtesting engine (use TimescaleDB instead of hardcoded prices)
2. Phase 2: UI improvements (OR/NOT logic, templates, inline validation)
3. Phase 3: Advanced features (parameter optimization, ML)

## Implementation Files

**Phase 1B created:**
- `src/domain/services/indicators/incremental_base.py` (390 lines)
- `src/domain/services/indicators/incremental_indicators.py` (497 lines)
- `src/domain/services/indicator_scheduler.py` (418 lines)
- `tests/test_incremental_system_integration.py` (580 lines)
- `scripts/test_incremental_system.py` (470 lines)

**Total:** ~2,355 lines of production code + tests
