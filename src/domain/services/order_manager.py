"""
Order Manager - In-Memory Paper Trading Implementation
======================================================
Provides a lightweight order/position tracker used when real MEXC
integration is unavailable. Designed to keep higher layers of the system
operational in development environments.
"""

from __future__ import annotations

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
    """Order direction"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class OrderRecord:
    order_id: str
    symbol: str
    side: OrderType
    quantity: float
    price: float
    status: OrderStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    strategy_name: str = ""
    pump_signal_strength: float = 0.0


@dataclass
class PositionRecord:
    symbol: str
    quantity: float = 0.0
    average_price: float = 0.0


class OrderManager:
    """Simple in-memory order manager for paper mode."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self._orders: Dict[str, OrderRecord] = {}
        self._positions: Dict[str, PositionRecord] = {}
        self._order_sequence = 0
        self.logger.info("order_manager.paper_mode_initialized")

    def _generate_order_id(self) -> str:
        self._order_sequence += 1
        return f"paper_order_{self._order_sequence:06d}"

    async def submit_order(self,
                          symbol: str,
                          order_type: OrderType,
                          quantity: float,
                          price: float,
                          strategy_name: str = "",
                          pump_signal_strength: float = 0.0) -> str:
        order_id = self._generate_order_id()
        status = OrderStatus.FILLED  # Paper mode fills immediately
        record = OrderRecord(
            order_id=order_id,
            symbol=symbol.upper(),
            side=order_type,
            quantity=float(quantity),
            price=float(price),
            status=status,
            strategy_name=strategy_name,
            pump_signal_strength=float(pump_signal_strength),
        )
        self._orders[order_id] = record
        self._update_position(record)
        self.logger.info("order_manager.paper_order_filled", {
            "order_id": order_id,
            "symbol": record.symbol,
            "side": record.side.value,
            "quantity": record.quantity,
            "price": record.price
        })
        return order_id

    async def take_profit(self, symbol: str, current_price: float) -> Optional[str]:
        position = self._positions.get(symbol.upper())
        if not position or position.quantity <= 0:
            return None
        order_id = await self.submit_order(symbol, OrderType.SELL, position.quantity, current_price,
                                           strategy_name="take_profit")
        return order_id

    async def emergency_exit(self, symbol: str, current_price: float) -> Optional[str]:
        position = self._positions.get(symbol.upper())
        if not position or position.quantity <= 0:
            return None
        order_id = await self.submit_order(symbol, OrderType.SELL, position.quantity, current_price,
                                           strategy_name="emergency_exit")
        return order_id

    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        record = self._orders.get(order_id)
        if not record:
            return None
        return self._serialize_order(record)

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        position = self._positions.get(symbol.upper())
        if not position or position.quantity == 0:
            return None
        return {
            "symbol": position.symbol,
            "quantity": position.quantity,
            "average_price": position.average_price,
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

    def get_all_orders(self) -> List[Dict[str, Any]]:
        return [self._serialize_order(o) for o in self._orders.values()]

    def get_all_positions(self) -> List[Dict[str, Any]]:
        return [
            {
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "average_price": pos.average_price
            }
            for pos in self._positions.values()
            if pos.quantity != 0
        ]

    async def cancel_order(self, order_id: str) -> bool:
        record = self._orders.get(order_id)
        if not record:
            return False
        record.status = OrderStatus.CANCELLED
        record.updated_at = datetime.utcnow()
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
            "pump_signal_strength": record.pump_signal_strength
        }

    def _update_position(self, order: OrderRecord) -> None:
        position = self._positions.setdefault(order.symbol, PositionRecord(symbol=order.symbol))
        if order.side == OrderType.BUY:
            new_total = position.quantity + order.quantity
            if new_total == 0:
                position.quantity = 0.0
                position.average_price = 0.0
                return
            position.average_price = (
                (position.quantity * position.average_price) + (order.quantity * order.price)
            ) / new_total
            position.quantity = new_total
        else:
            position.quantity = max(0.0, position.quantity - order.quantity)
            if position.quantity == 0:
                position.average_price = 0.0
