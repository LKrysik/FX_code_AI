# Kompleksowa Analiza Live Trading i Paper Trading
**Data:** 2025-11-05
**Status:** Krytyczne braki w implementacji - system nie działa

---

## Executive Summary

**KRYTYCZNY PROBLEM:** Live trading i paper trading mają kompletną infrastrukturę (adaptery, bazy danych, frontend), ale **brakuje połączenia między komponentami**. System przypomina samochód z silnikiem, kołami i kierownicą, gdzie **nie podłączono przekładni** między silnikiem a kołami.

### Główne Braki
1. ❌ **Brak Signal → Order Flow** - Sygnały z strategii nigdy nie prowadzą do zleceń
2. ❌ **LiveOrderManager** - Niekompletna implementacja (tylko `set_leverage()`)
3. ❌ **Brak Real-time Position Sync** - Pozycje z giełdy nie są synchronizowane
4. ❌ **Brak Indicator → Strategy Connection** - Wskaźniki nie są połączone ze strategiami w live trading
5. ❌ **Frontend Monitoring** - Brak wykresów z sygnałami, pozycjami, orderami w czasie rzeczywistym

---

## CZĘŚĆ I: Analiza Istniejącej Implementacji

### 1.1 Co DZIAŁA (Paper Trading - Kompletne)

#### A. MexcPaperAdapter (`src/infrastructure/adapters/mexc_paper_adapter.py`)
**Status: ✅ KOMPLETNY - 494 linii kodu**

```python
class MexcPaperAdapter:
    """Kompletna symulacja tradingu z leveraged futures"""

    # ✅ Funkcjonalności:
    - Leverage 1-200x
    - SHORT i LONG positions
    - Slippage simulation (0.01-0.1%)
    - Funding rate calculation
    - Liquidation price tracking
    - Position averaging
    - Unrealized P&L
    - Order history
```

**Kluczowe metody:**
- `place_futures_order()` - Natychmiastowe wypełnienie zleceń
- `get_position()` - Pozycja z P&L
- `set_leverage()` - Ustawienie dźwigni
- `calculate_liquidation_price()` - Poziom likwidacji

#### B. Database Schema (Migration 013)
**Status: ✅ KOMPLETNY**

```sql
-- 4 tabele paper trading:
1. paper_trading_sessions - Metadata sesji
2. paper_trading_orders - Historia zleceń z P&L
3. paper_trading_positions - Snapshoty pozycji
4. paper_trading_performance - Metryki w czasie
```

**Pełne wsparcie:**
- SHORT/LONG positions
- Leverage tracking
- Slippage tracking
- Funding costs
- Performance metrics (Sharpe, Sortino, max drawdown)

#### C. Frontend Paper Trading
**Status: ✅ KOMPLETNY - `/frontend/src/app/paper-trading/page.tsx`**

- Tworzenie sesji z wyborem strategii
- Wybór symboli i kierunku (LONG/SHORT/BOTH)
- Leverage selector (1-10x)
- Lista sesji z filtrowaniem
- Performance metrics
- Szczegóły sesji: ordery, pozycje, P&L

### 1.2 Co ISTNIEJE ale Jest Niekompletne

#### A. MexcFuturesAdapter (Live Trading)
**Status: ⚠️ CZĘŚCIOWO KOMPLETNY**

**Istnieje (`mexc_futures_adapter.py`):**
```python
- set_leverage() - ✅ Działa
- place_futures_order() - ✅ Działa
- get_position() - ✅ Działa
- get_funding_rate() - ✅ Działa
- close_position() - ✅ Działa
- Circuit breaker (3 retries, exponential backoff) - ✅ Działa
```

**Problem:** Adapter jest kompletny, ale **NIGDZIE NIE UŻYWANY** w flow execution.

#### B. LiveOrderManager
**Status: ⚠️ BARDZO NIEKOMPLETNY - `src/domain/services/order_manager_live.py`**

```python
class LiveOrderManager(OrderManager):
    def set_leverage(self, symbol: str, leverage: float):
        # ✅ Zaimplementowane (paper fallback)
        if self.mexc_adapter:
            return await self.mexc_adapter.set_leverage(symbol, leverage)
        else:
            # Paper mode fallback

    def submit_order(...):
        # ❌ BRAK IMPLEMENTACJI
        # Powinno:
        # 1. Wywołać mexc_adapter.place_futures_order()
        # 2. Zapisać do bazy
        # 3. Broadcast WebSocket

    def cancel_order(...):
        # ❌ BRAK IMPLEMENTACJI

    def get_position(...):
        # ❌ BRAK IMPLEMENTACJI (powinno sync z MEXC)
```

**Co brakuje:**
1. `submit_order()` - Brak wywołania MEXC API
2. `cancel_order()` - Nie zaimplementowane
3. `get_position()` - Brak synchronizacji z giełdą
4. Position reconciliation - Okresowa synchronizacja

#### C. ExecutionController
**Status: ⚠️ GENERYCZNY - Brak specyfiki live trading**

```python
# execution_controller.py
async def _execution_loop(self):
    """Generic loop - brak live trading logic"""
    while self.state == ExecutionState.RUNNING:
        # 1. Process market data
        # 2. Update indicators (StreamingIndicatorEngine)
        # 3. ??? Brak wywołania strategy evaluation ???
        # 4. ??? Brak order placement ???
```

**Problem:** Pętla jest uniwersalna dla wszystkich trybów (backtest, live, collect), ale **nie ma różnicowania logiki** dla live trading.

#### D. StrategyManager
**Status: ✅ KOMPLETNY - ale NIE POŁĄCZONY z execution**

**5-sekcyjna architektura (zgodna z user_feedback.md):**
```python
class Strategy:
    # S1: Signal Detection - Wykrywanie pompek
    signal_detection: ConditionGroup

    # O1: Signal Cancellation - Anulowanie sygnału
    signal_cancellation: ConditionGroup

    # Z1: Entry Conditions - Warunki wejścia
    entry_conditions: ConditionGroup

    # ZE1: Close Order Detection - Warunki zamknięcia
    close_order_detection: ConditionGroup

    # E1: Emergency Exit - Awaryjne wyjście
    emergency_exit: ConditionGroup
```

**Evaluation Flow - DZIAŁA:**
```python
# State Machine (strategy_manager.py, linie 1324-1649)
INACTIVE → MONITORING
    ↓ (S1 TRUE)
SIGNAL_DETECTED
    ↓ (O1 TRUE → SIGNAL_CANCELLED + cooldown)
    ↓ (Z1 TRUE)
ENTRY_EVALUATION → (Risk check + Order submission)
    ↓
POSITION_ACTIVE
    ↓ (ZE1 TRUE)
CLOSE_ORDER_EVALUATION → (Close order)
    ↓ (E1 TRUE)
EMERGENCY_EXIT → (Emergency close)
    ↓
EXITED
```

**CO DZIAŁA:**
1. ✅ Evaluation conditions against indicator values
2. ✅ State transitions (MONITORING → SIGNAL → ENTRY → POSITION → EXIT)
3. ✅ Risk-adjusted position sizing
4. ✅ Cooldown management (O1: 5 min, E1: 30 min)
5. ✅ Slot management (max 3 concurrent signals)
6. ✅ Symbol locking (one strategy per symbol)
7. ✅ QuestDB persistence

**CO NIE DZIAŁA:**
- ❌ Order submission w `_evaluate_strategy()` (linia 1507-1515) wywołuje `order_manager.submit_order()`, ale:
  - OrderManager jest paper-only
  - LiveOrderManager nie ma implementacji `submit_order()`
  - Więc ordery trafiają do in-memory storage, NIE NA GIEŁDĘ

### 1.3 Co Całkowicie BRAKUJE

#### A. Signal → Order Execution Flow
**Najbardziej krytyczny brak**

```python
# Co POWINNO się dziać (ale nie dzieje):

# 1. Market Data Arrival
MarketData → EventBus.publish("market_data")

# 2. Indicator Calculation
StreamingIndicatorEngine → EventBus.publish("indicator_updated")

# 3. Strategy Evaluation
StrategyManager subscribes → Evaluate conditions → Generate signal

# 4. ❌ MISSING: Signal to Order
# Powinno być:
signal = StrategyManager.evaluate()
if signal.action == "BUY":
    order = await RiskManager.validate(signal)
    if order.approved:
        # ❌ TU NIE MA KODU:
        await LiveOrderManager.submit_order(order)
        await EventBus.publish("order_created", order)

# 5. ❌ MISSING: Order Status Updates
# Po złożeniu zlecenia na MEXC:
# - Brak śledzenia statusu (FILLED, PARTIAL, CANCELLED)
# - Brak WebSocket broadcast do frontendu
# - Brak zapisu do bazy
```

#### B. Real-time Position Synchronization

```python
# ❌ BRAK:
class PositionSyncService:
    """Periodic sync with exchange positions"""

    async def sync_positions_with_exchange(self):
        """Every 10 seconds"""
        # 1. Get positions from MEXC
        exchange_positions = await mexc_adapter.get_all_positions()

        # 2. Compare with local positions
        local_positions = await db.get_open_positions()

        # 3. Reconcile differences
        # - Missing positions (opened outside app)
        # - Closed positions (liquidated)
        # - P&L updates

        # 4. Broadcast updates
        await event_bus.publish("position_updated", positions)
```

#### C. Wallet Balance Tracking

```python
# ❌ BRAK:
class WalletService:
    """Real-time wallet balance from MEXC"""

    async def get_balance(self) -> Dict[str, float]:
        # Query MEXC balance
        balance = await mexc_adapter.get_futures_balance()
        # {
        #   "available": 1000.0,
        #   "margin_used": 200.0,
        #   "unrealized_pnl": 50.0
        # }

    async def monitor_margin_ratio(self):
        # Alert if margin < threshold
```

#### D. WebSocket Real-time Updates

**Brakujące message types:**
```typescript
// ❌ MISSING in message_router.py:
"order_created" - Nowe zlecenie
"order_filled" - Zlecenie wypełnione
"order_cancelled" - Zlecenie anulowane
"position_opened" - Nowa pozycja
"position_updated" - Update P&L
"position_closed" - Pozycja zamknięta
"signal_generated" - Nowy sygnał strategii
"balance_updated" - Zmiana salda
```

#### E. Backtest Results Persistence

```sql
-- ❌ MISSING TABLE:
CREATE TABLE backtest_results (
    session_id STRING,
    strategy_name STRING,
    symbol STRING,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    initial_balance DOUBLE,
    final_balance DOUBLE,
    total_pnl DOUBLE,
    total_trades INT,
    win_rate DOUBLE,
    sharpe_ratio DOUBLE,
    max_drawdown DOUBLE,
    -- Trade-by-trade results
    trades_json STRING  -- Pełne szczegóły
);
```

#### F. Signal History Table

```sql
-- ❌ MISSING TABLE:
CREATE TABLE signal_history (
    signal_id STRING,
    session_id STRING,
    strategy_name STRING,
    symbol STRING,
    signal_type STRING,  -- S1, Z1, ZE1, E1
    action STRING,  -- BUY, SELL, HOLD
    confidence DOUBLE,
    indicator_values STRING,  -- JSON snapshot
    order_id STRING,  -- NULL if not executed
    timestamp TIMESTAMP
);
```

---

## CZĘŚĆ II: Perspektywa Tradera - Wymagania Interfejsu

### 2.1 Krytyczne Wymagania (Must-Have)

Jako trader grający na pump & dump **MUSZĘ** widzieć:

#### A. Real-time Chart z Sygnałami (Najważniejsze)
**Uzasadnienie:** Bez wykresu jestem ślepy. Nie widzę momentu wejścia/wyjścia.

```
┌─────────────────────────────────────────────────────────────┐
│ BTC_USDT - Live Trading                    📊 TradingView   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│   Price Chart                                                │
│   ┌───────────────────────────────────────────────────────┐ │
│   │                          /\                           │ │
│   │                         /  \    ← PUMP!               │ │
│   │              ▼ E1     /    \                          │ │
│   │             /       /      \                          │ │
│   │            /       /        \                         │ │
│   │   ▲ Z1   /       /          \                        │ │
│   │  /      /       /            \                       │ │
│   │ /  ▲ S1/       /              \                      │ │
│   │/      /       /                \___                  │ │
│   └───────────────────────────────────────────────────────┘ │
│                                                               │
│   Indicators (overlay):                                      │
│   ├─ TWAP (300s, 0s) - Blue line                           │
│   ├─ Velocity - Green/Red bars                             │
│   └─ Volume Surge - Yellow highlights                      │
│                                                               │
│   Signals (markers):                                         │
│   ├─ S1 (🔔 Signal Detected) - Yellow diamond               │
│   ├─ Z1 (🎯 Entry) - Green arrow up                        │
│   ├─ ZE1 (💰 Take Profit) - Blue arrow down                │
│   └─ E1 (🚨 Emergency Exit) - Red X                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Wymagania techniczne:**
- Świece 1-minutowe (lub 5s dla high-frequency)
- Overlays dla wskaźników (TWAP, Velocity, Volume)
- Markery sygnałów z tooltipem (timestamp, confidence, indicator values)
- Zoom/pan dla analizy historycznej
- Highlight pozycji otwartej (entry price, current P&L)

#### B. Live Position Monitor (Krytyczny)
**Uzasadnienie:** Muszę widzieć czy zarabiam czy tracę **natychmiast**.

```
┌─────────────────────────────────────────────────────────────┐
│ Open Positions                                   [Refresh]   │
├─────────────────────────────────────────────────────────────┤
│ BTC_USDT | SHORT | 0.05 BTC                                 │
│ Entry: $67,500 | Current: $66,200 | Leverage: 3x           │
│ Unrealized P&L: +$195 (+8.9%) 🟢                           │
│ Liquidation: $69,800 (margin safe: 85%)                    │
│ Duration: 12m 34s | Strategy: flash_pump_detection         │
│ [Close Position] [Set Stop Loss] [Take Profit]             │
├─────────────────────────────────────────────────────────────┤
│ ETH_USDT | LONG | 1.2 ETH                                   │
│ Entry: $3,100 | Current: $3,050 | Leverage: 2x             │
│ Unrealized P&L: -$60 (-1.9%) 🔴                            │
│ Liquidation: $2,480 (margin safe: 92%)                     │
│ Duration: 3m 12s | Strategy: pump_dump_detection           │
│ [Close Position] [Set Stop Loss] [Take Profit]             │
└─────────────────────────────────────────────────────────────┘
```

**Wymagania:**
- Update co 1-2 sekundy (WebSocket)
- Color-coded P&L (zielony: zysk, czerwony: strata)
- Margin ratio warning (< 80%: żółty, < 50%: czerwony)
- One-click close button
- Funding cost counter (aktualizowany co funding period)

#### C. Order History & Status
**Uzasadnienie:** Weryfikacja wykonania + analiza slippage.

```
┌─────────────────────────────────────────────────────────────┐
│ Orders (Last 50)                       [Filter: All ▼]      │
├─────────────────────────────────────────────────────────────┤
│ Time       │Symbol   │Type  │Side  │Qty  │Price  │Status  │
├────────────┼─────────┼──────┼──────┼─────┼───────┼────────┤
│ 14:23:45   │BTC_USDT │MARKET│SHORT │0.05 │67,500 │FILLED ✅│
│ 14:22:10   │ETH_USDT │LIMIT │LONG  │1.2  │3,100  │FILLED ✅│
│ 14:20:30   │BTC_USDT │MARKET│COVER │0.1  │68,200 │FILLED ✅│
│            │         │      │      │     │Profit: +$170 🟢│
│ 14:15:22   │ADA_USDT │LIMIT │BUY   │500  │0.52   │CANCELLED│
│ 14:10:05   │SOL_USDT │MARKET│SHORT │2.0  │105.30 │REJECTED❌│
│            │         │      │      │Reason: Insufficient margin │
└─────────────────────────────────────────────────────────────┘
```

**Kluczowe informacje:**
- Timestamp (precyzja: sekundy)
- Order type (MARKET vs LIMIT)
- Execution price vs requested price (slippage %)
- Status z ikoną (FILLED, PARTIAL, CANCELLED, REJECTED)
- Realized P&L dla closing orders
- Reason for rejection/cancellation

#### D. Strategy State Dashboard
**Uzasadnienie:** Widzę co strategia "myśli" i czy działa.

```
┌─────────────────────────────────────────────────────────────┐
│ Active Strategies                                            │
├─────────────────────────────────────────────────────────────┤
│ pump_dump_detection │ BTC_USDT │ POSITION_ACTIVE 🟢         │
│ ├─ State: Monitoring ZE1 close conditions                   │
│ ├─ Entry: 12m ago @ $67,500 (SHORT)                        │
│ ├─ Current P&L: +$195 (+8.9%)                              │
│ ├─ Indicator Values:                                        │
│ │  ├─ pump_magnitude_pct: -1.8% (below threshold)          │
│ │  ├─ volume_surge_ratio: 0.8x (declining)                 │
│ │  └─ unrealized_pnl_pct: +8.9% (close threshold: 15%)    │
│ └─ Next Action: ZE1 at 15% profit OR E1 if reversal        │
├─────────────────────────────────────────────────────────────┤
│ flash_pump_detection │ ETH_USDT │ MONITORING 🟡             │
│ ├─ State: Waiting for S1 signal                            │
│ ├─ Last Signal: 3m ago (cancelled - O1 triggered)          │
│ ├─ Cooldown: 2m remaining                                  │
│ ├─ Indicator Values:                                        │
│ │  ├─ pump_magnitude_pct: +2.1% (threshold: 5%)           │
│ │  ├─ price_momentum: +3.2 (threshold: 3.0)               │
│ │  └─ signal_age_seconds: N/A                             │
│ └─ Next Action: Monitoring for pump acceleration           │
└─────────────────────────────────────────────────────────────┘
```

**Kluczowe elementy:**
- Current state (MONITORING, SIGNAL_DETECTED, POSITION_ACTIVE, etc.)
- State transition history (last 5 states)
- Real-time indicator values vs thresholds
- Time in current state
- Next expected action
- Cooldown status (jeśli aktywny)

#### E. Real-time Performance Metrics
**Uzasadnienie:** Czy strategia jest profitable?

```
┌─────────────────────────────────────────────────────────────┐
│ Session Performance                      [Last 24h ▼]       │
├─────────────────────────────────────────────────────────────┤
│ Total P&L: +$1,245.50 (+12.5%) 🟢                          │
│ Realized: +$980.20 | Unrealized: +$265.30                  │
│                                                              │
│ Trades: 45 (32W / 13L) | Win Rate: 71.1%                   │
│ Avg Win: +$52.30 | Avg Loss: -$28.10 | Profit Factor: 2.42 │
│                                                              │
│ Best Trade: +$195 (BTC_USDT SHORT)                         │
│ Worst Trade: -$85 (SOL_USDT LONG)                          │
│                                                              │
│ Max Drawdown: -3.2% (recovered)                            │
│ Sharpe Ratio: 2.15 | Sortino Ratio: 3.42                   │
│                                                              │
│ Commission: -$18.50 | Funding Costs: -$6.20                │
└─────────────────────────────────────────────────────────────┘
```

**Dane w czasie rzeczywistym:**
- Total P&L (realized + unrealized)
- Win rate, profit factor
- Risk metrics (Sharpe, Sortino, max drawdown)
- Costs breakdown (commission, funding)

### 2.2 Przydatne Features (Should-Have)

#### A. Signal Log (Analiza post-mortem)
```
┌─────────────────────────────────────────────────────────────┐
│ Signal History (Last 100)                                    │
├─────────────────────────────────────────────────────────────┤
│ 14:23:30 │ pump_dump_detection │ BTC_USDT │ Z1 ENTRY 🎯    │
│ Confidence: 85% │ Action: SHORT @ $67,500                   │
│ Indicators: pump_magnitude: 9.2%, volume_surge: 4.5x       │
│ Result: Order FILLED → Position opened                      │
├─────────────────────────────────────────────────────────────┤
│ 14:20:15 │ flash_pump_detection │ ETH_USDT │ O1 CANCELLED 🔕│
│ Confidence: 65% │ Reason: Signal timeout (5m)              │
│ Indicators: pump_magnitude: 3.8% (dropped from 5.5%)       │
│ Result: No trade, cooldown started (3m)                    │
└─────────────────────────────────────────────────────────────┘
```

**Dlaczego przydatne:**
- Post-mortem analysis (why signal fired/cancelled)
- Confidence calibration (czy wysokie confidence = profitable?)
- Indicator thresholds tuning

#### B. Risk Alerts
```
┌─────────────────────────────────────────────────────────────┐
│ Risk Alerts                                     [Clear All]  │
├─────────────────────────────────────────────────────────────┤
│ ⚠️  BTC_USDT: Margin ratio 72% (below 80% threshold)       │
│     Consider closing position or adding margin              │
├─────────────────────────────────────────────────────────────┤
│ 🔴 ETH_USDT: Unrealized loss -5.2% (stop loss: -8%)       │
│     Position approaching stop loss level                    │
├─────────────────────────────────────────────────────────────┤
│ 🟡 Global: 3 open positions (limit: 3)                     │
│     No new positions can be opened                          │
└─────────────────────────────────────────────────────────────┘
```

#### C. Indicator Overlay Configuration
```
┌─────────────────────────────────────────────────────────────┐
│ Chart Indicators                                             │
├─────────────────────────────────────────────────────────────┤
│ ☑ TWAP (300s, 0s) - [Color: Blue] [Width: 2]              │
│ ☑ Velocity - [Color: Green/Red] [Style: Bars]             │
│ ☑ Volume Surge - [Highlight: Yellow] [Threshold: 3x]      │
│ ☑ Pump Magnitude - [Overlay: Percentage] [Show: Labels]   │
│ ☐ RSI - [Position: Below] [Period: 14]                    │
│ ☐ MACD - [Position: Below] [Settings: 12,26,9]            │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Nice-to-Have (Ale nie krytyczne)

#### A. Strategy Performance Comparison
- Side-by-side comparison: pump_dump_detection vs flash_pump_detection
- Which strategy is more profitable?
- Which has better win rate?

#### B. Trade Replay
- Odtworzenie sesji backtest/live z sygnałami
- Frame-by-frame analysis (co się działo przed sygnałem)

#### C. Notification System
- Browser notifications dla sygnałów S1/E1
- Telegram/Discord integration
- Email alerts dla krytycznych eventów

### 2.4 Co NIE jest potrzebne (Waste of Time)

❌ **Advanced charting tools** - Nie potrzebujemy drawing tools (lines, Fibonacci, etc.)
❌ **Order book depth visualization** - Nie trading na order flow
❌ **Social trading features** - Copy trading, leaderboards
❌ **Backtesting z UI** - Jest dedykowana strona
❌ **Multi-timeframe analysis** - Pump & dump = 1-5 min focus

---

## CZĘŚĆ III: Database Schema - Co Dodać

### 3.1 Live Trading Sessions

```sql
CREATE TABLE live_trading_sessions (
    session_id STRING PRIMARY KEY,
    strategy_ids STRING,  -- Comma-separated
    symbols STRING,  -- Comma-separated
    session_type STRING,  -- 'live' or 'paper'
    status STRING,  -- RUNNING, PAUSED, STOPPED, ERROR
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    initial_balance DOUBLE,
    current_balance DOUBLE,
    total_pnl DOUBLE,
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate DOUBLE,
    max_drawdown DOUBLE,
    sharpe_ratio DOUBLE,
    created_by STRING
) timestamp(start_time) PARTITION BY DAY WAL;

CREATE INDEX idx_live_sessions_id ON live_trading_sessions (session_id);
CREATE INDEX idx_live_sessions_status ON live_trading_sessions (status);
```

### 3.2 Signal History

```sql
CREATE TABLE signal_history (
    signal_id STRING PRIMARY KEY,
    session_id STRING,
    strategy_name STRING,
    symbol STRING,
    signal_type STRING,  -- S1, O1, Z1, ZE1, E1
    action STRING,  -- BUY, SELL, SHORT, COVER, HOLD
    confidence DOUBLE,
    indicator_values STRING,  -- JSON: {"pump_magnitude_pct": 9.2, ...}
    order_id STRING,  -- NULL if not executed
    execution_status STRING,  -- PENDING, EXECUTED, CANCELLED, REJECTED
    rejection_reason STRING,
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY WAL;

CREATE INDEX idx_signals_session ON signal_history (session_id);
CREATE INDEX idx_signals_strategy ON signal_history (strategy_name);
CREATE INDEX idx_signals_symbol ON signal_history (symbol);
```

### 3.3 Live Orders

```sql
CREATE TABLE live_orders (
    order_id STRING PRIMARY KEY,
    session_id STRING,
    strategy_name STRING,
    symbol STRING,
    side STRING,  -- BUY, SELL
    position_side STRING,  -- LONG, SHORT
    order_type STRING,  -- MARKET, LIMIT
    quantity DOUBLE,
    requested_price DOUBLE,
    execution_price DOUBLE,
    slippage_pct DOUBLE,
    leverage DOUBLE,
    status STRING,  -- PENDING, FILLED, PARTIAL, CANCELLED, REJECTED
    rejection_reason STRING,
    commission DOUBLE,
    realized_pnl DOUBLE,  -- For closing orders
    signal_id STRING,  -- Link to signal_history
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY WAL;

CREATE INDEX idx_live_orders_session ON live_orders (session_id);
CREATE INDEX idx_live_orders_symbol ON live_orders (symbol);
CREATE INDEX idx_live_orders_status ON live_orders (status);
```

### 3.4 Live Positions

```sql
CREATE TABLE live_positions (
    position_id STRING PRIMARY KEY,
    session_id STRING,
    symbol STRING,
    position_side STRING,  -- LONG, SHORT
    quantity DOUBLE,
    entry_price DOUBLE,
    current_price DOUBLE,
    leverage DOUBLE,
    liquidation_price DOUBLE,
    unrealized_pnl DOUBLE,
    unrealized_pnl_pct DOUBLE,
    margin_used DOUBLE,
    margin_ratio DOUBLE,  -- Percentage of maintenance margin
    funding_cost_accrued DOUBLE,
    strategy_name STRING,
    entry_signal_id STRING,  -- Link to signal_history
    status STRING,  -- OPEN, CLOSED
    close_timestamp TIMESTAMP,
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY WAL;

CREATE INDEX idx_live_positions_session ON live_positions (session_id);
CREATE INDEX idx_live_positions_symbol ON live_positions (symbol);
CREATE INDEX idx_live_positions_status ON live_positions (status);
```

### 3.5 Backtest Results

```sql
CREATE TABLE backtest_results (
    session_id STRING PRIMARY KEY,
    strategy_name STRING,
    symbols STRING,  -- Comma-separated
    data_collection_session_id STRING,  -- Link to data source
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    initial_balance DOUBLE,
    final_balance DOUBLE,
    total_pnl DOUBLE,
    total_return_pct DOUBLE,
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate DOUBLE,
    profit_factor DOUBLE,
    average_win DOUBLE,
    average_loss DOUBLE,
    max_drawdown DOUBLE,
    sharpe_ratio DOUBLE,
    sortino_ratio DOUBLE,
    calmar_ratio DOUBLE,
    trades_json STRING,  -- Full trade-by-trade details
    equity_curve_json STRING,  -- [{timestamp, equity}]
    created_at TIMESTAMP
) timestamp(start_time) PARTITION BY DAY;

CREATE INDEX idx_backtest_strategy ON backtest_results (strategy_name);
CREATE INDEX idx_backtest_data_session ON backtest_results (data_collection_session_id);
```

---

## CZĘŚĆ IV: Strategy-Based Execution Flow

### 4.1 Obecny Stan (Disconnected)

```
┌──────────────────────────────────────────────────────────────┐
│                    CURRENT (BROKEN) FLOW                      │
└──────────────────────────────────────────────────────────────┘

Market Data (MEXC)
    ↓
EventBus.publish("market_data")
    ↓
StreamingIndicatorEngine
    ↓ Calculates indicators
EventBus.publish("indicator_updated")
    ↓
StrategyManager._on_indicator_update()
    ↓ Evaluates strategy
Strategy.evaluate() → Signal generated
    ↓
OrderManager.submit_order() [PAPER MODE ONLY]
    ↓ ❌ NIE MA POŁĄCZENIA Z MEXC
In-memory order tracking
    ↓
❌ NIE MA FEEDBACK DO FRONTENDU
❌ NIE MA REAL ORDERS NA GIEŁDZIE
```

### 4.2 Docelowy Flow (Kompletny)

```
┌──────────────────────────────────────────────────────────────┐
│                    TARGET (COMPLETE) FLOW                     │
└──────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════╗
║ PHASE 1: Data Ingestion                                   ║
╚═══════════════════════════════════════════════════════════╝

MEXC WebSocket (wss://contract.mexc.com/edge)
    ↓
MarketDataProviderAdapter.on_message()
    ↓ Parse price, volume, timestamp
EventBus.publish("market.price_update", {
    symbol: "BTC_USDT",
    price: 67500.0,
    volume: 123.45,
    timestamp: 1730825000
})
    ↓
StreamingIndicatorEngine subscribes
    ↓ FOR EACH active indicator:
    ├─ TWAP (300s, 0s) - Ring buffer update → Calculate
    ├─ Velocity - Price delta → Calculate
    └─ Volume_Surge - Volume ratio → Calculate
    ↓
EventBus.publish("indicator.updated", {
    symbol: "BTC_USDT",
    indicator: "pump_magnitude_pct",
    value: 9.2,
    confidence: 0.85,
    timestamp: 1730825000
})

╔═══════════════════════════════════════════════════════════╗
║ PHASE 2: Strategy Evaluation                              ║
╚═══════════════════════════════════════════════════════════╝

StrategyManager._on_indicator_update()
    ↓ Update indicator cache:
    indicator_values["BTC_USDT"]["pump_magnitude_pct"] = 9.2
    ↓
FOR EACH active_strategy in active_strategies["BTC_USDT"]:
    ↓
    _evaluate_strategy(strategy, indicator_values)
        ↓
        ┌─────────────────────────────────────────────┐
        │ State Machine (5-Section Architecture)      │
        └─────────────────────────────────────────────┘

        CASE strategy.current_state:

        [MONITORING]:
            ├─ S1: evaluate_signal_detection()
            │  └─ pump_magnitude_pct >= 8.0? ✅
            │  └─ volume_surge_ratio >= 3.0? ✅
            │  └─ price_momentum >= 5.0? ✅
            │  → ALL TRUE
            ├─ Acquire signal slot (max 3 concurrent)
            ├─ Lock symbol (one strategy per symbol)
            ├─ Record indicator values at S1
            ├─ Transition: MONITORING → SIGNAL_DETECTED
            └─ EventBus.publish("strategy.signal_detected", {
                strategy_name: "pump_dump_detection",
                symbol: "BTC_USDT",
                confidence: 0.85,
                indicator_values: {...}
              })

        [SIGNAL_DETECTED]:
            ├─ O1: evaluate_signal_cancellation()
            │  └─ pump_magnitude_pct <= -2.0? ❌
            │  → NOT cancelled
            ├─ Z1: evaluate_entry_conditions()
            │  └─ rsi between (40, 80)? ✅
            │  └─ spread_pct <= 1.0? ✅
            │  → ENTRY CONDITIONS MET
            ├─ Transition: SIGNAL_DETECTED → ENTRY_EVALUATION
            └─ EventBus.publish("strategy.entry_conditions_met")

        [ENTRY_EVALUATION]:
            ├─ Calculate position size (risk-adjusted)
            │  ├─ base_size = 0.3 (30% of capital)
            │  ├─ risk_multiplier = f(risk_indicator)
            │  └─ position_size = $300
            ├─ RiskManager.assess_position_risk()
            │  ├─ Check max_position_size: $300 < $500 ✅
            │  ├─ Check volatility: acceptable ✅
            │  ├─ Check margin ratio: 85% > 50% ✅
            │  └─ APPROVED
            ├─ RiskManager.use_budget($300)
            │  └─ Reserve funds
            ├─ ✅ CRITICAL: LiveOrderManager.submit_order()
            │  ├─ order_type = strategy.get_entry_order_type()
            │  │  └─ SHORT (for pump_dump_detection)
            │  ├─ leverage = 3x
            │  ├─ quantity = $300 / $67,500 = 0.00444 BTC
            │  └─ MexcFuturesAdapter.place_futures_order(
            │       symbol="BTC_USDT",
            │       side="SELL",
            │       position_side="SHORT",
            │       order_type="MARKET",
            │       quantity=0.00444,
            │       leverage=3
            │     )
            │     ↓
            │     MEXC API Response:
            │     {
            │       "order_id": "12345",
            │       "status": "FILLED",
            │       "execution_price": 67480.0,
            │       "commission": 0.50
            │     }
            ├─ Save to QuestDB: live_orders table
            ├─ Transition: ENTRY_EVALUATION → POSITION_ACTIVE
            └─ EventBus.publish("strategy.position_opened", {
                order_id: "12345",
                entry_price: 67480.0,
                quantity: 0.00444,
                leverage: 3
              })

        [POSITION_ACTIVE]:
            ├─ E1: evaluate_emergency_exit() (priority)
            │  └─ pump_magnitude_pct <= -5.0? ❌
            │  └─ volume_surge_ratio >= 5.0? ❌
            │  → NO emergency
            ├─ ZE1: evaluate_close_order_detection()
            │  └─ unrealized_pnl_pct >= 15.0? ❌ (currently 8.9%)
            │  └─ price_momentum <= 1.0? ❌ (still 2.5)
            │  → NOT yet
            └─ Continue monitoring...

        [CLOSE_ORDER_EVALUATION]:
            ├─ Calculate risk-adjusted close price
            │  └─ adjustment = f(risk_indicator)
            │  └─ close_price = current_price * (1 + adjustment)
            ├─ ✅ CRITICAL: LiveOrderManager.close_position()
            │  └─ MexcFuturesAdapter.place_futures_order(
            │       symbol="BTC_USDT",
            │       side="BUY",  -- Cover SHORT
            │       position_side="SHORT",
            │       order_type="MARKET",
            │       quantity=0.00444
            │     )
            │     ↓
            │     MEXC API Response:
            │     {
            │       "order_id": "12346",
            │       "status": "FILLED",
            │       "execution_price": 66200.0,
            │       "realized_pnl": 195.0
            │     }
            ├─ Save to QuestDB: live_orders (realized_pnl)
            ├─ Release signal slot
            ├─ Unlock symbol
            ├─ Transition: CLOSE_ORDER_EVALUATION → EXITED
            └─ EventBus.publish("strategy.position_closed_ze1", {
                exit_price: 66200.0,
                realized_pnl: 195.0
              })

╔═══════════════════════════════════════════════════════════╗
║ PHASE 3: Real-time Position Sync (Background)            ║
╚═══════════════════════════════════════════════════════════╝

PositionSyncService (every 10 seconds)
    ↓
MexcFuturesAdapter.get_all_positions()
    ↓ [{symbol, side, quantity, unrealized_pnl, ...}]
    ↓
Compare with local positions (QuestDB: live_positions)
    ├─ New positions? → Add to DB + broadcast
    ├─ Closed positions? → Update status + broadcast
    └─ P&L changes? → Update + broadcast
    ↓
EventBus.publish("position.updated", {
    symbol: "BTC_USDT",
    unrealized_pnl: 195.0,
    margin_ratio: 85%
})

╔═══════════════════════════════════════════════════════════╗
║ PHASE 4: WebSocket Broadcasting (to Frontend)            ║
╚═══════════════════════════════════════════════════════════╝

EventBridge subscribes to EventBus events:
    ├─ "strategy.signal_detected"
    ├─ "strategy.position_opened"
    ├─ "strategy.position_closed_ze1"
    ├─ "position.updated"
    └─ "order.status_changed"
    ↓
FOR EACH connected WebSocket client:
    ↓
    ConnectionManager.broadcast({
        type: "position_updated",
        data: {
            symbol: "BTC_USDT",
            unrealized_pnl: 195.0,
            margin_ratio: 85%
        }
    })
    ↓
Frontend receives → Update UI in real-time
```

### 4.3 Konfiguracja Strategii w Live Trading

#### Loader Strategii z QuestDB

```python
# W ExecutionController.start() dla live/paper mode:

async def start_live_trading_session(
    session_id: str,
    symbols: List[str],
    strategy_config: Dict[str, Any]  # {strategy_name: strategy_json}
):
    """
    strategy_config format:
    {
        "pump_dump_detection": {
            "strategy_name": "pump_dump_detection",
            "enabled": True,
            "direction": "SHORT",
            "global_limits": {...},
            "signal_detection": {"conditions": [...]},
            "entry_conditions": {"conditions": [...]},
            ...
        },
        "flash_pump_detection": {...}
    }
    """

    # 1. Load strategies from config
    for strategy_name, strategy_json in strategy_config.items():
        strategy = strategy_manager.create_strategy_from_config(strategy_json)
        strategy_manager.add_strategy(strategy)

    # 2. Activate strategies for symbols
    for symbol in symbols:
        for strategy_name in strategy_config.keys():
            strategy_manager.activate_strategy_for_symbol(strategy_name, symbol)

    # 3. Load indicator variants from strategy config
    #    (Extract required indicators from conditions)
    required_indicators = extract_indicators_from_strategies(strategy_config)
    # required_indicators = [
    #     "pump_magnitude_pct",
    #     "volume_surge_ratio",
    #     "price_momentum",
    #     "rsi",
    #     "spread_pct"
    # ]

    # 4. Create indicator variants in StreamingIndicatorEngine
    for indicator_type in required_indicators:
        # Map condition_type to indicator variant
        variant_id = streaming_engine.get_or_create_variant(
            base_indicator_type=indicator_type,
            parameters=extract_parameters(strategy_config, indicator_type)
        )

        # Register for real-time calculation
        for symbol in symbols:
            streaming_engine.add_indicator_to_session(
                session_id=session_id,
                symbol=symbol,
                variant_id=variant_id
            )

    # 5. Start execution loop
    await execution_controller.start()
```

#### Extract Indicators Helper

```python
def extract_indicators_from_strategies(strategy_config: Dict[str, Any]) -> Set[str]:
    """Extract all unique indicator types from strategy conditions"""
    indicators = set()

    for strategy_json in strategy_config.values():
        # Scan all 5 condition groups
        for group_name in ["signal_detection", "signal_cancellation",
                          "entry_conditions", "close_order_detection",
                          "emergency_exit"]:
            if group_name in strategy_json:
                conditions = strategy_json[group_name].get("conditions", [])
                for condition in conditions:
                    condition_type = condition.get("condition_type")
                    if condition_type:
                        indicators.add(condition_type)

    return indicators

def extract_parameters(strategy_config: Dict[str, Any],
                      indicator_type: str) -> Dict[str, Any]:
    """Extract parameters for indicator from strategy config"""
    # Example: pump_magnitude_pct might have (t1, t2) windows
    # Default parameters from indicator registry
    default_params = {
        "pump_magnitude_pct": {"t1": 300, "t2": 0},
        "volume_surge_ratio": {"t1": 300, "t2": 900},
        "price_momentum": {"t1": 60, "t2": 0},
        "rsi": {"period": 14},
        "spread_pct": {}
    }

    # TODO: Allow strategy to override indicator parameters
    return default_params.get(indicator_type, {})
```

### 4.4 Backtesting Flow (Reuse Strategy Logic)

```
┌──────────────────────────────────────────────────────────────┐
│                   BACKTESTING FLOW                            │
└──────────────────────────────────────────────────────────────┘

User selects data_collection_session_id → POST /sessions/start
    ↓
ExecutionController.start(mode=BACKTEST)
    ↓
Load strategy_config (same as live trading)
    ↓
BacktestMarketDataProvider.initialize()
    ├─ Query QuestDB: tick_prices WHERE session_id = ?
    ├─ Load into memory buffer
    └─ Set acceleration_factor (e.g., 100x for fast replay)
    ↓
FOR EACH timestamp in historical data:
    ├─ Emit market_data event (accelerated time)
    │  └─ EventBus.publish("market_data", {price, volume, timestamp})
    ├─ StreamingIndicatorEngine calculates (or loads from DB)
    │  └─ Check if indicators pre-calculated:
    │     ├─ IF EXISTS in indicators table → Use cached
    │     └─ ELSE → Calculate on-the-fly
    ├─ StrategyManager evaluates
    │  └─ Same state machine as live trading
    ├─ OrderManager (paper mode) executes orders
    │  └─ Simulate fills with slippage
    └─ Track P&L, positions, orders
    ↓
Save backtest_results to QuestDB
    ├─ Final metrics (P&L, win rate, Sharpe)
    ├─ Trade-by-trade details (JSON)
    └─ Equity curve (JSON)
```

**Kluczowa różnica:**
- **Live Trading:** Orders go to MEXC via LiveOrderManager + MexcFuturesAdapter
- **Backtesting:** Orders simulated via OrderManager (paper mode)
- **Same Code:** StrategyManager evaluation logic IDENTICAL

---

## CZĘŚĆ V: Szczegółowy Plan Implementacji

### 5.1 Priority 1: Signal → Order Execution (KRYTYCZNE)

#### Task 1.1: Implement LiveOrderManager.submit_order()

**File:** `src/domain/services/order_manager_live.py`

```python
class LiveOrderManager(OrderManager):
    """Live trading order manager with MEXC integration"""

    def __init__(self, mexc_adapter: Optional[MexcFuturesAdapter],
                 db_pool: Optional[asyncpg.Pool], ...):
        super().__init__(...)
        self.mexc_adapter = mexc_adapter
        self.db_pool = db_pool

    async def submit_order(
        self,
        symbol: str,
        order_type: OrderType,
        quantity: float,
        price: float,
        strategy_name: str,
        pump_signal_strength: float = 0.0,
        leverage: float = 1.0
    ) -> str:
        """Submit order to MEXC (live) or paper mode"""

        # 1. Determine if live or paper
        if self.mexc_adapter and not self.paper_mode:
            # LIVE TRADING PATH
            order_id = await self._submit_live_order(
                symbol, order_type, quantity, price, leverage
            )
        else:
            # PAPER TRADING PATH (existing logic)
            order_id = await self._submit_paper_order(
                symbol, order_type, quantity, price, strategy_name
            )

        # 2. Save to database (live_orders table)
        await self._save_order_to_db(order_id, symbol, order_type, ...)

        # 3. Broadcast via WebSocket
        await self.event_bus.publish("order.created", {
            "order_id": order_id,
            "symbol": symbol,
            "side": order_type.value,
            "quantity": quantity,
            "status": "PENDING"
        })

        return order_id

    async def _submit_live_order(
        self,
        symbol: str,
        order_type: OrderType,
        quantity: float,
        price: float,
        leverage: float
    ) -> str:
        """Submit order to MEXC via adapter"""

        # 1. Set leverage first
        await self.mexc_adapter.set_leverage(symbol, int(leverage))

        # 2. Map OrderType to MEXC parameters
        if order_type == OrderType.BUY:
            side = "BUY"
            position_side = "LONG"
        elif order_type == OrderType.SHORT:
            side = "SELL"
            position_side = "SHORT"
        elif order_type == OrderType.SELL:
            side = "SELL"  # Close LONG
            position_side = "LONG"
        elif order_type == OrderType.COVER:
            side = "BUY"  # Close SHORT
            position_side = "SHORT"

        # 3. Place order
        response = await self.mexc_adapter.place_futures_order(
            symbol=symbol,
            side=side,
            position_side=position_side,
            order_type="MARKET",  # Always MARKET for pump trading
            quantity=quantity
        )

        # 4. Extract order_id and status
        order_id = response.get("orderId", str(uuid4()))
        status = response.get("status", "FILLED")
        execution_price = response.get("avgPrice", price)

        # 5. Update order record with execution details
        await self._update_order_execution(
            order_id=order_id,
            status=status,
            execution_price=execution_price,
            commission=response.get("commission", 0.0)
        )

        # 6. Broadcast order status
        await self.event_bus.publish("order.status_changed", {
            "order_id": order_id,
            "status": status,
            "execution_price": execution_price
        })

        return order_id

    async def close_position(
        self,
        symbol: str,
        close_price: float
    ) -> Optional[str]:
        """Close position for symbol"""

        # 1. Get current position
        position = await self.get_position(symbol)
        if not position:
            return None

        # 2. Determine close order type
        if position.quantity > 0:
            order_type = OrderType.SELL  # Close LONG
        else:
            order_type = OrderType.COVER  # Close SHORT

        # 3. Submit close order
        order_id = await self.submit_order(
            symbol=symbol,
            order_type=order_type,
            quantity=abs(position.quantity),
            price=close_price,
            strategy_name=position.strategy_name,
            leverage=position.leverage
        )

        # 4. Calculate realized P&L
        realized_pnl = self._calculate_realized_pnl(
            entry_price=position.entry_price,
            exit_price=close_price,
            quantity=abs(position.quantity),
            side="LONG" if position.quantity > 0 else "SHORT"
        )

        # 5. Update order with P&L
        await self._update_order_pnl(order_id, realized_pnl)

        # 6. Broadcast position closed
        await self.event_bus.publish("position.closed", {
            "symbol": symbol,
            "realized_pnl": realized_pnl
        })

        return order_id
```

**Estimated effort:** 4 hours

#### Task 1.2: Create PositionSyncService

**File:** `src/domain/services/position_sync_service.py`

```python
class PositionSyncService:
    """Sync positions with MEXC exchange"""

    def __init__(self, mexc_adapter, db_pool, event_bus, logger):
        self.mexc_adapter = mexc_adapter
        self.db_pool = db_pool
        self.event_bus = event_bus
        self.logger = logger
        self.sync_interval = 10  # seconds
        self.running = False

    async def start(self):
        """Start background sync loop"""
        self.running = True
        while self.running:
            try:
                await self.sync_positions()
            except Exception as e:
                self.logger.error("position_sync.error", {"error": str(e)})

            await asyncio.sleep(self.sync_interval)

    async def sync_positions(self):
        """Sync positions with exchange"""

        # 1. Get positions from MEXC
        exchange_positions = await self.mexc_adapter.get_all_positions()
        # Returns: [{symbol, side, quantity, unrealized_pnl, ...}]

        # 2. Get local positions from DB
        local_positions = await self._get_local_positions()

        # 3. Reconcile differences
        for ex_pos in exchange_positions:
            symbol = ex_pos["symbol"]
            local_pos = local_positions.get(symbol)

            if not local_pos:
                # Position opened outside app
                self.logger.warning("position_sync.external_position", {
                    "symbol": symbol
                })
                await self._create_local_position(ex_pos)

            elif ex_pos["quantity"] == 0 and local_pos["status"] == "OPEN":
                # Position closed (liquidated?)
                self.logger.warning("position_sync.position_closed", {
                    "symbol": symbol,
                    "reason": "liquidation_or_external"
                })
                await self._close_local_position(symbol)

            else:
                # Update P&L
                await self._update_position_pnl(symbol, ex_pos)

        # 4. Broadcast updates
        await self.event_bus.publish("positions.synced", {
            "positions": exchange_positions
        })

    async def _get_local_positions(self) -> Dict[str, Dict]:
        """Query local positions from live_positions table"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM live_positions WHERE status = 'OPEN'"
            )
        return {row["symbol"]: dict(row) for row in rows}
```

**Estimated effort:** 3 hours

#### Task 1.3: Wire Everything in Container

**File:** `src/infrastructure/container.py`

```python
class Container:
    def __init__(self, config: Settings):
        # ... existing initialization ...

        # MEXC Adapters
        if config.trading.live_trading_enabled:
            self.mexc_futures_adapter = MexcFuturesAdapter(
                api_key=config.exchange.mexc_api_key,
                api_secret=config.exchange.mexc_api_secret,
                logger=self.logger
            )
        else:
            self.mexc_futures_adapter = MexcPaperAdapter(
                logger=self.logger,
                initial_balance=config.paper_trading.initial_balance
            )

        # LiveOrderManager
        self.live_order_manager = LiveOrderManager(
            mexc_adapter=self.mexc_futures_adapter,
            db_pool=self.questdb_pool,
            event_bus=self.event_bus,
            logger=self.logger,
            paper_mode=not config.trading.live_trading_enabled
        )

        # StrategyManager (pass LiveOrderManager)
        self.strategy_manager = StrategyManager(
            event_bus=self.event_bus,
            logger=self.logger,
            order_manager=self.live_order_manager,  # ✅ Use LiveOrderManager
            risk_manager=self.risk_manager,
            db_pool=self.questdb_pool
        )

        # PositionSyncService
        if config.trading.live_trading_enabled:
            self.position_sync_service = PositionSyncService(
                mexc_adapter=self.mexc_futures_adapter,
                db_pool=self.questdb_pool,
                event_bus=self.event_bus,
                logger=self.logger
            )

    async def start_services(self):
        """Start background services"""
        if hasattr(self, 'position_sync_service'):
            asyncio.create_task(self.position_sync_service.start())
```

**Estimated effort:** 2 hours

### 5.2 Priority 2: Database Schema

#### Task 2.1: Create Migration 014

**File:** `database/questdb/migrations/014_create_live_trading_tables.sql`

```sql
-- Migration 014: Live Trading Tables
-- Creates tables for live trading sessions, orders, positions, signals, backtest results

-- 1. Live Trading Sessions
CREATE TABLE IF NOT EXISTS live_trading_sessions (
    session_id STRING,
    strategy_ids STRING,
    symbols STRING,
    session_type STRING,
    status STRING,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    initial_balance DOUBLE,
    current_balance DOUBLE,
    total_pnl DOUBLE,
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate DOUBLE,
    max_drawdown DOUBLE,
    sharpe_ratio DOUBLE,
    created_by STRING
) timestamp(start_time) PARTITION BY DAY WAL;

CREATE INDEX IF NOT EXISTS idx_live_sessions_id ON live_trading_sessions (session_id);
CREATE INDEX IF NOT EXISTS idx_live_sessions_status ON live_trading_sessions (status);

-- 2. Signal History
CREATE TABLE IF NOT EXISTS signal_history (
    signal_id STRING,
    session_id STRING,
    strategy_name STRING,
    symbol STRING,
    signal_type STRING,
    action STRING,
    confidence DOUBLE,
    indicator_values STRING,
    order_id STRING,
    execution_status STRING,
    rejection_reason STRING,
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY WAL;

CREATE INDEX IF NOT EXISTS idx_signals_session ON signal_history (session_id);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signal_history (strategy_name);

-- 3. Live Orders
CREATE TABLE IF NOT EXISTS live_orders (
    order_id STRING,
    session_id STRING,
    strategy_name STRING,
    symbol STRING,
    side STRING,
    position_side STRING,
    order_type STRING,
    quantity DOUBLE,
    requested_price DOUBLE,
    execution_price DOUBLE,
    slippage_pct DOUBLE,
    leverage DOUBLE,
    status STRING,
    rejection_reason STRING,
    commission DOUBLE,
    realized_pnl DOUBLE,
    signal_id STRING,
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY WAL;

CREATE INDEX IF NOT EXISTS idx_live_orders_session ON live_orders (session_id);
CREATE INDEX IF NOT EXISTS idx_live_orders_symbol ON live_orders (symbol);

-- 4. Live Positions
CREATE TABLE IF NOT EXISTS live_positions (
    position_id STRING,
    session_id STRING,
    symbol STRING,
    position_side STRING,
    quantity DOUBLE,
    entry_price DOUBLE,
    current_price DOUBLE,
    leverage DOUBLE,
    liquidation_price DOUBLE,
    unrealized_pnl DOUBLE,
    unrealized_pnl_pct DOUBLE,
    margin_used DOUBLE,
    margin_ratio DOUBLE,
    funding_cost_accrued DOUBLE,
    strategy_name STRING,
    entry_signal_id STRING,
    status STRING,
    close_timestamp TIMESTAMP,
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY WAL;

CREATE INDEX IF NOT EXISTS idx_live_positions_symbol ON live_positions (symbol);

-- 5. Backtest Results
CREATE TABLE IF NOT EXISTS backtest_results (
    session_id STRING,
    strategy_name STRING,
    symbols STRING,
    data_collection_session_id STRING,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    initial_balance DOUBLE,
    final_balance DOUBLE,
    total_pnl DOUBLE,
    total_return_pct DOUBLE,
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate DOUBLE,
    profit_factor DOUBLE,
    average_win DOUBLE,
    average_loss DOUBLE,
    max_drawdown DOUBLE,
    sharpe_ratio DOUBLE,
    sortino_ratio DOUBLE,
    calmar_ratio DOUBLE,
    trades_json STRING,
    equity_curve_json STRING,
    created_at TIMESTAMP
) timestamp(start_time) PARTITION BY DAY;

CREATE INDEX IF NOT EXISTS idx_backtest_strategy ON backtest_results (strategy_name);
```

**Estimated effort:** 1 hour

#### Task 2.2: Run Migration

```bash
python database/questdb/run_migrations.py
```

**Estimated effort:** 10 minutes

### 5.3 Priority 3: WebSocket Real-time Updates

#### Task 3.1: Add Message Types to MessageRouter

**File:** `src/api/message_router.py`

```python
class MessageRouter:
    def __init__(self, ...):
        # Add new routes
        self.routes = {
            # ... existing routes ...
            "order_created": self.handle_order_created,
            "order_status": self.handle_order_status,
            "position_update": self.handle_position_update,
            "signal_generated": self.handle_signal_generated
        }

    async def handle_order_created(self, client_id: str, message: Dict):
        """Broadcast order creation to all clients"""
        await self.connection_manager.broadcast({
            "type": "order_created",
            "data": message
        })

    async def handle_order_status(self, client_id: str, message: Dict):
        """Broadcast order status update"""
        await self.connection_manager.broadcast({
            "type": "order_status_changed",
            "data": message
        })

    async def handle_position_update(self, client_id: str, message: Dict):
        """Broadcast position update"""
        await self.connection_manager.broadcast({
            "type": "position_updated",
            "data": message
        })

    async def handle_signal_generated(self, client_id: str, message: Dict):
        """Broadcast strategy signal"""
        await self.connection_manager.broadcast({
            "type": "signal_generated",
            "data": message
        })
```

**Estimated effort:** 2 hours

#### Task 3.2: Wire EventBridge to New Events

**File:** `src/api/event_bridge.py`

```python
class EventBridge:
    async def start(self):
        """Subscribe to EventBus events"""
        await self.event_bus.subscribe("order.created", self._on_order_created)
        await self.event_bus.subscribe("order.status_changed", self._on_order_status)
        await self.event_bus.subscribe("position.updated", self._on_position_update)
        await self.event_bus.subscribe("strategy.signal_detected", self._on_signal)

    async def _on_order_created(self, data: Dict):
        await self.message_router.handle_order_created(None, data)

    async def _on_order_status(self, data: Dict):
        await self.message_router.handle_order_status(None, data)

    async def _on_position_update(self, data: Dict):
        await self.message_router.handle_position_update(None, data)

    async def _on_signal(self, data: Dict):
        await self.message_router.handle_signal_generated(None, data)
```

**Estimated effort:** 1 hour

### 5.4 Priority 4: Frontend Real-time Monitoring

#### Task 4.1: Create TradingChart Component

**File:** `frontend/src/components/trading/TradingChart.tsx`

```typescript
'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useWebSocket } from '@/hooks/useWebSocket';

// Dynamic import for TradingView widget (client-side only)
const TVChartContainer = dynamic(
  () => import('@/components/trading/TVChartContainer'),
  { ssr: false }
);

interface Signal {
  signal_id: string;
  signal_type: 'S1' | 'Z1' | 'ZE1' | 'E1';
  timestamp: number;
  price: number;
  confidence: number;
}

interface TradingChartProps {
  symbol: string;
  session_id: string;
}

export function TradingChart({ symbol, session_id }: TradingChartProps) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [currentPosition, setCurrentPosition] = useState<any>(null);

  const ws = useWebSocket();

  useEffect(() => {
    // Subscribe to signals
    ws.on('signal_generated', (data) => {
      if (data.symbol === symbol && data.session_id === session_id) {
        setSignals(prev => [...prev, {
          signal_id: data.signal_id,
          signal_type: data.signal_type,
          timestamp: Date.parse(data.timestamp),
          price: data.indicator_values.price,
          confidence: data.confidence
        }]);
      }
    });

    // Subscribe to position updates
    ws.on('position_updated', (data) => {
      if (data.symbol === symbol) {
        setCurrentPosition(data);
      }
    });

    return () => {
      ws.off('signal_generated');
      ws.off('position_updated');
    };
  }, [symbol, session_id, ws]);

  return (
    <div className="trading-chart">
      <TVChartContainer
        symbol={symbol}
        signals={signals}
        currentPosition={currentPosition}
      />
    </div>
  );
}
```

**Estimated effort:** 6 hours (including TradingView integration)

#### Task 4.2: Create PositionMonitor Component

**File:** `frontend/src/components/trading/PositionMonitor.tsx`

```typescript
'use client';

import React, { useEffect, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Box, Card, Typography, Button } from '@mui/material';

interface Position {
  symbol: string;
  position_side: 'LONG' | 'SHORT';
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  margin_ratio: number;
  leverage: number;
  duration_seconds: number;
}

export function PositionMonitor() {
  const [positions, setPositions] = useState<Position[]>([]);
  const ws = useWebSocket();

  useEffect(() => {
    // Initial load
    loadPositions();

    // Real-time updates
    ws.on('position_updated', (data) => {
      setPositions(prev => {
        const index = prev.findIndex(p => p.symbol === data.symbol);
        if (index >= 0) {
          const updated = [...prev];
          updated[index] = { ...updated[index], ...data };
          return updated;
        } else {
          return [...prev, data];
        }
      });
    });

    ws.on('position_closed', (data) => {
      setPositions(prev => prev.filter(p => p.symbol !== data.symbol));
    });

    return () => {
      ws.off('position_updated');
      ws.off('position_closed');
    };
  }, [ws]);

  const loadPositions = async () => {
    const response = await fetch('/api/positions/open');
    const data = await response.json();
    setPositions(data);
  };

  const handleClosePosition = async (symbol: string) => {
    await fetch(`/api/positions/${symbol}/close`, { method: 'POST' });
  };

  return (
    <Box>
      <Typography variant="h6">Open Positions</Typography>
      {positions.map(position => (
        <Card key={position.symbol}>
          <Typography variant="h6">{position.symbol}</Typography>
          <Typography>
            {position.position_side} | {position.quantity} | {position.leverage}x
          </Typography>
          <Typography
            color={position.unrealized_pnl >= 0 ? 'success.main' : 'error.main'}
          >
            P&L: {position.unrealized_pnl.toFixed(2)} ({position.unrealized_pnl_pct.toFixed(2)}%)
          </Typography>
          <Typography>
            Margin: {position.margin_ratio.toFixed(1)}%
          </Typography>
          <Button onClick={() => handleClosePosition(position.symbol)}>
            Close Position
          </Button>
        </Card>
      ))}
    </Box>
  );
}
```

**Estimated effort:** 4 hours

#### Task 4.3: Create REST API Endpoints

**File:** `src/api/live_trading_routes.py`

```python
from fastapi import APIRouter, Depends
from typing import List

router = APIRouter()

@router.get("/positions/open")
async def get_open_positions(
    session_id: str = None
) -> List[Dict]:
    """Get all open positions"""
    async with db_pool.acquire() as conn:
        query = "SELECT * FROM live_positions WHERE status = 'OPEN'"
        if session_id:
            query += f" AND session_id = '{session_id}'"
        rows = await conn.fetch(query)
    return [dict(row) for row in rows]

@router.post("/positions/{symbol}/close")
async def close_position(
    symbol: str,
    container: Container = Depends(get_container)
) -> Dict:
    """Close position for symbol"""
    order_manager = container.live_order_manager
    current_price = await get_current_price(symbol)
    order_id = await order_manager.close_position(symbol, current_price)
    return {"success": True, "order_id": order_id}

@router.get("/orders/history")
async def get_order_history(
    session_id: str,
    limit: int = 50
) -> List[Dict]:
    """Get order history for session"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM live_orders
            WHERE session_id = $1
            ORDER BY timestamp DESC
            LIMIT $2
            """,
            session_id, limit
        )
    return [dict(row) for row in rows]

@router.get("/signals/history")
async def get_signal_history(
    session_id: str,
    limit: int = 100
) -> List[Dict]:
    """Get signal history for session"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM signal_history
            WHERE session_id = $1
            ORDER BY timestamp DESC
            LIMIT $2
            """,
            session_id, limit
        )
    return [dict(row) for row in rows]
```

**Estimated effort:** 3 hours

### 5.5 Priority 5: Strategy → Indicator Integration

#### Task 5.1: Create IndicatorExtractor

**File:** `src/domain/services/indicator_extractor.py`

```python
class IndicatorExtractor:
    """Extract required indicators from strategy configuration"""

    @staticmethod
    def extract_indicators(strategy_config: Dict[str, Any]) -> Dict[str, Dict]:
        """
        Extract all unique indicators from strategy conditions

        Returns:
            {
                "pump_magnitude_pct": {"t1": 300, "t2": 0},
                "volume_surge_ratio": {"t1": 300, "t2": 900},
                ...
            }
        """
        indicators = {}

        # Scan all 5 condition groups
        condition_groups = [
            "signal_detection",
            "signal_cancellation",
            "entry_conditions",
            "close_order_detection",
            "emergency_exit"
        ]

        for group_name in condition_groups:
            if group_name not in strategy_config:
                continue

            conditions = strategy_config[group_name].get("conditions", [])
            for condition in conditions:
                condition_type = condition.get("condition_type")
                if not condition_type:
                    continue

                # Get parameters from condition or use defaults
                parameters = condition.get("parameters") or \
                             DEFAULT_INDICATOR_PARAMETERS.get(condition_type, {})

                indicators[condition_type] = parameters

        return indicators

    @staticmethod
    def create_indicator_variants(
        streaming_engine: StreamingIndicatorEngine,
        indicators: Dict[str, Dict]
    ) -> Dict[str, str]:
        """
        Create indicator variants in StreamingIndicatorEngine

        Returns:
            {
                "pump_magnitude_pct": "variant_uuid",
                "volume_surge_ratio": "variant_uuid",
                ...
            }
        """
        variant_ids = {}

        for indicator_type, parameters in indicators.items():
            # Check if variant already exists
            existing_variant = streaming_engine.get_variant_by_type_and_params(
                base_indicator_type=indicator_type,
                parameters=parameters
            )

            if existing_variant:
                variant_ids[indicator_type] = existing_variant.variant_id
            else:
                # Create new variant
                variant_id = streaming_engine.create_variant(
                    name=f"{indicator_type}_strategy",
                    base_indicator_type=indicator_type,
                    variant_type="price",  # or "volume", "orderbook"
                    parameters=parameters,
                    created_by="strategy_loader"
                )
                variant_ids[indicator_type] = variant_id

        return variant_ids

# Default parameters for common indicators
DEFAULT_INDICATOR_PARAMETERS = {
    "pump_magnitude_pct": {"t1": 300, "t2": 0},
    "volume_surge_ratio": {"t1": 300, "t2": 900},
    "price_momentum": {"t1": 60, "t2": 0},
    "rsi": {"period": 14},
    "spread_pct": {},
    "unrealized_pnl_pct": {}  # Calculated from position, not price
}
```

**Estimated effort:** 3 hours

#### Task 5.2: Wire in ExecutionController

**File:** `src/application/controllers/execution_controller.py`

```python
async def start_live_trading_session(
    self,
    session_id: str,
    symbols: List[str],
    strategy_config: Dict[str, Any]
):
    """Start live trading with strategy-driven indicators"""

    # 1. Load strategies
    for strategy_name, strategy_json in strategy_config.items():
        strategy = self.strategy_manager.create_strategy_from_config(strategy_json)
        self.strategy_manager.add_strategy(strategy)

    # 2. Extract required indicators
    extractor = IndicatorExtractor()
    indicators = extractor.extract_indicators(strategy_config)

    # 3. Create indicator variants
    variant_ids = extractor.create_indicator_variants(
        self.streaming_indicator_engine,
        indicators
    )

    # 4. Register indicators for symbols
    for symbol in symbols:
        for indicator_type, variant_id in variant_ids.items():
            self.streaming_indicator_engine.add_indicator_to_session(
                session_id=session_id,
                symbol=symbol,
                variant_id=variant_id
            )

    # 5. Activate strategies for symbols
    for symbol in symbols:
        for strategy_name in strategy_config.keys():
            self.strategy_manager.activate_strategy_for_symbol(
                strategy_name, symbol
            )

    # 6. Start execution loop
    await self._execution_loop()
```

**Estimated effort:** 2 hours

---

## Podsumowanie: Co Trzeba Zrobić

### Must-Do (Minimum Viable Product)

1. **LiveOrderManager.submit_order()** (4h)
2. **PositionSyncService** (3h)
3. **Wire in Container** (2h)
4. **Database Migration 014** (1h)
5. **WebSocket Message Types** (2h)
6. **EventBridge Wiring** (1h)
7. **REST API Endpoints** (3h)
8. **IndicatorExtractor** (3h)
9. **ExecutionController Strategy Loading** (2h)

**Total: ~21 hours (3 days)**

### Should-Do (Full Featured)

10. **TradingChart Component** (6h)
11. **PositionMonitor Component** (4h)
12. **Signal Log UI** (3h)
13. **Risk Alerts UI** (2h)
14. **Performance Metrics Dashboard** (3h)

**Total: ~39 hours (5 days)**

### Nice-to-Have (Polish)

15. **Strategy Performance Comparison** (4h)
16. **Trade Replay** (8h)
17. **Notification System** (6h)

**Total: ~57 hours (7 days)**

---

## Weryfikacja Działania

Po implementacji Priority 1-2 (Signal → Order + Database):

```bash
# 1. Start QuestDB
python database/questdb/install_questdb.py

# 2. Run migration
python database/questdb/run_migrations.py

# 3. Start backend (paper mode dla testów)
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload

# 4. Test via curl:

# Start live session (paper mode)
curl -X POST http://localhost:8080/api/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "paper",
    "symbols": ["BTC_USDT"],
    "strategy_config": {
      "pump_dump_detection": {
        "strategy_name": "pump_dump_detection",
        "enabled": true,
        "direction": "SHORT",
        ...
      }
    }
  }'

# Verify orders created
curl http://localhost:8080/api/orders/history?session_id=<session_id>

# Verify positions
curl http://localhost:8080/api/positions/open?session_id=<session_id>

# Verify signals
curl http://localhost:8080/api/signals/history?session_id=<session_id>
```

**Expected Result:**
- Sygnały S1/Z1/ZE1/E1 pojawiają się w `signal_history`
- Ordery trafiają do `live_orders` (paper mode) lub `live_orders` (live)
- Pozycje śledzane w `live_positions`
- WebSocket broadcast do frontendu
- Frontend real-time updates

---

## Konkluzja

System ma **solidne fundamenty**, ale brakuje **połączeń między komponentami**. To jak puzzle z wszystkimi elementami, które nie są złożone.

**Kluczowe problemy:**
1. ❌ Signal → Order flow **nie istnieje**
2. ❌ LiveOrderManager **niekompletny**
3. ❌ Frontend **brak real-time monitoring**
4. ❌ Database schema **brak tabel live trading**

**Po implementacji:**
✅ Strategia wykrywa sygnał (S1)
✅ Evaluacja entry conditions (Z1)
✅ Risk manager approve
✅ LiveOrderManager → MEXC order
✅ Position tracking w bazie
✅ Real-time updates via WebSocket
✅ Frontend chart + positions + orders

**Trading będzie działał.**
