# Backend Endpoint Analysis for Session Configuration

**Date:** 2025-11-18
**Purpose:** Analyze existing endpoints vs required endpoints for session configuration UI
**Status:** ✅ Analysis Complete - Most endpoints exist, minor enhancements needed

---

## Executive Summary

### ✅ Good News: Most Endpoints Already Exist!

The backend already has **90% of the required endpoints** for session configuration. Only minor enhancements are needed:

1. **GET /api/strategies** - ✅ **EXISTS** (line 885-902 in unified_server.py)
2. **GET /symbols** - ✅ **EXISTS** (line 1741-1762 in unified_server.py)
3. **GET /api/data-collection/sessions** - ✅ **EXISTS** (data_analysis_routes.py:304-326)
4. **POST /sessions/start** - ✅ **EXISTS** with full config support (line 1942-2068 in unified_server.py)
5. **POST /sessions/stop** - ✅ **EXISTS** (line 2070-2152 in unified_server.py)

### ⚠️ Minor Gaps Identified:

1. **GET /api/exchange/symbols** - MISSING (need real-time exchange symbol data with prices)
2. **Strategy metadata** - EXISTS but may need enhancement for win_rate/avg_profit stats
3. **Session configuration validation** - Partially exists, could be enhanced

---

## Detailed Endpoint Inventory

### 1. GET /api/strategies ✅ EXISTS

**Location:** [src/api/unified_server.py:885-902](../../src/api/unified_server.py#L885-L902)

**Purpose:** List all available strategies from QuestDB
**Authentication:** Required (JWT)
**Response Format:**
```json
{
  "type": "response",
  "data": {
    "strategies": [
      {
        "id": "pump_v2",
        "strategy_name": "Pump Detection v2",
        "description": "Detects rapid price increases...",
        "direction": "long",
        "enabled": true,
        "category": "momentum",
        "tags": ["pump", "velocity"],
        "created_at": "2025-11-18T12:00:00Z",
        "updated_at": "2025-11-18T12:00:00Z"
      }
    ]
  }
}
```

**Implementation:**
- Uses `QuestDBStrategyStorage` to read from `strategies` table
- Supports authentication via `Depends(get_current_user)`
- Returns all non-deleted strategies

**Enhancements Needed:**
- ❌ **Missing fields:** `winRate`, `avgProfit` (for UI display)
- ✅ Solution: Query backtest_results table and join with strategies

**Action:** Enhance response to include performance metrics

---

### 2. GET /symbols ✅ EXISTS (Partial)

**Location:** [src/api/unified_server.py:1741-1762](../../src/api/unified_server.py#L1741-L1762)

**Purpose:** Get available trading symbols from config.json
**Authentication:** Not required
**Response Format:**
```json
{
  "type": "response",
  "data": {
    "symbols": ["BTC_USDT", "ETH_USDT", "ADA_USDT"]
  }
}
```

**Implementation:**
- Reads from `config/config.json` → `trading.default_symbols`
- Fallback to container settings if file not found
- Simple list of symbol names only

**Limitations:**
- ❌ **No price data** - frontend mockup shows prices
- ❌ **No volume/24h change** - no market metadata
- ❌ **Static config** - not from live exchange

**Action:** Create new endpoint `GET /api/exchange/symbols` with live data

---

### 3. GET /api/data-collection/sessions ✅ EXISTS

**Location:** [src/api/data_analysis_routes.py:304-326](../../src/api/data_analysis_routes.py#L304-L326)

**Purpose:** List available data collection sessions for backtesting
**Authentication:** Not required
**Response Format:**
```json
{
  "sessions": [
    {
      "session_id": "session_20251118_120530_abc123",
      "symbols": ["BTC_USDT", "ETH_USDT"],
      "data_types": ["tick_prices", "orderbook"],
      "status": "completed",
      "start_time": "2025-11-18T12:05:30Z",
      "end_time": "2025-11-18T13:05:30Z",
      "records_collected": 125000,
      "duration": "1h"
    }
  ],
  "total_count": 10,
  "limit": 50
}
```

**Implementation:**
- Queries `data_collection_sessions` table in QuestDB
- Supports pagination (`limit` parameter)
- Optional `include_stats` for additional metadata

**Status:** ✅ Fully functional, no changes needed

---

### 4. POST /sessions/start ✅ EXISTS (Full Config Support)

**Location:** [src/api/unified_server.py:1942-2068](../../src/api/unified_server.py#L1942-L2068)

**Purpose:** Start live/paper/backtest session with full configuration
**Authentication:** Required (JWT + CSRF)
**Request Format:**
```json
{
  "session_type": "paper",
  "symbols": ["BTC_USDT", "ETH_USDT"],
  "strategy_config": {
    "strategies": ["pump_v2", "dump_v2"]
  },
  "config": {
    "budget": {
      "global_cap": 1000,
      "allocations": {}
    },
    "stop_loss_percent": 5.0,
    "take_profit_percent": 10.0,
    "session_id": "session_20251118...",  // For backtest only
    "acceleration_factor": 10  // For backtest only
  },
  "idempotent": true
}
```

**Response Format:**
```json
{
  "type": "response",
  "data": {
    "status": "session_started",
    "data": {
      "session_id": "exec_20251118_150123_xyz789",
      "session_type": "paper",
      "symbols": ["BTC_USDT", "ETH_USDT"]
    }
  }
}
```

**Implementation:**
- Line 1948-1972: Parameter extraction and symbol resolution
- Line 1973-1987: Stop existing session and wait for cleanup
- Line 1989-2005: Budget validation
- Line 2007-2021: Trading mode configuration
- Line 2024-2043: Dispatch to backtest/collect/live handlers

**Key Features:**
- ✅ **Strategy selection** - via `strategy_config.strategies` array
- ✅ **Symbol selection** - via `symbols` array
- ✅ **Budget config** - via `config.budget`
- ✅ **Risk params** - via `config.stop_loss_percent`, `take_profit_percent`
- ✅ **Backtest params** - via `config.session_id`, `config.acceleration_factor`
- ✅ **Idempotent** - prevents duplicate sessions

**Status:** ✅ Fully functional, supports ALL required configuration options

**Frontend Integration:** Can use directly without modification

---

### 5. POST /sessions/stop ✅ EXISTS

**Location:** [src/api/unified_server.py:2070-2152](../../src/api/unified_server.py#L2070-L2152)

**Purpose:** Stop active session
**Authentication:** Required (JWT + CSRF)
**Request Format:**
```json
{
  "session_id": "exec_20251118_150123_xyz789"
}
```

**Response Format:**
```json
{
  "type": "response",
  "data": {
    "status": "session_stopped",
    "data": {
      "session_id": "exec_20251118_150123_xyz789"
    }
  }
}
```

**Implementation:**
- Validates `session_id` required
- Stops via execution controller
- Fallback to QuestDB direct update for orphaned sessions
- Returns proper error codes (400, 404, 409, 500)

**Status:** ✅ Fully functional

---

## Missing Endpoints

### 1. GET /api/exchange/symbols ❌ MISSING

**Required By:** Frontend mockup (MOCK_SYMBOLS)
**Purpose:** Get tradeable symbols with real-time market data

**Expected Response:**
```json
{
  "type": "response",
  "data": {
    "symbols": [
      {
        "symbol": "BTC_USDT",
        "name": "Bitcoin",
        "price": 50250.00,
        "volume24h": 1250000000,
        "change24h": 2.5,
        "high24h": 51000.00,
        "low24h": 49500.00
      },
      {
        "symbol": "ETH_USDT",
        "name": "Ethereum",
        "price": 3050.00,
        "volume24h": 850000000,
        "change24h": -1.2,
        "high24h": 3100.00,
        "low24h": 3000.00
      }
    ]
  }
}
```

**Implementation Plan:**
1. Create new route in `unified_server.py`
2. Query MEXC exchange API for symbol list
3. Fetch 24h ticker data for each symbol
4. Combine and format response
5. Add caching (5-minute TTL) to reduce API calls

**Alternatives:**
- Use existing `GET /symbols` and enhance it
- Create separate `/api/exchange/tickers` endpoint
- Query QuestDB for recent prices instead of exchange

**Recommendation:** Create `/api/exchange/symbols` with 5-minute cache

---

## Architecture Analysis

### Current Session Start Flow

```
Frontend (trading-session/page.tsx)
  ↓
POST /sessions/start
  ↓
unified_server.py:post_sessions_start() [Line 1942]
  ↓
ExecutionController (via app.state.rest_service)
  ↓
Dispatch by session_type:
  - backtest → controller.start_backtest()
  - collect → controller.start_data_collection()
  - live/paper → controller.start_live_trading()
  ↓
Strategy activation via strategy_config.strategies
  ↓
Symbol subscription via symbols array
  ↓
EventBus publishes session_started event
  ↓
WebSocket broadcasts to connected clients
  ↓
Response: session_id
```

### Strategy Selection Flow

```
Frontend: Select strategies from table
  ↓
Strategy IDs: ["pump_v2", "dump_v2"]
  ↓
POST /sessions/start with:
  strategy_config: {
    strategies: ["pump_v2", "dump_v2"]
  }
  ↓
unified_server.py extracts strategy_config [Line 1953]
  ↓
ExecutionController receives strategy_config
  ↓
StrategyManager.activate_strategies()
  ↓
Strategies loaded from QuestDB strategies table
  ↓
Indicator subscriptions created for each strategy
  ↓
EventBus: strategy_activated events
```

### Symbol Selection Flow

```
Frontend: Select symbols from chip interface
  ↓
Symbol array: ["BTC_USDT", "ETH_USDT"]
  ↓
POST /sessions/start with:
  symbols: ["BTC_USDT", "ETH_USDT"]
  ↓
unified_server.py extracts symbols [Line 1958]
  ↓
Symbol resolution logic [Line 1959-1971]:
  1. Explicit symbols (if provided)
  2. Derive from strategy_config values
  3. Fallback to settings.trading.default_symbols
  ↓
ExecutionController receives resolved symbols
  ↓
MarketDataProvider subscribes to symbols
  ↓
EventBus: market_data events for each symbol
```

---

## Integration Requirements for Frontend

### Required Changes to trading-session/page.tsx

**1. Replace MOCK_STRATEGIES with real API:**

```typescript
// REMOVE:
const MOCK_STRATEGIES = [...];

// ADD:
const [strategies, setStrategies] = useState<Strategy[]>([]);
const [strategiesLoading, setStrategiesLoading] = useState(true);

useEffect(() => {
  const fetchStrategies = async () => {
    try {
      setStrategiesLoading(true);
      const response = await fetch('http://localhost:8080/api/strategies', {
        headers: {
          'Authorization': `Bearer ${authToken}`  // TODO: Get from auth context
        }
      });
      const data = await response.json();
      if (data.type === 'response') {
        setStrategies(data.data.strategies);
      }
    } catch (error) {
      console.error('Failed to load strategies:', error);
    } finally {
      setStrategiesLoading(false);
    }
  };

  fetchStrategies();
}, []);
```

**2. Replace MOCK_SYMBOLS with real API:**

```typescript
// REMOVE:
const MOCK_SYMBOLS = [...];

// ADD:
const [symbols, setSymbols] = useState<Symbol[]>([]);
const [symbolsLoading, setSymbolsLoading] = useState(true);

useEffect(() => {
  const fetchSymbols = async () => {
    try:
      setSymbolsLoading(true);
      // Use new exchange endpoint (once created)
      const response = await fetch('http://localhost:8080/api/exchange/symbols');
      const data = await response.json();
      if (data.type === 'response') {
        setSymbols(data.data.symbols);
      }
    } catch (error) {
      console.error('Failed to load symbols:', error);
      // Fallback to config symbols
      const fallbackResponse = await fetch('http://localhost:8080/symbols');
      const fallbackData = await fallbackResponse.json();
      if (fallbackData.type === 'response') {
        setSymbols(fallbackData.data.symbols.map(s => ({ symbol: s, name: s, price: 0 })));
      }
    } finally {
      setSymbolsLoading(false);
    }
  };

  fetchSymbols();
}, []);
```

**3. Replace MOCK_DATA_SESSIONS with real API:**

```typescript
// REMOVE:
const MOCK_DATA_SESSIONS = [...];

// ADD:
const [dataSessions, setDataSessions] = useState<DataSession[]>([]);
const [sessionsLoading, setSessionsLoading] = useState(false);

useEffect(() => {
  if (mode === 'backtest') {
    const fetchSessions = async () => {
      try {
        setSessionsLoading(true);
        const response = await fetch('http://localhost:8080/api/data-collection/sessions?limit=50');
        const data = await response.json();
        setDataSessions(data.sessions);
      } catch (error) {
        console.error('Failed to load data sessions:', error);
      } finally {
        setSessionsLoading(false);
      }
    };

    fetchSessions();
  }
}, [mode]);
```

**4. Implement real handleStartSession:**

```typescript
// REMOVE: Alert and console.log

// ADD:
const handleStartSession = async () => {
  try {
    setLoading(true);

    // Build session configuration
    const sessionConfig = {
      session_type: mode,
      symbols: selectedSymbols,
      strategy_config: {
        strategies: selectedStrategies
      },
      config: {
        budget: {
          global_cap: globalBudget,
          allocations: {}
        },
        stop_loss_percent: stopLoss,
        take_profit_percent: takeProfit,
        ...(mode === 'backtest' && {
          session_id: backtestSessionId,
          acceleration_factor: accelerationFactor
        })
      },
      idempotent: true
    };

    const response = await fetch('http://localhost:8080/sessions/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,  // TODO: Get from auth context
        'X-CSRF-Token': csrfToken  // TODO: Get from auth context
      },
      body: JSON.stringify(sessionConfig)
    });

    const data = await response.json();

    if (data.type === 'response') {
      setCurrentSessionId(data.data.data.session_id);
      setIsSessionRunning(true);

      // Redirect to dashboard
      router.push('/dashboard');
    } else {
      console.error('Failed to start session:', data.error_message);
      alert(`Failed to start session: ${data.error_message}`);
    }
  } catch (error) {
    console.error('Failed to start session:', error);
    alert('Failed to start session. Please try again.');
  } finally {
    setLoading(false);
  }
};
```

**5. Implement real handleStopSession:**

```typescript
// REMOVE: Local state change only

// ADD:
const handleStopSession = async () => {
  if (!currentSessionId) return;

  try {
    const response = await fetch('http://localhost:8080/sessions/stop', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
        'X-CSRF-Token': csrfToken
      },
      body: JSON.stringify({ session_id: currentSessionId })
    });

    const data = await response.json();

    if (data.type === 'response') {
      setIsSessionRunning(false);
      setCurrentSessionId(null);
    } else {
      console.error('Failed to stop session:', data.error_message);
      alert(`Failed to stop session: ${data.error_message}`);
    }
  } catch (error) {
    console.error('Failed to stop session:', error);
    alert('Failed to stop session. Please try again.');
  }
};
```

---

## Action Plan

### Phase 1: Backend Enhancements (Estimated: 2-3 hours)

1. ✅ **No changes needed** to existing endpoints - they're already correct!
2. ❌ **Create GET /api/exchange/symbols** endpoint:
   - New route in `unified_server.py` after line 1762
   - Query MEXC exchange for symbol list + tickers
   - Add 5-minute caching to reduce API load
   - Return symbol metadata (price, volume, 24h change)

3. ⚠️ **Enhance GET /api/strategies** (optional):
   - Join with `backtest_results` table
   - Calculate `winRate` and `avgProfit` from historical backtests
   - Add to response for UI display

### Phase 2: Frontend Integration (Estimated: 1-2 hours)

1. Replace MOCK_STRATEGIES with `GET /api/strategies`
2. Replace MOCK_SYMBOLS with `GET /api/exchange/symbols`
3. Replace MOCK_DATA_SESSIONS with `GET /api/data-collection/sessions`
4. Implement real `handleStartSession` with `POST /sessions/start`
5. Implement real `handleStopSession` with `POST /sessions/stop`
6. Add authentication token management
7. Add CSRF token management
8. Add loading states
9. Add error handling
10. Remove MOCKUP warnings

### Phase 3: Testing (Estimated: 1 hour)

1. Test strategy loading from QuestDB
2. Test symbol loading from exchange
3. Test session start for backtest/paper/live
4. Test session stop
5. Test error scenarios (missing auth, invalid config, etc.)
6. Verify E2E tests still pass

---

## Summary

### ✅ Excellent News:

**The backend is 90% ready!** All core endpoints exist and support the required functionality:

- **Strategy selection** - Fully supported via `GET /api/strategies`
- **Session configuration** - Fully supported via `POST /sessions/start`
- **Historical sessions** - Fully supported via `GET /api/data-collection/sessions`
- **Session stop** - Fully supported via `POST /sessions/stop`

### ⚠️ Minor Gaps:

1. **GET /api/exchange/symbols** - Need to create (2 hours work)
2. **Strategy performance metrics** - Optional enhancement (1 hour work)

### 🎯 Next Steps:

1. Create `/api/exchange/symbols` endpoint
2. Update frontend to use real endpoints
3. Test integration end-to-end
4. Remove MOCKUP warnings
5. Deploy to production

**Total Estimated Time: 4-6 hours**

---

**Author:** Claude Code
**Date:** 2025-11-18
**Status:** Analysis Complete - Ready for Implementation
