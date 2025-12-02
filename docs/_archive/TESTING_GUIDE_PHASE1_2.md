# Testing Guide - Phase 1 & 2 Verification
**Date:** 2025-11-08
**Branch:** `claude/analyze-handoff-plan-coordination-011CUv8MS8PAVTsZQ5aANXFX`
**Commit:** `23c72b2`

---

## Overview

This guide helps you verify the following fixes:
- ✅ **PHASE 1:** Signal flow, thread safety, database schema
- ✅ **PHASE 2:** TradingPersistenceService integration, event publishing

**Expected Result:** Paper Trading and Live Trading modes create orders from signals and persist all data to QuestDB.

---

## Prerequisites

Before starting tests, ensure you have:
- ✅ Latest code from branch pulled
- ✅ Python virtual environment activated
- ✅ Dependencies installed (`pip install -r requirements.txt`)

---

## Step 1: Start QuestDB

### Option A: Via PowerShell Script (Windows)
```powershell
.\start_all.ps1
```
This starts QuestDB, backend, and frontend together.

### Option B: Manual QuestDB Start
```bash
# If QuestDB is installed locally:
questdb start

# Verify it's running:
curl "http://localhost:9000/exec?query=SELECT%201"
# Expected: {"query":"SELECT 1","columns":[...],"dataset":[[1]],...}
```

### Verify QuestDB Web UI
Open in browser: http://127.0.0.1:9000

You should see the QuestDB console.

---

## Step 2: Run Migration 019

This creates the tables needed for TradingPersistenceService.

```bash
cd /home/user/FX_code_AI
python database/questdb/install_questdb.py
```

**Expected Output:**
```
================================================================================
 QuestDB Installation & Migration System
================================================================================

→ Checking QuestDB connection...
✓ Connected to QuestDB at 127.0.0.1:9000

→ Running migrations...
  → Migration 001: ✓ Already applied
  → Migration 002: ✓ Already applied
  → Migration 003: ✓ Already applied
  ...
  → Migration 019: ✓ Applying - Recreate trading tables
✓ Migration 019 completed successfully

✓ All migrations completed
```

### Verify Tables Created

In QuestDB Web UI (http://127.0.0.1:9000), run:

```sql
-- Check tables exist
SELECT table_name, designatedTimestamp, partitionBy, walEnabled
FROM tables()
WHERE table_name IN ('strategy_signals', 'orders', 'positions')
ORDER BY table_name;
```

**Expected Result:**
```
table_name        | designatedTimestamp | partitionBy | walEnabled
strategy_signals  | timestamp          | DAY         | true
orders           | timestamp          | DAY         | true
positions        | timestamp          | DAY         | true
```

### Verify Column Schemas

```sql
-- Check strategy_signals columns
SELECT column_name, column_type
FROM table_columns('strategy_signals')
ORDER BY column_name;

-- Check orders columns
SELECT column_name, column_type
FROM table_columns('orders')
ORDER BY column_name;

-- Check positions columns
SELECT column_name, column_type
FROM table_columns('positions')
ORDER BY column_name;
```

**Expected:** All columns from migration 019 should be present.

---

## Step 3: Start Backend Server

```bash
cd /home/user/FX_code_AI
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload
```

### Check Startup Logs

Look for these log entries:

```
✅ CRITICAL - Look for these:
INFO: unified_trading_controller.trading_persistence_started
INFO: order_manager.started
INFO: event_bus.subscriber_added topic="signal_generated"
INFO: event_bus.subscriber_added topic="order_created"
INFO: event_bus.subscriber_added topic="order_filled"
INFO: event_bus.subscriber_added topic="position_opened"
```

**If you see errors:**
- `asyncpg.exceptions.UndefinedTableError` → Migration 019 didn't run correctly
- `ModuleNotFoundError` → Dependencies not installed
- `asyncio.Lock` errors → Check Python version (need 3.9+)

---

## Step 4: Test Paper Trading

### 4.1 Start Paper Trading Session

```bash
curl -X POST http://localhost:8080/api/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "paper",
    "symbols": ["BTC_USDT"],
    "data_types": ["prices"],
    "duration": 300
  }'
```

**Expected Response:**
```json
{
  "status": "success",
  "session_id": "session_20251108_123456",
  "mode": "paper",
  "symbols": ["BTC_USDT"],
  "message": "Paper trading session started"
}
```

### 4.2 Check Session Status

```bash
curl http://localhost:8080/api/sessions/status
```

**Expected Response:**
```json
{
  "status": "RUNNING",
  "mode": "PAPER",
  "symbols": ["BTC_USDT"],
  "progress": 15.3,
  "duration_seconds": 46
}
```

### 4.3 Monitor Backend Logs

Watch for:
```
✅ SUCCESS INDICATORS:
INFO: strategy_manager.signal_generated signal_type="S1" symbol="BTC_USDT"
INFO: order_manager.signal_processed signal_type="S1"
INFO: order_manager.order_created order_id="order_xxx"
INFO: order_manager.order_filled order_id="order_xxx"
INFO: trading_persistence.signal_saved table="strategy_signals"
INFO: trading_persistence.order_saved table="orders"
INFO: trading_persistence.position_saved table="positions"
```

**If you DON'T see these:**
- No `signal_generated` → Strategy conditions not met (market data issue)
- No `order_created` → Signal flow broken (should be fixed by Agent 1)
- No `trading_persistence.*` → TradingPersistenceService not subscribed

---

## Step 5: Verify Database Writes

After ~2-5 minutes of running, check QuestDB:

### Check Signals Table

```sql
SELECT
    signal_id,
    strategy_id,
    symbol,
    signal_type,
    action,
    triggered,
    timestamp
FROM strategy_signals
WHERE symbol = 'BTC_USDT'
ORDER BY timestamp DESC
LIMIT 10;
```

**Expected:** At least 1-5 rows (depends on market conditions and strategy triggers)

**If EMPTY:**
- Check backend logs for `strategy_manager.signal_generated`
- Verify EventBus subscription: `trading_persistence.subscribed topic="signal_generated"`

### Check Orders Table

```sql
SELECT
    order_id,
    strategy_id,
    symbol,
    side,
    order_type,
    quantity,
    price,
    status,
    timestamp
FROM orders
WHERE symbol = 'BTC_USDT'
ORDER BY timestamp DESC
LIMIT 10;
```

**Expected:** At least 1-5 rows (one per signal)

**If EMPTY:**
- Check `order_manager.order_created` in logs
- Verify EventBus: `trading_persistence.subscribed topic="order_created"`
- Check if OrderManager published events (Agent 5 fix)

### Check Positions Table

```sql
SELECT
    position_id,
    strategy_id,
    symbol,
    side,
    quantity,
    entry_price,
    current_price,
    unrealized_pnl,
    status,
    timestamp
FROM positions
WHERE symbol = 'BTC_USDT'
ORDER BY timestamp DESC
LIMIT 10;
```

**Expected:** At least 1-2 rows (positions opened from orders)

**If EMPTY:**
- Check `order_manager.position_opened` in logs
- Verify EventBus: `trading_persistence.subscribed topic="position_opened"`
- Check if OrderManager published position events (Agent 5 fix)

### Check All Tables Summary

```sql
-- Quick summary of all trading data
SELECT
    'strategy_signals' as table_name,
    COUNT(*) as row_count,
    MAX(timestamp) as last_entry
FROM strategy_signals
UNION ALL
SELECT
    'orders',
    COUNT(*),
    MAX(timestamp)
FROM orders
UNION ALL
SELECT
    'positions',
    COUNT(*),
    MAX(timestamp)
FROM positions;
```

**Expected:**
```
table_name         | row_count | last_entry
strategy_signals   | 5         | 2025-11-08T14:23:45.123Z
orders            | 5         | 2025-11-08T14:23:45.234Z
positions         | 2         | 2025-11-08T14:23:45.345Z
```

---

## Step 6: Test Live Trading (Optional)

**⚠️ WARNING:** This uses REAL exchange API and may create REAL orders if configured incorrectly.

### 6.1 Configure for Paper Mode

Edit `config.json` or set environment variable:
```json
{
  "trading": {
    "live_trading_enabled": false
  }
}
```

### 6.2 Start Live Trading Session

```bash
curl -X POST http://localhost:8080/api/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "live",
    "symbols": ["BTC_USDT"],
    "data_types": ["prices"],
    "duration": 300
  }'
```

### 6.3 Verify Same Data Flow

LiveOrderManager should publish same events as OrderManager (paper).

Check logs for:
```
INFO: live_order_manager.signal_processed
INFO: live_order_manager.order_created
INFO: live_order_manager.order_filled
INFO: trading_persistence.order_saved
```

---

## Step 7: Stop Session and Cleanup

```bash
curl -X POST http://localhost:8080/api/sessions/stop
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Session stopped successfully"
}
```

Check logs for cleanup:
```
INFO: unified_trading_controller.trading_persistence_stopped
INFO: order_manager.stopped
INFO: event_bus.unsubscribed topic="signal_generated"
```

---

## Troubleshooting

### Issue: No signals generated

**Symptoms:**
- Backend running but no `signal_generated` in logs
- Empty `strategy_signals` table

**Diagnosis:**
```bash
# Check if strategies are active
curl http://localhost:8080/api/strategies/active

# Check market data is flowing
# Look for logs: "market.price_update"
```

**Solutions:**
- Strategies may not be activated → Activate via API
- Market conditions don't trigger signals → Wait longer or adjust thresholds
- MEXC adapter not connected → Check exchange credentials

### Issue: Signals but no orders

**Symptoms:**
- `signal_generated` in logs
- But NO `order_created`

**Diagnosis:**
This means Agent 1 fix didn't work. Check:
```python
# In src/domain/services/order_manager.py line 170
# Should be: await self.event_bus.subscribe("signal_generated", ...)

# In src/domain/services/strategy_manager.py line 1791
# Should be: await self.event_bus.publish("signal_generated", ...)
```

**Solutions:**
- Verify Agent 1 changes are in code
- Check EventBus topic name matches exactly
- Restart backend to reload code

### Issue: Orders but no database writes

**Symptoms:**
- `order_created` in logs
- But empty `orders` table in QuestDB

**Diagnosis:**
TradingPersistenceService not working. Check:
```bash
# Look for these in logs:
INFO: trading_persistence.subscribed topic="order_created"
INFO: trading_persistence.order_saved

# If missing, check:
INFO: unified_trading_controller.trading_persistence_started
```

**Solutions:**
- Verify Agent 4 wired service correctly
- Check QuestDB connection: `asyncpg.exceptions.*`
- Verify tables exist: migration 019 ran successfully
- Check EventBus: `event_bus.subscriber_count topic="order_created"`

### Issue: asyncpg connection errors

**Symptoms:**
```
asyncpg.exceptions.InvalidCatalogNameError: database "qdb" does not exist
```

**Solution:**
QuestDB default database is `qdb`. Check connection string:
```python
# In container.py line 473
host='127.0.0.1',
port=8812,
database='qdb',  # Must match QuestDB config
```

### Issue: Thread safety errors

**Symptoms:**
```
RuntimeError: cannot call `await` on a non-coroutine
RuntimeError: Task got Future attached to a different loop
```

**Solution:**
Agent 3 made some methods async. Ensure all callers use `await`:
```python
# OLD (broken):
orders = order_manager.get_all_orders()

# NEW (correct):
orders = await order_manager.get_all_orders()
```

---

## Success Criteria

✅ **All tests pass if:**

1. **QuestDB Migration:**
   - ✅ Migration 019 runs without errors
   - ✅ Tables `strategy_signals`, `orders`, `positions` exist
   - ✅ All columns match migration schema

2. **Backend Startup:**
   - ✅ Backend starts without errors
   - ✅ TradingPersistenceService starts successfully
   - ✅ EventBus subscriptions registered (7 topics)

3. **Paper Trading Flow:**
   - ✅ Session starts successfully
   - ✅ Market data flows (logs show `market.price_update`)
   - ✅ Signals generated (logs show `signal_generated`)
   - ✅ Orders created (logs show `order_created`)
   - ✅ Positions opened (logs show `position_opened`)

4. **Database Persistence:**
   - ✅ `strategy_signals` table has rows
   - ✅ `orders` table has rows
   - ✅ `positions` table has rows
   - ✅ Timestamps are recent (within last 5 minutes)

5. **Cleanup:**
   - ✅ Session stops without errors
   - ✅ EventBus unsubscribes correctly
   - ✅ No memory leaks (check process memory)

---

## Next Steps

After successful testing:

1. **Create Pull Request** from branch to main
2. **Document test results** in PR description
3. **Run automated test suite**: `python run_tests.py`
4. **Performance testing** (optional): Run 1-hour session, check memory
5. **Move to PHASE 3**: Backtesting integration

---

## Test Results Template

Copy this to document your test results:

```markdown
# Test Results - Phase 1 & 2

**Date:** [Date]
**Tester:** [Your name]
**Commit:** 23c72b2

## Environment
- OS: [Windows/Linux/Mac]
- Python: [Version]
- QuestDB: [Version]

## Migration 019
- [ ] Ran successfully
- [ ] Tables created: strategy_signals, orders, positions
- [ ] All columns present

## Backend Startup
- [ ] No errors on startup
- [ ] TradingPersistenceService started
- [ ] EventBus subscriptions: 7 topics

## Paper Trading Test
- [ ] Session started successfully
- [ ] Market data flowing
- [ ] Signals generated: [count]
- [ ] Orders created: [count]
- [ ] Positions opened: [count]

## Database Verification
- [ ] strategy_signals rows: [count]
- [ ] orders rows: [count]
- [ ] positions rows: [count]

## Issues Found
[List any issues or unexpected behavior]

## Conclusion
[PASS / FAIL / PARTIAL]
```

---

**End of Testing Guide**
