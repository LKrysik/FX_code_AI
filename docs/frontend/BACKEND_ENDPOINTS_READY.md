# Backend Endpoints Ready for Session Configuration

**Date:** 2025-11-18
**Status:** ✅ ALL ENDPOINTS IMPLEMENTED AND READY

---

## Summary

**Excellent news!** All required backend endpoints are now implemented and ready for the session configuration frontend to use.

### Endpoint Status

| Endpoint | Status | Purpose |
|----------|--------|---------|
| `GET /api/strategies` | ✅ EXISTS | List all available strategies from QuestDB |
| `GET /api/exchange/symbols` | ✅ **CREATED** | Get symbols with real-time prices from MEXC |
| `GET /api/data-collection/sessions` | ✅ EXISTS | List historical data sessions for backtest |
| `POST /sessions/start` | ✅ EXISTS | Start live/paper/backtest session with config |
| `POST /sessions/stop` | ✅ EXISTS | Stop active session |

---

## Endpoint Details

### 1. GET /api/strategies ✅

**URL:** `http://localhost:8080/api/strategies`
**Authentication:** Required (JWT Bearer token)

**Response:**
```json
{
  "type": "response",
  "data": {
    "strategies": [
      {
        "id": "pump_v2",
        "strategy_name": "Pump Detection v2",
        "description": "Detects rapid price increases using TWPA velocity",
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

**Frontend Usage:**
```typescript
const response = await fetch('http://localhost:8080/api/strategies', {
  headers: {
    'Authorization': `Bearer ${authToken}`
  }
});
const data = await response.json();
const strategies = data.data.strategies;
```

---

### 2. GET /api/exchange/symbols ✅ NEW!

**URL:** `http://localhost:8080/api/exchange/symbols`
**Authentication:** Not required
**Caching:** 5 minutes

**Response:**
```json
{
  "type": "response",
  "data": {
    "symbols": [
      {
        "symbol": "BTC_USDT",
        "name": "BTC/USDT",
        "price": 50250.00,
        "volume24h": 1250000000,
        "change24h": 0.0,
        "high24h": 0.0,
        "low24h": 0.0,
        "exchange": "mexc",
        "timestamp": "2025-11-18T12:30:00Z"
      },
      {
        "symbol": "ETH_USDT",
        "name": "ETH/USDT",
        "price": 3050.00,
        "volume24h": 850000000,
        "change24h": 0.0,
        "high24h": 0.0,
        "low24h": 0.0,
        "exchange": "mexc",
        "timestamp": "2025-11-18T12:30:00Z"
      }
    ]
  }
}
```

**Features:**
- Real-time prices from MEXC exchange
- 5-minute cache to reduce API load
- Includes all configured symbols from `config.json`
- Graceful fallback if ticker data unavailable

**Frontend Usage:**
```typescript
const response = await fetch('http://localhost:8080/api/exchange/symbols');
const data = await response.json();
const symbols = data.data.symbols;
```

---

### 3. GET /api/data-collection/sessions ✅

**URL:** `http://localhost:8080/api/data-collection/sessions?limit=50`
**Authentication:** Not required

**Response:**
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

**Frontend Usage:**
```typescript
const response = await fetch('http://localhost:8080/api/data-collection/sessions?limit=50');
const data = await response.json();
const sessions = data.sessions;
```

---

### 4. POST /sessions/start ✅

**URL:** `http://localhost:8080/sessions/start`
**Authentication:** Required (JWT + CSRF)
**Purpose:** Start trading session with full configuration

**Request Body:**
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
    "max_position_size": 100,
    "session_id": "session_20251118...",
    "acceleration_factor": 10
  },
  "idempotent": true
}
```

**Response:**
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

**Session Types:**
- `"live"` - Real money trading on MEXC
- `"paper"` - Simulated trading with fake money
- `"backtest"` - Replay historical data (requires `config.session_id`)
- `"collect"` - Data collection mode (no trading)

**Frontend Usage:**
```typescript
const sessionConfig = {
  session_type: "paper",
  symbols: ["BTC_USDT", "ETH_USDT"],
  strategy_config: {
    strategies: ["pump_v2", "dump_v2"]
  },
  config: {
    budget: {
      global_cap: 1000,
      allocations: {}
    },
    stop_loss_percent: 5.0,
    take_profit_percent: 10.0
  },
  idempotent: true
};

const response = await fetch('http://localhost:8080/sessions/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authToken}`,
    'X-CSRF-Token': csrfToken
  },
  body: JSON.stringify(sessionConfig)
});

const data = await response.json();
const sessionId = data.data.data.session_id;
```

---

### 5. POST /sessions/stop ✅

**URL:** `http://localhost:8080/sessions/stop`
**Authentication:** Required (JWT + CSRF)

**Request Body:**
```json
{
  "session_id": "exec_20251118_150123_xyz789"
}
```

**Response:**
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

**Frontend Usage:**
```typescript
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
```

---

## Frontend Integration Checklist

### Phase 1: Remove MOCKUP Data

- [ ] Remove `MOCK_STRATEGIES` array
- [ ] Remove `MOCK_SYMBOLS` array
- [ ] Remove `MOCK_DATA_SESSIONS` array
- [ ] Remove all MOCKUP warning banners
- [ ] Remove MOCKUP subheaders

### Phase 2: Add Real API Calls

#### Strategies:
```typescript
const [strategies, setStrategies] = useState<Strategy[]>([]);
const [strategiesLoading, setStrategiesLoading] = useState(true);

useEffect(() => {
  const fetchStrategies = async () => {
    try {
      setStrategiesLoading(true);
      const response = await fetch('http://localhost:8080/api/strategies', {
        headers: {
          'Authorization': `Bearer ${authToken}`
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

#### Symbols:
```typescript
const [symbols, setSymbols] = useState<Symbol[]>([]);
const [symbolsLoading, setSymbolsLoading] = useState(true);

useEffect(() => {
  const fetchSymbols = async () => {
    try {
      setSymbolsLoading(true);
      const response = await fetch('http://localhost:8080/api/exchange/symbols');
      const data = await response.json();
      if (data.type === 'response') {
        setSymbols(data.data.symbols);
      }
    } catch (error) {
      console.error('Failed to load symbols:', error);
    } finally {
      setSymbolsLoading(false);
    }
  };

  fetchSymbols();
}, []);
```

#### Data Sessions (for backtest):
```typescript
const [dataSessions, setDataSessions] = useState<DataSession[]>([]);
const [sessionsLoading, setSessionsLoading] = useState(false);

useEffect(() => {
  if (mode === 'backtest') {
    const fetchSessions = async () => {
      try:
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

#### Start Session:
```typescript
const handleStartSession = async () => {
  try {
    setLoading(true);

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
        'Authorization': `Bearer ${authToken}`,
        'X-CSRF-Token': csrfToken
      },
      body: JSON.stringify(sessionConfig)
    });

    const data = await response.json();

    if (data.type === 'response') {
      setCurrentSessionId(data.data.data.session_id);
      setIsSessionRunning(true);
      router.push('/dashboard');
    } else {
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

#### Stop Session:
```typescript
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
      alert(`Failed to stop session: ${data.error_message}`);
    }
  } catch (error) {
    console.error('Failed to stop session:', error);
    alert('Failed to stop session. Please try again.');
  }
};
```

### Phase 3: Add Authentication

- [ ] Get auth token from auth context/store
- [ ] Get CSRF token from auth context/store
- [ ] Add login page if not exists
- [ ] Add token refresh logic
- [ ] Handle 401 Unauthorized errors

### Phase 4: Add Error Handling

- [ ] Add error states for each API call
- [ ] Display user-friendly error messages
- [ ] Add retry logic for failed requests
- [ ] Handle network errors gracefully

### Phase 5: Add Loading States

- [ ] Show loading spinner for strategies
- [ ] Show loading spinner for symbols
- [ ] Show loading spinner for data sessions
- [ ] Show loading spinner for session start
- [ ] Disable buttons during loading

---

## Testing Checklist

### Backend Tests

- [ ] Test `GET /api/strategies` returns strategies from QuestDB
- [ ] Test `GET /api/exchange/symbols` returns symbols with prices
- [ ] Test `GET /api/exchange/symbols` cache works (5 min TTL)
- [ ] Test `GET /api/data-collection/sessions` returns sessions
- [ ] Test `POST /sessions/start` with paper mode
- [ ] Test `POST /sessions/start` with live mode
- [ ] Test `POST /sessions/start` with backtest mode
- [ ] Test `POST /sessions/start` validates required fields
- [ ] Test `POST /sessions/stop` stops active session
- [ ] Test authentication required for protected endpoints

### Frontend Tests

- [ ] Test strategies load on page mount
- [ ] Test symbols load on page mount
- [ ] Test data sessions load when mode = backtest
- [ ] Test strategy multi-select works
- [ ] Test symbol multi-select works
- [ ] Test budget/risk inputs work
- [ ] Test backtest session dropdown works
- [ ] Test acceleration slider works
- [ ] Test validation prevents invalid configs
- [ ] Test session starts successfully
- [ ] Test session stops successfully
- [ ] Test redirect to dashboard after session start

### Integration Tests

- [ ] End-to-end: Select strategies → Select symbols → Start paper session
- [ ] End-to-end: Select backtest session → Configure → Start backtest
- [ ] End-to-end: Start session → Stop session → Restart session
- [ ] Verify session appears in dashboard after start
- [ ] Verify session disappears from dashboard after stop

---

## Next Steps

1. ✅ **Backend endpoints created** - All required endpoints implemented
2. ⏳ **Update frontend** - Replace MOCKUP data with real API calls (1-2 hours)
3. ⏳ **Add authentication** - Implement auth token management (30 min)
4. ⏳ **Test integration** - Verify all endpoints work together (1 hour)
5. ⏳ **Remove MOCKUP warnings** - Clean up UI (15 min)
6. ⏳ **Deploy** - Push to production

**Total Estimated Time Remaining: 3-4 hours**

---

## Architecture Notes

### Why Create `/api/exchange/symbols` Instead of Enhancing `/symbols`?

1. **Separation of Concerns:**
   - `/symbols` - Simple config list (fast, no external API calls)
   - `/api/exchange/symbols` - Real-time exchange data (slower, requires MEXC API)

2. **Backward Compatibility:**
   - Existing code depends on `/symbols` returning simple array
   - New endpoint provides enhanced data without breaking existing code

3. **Performance:**
   - `/symbols` - Instant response from config file
   - `/api/exchange/symbols` - Cached (5 min) to reduce API load

### Session Start Configuration Flow

```
Frontend trading-session/page.tsx
  ↓ User selects strategies, symbols, budget, risk params
  ↓
POST /sessions/start {
  session_type: "paper",
  symbols: ["BTC_USDT", "ETH_USDT"],
  strategy_config: { strategies: ["pump_v2", "dump_v2"] },
  config: { budget, stop_loss, take_profit, ... }
}
  ↓
unified_server.py:post_sessions_start()
  ↓ Validates configuration
  ↓ Stops existing session if running
  ↓ Creates ExecutionController with config
  ↓
ExecutionController.start_live_trading() / start_backtest()
  ↓ Activates strategies via StrategyManager
  ↓ Subscribes to symbols via MarketDataProvider
  ↓ Initializes budget tracking via RiskManager
  ↓
EventBus publishes "session_started"
  ↓
WebSocket broadcasts to all connected clients
  ↓
Frontend receives session_id, redirects to /dashboard
```

---

## Summary

✅ **All backend endpoints are ready!**

The backend now fully supports:
- Strategy selection (from QuestDB)
- Symbol selection (with real-time prices from MEXC)
- Historical session selection (for backtesting)
- Full session configuration (budget, risk, strategies, symbols)
- Session start/stop operations

**Frontend can now:**
- Replace MOCKUP data with real API calls
- Get real-time symbol prices
- Start/stop sessions with full configuration
- Select multiple strategies and symbols
- Configure budget and risk parameters

**Next:** Update `frontend/src/app/trading-session/page.tsx` to use real endpoints.

---

**Author:** Claude Code
**Date:** 2025-11-18
**Status:** ✅ Backend Implementation Complete
