# TIER 1.2 - Paper Trading Testing Plan

**Date:** 2025-11-04
**Status:** Implementation Complete - Ready for Testing
**Completion:** 80% (API + Persistence) | 20% Remaining (ExecutionController Integration + WebSocket + UI)

---

## Executive Summary

TIER 1.2 implements a **complete paper trading system** with:
- Full futures API simulation (SHORT + LONG)
- Realistic slippage and funding rates
- QuestDB persistence for sessions, orders, positions, performance
- REST API for session management
- Paper trading adapter matching live MexcFuturesAdapter interface

This document provides **comprehensive testing procedures** to verify all functionality.

---

## Prerequisites

### 1. QuestDB Running
```bash
# Ensure QuestDB is running on port 9000 (web) and 8812 (PostgreSQL)
python database/questdb/install_questdb.py

# Verify web UI
open http://127.0.0.1:9000

# Check PostgreSQL connection
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect(host='127.0.0.1', port=8812, user='admin', password='quest', database='qdb'))"
```

### 2. Apply Database Migration
```bash
# Run migration 013 to create paper trading tables
# Option 1: Using psql
psql -h 127.0.0.1 -p 8812 -U admin -d qdb -f database/questdb/migrations/013_create_paper_trading_tables.sql

# Option 2: Using QuestDB web console
# Open http://127.0.0.1:9000
# Copy and paste SQL from 013_create_paper_trading_tables.sql
# Click "Run"
```

### 3. Start Backend Server
```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Start unified server
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload
```

### 4. Verify Initialization
```bash
# Check server logs for:
# - "Paper trading persistence initialized with QuestDB"
# - "paper_trading_routes initialized with QuestDB persistence"

# Check health endpoint
curl http://localhost:8080/api/paper-trading/health
```

---

## Test Suite

### TEST 1: Enhanced Paper Adapter

**Objective:** Verify MexcPaperAdapter supports full futures API

#### Test 1.1: Leverage Management
```python
import asyncio
from src.core.logger import get_logger
from src.infrastructure.adapters.mexc_paper_adapter import MexcPaperAdapter

async def test_leverage():
    logger = get_logger("test")

    async with MexcPaperAdapter(logger, initial_balance=10000.0) as adapter:
        # Set leverage
        result = await adapter.set_leverage("BTC_USDT", 3, "ISOLATED")
        assert result["success"] == True
        assert result["leverage"] == 3

        # Get leverage
        leverage = await adapter.get_leverage("BTC_USDT")
        assert leverage == 3

        print("✅ Leverage management works")

asyncio.run(test_leverage())
```

**Expected Result:**
```
✅ Leverage management works
```

#### Test 1.2: LONG Position Simulation
```python
async def test_long_position():
    logger = get_logger("test")

    async with MexcPaperAdapter(logger, initial_balance=10000.0) as adapter:
        # Set leverage
        await adapter.set_leverage("BTC_USDT", 3)

        # Open LONG position
        order = await adapter.place_futures_order(
            symbol="BTC_USDT",
            side="BUY",
            position_side="LONG",
            order_type="MARKET",
            quantity=0.1
        )

        assert order["status"] == "FILLED"
        assert order["side"] == "BUY"
        assert order["position_side"] == "LONG"
        assert order["leverage"] == 3
        assert order["liquidation_price"] > 0  # Should have liquidation price

        print(f"✅ LONG order placed: {order['order_id']}")
        print(f"   Entry: ${order['price']:.2f}")
        print(f"   Liquidation: ${order['liquidation_price']:.2f}")

        # Get position
        position = await adapter.get_position("BTC_USDT")
        assert position is not None
        assert position["position_side"] == "LONG"
        assert position["position_amount"] == 0.1
        assert position["leverage"] == 3

        print(f"✅ Position retrieved:")
        print(f"   Amount: {position['position_amount']} BTC")
        print(f"   Entry: ${position['entry_price']:.2f}")
        print(f"   P&L: ${position['unrealized_pnl']:.2f}")

asyncio.run(test_long_position())
```

**Expected Result:**
```
✅ LONG order placed: paper_00000001_abc12345
   Entry: $50,050.25
   Liquidation: $33,366.83
✅ Position retrieved:
   Amount: 0.1 BTC
   Entry: $50,050.25
   P&L: $-5.00
```

#### Test 1.3: SHORT Position Simulation
```python
async def test_short_position():
    logger = get_logger("test")

    async with MexcPaperAdapter(logger, initial_balance=10000.0) as adapter:
        # Set leverage
        await adapter.set_leverage("BTC_USDT", 5)

        # Open SHORT position
        order = await adapter.place_futures_order(
            symbol="BTC_USDT",
            side="SELL",
            position_side="SHORT",
            order_type="MARKET",
            quantity=0.05
        )

        assert order["status"] == "FILLED"
        assert order["side"] == "SELL"
        assert order["position_side"] == "SHORT"
        assert order["leverage"] == 5

        print(f"✅ SHORT order placed: {order['order_id']}")
        print(f"   Entry: ${order['price']:.2f}")
        print(f"   Liquidation: ${order['liquidation_price']:.2f}")

        # Verify liquidation price is ABOVE entry (for SHORT)
        assert order['liquidation_price'] > order['price'], \
            "SHORT liquidation must be above entry price"

        # Get position
        position = await adapter.get_position("BTC_USDT")
        assert position["position_side"] == "SHORT"

        print("✅ SHORT position verified")

asyncio.run(test_short_position())
```

**Expected Result:**
```
✅ SHORT order placed: paper_00000002_def67890
   Entry: $49,980.50
   Liquidation: $59,976.60  # 20% above entry (1 + 1/5 = 1.2)
✅ SHORT position verified
```

#### Test 1.4: Slippage Simulation
```python
async def test_slippage():
    logger = get_logger("test")

    async with MexcPaperAdapter(logger, initial_balance=10000.0) as adapter:
        # MARKET order should have slippage
        market_order = await adapter.place_futures_order(
            symbol="BTC_USDT",
            side="BUY",
            position_side="LONG",
            order_type="MARKET",
            quantity=0.1
        )

        # Execution price should differ slightly from market price
        # (slippage 0.01-0.1%)
        print(f"✅ MARKET order slippage applied")
        print(f"   Expected slippage range: 0.01-0.1%")

        # LIMIT order should have no slippage
        limit_order = await adapter.place_futures_order(
            symbol="BTC_USDT",
            side="SELL",
            position_side="SHORT",
            order_type="LIMIT",
            quantity=0.05,
            price=55000.0
        )

        assert limit_order["price"] == 55000.0, "LIMIT orders should have exact price"
        print(f"✅ LIMIT order has no slippage (exact price: ${limit_order['price']:.2f})")

asyncio.run(test_slippage())
```

#### Test 1.5: Funding Rate
```python
async def test_funding_rate():
    logger = get_logger("test")

    async with MexcPaperAdapter(logger, initial_balance=10000.0) as adapter:
        # Get funding rate
        funding_info = await adapter.get_funding_rate("BTC_USDT")

        assert "funding_rate" in funding_info
        assert "next_funding_time" in funding_info
        assert "mark_price" in funding_info

        print(f"✅ Funding rate retrieved:")
        print(f"   Rate: {funding_info['funding_rate'] * 100:.4f}%")
        print(f"   Mark Price: ${funding_info['mark_price']:.2f}")
        print(f"   Next Funding: {funding_info['next_funding_time']}")

        # Calculate funding cost
        cost = await adapter.calculate_funding_cost(
            symbol="BTC_USDT",
            position_amount=-0.1,  # SHORT 0.1 BTC
            holding_hours=24  # 24 hours = 3 funding intervals
        )

        print(f"✅ Funding cost calculated:")
        print(f"   Position: SHORT 0.1 BTC")
        print(f"   Holding: 24 hours")
        print(f"   Cost: ${cost:.2f}")

asyncio.run(test_funding_rate())
```

**Expected Result:**
```
✅ Funding rate retrieved:
   Rate: 0.0100%
   Mark Price: $50,000.00
   Next Funding: 2025-11-04T16:00:00
✅ Funding cost calculated:
   Position: SHORT 0.1 BTC
   Holding: 24 hours
   Cost: $-1.50  # Negative = you pay
```

---

### TEST 2: Database Persistence

**Objective:** Verify all QuestDB tables and CRUD operations

#### Test 2.1: Session Creation
```bash
# Create new paper trading session
curl -X POST http://localhost:8080/api/paper-trading/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "strat_pump_short_001",
    "strategy_name": "Pump Detection + SHORT",
    "symbols": ["BTC_USDT", "ETH_USDT"],
    "direction": "SHORT",
    "leverage": 3.0,
    "initial_balance": 10000.0,
    "notes": "Testing SHORT selling with 3x leverage"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "session_id": "paper_20251104_143022_a1b2c3d4",
  "message": "Paper trading session created successfully"
}
```

**Verify in QuestDB:**
```sql
-- Open http://127.0.0.1:9000
SELECT * FROM paper_trading_sessions
WHERE session_id = 'paper_20251104_143022_a1b2c3d4';

-- Should show:
-- session_id, strategy_name, symbols, direction=SHORT, leverage=3.0,
-- initial_balance=10000.0, status=RUNNING
```

#### Test 2.2: List Sessions
```bash
# List all sessions
curl http://localhost:8080/api/paper-trading/sessions

# Filter by strategy
curl "http://localhost:8080/api/paper-trading/sessions?strategy_id=strat_pump_short_001"

# Filter by status
curl "http://localhost:8080/api/paper-trading/sessions?status=RUNNING"
```

**Expected Response:**
```json
{
  "success": true,
  "sessions": [
    {
      "session_id": "paper_20251104_143022_a1b2c3d4",
      "strategy_name": "Pump Detection + SHORT",
      "symbols": "BTC_USDT,ETH_USDT",
      "direction": "SHORT",
      "leverage": 3.0,
      "initial_balance": 10000.0,
      "status": "RUNNING",
      "start_time": "2025-11-04T14:30:22.000000"
    }
  ],
  "count": 1
}
```

#### Test 2.3: Get Session Details
```bash
curl http://localhost:8080/api/paper-trading/sessions/paper_20251104_143022_a1b2c3d4
```

**Expected Response:**
```json
{
  "success": true,
  "session": {
    "session_id": "paper_20251104_143022_a1b2c3d4",
    "strategy_id": "strat_pump_short_001",
    "strategy_name": "Pump Detection + SHORT",
    "symbols": "BTC_USDT,ETH_USDT",
    "direction": "SHORT",
    "leverage": 3.0,
    "initial_balance": 10000.0,
    "final_balance": null,
    "total_pnl": 0.0,
    "total_trades": 0,
    "status": "RUNNING",
    "start_time": "2025-11-04T14:30:22.000000",
    "notes": "Testing SHORT selling with 3x leverage"
  }
}
```

#### Test 2.4: Record Order (Direct DB Test)
```python
async def test_record_order():
    from src.domain.services.paper_trading_persistence import PaperTradingPersistenceService
    from src.core.logger import get_logger

    logger = get_logger("test")
    persistence = PaperTradingPersistenceService(
        host="127.0.0.1",
        port=8812,
        user="admin",
        password="quest",
        logger=logger
    )

    await persistence.initialize()

    # Record order
    await persistence.record_order(
        session_id="paper_20251104_143022_a1b2c3d4",
        order_data={
            "order_id": "paper_00000001_test",
            "symbol": "BTC_USDT",
            "side": "SELL",
            "position_side": "SHORT",
            "type": "MARKET",
            "quantity": 0.1,
            "requested_price": 50000.0,
            "price": 49950.0,  # With slippage
            "slippage_pct": 0.1,
            "leverage": 3.0,
            "liquidation_price": 66600.0,
            "status": "FILLED",
            "commission": 5.0,
            "strategy_signal": "S1_pump_detected"
        }
    )

    print("✅ Order recorded to database")

    # Query orders
    orders = await persistence.get_session_orders("paper_20251104_143022_a1b2c3d4")
    assert len(orders) == 1
    assert orders[0]["order_id"] == "paper_00000001_test"

    print(f"✅ Order retrieved: {orders[0]['order_id']}")

    await persistence.close()

asyncio.run(test_record_order())
```

**Verify in QuestDB:**
```sql
SELECT * FROM paper_trading_orders
WHERE session_id = 'paper_20251104_143022_a1b2c3d4';
```

#### Test 2.5: Record Performance Metrics
```python
async def test_record_performance():
    from src.domain.services.paper_trading_persistence import PaperTradingPersistenceService
    from src.core.logger import get_logger

    logger = get_logger("test")
    persistence = PaperTradingPersistenceService(
        host="127.0.0.1",
        port=8812,
        user="admin",
        password="quest",
        logger=logger
    )

    await persistence.initialize()

    # Record performance snapshot
    await persistence.record_performance(
        session_id="paper_20251104_143022_a1b2c3d4",
        metrics={
            "current_balance": 10150.0,
            "total_pnl": 150.0,
            "total_return_pct": 1.5,
            "unrealized_pnl": 50.0,
            "realized_pnl": 100.0,
            "total_trades": 3,
            "winning_trades": 2,
            "losing_trades": 1,
            "win_rate": 0.667,
            "profit_factor": 2.5,
            "average_win": 75.0,
            "average_loss": -25.0,
            "largest_win": 100.0,
            "largest_loss": -25.0,
            "max_drawdown": 50.0,
            "current_drawdown": 0.0,
            "sharpe_ratio": 1.8,
            "sortino_ratio": 2.2,
            "calmar_ratio": 3.0,
            "open_positions": 1,
            "total_commission": 15.0,
            "total_funding_cost": 5.0
        }
    )

    print("✅ Performance metrics recorded")

    # Query performance
    performance = await persistence.get_session_performance("paper_20251104_143022_a1b2c3d4")
    assert len(performance) >= 1

    print(f"✅ Performance snapshots: {len(performance)}")

    await persistence.close()

asyncio.run(test_record_performance())
```

**Verify in QuestDB:**
```sql
SELECT * FROM paper_trading_performance
WHERE session_id = 'paper_20251104_143022_a1b2c3d4'
ORDER BY timestamp DESC;
```

#### Test 2.6: Stop Session
```bash
curl -X POST http://localhost:8080/api/paper-trading/sessions/paper_20251104_143022_a1b2c3d4/stop
```

**Expected Response:**
```json
{
  "success": true,
  "session_id": "paper_20251104_143022_a1b2c3d4",
  "message": "Session stopped successfully"
}
```

**Verify in QuestDB:**
```sql
SELECT session_id, status FROM paper_trading_sessions
WHERE session_id = 'paper_20251104_143022_a1b2c3d4';
-- status should be 'STOPPED'
```

---

### TEST 3: API Integration Testing

**Objective:** Test complete API workflow

#### Test 3.1: Full Session Lifecycle
```bash
#!/bin/bash

# 1. Create session
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8080/api/paper-trading/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "integration_test_001",
    "strategy_name": "Integration Test Strategy",
    "symbols": ["BTC_USDT"],
    "direction": "BOTH",
    "leverage": 2.0,
    "initial_balance": 5000.0
  }')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Created session: $SESSION_ID"

# 2. Get session details
curl -s http://localhost:8080/api/paper-trading/sessions/$SESSION_ID | jq

# 3. Stop session
curl -s -X POST http://localhost:8080/api/paper-trading/sessions/$SESSION_ID/stop | jq

# 4. Verify stopped
curl -s http://localhost:8080/api/paper-trading/sessions/$SESSION_ID | jq '.session.status'
# Should output: "STOPPED"

echo "✅ Full lifecycle test complete"
```

#### Test 3.2: Health Check
```bash
curl http://localhost:8080/api/paper-trading/health
```

**Expected Response:**
```json
{
  "success": true,
  "service": "paper-trading",
  "status": "healthy",
  "database": "connected"
}
```

---

## Integration Test Scenarios

### Scenario 1: Pump Detection + SHORT Strategy

**Setup:**
1. Create strategy with SHORT direction
2. Set leverage 3x
3. Initial balance: $10,000

**Steps:**
1. Detect pump (S1 triggered)
2. Open SHORT position 0.1 BTC @ $50,000
3. Price drops to $45,000
4. Close position (ZE1 triggered)
5. Calculate P&L

**Expected Results:**
- Entry: $50,000
- Exit: $45,000
- Price movement: -10%
- Quantity: 0.1 BTC
- P&L (without leverage): 0.1 × ($50,000 - $45,000) = +$500
- P&L (with 3x leverage): +$1,500 (3× profit)
- Return: 15%

---

## Error Handling Tests

### Test 4.1: Invalid Leverage
```bash
curl -X POST http://localhost:8080/api/paper-trading/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "test",
    "strategy_name": "Test",
    "symbols": ["BTC_USDT"],
    "leverage": 15.0
  }'
```

**Expected:** 422 Validation Error (leverage max 10.0)

### Test 4.2: Session Not Found
```bash
curl http://localhost:8080/api/paper-trading/sessions/nonexistent_session_id
```

**Expected:** 404 Not Found

### Test 4.3: Stop Non-Running Session
```bash
# First stop session
curl -X POST http://localhost:8080/api/paper-trading/sessions/$SESSION_ID/stop

# Try to stop again
curl -X POST http://localhost:8080/api/paper-trading/sessions/$SESSION_ID/stop
```

**Expected:** 400 Bad Request ("Session is not running")

---

## Performance Tests

### Test 5.1: Connection Pool Verification
```sql
-- In QuestDB console
-- Monitor active connections during load
-- Should stay between 2-10 connections

SELECT count(*) FROM pg_stat_activity WHERE datname = 'qdb';
```

### Test 5.2: Bulk Operations
```python
async def test_bulk_operations():
    # Create 10 sessions concurrently
    # Record 100 orders per session
    # Verify no connection pool exhaustion
    pass
```

---

## Known Limitations (TIER 1.2)

✅ **Implemented:**
- MexcPaperAdapter with full futures API
- QuestDB persistence (sessions, orders, positions, performance)
- REST API for session management
- Complete CRUD operations

⏳ **Not Yet Implemented (20% remaining):**
- ExecutionController integration for automated paper trading
- WebSocket real-time updates
- Frontend UI components (charts, order table)
- Live strategy execution in paper mode

---

## Success Criteria

✅ All TEST 1 cases pass (MexcPaperAdapter functionality)
✅ All TEST 2 cases pass (Database persistence)
✅ All TEST 3 cases pass (API integration)
✅ All TEST 4 cases pass (Error handling)
✅ Connection pool stays within 2-10 connections
✅ No SQL injection vulnerabilities
✅ All API endpoints return within 200ms
✅ QuestDB tables have proper indexes

---

## Next Steps After Testing

1. **Complete ExecutionController Integration**
   - Add paper trading mode to execution controller
   - Connect paper adapter to strategy manager
   - Implement automated signal → order flow

2. **Add WebSocket Events**
   - Broadcast order fills
   - Stream position updates
   - Push performance metrics

3. **Build Frontend UI**
   - Session management page
   - Real-time performance charts
   - Order history table
   - Position monitoring

4. **Documentation**
   - User guide for paper trading
   - Video tutorial
   - Example strategies

---

## Troubleshooting

### Issue: "Paper trading service not initialized"
**Solution:** Check server logs for initialization errors. Verify QuestDB is running.

### Issue: Connection pool exhausted
**Solution:** Check for unclosed connections. Verify `_release_connection` is called in finally blocks.

### Issue: Tables not found
**Solution:** Run migration 013. Verify in QuestDB console: `\dt paper_trading*`

### Issue: Orders not appearing
**Solution:** Check `paper_trading_orders` table. Verify session_id matches.

---

## Appendix

### A. Database Schema Verification
```sql
-- Verify all tables exist
SELECT table_name FROM information_schema.tables
WHERE table_name LIKE 'paper_trading%';

-- Expected output:
-- paper_trading_sessions
-- paper_trading_orders
-- paper_trading_positions
-- paper_trading_performance

-- Check table structure
SHOW COLUMNS FROM paper_trading_sessions;
```

### B. Performance Metrics Reference
```python
{
  "total_pnl": float,           # Total realized + unrealized P&L
  "total_return_pct": float,    # (total_pnl / initial_balance) * 100
  "win_rate": float,            # winning_trades / total_trades
  "profit_factor": float,       # total_wins / abs(total_losses)
  "max_drawdown": float,        # Maximum peak-to-trough decline
  "sharpe_ratio": float,        # Risk-adjusted return (annualized)
  "sortino_ratio": float,       # Downside risk-adjusted return
  "calmar_ratio": float         # Annual return / max drawdown
}
```

### C. API Reference
```
POST   /api/paper-trading/sessions              Create session
GET    /api/paper-trading/sessions              List sessions
GET    /api/paper-trading/sessions/{id}         Get session
GET    /api/paper-trading/sessions/{id}/perf... Get performance
GET    /api/paper-trading/sessions/{id}/orde... Get orders
POST   /api/paper-trading/sessions/{id}/stop    Stop session
DELETE /api/paper-trading/sessions/{id}         Delete session
GET    /api/paper-trading/health                Health check
```

---

**End of Testing Plan**
