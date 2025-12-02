# Implementation Roadmap: 30% → 100% Live Trading System

**Document Version:** 1.0
**Created:** 2025-11-06
**Author:** Claude (Senior Trading Systems Engineer)
**Status:** Complete Analysis

---

## Executive Summary

This roadmap defines the step-by-step transition from the current state (30% complete) to a production-ready live trading system (100% complete) for pump & dump cryptocurrency trading with risk minimization.

### Current State Assessment
- **Production Readiness:** 30%
- **Working Components:** Data collection, backtesting core, basic API
- **Missing Components:** Live order execution, position sync, risk management, complete UI, monitoring, deployment

### Target State
- **Production Readiness:** 100%
- **Timeline:** 205 hours (5-6 weeks with 1 engineer)
- **Phases:** 6 phases (0-5) with 3 milestones
- **Investment Required:** 205h development + 16h deployment infrastructure

### Milestone-Based Rollout
```
M1: Paper Trading Ready (After Phase 1, ~92h)
    ├─ Can test strategies with fake money
    └─ Go/No-Go: All Phase 0-1 tests pass

M2: Live Trading $100 (After Phase 3, ~156h)
    ├─ Limited capital exposure
    ├─ Full monitoring active
    └─ Go/No-Go: 7-day paper trading success + all alerts working

M3: Live Trading Full Capital (After Phase 5, ~205h)
    ├─ Production deployment
    ├─ Blue-green rollback ready
    └─ Go/No-Go: 30-day live $100 success + all metrics green
```

---

## Part I: Current State Inventory (30%)

### 1.1 What EXISTS and WORKS Today

#### Backend Infrastructure ✅
```
src/infrastructure/
├── config/
│   └── settings.py ✅ (Pydantic configuration)
├── adapters/
│   ├── mexc_adapter.py ✅ (Market data connection)
│   └── mexc_paper_adapter.py ✅ (Paper trading stub)
├── persistence/
│   └── questdb/
│       ├── client.py ✅ (QuestDB connection)
│       ├── tick_repository.py ✅ (Write tick_prices)
│       └── session_repository.py ✅ (Write data_collection_sessions)
└── container.py ✅ (Dependency injection)
```

**Evidence:**
- `settings.py`: 200+ lines, loads from config.json or env vars
- `mexc_adapter.py`: 400+ lines, connects to MEXC WebSocket, fetches deals API
- `questdb/client.py`: 150+ lines, InfluxDB Line Protocol writes (1M+ rows/sec)

#### Domain Services ✅
```
src/domain/services/
├── streaming_indicator_engine.py ✅ (TWPA, Velocity, Volume_Surge)
├── strategy_manager.py ✅ (Strategy evaluation)
└── indicators/
    ├── twpa.py ✅
    ├── velocity.py ✅
    └── volume_surge.py ✅
```

**Evidence:**
- `streaming_indicator_engine.py`: 800+ lines, ring buffers, O(1) incremental calculation
- Supports (t1, t2) window semantics: `(300, 0)` = "last 5 minutes"
- EventBus integration: publishes "indicator_updated" events

#### API Layer ✅
```
src/api/
├── unified_server.py ✅ (FastAPI app factory)
├── rest/
│   ├── data_collection_routes.py ✅ (GET /sessions, POST /sessions/start)
│   └── backtest_routes.py ✅ (POST /backtest/start)
└── websocket_server.py ⚠️ (50% complete - missing EventBridge)
```

**Evidence:**
- `unified_server.py`: Single server on port 8080, REST + WebSocket
- `data_collection_routes.py`: Start/stop data collection, query sessions from QuestDB
- WebSocket exists but NOT integrated with EventBus

#### Database ✅
```
QuestDB (Primary TimeSeries Database)
├── tick_prices ✅ (session_id, symbol, timestamp, price, volume)
├── data_collection_sessions ✅ (session_id, symbols, status, start_time, end_time)
├── indicators ✅ (symbol, indicator_id, timestamp, value, confidence)
└── strategies ✅ (id, strategy_name, strategy_json, enabled)
```

**Evidence:**
- Migration 003: Creates tick_prices, tick_orderbook, data_collection_sessions
- Writes work: 1M+ rows/sec via InfluxDB Line Protocol
- Queries work: PostgreSQL protocol on port 8812

#### Frontend ✅
```
frontend/src/
├── app/
│   ├── page.tsx ✅ (Main dashboard)
│   ├── data-collection/ ✅ (Start/stop collection UI)
│   └── backtest/ ✅ (Backtest configuration UI)
├── components/
│   └── common/ ✅ (Button, Input, Card)
└── hooks/
    └── useWebSocket.ts ⚠️ (Stub - not connected)
```

**Evidence:**
- Next.js 14 app running on port 3000
- Basic UI for data collection and backtesting
- WebSocket hook exists but NOT connected to backend

#### Testing ✅
```
tests_e2e/
├── api/ ✅ (213 tests for REST API)
├── frontend/ ⚠️ (9 tests - incomplete)
└── integration/ ⚠️ (2 tests - incomplete)
```

**Coverage:** ~40% (API layer well tested, domain/infrastructure not)

---

### 1.2 What is MISSING or INCOMPLETE (70%)

#### Critical Missing Components ❌

**1. EventBus (Foundation for Everything)**
```
STATUS: Does NOT exist
IMPACT: Blocks ALL real-time features
LOCATION: src/core/event_bus.py (missing file)

Required Topics:
- market_data (MarketDataProviderAdapter → StreamingIndicatorEngine)
- indicator_updated (StreamingIndicatorEngine → StrategyManager)
- signal_generated (StrategyManager → RiskManager)
- order_created (RiskManager → LiveOrderManager)
- order_filled (MEXC → PositionTracker)
- position_updated (PositionTracker → UI via WebSocket)
- risk_alert (RiskManager → UI via WebSocket)
```

**Evidence:** Searched codebase - NO event_bus.py file exists. Mentioned in CLAUDE.md but not implemented.

**2. LiveOrderManager (Core Live Trading)**
```
STATUS: 90% missing
LOCATION: src/domain/services/order_manager_live.py (stub exists, ~50 lines)

Missing Features:
❌ submit_order() - Create order on MEXC
❌ cancel_order() - Cancel pending order
❌ get_order_status() - Poll order status
❌ Order queue with TTL (5 min, max 1000 orders)
❌ Retry logic (3 attempts, exponential backoff)
❌ Error handling (insufficient balance, invalid symbol)
```

**Evidence:** Current file is stub with TODO comments, no MEXC API integration.

**3. PositionSyncService (Liquidation Detection)**
```
STATUS: Does NOT exist
IMPACT: Cannot detect liquidations or margin calls
LOCATION: src/domain/services/position_sync_service.py (missing file)

Required Features:
❌ Background sync every 10s (asyncio task)
❌ Fetch positions from MEXC (/api/v1/private/position/list)
❌ Compare local positions vs. exchange positions
❌ Detect discrepancies (liquidation, manual close)
❌ Emit position_updated events
❌ Calculate margin ratio (equity / maintenance_margin)
```

**4. RiskManager (Budget Allocation)**
```
STATUS: 60% complete
LOCATION: src/domain/services/risk_manager.py (exists but incomplete)

Missing Features:
❌ Budget allocation per symbol
❌ Position size limits (max 10% per symbol)
❌ validate_order() before submission
❌ Emergency circuit breaker integration
❌ Risk alert emission (margin < 15%)
```

**Evidence:** File exists with basic structure, but no validation logic implemented.

**5. Circuit Breaker (Exchange Downtime Protection)**
```
STATUS: Does NOT exist
IMPACT: Cannot handle MEXC API failures gracefully
LOCATION: src/infrastructure/circuit_breaker.py (missing file)

Required States:
- CLOSED: Normal operation
- OPEN: Stop all trading after 5 failures in 60s
- HALF_OPEN: Try 1 request after 30s cooldown

Required Features:
❌ Failure counting with sliding window
❌ Automatic state transitions
❌ Manual reset endpoint (POST /api/circuit-breaker/reset)
```

**6. Complete Frontend UI (User Visibility)**
```
STATUS: 20% complete
MISSING COMPONENTS:

❌ TradingChart (TradingView Lightweight Charts)
   - Candlestick chart with price/volume
   - Signal markers (S1 🟡, Z1 🟢, ZE1 🔵, E1 🔴)
   - Real-time updates via WebSocket
   - Historical data from QuestDB

❌ PositionMonitor
   - Current positions table (symbol, size, entry, current, PnL)
   - Margin ratio gauge (< 15% = red alert)
   - Liquidation price display
   - Real-time updates every 1s

❌ OrderHistory
   - All orders table (pending, filled, cancelled, failed)
   - Slippage tracking (expected vs. actual price)
   - Filters (status, symbol, time range)

❌ SignalLog
   - Full signal history (S1, O1, Z1, ZE1, E1)
   - Confidence scores
   - Strategy name
   - Execution results

❌ RiskAlerts
   - Alert list (severity, message, timestamp)
   - Sound notifications for critical alerts
   - Acknowledge/dismiss functionality
```

**Evidence:** Only basic data collection UI exists. No trading monitoring components.

**7. WebSocket EventBridge**
```
STATUS: Does NOT exist
LOCATION: src/api/websocket/event_bridge.py (missing file)

Required Features:
❌ Subscribe to EventBus topics
❌ Broadcast events to connected WebSocket clients
❌ Filter by client subscriptions (per symbol)
❌ Handle client disconnects
```

**8. Monitoring & Observability**
```
STATUS: Does NOT exist

Missing Components:
❌ Prometheus metrics collection
❌ Grafana dashboards (5 dashboards defined)
❌ Alertmanager rules
❌ Health check endpoints (/health, /health/ready, /health/deep)
❌ Log aggregation
```

**9. Deployment Infrastructure**
```
STATUS: Does NOT exist

Missing Components:
❌ Dockerfile.backend
❌ Dockerfile.frontend
❌ docker-compose.yml
❌ Blue-green deployment script (deploy.sh)
❌ Rollback script (rollback.sh)
❌ Database migration rollback
❌ Nginx load balancer config
```

**10. Testing Coverage**
```
CURRENT: 40% coverage
TARGET: 80% coverage

Missing Tests:
❌ Unit tests for EventBus
❌ Unit tests for LiveOrderManager
❌ Unit tests for PositionSyncService
❌ Unit tests for RiskManager
❌ Unit tests for Circuit Breaker
❌ Integration test: Data collection → Backtest → Results
❌ Integration test: Live trading → Order → Position sync
❌ E2E test: Full UI workflow (select session → start backtest → view results)
```

---

## Part II: Phase 0 - Infrastructure Foundation (32h)

**Goal:** Build the core infrastructure that all other phases depend on.

**Prerequisites:** None (starts from current state)

**Deliverables:**
- EventBus operational
- Circuit Breaker operational
- RiskManager validation logic
- Health check endpoints

### Task 0.1: EventBus Implementation (8h)

**File:** `src/core/event_bus.py`

**Implementation:**
```python
# src/core/event_bus.py
import asyncio
from typing import Dict, List, Callable, Any
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class EventBus:
    """
    Central async event bus for pub/sub communication.

    Delivery Guarantee: AT_LEAST_ONCE (may retry on failure)
    Thread Safety: asyncio single-thread only
    """

    def __init__(self):
        # CRITICAL: Use explicit dict, NOT defaultdict (memory leak prevention)
        self._subscribers: Dict[str, List[Callable]] = {}
        self._subscriber_count: Dict[str, int] = {}

    def subscribe(self, topic: str, handler: Callable):
        """Subscribe to topic with async handler."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
            self._subscriber_count[topic] = 0

        self._subscribers[topic].append(handler)
        self._subscriber_count[topic] += 1
        logger.info(f"Subscribed to '{topic}' (total: {self._subscriber_count[topic]})")

    def unsubscribe(self, topic: str, handler: Callable):
        """Unsubscribe handler from topic."""
        if topic in self._subscribers and handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)
            self._subscriber_count[topic] -= 1
            logger.info(f"Unsubscribed from '{topic}' (remaining: {self._subscriber_count[topic]})")

            # Cleanup empty topics (memory leak prevention)
            if self._subscriber_count[topic] == 0:
                del self._subscribers[topic]
                del self._subscriber_count[topic]

    async def publish(self, topic: str, data: Dict[str, Any]):
        """
        Publish event to all subscribers.

        Retry Policy: 3 attempts with exponential backoff (1s, 2s, 4s)
        Error Handling: Log error but continue to other subscribers
        """
        if topic not in self._subscribers:
            logger.debug(f"No subscribers for topic '{topic}'")
            return

        subscribers = self._subscribers[topic]
        logger.debug(f"Publishing to '{topic}' ({len(subscribers)} subscribers)")

        for subscriber in subscribers:
            retries = 0
            max_retries = 3

            while retries < max_retries:
                try:
                    await subscriber(data)
                    break  # Success
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Failed to deliver to subscriber after {max_retries} attempts: {e}")
                    else:
                        backoff = 2 ** (retries - 1)  # 1s, 2s, 4s
                        logger.warning(f"Delivery failed, retrying in {backoff}s... (attempt {retries}/{max_retries})")
                        await asyncio.sleep(backoff)

    def list_topics(self) -> List[str]:
        """List all active topics with subscriber counts."""
        return [
            f"{topic} ({count} subscribers)"
            for topic, count in self._subscriber_count.items()
        ]

    async def shutdown(self):
        """Cleanup all subscriptions."""
        logger.info("Shutting down EventBus...")
        self._subscribers.clear()
        self._subscriber_count.clear()
```

**Topics to Support:**
```python
# Core Topics (must be implemented)
TOPICS = {
    "market_data": "New tick price/volume from exchange",
    "indicator_updated": "Indicator calculation completed",
    "signal_generated": "Strategy generated trading signal (S1, Z1, etc.)",
    "order_created": "New order submitted to exchange",
    "order_filled": "Order executed by exchange",
    "order_cancelled": "Order cancelled",
    "position_updated": "Position changed (new, closed, liquidated)",
    "risk_alert": "Risk threshold breached (margin < 15%)",
}
```

**Testing:**
```python
# tests_e2e/unit/test_event_bus.py
import pytest
from src.core.event_bus import EventBus

@pytest.mark.asyncio
async def test_subscribe_and_publish():
    bus = EventBus()
    received = []

    async def handler(data):
        received.append(data)

    bus.subscribe("test_topic", handler)
    await bus.publish("test_topic", {"value": 123})

    assert len(received) == 1
    assert received[0]["value"] == 123

@pytest.mark.asyncio
async def test_retry_on_failure():
    bus = EventBus()
    attempts = []

    async def failing_handler(data):
        attempts.append(1)
        if len(attempts) < 2:  # Fail first attempt
            raise ValueError("Simulated failure")

    bus.subscribe("test", failing_handler)
    await bus.publish("test", {})

    assert len(attempts) == 2  # Initial + 1 retry

@pytest.mark.asyncio
async def test_unsubscribe_cleanup():
    bus = EventBus()

    async def handler(data):
        pass

    bus.subscribe("test", handler)
    bus.unsubscribe("test", handler)

    # Topic should be cleaned up
    assert "test" not in bus._subscribers
```

**Dependencies:** None (pure Python asyncio)

**Completion Criteria:**
- [ ] EventBus class passes all unit tests
- [ ] Retry logic works (3 attempts with backoff)
- [ ] Memory leak test passes (10k subscribe/unsubscribe cycles)
- [ ] Integration test: StreamingIndicatorEngine → StrategyManager via EventBus

---

### Task 0.2: Circuit Breaker Implementation (6h)

**File:** `src/infrastructure/circuit_breaker.py`

**Implementation:**
```python
# src/infrastructure/circuit_breaker.py
import time
from typing import Optional, Callable, Any
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking all calls
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """
    Circuit Breaker pattern for MEXC API calls.

    States:
    - CLOSED: All calls allowed
    - OPEN: All calls blocked (after 5 failures in 60s)
    - HALF_OPEN: Test 1 call after 30s cooldown

    Purpose: Prevent cascading failures when MEXC API is down.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        failure_window: int = 60
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_window = failure_window

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state_changed_at: float = time.time()

    def _should_attempt_reset(self) -> bool:
        """Check if recovery timeout has elapsed."""
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.state_changed_at
            return elapsed >= self.recovery_timeout
        return False

    def _record_success(self):
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            # Recovery successful
            logger.info("Circuit breaker recovery successful, transitioning to CLOSED")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.state_changed_at = time.time()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _record_failure(self):
        """Record failed call and update state."""
        now = time.time()

        # Reset count if outside failure window
        if self.last_failure_time and (now - self.last_failure_time) > self.failure_window:
            self.failure_count = 0

        self.failure_count += 1
        self.last_failure_time = now

        if self.state == CircuitState.HALF_OPEN:
            # Recovery failed, back to OPEN
            logger.warning("Circuit breaker recovery failed, transitioning back to OPEN")
            self.state = CircuitState.OPEN
            self.state_changed_at = now
        elif self.failure_count >= self.failure_threshold:
            # Threshold breached, open circuit
            logger.error(
                f"Circuit breaker opened: {self.failure_count} failures in {self.failure_window}s"
            )
            self.state = CircuitState.OPEN
            self.state_changed_at = now

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Raises:
            CircuitBreakerOpenError: When circuit is OPEN
        """
        # Check if we should attempt recovery
        if self._should_attempt_reset():
            logger.info("Circuit breaker attempting recovery, transitioning to HALF_OPEN")
            self.state = CircuitState.HALF_OPEN
            self.state_changed_at = time.time()

        # Block calls if OPEN
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN (opened at {self.state_changed_at})"
            )

        # Execute function
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

    def reset(self):
        """Manually reset circuit breaker."""
        logger.info("Circuit breaker manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.state_changed_at = time.time()

    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "state_changed_at": self.state_changed_at,
            "time_since_state_change": time.time() - self.state_changed_at,
        }

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is OPEN."""
    pass
```

**Integration with MexcAdapter:**
```python
# src/infrastructure/adapters/mexc_adapter.py (modify existing)

class MexcFuturesAdapter:
    def __init__(self, api_key: str, api_secret: str, circuit_breaker: CircuitBreaker):
        self.api_key = api_key
        self.api_secret = api_secret
        self.circuit_breaker = circuit_breaker

    async def submit_order(self, order: Order) -> str:
        """Submit order with circuit breaker protection."""
        try:
            return await self.circuit_breaker.call(
                self._submit_order_impl,
                order
            )
        except CircuitBreakerOpenError as e:
            logger.error(f"Order rejected: {e}")
            raise

    async def _submit_order_impl(self, order: Order) -> str:
        """Actual MEXC API call."""
        # Existing implementation...
```

**REST API Endpoint:**
```python
# src/api/rest/circuit_breaker_routes.py (new file)
from fastapi import APIRouter, Depends
from src.infrastructure.container import Container

router = APIRouter()

@router.get("/api/circuit-breaker/status")
async def get_circuit_breaker_status(container: Container = Depends()):
    cb = container.get_circuit_breaker()
    return cb.get_state()

@router.post("/api/circuit-breaker/reset")
async def reset_circuit_breaker(container: Container = Depends()):
    cb = container.get_circuit_breaker()
    cb.reset()
    return {"message": "Circuit breaker reset", "state": cb.get_state()}
```

**Testing:**
```python
# tests_e2e/unit/test_circuit_breaker.py
import pytest
from src.infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState

@pytest.mark.asyncio
async def test_circuit_opens_after_failures():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1, failure_window=10)

    async def failing_func():
        raise ValueError("Simulated failure")

    # First 2 failures should not open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            await cb.call(failing_func)
    assert cb.state == CircuitState.CLOSED

    # 3rd failure should open circuit
    with pytest.raises(ValueError):
        await cb.call(failing_func)
    assert cb.state == CircuitState.OPEN

    # 4th call should be blocked
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(failing_func)

@pytest.mark.asyncio
async def test_circuit_recovery():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, failure_window=10)

    async def failing_func():
        raise ValueError("Failure")

    async def success_func():
        return "success"

    # Open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            await cb.call(failing_func)
    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # Next call should transition to HALF_OPEN and succeed
    result = await cb.call(success_func)
    assert result == "success"
    assert cb.state == CircuitState.CLOSED
```

**Completion Criteria:**
- [ ] Circuit breaker passes all unit tests
- [ ] Integration test: MexcAdapter fails → circuit opens → blocks calls
- [ ] REST API endpoints work (GET /status, POST /reset)
- [ ] Recovery test: Circuit opens → 30s wait → recovers on success

---

### Task 0.3: RiskManager Validation Logic (8h)

**File:** `src/domain/services/risk_manager.py` (modify existing)

**Current State:** File exists with basic structure but no validation logic.

**Add Missing Features:**
```python
# src/domain/services/risk_manager.py (additions)

from typing import Dict, Optional
from dataclasses import dataclass
import logging
from src.core.event_bus import EventBus

logger = logging.getLogger(__name__)

@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_position_size_usd: float = 1000.0  # Max $1000 per position
    max_budget_per_symbol_pct: float = 0.10  # Max 10% of budget per symbol
    min_margin_ratio: float = 0.15  # Alert if margin < 15%
    max_open_positions: int = 5  # Max 5 concurrent positions
    max_daily_loss_pct: float = 0.05  # Max 5% daily loss

class RiskManager:
    """
    Validates orders before submission and monitors risk metrics.

    Responsibilities:
    - Budget allocation per symbol
    - Position size limits
    - Margin ratio monitoring
    - Emergency stop on daily loss limit
    """

    def __init__(
        self,
        event_bus: EventBus,
        limits: RiskLimits,
        total_budget_usd: float
    ):
        self.event_bus = event_bus
        self.limits = limits
        self.total_budget_usd = total_budget_usd

        # Track current state
        self.allocated_budget: Dict[str, float] = {}  # symbol → allocated USD
        self.open_positions: Dict[str, Position] = {}  # symbol → Position
        self.daily_pnl: float = 0.0
        self.daily_start_equity: float = total_budget_usd

        # Subscribe to position updates
        self.event_bus.subscribe("position_updated", self._on_position_updated)

    def validate_order(self, order: Order) -> tuple[bool, Optional[str]]:
        """
        Validate order against risk limits.

        Returns:
            (is_valid, error_message)
        """
        # Check 1: Max open positions
        if len(self.open_positions) >= self.limits.max_open_positions:
            return False, f"Max open positions reached ({self.limits.max_open_positions})"

        # Check 2: Budget allocation per symbol
        symbol_budget = self.total_budget_usd * self.limits.max_budget_per_symbol_pct
        allocated = self.allocated_budget.get(order.symbol, 0.0)
        order_value = order.quantity * order.price

        if allocated + order_value > symbol_budget:
            return False, f"Symbol budget exceeded: ${allocated + order_value:.2f} > ${symbol_budget:.2f}"

        # Check 3: Position size limit
        if order_value > self.limits.max_position_size_usd:
            return False, f"Position size too large: ${order_value:.2f} > ${self.limits.max_position_size_usd:.2f}"

        # Check 4: Daily loss limit
        daily_loss_pct = abs(self.daily_pnl) / self.daily_start_equity
        if self.daily_pnl < 0 and daily_loss_pct >= self.limits.max_daily_loss_pct:
            return False, f"Daily loss limit reached: {daily_loss_pct*100:.1f}% loss"

        return True, None

    async def _on_position_updated(self, data: Dict):
        """Handle position updates from EventBus."""
        symbol = data["symbol"]

        if data["status"] == "opened":
            # Track new position
            position = Position(**data["position"])
            self.open_positions[symbol] = position
            self.allocated_budget[symbol] = position.entry_price * position.size

        elif data["status"] == "closed":
            # Release budget
            if symbol in self.open_positions:
                position = self.open_positions[symbol]
                pnl = data.get("realized_pnl", 0.0)
                self.daily_pnl += pnl

                del self.open_positions[symbol]
                self.allocated_budget[symbol] = 0.0

                logger.info(f"Position closed: {symbol}, PnL: ${pnl:.2f}, Daily PnL: ${self.daily_pnl:.2f}")

        elif data["status"] == "liquidated":
            # Emergency: position liquidated
            if symbol in self.open_positions:
                position = self.open_positions[symbol]
                loss = position.entry_price * position.size  # Total loss
                self.daily_pnl -= loss

                del self.open_positions[symbol]
                self.allocated_budget[symbol] = 0.0

                # Emit critical alert
                await self.event_bus.publish("risk_alert", {
                    "severity": "critical",
                    "type": "liquidation",
                    "symbol": symbol,
                    "loss_usd": loss,
                    "message": f"🚨 LIQUIDATION: {symbol} - Loss: ${loss:.2f}"
                })

    def check_margin_ratio(self, equity: float, maintenance_margin: float) -> Optional[dict]:
        """
        Check if margin ratio is below threshold.

        Returns:
            Alert dict if ratio < threshold, else None
        """
        margin_ratio = equity / maintenance_margin if maintenance_margin > 0 else 1.0

        if margin_ratio < self.limits.min_margin_ratio:
            return {
                "severity": "high",
                "type": "low_margin",
                "margin_ratio": margin_ratio,
                "equity": equity,
                "maintenance_margin": maintenance_margin,
                "message": f"⚠️ Low margin ratio: {margin_ratio*100:.1f}% (threshold: {self.limits.min_margin_ratio*100:.1f}%)"
            }

        return None

    def reset_daily_metrics(self):
        """Reset daily P&L tracking (call at midnight UTC)."""
        logger.info(f"Resetting daily metrics. Previous daily PnL: ${self.daily_pnl:.2f}")
        self.daily_pnl = 0.0
        self.daily_start_equity = self.total_budget_usd
```

**Integration with Container:**
```python
# src/infrastructure/container.py (modify existing)

class Container:
    def __init__(self, config: Settings):
        self.config = config
        self._event_bus: Optional[EventBus] = None
        self._risk_manager: Optional[RiskManager] = None

    def get_event_bus(self) -> EventBus:
        if self._event_bus is None:
            self._event_bus = EventBus()
        return self._event_bus

    def get_risk_manager(self) -> RiskManager:
        if self._risk_manager is None:
            limits = RiskLimits(
                max_position_size_usd=self.config.max_position_size_usd,
                max_budget_per_symbol_pct=self.config.max_budget_per_symbol_pct,
                min_margin_ratio=self.config.min_margin_ratio,
                max_open_positions=self.config.max_open_positions,
                max_daily_loss_pct=self.config.max_daily_loss_pct,
            )
            self._risk_manager = RiskManager(
                event_bus=self.get_event_bus(),
                limits=limits,
                total_budget_usd=self.config.total_budget_usd
            )
        return self._risk_manager
```

**Testing:**
```python
# tests_e2e/unit/test_risk_manager.py
import pytest
from src.domain.services.risk_manager import RiskManager, RiskLimits
from src.core.event_bus import EventBus

@pytest.mark.asyncio
async def test_validate_order_budget_exceeded():
    bus = EventBus()
    limits = RiskLimits(max_budget_per_symbol_pct=0.10)
    rm = RiskManager(bus, limits, total_budget_usd=10000.0)

    # Order value: $1100 > $1000 (10% of $10000)
    order = Order(symbol="BTC_USDT", quantity=0.02, price=55000)
    valid, error = rm.validate_order(order)

    assert not valid
    assert "budget exceeded" in error.lower()

@pytest.mark.asyncio
async def test_validate_order_daily_loss_limit():
    bus = EventBus()
    limits = RiskLimits(max_daily_loss_pct=0.05)
    rm = RiskManager(bus, limits, total_budget_usd=10000.0)

    # Simulate -5% daily loss
    rm.daily_pnl = -500.0

    order = Order(symbol="BTC_USDT", quantity=0.01, price=50000)
    valid, error = rm.validate_order(order)

    assert not valid
    assert "daily loss limit" in error.lower()

@pytest.mark.asyncio
async def test_margin_ratio_alert():
    bus = EventBus()
    limits = RiskLimits(min_margin_ratio=0.15)
    rm = RiskManager(bus, limits, total_budget_usd=10000.0)

    # Margin ratio: 1000 / 8000 = 12.5% < 15%
    alert = rm.check_margin_ratio(equity=1000.0, maintenance_margin=8000.0)

    assert alert is not None
    assert alert["severity"] == "high"
    assert alert["type"] == "low_margin"
    assert alert["margin_ratio"] < 0.15
```

**Completion Criteria:**
- [ ] validate_order() passes all unit tests
- [ ] Budget allocation works correctly
- [ ] Daily loss limit blocks orders
- [ ] Margin ratio alerts emit risk_alert events
- [ ] Integration test: Order rejected → UI shows error message

---

### Task 0.4: Health Check Endpoints (4h)

**File:** `src/api/rest/health_routes.py` (new file)

**Implementation:**
```python
# src/api/rest/health_routes.py
from fastapi import APIRouter, Depends, HTTPException
from src.infrastructure.container import Container
import asyncio
import time

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Basic health check.

    Returns 200 if service is running.
    Used by: Load balancer, Docker healthcheck
    """
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

@router.get("/health/ready")
async def readiness_check(container: Container = Depends()):
    """
    Readiness check - can service handle requests?

    Checks:
    - EventBus initialized
    - QuestDB connection alive
    - No critical errors

    Returns 200 if ready, 503 if not ready.
    Used by: Kubernetes readiness probe, Blue-green deployment
    """
    checks = {}

    # Check 1: EventBus
    try:
        event_bus = container.get_event_bus()
        checks["event_bus"] = "ready"
    except Exception as e:
        checks["event_bus"] = f"error: {e}"

    # Check 2: QuestDB
    try:
        questdb_client = container.get_questdb_client()
        # Simple query to verify connection
        await questdb_client.pool.fetchval("SELECT 1")
        checks["questdb"] = "ready"
    except Exception as e:
        checks["questdb"] = f"error: {e}"

    # Check 3: Circuit Breaker
    try:
        circuit_breaker = container.get_circuit_breaker()
        state = circuit_breaker.get_state()
        if state["state"] == "open":
            checks["circuit_breaker"] = f"open (failures: {state['failure_count']})"
        else:
            checks["circuit_breaker"] = "ready"
    except Exception as e:
        checks["circuit_breaker"] = f"error: {e}"

    # Determine overall status
    all_ready = all(
        "error" not in str(v).lower() and "open" not in str(v).lower()
        for v in checks.values()
    )

    if all_ready:
        return {"status": "ready", "checks": checks, "timestamp": time.time()}
    else:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": checks, "timestamp": time.time()}
        )

@router.get("/health/deep")
async def deep_health_check(container: Container = Depends()):
    """
    Deep health check - comprehensive system verification.

    Checks:
    - All /health/ready checks
    - MEXC API connection
    - Disk space
    - Memory usage

    Used by: Monitoring system (Prometheus)
    """
    checks = {}

    # Run readiness checks first
    try:
        readiness_response = await readiness_check(container)
        checks.update(readiness_response["checks"])
    except HTTPException as e:
        checks.update(e.detail["checks"])

    # Check 4: MEXC API
    try:
        mexc_adapter = container.get_mexc_adapter()
        # Try to fetch server time (lightweight call)
        await asyncio.wait_for(
            mexc_adapter.get_server_time(),
            timeout=5.0
        )
        checks["mexc_api"] = "reachable"
    except asyncio.TimeoutError:
        checks["mexc_api"] = "timeout"
    except Exception as e:
        checks["mexc_api"] = f"error: {e}"

    # Check 5: Disk space
    import shutil
    disk_usage = shutil.disk_usage("/")
    free_gb = disk_usage.free / (1024**3)
    checks["disk_space"] = f"{free_gb:.1f} GB free"
    if free_gb < 5.0:
        checks["disk_space"] += " (WARNING: < 5 GB)"

    # Check 6: Memory usage
    import psutil
    mem = psutil.virtual_memory()
    checks["memory"] = f"{mem.percent}% used"
    if mem.percent > 90:
        checks["memory"] += " (WARNING: > 90%)"

    # Determine overall status
    critical_failed = any(
        "error" in str(v).lower() or "open" in str(v).lower()
        for k, v in checks.items()
        if k in ["event_bus", "questdb", "circuit_breaker"]
    )

    if critical_failed:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "checks": checks, "timestamp": time.time()}
        )
    else:
        return {"status": "healthy", "checks": checks, "timestamp": time.time()}
```

**Register Routes:**
```python
# src/api/unified_server.py (modify existing)
from src.api.rest import health_routes

def create_unified_app() -> FastAPI:
    app = FastAPI(title="FX Trading System")

    # Health checks (no /api prefix for load balancer compatibility)
    app.include_router(health_routes.router, tags=["Health"])

    # Other routes...
    return app
```

**Docker Healthcheck:**
```dockerfile
# Dockerfile.backend (add healthcheck)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
```

**Testing:**
```python
# tests_e2e/api/test_health_routes.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_readiness_check_success(client: AsyncClient):
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "event_bus" in data["checks"]
    assert "questdb" in data["checks"]

@pytest.mark.asyncio
async def test_readiness_check_circuit_breaker_open(client: AsyncClient, container):
    # Simulate circuit breaker opening
    cb = container.get_circuit_breaker()
    cb.state = CircuitState.OPEN

    response = await client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()["detail"]
    assert "open" in data["checks"]["circuit_breaker"]
```

**Completion Criteria:**
- [ ] GET /health returns 200
- [ ] GET /health/ready checks EventBus + QuestDB + Circuit Breaker
- [ ] GET /health/deep checks MEXC API + disk + memory
- [ ] Docker healthcheck works (container marked healthy after startup)
- [ ] Blue-green deployment script uses /health/ready

---

### Phase 0 Summary

**Total Time:** 32h (reduced from 36h through overengineering removal)

**Critical Path:**
```
EventBus (8h) → Circuit Breaker (6h) → RiskManager (8h) → Health Checks (4h)
                                     ↓
                                  Everything else depends on EventBus
```

**Deliverables:**
- ✅ EventBus operational with AT_LEAST_ONCE delivery
- ✅ Circuit Breaker protecting MEXC API calls
- ✅ RiskManager validating orders before submission
- ✅ Health check endpoints for deployment

**Testing Coverage Added:** +25 unit tests, +10 API tests

**Next Phase Dependencies:**
- Phase 1 (Live Trading) requires EventBus + Circuit Breaker + RiskManager
- Phase 4 (Frontend) requires EventBus for WebSocket bridge

---

## Part III: Phase 1 - Core Live Trading (60h)

**Goal:** Implement live order execution and position synchronization.

**Prerequisites:** Phase 0 complete (EventBus, Circuit Breaker, RiskManager)

**Deliverables:**
- LiveOrderManager operational
- PositionSyncService operational
- MEXC API integration complete
- Strategy → RiskManager → Order flow working

### Task 1.1: LiveOrderManager Implementation (16h)

**File:** `src/domain/services/order_manager_live.py` (replace stub)

**Current State:** Stub file with TODO comments (~50 lines)

**Implementation:**
```python
# src/domain/services/order_manager_live.py (complete rewrite)
import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import time
import logging
from src.core.event_bus import EventBus
from src.infrastructure.adapters.mexc_adapter import MexcFuturesAdapter
from src.infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"

@dataclass
class Order:
    order_id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    price: float
    order_type: str  # "limit" or "market"
    status: OrderStatus
    created_at: float
    updated_at: float
    exchange_order_id: Optional[str] = None
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    error_message: Optional[str] = None

class LiveOrderManager:
    """
    Manages order lifecycle for live trading.

    Responsibilities:
    - Submit orders to MEXC
    - Poll order status
    - Handle partial fills
    - Retry on transient failures
    - Emit order events to EventBus

    Order Queue:
    - Max size: 1000 orders
    - TTL: 5 minutes per order
    - Cleanup: Remove completed orders after 1 hour
    """

    def __init__(
        self,
        event_bus: EventBus,
        mexc_adapter: MexcFuturesAdapter,
        circuit_breaker: CircuitBreaker
    ):
        self.event_bus = event_bus
        self.mexc_adapter = mexc_adapter
        self.circuit_breaker = circuit_breaker

        # Order tracking (CRITICAL: Not defaultdict to prevent memory leak)
        self.orders: Dict[str, Order] = {}
        self.max_orders = 1000
        self.order_ttl_seconds = 300  # 5 minutes

        # Background tasks
        self._status_poll_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Subscribe to signal events
        self.event_bus.subscribe("signal_generated", self._on_signal_generated)

    async def start(self):
        """Start background tasks."""
        logger.info("Starting LiveOrderManager...")
        self._status_poll_task = asyncio.create_task(self._poll_order_status())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_orders())

    async def stop(self):
        """Stop background tasks."""
        logger.info("Stopping LiveOrderManager...")
        if self._status_poll_task:
            self._status_poll_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

    async def _on_signal_generated(self, data: Dict):
        """
        Handle signal from StrategyManager.

        Signal Types:
        - S1: Entry signal → Create order
        - Z1: Position opened → Monitor
        - ZE1: Partial exit → Create exit order
        - E1: Full exit → Create exit order
        """
        signal_type = data["signal_type"]

        if signal_type in ["S1", "ZE1", "E1"]:
            # Create order from signal
            order = Order(
                order_id=data["signal_id"],
                symbol=data["symbol"],
                side=data["side"],
                quantity=data["quantity"],
                price=data.get("price"),  # None for market orders
                order_type=data.get("order_type", "market"),
                status=OrderStatus.PENDING,
                created_at=time.time(),
                updated_at=time.time()
            )

            await self.submit_order(order)

    async def submit_order(self, order: Order) -> bool:
        """
        Submit order to exchange with retry logic.

        Returns:
            True if submitted successfully, False otherwise
        """
        # Check queue size
        if len(self.orders) >= self.max_orders:
            logger.error(f"Order queue full ({self.max_orders}), rejecting order {order.order_id}")
            order.status = OrderStatus.FAILED
            order.error_message = "Order queue full"
            await self.event_bus.publish("order_created", {
                "order_id": order.order_id,
                "status": "failed",
                "error": order.error_message
            })
            return False

        # Add to tracking
        self.orders[order.order_id] = order

        # Retry logic: 3 attempts with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Submit via circuit breaker
                exchange_order_id = await self.circuit_breaker.call(
                    self._submit_order_to_exchange,
                    order
                )

                # Success
                order.exchange_order_id = exchange_order_id
                order.status = OrderStatus.SUBMITTED
                order.updated_at = time.time()

                logger.info(
                    f"Order submitted: {order.order_id} → Exchange ID: {exchange_order_id}"
                )

                await self.event_bus.publish("order_created", {
                    "order_id": order.order_id,
                    "exchange_order_id": exchange_order_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": order.quantity,
                    "price": order.price,
                    "status": "submitted"
                })

                return True

            except CircuitBreakerOpenError as e:
                # Circuit breaker open, don't retry
                logger.error(f"Order submission blocked by circuit breaker: {e}")
                order.status = OrderStatus.FAILED
                order.error_message = str(e)
                await self.event_bus.publish("order_created", {
                    "order_id": order.order_id,
                    "status": "failed",
                    "error": order.error_message
                })
                return False

            except Exception as e:
                logger.warning(
                    f"Order submission failed (attempt {attempt + 1}/{max_retries}): {e}"
                )

                if attempt < max_retries - 1:
                    backoff = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(backoff)
                else:
                    # Final attempt failed
                    order.status = OrderStatus.FAILED
                    order.error_message = f"Failed after {max_retries} attempts: {e}"
                    await self.event_bus.publish("order_created", {
                        "order_id": order.order_id,
                        "status": "failed",
                        "error": order.error_message
                    })
                    return False

    async def _submit_order_to_exchange(self, order: Order) -> str:
        """
        Actual MEXC API call to submit order.

        Returns:
            Exchange order ID
        """
        if order.order_type == "market":
            return await self.mexc_adapter.create_market_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity
            )
        else:  # limit
            return await self.mexc_adapter.create_limit_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=order.price
            )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order."""
        if order_id not in self.orders:
            logger.warning(f"Cannot cancel unknown order: {order_id}")
            return False

        order = self.orders[order_id]

        if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            logger.warning(f"Cannot cancel order in status {order.status}: {order_id}")
            return False

        try:
            await self.circuit_breaker.call(
                self.mexc_adapter.cancel_order,
                order.symbol,
                order.exchange_order_id
            )

            order.status = OrderStatus.CANCELLED
            order.updated_at = time.time()

            logger.info(f"Order cancelled: {order_id}")

            await self.event_bus.publish("order_cancelled", {
                "order_id": order_id,
                "exchange_order_id": order.exchange_order_id
            })

            return True

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def _poll_order_status(self):
        """
        Background task: Poll order status every 2 seconds.

        Checks all SUBMITTED orders for fills.
        """
        while True:
            try:
                await asyncio.sleep(2)

                # Get all submitted orders
                submitted_orders = [
                    order for order in self.orders.values()
                    if order.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
                ]

                if not submitted_orders:
                    continue

                logger.debug(f"Polling status for {len(submitted_orders)} orders...")

                # Poll each order
                for order in submitted_orders:
                    try:
                        status = await self.circuit_breaker.call(
                            self.mexc_adapter.get_order_status,
                            order.symbol,
                            order.exchange_order_id
                        )

                        await self._update_order_status(order, status)

                    except CircuitBreakerOpenError:
                        logger.warning("Skipping order status poll: circuit breaker open")
                        break  # Skip remaining orders
                    except Exception as e:
                        logger.error(f"Failed to poll order {order.order_id}: {e}")

            except asyncio.CancelledError:
                logger.info("Order status polling stopped")
                break
            except Exception as e:
                logger.error(f"Error in order status polling: {e}")

    async def _update_order_status(self, order: Order, exchange_status: Dict):
        """Update order from exchange status."""
        old_status = order.status

        # Parse exchange response
        if exchange_status["status"] == "FILLED":
            order.status = OrderStatus.FILLED
            order.filled_quantity = exchange_status["executedQty"]
            order.average_fill_price = exchange_status["avgPrice"]
        elif exchange_status["status"] == "PARTIALLY_FILLED":
            order.status = OrderStatus.PARTIALLY_FILLED
            order.filled_quantity = exchange_status["executedQty"]
        elif exchange_status["status"] == "CANCELED":
            order.status = OrderStatus.CANCELLED

        order.updated_at = time.time()

        # Emit event if status changed
        if order.status != old_status:
            logger.info(
                f"Order status changed: {order.order_id} {old_status.value} → {order.status.value}"
            )

            if order.status == OrderStatus.FILLED:
                await self.event_bus.publish("order_filled", {
                    "order_id": order.order_id,
                    "exchange_order_id": order.exchange_order_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": order.filled_quantity,
                    "price": order.average_fill_price,
                    "slippage": abs(order.average_fill_price - (order.price or order.average_fill_price))
                })

    async def _cleanup_old_orders(self):
        """
        Background task: Cleanup old orders every 60 seconds.

        Removes orders older than 1 hour.
        """
        while True:
            try:
                await asyncio.sleep(60)

                now = time.time()
                to_remove = []

                for order_id, order in self.orders.items():
                    age = now - order.created_at

                    # Remove if > 1 hour old and in terminal state
                    if age > 3600 and order.status in [
                        OrderStatus.FILLED,
                        OrderStatus.CANCELLED,
                        OrderStatus.FAILED
                    ]:
                        to_remove.append(order_id)

                if to_remove:
                    for order_id in to_remove:
                        del self.orders[order_id]
                    logger.info(f"Cleaned up {len(to_remove)} old orders")

            except asyncio.CancelledError:
                logger.info("Order cleanup stopped")
                break
            except Exception as e:
                logger.error(f"Error in order cleanup: {e}")

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)

    def get_all_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all orders, optionally filtered by symbol."""
        if symbol:
            return [o for o in self.orders.values() if o.symbol == symbol]
        return list(self.orders.values())
```

**REST API Endpoints:**
```python
# src/api/rest/trading_routes.py (new file - Part of Gap #1 solution)
from fastapi import APIRouter, Depends, HTTPException
from src.infrastructure.container import Container
from typing import Optional

router = APIRouter()

@router.get("/api/trading/orders")
async def get_orders(
    symbol: Optional[str] = None,
    container: Container = Depends()
):
    """Get all orders, optionally filtered by symbol."""
    order_manager = container.get_live_order_manager()
    orders = order_manager.get_all_orders(symbol=symbol)
    return {
        "orders": [
            {
                "order_id": o.order_id,
                "symbol": o.symbol,
                "side": o.side,
                "quantity": o.quantity,
                "price": o.price,
                "status": o.status.value,
                "created_at": o.created_at,
                "filled_quantity": o.filled_quantity,
                "average_fill_price": o.average_fill_price
            }
            for o in orders
        ]
    }

@router.post("/api/trading/orders/{order_id}/cancel")
async def cancel_order(order_id: str, container: Container = Depends()):
    """Cancel pending order."""
    order_manager = container.get_live_order_manager()
    success = await order_manager.cancel_order(order_id)

    if success:
        return {"message": "Order cancelled", "order_id": order_id}
    else:
        raise HTTPException(status_code=400, detail="Failed to cancel order")
```

**Testing:**
```python
# tests_e2e/unit/test_live_order_manager.py
import pytest
from src.domain.services.order_manager_live import LiveOrderManager, Order, OrderStatus
from src.core.event_bus import EventBus
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_submit_order_success():
    event_bus = EventBus()
    mexc_adapter = AsyncMock()
    mexc_adapter.create_market_order.return_value = "MEXC_12345"
    circuit_breaker = MagicMock()
    circuit_breaker.call = AsyncMock(side_effect=lambda f, *args: f(*args))

    manager = LiveOrderManager(event_bus, mexc_adapter, circuit_breaker)

    order = Order(
        order_id="order_1",
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01,
        price=None,
        order_type="market",
        status=OrderStatus.PENDING,
        created_at=time.time(),
        updated_at=time.time()
    )

    success = await manager.submit_order(order)

    assert success
    assert order.status == OrderStatus.SUBMITTED
    assert order.exchange_order_id == "MEXC_12345"

@pytest.mark.asyncio
async def test_submit_order_circuit_breaker_open():
    event_bus = EventBus()
    mexc_adapter = AsyncMock()
    circuit_breaker = MagicMock()
    circuit_breaker.call = AsyncMock(side_effect=CircuitBreakerOpenError("Circuit open"))

    manager = LiveOrderManager(event_bus, mexc_adapter, circuit_breaker)

    order = Order(...)
    success = await manager.submit_order(order)

    assert not success
    assert order.status == OrderStatus.FAILED
    assert "circuit" in order.error_message.lower()

@pytest.mark.asyncio
async def test_cancel_order():
    event_bus = EventBus()
    mexc_adapter = AsyncMock()
    mexc_adapter.cancel_order.return_value = True
    circuit_breaker = MagicMock()
    circuit_breaker.call = AsyncMock(side_effect=lambda f, *args: f(*args))

    manager = LiveOrderManager(event_bus, mexc_adapter, circuit_breaker)

    # Add order first
    order = Order(...)
    order.status = OrderStatus.SUBMITTED
    order.exchange_order_id = "MEXC_12345"
    manager.orders[order.order_id] = order

    success = await manager.cancel_order(order.order_id)

    assert success
    assert order.status == OrderStatus.CANCELLED
```

**Completion Criteria:**
- [ ] submit_order() passes all unit tests
- [ ] cancel_order() works correctly
- [ ] Background status polling works (2s interval)
- [ ] Order cleanup removes old orders (1h TTL)
- [ ] Circuit breaker integration works
- [ ] EventBus integration: signal_generated → order_created → order_filled
- [ ] REST API endpoints work (GET /orders, POST /orders/{id}/cancel)

---

### Task 1.2: PositionSyncService Implementation (12h)

**File:** `src/domain/services/position_sync_service.py` (new file)

**Purpose:** Synchronize local positions with MEXC positions to detect liquidations and manual closes.

**Implementation:**
```python
# src/domain/services/position_sync_service.py
import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass
import time
import logging
from src.core.event_bus import EventBus
from src.infrastructure.adapters.mexc_adapter import MexcFuturesAdapter
from src.infrastructure.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

@dataclass
class Position:
    symbol: str
    side: str  # "long" or "short"
    size: float
    entry_price: float
    current_price: float
    liquidation_price: float
    unrealized_pnl: float
    margin: float
    leverage: int
    opened_at: float
    updated_at: float

class PositionSyncService:
    """
    Synchronizes local positions with exchange positions.

    Responsibilities:
    - Fetch positions from MEXC every 10s
    - Detect discrepancies (liquidation, manual close)
    - Calculate margin ratio
    - Emit position_updated events
    - Emit risk_alert events when margin < 15%

    Memory Management:
    - Max 100 positions tracked
    - Closed positions removed after 5 minutes
    """

    def __init__(
        self,
        event_bus: EventBus,
        mexc_adapter: MexcFuturesAdapter,
        circuit_breaker: CircuitBreaker
    ):
        self.event_bus = event_bus
        self.mexc_adapter = mexc_adapter
        self.circuit_breaker = circuit_breaker

        # Local position tracking (NOT defaultdict)
        self.positions: Dict[str, Position] = {}
        self.max_positions = 100

        # Background task
        self._sync_task: Optional[asyncio.Task] = None

        # Subscribe to order fills
        self.event_bus.subscribe("order_filled", self._on_order_filled)

    async def start(self):
        """Start position sync background task."""
        logger.info("Starting PositionSyncService...")
        self._sync_task = asyncio.create_task(self._sync_positions())

    async def stop(self):
        """Stop position sync."""
        logger.info("Stopping PositionSyncService...")
        if self._sync_task:
            self._sync_task.cancel()

    async def _on_order_filled(self, data: Dict):
        """
        Handle order fill event.

        Updates local position or creates new position.
        """
        symbol = data["symbol"]
        side = data["side"]
        quantity = data["quantity"]
        price = data["price"]

        if symbol in self.positions:
            # Update existing position
            position = self.positions[symbol]

            if side == "buy":
                # Adding to long or reducing short
                if position.side == "long":
                    # Average entry price
                    total_cost = position.size * position.entry_price + quantity * price
                    position.size += quantity
                    position.entry_price = total_cost / position.size
                else:  # short
                    position.size -= quantity
                    if position.size <= 0:
                        # Position closed
                        del self.positions[symbol]
                        await self.event_bus.publish("position_updated", {
                            "symbol": symbol,
                            "status": "closed",
                            "realized_pnl": position.unrealized_pnl
                        })
                        return
            else:  # sell
                # Similar logic for sell...
                pass
        else:
            # Create new position
            if len(self.positions) >= self.max_positions:
                logger.error(f"Max positions reached ({self.max_positions})")
                return

            position = Position(
                symbol=symbol,
                side="long" if side == "buy" else "short",
                size=quantity,
                entry_price=price,
                current_price=price,
                liquidation_price=0.0,  # Will be updated by sync
                unrealized_pnl=0.0,
                margin=0.0,
                leverage=1,
                opened_at=time.time(),
                updated_at=time.time()
            )

            self.positions[symbol] = position

            await self.event_bus.publish("position_updated", {
                "symbol": symbol,
                "status": "opened",
                "position": {
                    "side": position.side,
                    "size": position.size,
                    "entry_price": position.entry_price
                }
            })

    async def _sync_positions(self):
        """
        Background task: Sync positions every 10 seconds.

        Fetches positions from MEXC and compares with local positions.
        """
        while True:
            try:
                await asyncio.sleep(10)

                # Fetch from MEXC
                try:
                    exchange_positions = await self.circuit_breaker.call(
                        self.mexc_adapter.get_positions
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch positions from MEXC: {e}")
                    continue

                # Build symbol → exchange position map
                exchange_map = {p["symbol"]: p for p in exchange_positions}

                # Check each local position
                for symbol, local_pos in list(self.positions.items()):
                    if symbol not in exchange_map:
                        # Position missing on exchange → liquidated or manually closed
                        logger.warning(f"Position {symbol} missing on exchange (liquidation?)")

                        del self.positions[symbol]

                        await self.event_bus.publish("position_updated", {
                            "symbol": symbol,
                            "status": "liquidated",
                            "position": {
                                "side": local_pos.side,
                                "size": local_pos.size,
                                "entry_price": local_pos.entry_price
                            }
                        })

                        # Emit critical risk alert
                        await self.event_bus.publish("risk_alert", {
                            "severity": "critical",
                            "type": "liquidation",
                            "symbol": symbol,
                            "message": f"🚨 LIQUIDATION DETECTED: {symbol}"
                        })
                    else:
                        # Position exists, update details
                        exchange_pos = exchange_map[symbol]

                        local_pos.current_price = exchange_pos["markPrice"]
                        local_pos.liquidation_price = exchange_pos["liquidationPrice"]
                        local_pos.unrealized_pnl = exchange_pos["unrealizedProfit"]
                        local_pos.margin = exchange_pos["margin"]
                        local_pos.leverage = exchange_pos["leverage"]
                        local_pos.updated_at = time.time()

                        # Calculate margin ratio
                        equity = local_pos.margin + local_pos.unrealized_pnl
                        maintenance_margin = exchange_pos["maintenanceMargin"]
                        margin_ratio = equity / maintenance_margin if maintenance_margin > 0 else 1.0

                        # Check margin threshold (15%)
                        if margin_ratio < 0.15:
                            await self.event_bus.publish("risk_alert", {
                                "severity": "high",
                                "type": "low_margin",
                                "symbol": symbol,
                                "margin_ratio": margin_ratio,
                                "message": f"⚠️ Low margin ratio: {symbol} ({margin_ratio*100:.1f}%)"
                            })

                # Check for new positions on exchange (manually opened?)
                for symbol, exchange_pos in exchange_map.items():
                    if symbol not in self.positions:
                        logger.info(f"New position detected on exchange: {symbol}")

                        # Add to local tracking
                        position = Position(
                            symbol=symbol,
                            side="long" if exchange_pos["positionSide"] == "LONG" else "short",
                            size=exchange_pos["positionAmt"],
                            entry_price=exchange_pos["entryPrice"],
                            current_price=exchange_pos["markPrice"],
                            liquidation_price=exchange_pos["liquidationPrice"],
                            unrealized_pnl=exchange_pos["unrealizedProfit"],
                            margin=exchange_pos["margin"],
                            leverage=exchange_pos["leverage"],
                            opened_at=time.time(),
                            updated_at=time.time()
                        )

                        self.positions[symbol] = position

                        await self.event_bus.publish("position_updated", {
                            "symbol": symbol,
                            "status": "opened",
                            "position": {
                                "side": position.side,
                                "size": position.size,
                                "entry_price": position.entry_price
                            }
                        })

                logger.debug(f"Position sync complete: {len(self.positions)} positions tracked")

            except asyncio.CancelledError:
                logger.info("Position sync stopped")
                break
            except Exception as e:
                logger.error(f"Error in position sync: {e}")

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol."""
        return self.positions.get(symbol)

    def get_all_positions(self) -> List[Position]:
        """Get all positions."""
        return list(self.positions.values())

    def get_total_unrealized_pnl(self) -> float:
        """Get sum of unrealized PnL across all positions."""
        return sum(p.unrealized_pnl for p in self.positions.values())
```

**REST API Endpoints:**
```python
# src/api/rest/trading_routes.py (additions)

@router.get("/api/trading/positions")
async def get_positions(container: Container = Depends()):
    """Get all open positions."""
    position_sync = container.get_position_sync_service()
    positions = position_sync.get_all_positions()
    return {
        "positions": [
            {
                "symbol": p.symbol,
                "side": p.side,
                "size": p.size,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "liquidation_price": p.liquidation_price,
                "unrealized_pnl": p.unrealized_pnl,
                "margin": p.margin,
                "leverage": p.leverage,
                "margin_ratio": (p.margin + p.unrealized_pnl) / (p.margin / p.leverage) if p.leverage > 0 else 1.0,
                "opened_at": p.opened_at
            }
            for p in positions
        ],
        "total_unrealized_pnl": position_sync.get_total_unrealized_pnl()
    }

@router.post("/api/trading/positions/{symbol}/close")
async def close_position(symbol: str, container: Container = Depends()):
    """Close position immediately (market order)."""
    position_sync = container.get_position_sync_service()
    position = position_sync.get_position(symbol)

    if not position:
        raise HTTPException(status_code=404, detail=f"Position not found: {symbol}")

    # Create market order to close position
    order_manager = container.get_live_order_manager()

    close_order = Order(
        order_id=f"close_{symbol}_{int(time.time())}",
        symbol=symbol,
        side="sell" if position.side == "long" else "buy",
        quantity=position.size,
        price=None,
        order_type="market",
        status=OrderStatus.PENDING,
        created_at=time.time(),
        updated_at=time.time()
    )

    success = await order_manager.submit_order(close_order)

    if success:
        return {"message": "Close order submitted", "order_id": close_order.order_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to submit close order")
```

**Testing:**
```python
# tests_e2e/unit/test_position_sync_service.py
import pytest
from src.domain.services.position_sync_service import PositionSyncService, Position
from src.core.event_bus import EventBus
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_on_order_filled_creates_position():
    event_bus = EventBus()
    mexc_adapter = AsyncMock()
    circuit_breaker = AsyncMock()

    service = PositionSyncService(event_bus, mexc_adapter, circuit_breaker)

    await service._on_order_filled({
        "symbol": "BTC_USDT",
        "side": "buy",
        "quantity": 0.01,
        "price": 50000.0
    })

    assert "BTC_USDT" in service.positions
    position = service.positions["BTC_USDT"]
    assert position.side == "long"
    assert position.size == 0.01
    assert position.entry_price == 50000.0

@pytest.mark.asyncio
async def test_sync_detects_liquidation():
    event_bus = EventBus()
    alerts = []

    async def capture_alert(data):
        alerts.append(data)

    event_bus.subscribe("risk_alert", capture_alert)

    mexc_adapter = AsyncMock()
    mexc_adapter.get_positions.return_value = []  # No positions on exchange
    circuit_breaker = AsyncMock()
    circuit_breaker.call = AsyncMock(side_effect=lambda f: f())

    service = PositionSyncService(event_bus, mexc_adapter, circuit_breaker)

    # Add local position
    service.positions["BTC_USDT"] = Position(
        symbol="BTC_USDT",
        side="long",
        size=0.01,
        entry_price=50000.0,
        current_price=50000.0,
        liquidation_price=45000.0,
        unrealized_pnl=0.0,
        margin=500.0,
        leverage=10,
        opened_at=time.time(),
        updated_at=time.time()
    )

    # Trigger sync
    await service._sync_positions()

    # Position should be removed
    assert "BTC_USDT" not in service.positions

    # Alert should be emitted
    assert len(alerts) == 1
    assert alerts[0]["type"] == "liquidation"
    assert alerts[0]["severity"] == "critical"
```

**Completion Criteria:**
- [ ] _on_order_filled() creates/updates positions correctly
- [ ] _sync_positions() detects liquidations
- [ ] _sync_positions() detects low margin ratios (< 15%)
- [ ] Background sync runs every 10s
- [ ] REST API endpoints work (GET /positions, POST /positions/{symbol}/close)
- [ ] Integration test: Order fill → Position opened → Sync → UI displays position

---

### Task 1.3: MEXC Adapter Enhancements (12h)

**File:** `src/infrastructure/adapters/mexc_adapter.py` (modify existing)

**Current State:** Basic market data connection working, but missing order execution methods.

**Add Missing Methods:**
```python
# src/infrastructure/adapters/mexc_adapter.py (additions)

class MexcFuturesAdapter:
    """MEXC Futures API adapter with complete order execution."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://futures.mexc.com"
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession()

    async def stop(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature for authenticated requests."""
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        signed: bool = False
    ) -> Dict:
        """Make HTTP request to MEXC API."""
        if not self.session:
            raise RuntimeError("Session not initialized. Call start() first.")

        url = f"{self.base_url}{endpoint}"
        headers = {"X-MEXC-APIKEY": self.api_key}

        if signed:
            params = params or {}
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._generate_signature(params)

        async with self.session.request(method, url, params=params, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"MEXC API error {resp.status}: {text}")

            return await resp.json()

    async def create_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> str:
        """
        Create market order.

        Returns:
            Exchange order ID
        """
        params = {
            "symbol": symbol,
            "side": side.upper(),  # BUY or SELL
            "type": "MARKET",
            "quantity": quantity
        }

        response = await self._request("POST", "/api/v1/private/order/submit", params, signed=True)
        return response["data"]["orderId"]

    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> str:
        """
        Create limit order.

        Returns:
            Exchange order ID
        """
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": quantity,
            "price": price,
            "timeInForce": "GTC"  # Good till cancelled
        }

        response = await self._request("POST", "/api/v1/private/order/submit", params, signed=True)
        return response["data"]["orderId"]

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel order.

        Returns:
            True if cancelled successfully
        """
        params = {
            "symbol": symbol,
            "orderId": order_id
        }

        response = await self._request("POST", "/api/v1/private/order/cancel", params, signed=True)
        return response["success"]

    async def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """
        Get order status.

        Returns:
            Order details with status, executedQty, avgPrice
        """
        params = {
            "symbol": symbol,
            "orderId": order_id
        }

        response = await self._request("GET", "/api/v1/private/order/get", params, signed=True)
        return response["data"]

    async def get_positions(self) -> List[Dict]:
        """
        Get all open positions.

        Returns:
            List of position dicts with symbol, positionSide, positionAmt, entryPrice, etc.
        """
        response = await self._request("GET", "/api/v1/private/position/list", {}, signed=True)
        return response["data"]

    async def get_account_info(self) -> Dict:
        """
        Get account information.

        Returns:
            Account balance, available margin, total equity
        """
        response = await self._request("GET", "/api/v1/private/account/assets", {}, signed=True)
        return response["data"]

    async def get_server_time(self) -> int:
        """
        Get MEXC server time (lightweight health check).

        Returns:
            Unix timestamp in milliseconds
        """
        response = await self._request("GET", "/api/v1/common/ping", {})
        return response["data"]["serverTime"]
```

**Testing:**
```python
# tests_e2e/integration/test_mexc_adapter_integration.py
import pytest
from src.infrastructure.adapters.mexc_adapter import MexcFuturesAdapter
import os

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_server_time():
    """Test connectivity to MEXC API."""
    adapter = MexcFuturesAdapter(
        api_key=os.getenv("MEXC_API_KEY", "test"),
        api_secret=os.getenv("MEXC_API_SECRET", "test")
    )

    await adapter.start()

    try:
        server_time = await adapter.get_server_time()
        assert server_time > 0
    finally:
        await adapter.stop()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_cancel_order():
    """Test order creation and cancellation (requires testnet credentials)."""
    adapter = MexcFuturesAdapter(
        api_key=os.getenv("MEXC_TESTNET_API_KEY"),
        api_secret=os.getenv("MEXC_TESTNET_API_SECRET"),
        base_url="https://testnet.mexc.com"  # Use testnet
    )

    await adapter.start()

    try:
        # Create small limit order (won't fill)
        order_id = await adapter.create_limit_order(
            symbol="BTC_USDT",
            side="buy",
            quantity=0.001,
            price=10000.0  # Well below market price
        )

        assert order_id is not None

        # Check status
        status = await adapter.get_order_status("BTC_USDT", order_id)
        assert status["status"] == "NEW"

        # Cancel order
        success = await adapter.cancel_order("BTC_USDT", order_id)
        assert success

        # Verify cancelled
        status = await adapter.get_order_status("BTC_USDT", order_id)
        assert status["status"] == "CANCELED"

    finally:
        await adapter.stop()
```

**Completion Criteria:**
- [ ] create_market_order() works on testnet
- [ ] create_limit_order() works on testnet
- [ ] cancel_order() works
- [ ] get_order_status() returns correct data
- [ ] get_positions() returns positions list
- [ ] get_account_info() returns balance
- [ ] Signature generation passes MEXC authentication
- [ ] Integration tests pass on testnet

---

### Task 1.4: Strategy → Order Flow Integration (8h)

**Goal:** Connect StrategyManager signal generation to LiveOrderManager order submission.

**Files Modified:**
- `src/domain/services/strategy_manager.py`
- `src/application/controllers/execution_controller.py`

**StrategyManager Modifications:**
```python
# src/domain/services/strategy_manager.py (modify signal emission)

class StrategyManager:
    """Manages strategy lifecycle and signal generation."""

    async def _emit_signal(
        self,
        strategy_name: str,
        symbol: str,
        signal_type: str,  # S1, Z1, ZE1, E1
        confidence: float,
        indicator_values: Dict[str, float]
    ):
        """
        Emit trading signal to EventBus.

        Signal will be picked up by LiveOrderManager or BacktestEngine.
        """
        signal_id = f"{strategy_name}_{symbol}_{signal_type}_{int(time.time())}"

        # Determine order parameters based on signal type
        if signal_type == "S1":  # Entry signal
            side = self._get_strategy_direction(strategy_name)  # "buy" or "sell"
            quantity = await self._calculate_position_size(symbol, confidence)
            order_type = "market"  # Fast execution for pump & dump

        elif signal_type in ["ZE1", "E1"]:  # Exit signals
            side = "sell" if self._is_long_position(symbol) else "buy"
            quantity = self._get_position_size(symbol)
            if signal_type == "ZE1":  # Partial exit
                quantity *= 0.5  # Exit 50%
            order_type = "market"

        else:  # Z1, O1 (monitoring only, no orders)
            side = None
            quantity = 0
            order_type = None

        signal_data = {
            "signal_id": signal_id,
            "strategy_name": strategy_name,
            "symbol": symbol,
            "signal_type": signal_type,
            "confidence": confidence,
            "indicator_values": indicator_values,
            "timestamp": time.time(),
            # Order parameters (if applicable)
            "side": side,
            "quantity": quantity,
            "order_type": order_type
        }

        await self.event_bus.publish("signal_generated", signal_data)

        logger.info(
            f"Signal emitted: {signal_type} for {symbol} "
            f"(strategy: {strategy_name}, confidence: {confidence:.2f})"
        )

    async def _calculate_position_size(self, symbol: str, confidence: float) -> float:
        """
        Calculate position size based on confidence and risk limits.

        Uses Kelly Criterion adjusted by confidence:
        position_size = (confidence - 0.5) * 2 * max_budget_per_symbol
        """
        # Get max budget from RiskManager
        max_budget = self.risk_manager.limits.max_position_size_usd

        # Adjust by confidence (0.5 = neutral, 1.0 = very confident)
        kelly_fraction = max(0, (confidence - 0.5) * 2)  # 0 to 1 range

        # Get current price to calculate quantity
        current_price = await self._get_current_price(symbol)

        position_size_usd = max_budget * kelly_fraction
        quantity = position_size_usd / current_price

        return round(quantity, 6)  # Round to 6 decimals for crypto
```

**ExecutionController Integration:**
```python
# src/application/controllers/execution_controller.py (modify start_live_trading)

async def start_live_trading(
    self,
    symbols: List[str],
    strategy_names: List[str],
    budget_usd: float
) -> str:
    """Start live trading session."""
    session_id = f"live_{int(time.time())}"

    # Initialize components in order
    await self.event_bus.start()
    await self.risk_manager.initialize(budget_usd)
    await self.live_order_manager.start()
    await self.position_sync_service.start()
    await self.strategy_manager.activate_strategies(strategy_names)

    # Start market data stream
    await self.mexc_adapter.subscribe_to_symbols(symbols)

    self.state = ExecutionState.RUNNING
    self.current_session_id = session_id

    logger.info(
        f"Live trading started: session={session_id}, "
        f"symbols={symbols}, strategies={strategy_names}, budget=${budget_usd}"
    )

    return session_id
```

**Testing:**
```python
# tests_e2e/integration/test_strategy_order_flow.py
import pytest
from src.core.event_bus import EventBus
from src.domain.services.strategy_manager import StrategyManager
from src.domain.services.order_manager_live import LiveOrderManager
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_s1_signal_creates_order():
    """Test that S1 signal from StrategyManager creates order in LiveOrderManager."""
    event_bus = EventBus()

    # Mock dependencies
    strategy_manager = StrategyManager(event_bus, mock_indicator_engine, mock_risk_manager)
    order_manager = LiveOrderManager(event_bus, mock_mexc_adapter, mock_circuit_breaker)

    # Start order manager (subscribes to signal_generated)
    await order_manager.start()

    # Emit S1 signal
    await strategy_manager._emit_signal(
        strategy_name="TestStrategy",
        symbol="BTC_USDT",
        signal_type="S1",
        confidence=0.85,
        indicator_values={"twpa_5min": 50000, "velocity": 0.02}
    )

    # Wait for event processing
    await asyncio.sleep(0.1)

    # Order should be created
    orders = order_manager.get_all_orders(symbol="BTC_USDT")
    assert len(orders) == 1
    assert orders[0].side == "buy"  # Assuming long strategy
    assert orders[0].order_type == "market"
```

**Completion Criteria:**
- [ ] S1 signal creates order automatically
- [ ] ZE1 signal creates partial exit order (50%)
- [ ] E1 signal creates full exit order (100%)
- [ ] Position size calculated using confidence (Kelly Criterion)
- [ ] Integration test: Signal → RiskManager validation → Order submission
- [ ] Live trading flow: Market data → Indicators → Strategy → Signal → Order

---

### Task 1.5: WebSocket EventBridge Implementation (8h)

**File:** `src/api/websocket/event_bridge.py` (new file)

**Purpose:** Bridge EventBus events to WebSocket clients for real-time UI updates.

**Implementation:**
```python
# src/api/websocket/event_bridge.py
import asyncio
from typing import Dict, Set, Optional
import logging
from src.core.event_bus import EventBus
from src.api.websocket_server import ConnectionManager

logger = logging.getLogger(__name__)

class EventBridge:
    """
    Bridges EventBus to WebSocket clients.

    Subscribes to EventBus topics and broadcasts to connected WebSocket clients
    based on their subscriptions.

    Topics Supported:
    - market_data
    - indicator_updated
    - signal_generated
    - order_created
    - order_filled
    - position_updated
    - risk_alert
    """

    def __init__(
        self,
        event_bus: EventBus,
        connection_manager: ConnectionManager
    ):
        self.event_bus = event_bus
        self.connection_manager = connection_manager

        # Client subscriptions: client_id → Set[topics]
        self.client_subscriptions: Dict[str, Set[str]] = {}

    async def start(self):
        """Subscribe to EventBus topics."""
        logger.info("Starting EventBridge...")

        topics = [
            "market_data",
            "indicator_updated",
            "signal_generated",
            "order_created",
            "order_filled",
            "order_cancelled",
            "position_updated",
            "risk_alert"
        ]

        for topic in topics:
            self.event_bus.subscribe(topic, self._create_handler(topic))

    def subscribe_client(self, client_id: str, topics: Set[str]):
        """Subscribe client to topics."""
        self.client_subscriptions[client_id] = topics
        logger.info(f"Client {client_id} subscribed to: {topics}")

    def unsubscribe_client(self, client_id: str):
        """Unsubscribe client from all topics."""
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
            logger.info(f"Client {client_id} unsubscribed")

    def _create_handler(self, topic: str):
        """Create EventBus handler for topic."""
        async def handler(data: Dict):
            await self._broadcast_to_subscribers(topic, data)
        return handler

    async def _broadcast_to_subscribers(self, topic: str, data: Dict):
        """Broadcast event to subscribed WebSocket clients."""
        # Find clients subscribed to this topic
        target_clients = [
            client_id
            for client_id, topics in self.client_subscriptions.items()
            if topic in topics
        ]

        if not target_clients:
            return

        # Filter by symbol if applicable
        symbol = data.get("symbol")
        if symbol:
            # Only send to clients subscribed to this symbol
            # (symbol subscriptions stored in connection_manager)
            target_clients = [
                c for c in target_clients
                if self.connection_manager.is_subscribed_to_symbol(c, symbol)
            ]

        logger.debug(
            f"Broadcasting {topic} to {len(target_clients)} clients"
        )

        # Broadcast message
        message = {
            "type": topic,
            "data": data,
            "timestamp": data.get("timestamp", time.time())
        }

        await self.connection_manager.broadcast_to_clients(target_clients, message)
```

**ConnectionManager Modifications:**
```python
# src/api/websocket_server.py (add symbol subscription tracking)

class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_symbols: Dict[str, Set[str]] = {}  # client_id → symbols

    def subscribe_to_symbol(self, client_id: str, symbol: str):
        """Subscribe client to symbol-specific updates."""
        if client_id not in self.client_symbols:
            self.client_symbols[client_id] = set()
        self.client_symbols[client_id].add(symbol)

    def unsubscribe_from_symbol(self, client_id: str, symbol: str):
        """Unsubscribe client from symbol."""
        if client_id in self.client_symbols:
            self.client_symbols[client_id].discard(symbol)

    def is_subscribed_to_symbol(self, client_id: str, symbol: str) -> bool:
        """Check if client is subscribed to symbol."""
        return symbol in self.client_symbols.get(client_id, set())

    async def broadcast_to_clients(self, client_ids: List[str], message: Dict):
        """Broadcast message to specific clients."""
        for client_id in client_ids:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send to client {client_id}: {e}")
```

**Integration with unified_server.py:**
```python
# src/api/unified_server.py (modify lifespan)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    container = Container(settings)
    app.state.container = container

    event_bus = container.get_event_bus()
    connection_manager = container.get_connection_manager()
    event_bridge = EventBridge(event_bus, connection_manager)

    await event_bridge.start()
    app.state.event_bridge = event_bridge

    yield

    # Shutdown
    await event_bus.shutdown()
```

**WebSocket Subscribe Message:**
```typescript
// Frontend client subscribes to topics
const ws = new WebSocket('ws://localhost:8080/ws');

ws.send(JSON.stringify({
  type: 'subscribe',
  topics: ['signal_generated', 'order_filled', 'position_updated', 'risk_alert'],
  symbols: ['BTC_USDT', 'ETH_USDT']
}));

// Receive events
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'signal_generated':
      // Add signal to SignalLog
      break;
    case 'order_filled':
      // Update OrderHistory
      break;
    case 'position_updated':
      // Update PositionMonitor
      break;
    case 'risk_alert':
      // Show RiskAlert notification
      break;
  }
};
```

**Testing:**
```python
# tests_e2e/integration/test_event_bridge.py
import pytest
from src.api.websocket.event_bridge import EventBridge
from src.core.event_bus import EventBus
from src.api.websocket_server import ConnectionManager
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_event_bridge_broadcasts_to_subscribed_clients():
    """Test that EventBridge broadcasts events to subscribed clients."""
    event_bus = EventBus()
    connection_manager = ConnectionManager()

    # Mock WebSocket connection
    mock_ws = AsyncMock()
    connection_manager.active_connections["client_1"] = mock_ws

    event_bridge = EventBridge(event_bus, connection_manager)
    await event_bridge.start()

    # Subscribe client to topic
    event_bridge.subscribe_client("client_1", {"signal_generated"})
    connection_manager.subscribe_to_symbol("client_1", "BTC_USDT")

    # Publish event to EventBus
    await event_bus.publish("signal_generated", {
        "symbol": "BTC_USDT",
        "signal_type": "S1",
        "confidence": 0.85
    })

    # Wait for event processing
    await asyncio.sleep(0.1)

    # WebSocket should have received message
    mock_ws.send_json.assert_called_once()
    call_args = mock_ws.send_json.call_args[0][0]
    assert call_args["type"] == "signal_generated"
    assert call_args["data"]["symbol"] == "BTC_USDT"
```

**Completion Criteria:**
- [ ] EventBridge subscribes to all 7 EventBus topics
- [ ] Client subscription management works
- [ ] Symbol filtering works (only sends symbol-specific events)
- [ ] Broadcast to multiple clients works
- [ ] WebSocket subscribe/unsubscribe messages work
- [ ] Integration test: EventBus event → WebSocket client receives message

---

### Task 1.6: REST API Endpoints for Trading (4h)

**File:** `src/api/rest/trading_routes.py` (complete with all endpoints from Gap #1)

**Missing Endpoints (from Target State Architecture Gap #1):**
```python
# src/api/rest/trading_routes.py (complete file)
from fastapi import APIRouter, Depends, HTTPException, Query
from src.infrastructure.container import Container
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter()

# --- Performance Metrics ---

@router.get("/api/trading/performance/{session_id}")
async def get_performance_metrics(
    session_id: str,
    container: Container = Depends()
):
    """
    Get performance metrics for trading session.

    Metrics:
    - Total PnL (realized + unrealized)
    - Win rate (% of profitable trades)
    - Sharpe ratio (risk-adjusted return)
    - Max drawdown
    - Number of trades
    """
    # Query from QuestDB: completed orders + positions
    questdb_client = container.get_questdb_client()

    # Get all orders for session
    orders_query = """
        SELECT
            symbol,
            side,
            quantity,
            average_fill_price,
            created_at
        FROM orders
        WHERE session_id = $1 AND status = 'filled'
        ORDER BY created_at
    """
    orders = await questdb_client.pool.fetch(orders_query, session_id)

    # Calculate metrics
    total_realized_pnl = 0.0
    winning_trades = 0
    losing_trades = 0

    # Track positions to calculate PnL
    positions_map = {}  # symbol → (quantity, entry_price)

    for order in orders:
        symbol = order["symbol"]
        side = order["side"]
        quantity = order["quantity"]
        price = order["average_fill_price"]

        if symbol not in positions_map:
            # Opening position
            positions_map[symbol] = {
                "quantity": quantity if side == "buy" else -quantity,
                "entry_price": price,
                "entry_time": order["created_at"]
            }
        else:
            # Closing or adding to position
            pos = positions_map[symbol]

            if (side == "buy" and pos["quantity"] < 0) or (side == "sell" and pos["quantity"] > 0):
                # Closing position (opposite side)
                close_quantity = min(abs(pos["quantity"]), quantity)

                if pos["quantity"] > 0:  # Long position
                    pnl = (price - pos["entry_price"]) * close_quantity
                else:  # Short position
                    pnl = (pos["entry_price"] - price) * close_quantity

                total_realized_pnl += pnl

                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1

                # Update position
                pos["quantity"] -= close_quantity * (1 if side == "sell" else -1)

    total_trades = winning_trades + losing_trades
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    # Get unrealized PnL from current positions
    position_sync = container.get_position_sync_service()
    total_unrealized_pnl = position_sync.get_total_unrealized_pnl()

    return {
        "session_id": session_id,
        "total_pnl": total_realized_pnl + total_unrealized_pnl,
        "realized_pnl": total_realized_pnl,
        "unrealized_pnl": total_unrealized_pnl,
        "win_rate": win_rate,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades
    }

# --- Order Management (already defined in Task 1.1) ---
# GET /api/trading/orders
# POST /api/trading/orders/{order_id}/cancel

# --- Position Management (already defined in Task 1.2) ---
# GET /api/trading/positions
# POST /api/trading/positions/{symbol}/close
```

**Register in unified_server.py:**
```python
# src/api/unified_server.py (add trading routes)
from src.api.rest import trading_routes

app.include_router(trading_routes.router, tags=["Trading"])
```

**Testing:**
```python
# tests_e2e/api/test_trading_routes.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_performance_metrics(client: AsyncClient):
    """Test GET /api/trading/performance/{session_id}"""
    response = await client.get("/api/trading/performance/test_session_123")

    assert response.status_code == 200
    data = response.json()
    assert "total_pnl" in data
    assert "win_rate" in data
    assert "total_trades" in data
```

**Completion Criteria:**
- [ ] GET /api/trading/performance/{session_id} returns correct metrics
- [ ] GET /api/trading/orders returns all orders
- [ ] POST /api/trading/orders/{id}/cancel cancels order
- [ ] GET /api/trading/positions returns positions with margin ratio
- [ ] POST /api/trading/positions/{symbol}/close closes position
- [ ] All 5 endpoints pass API tests

---

### Phase 1 Summary

**Total Time:** 60h

**Critical Path:**
```
EventBus (Phase 0) → LiveOrderManager (16h) → PositionSyncService (12h) → MEXC Adapter (12h)
                                           ↓
                              Strategy Integration (8h) + EventBridge (8h) + REST API (4h)
```

**Deliverables:**
- ✅ LiveOrderManager with retry logic and order queue
- ✅ PositionSyncService with liquidation detection
- ✅ MEXC Adapter with complete order execution
- ✅ Strategy → Signal → Order flow integrated
- ✅ WebSocket EventBridge for real-time UI updates
- ✅ 5 REST API endpoints for trading operations

**Testing Coverage Added:** +40 unit tests, +15 integration tests

**Milestone 1 Achieved:** Paper Trading Ready (after Phase 0 + Phase 1 = 92h)

**Next Phase:** Phase 2 - Testing (40h) to reach 80% coverage

---

## Part IV: Phase 2 - Testing & Quality Assurance (40h)

**Goal:** Achieve 80% test coverage and ensure system reliability before live trading.

**Prerequisites:** Phase 0 + Phase 1 complete

**Deliverables:**
- 80% code coverage
- All critical paths tested
- Integration tests for full workflows
- E2E tests for UI workflows

### Task 2.1: Unit Tests for Core Components (16h)

**Components to Test:**
- EventBus (Phase 0)
- Circuit Breaker (Phase 0)
- RiskManager (Phase 0)
- LiveOrderManager (Phase 1)
- PositionSyncService (Phase 1)
- StrategyManager (existing, add coverage)
- StreamingIndicatorEngine (existing, add coverage)

**Test Structure:**
```
tests_e2e/unit/
├── core/
│   └── test_event_bus.py (12 tests)
├── infrastructure/
│   ├── test_circuit_breaker.py (10 tests)
│   └── test_mexc_adapter.py (8 tests - mocked)
├── domain/
│   ├── services/
│   │   ├── test_risk_manager.py (15 tests)
│   │   ├── test_order_manager_live.py (20 tests)
│   │   ├── test_position_sync_service.py (15 tests)
│   │   ├── test_strategy_manager.py (18 tests)
│   │   └── test_streaming_indicator_engine.py (25 tests)
│   └── calculators/
│       └── test_indicator_calculator.py (12 tests)
```

**Key Test Scenarios:**

**EventBus Tests:**
```python
# tests_e2e/unit/core/test_event_bus.py
- test_subscribe_and_publish()
- test_unsubscribe()
- test_multiple_subscribers()
- test_retry_on_failure()
- test_max_retries_exceeded()
- test_no_subscribers()
- test_subscriber_cleanup_on_unsubscribe()
- test_concurrent_publish()
- test_subscriber_exception_doesnt_affect_others()
- test_memory_leak_prevention() # 10k subscribe/unsubscribe cycles
- test_shutdown()
- test_list_topics()
```

**Circuit Breaker Tests:**
```python
# tests_e2e/unit/infrastructure/test_circuit_breaker.py
- test_closed_state_allows_calls()
- test_opens_after_threshold_failures()
- test_blocks_calls_when_open()
- test_transitions_to_half_open_after_timeout()
- test_half_open_success_closes_circuit()
- test_half_open_failure_reopens_circuit()
- test_failure_count_resets_outside_window()
- test_manual_reset()
- test_get_state()
- test_concurrent_failures()
```

**RiskManager Tests:**
```python
# tests_e2e/unit/domain/services/test_risk_manager.py
- test_validate_order_within_limits()
- test_validate_order_budget_exceeded()
- test_validate_order_position_size_too_large()
- test_validate_order_max_positions_reached()
- test_validate_order_daily_loss_limit()
- test_margin_ratio_alert_below_threshold()
- test_margin_ratio_ok_above_threshold()
- test_position_opened_allocates_budget()
- test_position_closed_releases_budget()
- test_position_liquidated_emits_alert()
- test_daily_pnl_tracking()
- test_reset_daily_metrics()
- test_concurrent_order_validation()
- test_budget_allocation_race_condition()
- test_max_positions_concurrent()
```

**Coverage Target:** 80% overall, 100% for critical paths (order submission, position sync, risk validation)

**Completion Criteria:**
- [ ] 135+ unit tests written
- [ ] 80% coverage achieved (measured by pytest-cov)
- [ ] All critical components have >90% coverage
- [ ] Memory leak tests pass (10k cycles)
- [ ] Concurrency tests pass (race conditions)

---

### Task 2.2: Integration Tests (12h)

**Test Workflows:**
```
tests_e2e/integration/
├── test_data_collection_workflow.py
├── test_backtest_workflow.py
├── test_live_trading_workflow.py (paper trading)
├── test_strategy_order_flow.py (already defined in Task 1.4)
├── test_event_bridge.py (already defined in Task 1.5)
├── test_mexc_adapter_integration.py (already defined in Task 1.3)
└── test_position_recovery_after_crash.py
```

**Key Integration Tests:**

**1. Data Collection Workflow (2h):**
```python
# test_data_collection_workflow.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_data_collection_workflow():
    """
    Test: POST /sessions/start (collect mode)
          → Market data streams from MEXC
          → Data written to QuestDB tick_prices
          → WebSocket broadcasts progress
          → POST /sessions/stop
          → Session finalized in data_collection_sessions
    """
    # Start data collection
    response = await client.post("/api/sessions/start", json={
        "mode": "collect",
        "symbols": ["BTC_USDT"],
        "duration_seconds": 10
    })
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # Wait for collection
    await asyncio.sleep(10)

    # Stop collection
    response = await client.post(f"/api/sessions/{session_id}/stop")
    assert response.status_code == 200

    # Verify data in QuestDB
    questdb = container.get_questdb_client()
    rows = await questdb.pool.fetch(
        "SELECT COUNT(*) as count FROM tick_prices WHERE session_id = $1",
        session_id
    )
    assert rows[0]["count"] > 0
```

**2. Backtest Workflow (2h):**
```python
# test_backtest_workflow.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_backtest_workflow():
    """
    Test: Select historical session
          → POST /sessions/start (backtest mode)
          → Indicators calculate incrementally
          → Strategy generates signals
          → Orders tracked (simulated)
          → Results saved to backtest_results/
    """
    # Get historical session
    response = await client.get("/api/data-collection/sessions")
    sessions = response.json()["sessions"]
    historical_session_id = sessions[0]["session_id"]

    # Start backtest
    response = await client.post("/api/sessions/start", json={
        "mode": "backtest",
        "session_id": historical_session_id,
        "strategy_names": ["TestStrategy"],
        "acceleration_factor": 10.0
    })
    assert response.status_code == 200
    backtest_session_id = response.json()["session_id"]

    # Wait for completion
    await asyncio.sleep(30)

    # Check results
    response = await client.get(f"/api/sessions/{backtest_session_id}/results")
    assert response.status_code == 200
    results = response.json()
    assert "total_pnl" in results
    assert "total_trades" in results
```

**3. Live Trading Workflow (Paper Trading) (4h):**
```python
# test_live_trading_workflow.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_paper_trading_workflow():
    """
    Test: POST /sessions/start (paper mode)
          → MEXC paper adapter (simulated fills)
          → Strategy generates S1 signal
          → RiskManager validates order
          → LiveOrderManager submits order
          → Order fills (simulated)
          → Position opens
          → PositionSyncService tracks position
          → Strategy generates E1 signal
          → Position closes
          → Performance metrics calculated
    """
    # Start paper trading
    response = await client.post("/api/sessions/start", json={
        "mode": "paper",
        "symbols": ["BTC_USDT"],
        "strategy_names": ["TestStrategy"],
        "budget_usd": 1000.0
    })
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # Wait for signals and orders
    await asyncio.sleep(60)

    # Check orders
    response = await client.get(f"/api/trading/orders?session_id={session_id}")
    orders = response.json()["orders"]
    assert len(orders) > 0

    # Check positions
    response = await client.get("/api/trading/positions")
    positions = response.json()["positions"]
    # May be 0 if position closed, or 1+ if still open

    # Stop trading
    response = await client.post(f"/api/sessions/{session_id}/stop")
    assert response.status_code == 200

    # Check performance
    response = await client.get(f"/api/trading/performance/{session_id}")
    assert response.status_code == 200
    metrics = response.json()
    assert "total_pnl" in metrics
```

**4. Position Recovery After Crash (2h):**
```python
# test_position_recovery_after_crash.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_position_recovery_after_restart():
    """
    Test: System crashes with open position
          → Restart system
          → PositionSyncService fetches positions from MEXC
          → Local positions restored
          → Trading continues
    """
    # Start live trading with position
    # (Simulate crash by killing ExecutionController)
    # Restart ExecutionController
    # Verify position_sync_service recovers position
```

**5. Order Slippage Tracking (2h):**
```python
# test_order_slippage.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_order_slippage_tracking():
    """
    Test: Market order submitted at price X
          → Order fills at price Y
          → Slippage = |Y - X|
          → Slippage tracked in order_filled event
          → UI displays slippage in OrderHistory
    """
```

**Completion Criteria:**
- [ ] Data collection workflow test passes
- [ ] Backtest workflow test passes
- [ ] Paper trading workflow test passes (60s session)
- [ ] Position recovery test passes
- [ ] Order slippage tracking test passes
- [ ] All integration tests pass consistently (no flaky tests)

---

### Task 2.3: E2E Frontend Tests (8h)

**Test Framework:** Playwright (already used in tests_e2e/frontend/)

**Test Scenarios:**
```
tests_e2e/frontend/
├── test_data_collection_ui.spec.ts (existing, extend)
├── test_backtest_ui.spec.ts (existing, extend)
├── test_live_trading_ui.spec.ts (new)
├── test_trading_chart.spec.ts (new)
├── test_position_monitor.spec.ts (new)
└── test_risk_alerts.spec.ts (new)
```

**Key E2E Tests:**

**1. Live Trading UI Workflow (3h):**
```typescript
// test_live_trading_ui.spec.ts
test('start live trading session and monitor', async ({ page }) => {
  // Navigate to trading page
  await page.goto('http://localhost:3000/trading');

  // Fill in session details (QuickSessionStarter)
  await page.fill('[name="symbols"]', 'BTC_USDT');
  await page.selectOption('[name="strategy"]', 'TestStrategy');
  await page.fill('[name="budget"]', '1000');
  await page.selectOption('[name="mode"]', 'paper');

  // Start session
  await page.click('button:text("Start Trading")');

  // Verify TradingChart renders
  await page.waitForSelector('.trading-chart-container');

  // Wait for signal marker to appear
  await page.waitForSelector('.signal-marker', { timeout: 30000 });

  // Verify SignalLog shows signal
  const signalLog = await page.locator('.signal-log-entry').first();
  await expect(signalLog).toContainText('S1');

  // Verify PositionMonitor shows position
  await page.waitForSelector('.position-row', { timeout: 10000 });
  const positionRow = await page.locator('.position-row').first();
  await expect(positionRow).toContainText('BTC_USDT');

  // Verify OrderHistory shows order
  const orderRow = await page.locator('.order-row').first();
  await expect(orderRow).toContainText('filled');

  // Stop session
  await page.click('button:text("Stop Trading")');
});
```

**2. TradingChart Interaction (2h):**
```typescript
// test_trading_chart.spec.ts
test('trading chart displays signals and updates', async ({ page }) => {
  await page.goto('http://localhost:3000/trading');

  // Start session with historical data
  // ...

  // Verify chart renders
  const chart = await page.locator('.trading-chart');
  await expect(chart).toBeVisible();

  // Verify candlesticks render
  await page.waitForSelector('.candlestick', { timeout: 5000 });

  // Verify signal markers render
  const s1Marker = await page.locator('.signal-marker[data-type="S1"]').first();
  await expect(s1Marker).toBeVisible();

  // Hover over signal marker
  await s1Marker.hover();

  // Verify tooltip shows signal details
  const tooltip = await page.locator('.signal-tooltip');
  await expect(tooltip).toContainText('Entry Signal');
  await expect(tooltip).toContainText('Confidence');
});
```

**3. RiskAlerts Notification (2h):**
```typescript
// test_risk_alerts.spec.ts
test('risk alert displays and plays sound', async ({ page }) => {
  await page.goto('http://localhost:3000/trading');

  // Start session
  // ...

  // Simulate low margin alert (via WebSocket mock or real event)
  // ...

  // Verify alert appears in RiskAlerts component
  await page.waitForSelector('.risk-alert.severity-high', { timeout: 10000 });
  const alert = await page.locator('.risk-alert').first();
  await expect(alert).toContainText('Low margin ratio');

  // Verify sound plays (check audio element)
  const audio = await page.locator('audio[data-testid="alert-sound"]');
  const isPaused = await audio.evaluate((el: HTMLAudioElement) => el.paused);
  expect(isPaused).toBe(false);  // Sound should be playing

  // Acknowledge alert
  await page.click('.risk-alert button:text("Acknowledge")');

  // Verify alert disappears
  await expect(alert).not.toBeVisible();
});
```

**4. InlineEdit Component (1h):**
```typescript
// test_inline_edit.spec.ts
test('inline edit updates value on Enter', async ({ page }) => {
  await page.goto('http://localhost:3000/trading');

  // Click on editable budget field
  await page.click('.inline-edit[data-field="budget"]');

  // Input should be focused
  const input = await page.locator('.inline-edit input');
  await expect(input).toBeFocused();

  // Type new value
  await input.fill('2000');

  // Press Enter
  await input.press('Enter');

  // Verify value updated
  await expect(page.locator('.inline-edit[data-field="budget"]')).toContainText('$2,000');
});
```

**Completion Criteria:**
- [ ] Live trading UI workflow test passes
- [ ] TradingChart renders signals correctly
- [ ] PositionMonitor displays positions with margin ratio
- [ ] OrderHistory displays orders with slippage
- [ ] SignalLog displays full history
- [ ] RiskAlerts plays sound and allows acknowledge
- [ ] InlineEdit component works (Enter/Escape)
- [ ] All E2E tests pass on CI

---

### Task 2.4: Load Testing & Performance (4h)

**Goal:** Verify system handles expected load for pump & dump trading.

**Test Scenarios:**

**1. High-Frequency Market Data (1h):**
```python
# tests_e2e/performance/test_market_data_load.py
@pytest.mark.performance
@pytest.mark.asyncio
async def test_1000_ticks_per_second():
    """
    Test: EventBus handles 1000 ticks/sec
          → StreamingIndicatorEngine processes all ticks
          → No backpressure or dropped messages
    """
    event_bus = EventBus()
    indicator_engine = StreamingIndicatorEngine(event_bus)

    await indicator_engine.start()

    # Publish 10,000 ticks over 10 seconds (1000/sec)
    start_time = time.time()
    for i in range(10000):
        await event_bus.publish("market_data", {
            "symbol": "BTC_USDT",
            "price": 50000 + random.uniform(-100, 100),
            "volume": 1.0,
            "timestamp": time.time()
        })
        await asyncio.sleep(0.001)  # 1ms between ticks

    elapsed = time.time() - start_time
    assert elapsed < 15  # Should complete within 15s (some buffer)

    # Verify all ticks processed
    assert indicator_engine.processed_count == 10000
```

**2. Multiple Concurrent Sessions (1h):**
```python
# tests_e2e/performance/test_concurrent_sessions.py
@pytest.mark.performance
@pytest.mark.asyncio
async def test_5_concurrent_trading_sessions():
    """
    Test: 5 paper trading sessions running simultaneously
          → Each session has 3 strategies
          → All sessions process market data
          → No interference between sessions
    """
    sessions = []
    for i in range(5):
        response = await client.post("/api/sessions/start", json={
            "mode": "paper",
            "symbols": [f"SYM{i}_USDT"],
            "strategy_names": ["Strategy1", "Strategy2", "Strategy3"],
            "budget_usd": 1000.0
        })
        sessions.append(response.json()["session_id"])

    # Run for 60 seconds
    await asyncio.sleep(60)

    # Stop all sessions
    for session_id in sessions:
        await client.post(f"/api/sessions/{session_id}/stop")

    # Verify each session has orders
    for session_id in sessions:
        response = await client.get(f"/api/trading/orders?session_id={session_id}")
        orders = response.json()["orders"]
        assert len(orders) > 0
```

**3. WebSocket Broadcast Load (1h):**
```python
# tests_e2e/performance/test_websocket_broadcast.py
@pytest.mark.performance
@pytest.mark.asyncio
async def test_100_websocket_clients():
    """
    Test: 100 WebSocket clients connected
          → EventBus publishes signal_generated
          → All 100 clients receive message within 1s
    """
    clients = []
    for i in range(100):
        ws = await websocket_connect("ws://localhost:8080/ws")
        await ws.send_json({"type": "subscribe", "topics": ["signal_generated"]})
        clients.append(ws)

    # Publish event
    start_time = time.time()
    await event_bus.publish("signal_generated", {
        "symbol": "BTC_USDT",
        "signal_type": "S1",
        "confidence": 0.85
    })

    # Wait for all clients to receive
    received_count = 0
    for ws in clients:
        try:
            message = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
            if message["type"] == "signal_generated":
                received_count += 1
        except asyncio.TimeoutError:
            pass

    elapsed = time.time() - start_time

    assert received_count >= 95  # Allow 5% loss
    assert elapsed < 1.0  # All messages within 1s
```

**4. Memory Usage Monitoring (1h):**
```python
# tests_e2e/performance/test_memory_usage.py
@pytest.mark.performance
@pytest.mark.asyncio
async def test_memory_stable_over_1hour():
    """
    Test: System runs for 1 hour
          → Memory usage measured every 5 minutes
          → No memory leak (< 10% growth)
    """
    import psutil
    process = psutil.Process()

    initial_memory = process.memory_info().rss / (1024**2)  # MB

    # Start trading session
    response = await client.post("/api/sessions/start", json={
        "mode": "paper",
        "symbols": ["BTC_USDT"],
        "strategy_names": ["TestStrategy"],
        "budget_usd": 1000.0
    })
    session_id = response.json()["session_id"]

    # Run for 1 hour, measure memory every 5 minutes
    memory_samples = []
    for _ in range(12):  # 12 * 5 min = 60 min
        await asyncio.sleep(300)  # 5 minutes
        current_memory = process.memory_info().rss / (1024**2)
        memory_samples.append(current_memory)

    # Stop session
    await client.post(f"/api/sessions/{session_id}/stop")

    # Check memory growth
    final_memory = memory_samples[-1]
    growth_pct = (final_memory - initial_memory) / initial_memory * 100

    assert growth_pct < 10  # < 10% memory growth
```

**Completion Criteria:**
- [ ] System handles 1000 ticks/sec without dropped messages
- [ ] 5 concurrent sessions run without interference
- [ ] 100 WebSocket clients receive messages within 1s
- [ ] Memory growth < 10% over 1 hour
- [ ] CPU usage < 80% under normal load

---

### Phase 2 Summary

**Total Time:** 40h

**Deliverables:**
- ✅ 135+ unit tests (80% coverage)
- ✅ 12+ integration tests (full workflows)
- ✅ 10+ E2E frontend tests (Playwright)
- ✅ 4+ performance tests (load, memory, concurrency)

**Testing Coverage:**
- Unit: 80% overall, 100% critical paths
- Integration: All major workflows covered
- E2E: Complete UI workflows tested
- Performance: System validated for pump & dump trading load

**Next Phase:** Phase 3 - Monitoring & Observability (24h)

---

## Part V: Phase 3 - Monitoring & Observability (24h)

**Goal:** Full visibility into system health and trading performance.

**Prerequisites:** Phase 0-2 complete

**Deliverables:**
- Prometheus metrics collection
- Grafana dashboards
- Alertmanager rules
- Log aggregation

### Task 3.1: Prometheus Metrics (8h)

**Install Dependencies:**
```bash
pip install prometheus-client
```

**Implementation:**
```python
# src/infrastructure/monitoring/metrics.py (new file)
from prometheus_client import Counter, Gauge, Histogram, Summary
import time

# Order Metrics
orders_submitted_total = Counter(
    'orders_submitted_total',
    'Total orders submitted',
    ['symbol', 'side', 'order_type']
)

orders_filled_total = Counter(
    'orders_filled_total',
    'Total orders filled',
    ['symbol', 'side']
)

orders_failed_total = Counter(
    'orders_failed_total',
    'Total orders failed',
    ['symbol', 'reason']
)

order_submission_duration = Histogram(
    'order_submission_duration_seconds',
    'Time to submit order to exchange',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Position Metrics
open_positions = Gauge(
    'open_positions',
    'Number of open positions',
    ['symbol']
)

unrealized_pnl_usd = Gauge(
    'unrealized_pnl_usd',
    'Unrealized PnL in USD',
    ['symbol']
)

margin_ratio = Gauge(
    'margin_ratio',
    'Current margin ratio (equity / maintenance_margin)',
    ['symbol']
)

# Risk Metrics
risk_alerts_total = Counter(
    'risk_alerts_total',
    'Total risk alerts triggered',
    ['severity', 'type']
)

daily_pnl_usd = Gauge(
    'daily_pnl_usd',
    'Daily realized PnL in USD'
)

# Circuit Breaker Metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half_open, 2=open)'
)

circuit_breaker_failures = Counter(
    'circuit_breaker_failures_total',
    'Total circuit breaker failures'
)

# Event Bus Metrics
eventbus_published_total = Counter(
    'eventbus_published_total',
    'Total events published',
    ['topic']
)

eventbus_subscribers = Gauge(
    'eventbus_subscribers',
    'Number of subscribers per topic',
    ['topic']
)

# WebSocket Metrics
websocket_connections = Gauge(
    'websocket_connections',
    'Number of active WebSocket connections'
)

websocket_messages_sent = Counter(
    'websocket_messages_sent_total',
    'Total WebSocket messages sent',
    ['type']
)

# System Metrics
active_sessions = Gauge(
    'active_sessions',
    'Number of active trading sessions',
    ['mode']
)
```

**Instrument Components:**
```python
# src/domain/services/order_manager_live.py (add metrics)
from src.infrastructure.monitoring.metrics import (
    orders_submitted_total,
    orders_filled_total,
    orders_failed_total,
    order_submission_duration
)

async def submit_order(self, order: Order) -> bool:
    # Start timer
    start_time = time.time()

    try:
        # Submit order
        success = await self._submit_order_impl(order)

        # Record metrics
        if success:
            orders_submitted_total.labels(
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type
            ).inc()
        else:
            orders_failed_total.labels(
                symbol=order.symbol,
                reason="submission_failed"
            ).inc()

        return success

    finally:
        # Record duration
        duration = time.time() - start_time
        order_submission_duration.observe(duration)

async def _update_order_status(self, order: Order, exchange_status: Dict):
    # ... existing code ...

    if order.status == OrderStatus.FILLED:
        orders_filled_total.labels(
            symbol=order.symbol,
            side=order.side
        ).inc()
```

**Expose Metrics Endpoint:**
```python
# src/api/rest/metrics_routes.py (new file)
from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

**Completion Criteria:**
- [ ] 25+ metrics defined and instrumented
- [ ] GET /metrics endpoint returns Prometheus format
- [ ] Metrics update in real-time during trading
- [ ] Prometheus scrapes metrics successfully

---

### Task 3.2: Grafana Dashboards (8h)

**Install Grafana:**
```yaml
# docker-compose.yml (add Grafana)
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
```

**Prometheus Config:**
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fx_trading_system'
    static_configs:
      - targets: ['host.docker.internal:8080']
```

**Dashboard 1: Trading Overview (2h):**
```json
// monitoring/grafana/dashboards/trading_overview.json
{
  "title": "Trading Overview",
  "panels": [
    {
      "title": "Total Orders (24h)",
      "targets": [{"expr": "sum(increase(orders_submitted_total[24h]))"}],
      "type": "stat"
    },
    {
      "title": "Orders by Status",
      "targets": [
        {"expr": "sum by (status) (orders_submitted_total)", "legendFormat": "{{status}}"}
      ],
      "type": "timeseries"
    },
    {
      "title": "Open Positions",
      "targets": [{"expr": "sum(open_positions)"}],
      "type": "gauge"
    },
    {
      "title": "Daily PnL",
      "targets": [{"expr": "daily_pnl_usd"}],
      "type": "stat"
    },
    {
      "title": "Unrealized PnL by Symbol",
      "targets": [{"expr": "sum by (symbol) (unrealized_pnl_usd)"}],
      "type": "bargauge"
    }
  ]
}
```

**Dashboard 2: Risk Monitoring (2h):**
```json
// monitoring/grafana/dashboards/risk_monitoring.json
{
  "title": "Risk Monitoring",
  "panels": [
    {
      "title": "Margin Ratio (All Positions)",
      "targets": [{"expr": "min(margin_ratio)"}],
      "type": "gauge",
      "thresholds": [0.15, 0.25, 0.50]  // Red < 15%, Yellow < 25%
    },
    {
      "title": "Risk Alerts (24h)",
      "targets": [{"expr": "sum by (severity) (increase(risk_alerts_total[24h]))"}],
      "type": "bargauge"
    },
    {
      "title": "Circuit Breaker State",
      "targets": [{"expr": "circuit_breaker_state"}],
      "type": "stat",
      "mappings": [
        {"value": 0, "text": "CLOSED", "color": "green"},
        {"value": 1, "text": "HALF_OPEN", "color": "yellow"},
        {"value": 2, "text": "OPEN", "color": "red"}
      ]
    }
  ]
}
```

**Dashboard 3: System Performance (2h):**
```json
// monitoring/grafana/dashboards/system_performance.json
{
  "title": "System Performance",
  "panels": [
    {
      "title": "Order Submission Latency (p95)",
      "targets": [{"expr": "histogram_quantile(0.95, order_submission_duration_seconds_bucket)"}],
      "type": "timeseries"
    },
    {
      "title": "EventBus Messages/sec",
      "targets": [{"expr": "sum(rate(eventbus_published_total[1m]))"}],
      "type": "timeseries"
    },
    {
      "title": "WebSocket Connections",
      "targets": [{"expr": "websocket_connections"}],
      "type": "graph"
    },
    {
      "title": "Active Sessions by Mode",
      "targets": [{"expr": "sum by (mode) (active_sessions)"}],
      "type": "piechart"
    }
  ]
}
```

**Dashboard 4: Order Flow Analysis (1h):**
```json
// monitoring/grafana/dashboards/order_flow.json
{
  "title": "Order Flow Analysis",
  "panels": [
    {
      "title": "Order Submission Rate",
      "targets": [{"expr": "rate(orders_submitted_total[1m])"}],
      "type": "timeseries"
    },
    {
      "title": "Order Fill Rate",
      "targets": [{"expr": "rate(orders_filled_total[1m]) / rate(orders_submitted_total[1m])"}],
      "type": "timeseries"
    },
    {
      "title": "Failed Orders by Reason",
      "targets": [{"expr": "sum by (reason) (increase(orders_failed_total[24h]))"}],
      "type": "bargauge"
    }
  ]
}
```

**Dashboard 5: Exchange Health (1h):**
```json
// monitoring/grafana/dashboards/exchange_health.json
{
  "title": "Exchange Health",
  "panels": [
    {
      "title": "Circuit Breaker Failures",
      "targets": [{"expr": "increase(circuit_breaker_failures_total[5m])"}],
      "type": "stat",
      "thresholds": [0, 3, 10]  // Warn at 3, critical at 10
    },
    {
      "title": "MEXC API Latency (from order submission)",
      "targets": [{"expr": "histogram_quantile(0.95, order_submission_duration_seconds_bucket)"}],
      "type": "timeseries"
    }
  ]
}
```

**Completion Criteria:**
- [ ] 5 Grafana dashboards created
- [ ] Dashboards auto-provisioned on Grafana startup
- [ ] All panels display real data from Prometheus
- [ ] Thresholds configured for alerts (margin ratio < 15%)

---

### Task 3.3: Alertmanager Rules (4h)

**Install Alertmanager:**
```yaml
# docker-compose.yml (add Alertmanager)
  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
```

**Alert Rules:**
```yaml
# monitoring/prometheus_rules.yml
groups:
  - name: trading_alerts
    interval: 30s
    rules:
      # Critical Alerts
      - alert: MarginRatioCritical
        expr: min(margin_ratio) < 0.15
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Margin ratio below 15% - liquidation risk!"
          description: "Margin ratio is {{ $value | humanizePercentage }}"

      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state == 2
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker is OPEN - trading stopped"
          description: "Exchange API failures detected"

      - alert: LargeDailyLoss
        expr: daily_pnl_usd < -500
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Daily loss exceeds -$500"
          description: "Current daily PnL: ${{ $value }}"

      # High Priority Alerts
      - alert: HighOrderFailureRate
        expr: rate(orders_failed_total[5m]) / rate(orders_submitted_total[5m]) > 0.20
        for: 5m
        labels:
          severity: high
        annotations:
          summary: "Order failure rate > 20%"
          description: "{{ $value | humanizePercentage }} of orders failing"

      - alert: WebSocketConnectionLoss
        expr: websocket_connections == 0
        for: 1m
        labels:
          severity: high
        annotations:
          summary: "All WebSocket clients disconnected"
          description: "No active UI connections"

      # Medium Priority Alerts
      - alert: HighOrderLatency
        expr: histogram_quantile(0.95, order_submission_duration_seconds_bucket) > 2.0
        for: 5m
        labels:
          severity: medium
        annotations:
          summary: "Order submission latency > 2s (p95)"
          description: "Latency: {{ $value }}s"

      - alert: EventBusBackpressure
        expr: rate(eventbus_published_total[1m]) > 1000
        for: 2m
        labels:
          severity: medium
        annotations:
          summary: "EventBus under high load (> 1000 events/min)"
```

**Alertmanager Config:**
```yaml
# monitoring/alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@fxtrading.com'
  smtp_auth_username: 'alerts@fxtrading.com'
  smtp_auth_password: 'password'

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'

  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true

    - match:
        severity: critical
      receiver: 'email'

    - match:
        severity: high
      receiver: 'email'

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://localhost:8080/api/alerts/webhook'

  - name: 'email'
    email_configs:
      - to: 'team@fxtrading.com'
        headers:
          Subject: '[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

**Webhook Handler:**
```python
# src/api/rest/alerts_routes.py (new file)
from fastapi import APIRouter, Request
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/alerts/webhook")
async def alertmanager_webhook(request: Request):
    """Receive alerts from Alertmanager."""
    payload = await request.json()

    for alert in payload.get("alerts", []):
        logger.error(
            f"ALERT [{alert['status']}]: {alert['labels']['alertname']} - "
            f"{alert['annotations']['summary']}"
        )

        # Could also emit to EventBus for UI display
        # await event_bus.publish("risk_alert", {
        #     "severity": alert["labels"]["severity"],
        #     "type": alert["labels"]["alertname"],
        #     "message": alert["annotations"]["summary"]
        # })

    return {"status": "ok"}
```

**Completion Criteria:**
- [ ] 7+ alert rules configured
- [ ] Alerts trigger correctly (test by simulating conditions)
- [ ] Email notifications work
- [ ] PagerDuty integration works (critical alerts only)
- [ ] Webhook handler receives alerts

---

### Task 3.4: Log Aggregation (4h)

**Structured Logging Setup:**
```python
# src/infrastructure/logging/logger.py (new file)
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging(level=logging.INFO):
    """Configure structured JSON logging."""
    logger = logging.getLogger()
    logger.setLevel(level)

    # Console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
```

**Log Critical Events:**
```python
# src/domain/services/order_manager_live.py (add structured logging)
logger.info(
    "Order submitted",
    extra={
        "order_id": order.order_id,
        "symbol": order.symbol,
        "side": order.side,
        "quantity": order.quantity,
        "price": order.price,
        "exchange_order_id": exchange_order_id,
        "event_type": "order_submitted"
    }
)

logger.error(
    "Order submission failed",
    extra={
        "order_id": order.order_id,
        "symbol": order.symbol,
        "error": str(e),
        "attempt": attempt + 1,
        "event_type": "order_failed"
    }
)
```

**Completion Criteria:**
- [ ] Structured JSON logging configured
- [ ] Critical events logged (orders, positions, alerts)
- [ ] Logs written to stdout (Docker captures)
- [ ] Log levels configured per module

---

### Phase 3 Summary

**Total Time:** 24h

**Deliverables:**
- ✅ 25+ Prometheus metrics instrumented
- ✅ 5 Grafana dashboards
- ✅ 7+ Alertmanager rules
- ✅ Structured JSON logging

**Monitoring Coverage:**
- Orders (submission, fills, failures, latency)
- Positions (open, PnL, margin ratio)
- Risk (alerts, daily PnL, circuit breaker)
- System (EventBus, WebSocket, sessions)
- Exchange (API health, latency)

**Milestone 2 Achieved:** Live Trading $100 Ready (after Phase 0-3 = 156h)

**Go/No-Go for M2:**
- [ ] 7-day paper trading session successful (no crashes)
- [ ] All 7 alert rules working
- [ ] Grafana dashboards displaying real data
- [ ] 80% test coverage maintained

**Next Phase:** Phase 4 - Frontend UI (33h)

---

## Part VI: Phase 4 - Frontend UI (33h)

**Goal:** Complete UI for live trading monitoring and control.

**Prerequisites:** Phase 0-3 complete

**Deliverables:**
- TradingChart with signal markers
- PositionMonitor with margin ratio
- OrderHistory with slippage tracking
- SignalLog with full history
- RiskAlerts with sound notifications
- InlineEdit component (from PR #152)
- useSmartDefaults hook (from PR #152)

### Task 4.1: TradingChart Component (6h)

**File:** `frontend/src/components/trading/TradingChart.tsx` (new file)

**Implementation:** TradingView Lightweight Charts integration with signal markers (S1 🟡, Z1 🟢, ZE1 🔵, E1 🔴).

**Key Features:**
- Candlestick chart + volume
- Real-time WebSocket updates
- Signal markers on chart
- Tooltip on hover (signal type, confidence, indicators)
- Historical data from QuestDB

**Completion Criteria:**
- [ ] Chart renders with candlesticks
- [ ] WebSocket updates chart in real-time
- [ ] Signal markers appear correctly
- [ ] Tooltip shows signal details

---

### Task 4.2: PositionMonitor Component (4h)

**File:** `frontend/src/components/trading/PositionMonitor.tsx` (new file)

**Implementation:** Real-time position monitoring table.

**Key Features:**
- Position table (symbol, side, size, entry, current, PnL, margin ratio, liquidation price)
- Margin ratio gauge (< 15% = red alert)
- Close position button
- Updates every 1s via WebSocket

**Completion Criteria:**
- [ ] Table displays all positions
- [ ] Margin ratio color-coded (green > 25%, yellow 15-25%, red < 15%)
- [ ] Close button triggers POST /api/trading/positions/{symbol}/close
- [ ] Real-time updates work

---

### Task 4.3: OrderHistory Component (3h)

**File:** `frontend/src/components/trading/OrderHistory.tsx` (new file)

**Implementation:** Order history table with slippage tracking.

**Key Features:**
- All orders table (pending, filled, cancelled, failed)
- Slippage column (expected vs. actual price)
- Filters (status, symbol, time range)
- Cancel order button (for pending orders)

**Completion Criteria:**
- [ ] Table shows all orders
- [ ] Slippage calculated correctly
- [ ] Filters work
- [ ] Cancel button works

---

### Task 4.4: SignalLog Component (3h)

**File:** `frontend/src/components/trading/SignalLog.tsx` (new file)

**Implementation:** Full signal history log.

**Key Features:**
- Signal list (S1, O1, Z1, ZE1, E1) with timestamps
- Confidence scores
- Strategy name
- Execution results (order created/failed)
- Real-time updates via WebSocket

**Completion Criteria:**
- [ ] All signals displayed in chronological order
- [ ] Confidence scores visible
- [ ] Execution status shown
- [ ] Real-time updates work

---

### Task 4.5: RiskAlerts Component (2h)

**File:** `frontend/src/components/trading/RiskAlerts.tsx` (new file)

**Implementation:** Alert notifications with sound.

**Key Features:**
- Alert list (severity, message, timestamp)
- Sound notifications for critical alerts
- Acknowledge/dismiss button
- Alert types: low_margin, liquidation, daily_loss, circuit_breaker

**Completion Criteria:**
- [ ] Alerts appear in real-time via WebSocket
- [ ] Sound plays for critical alerts
- [ ] Acknowledge button works
- [ ] Alerts removed after acknowledge

---

### Task 4.6: WebSocket Integration (8h)

**File:** `frontend/src/hooks/useWebSocket.ts` (modify existing)

**Implementation:** Complete WebSocket integration with EventBridge.

**Key Features:**
- Auto-reconnect on disconnect
- Exponential backoff (1s, 2s, 4s, 8s, 16s)
- Heartbeat every 30s
- Topic subscription management
- Symbol filtering

**Topics to Subscribe:**
```typescript
const topics = [
  'market_data',
  'indicator_updated',
  'signal_generated',
  'order_created',
  'order_filled',
  'order_cancelled',
  'position_updated',
  'risk_alert'
];
```

**Completion Criteria:**
- [ ] WebSocket connects on mount
- [ ] Reconnects automatically on disconnect
- [ ] Heartbeat prevents timeout
- [ ] All 8 message types handled
- [ ] Symbol filtering works

---

### Task 4.7: PerformanceDashboard Component (3h)

**File:** `frontend/src/components/trading/PerformanceDashboard.tsx` (new file)

**Implementation:** Performance metrics visualization.

**Key Features:**
- Total PnL (realized + unrealized)
- Win rate gauge
- Number of trades
- Winning vs. losing trades chart

**Completion Criteria:**
- [ ] Metrics fetched from GET /api/trading/performance/{session_id}
- [ ] Charts render correctly
- [ ] Updates when session ends

---

### Task 4.8: Copy InlineEdit & useSmartDefaults from PR #152 (4h)

**Files:**
- `frontend/src/components/common/InlineEdit.tsx` (259 lines from PR #152)
- `frontend/src/hooks/useSmartDefaults.ts` (117 lines from PR #152 + safety mod)

**Modifications to useSmartDefaults:**
```typescript
// Add safety confirmation for live trading
const confirmLiveTrading = (budget: number) => {
  if (defaults.mode === 'live') {
    return window.confirm(
      `⚠️ START LIVE TRADING?\nBudget: ${budget}\nThis will use REAL money!`
    );
  }
  return true;
};
```

**Integration:**
- Use InlineEdit in PositionMonitor for stop-loss editing
- Use useSmartDefaults in QuickSessionStarter

**Completion Criteria:**
- [ ] InlineEdit component copied and works (Enter/Escape)
- [ ] useSmartDefaults copied with safety confirmation
- [ ] Integration tests pass

---

### Phase 4 Summary

**Total Time:** 33h

**Deliverables:**
- ✅ 7 new UI components (TradingChart, PositionMonitor, OrderHistory, SignalLog, RiskAlerts, PerformanceDashboard, QuickSessionStarter)
- ✅ WebSocket integration complete
- ✅ InlineEdit + useSmartDefaults from PR #152
- ✅ 3-panel layout (Left: session setup, Center: chart + signals, Right: positions + orders + alerts)

**Next Phase:** Phase 5 - Deployment (16h)

---

## Part VII: Phase 5 - Deployment & Infrastructure (16h)

**Goal:** Production-ready deployment with rollback capability.

**Prerequisites:** Phase 0-4 complete

**Deliverables:**
- Docker containers (backend + frontend)
- Blue-green deployment script
- Rollback script
- Nginx load balancer

### Task 5.1: Docker Containerization (4h)

**Files:**
```
Dockerfile.backend
Dockerfile.frontend
docker-compose.yml
.dockerignore
```

**Dockerfile.backend:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY database/ database/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "src.api.unified_server:create_unified_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
```

**Dockerfile.frontend:**
```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/out /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://admin:quest@questdb:8812/qdb
      - MEXC_API_KEY=${MEXC_API_KEY}
      - MEXC_API_SECRET=${MEXC_API_SECRET}
    depends_on:
      - questdb
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped

  questdb:
    image: questdb/questdb:latest
    ports:
      - "9000:9000"  # REST API
      - "8812:8812"  # PostgreSQL
      - "9009:9009"  # InfluxDB Line Protocol
    volumes:
      - questdb-data:/root/.questdb
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus_rules.yml:/etc/prometheus/rules.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./monitoring/grafana:/etc/grafana/provisioning
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    restart: unless-stopped

volumes:
  questdb-data:
  grafana-data:
```

**Completion Criteria:**
- [ ] Backend Docker image builds successfully
- [ ] Frontend Docker image builds successfully
- [ ] docker-compose up starts all services
- [ ] Health checks work
- [ ] All services accessible via ports

---

### Task 5.2: Blue-Green Deployment Script (4h)

**File:** `scripts/deploy.sh`

**Implementation:**
```bash
#!/bin/bash
set -e

BLUE_PORT=8080
GREEN_PORT=8081
HEALTH_CHECK_URL="http://localhost"
MAX_HEALTH_RETRIES=10
HEALTH_CHECK_INTERVAL=5

get_active_env() {
    if curl -sf ${HEALTH_CHECK_URL}:${BLUE_PORT}/health > /dev/null 2>&1; then
        echo "blue"
    elif curl -sf ${HEALTH_CHECK_URL}:${GREEN_PORT}/health > /dev/null 2>&1; then
        echo "green"
    else
        echo "none"
    fi
}

wait_for_health() {
    local port=$1
    local retries=0

    while [ $retries -lt $MAX_HEALTH_RETRIES ]; do
        if curl -sf ${HEALTH_CHECK_URL}:${port}/health/ready > /dev/null 2>&1; then
            echo "Health check passed for port $port"
            return 0
        fi
        echo "Waiting for health check ($retries/$MAX_HEALTH_RETRIES)..."
        sleep $HEALTH_CHECK_INTERVAL
        retries=$((retries + 1))
    done

    echo "Health check failed after $MAX_HEALTH_RETRIES attempts"
    return 1
}

deploy() {
    local active=$(get_active_env)
    local target_env
    local target_port

    if [ "$active" == "blue" ]; then
        target_env="green"
        target_port=$GREEN_PORT
    else
        target_env="blue"
        target_port=$BLUE_PORT
    fi

    echo "Active environment: $active"
    echo "Deploying to: $target_env (port $target_port)"

    # Build and start target environment
    docker-compose -f docker-compose.${target_env}.yml build
    docker-compose -f docker-compose.${target_env}.yml up -d

    # Wait for health check
    if ! wait_for_health $target_port; then
        echo "Deployment failed: health check timeout"
        docker-compose -f docker-compose.${target_env}.yml down
        exit 1
    fi

    # Switch Nginx to target environment
    echo "Switching Nginx to $target_env environment..."
    sed -i "s/proxy_pass.*$/proxy_pass http://localhost:${target_port};/" /etc/nginx/conf.d/trading.conf
    nginx -s reload

    echo "Deployment successful. Active: $target_env"

    # Stop old environment
    if [ "$active" != "none" ]; then
        echo "Stopping old environment: $active"
        docker-compose -f docker-compose.${active}.yml down
    fi
}

deploy
```

**Completion Criteria:**
- [ ] Script deploys to inactive environment
- [ ] Health checks pass before switch
- [ ] Nginx switches to new environment
- [ ] Old environment stopped after switch
- [ ] Rollback on health check failure

---

### Task 5.3: Rollback Script (4h)

**File:** `scripts/rollback.sh`

**Implementation:**
```bash
#!/bin/bash
set -e

rollback() {
    local active=$(get_active_env)
    local target_env

    if [ "$active" == "blue" ]; then
        target_env="green"
        target_port=$GREEN_PORT
    else
        target_env="blue"
        target_port=$BLUE_PORT
    fi

    echo "Rolling back from $active to $target_env"

    # Start previous environment
    docker-compose -f docker-compose.${target_env}.yml up -d

    # Wait for health check
    if ! wait_for_health $target_port; then
        echo "Rollback failed: previous environment unhealthy"
        exit 1
    fi

    # Switch Nginx back
    sed -i "s/proxy_pass.*$/proxy_pass http://localhost:${target_port};/" /etc/nginx/conf.d/trading.conf
    nginx -s reload

    # Stop current (failed) environment
    docker-compose -f docker-compose.${active}.yml down

    echo "Rollback successful. Active: $target_env"
}

rollback
```

**Completion Criteria:**
- [ ] Script restarts previous environment
- [ ] Health checks pass
- [ ] Nginx switches back
- [ ] Current environment stopped
- [ ] System operational after rollback

---

### Task 5.4: Database Migration Rollback (4h)

**File:** `scripts/rollback_migration.py`

**Implementation:**
```python
#!/usr/bin/env python3
import asyncio
import asyncpg
import sys

async def rollback_migration(migration_number: int):
    """Rollback database migration."""
    conn = await asyncpg.connect(
        host='localhost',
        port=8812,
        user='admin',
        password='quest',
        database='qdb'
    )

    try:
        # Read rollback SQL
        with open(f'database/migrations/{migration_number:03d}_rollback.sql') as f:
            rollback_sql = f.read()

        # Execute rollback
        await conn.execute(rollback_sql)

        # Update migration version
        await conn.execute(
            "DELETE FROM schema_migrations WHERE version = $1",
            migration_number
        )

        print(f"Successfully rolled back migration {migration_number}")

    finally:
        await conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python rollback_migration.py <migration_number>")
        sys.exit(1)

    migration_num = int(sys.argv[1])
    asyncio.run(rollback_migration(migration_num))
```

**Completion Criteria:**
- [ ] Script reads rollback SQL file
- [ ] Executes rollback SQL
- [ ] Updates schema_migrations table
- [ ] Handles errors gracefully

---

### Phase 5 Summary

**Total Time:** 16h

**Deliverables:**
- ✅ Docker containers for backend + frontend
- ✅ docker-compose.yml with all services
- ✅ Blue-green deployment script
- ✅ Rollback script
- ✅ Database migration rollback

**Production Readiness:** 100% (after all phases complete)

---

## Part VIII: Critical Path Analysis

**Total Project Timeline:** 205 hours (5-6 weeks with 1 engineer)

### Critical Path (Blocking Dependencies)

```
START
  ↓
Phase 0: EventBus (8h) ← CRITICAL - blocks everything
  ↓
Phase 0: Circuit Breaker (6h) ← CRITICAL - blocks MEXC integration
  ↓
Phase 0: RiskManager (8h) ← CRITICAL - blocks order validation
  ↓
Phase 1: MEXC Adapter (12h) ← CRITICAL - blocks order submission
  ↓
Phase 1: LiveOrderManager (16h) ← CRITICAL - blocks live trading
  ↓
Phase 1: PositionSyncService (12h) ← CRITICAL - blocks position monitoring
  ↓
Phase 1: Strategy Integration (8h) ← CRITICAL - blocks signal → order flow
  ↓
Phase 1: EventBridge (8h) ← CRITICAL - blocks UI updates
  ↓
MILESTONE 1: Paper Trading Ready (92h total)
  ↓
Phase 2: Unit Tests (16h) ← CRITICAL - required for confidence
  ↓
Phase 2: Integration Tests (12h) ← CRITICAL - required for confidence
  ↓
Phase 3: Prometheus Metrics (8h) ← CRITICAL - required for monitoring
  ↓
Phase 3: Grafana Dashboards (8h) ← CRITICAL - required for visibility
  ↓
Phase 3: Alertmanager (4h) ← CRITICAL - required for risk management
  ↓
MILESTONE 2: Live Trading $100 Ready (156h total)
  ↓
Phase 4: TradingChart (6h) ← CRITICAL - required for monitoring
  ↓
Phase 4: PositionMonitor (4h) ← CRITICAL - required for liquidation prevention
  ↓
Phase 4: RiskAlerts (2h) ← CRITICAL - required for safety
  ↓
Phase 4: WebSocket Integration (8h) ← CRITICAL - required for real-time
  ↓
Phase 5: Docker (4h) ← CRITICAL - required for deployment
  ↓
Phase 5: Blue-Green Deployment (4h) ← CRITICAL - required for rollback
  ↓
MILESTONE 3: Live Trading Full Capital Ready (205h total)
  ↓
END
```

### Non-Critical Path (Can be Parallelized)

```
Phase 0: Health Checks (4h) - can be done anytime before Phase 3
Phase 1: REST API Endpoints (4h) - can be done after Phase 1.1-1.5
Phase 2: E2E Tests (8h) - can be done in parallel with Phase 3
Phase 2: Performance Tests (4h) - can be done in parallel with Phase 3
Phase 3: Log Aggregation (4h) - can be done in parallel with Phase 4
Phase 4: OrderHistory (3h) - can be done in parallel with other UI components
Phase 4: SignalLog (3h) - can be done in parallel with other UI components
Phase 4: PerformanceDashboard (3h) - can be done after Phase 4 main components
Phase 5: Rollback Script (4h) - can be done in parallel with deployment testing
Phase 5: Migration Rollback (4h) - can be done after Phase 5.1-5.2
```

### Fastest Possible Timeline (with parallelization)

**Optimistic:** ~180h (4.5 weeks) if:
- 2 engineers working in parallel
- No major blockers
- All tests pass on first attempt

**Realistic:** ~205h (5-6 weeks) with:
- 1 engineer
- Some debugging time
- Test failures requiring fixes

---

## Part IX: Milestone Definitions

### Milestone 1: Paper Trading Ready (92h)

**Achieved After:** Phase 0 + Phase 1

**Capabilities:**
- ✅ Paper trading works (simulated fills)
- ✅ Strategy generates signals
- ✅ Orders submitted and tracked
- ✅ Positions synced
- ✅ Risk validation active
- ✅ Circuit breaker protects against failures

**Limitations:**
- ❌ No monitoring (Grafana/alerts)
- ❌ No complete UI (basic only)
- ❌ No deployment automation
- ❌ Test coverage ~40%

**Use Case:** Internal testing with paper trading only. NOT production-ready.

---

### Milestone 2: Live Trading $100 Ready (156h)

**Achieved After:** Phase 0-3 (M1 + Phase 2 + Phase 3)

**Capabilities:**
- ✅ All M1 capabilities
- ✅ 80% test coverage
- ✅ Full monitoring (Prometheus + Grafana)
- ✅ Alerting (Alertmanager + PagerDuty)
- ✅ Performance validated (1000 ticks/sec, 5 concurrent sessions)
- ✅ Memory leak prevention verified

**Limitations:**
- ❌ UI incomplete (TradingChart, PositionMonitor missing)
- ❌ No production deployment
- ❌ Manual deployment only

**Use Case:** Live trading with limited capital ($100) to validate real exchange integration. Manual monitoring via Grafana required.

**Go/No-Go Criteria:**
```
✓ 7-day paper trading successful (no crashes)
✓ All 7 Alertmanager rules working
✓ Grafana dashboards displaying real data
✓ 80% test coverage maintained
✓ Memory growth < 10% over 1 hour test
✓ Circuit breaker tested (simulated MEXC downtime)
```

---

### Milestone 3: Live Trading Full Capital Ready (205h)

**Achieved After:** Phase 0-5 (M2 + Phase 4 + Phase 5)

**Capabilities:**
- ✅ All M2 capabilities
- ✅ Complete UI (TradingChart, PositionMonitor, OrderHistory, SignalLog, RiskAlerts)
- ✅ Real-time WebSocket updates
- ✅ InlineEdit + useSmartDefaults from PR #152
- ✅ Production deployment (Docker + Blue-Green)
- ✅ Rollback capability

**Limitations:**
- None for pump & dump trading use case

**Use Case:** Full production live trading with entire capital. Complete monitoring and UI for 24/7 operation.

**Go/No-Go Criteria:**
```
✓ All M2 Go/No-Go criteria met
✓ 30-day live trading with $100 successful
  - No liquidations
  - No missed signals due to system failure
  - < 5 critical alerts per day
✓ Blue-green deployment tested successfully
✓ Rollback tested successfully
✓ All UI components functional (E2E tests pass)
✓ TradingChart displays signals in real-time (< 1s delay)
✓ PositionMonitor shows margin ratio correctly
✓ RiskAlerts sound plays for critical alerts
✓ 100 WebSocket clients tested (< 1s broadcast time)
```

---

## Part X: Go/No-Go Decision Checklists

### Go/No-Go for M1 → M2 (Paper Trading → Live $100)

**STOP if ANY of these are NO:**

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 7-day paper trading session completed without crashes | ☐ | Logs show continuous uptime |
| All Phase 0-1 unit tests pass | ☐ | pytest --cov report shows 80% |
| EventBus handles 1000 ticks/sec without dropped messages | ☐ | Performance test passes |
| Circuit breaker opens after 5 MEXC failures | ☐ | Integration test passes |
| RiskManager blocks orders exceeding budget | ☐ | Unit test passes |
| LiveOrderManager submits orders to MEXC testnet | ☐ | Integration test passes |
| PositionSyncService detects liquidation | ☐ | Unit test passes (mock) |
| No memory leaks (< 10% growth over 1h) | ☐ | Performance test passes |

**GO Decision:** If all ☑, proceed to Phase 2-3 (Testing + Monitoring)

---

### Go/No-Go for M2 → M3 (Live $100 → Live Full Capital)

**STOP if ANY of these are NO:**

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 30 consecutive days live trading with $100 | ☐ | Trade log shows continuity |
| Zero liquidations during 30-day period | ☐ | Position history verified |
| Zero missed signals due to system failure | ☐ | Signal log vs. backtest comparison |
| < 5 critical alerts per day (average) | ☐ | Grafana alert history |
| All 7 Alertmanager rules triggered correctly in tests | ☐ | Test reports |
| Blue-green deployment tested 3 times successfully | ☐ | Deployment logs |
| Rollback tested 2 times successfully | ☐ | Rollback logs |
| All E2E UI tests pass | ☐ | Playwright test report |
| TradingChart displays signals with < 1s delay | ☐ | WebSocket latency test |
| PositionMonitor margin ratio accuracy verified | ☐ | Cross-check with MEXC API |
| RiskAlerts sound plays for all critical alerts | ☐ | E2E test passes |
| 100 WebSocket clients broadcast < 1s | ☐ | Performance test passes |
| Total system uptime > 99.5% during 30-day period | ☐ | Calculate from logs |

**GO Decision:** If all ☑, proceed to full capital live trading

---

## Part XI: Risk Mitigation Strategies

### Risk #1: MEXC API Downtime (Probability: High, Impact: Critical)

**Mitigation:**
- Circuit breaker opens after 5 failures → stops trading
- Alertmanager notifies via PagerDuty immediately
- Grafana dashboard shows circuit breaker state
- Manual intervention required: check MEXC status page

**Testing:** Simulate downtime by blocking MEXC API endpoint

---

### Risk #2: Position Liquidation (Probability: Medium, Impact: Critical)

**Mitigation:**
- PositionSyncService checks margin ratio every 10s
- RiskAlert emitted when margin < 15%
- Sound notification in UI
- Automatic position close if margin < 10% (add in Phase 1 if desired)

**Testing:** Simulate high volatility with price swings

---

### Risk #3: WebSocket Disconnect (Probability: High, Impact: High)

**Mitigation:**
- Auto-reconnect with exponential backoff
- Heartbeat every 30s
- EventBridge continues operating (backend keeps state)
- UI shows "Disconnected" banner

**Testing:** Simulate network loss by blocking WebSocket port

---

### Risk #4: Memory Leak (Probability: Low, Impact: High)

**Mitigation:**
- NO defaultdict in long-lived structures
- Explicit cache cleanup (order queue, positions)
- Memory monitoring via Prometheus
- Alert if memory growth > 10% over 1h

**Testing:** 1-hour load test with memory profiling

---

### Risk #5: Deployment Failure (Probability: Medium, Impact: High)

**Mitigation:**
- Blue-green deployment (zero downtime)
- Health checks before switch (10 retries, 5s interval)
- Rollback script ready
- Nginx switches only after health checks pass

**Testing:** Test deployment 3 times, rollback 2 times

---

## Part XII: Final Timeline Summary

```
Phase 0: Infrastructure Foundation      32h  (Week 1)
Phase 1: Core Live Trading              60h  (Week 2-3)
Phase 2: Testing & Quality Assurance    40h  (Week 4)
Phase 3: Monitoring & Observability     24h  (Week 5)
Phase 4: Frontend UI                    33h  (Week 5-6)
Phase 5: Deployment & Infrastructure    16h  (Week 6)
───────────────────────────────────────────
TOTAL:                                 205h  (5-6 weeks)

Milestones:
M1: Paper Trading Ready         @  92h (Week 2)
M2: Live $100 Ready            @ 156h (Week 4)
M3: Live Full Capital Ready    @ 205h (Week 6)
```

---

## Conclusion

This roadmap provides a **complete, step-by-step path** from 30% to 100% production readiness for live cryptocurrency trading focused on pump & dump strategies.

**Key Strengths:**
1. **Coherent Architecture:** EventBus-driven design with proven patterns (Circuit Breaker, State Machine, Position Sync)
2. **Risk-First Approach:** RiskManager, margin monitoring, circuit breaker, and multiple safety layers
3. **Evidence-Based:** All gaps identified with solutions, overengineering removed (-3h)
4. **Milestone-Driven:** Clear Go/No-Go criteria at each stage
5. **Production-Ready:** Blue-green deployment, rollback, monitoring, and 80% test coverage

**Critical Success Factors:**
- Follow critical path (EventBus → LiveOrderManager → PositionSync → Testing → Monitoring)
- Achieve M1 Go/No-Go before proceeding to M2
- Achieve M2 Go/No-Go (30-day $100 live) before full capital
- Never skip testing phases (40h) - they prevent catastrophic failures

**Next Steps:**
1. Start Phase 0 (EventBus implementation)
2. Track progress with todos (this document)
3. Review M1 Go/No-Go checklist after Phase 1
4. Deploy to production only after M3 Go/No-Go checklist is 100% ☑

---

**Document Status:** COMPLETE
**Total Lines:** ~4,800
**Estimated Reading Time:** 90 minutes
**Target Audience:** Senior Engineer, Project Manager, Stakeholders