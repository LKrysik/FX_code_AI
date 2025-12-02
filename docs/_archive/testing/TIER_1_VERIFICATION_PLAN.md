# TIER 1 Verification Testing Plan
**Date:** 2025-11-04
**Purpose:** Verify all TIER 1.1 + TIER 1.4 implementations and bug fixes
**Status:** Ready for Manual Testing
**Estimated Time:** 2-3 hours

---

## 🎯 Overview

Po naprawieniu krytycznych błędów (#1, #2, #3), system jest gotowy do kompleksowego testowania.

**Co zostało naprawione:**
- ✅ BŁĄD #1: Leverage data mapping (z1_entry.leverage → global_limits.max_leverage)
- ✅ BŁĄD #2: Live trading mode activation (live_trading_enabled field added)
- ✅ BŁĄD #3: Leverage validation (schema validator)

**Co wymaga testowania:**
- TIER 1.1: MEXC Futures Adapter + LiveOrderManager
- TIER 1.4: Leverage UI Controls
- Integration: Frontend → Backend → Trading Execution

---

## 📋 Prerequisites - Przed Rozpoczęciem Testów

### 1. Backend Setup
```bash
cd /home/user/FX_code_AI

# Activate virtual environment (if not using system Python)
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate  # Windows

# Verify Python packages
python -c "import fastapi, asyncpg, questdb.ingress; print('✅ All packages OK')"

# Start QuestDB (if not running)
# See: database/questdb/install_questdb.py
# Expected ports:
# - Web UI: http://127.0.0.1:9000
# - PostgreSQL: localhost:8812
# - ILP: localhost:9009

# Start backend server
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8080
INFO:     Application startup complete
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies (if needed)
npm install

# Start development server
npm run dev
```

**Expected Output:**
```
> frontend@0.1.0 dev
> next dev

ready - started server on 0.0.0.0:3000
```

### 3. Configuration Setup

**Option A: Paper Trading (Safe - Recommended for Initial Tests)**
```json
// config.json or use default settings
{
  "trading": {
    "mode": "backtest",
    "live_trading_enabled": false  // Paper mode
  }
}
```

**Option B: Live Trading (DANGEROUS - Only After Paper Tests Pass!)**
```json
// config.json
{
  "trading": {
    "mode": "live",
    "live_trading_enabled": true,  // ⚠️ REAL ORDERS!
    "max_position_size_usdt": 50   // Start small!
  },
  "exchanges": {
    "mexc_api_key": "YOUR_MEXC_API_KEY",
    "mexc_api_secret": "YOUR_MEXC_API_SECRET"
  }
}
```

**⚠️ CRITICAL:** Test on MEXC Testnet first if available!

---

## 🧪 Test Suite

### TEST GROUP 1: Backend Bug Fixes Verification

#### Test 1.1: Leverage Data Mapping (Bug #1 Fix)
**Purpose:** Verify z1_entry.leverage is mapped to global_limits.max_leverage

**Steps:**
```bash
# 1. Create test strategy via API
curl -X POST http://localhost:8080/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "test_leverage_mapping",
    "direction": "SHORT",
    "s1_signal": {"conditions": []},
    "z1_entry": {
      "conditions": [],
      "leverage": 3,
      "positionSize": {"type": "percentage", "value": 10}
    },
    "o1_cancel": {"timeoutSeconds": 60, "conditions": []},
    "ze1_close": {"conditions": []},
    "emergency_exit": {
      "conditions": [],
      "cooldownMinutes": 30,
      "actions": {"cancelPending": true, "closePosition": true, "logEvent": true}
    }
  }'

# 2. Check backend logs
# Expected: "api.strategy_leverage_mapped" with z1_leverage=3

# 3. Verify in QuestDB
# Navigate to http://127.0.0.1:9000
# Run query:
SELECT
    strategy_name,
    strategy_config->'z1_entry'->'leverage' as z1_leverage,
    strategy_config->'global_limits'->'max_leverage' as gl_leverage
FROM strategy_configs
WHERE strategy_name = 'test_leverage_mapping';
```

**Expected Results:**
- ✅ API returns 200 OK
- ✅ Backend log shows: `api.strategy_leverage_mapped z1_leverage=3 mapped_to=global_limits.max_leverage`
- ✅ QuestDB shows:
  ```
  z1_leverage: 3
  gl_leverage: 3  ← CRITICAL: This must be set!
  ```

**Pass Criteria:** Both z1_leverage AND gl_leverage are set to 3

---

#### Test 1.2: Leverage Validation (Bug #3 Fix)
**Purpose:** Verify schema validator rejects invalid leverage values

**Test Case 1.2a: Invalid Range (Too High)**
```bash
curl -X POST http://localhost:8080/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "test_invalid_leverage",
    "z1_entry": {
      "leverage": 11,
      "positionSize": {"type": "percentage", "value": 10}
    },
    ...
  }'
```

**Expected Result:**
- ❌ API returns 400 Bad Request
- Response body contains: `"z1_entry.leverage must be between 1 and 10"`

**Test Case 1.2b: Invalid Type**
```bash
curl -X POST http://localhost:8080/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "z1_entry": {
      "leverage": "abc",
      ...
    }
  }'
```

**Expected Result:**
- ❌ API returns 400 Bad Request
- Response body contains: `"z1_entry.leverage must be a number"`

**Test Case 1.2c: High Risk Warning**
```bash
curl -X POST http://localhost:8080/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "z1_entry": {
      "leverage": 6,
      ...
    }
  }'
```

**Expected Result:**
- ✅ API returns 200 OK (still valid)
- Response includes warning: `"z1_entry.leverage=6x is HIGH RISK"`

**Pass Criteria:** All three test cases produce expected results

---

#### Test 1.3: Live Trading Mode Activation (Bug #2 Fix)
**Purpose:** Verify live_trading_enabled setting works

**Test Case 1.3a: Paper Mode (Default)**
```bash
# 1. Ensure config has live_trading_enabled=false (or omit it)
# 2. Start backend with debugging:
python -c "
import asyncio
from src.infrastructure.container import Container
from src.infrastructure.config.settings import load_settings

async def test():
    settings = load_settings()
    container = Container(settings, None)
    order_manager = await container.create_order_manager()
    print(f'Order Manager Type: {type(order_manager).__name__}')
    print(f'Live Mode: {getattr(order_manager, \"is_live_mode\", False)}')

asyncio.run(test())
"
```

**Expected Output:**
```
Order Manager Type: OrderManager
Live Mode: False
```

**Test Case 1.3b: Live Mode**
```bash
# 1. Set config:
# config.json: {"trading": {"live_trading_enabled": true}}
# 2. Run same test
```

**Expected Output:**
```
Order Manager Type: LiveOrderManager  ← CRITICAL: Must be LiveOrderManager!
Live Mode: True
```

**Pass Criteria:**
- Paper mode → OrderManager
- Live mode → LiveOrderManager

---

### TEST GROUP 2: Frontend Leverage UI

#### Test 2.1: Leverage Dropdown Display
**Purpose:** Verify leverage UI appears in Strategy Builder

**Steps:**
1. Navigate to http://localhost:3000/strategy-builder
2. Click "Create New Strategy"
3. Set direction to SHORT
4. Scroll to Section Z1 (Entry)
5. Look for "⚡ Leverage (Futures Trading)" section

**Expected Results:**
- ✅ Leverage section appears after Position Size
- ✅ Dropdown shows 5 options:
  - 1x - No leverage (Safest)
  - 2x - Conservative
  - 3x - RECOMMENDED ⭐ (in green)
  - 5x - High risk ⚠️ (in orange)
  - 10x - EXTREME RISK 🔴 (in red)
- ✅ Default value is 1x

**Pass Criteria:** All UI elements render correctly

---

#### Test 2.2: Liquidation Price Calculation
**Purpose:** Verify real-time liquidation price updates

**Steps:**
1. In Strategy Builder, set direction to SHORT
2. Select leverage = 3x
3. Observe "Liquidation Price" display

**Expected Results:**
- ✅ Shows: "Liquidation Price (example @ $50,000 entry): $66,666.67 ↑"
- ✅ Distance: "33.3% from entry price"
- ✅ Risk Level: "HIGH" (yellow badge)
- ✅ Margin requirement: "33.3%"

**Test Different Leverages:**
| Leverage | Expected Liquidation | Distance | Risk Level |
|----------|---------------------|----------|------------|
| 1x | N/A | N/A | LOW |
| 2x | $75,000 ↑ | 50.0% | MODERATE |
| 3x | $66,667 ↑ | 33.3% | HIGH |
| 5x | $60,000 ↑ | 20.0% | HIGH |
| 10x | $55,000 ↑ | 10.0% | EXTREME |

**Pass Criteria:** All calculations match expected values

---

#### Test 2.3: Warning Banners
**Purpose:** Verify risk warnings appear correctly

**Test Case 2.3a: No Warnings (1x-3x)**
- Select leverage 1x, 2x, or 3x
- **Expected:** No warning banners (only info tip for 1x)

**Test Case 2.3b: High Leverage Warning (4x-5x)**
- Select leverage 5x
- **Expected:** Orange warning banner:
  ```
  High Leverage Warning! 5x leverage means your position will be
  liquidated if price moves just 20.0% upward.
  ```

**Test Case 2.3c: Extreme Risk Warning (6x-10x)**
- Select leverage 10x
- **Expected:** TWO banners:
  1. Orange warning (high leverage)
  2. Red error banner:
  ```
  EXTREME RISK! 10x leverage is NOT recommended for pump & dump
  strategies due to extreme volatility (±30-50% swings).
  ```

**Pass Criteria:** Correct warnings appear at correct thresholds

---

#### Test 2.4: Strategy Persistence
**Purpose:** Verify leverage saves and loads correctly

**Steps:**
1. Create strategy "test_leverage_3x" with leverage=3x
2. Fill all required sections (S1, Z1, O1, ZE1, E1)
3. Click "Save Strategy"
4. Wait for success message
5. Reload page
6. Load strategy "test_leverage_3x"

**Expected Results:**
- ✅ Strategy saves without errors
- ✅ After reload, strategy loads successfully
- ✅ Leverage dropdown shows "3x - RECOMMENDED ⭐"
- ✅ Liquidation price displays correctly

**Verification in Database:**
```sql
-- In QuestDB Web UI (http://127.0.0.1:9000)
SELECT
    strategy_name,
    strategy_config->'z1_entry'->'leverage' as leverage
FROM strategy_configs
WHERE strategy_name = 'test_leverage_3x';

-- Expected: leverage = 3
```

**Pass Criteria:** Leverage persists through save/load cycle

---

### TEST GROUP 3: End-to-End Integration

#### Test 3.1: Paper Trading with Leverage
**Purpose:** Verify leverage is used in order execution (paper mode)

**Steps:**
1. Ensure `live_trading_enabled = false`
2. Create strategy with leverage=3x
3. Activate strategy via API or UI
4. Trigger S1 signal (simulate market conditions)
5. Watch backend logs for order execution

**Expected Logs:**
```
strategy_manager.evaluating_signal strategy=test_leverage_3x
order_manager.paper_mode_submit_order symbol=BTC_USDT leverage=3.0  ← CRITICAL!
order_manager.position_updated leverage=3.0 liquidation_price=66666.67
```

**Verification:**
```bash
# Check position in OrderManager
curl http://localhost:8080/api/positions
```

**Expected Response:**
```json
{
  "positions": [
    {
      "symbol": "BTC_USDT",
      "quantity": -0.001,
      "leverage": 3.0,  ← CRITICAL: Must be 3, not 1!
      "liquidation_price": 66666.67
    }
  ]
}
```

**Pass Criteria:** leverage=3.0 in logs AND position data

---

#### Test 3.2: Live Trading with Leverage (MEXC Testnet)
**Purpose:** Verify leverage is set on MEXC exchange

**⚠️ WARNING:** Only proceed if you have MEXC testnet credentials or are comfortable with small real orders!

**Steps:**
1. Set `live_trading_enabled = true` in config.json
2. Add MEXC API credentials
3. Create strategy with leverage=3x, max_position_size=50 USDT
4. Activate strategy
5. Trigger order

**Expected Logs:**
```
container.creating_live_order_manager adapter_type=MexcFuturesAdapter
mexc_futures_adapter.set_leverage symbol=BTC_USDT leverage=3
mexc_futures_adapter.place_order side=SELL positionSide=SHORT
order_manager.live_order_submitted order_id=12345 leverage=3.0
```

**Verification on MEXC:**
1. Log in to MEXC account
2. Go to Futures → Positions
3. Check BTC_USDT position
4. **Expected:** Leverage = 3x

**Pass Criteria:**
- Order placed successfully
- Leverage set to 3x on MEXC
- Position visible in MEXC UI

---

### TEST GROUP 4: Error Handling

#### Test 4.1: Invalid Leverage Rejection
**Purpose:** Verify invalid leverage is rejected before execution

**Test Case 4.1a: Leverage Too High (API)**
```bash
curl -X POST http://localhost:8080/api/strategies \
  -d '{"z1_entry": {"leverage": 999}}'
```

**Expected:** 400 Bad Request, error message

**Test Case 4.1b: Leverage Too High (Direct DB Insert - Bypass Validation)**
```sql
-- Simulate attacker bypassing API validation
INSERT INTO strategy_configs (strategy_name, strategy_config)
VALUES ('malicious_strategy', '{"z1_entry": {"leverage": 100}}');
```

**Then try to execute strategy:**
- **Expected:** Strategy manager should validate before execution
- **Note:** This is a KNOWN GAP - no runtime validation in strategy_manager.py yet

**Test Case 4.1c: Missing Leverage (Default)**
```bash
# Create strategy WITHOUT leverage field
curl -X POST http://localhost:8080/api/strategies \
  -d '{"z1_entry": {"positionSize": {...}}}'  # No leverage
```

**Expected:**
- ✅ Strategy accepts (leverage is optional)
- ✅ Defaults to 1x (no leverage)
- ✅ Backend uses leverage=1.0

**Pass Criteria:** Invalid values rejected, defaults work correctly

---

## 📊 Test Results Template

```markdown
## Test Execution Results
**Date:** [YYYY-MM-DD]
**Tester:** [Name]
**Environment:** [Local/Staging/Production]

### GROUP 1: Backend Bug Fixes
- [ ] Test 1.1: Leverage Data Mapping
  - Status: PASS / FAIL
  - Notes: _____

- [ ] Test 1.2: Leverage Validation
  - Status: PASS / FAIL
  - Notes: _____

- [ ] Test 1.3: Live Trading Mode Activation
  - Status: PASS / FAIL
  - Notes: _____

### GROUP 2: Frontend Leverage UI
- [ ] Test 2.1: Leverage Dropdown Display
  - Status: PASS / FAIL
  - Notes: _____

- [ ] Test 2.2: Liquidation Price Calculation
  - Status: PASS / FAIL
  - Notes: _____

- [ ] Test 2.3: Warning Banners
  - Status: PASS / FAIL
  - Notes: _____

- [ ] Test 2.4: Strategy Persistence
  - Status: PASS / FAIL
  - Notes: _____

### GROUP 3: End-to-End Integration
- [ ] Test 3.1: Paper Trading with Leverage
  - Status: PASS / FAIL
  - Notes: _____

- [ ] Test 3.2: Live Trading with Leverage (OPTIONAL)
  - Status: PASS / FAIL / SKIPPED
  - Notes: _____

### GROUP 4: Error Handling
- [ ] Test 4.1: Invalid Leverage Rejection
  - Status: PASS / FAIL
  - Notes: _____

### Summary
- **Total Tests:** 10
- **Passed:** ___
- **Failed:** ___
- **Skipped:** ___
- **Overall Status:** PASS / FAIL
```

---

## 🐛 Known Issues to Monitor

### PROBLEM #4: Hardcoded $50,000 Entry Price (Not Fixed Yet)
**Impact:** Liquidation price display shows example for BTC, not actual symbol
**Severity:** LOW (informational only)
**Workaround:** User must mentally calculate for their symbol
**Fix Planned:** TIER 1.6 or later

### PROBLEM #5: Unbounded Leverage Cache (Not Fixed Yet)
**Impact:** Potential memory leak in long-running applications
**Severity:** LOW (typical usage < 100 symbols = < 5KB)
**Monitoring:** Check memory usage after 24h+ runtime
**Fix Planned:** Optional, may defer to later sprint

---

## 🎯 Success Criteria

**Minimum Criteria (Must Pass to Proceed):**
- ✅ Test 1.1: Leverage mapping works
- ✅ Test 1.2: Validation rejects invalid values
- ✅ Test 2.4: Strategy persistence works
- ✅ Test 3.1: Paper trading uses correct leverage

**Recommended Criteria (Should Pass):**
- ✅ All GROUP 2 tests (Frontend UI)
- ✅ Test 1.3: Live mode activation

**Optional Criteria (Nice to Have):**
- ✅ Test 3.2: Live trading on testnet
- ✅ Test 4.1: Comprehensive error handling

---

## 📝 Next Steps After Testing

### If All Tests PASS:
1. ✅ Mark TIER 1.1 + TIER 1.4 as COMPLETE
2. ✅ Update STATUS.md with completion date
3. ✅ Proceed to TIER 1.2 (Paper Trading Engine)
4. ✅ Consider deploying to staging environment

### If Tests FAIL:
1. ❌ Document failure in test results
2. ❌ Create bug report with reproduction steps
3. ❌ Fix bugs before proceeding
4. ❌ Re-run failed tests
5. ❌ DO NOT proceed to TIER 1.2 until all critical tests pass

---

## 🔗 Related Documentation

- **Bug Analysis:** `docs/reviews/TIER_1_ERROR_ANALYSIS.md`
- **Code Review:** `docs/reviews/TIER_1_CODE_REVIEW.md`
- **MEXC Adapter:** `src/infrastructure/adapters/mexc_futures_adapter.py`
- **LiveOrderManager:** `src/domain/services/order_manager_live.py`
- **Leverage Calculator:** `frontend/src/utils/leverageCalculator.ts`
- **Strategy Schema:** `src/domain/services/strategy_schema.py`

---

**Testing Plan Prepared By:** Claude Code Review System
**Date:** 2025-11-04
**Version:** 1.0
**Estimated Testing Time:** 2-3 hours (depending on environment setup)
