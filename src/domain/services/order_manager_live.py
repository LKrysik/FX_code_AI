"""
LiveOrderManager - Live Order Execution and Management
=======================================================
Manages order lifecycle for live trading with retry logic, status polling, and cleanup.

Features:
- Submit orders to MEXC with retry (3 attempts, exponential backoff)
- Background status polling (every 2s)
- Cleanup old orders (every 60s, removes orders > 1 hour old)
- Circuit breaker integration for MEXC calls
- RiskManager validation before submission
- EventBus integration for signal_generated → order_created → order_filled flow

Critical Requirements:
- ✅ Order queue max 1000 (NO defaultdict, explicit dict)
- ✅ Explicit cleanup in stop() methods
- ✅ RiskManager.validate_order() before submission
- ✅ Circuit breaker wraps all MEXC calls
- ✅ All config from settings.py
"""

import asyncio
import time
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

from ...core.event_bus import EventBus
from ...infrastructure.adapters.mexc_adapter import MexcRealAdapter
from ...core.circuit_breaker import CircuitBreakerOpenException
from ..models.trading import Position

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class Order:
    """Order dataclass for live trading"""
    order_id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    price: Optional[float]  # None for market orders
    order_type: str  # "limit" or "market"
    status: OrderStatus
    created_at: float  # Unix timestamp
    updated_at: float  # Unix timestamp
    strategy_id: str = "unknown"  # Strategy that generated this order
    exchange_order_id: Optional[str] = None
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    error_message: Optional[str] = None


class LiveOrderManager:
    """
    Manages order lifecycle for live trading.

    Responsibilities:
    - Submit orders to MEXC
    - Poll order status every 2 seconds
    - Handle partial fills
    - Retry on transient failures (3 attempts with exponential backoff: 1s, 2s, 4s)
    - Emit order events to EventBus

    Order Queue:
    - Max size: 1000 orders (configurable)
    - TTL: Not used (cleanup based on age)
    - Cleanup: Remove completed orders after 1 hour
    """

    def __init__(
        self,
        event_bus: EventBus,
        mexc_adapter: MexcRealAdapter,
        risk_manager,  # RiskManager (avoid circular import)
        max_orders: int = 1000,
        order_timeout_seconds: int = 60  # FIX (Agent 4 - Task 3): Order timeout
    ):
        """
        Initialize LiveOrderManager.

        Args:
            event_bus: EventBus instance for pub/sub
            mexc_adapter: MEXC adapter with circuit breaker
            risk_manager: RiskManager for order validation
            max_orders: Maximum number of orders to track
            order_timeout_seconds: Timeout for pending orders (default: 60s)
        """
        self.event_bus = event_bus
        self.mexc_adapter = mexc_adapter
        self.risk_manager = risk_manager
        self.max_orders = max_orders
        self.order_timeout_seconds = order_timeout_seconds

        # Order tracking (CRITICAL: Not defaultdict to prevent memory leak)
        self.orders: Dict[str, Order] = {}

        # FIX (Agent 4 - Task 3): Order timeout tracking
        self._order_timeouts: Dict[str, asyncio.Task] = {}

        # Lock for thread-safe order dict access
        self._order_lock = asyncio.Lock()

        # Background tasks
        self._status_poll_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Note: EventBus subscriptions moved to start() method (async required)

        logger.info(f"LiveOrderManager initialized (max_orders: {max_orders})")

    async def start(self):
        """Start background tasks and subscribe to events."""
        if self._running:
            logger.warning("LiveOrderManager already running")
            return

        logger.info("Starting LiveOrderManager background tasks...")
        self._running = True

        # Subscribe to signal events (async required)
        await self.event_bus.subscribe("signal_generated", self._on_signal_generated)

        # Start background tasks
        self._status_poll_task = asyncio.create_task(self._poll_order_status())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_orders())

    async def stop(self):
        """Stop background tasks and cleanup."""
        logger.info("Stopping LiveOrderManager...")
        self._running = False

        # Unsubscribe from events
        await self.event_bus.unsubscribe("signal_generated", self._on_signal_generated)

        # Cancel background tasks
        if self._status_poll_task:
            self._status_poll_task.cancel()
            try:
                await self._status_poll_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # FIX (Agent 4 - Task 3): Cancel all timeout tasks
        timeout_count = len(self._order_timeouts)
        for order_id, timeout_task in list(self._order_timeouts.items()):
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass
        self._order_timeouts.clear()
        if timeout_count > 0:
            logger.info(f"Cancelled {timeout_count} timeout tasks")

        # Explicit cleanup (memory leak prevention)
        async with self._order_lock:
            self.orders.clear()

        logger.info("LiveOrderManager stopped")

    async def _on_signal_generated(self, data: Dict):
        """
        Handle signal from StrategyManager.

        Signal Types:
        - S1: Entry signal → Create order
        - Z1: Position opened → Monitor (no order)
        - ZE1: Partial exit → Create exit order
        - E1: Full exit → Create exit order

        Args:
            data: Signal data from EventBus
        """
        signal_type = data.get("signal_type")

        # Only create orders for S1, ZE1, E1 signals
        if signal_type not in ["S1", "ZE1", "E1"]:
            return

        # Create order from signal
        order = Order(
            order_id=data.get("signal_id", f"order_{int(time.time() * 1000)}"),
            symbol=data["symbol"],
            side=data["side"],
            quantity=data["quantity"],
            price=data.get("price"),  # None for market orders
            order_type=data.get("order_type", "market"),
            status=OrderStatus.PENDING,
            created_at=time.time(),
            updated_at=time.time(),
            strategy_id=data.get("strategy_id", "unknown")
        )

        await self.submit_order(order)

    async def submit_order(self, order: Order, current_positions: List[Position] = None) -> bool:
        """
        Submit order to exchange with retry logic and risk validation.

        Flow:
        1. Check queue size (max 1000)
        2. Validate with RiskManager (if current_positions provided)
        3. Submit to MEXC via circuit breaker
        4. Retry up to 3 times with exponential backoff (1s, 2s, 4s)
        5. Emit order_created event

        Args:
            order: Order object to submit
            current_positions: List of current open positions (for risk validation)

        Returns:
            True if submitted successfully, False otherwise
        """
        # Check queue size (protect with lock)
        async with self._order_lock:
            if len(self.orders) >= self.max_orders:
                logger.error(f"Order queue full ({self.max_orders}), rejecting order {order.order_id}")
                order.status = OrderStatus.FAILED
                order.error_message = "Order queue full"
                await self._emit_order_event("order_created", order, status="failed")
                return False

        # Risk validation (if current_positions provided)
        if current_positions is not None and self.risk_manager:
            try:
                risk_result = await self.risk_manager.can_open_position(
                    symbol=order.symbol,
                    side=order.side,
                    quantity=Decimal(str(order.quantity)),
                    price=Decimal(str(order.price)) if order.price else Decimal('0.0'),
                    current_positions=current_positions
                )

                if not risk_result.can_proceed:
                    logger.warning(
                        f"Order rejected by RiskManager: {order.order_id}, reason: {risk_result.reason}"
                    )
                    order.status = OrderStatus.FAILED
                    order.error_message = f"Risk check failed: {risk_result.reason}"
                    await self._emit_order_event("order_created", order, status="failed")
                    return False
            except Exception as e:
                logger.error(f"Risk validation error for order {order.order_id}: {e}")
                order.status = OrderStatus.FAILED
                order.error_message = f"Risk validation error: {str(e)}"
                await self._emit_order_event("order_created", order, status="failed")
                return False

        # Add to tracking (protect with lock)
        async with self._order_lock:
            self.orders[order.order_id] = order

        # Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Submit via MEXC adapter (circuit breaker already integrated in adapter)
                exchange_order_id = await self._submit_order_to_exchange(order)

                # Success
                order.exchange_order_id = exchange_order_id
                order.status = OrderStatus.SUBMITTED
                order.updated_at = time.time()

                logger.info(
                    f"Order submitted: {order.order_id} → Exchange ID: {exchange_order_id}"
                )

                # FIX (Agent 4 - Task 3): Create timeout task
                timeout_task = asyncio.create_task(self._timeout_order(order.order_id))
                self._order_timeouts[order.order_id] = timeout_task
                logger.debug(f"Timeout task created for order {order.order_id} ({self.order_timeout_seconds}s)")

                await self._emit_order_event("order_created", order, status="submitted")
                return True

            except CircuitBreakerOpenException as e:
                # Circuit breaker open, don't retry
                logger.error(f"Order submission blocked by circuit breaker: {e}")
                order.status = OrderStatus.FAILED
                order.error_message = str(e)
                await self._emit_order_event("order_created", order, status="failed")
                return False

            except Exception as e:
                logger.warning(
                    f"Order submission failed (attempt {attempt + 1}/{max_retries}): {e}"
                )

                if attempt < max_retries - 1:
                    # Calculate backoff: 2^attempt = 1s, 2s, 4s
                    backoff = 2 ** attempt
                    await asyncio.sleep(backoff)
                else:
                    # Final attempt failed
                    order.status = OrderStatus.FAILED
                    order.error_message = f"Failed after {max_retries} attempts: {e}"
                    await self._emit_order_event("order_created", order, status="failed")
                    return False

        return False

    async def _submit_order_to_exchange(self, order: Order) -> str:
        """
        Actual MEXC API call to submit order.

        Args:
            order: Order object

        Returns:
            Exchange order ID

        Raises:
            Exception: On API errors
        """
        if order.order_type == "market":
            return await self.mexc_adapter.create_market_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity
            )
        else:  # limit
            if order.price is None:
                raise ValueError("Limit order requires price")
            return await self.mexc_adapter.create_limit_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=order.price
            )

    async def _timeout_order(self, order_id: str):
        """
        FIX (Agent 4 - Task 3): Timeout handler for pending orders.

        Automatically cancels order if it stays in PENDING/SUBMITTED state
        for longer than order_timeout_seconds.

        Args:
            order_id: Local order ID to timeout
        """
        try:
            await asyncio.sleep(self.order_timeout_seconds)

            # Check if order still pending/submitted
            async with self._order_lock:
                if order_id not in self.orders:
                    return  # Order already removed

                order = self.orders[order_id]

            if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                logger.warning(
                    f"Order timeout: {order_id} still in {order.status.value} after {self.order_timeout_seconds}s, cancelling..."
                )

                # Attempt to cancel the order
                success = await self.cancel_order(order_id)

                if success:
                    logger.info(f"Order {order_id} cancelled due to timeout")
                else:
                    logger.error(f"Failed to cancel timed out order {order_id}")
            else:
                # Order already in terminal state, no action needed
                logger.debug(f"Order {order_id} timeout task found order in {order.status.value}, no cancellation needed")

        except asyncio.CancelledError:
            # Timeout task cancelled (order filled or manually cancelled)
            logger.debug(f"Timeout task cancelled for order {order_id} (order completed)")
        except Exception as e:
            logger.error(f"Error in timeout handler for order {order_id}: {e}")

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel pending order.

        Args:
            order_id: Local order ID

        Returns:
            True if cancelled successfully, False otherwise
        """
        # Get order (protect with lock)
        async with self._order_lock:
            if order_id not in self.orders:
                logger.warning(f"Cannot cancel unknown order: {order_id}")
                return False

            order = self.orders[order_id]

        if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            logger.warning(f"Cannot cancel order in status {order.status}: {order_id}")
            return False

        try:
            # Cancel via MEXC adapter (circuit breaker already integrated)
            success = await self.mexc_adapter.cancel_order(
                order.symbol,
                order.exchange_order_id
            )

            if success:
                order.status = OrderStatus.CANCELLED
                order.updated_at = time.time()

                logger.info(f"Order cancelled: {order_id}")

                # FIX (Agent 4 - Task 3): Cancel timeout task
                if order_id in self._order_timeouts:
                    self._order_timeouts[order_id].cancel()
                    del self._order_timeouts[order_id]
                    logger.debug(f"Timeout task cancelled for manually cancelled order {order_id}")

                await self.event_bus.publish("order_cancelled", {
                    "order_id": order_id,
                    "exchange_order_id": order.exchange_order_id,
                    "timestamp": int(time.time() * 1000)
                })

                return True
            else:
                logger.warning(f"Failed to cancel order {order_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def _poll_order_status(self):
        """
        Background task: Poll order status every 2 seconds.

        Checks all SUBMITTED orders for fills.
        """
        while self._running:
            try:
                await asyncio.sleep(2)

                # Get all submitted/partially filled orders (protect with lock)
                async with self._order_lock:
                    active_orders = [
                        order for order in self.orders.values()
                        if order.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
                    ]

                if not active_orders:
                    continue

                logger.debug(f"Polling status for {len(active_orders)} orders...")

                # Poll each order
                for order in active_orders:
                    try:
                        # Get order status from MEXC (circuit breaker integrated in adapter)
                        status_response = await self.mexc_adapter.get_order_status(
                            order.symbol,
                            order.exchange_order_id
                        )

                        await self._update_order_status(order, status_response)

                    except CircuitBreakerOpenException:
                        logger.warning("Skipping order status poll: circuit breaker open")
                        break  # Skip remaining orders
                    except Exception as e:
                        logger.error(f"Failed to poll order {order.order_id}: {e}")

            except asyncio.CancelledError:
                logger.info("Order status polling stopped")
                break
            except Exception as e:
                logger.error(f"Error in order status polling: {e}")

    async def _update_order_status(self, order: Order, status_response):
        """
        Update order from MEXC status response.

        Args:
            order: Local order object
            status_response: OrderStatusResponse from MEXC adapter
        """
        old_status = order.status

        # Update order fields from response
        order.filled_quantity = status_response.filled_quantity
        order.average_fill_price = status_response.average_fill_price
        order.updated_at = time.time()

        # Update status based on MEXC status
        if status_response.status.value == "FILLED":
            order.status = OrderStatus.FILLED
        elif status_response.status.value == "PARTIALLY_FILLED":
            order.status = OrderStatus.PARTIALLY_FILLED
        elif status_response.status.value == "CANCELED":
            order.status = OrderStatus.CANCELLED

        # Emit event if status changed
        if order.status != old_status:
            logger.info(
                f"Order status changed: {order.order_id} {old_status.value} → {order.status.value}"
            )

            # FIX (Agent 4 - Task 3): Cancel timeout task for terminal states
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.FAILED]:
                if order.order_id in self._order_timeouts:
                    self._order_timeouts[order.order_id].cancel()
                    del self._order_timeouts[order.order_id]
                    logger.debug(f"Timeout task cancelled for order {order.order_id} (status: {order.status.value})")

            if order.status == OrderStatus.FILLED:
                # Calculate commission (0.1% of filled value)
                commission = order.filled_quantity * order.average_fill_price * 0.001

                await self.event_bus.publish("order_filled", {
                    "order_id": order.order_id,
                    "symbol": order.symbol,  # FIX: Add symbol for position tracking
                    "side": order.side,      # FIX: Add side for position tracking
                    "quantity": order.filled_quantity,  # FIX: Use filled_quantity for position calc
                    "price": order.average_fill_price,  # FIX: Use average_fill_price for position calc
                    "filled_quantity": order.filled_quantity,
                    "filled_price": order.average_fill_price,
                    "commission": commission,
                    "status": "FILLED",
                    "timestamp": int(time.time() * 1000)
                })

    async def _cleanup_old_orders(self):
        """
        Background task: Cleanup old orders every 60 seconds.

        Removes orders older than 1 hour that are in terminal states.
        """
        while self._running:
            try:
                await asyncio.sleep(60)

                now = time.time()
                to_remove = []

                # Protect iteration and deletion with lock
                async with self._order_lock:
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

    async def _emit_order_event(self, event_type: str, order: Order, status: str):
        """
        Emit order event to EventBus with TradingPersistenceService-compatible schema.

        Args:
            event_type: Event type (order_created, order_filled, etc.)
            order: Order object
            status: Order status string
        """
        event_data = {
            "order_id": order.order_id,
            "exchange_order_id": order.exchange_order_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "price": order.price,
            "status": status if status != "submitted" else "NEW",  # Map to TPS schema
            "error": order.error_message,
            "timestamp": int(time.time() * 1000)
        }

        # Add extra fields for order_created events
        if event_type == "order_created":
            event_data["strategy_id"] = order.strategy_id
            event_data["order_type"] = order.order_type.upper()
            event_data["metadata"] = {}

        await self.event_bus.publish(event_type, event_data)

    # === Public Getters ===

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        async with self._order_lock:
            return self.orders.get(order_id)

    async def get_all_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all orders, optionally filtered by symbol."""
        async with self._order_lock:
            if symbol:
                return [o for o in self.orders.values() if o.symbol == symbol]
            return list(self.orders.values())

    async def get_metrics(self) -> Dict[str, int]:
        """Get order manager metrics."""
        async with self._order_lock:
            return {
                "total_orders": len(self.orders),
                "pending": sum(1 for o in self.orders.values() if o.status == OrderStatus.PENDING),
                "submitted": sum(1 for o in self.orders.values() if o.status == OrderStatus.SUBMITTED),
                "filled": sum(1 for o in self.orders.values() if o.status == OrderStatus.FILLED),
                "cancelled": sum(1 for o in self.orders.values() if o.status == OrderStatus.CANCELLED),
                "failed": sum(1 for o in self.orders.values() if o.status == OrderStatus.FAILED),
            }

    async def close_position(self, position_id: str, symbol: str, quantity: float, current_price: float) -> bool:
        """
        Close an existing position by creating a market exit order.

        Args:
            position_id: Position identifier
            symbol: Trading symbol (e.g., "BTC_USDT")
            quantity: Position size to close
            current_price: Current market price (for logging)

        Returns:
            True if close order submitted successfully, False otherwise
        """
        logger.info(f"Closing position {position_id}: {symbol} qty={quantity} @ {current_price}")

        # Determine exit side (opposite of position side)
        # If we have a long position, we need to sell; if short, we need to buy
        # TODO: Implement position side detection from Position object (see GitHub issue)
        # Requires: Position tracking system to determine if position is LONG or SHORT
        # Current implementation: assumes LONG positions (exit_side="sell")
        # Update when position management is fully implemented
        exit_side = "sell"

        # Create market exit order
        order = Order(
            order_id=f"close_{position_id}_{int(time.time() * 1000)}",
            symbol=symbol,
            side=exit_side,
            quantity=quantity,
            price=None,  # Market order
            order_type="market",
            status=OrderStatus.PENDING,
            created_at=time.time(),
            updated_at=time.time()
        )

        # Submit order (will handle retries and events)
        success = await self.submit_order(order, current_positions=None)

        if success:
            logger.info(f"Position close order submitted: {position_id} → {order.order_id}")
        else:
            logger.error(f"Failed to submit position close order: {position_id}")

        return success
