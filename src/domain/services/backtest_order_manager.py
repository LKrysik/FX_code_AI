"""
Backtest Order Manager - Instant Execution for Backtesting
===========================================================
Provides instant order execution for backtesting with configurable slippage.
Designed to match OrderManager's interface while providing deterministic fills.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

from ...core.logger import StructuredLogger


class OrderStatus(Enum):
    """Order execution status"""
    NEW = "new"
    FILLED = "filled"
    CANCELLED = "cancelled"


class OrderType(Enum):
    """Order type for trading operations

    BUY: Open long position (spot/margin)
    SELL: Close long position (spot/margin)
    SHORT: Open short position (margin/futures)
    COVER: Close short position (margin/futures)
    """
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"
    COVER = "cover"

    def is_opening_order(self) -> bool:
        """Check if order opens a position"""
        return self in (OrderType.BUY, OrderType.SHORT)

    def is_closing_order(self) -> bool:
        """Check if order closes a position"""
        return self in (OrderType.SELL, OrderType.COVER)

    def get_position_type(self) -> str:
        """Get resulting position type"""
        if self in (OrderType.BUY, OrderType.SELL):
            return "LONG"
        else:
            return "SHORT"


@dataclass
class OrderRecord:
    """Order record with SHORT support, leverage, and slippage tracking"""
    order_id: str
    symbol: str
    order_type: OrderType
    quantity: float
    price: float
    status: OrderStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    strategy_name: str = ""
    leverage: float = 1.0
    order_kind: str = "MARKET"


@dataclass
class PositionRecord:
    """Position record with SHORT support and leverage tracking

    Convention: quantity sign determines position type
    - quantity > 0: LONG position
    - quantity < 0: SHORT position
    - quantity = 0: No position
    """
    symbol: str
    quantity: float = 0.0  # Positive = LONG, Negative = SHORT
    average_price: float = 0.0
    leverage: float = 1.0
    liquidation_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0

    @property
    def position_type(self) -> str:
        """Get position type based on quantity sign"""
        if self.quantity > 0:
            return "LONG"
        elif self.quantity < 0:
            return "SHORT"
        else:
            return "NONE"

    @property
    def position_size(self) -> float:
        """Get absolute position size"""
        return abs(self.quantity)

    def update_unrealized_pnl(self, current_price: float) -> None:
        """Update unrealized P&L based on current price

        Args:
            current_price: Current market price
        """
        if self.quantity == 0 or self.average_price == 0:
            self.unrealized_pnl = 0.0
            self.unrealized_pnl_pct = 0.0
            return

        if self.quantity > 0:  # LONG position
            self.unrealized_pnl = self.quantity * (current_price - self.average_price)
            self.unrealized_pnl_pct = ((current_price - self.average_price) / self.average_price) * 100
        else:  # SHORT position (quantity < 0)
            self.unrealized_pnl = abs(self.quantity) * (self.average_price - current_price)
            self.unrealized_pnl_pct = ((self.average_price - current_price) / self.average_price) * 100


class BacktestOrderManager:
    """
    Order manager for backtesting with instant execution.

    Architecture:
    - Subscribes to "signal_generated" events (like OrderManager)
    - Instant fills (no delays or slippage by default)
    - Publishes same events as OrderManager for TradingPersistenceService
    - In-memory position tracking

    Key Differences vs OrderManager:
    - Orders fill instantly (no async delays)
    - Configurable slippage model (default 0%)
    - Deterministic execution for reproducible backtests

    Lifecycle:
    1. Create instance via Container
    2. Call start() to subscribe to EventBus
    3. Process signals automatically
    4. Call stop() to cleanup
    """

    def __init__(
        self,
        logger: StructuredLogger,
        event_bus=None,
        slippage_pct: float = 0.0
    ):
        """
        Initialize backtest order manager.

        Args:
            logger: Structured logger instance
            event_bus: Optional EventBus for signal subscription (None for tests)
            slippage_pct: Slippage percentage (default 0% for deterministic backtests)
        """
        self.logger = logger
        self.event_bus = event_bus
        self.slippage_pct = slippage_pct
        self._lock = asyncio.Lock()  # Main lock for orders/positions
        self._order_sequence_lock = asyncio.Lock()  # Atomic ID generation
        self._orders: Dict[str, OrderRecord] = {}
        self._positions: Dict[str, PositionRecord] = {}
        self._order_sequence = 0
        self._started = False
        self.logger.info("backtest_order_manager.initialized", {
            "slippage_pct": slippage_pct,
            "eventbus_enabled": event_bus is not None
        })

    async def start(self) -> None:
        """
        Start order manager and subscribe to signal events.
        Required for integration with ExecutionController.
        """
        if self._started:
            return

        if self.event_bus:
            await self.event_bus.subscribe("signal_generated", self._on_signal_generated)
            self.logger.info("backtest_order_manager.subscribed_to_signals")

        self._started = True

    async def stop(self) -> None:
        """
        Stop order manager and unsubscribe from events.
        Clean up resources.
        """
        if not self._started:
            return

        if self.event_bus:
            await self.event_bus.unsubscribe("signal_generated", self._on_signal_generated)
            self.logger.info("backtest_order_manager.unsubscribed_from_signals")

        # Clear memory to prevent leaks
        async with self._lock:
            self._orders.clear()
            self._positions.clear()

        self._started = False

    async def _on_signal_generated(self, data: Dict) -> None:
        """
        Handle signal from StrategyManager via EventBus.

        Signal Types (5-state model):
        - S1: Entry signal → Create order
        - Z1: Position opened → Monitor (no order)
        - ZE1: Partial exit → Create exit order
        - E1: Full exit → Create exit order

        Args:
            data: Signal data with keys: signal_type, symbol, side, quantity, price, order_type
        """
        signal_type = data.get("signal_type")

        # Only create orders for S1, ZE1, E1 signals (5-state model)
        if signal_type not in ["S1", "ZE1", "E1"]:
            self.logger.debug("backtest_order_manager.signal_ignored", {
                "signal_type": signal_type,
                "reason": "not_actionable"
            })
            return

        # Extract signal data
        symbol = data.get("symbol")
        side = data.get("side", "").lower()
        quantity = data.get("quantity", 0.0)
        price = data.get("price", 0.0)
        strategy_name = data.get("strategy_name", "unknown")

        # Validate required fields
        if not symbol or not side or quantity <= 0 or price <= 0:
            self.logger.error("backtest_order_manager.invalid_signal", {
                "signal": data,
                "reason": "missing_required_fields"
            })
            return

        # Convert side to OrderType
        if side == "buy":
            order_type = OrderType.BUY
        elif side == "sell":
            order_type = OrderType.SELL
        elif side == "short":
            order_type = OrderType.SHORT
        elif side == "cover":
            order_type = OrderType.COVER
        else:
            self.logger.error("backtest_order_manager.invalid_signal_side", {
                "side": side,
                "symbol": symbol
            })
            return

        # Submit order
        try:
            order_id = await self.submit_order(
                symbol=symbol,
                order_type=order_type,
                quantity=quantity,
                price=price,
                strategy_name=strategy_name
            )

            self.logger.info("backtest_order_manager.signal_processed", {
                "signal_type": signal_type,
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity
            })

        except Exception as e:
            self.logger.error("backtest_order_manager.signal_processing_failed", {
                "signal": data,
                "error": str(e),
                "error_type": type(e).__name__
            })

    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        self._order_sequence += 1
        return f"backtest_order_{self._order_sequence:06d}"

    def _calculate_liquidation_price(self, entry_price: float, leverage: float, is_long: bool) -> Optional[float]:
        """Calculate liquidation price for leveraged position

        Args:
            entry_price: Entry price
            leverage: Leverage multiplier
            is_long: True for LONG, False for SHORT

        Returns:
            Liquidation price, or None if no leverage (1.0)
        """
        if leverage <= 1.0:
            return None  # No liquidation for non-leveraged positions

        if is_long:
            # LONG: liquidation = entry × (1 - 1/leverage)
            return entry_price * (1 - 1 / leverage)
        else:
            # SHORT: liquidation = entry × (1 + 1/leverage)
            return entry_price * (1 + 1 / leverage)

    async def submit_order(
        self,
        symbol: str,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Submit order with INSTANT fill (backtest).

        Args:
            symbol: Trading symbol
            order_type: BUY, SELL, SHORT, COVER
            quantity: Order quantity
            price: Order price
            **kwargs: strategy_name, order_kind, leverage, etc.

        Returns:
            order_id: Unique order identifier
        """
        async with self._lock:
            # Generate order ID atomically
            async with self._order_sequence_lock:
                order_id = self._generate_order_id()

            strategy_name = kwargs.get('strategy_name', 'backtest')
            order_kind = kwargs.get('order_kind', 'MARKET')
            leverage = kwargs.get('leverage', 1.0)

            # Calculate fill price (with optional slippage)
            if self.slippage_pct > 0:
                slippage_factor = 1.0 + (self.slippage_pct / 100.0)
                if order_type in [OrderType.BUY, OrderType.SHORT]:
                    fill_price = price * slippage_factor  # Worse price for buys
                else:
                    fill_price = price * (2.0 - slippage_factor)  # Worse price for sells
            else:
                fill_price = price  # No slippage

            # Create order record
            record = OrderRecord(
                order_id=order_id,
                symbol=symbol.upper(),
                order_type=order_type,
                quantity=float(quantity),
                price=float(fill_price),
                status=OrderStatus.NEW,
                strategy_name=strategy_name,
                order_kind=order_kind,
                leverage=float(leverage),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self._orders[order_id] = record

            # Publish order_created event
            if self.event_bus:
                await self.event_bus.publish("order_created", {
                    "order_id": order_id,
                    "strategy_id": strategy_name,
                    "symbol": symbol.upper(),
                    "side": order_type.name,  # BUY, SELL, SHORT, COVER
                    "order_type": order_kind,  # MARKET or LIMIT
                    "quantity": quantity,
                    "price": fill_price,
                    "status": "NEW",
                    "metadata": {
                        "leverage": leverage,
                        "slippage_pct": self.slippage_pct,
                        "backtest": True
                    },
                    "timestamp": time.time()
                })

            # ✅ INSTANT FILL (backtest characteristic)
            record.status = OrderStatus.FILLED
            await self._update_position(record)

            # Publish order_filled event
            if self.event_bus:
                await self.event_bus.publish("order_filled", {
                    "order_id": order_id,
                    "filled_quantity": quantity,
                    "filled_price": fill_price,
                    "commission": 0.0,  # Backtest - no commission
                    "status": "FILLED",
                    "timestamp": time.time()
                })

            self.logger.info("backtest_order_manager.order_filled", {
                "order_id": order_id,
                "symbol": record.symbol,
                "side": record.order_type.value,
                "quantity": record.quantity,
                "price": record.price,
                "leverage": record.leverage,
                "slippage_pct": self.slippage_pct
            })

            return order_id

    async def _update_position(self, order: OrderRecord) -> None:
        """Update position with SHORT support using quantity sign convention

        Convention:
        - quantity > 0: LONG position
        - quantity < 0: SHORT position
        - quantity = 0: No position

        Order types:
        - BUY: Opens/increases LONG (adds positive quantity)
        - SELL: Closes/decreases LONG (reduces positive quantity)
        - SHORT: Opens/increases SHORT (adds negative quantity)
        - COVER: Closes/decreases SHORT (reduces negative quantity)
        """
        position = self._positions.setdefault(order.symbol, PositionRecord(symbol=order.symbol))

        # Track old quantity for position event detection
        old_quantity = position.quantity

        if order.order_type == OrderType.BUY:
            # BUY: Open/increase LONG position
            new_quantity = old_quantity + order.quantity

            if old_quantity <= 0:
                # Opening new LONG or flipping from SHORT to LONG
                position.quantity = new_quantity
                position.average_price = order.price
                position.leverage = order.leverage
                position.liquidation_price = self._calculate_liquidation_price(
                    order.price, order.leverage, is_long=True
                )
            else:
                # Increasing existing LONG position (average up)
                position.average_price = (
                    (old_quantity * position.average_price) + (order.quantity * order.price)
                ) / new_quantity
                position.quantity = new_quantity
                position.liquidation_price = self._calculate_liquidation_price(
                    position.average_price, position.leverage, is_long=True
                )

        elif order.order_type == OrderType.SELL:
            # SELL: Close/decrease LONG position
            new_quantity = old_quantity - order.quantity

            if old_quantity <= 0:
                # ERROR: Trying to SELL when not LONG
                self.logger.warning("backtest_order_manager.invalid_sell", {
                    "symbol": order.symbol,
                    "current_position": old_quantity,
                    "order_quantity": order.quantity
                })
                return

            position.quantity = new_quantity
            if new_quantity <= 0:
                # Position closed or flipped to SHORT
                position.average_price = 0.0
                position.leverage = 1.0
                position.liquidation_price = None

        elif order.order_type == OrderType.SHORT:
            # SHORT: Open/increase SHORT position (negative quantity)
            new_quantity = old_quantity - order.quantity

            if old_quantity >= 0:
                # Opening new SHORT or flipping from LONG to SHORT
                position.quantity = new_quantity
                position.average_price = order.price
                position.leverage = order.leverage
                position.liquidation_price = self._calculate_liquidation_price(
                    order.price, order.leverage, is_long=False
                )
            else:
                # Increasing existing SHORT position (average down)
                total_short_qty = abs(new_quantity)
                old_short_qty = abs(old_quantity)
                position.average_price = (
                    (old_short_qty * position.average_price) + (order.quantity * order.price)
                ) / total_short_qty
                position.quantity = new_quantity
                position.liquidation_price = self._calculate_liquidation_price(
                    position.average_price, position.leverage, is_long=False
                )

        elif order.order_type == OrderType.COVER:
            # COVER: Close/decrease SHORT position
            new_quantity = old_quantity + order.quantity

            if old_quantity >= 0:
                # ERROR: Trying to COVER when not SHORT
                self.logger.warning("backtest_order_manager.invalid_cover", {
                    "symbol": order.symbol,
                    "current_position": old_quantity,
                    "order_quantity": order.quantity
                })
                return

            position.quantity = new_quantity
            if new_quantity >= 0:
                # Position closed or flipped to LONG
                position.average_price = 0.0
                position.leverage = 1.0
                position.liquidation_price = None

        # Log position update
        self.logger.info("backtest_order_manager.position_updated", {
            "symbol": order.symbol,
            "order_side": order.order_type.value,
            "new_quantity": position.quantity,
            "position_type": position.position_type,
            "average_price": position.average_price,
            "leverage": position.leverage,
            "liquidation_price": position.liquidation_price
        })

        # Publish position events based on quantity changes
        if self.event_bus:
            if old_quantity == 0 and position.quantity != 0:
                # Position opened
                await self.event_bus.publish("position_opened", {
                    "position_id": f"{order.symbol}_{order.order_id}",
                    "strategy_id": order.strategy_name,
                    "symbol": order.symbol,
                    "side": position.position_type,  # LONG or SHORT
                    "quantity": position.position_size,
                    "entry_price": position.average_price,
                    "current_price": position.average_price,
                    "stop_loss": None,
                    "take_profit": None,
                    "metadata": {
                        "leverage": position.leverage,
                        "liquidation_price": position.liquidation_price,
                        "backtest": True
                    },
                    "timestamp": time.time()
                })
            elif old_quantity != 0 and position.quantity == 0:
                # Position closed
                await self.event_bus.publish("position_closed", {
                    "position_id": f"{order.symbol}_{order.order_id}",
                    "current_price": order.price,
                    "realized_pnl": 0.0,  # TODO: Calculate from entry/exit prices
                    "timestamp": time.time()
                })
            elif old_quantity != 0 and position.quantity != 0:
                # Position updated (size changed)
                await self.event_bus.publish("position_updated", {
                    "position_id": f"{order.symbol}_{order.order_id}",
                    "current_price": order.price,
                    "unrealized_pnl": position.unrealized_pnl,
                    "timestamp": time.time()
                })

    async def get_all_orders(self) -> List[Dict[str, Any]]:
        """Get all orders"""
        async with self._lock:
            return [self._serialize_order(o) for o in self._orders.values()]

    async def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions with SHORT support"""
        async with self._lock:
            return [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "average_price": pos.average_price,
                    "position_type": pos.position_type,
                    "position_size": pos.position_size,
                    "leverage": pos.leverage,
                    "liquidation_price": pos.liquidation_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "unrealized_pnl_pct": pos.unrealized_pnl_pct
                }
                for pos in self._positions.values()
                if pos.quantity != 0
            ]

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        async with self._lock:
            record = self._orders.get(order_id)
            if not record:
                return False
            record.status = OrderStatus.CANCELLED
            record.updated_at = datetime.utcnow()

            # Publish order_cancelled event
            if self.event_bus:
                await self.event_bus.publish("order_cancelled", {
                    "order_id": order_id,
                    "timestamp": time.time()
                })

            self.logger.info("backtest_order_manager.order_cancelled", {"order_id": order_id})
            return True

    def _serialize_order(self, record: OrderRecord) -> Dict[str, Any]:
        """Serialize order record to dictionary"""
        return {
            "order_id": record.order_id,
            "symbol": record.symbol,
            "side": record.order_type.value,
            "quantity": record.quantity,
            "price": record.price,
            "status": record.status.value,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "strategy_name": record.strategy_name,
            "leverage": record.leverage,
            "order_kind": record.order_kind
        }
