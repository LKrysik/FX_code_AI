"""
Order Manager - In-Memory Paper Trading Implementation
======================================================
Provides a lightweight order/position tracker used when real MEXC
integration is unavailable. Designed to keep higher layers of the system
operational in development environments.
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
    PENDING = "pending"
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
    side: OrderType
    quantity: float  # Positive for BUY/SHORT, negative not used (side determines direction)
    price: float
    status: OrderStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    strategy_name: str = ""
    pump_signal_strength: float = 0.0
    leverage: float = 1.0  # 1.0 = no leverage, 3.0 = 3x leverage
    order_kind: str = "MARKET"  # MARKET or LIMIT
    max_slippage_pct: float = 1.0  # Maximum allowed slippage percentage
    actual_slippage_pct: float = 0.0  # Actual slippage at execution (paper trading)


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
    leverage: float = 1.0  # 1.0 = no leverage, 3.0 = 3x leverage
    liquidation_price: Optional[float] = None  # Price at which position is liquidated
    unrealized_pnl: float = 0.0  # Unrealized profit/loss in quote currency
    unrealized_pnl_pct: float = 0.0  # Unrealized P&L as percentage

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

        ✅ EDGE CASE FIX: Handle zero/invalid prices gracefully.

        Args:
            current_price: Current market price
        """
        # ✅ EDGE CASE FIX: Handle invalid inputs
        if current_price is None or current_price <= 0:
            # Invalid current price - keep existing P&L
            return

        if self.quantity == 0 or self.average_price == 0:
            self.unrealized_pnl = 0.0
            self.unrealized_pnl_pct = 0.0
            return

        # ✅ EDGE CASE FIX: Protect against division by zero
        if self.average_price <= 0:
            self.unrealized_pnl = 0.0
            self.unrealized_pnl_pct = 0.0
            return

        if self.quantity > 0:  # LONG position
            self.unrealized_pnl = self.quantity * (current_price - self.average_price)
            self.unrealized_pnl_pct = ((current_price - self.average_price) / self.average_price) * 100
        else:  # SHORT position (quantity < 0)
            # For SHORT: profit when price drops, loss when price rises
            self.unrealized_pnl = abs(self.quantity) * (self.average_price - current_price)
            self.unrealized_pnl_pct = ((self.average_price - current_price) / self.average_price) * 100


class OrderManager:
    """
    In-memory order manager for paper trading with EventBus integration.

    Architecture:
    - Subscribes to EventBus "signal_generated" events (like LiveOrderManager)
    - Simulates order execution with slippage
    - Tracks positions in-memory
    - Compatible with unified live/paper/backtest architecture

    Lifecycle:
    1. Create instance via Container
    2. Call start() to subscribe to EventBus
    3. Process signals automatically
    4. Call stop() to cleanup
    """

    def __init__(self, logger: StructuredLogger, event_bus=None):
        """
        Initialize paper trading order manager.

        Args:
            logger: Structured logger instance
            event_bus: Optional EventBus for signal subscription (None for tests)
        """
        self.logger = logger
        self.event_bus = event_bus
        self._lock = asyncio.Lock()  # Main lock for orders/positions
        self._order_sequence_lock = asyncio.Lock()  # Atomic ID generation
        self._orders: Dict[str, OrderRecord] = {}
        self._positions: Dict[str, PositionRecord] = {}
        self._order_sequence = 0
        self._started = False
        self.logger.info("order_manager.paper_mode_initialized", {
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
            self.logger.info("order_manager.subscribed_to_signals")

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
            self.logger.info("order_manager.unsubscribed_from_signals")

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
            self.logger.debug("order_manager.signal_ignored", {
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
            self.logger.error("order_manager.invalid_signal", {
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
            self.logger.error("order_manager.invalid_signal_side", {
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

            self.logger.info("order_manager.signal_processed", {
                "signal_type": signal_type,
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity
            })

        except Exception as e:
            self.logger.error("order_manager.signal_processing_failed", {
                "signal": data,
                "error": str(e),
                "error_type": type(e).__name__
            })

    def _generate_order_id(self) -> str:
        self._order_sequence += 1
        return f"paper_order_{self._order_sequence:06d}"

    def _simulate_slippage(self, price: float, order_type: OrderType, max_slippage_pct: float) -> tuple[float, float]:
        """Simulate slippage for paper trading

        Args:
            price: Requested price
            order_type: Order type (BUY/SHORT/SELL/COVER)
            max_slippage_pct: Maximum allowed slippage percentage

        Returns:
            tuple of (actual_price, actual_slippage_pct)
        """
        import random

        # Simulate slippage as random value between 0 and max_slippage_pct
        slippage_pct = random.uniform(0, max_slippage_pct)

        # BUY/SHORT: slippage increases price (worse fill)
        # SELL/COVER: slippage decreases price (worse fill)
        if order_type in (OrderType.BUY, OrderType.SHORT):
            actual_price = price * (1 + slippage_pct / 100)
        else:  # SELL or COVER
            actual_price = price * (1 - slippage_pct / 100)

        return actual_price, slippage_pct

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
            # Example: entry=$100, leverage=3x → liq=$66.67
            return entry_price * (1 - 1 / leverage)
        else:
            # SHORT: liquidation = entry × (1 + 1/leverage)
            # Example: entry=$100, leverage=3x → liq=$133.33
            return entry_price * (1 + 1 / leverage)

    def _validate_order_inputs(
        self,
        symbol: str,
        quantity: float,
        price: float,
        leverage: float,
        max_slippage_pct: float
    ) -> None:
        """
        Validate order input parameters.

        ✅ EDGE CASE FIX: Added comprehensive input validation.

        Raises:
            ValueError: If any parameter is invalid
        """
        # Validate symbol
        if not symbol or not isinstance(symbol, str) or len(symbol.strip()) == 0:
            raise ValueError("Invalid symbol: must be a non-empty string")

        # Validate quantity
        if quantity is None or quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity} - must be positive")

        # Check for unreasonably large quantity
        if quantity > 1e15:
            raise ValueError(f"Invalid quantity: {quantity} - exceeds reasonable limit")

        # Validate price
        if price is None or price <= 0:
            raise ValueError(f"Invalid price: {price} - must be positive")

        # Check for unreasonably large price
        if price > 1e15:
            raise ValueError(f"Invalid price: {price} - exceeds reasonable limit")

        # Validate leverage
        if leverage < 1.0 or leverage > 10.0:
            raise ValueError(f"Leverage must be between 1.0 and 10.0, got {leverage}")

        # Validate slippage
        if max_slippage_pct < 0:
            raise ValueError(f"Invalid max_slippage_pct: {max_slippage_pct} - cannot be negative")

    async def submit_order(self,
                          symbol: str,
                          order_type: OrderType,
                          quantity: float,
                          price: float,
                          strategy_name: str = "",
                          pump_signal_strength: float = 0.0,
                          leverage: float = 1.0,
                          order_kind: str = "MARKET",
                          max_slippage_pct: float = 1.0) -> str:
        """Submit order with SHORT support, leverage, and slippage simulation

        Args:
            symbol: Trading symbol (e.g., 'BTC_USDT')
            order_type: Order type (BUY, SELL, SHORT, COVER)
            quantity: Order quantity (always positive)
            price: Target price
            strategy_name: Name of strategy placing order
            pump_signal_strength: Pump detection signal strength
            leverage: Leverage multiplier (1.0 = no leverage, 3.0 = 3x, max 10x)
            order_kind: Order kind (MARKET or LIMIT)
            max_slippage_pct: Maximum allowed slippage percentage

        Returns:
            Order ID

        Raises:
            ValueError: If any parameter is invalid
        """
        # ✅ EDGE CASE FIX: Validate all inputs before acquiring lock
        self._validate_order_inputs(symbol, quantity, price, leverage, max_slippage_pct)

        async with self._lock:  # Protect entire order submission
            # Log warning for high leverage (>5x)
            if leverage > 5.0:
                self.logger.warning("order_manager.high_leverage_warning", {
                    "leverage": leverage,
                    "symbol": symbol,
                    "order_type": order_type.name,
                    "liquidation_distance_pct": round(100 / leverage, 1),
                    "warning": f"HIGH RISK: {leverage}x leverage. Liquidation at {(100/leverage):.1f}% price movement"
                })

            # Generate ID atomically
            async with self._order_sequence_lock:
                order_id = self._generate_order_id()

            # Simulate slippage for MARKET orders
            actual_price = price
            actual_slippage_pct = 0.0
            if order_kind == "MARKET":
                actual_price, actual_slippage_pct = self._simulate_slippage(price, order_type, max_slippage_pct)

            status = OrderStatus.FILLED  # Paper mode fills immediately
            record = OrderRecord(
                order_id=order_id,
                symbol=symbol.upper(),
                side=order_type,
                quantity=float(quantity),
                price=float(actual_price),
                status=status,
                strategy_name=strategy_name,
                pump_signal_strength=float(pump_signal_strength),
                leverage=float(leverage),
                order_kind=order_kind,
                max_slippage_pct=float(max_slippage_pct),
                actual_slippage_pct=float(actual_slippage_pct),
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
                    "price": actual_price,
                    "status": "NEW",
                    "metadata": {
                        "leverage": leverage,
                        "max_slippage_pct": max_slippage_pct,
                        "actual_slippage_pct": actual_slippage_pct,
                        "pump_signal_strength": pump_signal_strength
                    },
                    "timestamp": time.time()
                })

            await self._update_position(record)

            # Publish order_filled event (paper trades fill immediately)
            if self.event_bus:
                await self.event_bus.publish("order_filled", {
                    "order_id": order_id,
                    "filled_quantity": quantity,
                    "filled_price": actual_price,
                    "commission": 0.0,  # Paper trading - no commission
                    "status": "FILLED",
                    "timestamp": time.time()
                })

            self.logger.info("order_manager.paper_order_filled", {
                "order_id": order_id,
                "symbol": record.symbol,
                "side": record.side.value,
                "quantity": record.quantity,
                "price": record.price,
                "leverage": record.leverage,
                "slippage_pct": record.actual_slippage_pct
            })
            return order_id

    async def close_position(self,
                            symbol: str,
                            current_price: float,
                            strategy_name: str = "close_position",
                            leverage: float = 1.0,
                            order_kind: str = "MARKET",
                            max_slippage_pct: float = 1.0) -> Optional[str]:
        """Universal position close method for both LONG and SHORT

        Args:
            symbol: Trading symbol
            current_price: Current market price
            strategy_name: Reason for closing (e.g., 'take_profit', 'emergency_exit')
            leverage: Leverage for the close order
            order_kind: MARKET or LIMIT
            max_slippage_pct: Maximum allowed slippage

        Returns:
            Order ID if position closed, None if no position
        """
        position = self._positions.get(symbol.upper())
        if not position or position.quantity == 0:
            return None

        # Determine close order type based on current position
        if position.quantity > 0:
            # Close LONG position with SELL
            order_type = OrderType.SELL
            close_quantity = position.quantity
        else:
            # Close SHORT position with COVER
            order_type = OrderType.COVER
            close_quantity = abs(position.quantity)

        # Submit close order
        order_id = await self.submit_order(
            symbol=symbol,
            order_type=order_type,
            quantity=close_quantity,
            price=current_price,
            strategy_name=strategy_name,
            leverage=leverage,
            order_kind=order_kind,
            max_slippage_pct=max_slippage_pct
        )

        return order_id

    async def take_profit(self, symbol: str, current_price: float) -> Optional[str]:
        """Close position for take profit - supports both LONG and SHORT"""
        return await self.close_position(symbol, current_price, strategy_name="take_profit")

    async def emergency_exit(self, symbol: str, current_price: float) -> Optional[str]:
        """Emergency close position - supports both LONG and SHORT"""
        return await self.close_position(symbol, current_price, strategy_name="emergency_exit")

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        record = self._orders.get(order_id)
        if not record:
            return None
        return self._serialize_order(record)

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position with SHORT support and extended fields

        Returns:
            Position dict with all fields, or None if no position
        """
        position = self._positions.get(symbol.upper())
        if not position or position.quantity == 0:
            return None
        return {
            "symbol": position.symbol,
            "quantity": position.quantity,
            "average_price": position.average_price,
            "position_type": position.position_type,
            "position_size": position.position_size,
            "leverage": position.leverage,
            "liquidation_price": position.liquidation_price,
            "unrealized_pnl": position.unrealized_pnl,
            "unrealized_pnl_pct": position.unrealized_pnl_pct
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        total_orders = len(self._orders)
        filled_orders = len([o for o in self._orders.values() if o.status == OrderStatus.FILLED])
        return {
            "total_orders": total_orders,
            "filled_orders": filled_orders,
            "open_orders": total_orders - filled_orders,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_all_orders(self) -> List[Dict[str, Any]]:
        async with self._lock:
            return [self._serialize_order(o) for o in self._orders.values()]

    async def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions with SHORT support and extended fields"""
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

            self.logger.info("order_manager.paper_order_cancelled", {"order_id": order_id})
            return True

    def _serialize_order(self, record: OrderRecord) -> Dict[str, Any]:
        return {
            "order_id": record.order_id,
            "symbol": record.symbol,
            "side": record.side.value,
            "quantity": record.quantity,
            "price": record.price,
            "status": record.status.value,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "strategy_name": record.strategy_name,
            "pump_signal_strength": record.pump_signal_strength,
            "leverage": record.leverage,
            "order_kind": record.order_kind,
            "max_slippage_pct": record.max_slippage_pct,
            "actual_slippage_pct": record.actual_slippage_pct
        }

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

        # Store entry price for realized PnL calculation (if position closes)
        entry_price_before_close = position.average_price

        if order.side == OrderType.BUY:
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
                # Keep existing leverage, recalculate liquidation
                position.liquidation_price = self._calculate_liquidation_price(
                    position.average_price, position.leverage, is_long=True
                )

        elif order.side == OrderType.SELL:
            # SELL: Close/decrease LONG position
            new_quantity = old_quantity - order.quantity

            if old_quantity <= 0:
                # ERROR: Trying to SELL when not LONG
                self.logger.warning("order_manager.invalid_sell", {
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

        elif order.side == OrderType.SHORT:
            # SHORT: Open/increase SHORT position (negative quantity)
            new_quantity = old_quantity - order.quantity  # Subtract to make more negative

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
                # Keep existing leverage, recalculate liquidation
                position.liquidation_price = self._calculate_liquidation_price(
                    position.average_price, position.leverage, is_long=False
                )

        elif order.side == OrderType.COVER:
            # COVER: Close/decrease SHORT position
            new_quantity = old_quantity + order.quantity  # Add to reduce negative

            if old_quantity >= 0:
                # ERROR: Trying to COVER when not SHORT
                self.logger.warning("order_manager.invalid_cover", {
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
        self.logger.info("order_manager.position_updated", {
            "symbol": order.symbol,
            "order_side": order.side.value,
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
                    "stop_loss": None,  # Not tracked in OrderManager
                    "take_profit": None,  # Not tracked in OrderManager
                    "metadata": {
                        "leverage": position.leverage,
                        "liquidation_price": position.liquidation_price
                    },
                    "timestamp": time.time()
                })
            elif old_quantity != 0 and position.quantity == 0:
                # Position closed - calculate realized PnL
                # Formula:
                # - LONG: (exit_price - entry_price) * quantity
                # - SHORT: (entry_price - exit_price) * abs(quantity)
                # entry_price_before_close was stored before position reset
                exit_price = order.price

                if old_quantity > 0:
                    # LONG position closed
                    realized_pnl = (exit_price - entry_price_before_close) * old_quantity
                else:
                    # SHORT position closed
                    realized_pnl = (entry_price_before_close - exit_price) * abs(old_quantity)

                await self.event_bus.publish("position_closed", {
                    "position_id": f"{order.symbol}_{order.order_id}",
                    "current_price": exit_price,
                    "realized_pnl": realized_pnl,
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
