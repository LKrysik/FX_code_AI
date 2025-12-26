"""
MEXC Futures Order Executor - IOrderExecutor Implementation
============================================================
Wraps MexcFuturesAdapter to implement the IOrderExecutor interface.
This bridges the gap between the trading orchestrator and the MEXC API.

Created to fix: TradeExecutorFactory NotImplementedError
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from ...domain.interfaces.trading import IOrderExecutor
from ...domain.models.trading import Order, OrderSide, OrderType, OrderStatus
from ...core.logger import StructuredLogger
from .mexc_futures_adapter import MexcFuturesAdapter


class MexcFuturesOrderExecutor(IOrderExecutor):
    """
    IOrderExecutor implementation using MexcFuturesAdapter.

    This class:
    - Implements the IOrderExecutor interface for TradingOrchestrator
    - Wraps MexcFuturesAdapter for actual MEXC API calls
    - Translates between domain models and MEXC API formats
    """

    def __init__(
        self,
        mexc_adapter: MexcFuturesAdapter,
        logger: StructuredLogger,
        default_leverage: int = 3
    ):
        """
        Initialize MEXC Futures Order Executor.

        Args:
            mexc_adapter: MexcFuturesAdapter instance (with circuit breaker)
            logger: Structured logger
            default_leverage: Default leverage for positions (1-10, default: 3)
        """
        self.mexc_adapter = mexc_adapter
        self.logger = logger
        self.default_leverage = default_leverage
        self._connected = False
        self._order_cache: Dict[str, Order] = {}

        self.logger.info("mexc_futures_order_executor.initialized", {
            "default_leverage": default_leverage
        })

    async def connect(self) -> None:
        """Establish connection to MEXC Futures API"""
        try:
            # MexcFuturesAdapter uses context manager, MexcPaperAdapter doesn't need session
            if hasattr(self.mexc_adapter, '_ensure_session'):
                await self.mexc_adapter._ensure_session()
            self._connected = True
            self.logger.info("mexc_futures_order_executor.connected")
        except Exception as e:
            self.logger.error("mexc_futures_order_executor.connect_failed", {
                "error": str(e)
            })
            raise

    async def disconnect(self) -> None:
        """Close connection to MEXC Futures API"""
        try:
            if hasattr(self.mexc_adapter, '_close_session'):
                await self.mexc_adapter._close_session()
            self._connected = False
            self.logger.info("mexc_futures_order_executor.disconnected")
        except Exception as e:
            self.logger.error("mexc_futures_order_executor.disconnect_error", {
                "error": str(e)
            })

    async def place_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Place a market order on MEXC Futures"""
        try:
            # Determine position side based on order side
            # BUY -> LONG, SELL -> SHORT
            position_side = "LONG" if side == OrderSide.BUY else "SHORT"

            self.logger.info("mexc_futures_order_executor.placing_market_order", {
                "symbol": symbol,
                "side": side.value,
                "position_side": position_side,
                "quantity": str(quantity)
            })

            # Set leverage before placing order
            await self.mexc_adapter.set_leverage(symbol, self.default_leverage)

            # Place order via MEXC adapter
            response = await self.mexc_adapter.place_futures_order(
                symbol=symbol,
                side=side.value.upper(),
                position_side=position_side,
                order_type="MARKET",
                quantity=float(quantity)
            )

            # Convert to domain Order model
            order = self._response_to_order(response, symbol, side, quantity, None)
            self._order_cache[order.order_id] = order

            self.logger.info("mexc_futures_order_executor.market_order_placed", {
                "order_id": order.order_id,
                "symbol": symbol,
                "status": order.status.value
            })

            return order

        except Exception as e:
            self.logger.error("mexc_futures_order_executor.market_order_failed", {
                "symbol": symbol,
                "side": side.value,
                "error": str(e)
            })
            raise

    async def place_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Place a limit order on MEXC Futures"""
        try:
            position_side = "LONG" if side == OrderSide.BUY else "SHORT"

            self.logger.info("mexc_futures_order_executor.placing_limit_order", {
                "symbol": symbol,
                "side": side.value,
                "position_side": position_side,
                "quantity": str(quantity),
                "price": str(price)
            })

            # Set leverage before placing order
            await self.mexc_adapter.set_leverage(symbol, self.default_leverage)

            # Place order via MEXC adapter
            response = await self.mexc_adapter.place_futures_order(
                symbol=symbol,
                side=side.value.upper(),
                position_side=position_side,
                order_type="LIMIT",
                quantity=float(quantity),
                price=float(price)
            )

            # Convert to domain Order model
            order = self._response_to_order(response, symbol, side, quantity, price)
            self._order_cache[order.order_id] = order

            return order

        except Exception as e:
            self.logger.error("mexc_futures_order_executor.limit_order_failed", {
                "symbol": symbol,
                "error": str(e)
            })
            raise

    async def place_stop_loss_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        stop_price: Decimal,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Place a stop loss order on MEXC Futures"""
        # MEXC Futures uses different endpoint for stop orders
        # For now, implement as a limit order at stop price
        # TODO: Implement proper stop order when MEXC API supports it
        self.logger.warning("mexc_futures_order_executor.stop_loss_as_limit", {
            "symbol": symbol,
            "note": "Stop loss implemented as limit order - monitor position manually"
        })
        return await self.place_limit_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=stop_price,
            client_order_id=client_order_id
        )

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order"""
        try:
            self.logger.info("mexc_futures_order_executor.cancelling_order", {
                "order_id": order_id,
                "symbol": symbol
            })

            # MEXC cancel order endpoint
            response = await self.mexc_adapter._make_request(
                "DELETE",
                "/fapi/v1/order",
                {"symbol": symbol.upper(), "orderId": order_id},
                signed=True
            )

            # Update cache
            if order_id in self._order_cache:
                self._order_cache[order_id].status = OrderStatus.CANCELLED

            return True

        except Exception as e:
            self.logger.error("mexc_futures_order_executor.cancel_order_failed", {
                "order_id": order_id,
                "error": str(e)
            })
            return False

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all orders for a symbol (or all symbols)"""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol.upper()

            response = await self.mexc_adapter._make_request(
                "DELETE",
                "/fapi/v1/allOpenOrders",
                params,
                signed=True
            )

            cancelled_count = response.get("count", 0) if isinstance(response, dict) else 0

            self.logger.info("mexc_futures_order_executor.cancelled_all_orders", {
                "symbol": symbol,
                "cancelled_count": cancelled_count
            })

            return cancelled_count

        except Exception as e:
            self.logger.error("mexc_futures_order_executor.cancel_all_failed", {
                "symbol": symbol,
                "error": str(e)
            })
            return 0

    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Order]:
        """Get current status of an order"""
        try:
            response = await self.mexc_adapter._make_request(
                "GET",
                "/fapi/v1/order",
                {"symbol": symbol.upper(), "orderId": order_id},
                signed=True
            )

            if response:
                # Update cache with latest status
                order = self._parse_order_response(response)
                self._order_cache[order_id] = order
                return order

            return self._order_cache.get(order_id)

        except Exception as e:
            self.logger.error("mexc_futures_order_executor.get_order_status_failed", {
                "order_id": order_id,
                "error": str(e)
            })
            return self._order_cache.get(order_id)

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders"""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol.upper()

            response = await self.mexc_adapter._make_request(
                "GET",
                "/fapi/v1/openOrders",
                params,
                signed=True
            )

            orders = []
            if isinstance(response, list):
                for order_data in response:
                    order = self._parse_order_response(order_data)
                    orders.append(order)

            return orders

        except Exception as e:
            self.logger.error("mexc_futures_order_executor.get_open_orders_failed", {
                "symbol": symbol,
                "error": str(e)
            })
            return []

    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Order]:
        """Get order history"""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol.upper()
            if start_time:
                params["startTime"] = int(start_time.timestamp() * 1000)
            if end_time:
                params["endTime"] = int(end_time.timestamp() * 1000)

            response = await self.mexc_adapter._make_request(
                "GET",
                "/fapi/v1/allOrders",
                params,
                signed=True
            )

            orders = []
            if isinstance(response, list):
                for order_data in response:
                    order = self._parse_order_response(order_data)
                    orders.append(order)

            return orders

        except Exception as e:
            self.logger.error("mexc_futures_order_executor.get_order_history_failed", {
                "error": str(e)
            })
            return []

    def get_exchange_name(self) -> str:
        """Get the name of the exchange"""
        return "MEXC_FUTURES"

    async def health_check(self) -> bool:
        """Check if trading connection is healthy"""
        try:
            # Check circuit breaker status (only for live adapter)
            if hasattr(self.mexc_adapter, 'is_circuit_breaker_healthy'):
                if not self.mexc_adapter.is_circuit_breaker_healthy():
                    self.logger.warning("mexc_futures_order_executor.circuit_breaker_unhealthy")
                    return False

            # Try to get account info as health check
            if hasattr(self.mexc_adapter, 'get_balances'):
                await self.mexc_adapter.get_balances()

            return True

        except Exception as e:
            self.logger.error("mexc_futures_order_executor.health_check_failed", {
                "error": str(e)
            })
            return False

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            # Get balances (different method for paper vs live)
            if hasattr(self.mexc_adapter, 'get_balances'):
                balances = await self.mexc_adapter.get_balances()
            elif hasattr(self.mexc_adapter, '_assets'):
                balances = {"assets": self.mexc_adapter._assets}
            else:
                balances = {}

            # Get positions
            if hasattr(self.mexc_adapter, 'get_positions'):
                positions = await self.mexc_adapter.get_positions()
            else:
                positions = []

            # Get circuit breaker status (only for live adapter)
            circuit_breaker = None
            if hasattr(self.mexc_adapter, 'get_circuit_breaker_status'):
                circuit_breaker = self.mexc_adapter.get_circuit_breaker_status()

            return {
                "exchange": "MEXC_FUTURES",
                "balances": balances,
                "positions": positions,
                "circuit_breaker": circuit_breaker
            }

        except Exception as e:
            self.logger.error("mexc_futures_order_executor.get_account_info_failed", {
                "error": str(e)
            })
            return {"exchange": "MEXC_FUTURES", "error": str(e)}

    async def get_trading_fees(self, symbol: str) -> Dict[str, Decimal]:
        """Get trading fees for a symbol"""
        # MEXC Futures standard fees
        # Actual fees may vary based on VIP level
        return {
            "maker": Decimal("0.0002"),  # 0.02%
            "taker": Decimal("0.0004"),  # 0.04%
        }

    def _response_to_order(
        self,
        response: Dict[str, Any],
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Optional[Decimal]
    ) -> Order:
        """Convert MEXC API response to domain Order model"""
        from ...domain.models.trading import Order as DomainOrder

        order_id = str(response.get("order_id", response.get("orderId", "")))
        status_str = response.get("status", "NEW")

        # Map MEXC status to domain OrderStatus
        # Note: EXPIRED mapped to CANCELLED as domain model doesn't have EXPIRED
        status_map = {
            "NEW": OrderStatus.PENDING,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.CANCELLED  # Map EXPIRED to CANCELLED
        }
        status = status_map.get(status_str, OrderStatus.PENDING)

        return DomainOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT if price else OrderType.MARKET,
            quantity=quantity,
            price=price,
            status=status,
            filled_quantity=Decimal(str(response.get("executedQty", 0))),
            average_price=Decimal(str(response.get("avgPrice", 0))) if response.get("avgPrice") else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            exchange="MEXC_FUTURES",
            exchange_order_id=order_id
        )

    def _parse_order_response(self, response: Dict[str, Any]) -> Order:
        """Parse MEXC order response to domain Order"""
        from ...domain.models.trading import Order as DomainOrder

        side_str = response.get("side", "BUY")
        side = OrderSide.BUY if side_str == "BUY" else OrderSide.SELL

        order_type_str = response.get("type", "MARKET")
        order_type = OrderType.LIMIT if order_type_str == "LIMIT" else OrderType.MARKET

        status_str = response.get("status", "NEW")
        # Note: EXPIRED mapped to CANCELLED as domain model doesn't have EXPIRED
        status_map = {
            "NEW": OrderStatus.PENDING,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.CANCELLED  # Map EXPIRED to CANCELLED
        }
        status = status_map.get(status_str, OrderStatus.PENDING)

        return DomainOrder(
            order_id=str(response.get("orderId", "")),
            symbol=response.get("symbol", ""),
            side=side,
            order_type=order_type,
            quantity=Decimal(str(response.get("origQty", 0))),
            price=Decimal(str(response.get("price", 0))) if response.get("price") else None,
            status=status,
            filled_quantity=Decimal(str(response.get("executedQty", 0))),
            average_price=Decimal(str(response.get("avgPrice", 0))) if response.get("avgPrice") else None,
            created_at=datetime.fromtimestamp(response.get("time", 0) / 1000) if response.get("time") else datetime.utcnow(),
            updated_at=datetime.fromtimestamp(response.get("updateTime", 0) / 1000) if response.get("updateTime") else datetime.utcnow(),
            exchange="MEXC_FUTURES",
            exchange_order_id=str(response.get("orderId", ""))
        )
