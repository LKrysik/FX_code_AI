# Session Separation Fix - Implementation Summary
## Date: 2025-12-17
## Related: AUDIT_FINAL_REPORT.md - Issue #2 & #5

---

## **Problem Statement**

Backtest sessions were **invisible in the frontend** because:
1. `TradingPersistenceService` saved signals/orders/positions without `session_id`
2. `UnifiedTradingController.start_backtest` didn't create session record in `paper_trading_sessions`
3. Frontend queried `/api/paper-trading/sessions` which only showed paper trading sessions

**Impact:** Users could run backtests, but couldn't see results in Session History page.

---

## **Implementation**

### **1. Database Schema Migration** ✅
**File:** `migrations/add_session_id_to_trading_tables.sql`

Added `session_id SYMBOL` column to:
- `strategy_signals`
- `orders`
- `positions`

Created indexes for performance:
```sql
CREATE INDEX IF NOT EXISTS idx_strategy_signals_session_id ON strategy_signals(session_id);
CREATE INDEX IF NOT EXISTS idx_orders_session_id ON orders(session_id);
CREATE INDEX IF NOT EXISTS idx_positions_session_id ON positions(session_id);
```

**Action Required:** Run migration manually:
```bash
psql -h 127.0.0.1 -p 8812 -U admin -d qdb -f migrations/add_session_id_to_trading_tables.sql
```

---

### **2. TradingPersistenceService Updates** ✅
**File:** `src/domain/services/trading_persistence.py`

**Changes:**
- Added `session_id` parameter to `__init__` (line 54)
- Store `session_id` as instance variable (line 77)
- Updated all INSERT queries to include `session_id`:
  - `_on_signal_generated` (lines 233-251)
  - `_on_order_created` (lines 323-347)
  - `_on_position_opened` (lines 500-528)

**Example:**
```python
INSERT INTO strategy_signals (..., session_id) 
VALUES ($1, ..., $10)
```

---

### **3. Container Factory Updates** ✅
**File:** `src/infrastructure/container.py`

**Changes:**
1. **`create_trading_persistence_service`** (lines 458-512):
   - Added `session_id` parameter
   - Pass `session_id` to `TradingPersistenceService` constructor
   - Update `session_id` on existing singleton when called with new session

2. **`create_paper_trading_persistence_service`** (lines 550-576):
   - NEW METHOD: Creates `PaperTradingPersistenceService` singleton
   - Manages `paper_trading_sessions` table
   - Used for session CRUD operations

3. **`create_unified_trading_controller`** (lines 1107-1121):
   - Inject `paper_trading_persistence` into controller
   - Enables backtest session creation

---

### **4. UnifiedTradingController Updates** ✅
**File:** `src/application/controllers/unified_trading_controller.py`

**Changes:**
1. **Constructor** (lines 25-56):
   - Added `paper_trading_persistence` parameter
   - Store as instance variable

2. **`start_backtest`** (lines 322-370):
   - Update `TradingPersistenceService.session_id` after session creation
   - Create session record in `paper_trading_sessions` table
   - Extract strategy info from kwargs
   - Handle errors gracefully (don't fail backtest if session creation fails)

**Code:**
```python
# Update persistence service
if self.trading_persistence_service:
    self.trading_persistence_service.session_id = session_id

# Create session record
if self.paper_trading_persistence:
    await self.paper_trading_persistence.create_session({
        "session_id": session_id,
        "strategy_name": strategy_name,
        "symbols": symbols,
        ...
    })
```

---

## **Testing Checklist**

### **Manual Testing**
- [ ] Run database migration
- [ ] Start backend server
- [ ] Create backtest via `/api/backtesting/start`
- [ ] Verify session appears in `/api/paper-trading/sessions`
- [ ] Check `strategy_signals` table has `session_id` populated
- [ ] Check `orders` table has `session_id` populated
- [ ] Check `positions` table has `session_id` populated
- [ ] Verify frontend Session History page shows backtest

### **SQL Verification**
```sql
-- Check schema
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'strategy_signals';

-- Check data
SELECT session_id, COUNT(*) 
FROM strategy_signals 
GROUP BY session_id;

-- Check session record
SELECT * FROM paper_trading_sessions 
WHERE created_by = 'backtest';
```

---

## **Known Limitations**

1. **Migration Required:** Schema changes need manual execution
2. **Singleton Pattern:** `TradingPersistenceService` is singleton with mutable `session_id`
   - **Risk:** Concurrent sessions could overwrite each other's `session_id`
   - **Mitigation:** Only one active session at a time (enforced by `ExecutionController`)
3. **No Batch Inserts:** Still using individual INSERTs (see AUDIT_FINAL_REPORT.md Issue #1)

---

## **Next Steps**

1. **HIGH PRIORITY:** Run database migration
2. **MEDIUM:** Test backtest session visibility
3. **LOW:** Consider per-session `TradingPersistenceService` instances (remove singleton)
4. **LOW:** Implement batch inserts for high-frequency backtests

---

## **Rollback Plan**

If issues occur:
1. Revert `TradingPersistenceService` changes (remove `session_id` parameter)
2. Revert `UnifiedTradingController.start_backtest` changes
3. Drop `session_id` columns:
```sql
ALTER TABLE strategy_signals DROP COLUMN session_id;
ALTER TABLE orders DROP COLUMN session_id;
ALTER TABLE positions DROP COLUMN session_id;
```
