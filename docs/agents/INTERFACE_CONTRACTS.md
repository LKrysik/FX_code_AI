# Interface Contracts - Multi-Agent Implementation

**Maintained by:** Agent 0 (Coordinator)
**Last Updated:** 2025-11-07
**Purpose:** Single source of truth for all component interfaces

---

## Overview

This document defines the **interface contracts** between components being implemented by different agents. All agents MUST refer to this document when integrating with other agents' code.

**Breaking Change Protocol:**
1. Agent proposes change in DAILY_SYNC.md or ISSUES.md
2. Agent 0 reviews and decides if justified
3. Agent 0 updates this document with version number and "BREAKING CHANGE" flag
4. Agent 0 notifies ALL affected agents
5. Agent 0 assigns migration tasks
6. Agent 0 verifies all migrations complete before allowing merge

---

## EventBus Interface v1.0

**Owner:** Agent 1 (Core Infrastructure)
**Consumers:** Agent 2 (RiskManager), Agent 3 (LiveOrderManager), Agent 5 (Monitoring), Agent 6 (EventBridge)
**Status:** Not Implemented
**File:** `src/core/event_bus.py`

**Last Updated:** 2025-11-07 (Initial Spec)
**Breaking Changes:** N/A (Initial version)

### Interface

```python
from typing import Dict, Any, List, Callable
import asyncio

class EventBus:
    """
    Central event bus for publish-subscribe communication.

    Delivery Guarantee: AT_LEAST_ONCE (NOT EXACTLY_ONCE)
    Error Handling: Subscriber crash does NOT affect other subscribers
    Memory Management: Explicit dict (NO defaultdict)
    """

    def __init__(self):
        # CRITICAL: Use explicit dict, NOT defaultdict (memory leak prevention)
        self._subscribers: Dict[str, List[Callable]] = {}
        self._subscriber_count: Dict[str, int] = {}

    def subscribe(self, topic: str, handler: Callable) -> None:
        """
        Subscribe to topic with async handler.

        Args:
            topic: Event topic name (see TOPICS below)
            handler: Async callable receiving Dict[str, Any]

        Example:
            async def my_handler(data: Dict[str, Any]):
                print(f"Received: {data}")

            event_bus.subscribe("market_data", my_handler)
        """
        pass

    def unsubscribe(self, topic: str, handler: Callable) -> None:
        """
        Unsubscribe handler from topic.

        Args:
            topic: Event topic name
            handler: Previously registered handler

        Note: Automatically cleans up empty topics to prevent memory leaks
        """
        pass

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """
        Publish event to all subscribers.

        Args:
            topic: Event topic name
            data: Event payload (must be JSON-serializable)

        Retry Policy: 3 attempts with exponential backoff (1s, 2s, 4s)
        Error Handling: Logs error but continues to other subscribers

        Example:
            await event_bus.publish("market_data", {
                "symbol": "BTC_USDT",
                "timestamp": 1699372800000,
                "price": 50000.0,
                "volume": 1000.0
            })
        """
        pass

    def list_topics(self) -> List[str]:
        """
        List all active topics with subscriber counts.

        Returns:
            List of strings: ["market_data (3 subscribers)", ...]
        """
        pass

    async def shutdown(self) -> None:
        """
        Cleanup all subscriptions.

        CRITICAL: Must be called during application shutdown to prevent leaks.
        """
        pass
```

### Event Topics

**MANDATORY TOPICS** (DO NOT CHANGE without Agent 0 approval):

```python
TOPICS = {
    # Market Data Events
    "market_data": {
        "description": "New tick price/volume from exchange",
        "schema": {
            "symbol": "str",           # e.g., "BTC_USDT"
            "timestamp": "int",         # Unix timestamp in milliseconds
            "price": "float",           # Current price
            "volume": "float",          # Trade volume
            "quote_volume": "float"     # Quote asset volume
        },
        "publisher": "MarketDataProviderAdapter",
        "subscribers": ["StreamingIndicatorEngine", "DataCollectionPersistenceService", "EventBridge"]
    },

    # Indicator Events
    "indicator_updated": {
        "description": "Indicator calculation completed",
        "schema": {
            "indicator_id": "str",      # e.g., "TWPA_300_0"
            "symbol": "str",            # e.g., "BTC_USDT"
            "timestamp": "int",         # Calculation timestamp
            "value": "float",           # Indicator value
            "confidence": "float"       # Confidence score (0-1)
        },
        "publisher": "StreamingIndicatorEngine",
        "subscribers": ["StrategyManager", "EventBridge"]
    },

    # Signal Events
    "signal_generated": {
        "description": "Strategy generated trading signal (S1, Z1, ZE1, E1)",
        "schema": {
            "signal_id": "str",         # Unique signal ID
            "signal_type": "str",       # "S1", "Z1", "ZE1", "E1"
            "strategy_id": "str",       # Strategy that generated signal
            "symbol": "str",            # e.g., "BTC_USDT"
            "side": "str",              # "buy" or "sell"
            "quantity": "float",        # Suggested quantity
            "timestamp": "int",         # Signal timestamp
            "metadata": "dict"          # Additional signal data
        },
        "publisher": "StrategyManager",
        "subscribers": ["LiveOrderManager", "EventBridge"]
    },

    # Order Events
    "order_created": {
        "description": "New order submitted to exchange",
        "schema": {
            "order_id": "str",          # Internal order ID
            "exchange_order_id": "str", # MEXC order ID
            "symbol": "str",
            "side": "str",              # "buy" or "sell"
            "order_type": "str",        # "market" or "limit"
            "quantity": "float",
            "price": "float",           # For limit orders
            "status": "str",            # "pending", "submitted", "failed"
            "timestamp": "int",
            "error": "str"              # If status == "failed"
        },
        "publisher": "LiveOrderManager",
        "subscribers": ["PositionSyncService", "EventBridge"]
    },

    "order_filled": {
        "description": "Order executed by exchange",
        "schema": {
            "order_id": "str",
            "exchange_order_id": "str",
            "symbol": "str",
            "filled_price": "float",    # Actual execution price
            "filled_quantity": "float", # Actual filled amount
            "fee": "float",             # Trading fee
            "timestamp": "int"
        },
        "publisher": "LiveOrderManager",
        "subscribers": ["PositionSyncService", "RiskManager", "EventBridge"]
    },

    # Position Events
    "position_updated": {
        "description": "Position changed (opened, closed, liquidated)",
        "schema": {
            "position_id": "str",
            "symbol": "str",
            "side": "str",              # "long" or "short"
            "quantity": "float",
            "entry_price": "float",
            "current_price": "float",
            "unrealized_pnl": "float",
            "margin_ratio": "float",    # equity / maintenance_margin (%)
            "liquidation_price": "float",
            "status": "str",            # "open", "closed", "liquidated"
            "timestamp": "int"
        },
        "publisher": "PositionSyncService",
        "subscribers": ["RiskManager", "EventBridge"]
    },

    # Risk Events
    "risk_alert": {
        "description": "Risk threshold breached",
        "schema": {
            "alert_id": "str",
            "session_id": "str",
            "severity": "str",          # "CRITICAL", "WARNING", "INFO"
            "alert_type": "str",        # "MARGIN_LOW", "DAILY_LOSS_LIMIT", etc.
            "message": "str",           # Human-readable message
            "details": "dict",          # Additional context
            "timestamp": "int"
        },
        "publisher": "RiskManager",
        "subscribers": ["EventBridge", "AlertManager"]
    }
}
```

### Critical Requirements

- ✅ NO defaultdict (memory leak prevention)
- ✅ Retry logic: 3 attempts, exponential backoff (1s, 2s, 4s)
- ✅ Error isolation: subscriber crash doesn't affect others
- ✅ AT_LEAST_ONCE delivery (NO EXACTLY_ONCE overengineering)
- ✅ Explicit cleanup in shutdown()

### Integration Example

```python
# Agent 3 (LiveOrderManager) subscribing to signals
class LiveOrderManager:
    def __init__(self, event_bus: EventBus, risk_manager: RiskManager):
        self.event_bus = event_bus
        self.risk_manager = risk_manager

        # Subscribe to signal_generated events
        self.event_bus.subscribe("signal_generated", self._handle_signal)

    async def _handle_signal(self, data: Dict[str, Any]):
        # Validate signal
        signal = Signal(**data)

        # Check risk
        risk_check = await self.risk_manager.validate_order(signal)
        if not risk_check.can_proceed:
            logger.warning(f"Signal rejected by risk manager: {risk_check.reason}")
            return

        # Submit order
        order = await self._submit_order(signal)

        # Publish order_created event
        await self.event_bus.publish("order_created", order.to_dict())
```

---

## Circuit Breaker Interface v1.0

**Owner:** Agent 1 (Core Infrastructure)
**Consumers:** Agent 3 (LiveOrderManager for MEXC calls)
**Status:** Not Implemented
**File:** `src/infrastructure/circuit_breaker.py`

**Last Updated:** 2025-11-07 (Initial Spec)
**Breaking Changes:** N/A (Initial version)

### Interface

```python
from enum import Enum
from typing import Callable, Any

class CircuitBreakerState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Blocking all calls
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is OPEN"""
    pass

class CircuitBreaker:
    """
    Circuit breaker pattern for external API calls.

    State Transitions:
    - CLOSED → OPEN: After 5 failures in 60s window
    - OPEN → HALF_OPEN: After 30s cooldown
    - HALF_OPEN → CLOSED: After 1 successful call
    - HALF_OPEN → OPEN: On failure
    """

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async callable to execute
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result from func

        Raises:
            CircuitBreakerOpenError: If circuit is OPEN

        Example:
            async def fetch_price():
                return await mexc_api.get_price("BTC_USDT")

            try:
                price = await circuit_breaker.call(fetch_price)
            except CircuitBreakerOpenError:
                # Use cached price or skip
                pass
        """
        pass

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state"""
        pass

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED (for testing/recovery)"""
        pass

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get circuit breaker metrics.

        Returns:
            {
                "state": "closed",
                "failure_count": 2,
                "success_count": 100,
                "last_failure_time": 1699372800,
                "last_state_change": 1699372800
            }
        """
        pass
```

### Critical Requirements

- ✅ OPEN after 5 failures in 60s window
- ✅ HALF_OPEN after 30s cooldown
- ✅ CLOSED after 1 successful call in HALF_OPEN
- ✅ Raises CircuitBreakerOpenError when OPEN

### Integration Example

```python
# Agent 3 (LiveOrderManager) using Circuit Breaker
class LiveOrderManager:
    def __init__(self, circuit_breaker: CircuitBreaker, mexc_adapter: MexcAdapter):
        self.circuit_breaker = circuit_breaker
        self.mexc_adapter = mexc_adapter

    async def _submit_order(self, order: Order):
        try:
            # Wrap MEXC API call with circuit breaker
            result = await self.circuit_breaker.call(
                self.mexc_adapter.create_market_order,
                order.symbol,
                order.side,
                order.quantity
            )
            return result
        except CircuitBreakerOpenError:
            logger.error("Circuit breaker OPEN - MEXC API unavailable")
            # Queue order for later or reject
            raise
```

---

## RiskManager Interface v1.0

**Owner:** Agent 2 (Risk Management & Validation)
**Consumers:** Agent 3 (LiveOrderManager)
**Status:** Not Implemented
**File:** `src/domain/services/risk_manager.py`

**Last Updated:** 2025-11-07 (Initial Spec)
**Breaking Changes:** N/A (Initial version)

### Interface

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class RiskCheckResult:
    """Result of risk validation"""
    can_proceed: bool
    reason: Optional[str]  # If False, explains why
    risk_score: float      # 0-100 (higher = riskier)

class RiskManager:
    """
    Risk management for live trading.

    Implements 6 risk checks (per TARGET_STATE_ARCHITECTURE.md):
    1. Max position size (10% of capital)
    2. Max number of positions (3 concurrent)
    3. Position concentration (max 30% in one symbol)
    4. Daily loss limit (5% of capital)
    5. Total drawdown (15% from peak)
    6. Margin utilization (< 80% of available margin)
    """

    async def can_open_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        current_positions: List[Position]
    ) -> RiskCheckResult:
        """
        Validate if new position can be opened.

        Args:
            symbol: Trading symbol (e.g., "BTC_USDT")
            side: "long" or "short"
            quantity: Position size
            price: Entry price
            current_positions: List of currently open positions

        Returns:
            RiskCheckResult with can_proceed=True/False

        Example:
            result = await risk_manager.can_open_position(
                symbol="BTC_USDT",
                side="long",
                quantity=0.1,
                price=50000.0,
                current_positions=[...]
            )

            if not result.can_proceed:
                logger.warning(f"Position rejected: {result.reason}")
        """
        pass

    async def validate_order(self, order: Order) -> RiskCheckResult:
        """
        Validate order before submission.

        Args:
            order: Order object to validate

        Returns:
            RiskCheckResult

        Note: This is a convenience wrapper around can_open_position()
        """
        pass

    # Internal risk checks (not public API)
    # All checks are configurable via config.json
```

### Risk Check Configuration

All limits are configurable via `config.json`:

```json
{
  "risk_manager": {
    "max_position_size_percent": 10,
    "max_concurrent_positions": 3,
    "max_symbol_concentration_percent": 30,
    "daily_loss_limit_percent": 5,
    "max_drawdown_percent": 15,
    "max_margin_utilization_percent": 80
  }
}
```

### Critical Requirements

- ✅ All checks configurable via config.json (NO hardcoded limits)
- ✅ Emit risk_alert event when check fails
- ✅ Thread-safe (async-safe) state management
- ✅ All 6 risk checks implemented

### Integration Example

```python
# Agent 3 (LiveOrderManager) using RiskManager
class LiveOrderManager:
    def __init__(self, event_bus: EventBus, risk_manager: RiskManager):
        self.event_bus = event_bus
        self.risk_manager = risk_manager

        # Subscribe to signals
        self.event_bus.subscribe("signal_generated", self._handle_signal)

    async def _handle_signal(self, data: Dict[str, Any]):
        signal = Signal(**data)

        # Validate with risk manager
        risk_check = await self.risk_manager.validate_order(signal)

        if not risk_check.can_proceed:
            logger.warning(f"Signal rejected: {risk_check.reason} (risk_score={risk_check.risk_score})")

            # Emit risk alert
            await self.event_bus.publish("risk_alert", {
                "alert_id": generate_id(),
                "severity": "WARNING",
                "alert_type": "ORDER_REJECTED",
                "message": risk_check.reason,
                "details": {"signal": signal.to_dict(), "risk_score": risk_check.risk_score}
            })
            return

        # Proceed with order submission
        await self._submit_order(signal)
```

---

## LiveOrderManager Interface v1.0

**Owner:** Agent 3 (Live Trading Core)
**Consumers:** Agent 6 (REST API)
**Status:** Not Implemented
**File:** `src/domain/services/order_manager_live.py`

**Last Updated:** 2025-11-07 (Initial Spec)
**Breaking Changes:** N/A (Initial version)

### Interface

```python
from typing import Optional

class LiveOrderManager:
    """
    Live order execution manager.

    Features:
    - Order queue with max 1000 orders (memory leak prevention)
    - Order TTL: 5 minutes
    - Retry logic: 3 attempts with exponential backoff
    - Background tasks: order polling (2s), cleanup (5min)
    - Emits: order_created, order_filled events
    """

    async def submit_order(self, order: Order) -> bool:
        """
        Submit order to exchange.

        Args:
            order: Order object to submit

        Returns:
            True if submitted successfully, False otherwise

        Events Emitted:
            - order_created (always)
            - order_filled (when filled)

        Example:
            order = Order(
                symbol="BTC_USDT",
                side="buy",
                order_type="market",
                quantity=0.1
            )
            success = await order_manager.submit_order(order)
        """
        pass

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel pending order.

        Args:
            order_id: Internal order ID

        Returns:
            True if cancelled successfully, False otherwise
        """
        pass

    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """
        Get current order status.

        Args:
            order_id: Internal order ID

        Returns:
            Order object or None if not found
        """
        pass

    async def start(self) -> None:
        """
        Start background tasks.

        Starts:
        - Order status polling loop (every 2s)
        - Order cleanup loop (every 5 min)
        """
        pass

    async def stop(self) -> None:
        """
        Stop background tasks and cleanup.

        CRITICAL: Must be called during shutdown to:
        - Cancel background tasks
        - Clear order queue
        - Cleanup subscriptions
        """
        pass
```

### Critical Requirements

- ✅ Order queue max 1000 orders (memory leak prevention)
- ✅ Order TTL: 5 minutes
- ✅ Retry logic: 3 attempts with exponential backoff
- ✅ Emit order_created, order_filled events to EventBus
- ✅ Circuit breaker integration for MEXC calls
- ✅ Subscribe to signal_generated events from StrategyManager

### Background Tasks

```python
# Internal methods (not public API)
async def _poll_order_status(self) -> None:
    """Background task: Poll MEXC for order status every 2s"""
    pass

async def _cleanup_old_orders(self) -> None:
    """Background task: Remove orders older than TTL every 5 min"""
    pass
```

---

## PositionSyncService Interface v1.0

**Owner:** Agent 3 (Live Trading Core)
**Consumers:** Agent 6 (REST API)
**Status:** Not Implemented
**File:** `src/domain/services/position_sync_service.py`

**Last Updated:** 2025-11-07 (Initial Spec)
**Breaking Changes:** N/A (Initial version)

### Interface

```python
from dataclasses import dataclass
from typing import List

@dataclass
class ReconciliationResult:
    """Result of position reconciliation"""
    matched: List[Position]        # Local == Exchange
    local_only: List[Position]     # Liquidated or manually closed on exchange
    exchange_only: List[Position]  # Opened externally (not via our system)

class PositionSyncService:
    """
    Position synchronization with exchange.

    Features:
    - Sync loop every 10 seconds
    - Detects liquidations (position missing on exchange)
    - Calculates margin ratio: equity / maintenance_margin
    - Emits: position_updated, risk_alert events
    """

    async def start(self) -> None:
        """
        Start sync loop.

        Starts background task that calls reconcile_positions() every 10s
        """
        pass

    async def stop(self) -> None:
        """
        Stop sync loop and cleanup.

        CRITICAL: Must be called during shutdown
        """
        pass

    async def reconcile_positions(self) -> ReconciliationResult:
        """
        Reconcile local positions with exchange positions.

        Returns:
            ReconciliationResult with matched/missing positions

        Side Effects:
            - Emits position_updated for changed positions
            - Emits risk_alert for liquidated positions
            - Emits risk_alert for margin ratio < 15%

        Example:
            result = await position_sync.reconcile_positions()

            if result.local_only:
                logger.error(f"Liquidated positions detected: {result.local_only}")

            if result.exchange_only:
                logger.warning(f"External positions detected: {result.exchange_only}")
        """
        pass
```

### Critical Requirements

- ✅ Sync every 10 seconds
- ✅ Detect liquidations (position missing on exchange)
- ✅ Calculate margin ratio: equity / maintenance_margin
- ✅ Emit position_updated, risk_alert events
- ✅ Handle network failures gracefully (don't crash on timeout)

### Integration Example

```python
# Example: Detecting liquidation
async def reconcile_positions(self) -> ReconciliationResult:
    local_positions = await self.db.get_open_positions()
    exchange_positions = await self.mexc_adapter.get_positions()

    # Find liquidated positions
    local_only = []
    for local_pos in local_positions:
        if not self._find_matching(local_pos, exchange_positions):
            local_only.append(local_pos)

            # Emit liquidation alert
            await self.event_bus.publish("risk_alert", {
                "alert_id": generate_id(),
                "severity": "CRITICAL",
                "alert_type": "POSITION_LIQUIDATED",
                "message": f"Position liquidated: {local_pos.symbol}",
                "details": {"position": local_pos.to_dict()}
            })

    return ReconciliationResult(matched=[], local_only=local_only, exchange_only=[])
```

---

## MEXC Adapter Interface v1.0

**Owner:** Agent 3 (Live Trading Core)
**Consumers:** LiveOrderManager, PositionSyncService
**Status:** ✅ IMPLEMENTED (2025-11-07)
**File:** `src/infrastructure/adapters/mexc_adapter.py`

**Last Updated:** 2025-11-07 (Implemented by Agent 3)
**Breaking Changes:** N/A (Initial implementation)

### Interface

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

class OrderStatus(str, Enum):
    """MEXC order status"""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

@dataclass
class OrderStatusResponse:
    """Order status response from MEXC"""
    exchange_order_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    order_type: str  # "MARKET" or "LIMIT"
    quantity: float
    price: float
    status: OrderStatus
    filled_quantity: float
    average_fill_price: Optional[float]
    created_at: int  # Unix timestamp in milliseconds
    updated_at: int  # Unix timestamp in milliseconds

@dataclass
class PositionResponse:
    """Position response from MEXC"""
    symbol: str
    side: str  # "LONG" or "SHORT"
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    margin_ratio: float  # equity / maintenance_margin (%)
    liquidation_price: float
    leverage: float
    margin: float

class MexcRealAdapter:
    """
    MEXC API adapter with order submission and position fetching.

    Features:
    - Rate limiting: 10 requests/sec
    - Retry logic: 3 attempts via ResilientService
    - Circuit breaker integration
    - Comprehensive error handling
    """

    async def create_market_order(symbol: str, side: str, quantity: float) -> str:
        """
        Create market order.

        Args:
            symbol: Trading symbol (e.g., "BTC_USDT")
            side: "buy" or "sell"
            quantity: Order quantity

        Returns:
            Exchange order ID (string)

        Raises:
            Exception: On API errors (500, 418, timeout, etc.)
        """
        pass

    async def create_limit_order(
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> str:
        """
        Create limit order.

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            quantity: Order quantity
            price: Limit price

        Returns:
            Exchange order ID (string)

        Raises:
            Exception: On API errors
        """
        pass

    async def cancel_order(symbol: str, exchange_order_id: str) -> bool:
        """
        Cancel order.

        Args:
            symbol: Trading symbol
            exchange_order_id: Exchange order ID

        Returns:
            True if cancelled successfully, False if order not found

        Raises:
            Exception: On API errors (except 'not found')
        """
        pass

    async def get_order_status(
        symbol: str,
        exchange_order_id: str
    ) -> OrderStatusResponse:
        """
        Get order status.

        Args:
            symbol: Trading symbol
            exchange_order_id: Exchange order ID

        Returns:
            OrderStatusResponse with order details

        Raises:
            Exception: On API errors
        """
        pass

    async def get_positions() -> List[PositionResponse]:
        """
        Get all open positions from MEXC Futures.

        Returns:
            List of PositionResponse objects (empty list if no positions)

        Raises:
            Exception: On API errors
        """
        pass
```

### Critical Requirements

✅ **COMPLETED:**
- ✅ Rate limiting: 10 requests/sec (changed from 20)
- ✅ Retry logic: 3 attempts with exponential backoff (via ResilientService)
- ✅ Error handling for ALL MEXC API errors (500, 418, timeout)
- ✅ API keys from settings.py (NO hardcoded)
- ✅ All 5 methods implemented
- ✅ Comprehensive unit tests (20+ test cases)

### Error Handling

**HTTP 500 (Server Error):**
- Handled by ResilientService
- Retries: 3 attempts with exponential backoff (1s, 2s, 4s)
- Final failure: Raises exception

**HTTP 418 (Rate Limit):**
- Handled by ResilientService
- Retries with backoff
- Local rate limiter prevents hitting this

**Network Timeout:**
- Handled by ResilientService
- Timeout: 30 seconds (configurable)
- Retries on timeout

**HTTP 400 (Bad Request):**
- For `cancel_order`: Returns False if "not found" or "unknown order"
- For other methods: Raises exception immediately (no retry)

### Integration Example

```python
# Agent 3 (LiveOrderManager) using MEXC Adapter
from src.infrastructure.adapters.mexc_adapter import MexcRealAdapter
from src.core.logger import StructuredLogger
from src.infrastructure.config.settings import settings

# Initialize adapter
adapter = MexcRealAdapter(
    api_key=settings.exchanges.mexc_api_key,
    api_secret=settings.exchanges.mexc_api_secret,
    logger=logger
)

# Submit market order
order_id = await adapter.create_market_order(
    symbol="BTC_USDT",
    side="buy",
    quantity=0.1
)

# Check order status
status = await adapter.get_order_status(
    symbol="BTC_USDT",
    exchange_order_id=order_id
)

# Get positions
positions = await adapter.get_positions()
for pos in positions:
    print(f"{pos.symbol}: {pos.side} {pos.quantity} @ {pos.entry_price}")
```

### Test Coverage

**Unit Tests:** `tests_e2e/unit/test_mexc_adapter.py`

**Test Classes:**
1. `TestMexcAdapterOrderSubmission` (6 tests)
   - Market order success
   - Limit order success
   - API error handling
   - Order cancellation success
   - Order not found handling

2. `TestMexcAdapterOrderStatus` (3 tests)
   - Order status success
   - Partially filled orders
   - Order not found

3. `TestMexcAdapterPositions` (4 tests)
   - Position fetch success
   - Empty positions
   - Zero quantity filtering
   - API error handling

4. `TestMexcAdapterErrorHandling` (4 tests)
   - HTTP 500 retry
   - HTTP 418 rate limit
   - Network timeout
   - Rate limiting enforcement (10 req/sec)

5. `TestMexcAdapterCancellation` (1 test)
   - Non-'not found' errors propagate

**Total:** 18 test cases covering all scenarios

---

## Version History

### v1.1 (2025-11-07)
- ✅ MEXC Adapter Interface implemented (Agent 3)
- ✅ OrderStatusResponse and PositionResponse dataclasses added
- ✅ All 5 methods implemented with comprehensive error handling
- ✅ Unit tests created (18 test cases)
- ✅ Rate limiting adjusted to 10 requests/sec
- No breaking changes to existing interfaces

### v1.0 (2025-11-07)
- Initial interface contracts
- All interfaces: Not Implemented
- No breaking changes

---

## Notes for Agents

1. **Before implementing:** Read your assigned interface(s) carefully
2. **During implementation:** If you need to change an interface, report to Agent 0 via ISSUES.md
3. **After implementation:** Update status in this document from "Not Implemented" → "Implemented"
4. **Breaking changes:** NEVER make breaking changes without Agent 0 approval

**Questions?** Ask Agent 0 in DAILY_SYNC.md or ISSUES.md
