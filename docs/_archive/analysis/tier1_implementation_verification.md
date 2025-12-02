# TIER 1 SHORT Selling System - Comprehensive Code Verification Analysis

**Data weryfikacji:** 2025-11-04
**Zakres:** Backend + Frontend
**Cel:** Weryfikacja założeń względem istniejącego kodu, identyfikacja luk, rekomendacje rozwojowe

---

## Executive Summary

**Wynik weryfikacji:** System TIER 1 SHORT Selling został zaimplementowany z **wysokim pokryciem funkcjonalności** (około 75%), ale wymaga **krytycznych uzupełnień** w obszarze monitoringu i odporności.

**Kluczowe odkrycia:**
- ✅ **ISTNIEJE**: Emergency Exit (user-configured protection)
- ✅ **ISTNIEJE**: Circuit Breaker & Retry Logic (kod gotowy, ale NIE UŻYWANY w krytycznych miejscach)
- ✅ **ISTNIEJE**: Paper Trading API (8 endpointów)
- ✅ **ISTNIEJE**: Backtest UI (wymaga aktualizacji po usunięciu Visual Builder)
- ❌ **BRAK**: Automatic Liquidation Monitor (real-time distance tracking)
- ❌ **BRAK**: Live Position Monitor UI (dashboard z pozycjami)
- ❌ **BRAK**: Paper Trading Dashboard UI
- ⚠️ **CZĘŚCIOWO**: Order retry logic (kod istnieje, ale NIE jest używany w MEXC adapter)

---

## 1. EMERGENCY EXIT vs. LIQUIDATION MONITOR - Kluczowa Różnica

### 1.1 Emergency Exit (✅ ISTNIEJE)

**Lokalizacja kodu:**
- Backend: `src/domain/services/strategy_manager.py:1532-1562` (evaluation)
- Backend: `src/domain/services/strategy_manager.py:1602-1635` (execution)
- Frontend: `frontend/src/components/strategy/StrategyBuilder5Section.tsx:1693-1801` (UI config)

**Dowód z kodu (strategy_manager.py:1532-1562):**
```python
elif strategy.current_state == StrategyState.POSITION_ACTIVE:
    # E1: Check emergency exit conditions (higher priority than ZE1)
    emergency_result = strategy.evaluate_emergency_exit(indicator_values)
    if emergency_result == ConditionResult.TRUE:
        emergency_indicators = strategy._record_decision_indicators(indicator_values, "E1_emergency_exit")
        strategy.current_state = StrategyState.EMERGENCY_EXIT

        # Start cooldown if configured
        cooldown_minutes = strategy.global_limits.get("emergency_exit_cooldown_minutes", 30)
        strategy.start_cooldown(cooldown_minutes, "emergency_exit")
```

**Charakterystyka:**
- ✅ Istnieje i działa
- ✅ Użytkownik konfiguruje warunki (np. `pump_magnitude_pct < -5%`)
- ✅ Wyższy priorytet niż normalne close (ZE1)
- ✅ Mechanizm cooldown
- ⚠️ **WYMAGA** manualnej konfiguracji przez użytkownika

**Dlaczego to nie zastępuje Liquidation Monitor:**
Emergency Exit to narzędzie strategiczne oparte na warunkach biznesowych (np. odwrócenie trendu pumpa), a NIE matematyczna ochrona przed likwidacją.

### 1.2 Liquidation Monitor (❌ BRAK - DO IMPLEMENTACJI)

**Status:** Kalkulacja liquidation_price ISTNIEJE, ale monitoring NIE ISTNIEJE.

**Dowód - kalkulacja istnieje (order_manager.py:165-186):**
```python
def _calculate_liquidation_price(self, entry_price: float, leverage: float, is_long: bool) -> Optional[float]:
    """Calculate liquidation price for leveraged position"""
    if leverage <= 1.0:
        return None  # No liquidation for non-leveraged positions

    if is_long:
        # LONG: liquidation = entry × (1 - 1/leverage)
        return entry_price * (1 - 1 / leverage)
    else:
        # SHORT: liquidation = entry × (1 + 1/leverage)
        return entry_price * (1 + 1 / leverage)
```

**Dowód - pozycja przechowuje liquidation_price (order_manager.py:82-90):**
```python
@dataclass
class Position:
    symbol: str
    quantity: float = 0.0
    average_price: float = 0.0
    leverage: float = 1.0
    liquidation_price: Optional[float] = None  # Price at which position is liquidated
    unrealized_pnl: float = 0.0
```

**Dowód - brak monitoringu:**
```bash
# Wynik grep dla: "liquidation.*monitor|check.*liquidation|liquidation.*protection"
No files found
```

**Co BRAKUJE:**
1. ❌ Real-time monitoring odległości do liquidation price
2. ❌ Automatic trigger when distance < 10% (safety threshold)
3. ❌ Alert notifications (WebSocket push to frontend)
4. ❌ Automatic emergency close przy zbliżeniu do likwidacji

**Gdzie dodać:**
- **Backend:** Nowy serwis `src/domain/services/liquidation_monitor.py`
  - Subscribe to EventBus: "market_data" events
  - Calculate distance: `(liquidation_price - current_price) / current_price * 100`
  - Publish "liquidation_warning" event when distance < threshold
  - Integrate with OrderManager for emergency close

- **Frontend:** Nowy komponent `frontend/src/components/trading/LiquidationAlert.tsx`
  - Real-time display: liquidation distance percentage
  - Color coding: green (>20%), yellow (10-20%), red (<10%)
  - WebSocket subscription to "liquidation_warning" events

**ROI:** 🔴 CRITICAL - Prevents account wipeout in high-leverage scenarios

---

## 2. CIRCUIT BREAKER & RETRY LOGIC

### 2.1 Circuit Breaker Implementation (✅ ISTNIEJE, ale NIE UŻYWANY)

**Lokalizacje kodu:**
- `src/core/circuit_breaker.py` (375 linii - pełna implementacja)
- `src/infrastructure/exchanges/circuit_breaker.py` (236 linii - alternatywna implementacja)

**Dowód - pełna funkcjonalność (circuit_breaker.py:53-176):**
```python
class CircuitBreaker:
    """Circuit breaker implementation with thread-safe operations"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._lock = threading.RLock()  # Thread safety

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        if not self._can_attempt_request():
            self.metrics.rejected_requests += 1
            raise CircuitBreakerOpenException(f"Circuit breaker is OPEN")

        try:
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
            self._record_success()
            return result
        except self.config.expected_exception as e:
            self._record_failure(e)
            raise
```

**Dowód - kod retry logic (circuit_breaker.py:230-290):**
```python
class RetryHandler:
    """Retry handler with exponential backoff and jitter"""

    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with retry logic"""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except self.config.retry_on as e:
                last_exception = e
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)  # Exponential backoff
                    logger.warning(f"Retry attempt {attempt + 1}/{self.config.max_attempts}. Retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)

        raise last_exception
```

**Dowód - ResilientService (łączy circuit breaker + retry) (circuit_breaker.py:293-330):**
```python
class ResilientService:
    """Service that combines circuit breaker and retry patterns"""

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with both circuit breaker and retry protection"""
        async def wrapped_call():
            return await self.retry_handler.execute_async(func, *args, **kwargs)

        return await self.circuit_breaker.call_async(wrapped_call)
```

### 2.2 Problem: Circuit Breaker NIE jest używany w MEXC Adapter

**Dowód - brak integracji w MEXC adapter:**
```bash
# grep -i "circuit.*breaker|ResilientService|resilient_service" src/infrastructure/adapters/mexc_futures_adapter.py
No matches found
```

**Konsekwencje:**
- ❌ Brak ochrony przed kaskadowymi błędami API
- ❌ Brak automatycznego retry przy sieciowych błędach
- ❌ Brak fail-fast przy problemach z MEXC
- ❌ Potencjalna przeciążenie API przy awariach

**Gdzie zintegrować:**
```python
# src/infrastructure/adapters/mexc_futures_adapter.py

from src.core.circuit_breaker import ResilientService, CircuitBreakerConfig, RetryConfig

class MexcFuturesAdapter:
    def __init__(self, ...):
        # Add circuit breaker for critical operations
        self.order_service = ResilientService(
            name="mexc_orders",
            circuit_config=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60.0,
                timeout=10.0
            ),
            retry_config=RetryConfig(
                max_attempts=3,
                initial_delay=1.0,
                backoff_factor=2.0
            )
        )

    async def place_futures_order(self, ...):
        # Wrap API call with resilient service
        return await self.order_service.call_async(self._place_order_impl, ...)
```

**ROI:** 🔴 CRITICAL - Prevents API cascading failures and improves reliability

---

## 3. FRONTEND UI - Status Implementacji

### 3.1 Paper Trading UI (⚠️ CZĘŚCIOWO ISTNIEJE)

**Backend API (✅ PEŁNA IMPLEMENTACJA):**
- Lokalizacja: `src/api/paper_trading_routes.py` (450 linii)
- **Dowód - 8 endpointów:**
```python
@router.post("/sessions", ...)              # Linia 107 - Create session
@router.get("/sessions", ...)               # Linia 159 - List sessions
@router.get("/sessions/{session_id}", ...)  # Linia 204 - Get session details
@router.get("/sessions/{session_id}/performance", ...)  # Linia 241 - Performance metrics
@router.get("/sessions/{session_id}/orders", ...)       # Linia 287 - Order history
@router.post("/sessions/{session_id}/stop", ...)        # Linia 333 - Stop session
@router.delete("/sessions/{session_id}", ...)           # Linia 384 - Delete session
@router.get("/health", ...)                             # Linia 430 - Health check
```

**Frontend UI (❌ BRAK DEDYKOWANEGO DASHBOARDU):**
- **Dowód - session type selector ISTNIEJE (trading/page.tsx:480-481):**
```tsx
<MenuItem value="paper">Paper Trading (Virtual)</MenuItem>
<MenuItem value="live">Live Trading (Real Money)</MenuItem>
<MenuItem value="backtest">Backtesting (Historical)</MenuItem>
```

- **Dowód - brak komponentów Paper Trading:**
```bash
# Glob pattern: frontend/src/**/*paper*.tsx
No files found

# Glob pattern: frontend/src/**/*Paper*.tsx
No files found
```

**Co BRAKUJE:**
1. ❌ `frontend/src/components/paper-trading/PaperTradingDashboard.tsx`
   - Session list with performance metrics
   - Real-time P&L display
   - Position tracking
   - Order history table

2. ❌ `frontend/src/components/paper-trading/SessionControls.tsx`
   - Start/stop session buttons
   - Session configuration form
   - Status indicators

3. ❌ `frontend/src/app/paper-trading/page.tsx`
   - Dedicated page for paper trading management

**Gdzie dodać:**
- Create new route: `/app/paper-trading/page.tsx`
- Reuse API integration from `src/services/api.ts`
- Integrate with WebSocket for real-time updates

**ROI:** 🟡 HIGH - Enables safe strategy testing before live deployment

### 3.2 Live Position Monitor (❌ BRAK)

**Dowód - brak komponentów:**
```bash
# grep -i "position.*monitor|PositionMonitor|live.*position" frontend/src
No files found

# Glob: frontend/src/**/*position*.tsx
No files found
```

**Co BRAKUJE:**
1. ❌ Real-time position display (leverage, liquidation price, unrealized P&L)
2. ❌ Visual liquidation distance indicator (progress bar with color coding)
3. ❌ Position controls (emergency close, adjust stop-loss)

**Gdzie dodać:**
```
frontend/src/components/trading/PositionMonitor.tsx
├── PositionCard.tsx (individual position display)
├── LiquidationIndicator.tsx (distance to liquidation)
└── PositionActions.tsx (emergency controls)
```

**Backend data source:**
- API: `GET /api/positions` (needs implementation)
- WebSocket: Subscribe to "position_update" events

**ROI:** 🔴 CRITICAL - Essential for monitoring leveraged positions

### 3.3 Backtest UI (✅ ISTNIEJE, ale WYMAGA AKTUALIZACJI)

**Lokalizacja:** `frontend/src/app/backtesting/page.tsx` (1046 linii)

**Dowód - pełny UI istnieje:**
- Sessions table z kolumnami: Session ID, Status, Symbols, Date Range, Strategy, Trades, Win Rate, P&L, Max DD, Actions (linie 442-544)
- Analytics Dashboard z kartami: Total Return, Win Rate, Sharpe Ratio, Max Drawdown (linie 546-688)
- Performance Summary (linie 702-773)
- Risk Metrics (linie 775-813)

**Problem:**
```tsx
// Linia 893-895
<Alert severity="warning">
  Backtest functionality temporarily disabled. Strategy Builder removed - only 5-section strategies supported.
</Alert>
```

**Kod komentowany (linie 306-337):**
```tsx
// DEPRECATED: Backtest requires reimplementation with 5-section strategies
// Visual Strategy Builder has been removed
setSnackbar({
  open: true,
  message: 'Backtest functionality requires reimplementation after Strategy Builder removal',
  severity: 'warning'
});
```

**Co WYMAGA AKTUALIZACJI:**
1. ⚠️ Zmienić backend integration z Visual Builder na 5-section strategies
2. ⚠️ Odkomentować i dostosować `handleCreateBacktest()` do nowego formatu
3. ⚠️ Zaktualizować strategy selector do używania 5-section strategy API

**Gdzie zmienić:**
- Linie 278-337: `handleCreateBacktest()` - dostosować do 5-section format
- Linie 848-891: Strategy selector - zastąpić blueprint selection 5-section strategy selection

**ROI:** 🟡 HIGH - Re-enables historical strategy testing

---

## 4. LEVERAGE VALIDATION

### 4.1 Server-Side Validation (✅ ISTNIEJE)

**Lokalizacja:** `src/infrastructure/adapters/mexc_futures_adapter.py:107-108`

**Dowód:**
```python
if leverage < 1 or leverage > 200:
    raise ValueError(f"Leverage must be between 1 and 200, got {leverage}")
```

✅ Walidacja działa poprawnie (1-200 range zgodny z MEXC API)

### 4.2 Client-Side Validation (❌ BRAK)

**Dowód - brak walidacji w UI:**
```bash
# grep "leverage.*validation|validate.*leverage" frontend/src/components/strategy/StrategyBuilder5Section.tsx
No matches found
```

**Konsekwencje:**
- Użytkownik może wpisać niepoprawną wartość (np. 500, 0, -5)
- Błąd dopiero po wysłaniu do backendu (zła UX)

**Gdzie dodać:**
```tsx
// frontend/src/components/strategy/StrategyBuilder5Section.tsx

<TextField
  type="number"
  label="Leverage"
  value={formData.z1_entry.leverage}
  onChange={(e) => {
    const value = parseFloat(e.target.value);
    if (value < 1 || value > 200) {
      setLeverageError("Leverage must be between 1 and 200");
      return;
    }
    setLeverageError(null);
    setFormData({ ...formData, z1_entry: { ...formData.z1_entry, leverage: value } });
  }}
  error={leverageError !== null}
  helperText={leverageError || "Recommended: 1-10 for safety"}
  inputProps={{ min: 1, max: 200, step: 0.1 }}
/>
```

**ROI:** 🟢 MEDIUM - Improves UX, prevents backend errors

---

## 5. ERROR HANDLING - Frontend

### 5.1 Status (✅ PODSTAWOWY, ale można ULEPSZYĆ)

**Dowód - error handling w trading/page.tsx:**
```tsx
// Linia 83
const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info'}>({...})

// Przykład catch block (linie 142-147):
} catch (error) {
  setSnackbar({
    open: true,
    message: `Failed to start session: ${error.message || 'Unknown error'}`,
    severity: 'error'
  });
}
```

**Co DZIAŁA:**
- ✅ Snackbar notifications dla błędów
- ✅ Try-catch bloki w async operacjach
- ✅ Error display w UI

**Co można ULEPSZYĆ:**
1. ⚠️ Brak strukturalnego error typing (wszystkie jako `error`)
2. ⚠️ Brak retry mechanism w UI dla transient errors
3. ⚠️ Brak detailed error messages (tylko generic "Failed to...")

**Rekomendacje:**
```tsx
// Dodać typed errors
interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

// Enhanced error handler
const handleApiError = (error: ApiError) => {
  if (error.code === 'NETWORK_ERROR') {
    // Show retry button
    setShowRetry(true);
  } else if (error.code === 'VALIDATION_ERROR') {
    // Highlight form fields
    setFieldErrors(error.details);
  } else {
    // Generic error
    setSnackbar({ message: error.message, severity: 'error' });
  }
};
```

**ROI:** 🟢 MEDIUM - Better UX for error scenarios

---

## 6. RACE CONDITION - Connection Pool

### 6.1 Bug w Paper Trading Persistence (⚠️ WYMAGA NAPRAWY)

**Lokalizacja:** `src/domain/services/paper_trading_persistence.py:80-96`

**Dowód - unsafe pool initialization:**
```python
async def _ensure_pool(self):
    """Ensure connection pool is initialized"""
    if self._pool is None:  # ❌ NOT THREAD-SAFE
        self.logger.info("paper_trading.initializing_pool")
        self._pool = await asyncpg.create_pool(
            host=self.db_config['host'],
            port=self.db_config['port'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database'],
            min_size=2,
            max_size=10,
            command_timeout=30
        )
        self.logger.info("paper_trading.pool_ready")
```

**Problem:**
Multiple concurrent calls to `_ensure_pool()` can create duplicate connection pools.

**Proof of race condition:**
1. Request A calls `_ensure_pool()` → checks `self._pool is None` → TRUE
2. Request B calls `_ensure_pool()` → checks `self._pool is None` → TRUE (still)
3. Request A starts creating pool
4. Request B starts creating pool (DUPLICATE!)

**Naprawa:**
```python
import asyncio

class PaperTradingPersistence:
    def __init__(self, ...):
        self._pool: Optional[asyncpg.Pool] = None
        self._pool_lock = asyncio.Lock()  # ✅ Add lock

    async def _ensure_pool(self):
        """Thread-safe pool initialization"""
        async with self._pool_lock:  # ✅ Acquire lock
            if self._pool is None:
                self.logger.info("paper_trading.initializing_pool")
                self._pool = await asyncpg.create_pool(...)
                self.logger.info("paper_trading.pool_ready")
```

**ROI:** 🔴 CRITICAL - Prevents connection pool leaks and database errors

---

## 7. REKOMENDACJE ROZWOJOWE - Priorytetyzacja ROI

### 7.1 TIER CRITICAL (🔴 Immediate Action Required)

| # | Feature | Effort | ROI | Uzasadnienie |
|---|---------|--------|-----|--------------|
| 1 | **Automatic Liquidation Monitor** | 3-5 dni | 🔴 CRITICAL | Prevents account wipeout, essential for leveraged trading |
| 2 | **Circuit Breaker Integration (MEXC)** | 1-2 dni | 🔴 CRITICAL | Prevents API cascading failures, improves system stability |
| 3 | **Live Position Monitor UI** | 2-3 dni | 🔴 CRITICAL | Essential visibility for active trading, risk management |
| 4 | **Race Condition Fix (Connection Pool)** | 0.5 dni | 🔴 CRITICAL | Prevents database connection leaks and errors |

**Łączny czas:** 6.5-10.5 dni
**Priorytet:** Wykonać NATYCHMIAST przed uruchomieniem live trading

### 7.2 TIER HIGH (🟡 Important, Schedule Soon)

| # | Feature | Effort | ROI | Uzasadnienie |
|---|---------|--------|-----|--------------|
| 5 | **Paper Trading Dashboard UI** | 3-4 dni | 🟡 HIGH | Enables safe strategy testing, reduces live trading risk |
| 6 | **Backtest UI Update (5-section)** | 2-3 dni | 🟡 HIGH | Re-enables historical testing, strategy validation |
| 7 | **Order Retry Logic (integration)** | 1-2 dni | 🟡 HIGH | Reduces order failures due to network issues |

**Łączny czas:** 6-9 dni
**Priorytet:** Zaplanować w następnym sprincie

### 7.3 TIER MEDIUM (🟢 Nice to Have, Can Wait)

| # | Feature | Effort | ROI | Uzasadnienie |
|---|---------|--------|-----|--------------|
| 8 | **Client-Side Leverage Validation** | 0.5 dni | 🟢 MEDIUM | Improves UX, prevents unnecessary backend calls |
| 9 | **Enhanced Error Handling (UI)** | 1-2 dni | 🟢 MEDIUM | Better user experience in error scenarios |
| 10 | **WebSocket Reconnection Logic** | 1 dzień | 🟢 MEDIUM | Improves real-time data reliability |

**Łączny czas:** 2.5-3.5 dni
**Priorytet:** Backlog, implementować gdy czas pozwala

---

## 8. OCENA SYSTEMU (8 Wymiarów)

| Wymiar | Ocena | Uzasadnienie | Dowód |
|--------|-------|--------------|-------|
| **1. Funkcjonalność** | 7/10 | Core features implemented, missing monitoring/UI | Emergency Exit (✅), Liquidation Monitor (❌) |
| **2. Niezawodność** | 5/10 | Circuit breaker exists but NOT used, race condition in pool | Circuit breaker code (✅), MEXC integration (❌), Pool lock (❌) |
| **3. Wydajność** | 8/10 | Efficient data flow, good architecture | EventBus pattern, streaming indicators |
| **4. Bezpieczeństwo** | 6/10 | Leverage validation OK, liquidation monitoring MISSING | Server-side validation (✅), Auto-monitor (❌) |
| **5. Testowalność** | 6/10 | Paper trading backend ready, UI missing | 8 API endpoints (✅), Dashboard (❌) |
| **6. Utrzymywalność** | 8/10 | Clean architecture, good separation of concerns | Layered design, DI container |
| **7. Skalowalność** | 7/10 | Event-driven design scales well, needs connection pooling fix | EventBus (✅), Pool race condition (❌) |
| **8. User Experience** | 5/10 | Backend complete, frontend UIs missing | API ready (✅), Dashboards (❌) |

**Średnia:** **6.5/10**

**Kluczowe wnioski:**
- System ma **solidne fundamenty** (architecture, backend logic)
- **Krytyczne luki** w monitoringu i UI
- **Wymaga uzupełnienia** przed production deployment

---

## 9. PLAN DZIAŁANIA

### Sprint 1 (Tydzień 1-2): CRITICAL Fixes

**Cel:** Przygotowanie do safe live trading

1. **Automatic Liquidation Monitor** (3-5 dni)
   - Backend: `src/domain/services/liquidation_monitor.py`
   - EventBus integration: subscribe "market_data", publish "liquidation_warning"
   - Frontend: `LiquidationAlert.tsx` component
   - Tests: unit + integration

2. **Circuit Breaker Integration** (1-2 dni)
   - Modify: `mexc_futures_adapter.py`
   - Wrap: `place_futures_order()`, `set_leverage()`, `get_position()`
   - Tests: failure scenarios, retry logic

3. **Live Position Monitor UI** (2-3 dni)
   - Create: `PositionMonitor.tsx`
   - WebSocket: subscribe "position_update"
   - Real-time: P&L, leverage, liquidation distance

4. **Fix Connection Pool Race** (0.5 dni)
   - Add: `asyncio.Lock` in `paper_trading_persistence.py`
   - Test: concurrent session creation

**Deliverable:** Safe live trading with real-time monitoring

### Sprint 2 (Tydzień 3-4): HIGH Priority Features

5. **Paper Trading Dashboard** (3-4 dni)
6. **Backtest UI Update** (2-3 dni)
7. **Order Retry Integration** (1-2 dni)

**Deliverable:** Complete testing infrastructure

### Sprint 3 (Tydzień 5): MEDIUM Priority Polish

8. **Client-Side Validation** (0.5 dni)
9. **Enhanced Error Handling** (1-2 dni)
10. **WebSocket Reconnection** (1 dzień)

**Deliverable:** Production-ready UX

---

## 10. ZAŁĄCZNIKI - Kluczowe Lokalizacje Kodu

### Backend (Core)

```
src/domain/services/
├── strategy_manager.py:1532-1635    # Emergency Exit (✅ IMPLEMENTED)
├── order_manager.py:165-186         # Liquidation calculation (✅ EXISTS)
├── order_manager.py:82-90           # Position tracking (✅ EXISTS)
└── paper_trading_persistence.py:80-96  # Race condition (⚠️ BUG)

src/infrastructure/adapters/
└── mexc_futures_adapter.py:107-108  # Leverage validation (✅ IMPLEMENTED)
                                     # Circuit breaker (❌ NOT INTEGRATED)

src/core/
└── circuit_breaker.py:53-375        # Circuit breaker & retry (✅ CODE READY)

src/api/
└── paper_trading_routes.py:107-430  # 8 API endpoints (✅ IMPLEMENTED)
```

### Frontend (UI)

```
frontend/src/
├── app/
│   ├── trading/page.tsx:480-481         # Session type selector (✅ EXISTS)
│   └── backtesting/page.tsx:1-1046      # Backtest UI (⚠️ NEEDS UPDATE)
│
├── components/strategy/
│   └── StrategyBuilder5Section.tsx:1693-1801  # Emergency Exit config (✅ EXISTS)
│
└── utils/
    └── leverageCalculator.ts:34-53      # Liquidation formulas (✅ IMPLEMENTED)
```

### Missing Components (DO DODANIA)

```
src/domain/services/
└── liquidation_monitor.py               # ❌ TO CREATE

frontend/src/
├── components/trading/
│   ├── PositionMonitor.tsx             # ❌ TO CREATE
│   ├── LiquidationAlert.tsx            # ❌ TO CREATE
│   └── PositionCard.tsx                # ❌ TO CREATE
│
├── components/paper-trading/
│   ├── PaperTradingDashboard.tsx       # ❌ TO CREATE
│   └── SessionControls.tsx             # ❌ TO CREATE
│
└── app/paper-trading/
    └── page.tsx                         # ❌ TO CREATE
```

---

## Podsumowanie

**System TIER 1 SHORT Selling jest zaawansowany (~75% kompletności), ale wymaga krytycznych uzupełnień:**

✅ **CO DZIAŁA:**
- Emergency Exit (user-configured protection)
- Leverage support (1-200x)
- SHORT order mapping (MEXC API)
- Paper Trading backend (8 endpoints)
- Liquidation price calculation
- Circuit breaker & retry code (ready to use)

❌ **CO BRAKUJE:**
- Automatic liquidation monitoring (CRITICAL)
- Live position monitor UI (CRITICAL)
- Paper trading dashboard UI
- Circuit breaker integration with MEXC
- Backtest UI update (5-section strategies)

⚠️ **CO WYMAGA NAPRAWY:**
- Connection pool race condition
- Client-side leverage validation
- Order retry integration

**Rekomendacja:** Wykonać Sprint 1 (CRITICAL fixes) **PRZED** uruchomieniem live trading. Estimated time: **6.5-10.5 dni**.
