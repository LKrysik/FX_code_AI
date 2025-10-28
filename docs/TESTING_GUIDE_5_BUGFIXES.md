# Testing Guide: 5 Critical Bug Fixes

**Quick Reference Guide for Production/Staging Testing**

## Overview

This guide provides step-by-step testing procedures for the 5 critical bug fixes implemented in the QuestDB migration project.

**Prerequisite**: QuestDB must be running and accessible on ports 9009 (ILP) and 8812 (PostgreSQL wire protocol).

---

## Setup

### 1. Start QuestDB

```bash
# Start QuestDB (if not already running)
cd ~/questdb
./bin/questdb.sh start

# Verify QuestDB is running
curl http://localhost:9000/health
```

### 2. Start API Server

```bash
cd /home/user/FX_code_AI
python src/main.py
```

### 3. Create Test Session

```bash
# Create a test data collection session
# Replace with your actual session creation method
# Example assumes you have a script or API endpoint for this
```

---

## Test 1: BUG-004 - Delete Methods Foundation

**What**: Test QuestDB provider delete methods work correctly

**API Endpoint**: None (internal methods, tested via BUG-001)

**Test via Python**:

```python
import asyncio
from data_feed.questdb_provider import QuestDBProvider
from data.questdb_data_provider import QuestDBDataProvider
from core.logger import StructuredLogger

async def test_delete_methods():
    # Initialize providers
    questdb = QuestDBProvider(
        ilp_host='127.0.0.1', ilp_port=9009,
        pg_host='127.0.0.1', pg_port=8812
    )
    await questdb.initialize()

    logger = StructuredLogger("test")
    provider = QuestDBDataProvider(questdb, logger)

    # Create a test session with data
    session_id = "test_delete_001"
    # ... insert test data ...

    # Test delete
    result = await provider.delete_session(session_id)
    print(f"Deleted: {result}")

    await questdb.close()

asyncio.run(test_delete_methods())
```

**Expected Results**:
- ✅ All tables with session data are deleted
- ✅ Returns counts: `{'tick_prices': X, 'indicators': Y, ...}`
- ✅ No orphaned rows remain in database

**Verification**:
```sql
-- Run in QuestDB web console (http://localhost:9000)
SELECT COUNT(*) FROM tick_prices WHERE session_id = 'test_delete_001';
-- Should return 0
```

---

## Test 2: BUG-001 - delete_session API

**What**: Test DELETE /api/data-analysis/sessions/{session_id} endpoint

**Prerequisites**: Have a completed (non-active) test session

### Test 2.1: Delete Valid Session

```bash
# Get list of sessions
curl http://localhost:8000/api/data-analysis/sessions

# Delete a test session
curl -X DELETE http://localhost:8000/api/data-analysis/sessions/test_session_001

# Expected response:
{
  "success": true,
  "session_id": "test_session_001",
  "deleted_counts": {
    "backtest_results": 0,
    "indicators": 864000,
    "aggregated_ohlcv": 28800,
    "tick_orderbook": 0,
    "tick_prices": 288000,
    "data_collection_sessions": 1,
    "total": 1180801
  },
  "message": "Successfully deleted session test_session_001 and 1180801 related records"
}
```

### Test 2.2: Attempt Delete Active Session

```bash
# Try to delete an active session
curl -X DELETE http://localhost:8000/api/data-analysis/sessions/active_session_001

# Expected response:
{
  "success": false,
  "error": "Cannot delete active session active_session_001"
}
```

### Test 2.3: Verify Deletion

```bash
# Query deleted session - should return 404
curl http://localhost:8000/api/data-analysis/sessions/test_session_001

# Expected: 404 Not Found
```

**Success Criteria**:
- ✅ Valid session deleted successfully
- ✅ Active session deletion rejected
- ✅ Deleted session not queryable
- ✅ Deletion counts accurate

---

## Test 3: BUG-003 - DataExportService

**What**: Test data export endpoints work with QuestDB

**Prerequisites**: Have a session with data in QuestDB

### Test 3.1: Export to CSV

```bash
curl -X GET \
  "http://localhost:8000/api/data-analysis/sessions/test_session_001/export?format=csv" \
  -o test_export.csv

# Verify file contents
head -20 test_export.csv
```

**Expected**: CSV file with columns: timestamp, price, volume

### Test 3.2: Export to JSON

```bash
curl -X GET \
  "http://localhost:8000/api/data-analysis/sessions/test_session_001/export?format=json" \
  -o test_export.json

# Verify JSON structure
cat test_export.json | python -m json.tool | head -30
```

**Expected**: JSON array with objects: `[{"timestamp": ..., "price": ..., "volume": ...}, ...]`

### Test 3.3: Export to ZIP

```bash
curl -X GET \
  "http://localhost:8000/api/data-analysis/sessions/test_session_001/export?format=zip" \
  -o test_export.zip

# Extract and verify contents
unzip -l test_export.zip
```

**Expected**: ZIP archive containing session_metadata.json and per-symbol data files

### Test 3.4: Export Non-Existent Session

```bash
curl -X GET \
  "http://localhost:8000/api/data-analysis/sessions/nonexistent_session/export?format=csv"

# Expected: 404 error
```

**Success Criteria**:
- ✅ All export formats work
- ✅ Data matches database contents
- ✅ Non-existent session returns 404
- ✅ File formats are valid

---

## Test 4: BUG-005 - DataQualityService

**What**: Test data quality assessment with full dataset

**Prerequisites**: Have a session with data (ideally with some gaps/anomalies for interesting results)

### Test 4.1: Assess Session Quality

```bash
curl -X GET \
  "http://localhost:8000/api/data-analysis/sessions/test_session_001/quality?symbol=BTC/USDT"
```

**Expected Response**:
```json
{
  "session_id": "test_session_001",
  "symbol": "BTC/USDT",
  "overall_score": 87.5,
  "completeness_score": 98.2,
  "gap_count": 3,
  "anomaly_count": 12,
  "data_points": 288000,
  "missing_values": 0,
  "timestamp_issues": 0
}
```

### Test 4.2: Get Quality Report

```bash
curl -X GET \
  "http://localhost:8000/api/data-analysis/sessions/test_session_001/quality/report?symbol=BTC/USDT" \
  | python -m json.tool
```

**Expected Response**: Detailed report including:
- Metrics (overall_score, completeness, etc.)
- Gaps list (start_time, end_time, duration, severity)
- Anomalies list (timestamp, field, value, expected_range)
- Recommendations (improvement suggestions)

### Test 4.3: Verify Full Dataset Analysis

**Before Fix**: Only analyzed 5K points
**After Fix**: Analyzes ALL points

```bash
# Check logs to verify dataset size
tail -f logs/api.log | grep "Quality assessment"

# Should show log like:
# "Quality assessment for session test_session_001: score=87.5, gaps=3, anomalies=12"
```

**Success Criteria**:
- ✅ Quality metrics calculated
- ✅ Full dataset analyzed (not just 5K points)
- ✅ Gaps detected correctly
- ✅ Anomalies detected correctly
- ✅ Recommendations provided

---

## Test 5: BUG-002 - Indicators API QuestDB Integration

**What**: Test indicators are written to and read from QuestDB

**Prerequisites**: Have a session with tick price data

### Test 5.1: Compute New Indicator

```bash
curl -X POST \
  http://localhost:8000/api/indicators/sessions/test_session_001/indicators \
  -H "Content-Type: application/json" \
  -d '{
    "indicator_type": "moving_average",
    "symbol": "BTC/USDT",
    "parameters": {
      "period": 20,
      "ma_type": "SMA"
    },
    "variant_id": "sma_20"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "indicator_id": "moving_average_sma_20",
  "points_computed": 287980,
  "storage": {
    "questdb": true,
    "csv": true
  }
}
```

**Check Logs**:
```bash
tail -f logs/api.log | grep "indicator"

# Should see:
# "Inserted 287980 indicators to QuestDB"
# "Saved 287980 indicators to CSV (backward compatibility)"
```

### Test 5.2: Query Indicator from QuestDB

```bash
curl -X GET \
  "http://localhost:8000/api/indicators/sessions/test_session_001/history?symbol=BTC/USDT&indicator_id=moving_average_sma_20&limit=100"
```

**Expected Response**:
```json
{
  "history": [
    {
      "timestamp": 1698364800,
      "value": 35234.56,
      "metadata": {
        "session_id": "test_session_001",
        "symbol": "BTC/USDT",
        "confidence": 0.95
      }
    },
    ...
  ],
  "source": "questdb"
}
```

**Critical**: Verify `"source": "questdb"` (not `"csv_fallback"`)

### Test 5.3: Verify Dual-Write Consistency

```bash
# Query from QuestDB via API
curl "http://localhost:8000/api/indicators/sessions/test_session_001/history?symbol=BTC/USDT&indicator_id=moving_average_sma_20&limit=10" > questdb_data.json

# Compare with CSV (if you have CSV reading endpoint)
# OR check QuestDB directly:
```

**SQL Query** (http://localhost:9000):
```sql
SELECT timestamp, value, confidence
FROM indicators
WHERE session_id = 'test_session_001'
  AND symbol = 'BTC/USDT'
  AND indicator_id = 'moving_average_sma_20'
ORDER BY timestamp DESC
LIMIT 10;
```

**Verify**: QuestDB data matches API response

### Test 5.4: Test CSV Fallback

```bash
# Temporarily stop QuestDB
cd ~/questdb
./bin/questdb.sh stop

# Query indicator - should fallback to CSV
curl -X GET \
  "http://localhost:8000/api/indicators/sessions/test_session_001/history?symbol=BTC/USDT&indicator_id=moving_average_sma_20&limit=10"

# Expected response should include:
# "source": "csv_fallback"

# Restart QuestDB
./bin/questdb.sh start
```

### Test 5.5: Test Backtest Integration

```bash
# Run a backtest that uses indicators
curl -X POST \
  http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_001",
    "strategy": "ma_crossover",
    "symbols": ["BTC/USDT"],
    "indicators": ["moving_average_sma_20", "moving_average_sma_50"],
    "start_time": "2024-10-01T00:00:00Z",
    "end_time": "2024-10-28T00:00:00Z"
  }'
```

**Expected**: Backtest successfully queries indicators from QuestDB and completes

**Success Criteria**:
- ✅ New indicators written to both QuestDB and CSV
- ✅ Indicator queries read from QuestDB (check "source" field)
- ✅ Dual-write succeeds for both storage systems
- ✅ CSV fallback works when QuestDB unavailable
- ✅ Backtests can query indicators from QuestDB

---

## Test 6: Migration Script

**What**: Test historical indicator CSV migration to QuestDB

**Prerequisites**: Have historical indicator CSV files in data directory

### Test 6.1: Dry Run

```bash
cd /home/user/FX_code_AI
python database/questdb/migrate_indicators_csv_to_questdb.py \
  --dry-run \
  --verbose
```

**Expected Output**:
```
[1/24] Migrating moving_average_sma_20 for exec_20251027_123456/BTC/USDT...
[2/24] Migrating moving_average_sma_50 for exec_20251027_123456/BTC/USDT...
...
============================================================
MIGRATION SUMMARY
============================================================
Indicators found:     24
Indicators migrated:  0
Indicators skipped:   0
Indicators failed:    0
Total records:        5760000
Sessions processed:   3
Errors:               0

(DRY RUN - no data was actually migrated)
============================================================
```

### Test 6.2: Actual Migration

```bash
python database/questdb/migrate_indicators_csv_to_questdb.py --verbose
```

**Expected**: Similar output but without "(DRY RUN)" message

### Test 6.3: Verify Migration

```sql
-- Check migrated indicators in QuestDB (http://localhost:9000)
SELECT session_id, symbol, indicator_id, COUNT(*) as row_count
FROM indicators
GROUP BY session_id, symbol, indicator_id
ORDER BY session_id, symbol, indicator_id;
```

**Expected**: Row counts match CSV file line counts

### Test 6.4: Test Duplicate Prevention

```bash
# Re-run migration - should skip already migrated indicators
python database/questdb/migrate_indicators_csv_to_questdb.py --verbose
```

**Expected Output**:
```
Indicators found:     24
Indicators migrated:  0
Indicators skipped:   24  <-- All skipped (already in DB)
```

### Test 6.5: Filter by Session

```bash
python database/questdb/migrate_indicators_csv_to_questdb.py \
  --session exec_20251027_123456 \
  --verbose
```

**Expected**: Only indicators for specified session migrated

### Test 6.6: Filter by Symbol

```bash
python database/questdb/migrate_indicators_csv_to_questdb.py \
  --symbol "BTC/USDT" \
  --verbose
```

**Expected**: Only indicators for specified symbol migrated

**Success Criteria**:
- ✅ Dry-run shows correct indicator count without modifying database
- ✅ Actual migration inserts correct number of rows
- ✅ Re-running migration skips duplicates
- ✅ Session filter works correctly
- ✅ Symbol filter works correctly
- ✅ QuestDB data matches CSV data

---

## Monitoring Commands

### Check QuestDB Health

```bash
# Health check
curl http://localhost:9000/health

# Check connection from Python
python -c "
import asyncio
from data_feed.questdb_provider import QuestDBProvider

async def check():
    qdb = QuestDBProvider('127.0.0.1', 9009, '127.0.0.1', 8812)
    await qdb.initialize()
    health = await qdb.health_check()
    print(f'QuestDB Health: {health}')
    await qdb.close()

asyncio.run(check())
"
```

### Monitor API Logs

```bash
# Watch for indicator operations
tail -f logs/api.log | grep "indicator"

# Watch for delete operations
tail -f logs/api.log | grep "delete_session"

# Watch for export operations
tail -f logs/api.log | grep "export"

# Watch for quality assessments
tail -f logs/api.log | grep "quality"
```

### Check Database Row Counts

```sql
-- Run in QuestDB web console (http://localhost:9000)

-- Overall counts
SELECT
  'tick_prices' as table_name, COUNT(*) as row_count FROM tick_prices
UNION ALL
SELECT 'indicators', COUNT(*) FROM indicators
UNION ALL
SELECT 'aggregated_ohlcv', COUNT(*) FROM aggregated_ohlcv
UNION ALL
SELECT 'tick_orderbook', COUNT(*) FROM tick_orderbook
UNION ALL
SELECT 'backtest_results', COUNT(*) FROM backtest_results
UNION ALL
SELECT 'data_collection_sessions', COUNT(*) FROM data_collection_sessions;

-- Per-session counts
SELECT
  session_id,
  COUNT(*) as tick_count
FROM tick_prices
GROUP BY session_id
ORDER BY session_id;

-- Indicator counts
SELECT
  session_id,
  symbol,
  indicator_id,
  COUNT(*) as point_count
FROM indicators
GROUP BY session_id, symbol, indicator_id
ORDER BY session_id, symbol, indicator_id;
```

### Performance Monitoring

```bash
# Monitor API response times
tail -f logs/api.log | grep "duration" | awk '{print $NF}'

# Monitor QuestDB query performance
# (Check QuestDB logs in ~/questdb/log/)
tail -f ~/questdb/log/stdout-*.txt | grep "SELECT"
```

---

## Troubleshooting

### Issue: QuestDB Connection Failed

**Symptoms**: API returns "Failed to connect to QuestDB" errors

**Solutions**:
```bash
# Check if QuestDB is running
ps aux | grep questdb

# Check QuestDB logs
tail -f ~/questdb/log/stdout-*.txt

# Restart QuestDB
cd ~/questdb
./bin/questdb.sh stop
./bin/questdb.sh start

# Verify ports
netstat -tuln | grep -E '9000|9009|8812'
```

### Issue: Dual-Write Failed

**Symptoms**: Logs show "QuestDB write failed" or "CSV write failed"

**Check Logs**:
```bash
tail -f logs/api.log | grep -E "Inserted|Saved"
```

**Verify Both Writes**:
```bash
# Check QuestDB
curl "http://localhost:9000" -d "SELECT COUNT(*) FROM indicators WHERE indicator_id = 'moving_average_sma_20'"

# Check CSV
ls -lh data/*/BTC/USDT/indicators/moving_average_sma_20.csv
```

### Issue: Migration Script Fails

**Symptoms**: Migration script exits with errors

**Debug Steps**:
```bash
# Run with verbose and check first error
python database/questdb/migrate_indicators_csv_to_questdb.py --verbose 2>&1 | tee migration.log

# Check specific CSV file
head -5 data/exec_20251027_123456/BTC/USDT/indicators/moving_average_sma_20.csv

# Test with single session
python database/questdb/migrate_indicators_csv_to_questdb.py --session exec_20251027_123456 --verbose
```

### Issue: Delete Operation Hangs

**Symptoms**: DELETE request times out or takes very long

**Debug**:
```sql
-- Check row counts (may be deleting millions of rows)
SELECT COUNT(*) FROM tick_prices WHERE session_id = 'test_session_001';

-- Check for locks
-- (QuestDB doesn't have traditional locks, but check active queries)
```

**Solution**: Increase request timeout or optimize delete query

### Issue: Export Returns Empty Data

**Symptoms**: Export file is empty or has no data

**Debug**:
```bash
# Verify session has data
curl "http://localhost:8000/api/data-analysis/sessions/test_session_001"

# Check QuestDB directly
curl "http://localhost:9000" -d "SELECT COUNT(*) FROM tick_prices WHERE session_id = 'test_session_001'"

# Check API logs
tail -f logs/api.log | grep "export"
```

---

## Success Checklist

After running all tests, verify:

- [ ] **BUG-004**: Delete methods work correctly
- [ ] **BUG-001**: Delete session API removes all data
- [ ] **BUG-001**: Active sessions cannot be deleted
- [ ] **BUG-003**: Export to CSV works
- [ ] **BUG-003**: Export to JSON works
- [ ] **BUG-003**: Export to ZIP works
- [ ] **BUG-005**: Quality assessment uses full dataset
- [ ] **BUG-005**: Gaps detected correctly
- [ ] **BUG-005**: Anomalies detected correctly
- [ ] **BUG-002**: New indicators written to QuestDB
- [ ] **BUG-002**: New indicators written to CSV
- [ ] **BUG-002**: Indicator queries read from QuestDB
- [ ] **BUG-002**: CSV fallback works when QuestDB down
- [ ] **BUG-002**: Backtests can use indicators from QuestDB
- [ ] **Migration**: Dry-run shows correct counts
- [ ] **Migration**: Actual migration works
- [ ] **Migration**: Duplicate prevention works
- [ ] **Migration**: Filters (session/symbol) work

---

## Next Steps After Testing

1. **Monitor Production** (2-4 weeks):
   - Track indicator "source" field (should be "questdb" > 99%)
   - Monitor dual-write success rates
   - Track API performance metrics
   - Watch for QuestDB errors

2. **Plan CSV Deprecation**:
   - After 2-4 weeks of stable QuestDB operation
   - Remove CSV write from indicators API
   - Remove CSV fallback from history endpoint
   - Deprecate IndicatorPersistenceService

3. **Performance Optimization**:
   - Add pagination to indicator history endpoint
   - Add caching for frequently accessed data
   - Optimize QuestDB queries if needed

---

**Document Version**: 1.0
**Last Updated**: 2025-10-28
**Author**: Claude (AI Assistant)
