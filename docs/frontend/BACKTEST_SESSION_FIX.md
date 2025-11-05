# Backtest Session ID Fix - Complete Implementation

**Date:** 2025-11-05
**Status:** ✅ Completed
**Issue:** Backtest requests were failing with "session_id parameter is required for backtest"

---

## 🎯 **Problem Overview**

### **Original Issue**
Backtest functionality was broken due to missing `session_id` parameter:

```
POST /sessions/start
{
  "session_type": "backtest",
  "symbols": ["BTC_USDT"],
  "config": {
    "acceleration_factor": 10
    // ❌ Missing: session_id
  }
}
```

**Backend Response:**
```
HTTP 400 Bad Request
{
  "error_message": "session_id parameter is required for backtest.
                    Specify the data collection session to replay for backtesting.
                    Use GET /api/data-collection/sessions to list available sessions."
}
```

### **Root Causes**

1. **Frontend API Service** - `startBacktest()` didn't accept or send `session_id`
2. **Backtesting Page** - Used mock data instead of real sessions from QuestDB
3. **No UI Component** - No way for users to select a data collection session
4. **Backend Validation** - Error occurred late (execution phase) instead of early (validation phase)

---

## ✅ **Complete Solution**

### **1. Backend Fix** (`src/application/services/command_processor.py`)

**Added session_id validation in `_validate_start_backtest()`:**

```python
async def _validate_start_backtest(self, parameters: Dict[str, Any]) -> CommandValidationResult:
    errors = []
    warnings = []

    # ✅ CRITICAL FIX: Validate session_id is present
    if "session_id" not in parameters or not parameters["session_id"]:
        errors.append(
            "session_id parameter is required for backtest. "
            "Specify the data collection session to replay for backtesting. "
            "Use GET /api/data-collection/sessions to list available sessions."
        )

    # ... rest of validation
```

**Benefits:**
- Fail-fast: error caught in validation phase (before lock acquisition)
- Better error messaging
- Resource efficiency (no wasted CPU/locks)
- Architectural coherence (validators check ALL required parameters)

---

### **2. Frontend API Service** (`frontend/src/services/api.ts`)

**Updated `startBacktest()` signature:**

```typescript
/**
 * Start a backtest session
 *
 * @param symbols - List of trading symbols to backtest
 * @param sessionId - Data collection session ID to replay (REQUIRED)
 * @param config - Additional configuration
 */
async startBacktest(symbols: string[], sessionId: string, config: any = {}): Promise<any> {
  if (!sessionId) {
    throw new Error(
      'session_id is required for backtest. ' +
      'Please select a data collection session to replay. ' +
      'Use getDataCollectionSessions() to list available sessions.'
    );
  }

  const response = await axios.post<ApiResponse>('/sessions/start', {
    session_type: 'backtest',
    symbols: symbols,
    strategy_config: config.strategy_config || {},
    config: {
      session_id: sessionId,  // ✅ CRITICAL: Pass session_id to backend
      acceleration_factor: config.acceleration_factor || 10,
      ...config
    }
  });
  return response.data;
}
```

**Changes:**
- Added `sessionId` parameter (required)
- Frontend validation (throws error if missing)
- Passes `session_id` in `config` object to backend

---

### **3. SessionSelector Component** (`frontend/src/components/backtest/SessionSelector.tsx`)

**New React component with advanced features:**

```typescript
<SessionSelector
  value={selectedSessionId}
  onChange={(sessionId) => setSelectedSessionId(sessionId)}
  requiredSymbols={['BTC_USDT', 'ETH_USDT']}
  minRecords={1000}
  autoRefresh={true}
  refreshInterval={30000}
/>
```

**Features:**

#### **Real-time Session Loading**
- Fetches sessions from `GET /api/data-collection/sessions`
- Auto-refresh every 30 seconds (configurable)
- Shows only completed sessions with data

#### **Session Preview**
```
┌─────────────────────────────────────────────────────────┐
│ Selected Session Preview                                │
├─────────────────────────────────────────────────────────┤
│ Session ID: dc_20251105_203000_xyz                     │
│ Status: ✓ completed                                    │
│ Total Records: 15,234                                  │
│ Duration: 30 minutes                                   │
│ Symbols: BTC_USDT, ETH_USDT, ADA_USDT                │
│ Collection Date: Nov 5, 2025, 8:30 PM                 │
│                                                        │
│ ✓ Session data quality is good. Ready for backtesting.│
└─────────────────────────────────────────────────────────┘
```

#### **Quality Validation**
- **Good** ✓: Sufficient records, recent data, all symbols present
- **Warning** ⚠: Low records, missing some symbols, old data (>30 days)
- **Error** ❌: Too few records (below minimum threshold)

#### **Search/Filter**
- Filter by session ID
- Filter by symbols
- Filter by collection date
- Real-time search as you type

#### **Visual Indicators**
```typescript
// Quality icons
✓ Good quality (green checkmark)
⚠ Warning (yellow warning icon)
❌ Error (red error icon)

// Stats chips
[🗄️ 15,234 records] [📊 3 symbols] [📅 30min]
```

---

### **4. Backtesting Page Update** (`frontend/src/app/backtesting/page.tsx`)

**Replaced mock data with real session selection:**

```typescript
// ❌ OLD: Mock data
const mockDataSources = [
  { session_id: 'session_20250909_130028_8eb70dba', ... }
];

// ✅ NEW: Real session selector
const [selectedDataSession, setSelectedDataSession] = useState<string>('');

<SessionSelector
  value={selectedDataSession}
  onChange={setSelectedDataSession}
  requiredSymbols={backtestForm.symbols}
  minRecords={1000}
/>
```

**Updated `handleCreateBacktest()`:**

```typescript
const handleCreateBacktest = async () => {
  // ✅ Validate session_id is selected
  if (!selectedDataSession) {
    setSnackbar({
      open: true,
      message: 'Please select a data collection session',
      severity: 'error'
    });
    return;
  }

  // ✅ Pass session_id to API
  const response = await apiService.startBacktest(
    backtestForm.symbols,
    selectedDataSession,  // ✅ CRITICAL
    {
      strategy_config: selectedStrategy,
      acceleration_factor: backtestForm.acceleration_factor,
      budget: backtestForm.config.budget
    }
  );

  // Handle response...
};
```

**Removed obsolete fields:**
- ❌ `start_date` / `end_date` (not needed - session defines time range)
- ❌ `timeframe` (not needed - data is tick-level)
- ❌ `data_sources` array (replaced with single `selectedDataSession`)

**Added new fields:**
- ✅ `acceleration_factor` (playback speed multiplier)

---

### **5. E2E Tests** (`tests_e2e/api/test_backtest_session_flow.py`)

**Complete flow test:**

```python
async def test_complete_backtest_flow_with_session_id(api_client):
    """
    Tests entire flow:
    1. Collect data → POST /sessions/start (session_type=collect)
    2. List sessions → GET /api/data-collection/sessions
    3. Start backtest → POST /sessions/start with session_id
    4. Verify backtest runs successfully
    """
    # Step 1: Start data collection
    collect_response = await api_client.post('/sessions/start', ...)
    session_id = collect_response.json()['data']['data']['session_id']

    # Step 2: List sessions
    sessions_response = await api_client.get('/api/data-collection/sessions')
    assert session_id in [s['session_id'] for s in sessions_response.json()['sessions']]

    # Step 3: Start backtest with session_id
    backtest_response = await api_client.post('/sessions/start', json={
        'session_type': 'backtest',
        'config': {
            'session_id': session_id,  # ✅ CRITICAL
            ...
        }
    })

    assert backtest_response.status_code == 200  # ✅ Success!
```

**Validation tests:**
- Test backtest WITHOUT session_id → Fails with clear error ✅
- Test backtest with INVALID session_id → Fails appropriately ✅

---

## 📊 **Architecture Improvements**

### **Before**
```
User clicks "Start Backtest" (no session selection)
  ↓
Frontend sends request WITHOUT session_id
  ↓
Backend validates: ✅ OK (missing validation!)
  ↓
Backend acquires resource locks
  ↓
Backend executor: ❌ FAILS "session_id required"
  ↓
Resources wasted, poor error message
```

### **After**
```
User selects data collection session (SessionSelector)
  ↓
Frontend validates: session_id present?
  ↓
Frontend sends request WITH session_id
  ↓
Backend validates: ✅ session_id present
  ↓
Backend executes backtest successfully
  ↓
User sees results
```

---

## 🎨 **User Experience Improvements**

### **Before**
1. ❌ No way to select historical data
2. ❌ Error message unclear
3. ❌ No data preview
4. ❌ No quality validation

### **After**
1. ✅ Clear session selector with search
2. ✅ Real-time session list from QuestDB
3. ✅ Rich data preview (records, symbols, duration)
4. ✅ Quality validation (good/warning/error)
5. ✅ Auto-refresh (sessions update automatically)
6. ✅ Visual feedback (icons, chips, progress)
7. ✅ Clear error messages with instructions

---

## 🧪 **Testing Guide**

### **Manual Testing**

**Prerequisites:**
1. QuestDB running (`python database/questdb/install_questdb.py`)
2. Backend running (`python -m uvicorn src.api.unified_server:create_unified_app --factory --port 8080`)
3. Frontend running (`cd frontend && npm run dev`)

**Test Steps:**

**Step 1: Collect Data**
```bash
# Navigate to Data Collection page
http://localhost:3000/data-collection

# Click "Start Collection"
# Select symbols: BTC_USDT, ETH_USDT
# Duration: 30 seconds
# Click "Start"

# Wait for completion (progress bar shows 100%)
# Note the session_id (e.g., dc_20251105_203000_xyz)
```

**Step 2: Start Backtest**
```bash
# Navigate to Backtesting page
http://localhost:3000/backtesting

# Click "New Backtest"

# Dialog opens:
# 1. Select symbols: BTC_USDT, ETH_USDT
# 2. Select strategy: (any strategy)
# 3. Select data session: dc_20251105_203000_xyz
#    → Should see session preview with stats
#    → Quality indicator: ✓ Good
# 4. Acceleration factor: 10
# 5. Budget: 10000

# Click "Start Backtest"

# ✅ SUCCESS: Backtest starts (no error!)
# ✅ See backtest in sessions table
# ✅ Status: "running"
```

**Step 3: Verify Results**
```bash
# Wait for backtest to complete
# Check execution status
# View results

# ✅ Backtest completed successfully
```

---

### **Automated Testing**

```bash
# Run E2E tests
python run_tests.py --api

# Or run specific test file
pytest tests_e2e/api/test_backtest_session_flow.py -v -s

# Expected output:
# ✅ test_complete_backtest_flow_with_session_id PASSED
# ✅ test_backtest_without_session_id_fails_validation PASSED
# ✅ test_backtest_with_invalid_session_id_fails PASSED
```

---

## 📁 **Files Changed**

### **Backend**
- `src/application/services/command_processor.py` - Added session_id validation
- `src/api/unified_server.py` - Added architectural documentation

### **Frontend**
- `frontend/src/services/api.ts` - Updated `startBacktest()` signature
- `frontend/src/app/backtesting/page.tsx` - Replaced mock data, integrated SessionSelector
- `frontend/src/components/backtest/SessionSelector.tsx` - **NEW** component

### **Tests**
- `tests_e2e/api/test_backtest_session_flow.py` - **NEW** E2E tests
- `tests_e2e/fixtures/sessions.json` - Updated backtest fixture format

### **Documentation**
- `docs/frontend/BACKTEST_SESSION_FIX.md` - **NEW** (this file)

---

## 🚀 **Next Steps (Future Enhancements)**

### **Completed ✅**
- [x] Backend validation fix
- [x] Frontend API update
- [x] SessionSelector component
- [x] Backtesting page integration
- [x] E2E tests
- [x] Documentation

### **Future Enhancements 🎯**
- [ ] Session data visualization (price charts, volume distribution)
- [ ] Multi-session backtest (test across multiple data sessions)
- [ ] Session quality scoring algorithm
- [ ] Advanced filters (date range, symbol count, data types)
- [ ] Session comparison (compare multiple sessions before selecting)
- [ ] Export session metadata (download session info as JSON)
- [ ] Session tags/labels (organize sessions by market conditions)

---

## 🔗 **Related Documentation**

- Backend validation: `docs/architecture/VALIDATION.md`
- QuestDB schema: `docs/database/QUESTDB.md`
- API reference: `docs/api/REST.md`
- Testing guide: `QUICK_START_TESTS.md`

---

## 📞 **Support**

If you encounter issues with backtest session selection:

1. **Check QuestDB is running:**
   ```bash
   curl http://127.0.0.1:9000/exec -G \
     --data-urlencode "query=SELECT COUNT(*) FROM data_collection_sessions;"
   ```

2. **Verify sessions exist:**
   ```bash
   curl http://localhost:8080/api/data-collection/sessions | jq
   ```

3. **Check browser console:**
   - Open DevTools (F12)
   - Look for errors in Console tab
   - Check Network tab for API call responses

4. **Check backend logs:**
   - Look for validation errors
   - Check for QuestDB connection issues

---

**Status:** ✅ Production Ready
**Last Updated:** 2025-11-05
**Author:** Claude (Anthropic AI Assistant)
