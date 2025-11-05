"""
Live Order Manager - MEXC Futures Integration
==============================================
Order manager for live trading with MEXC futures API.
Extends paper trading OrderManager with real exchange integration.

Key differences from paper OrderManager:
- Uses MexcFuturesAdapter for real order execution
- Sets leverage on MEXC before opening positions
- Syncs positions with MEXC (real-time position tracking)
- Handles order rejection and retries
- Calculates funding costs for SHORT positions

Usage:
    from src.infrastructure.adapters.mexc_futures_adapter import MexcFuturesAdapter

    async with MexcFuturesAdapter(api_key, api_secret, logger) as adapter:
        order_manager = LiveOrderManager(logger, exchange_adapter=adapter)

        # Set leverage before opening position
        await order_manager.set_leverage("BTC_USDT", 3)

        # Open SHORT position
        order_id = await order_manager.submit_order(
            symbol="BTC_USDT",
            order_type=OrderType.SHORT,
            quantity=0.001,
            price=50000,
            leverage=3.0
        )
"""

from typing import Optional, Dict, Any
from datetime import datetime

from .order_manager import (
    OrderManager,
    OrderType,
    OrderStatus,
    OrderRecord,
    PositionRecord
)
from ...core.logger import StructuredLogger


class LiveOrderManager(OrderManager):
    """
    Live order manager with MEXC Futures integration.

    Extends paper OrderManager to support real trading via MexcFuturesAdapter.
    Falls back to paper mode if no adapter provided.
    """

    def __init__(self,
                 logger: StructuredLogger,
                 exchange_adapter: Optional[Any] = None):
        """
        Initialize live order manager.

        Args:
            logger: Structured logger
            exchange_adapter: MexcFuturesAdapter instance (None = paper mode)
        """
        super().__init__(logger)
        self.exchange_adapter = exchange_adapter
        self.is_live_mode = exchange_adapter is not None

        if self.is_live_mode:
            self.logger.info("order_manager.live_mode_initialized", {
                "adapter_type": type(exchange_adapter).__name__
            })
        else:
            self.logger.info("order_manager.paper_mode_initialized")

    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for symbol on exchange.

        Args:
            symbol: Trading symbol
            leverage: Leverage multiplier (1-10 recommended)

        Returns:
            True if leverage set successfully

        Note:
            In paper mode, this only updates internal state.
            In live mode, sends request to MEXC.
        """
        if not self.is_live_mode:
            # Paper mode: just log
            self.logger.info("order_manager.set_leverage_paper", {
                "symbol": symbol,
                "leverage": leverage
            })
            return True

        # Live mode: set leverage on exchange
        try:
            await self.exchange_adapter.set_leverage(symbol, leverage)
            self.logger.info("order_manager.set_leverage_success", {
                "symbol": symbol,
                "leverage": leverage
            })
            return True

        except Exception as e:
            self.logger.error("order_manager.set_leverage_error", {
                "symbol": symbol,
                "leverage": leverage,
                "error": str(e)
            })
            return False

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
        """
        Submit order - uses exchange adapter in live mode, simulates in paper mode.

        Args:
            symbol: Trading symbol
            order_type: Order type (BUY, SELL, SHORT, COVER)
            quantity: Order quantity
            price: Target price
            strategy_name: Strategy name
            pump_signal_strength: Signal strength
            leverage: Leverage multiplier (1.0-10.0)
            order_kind: MARKET or LIMIT
            max_slippage_pct: Max slippage %

        Returns:
            Order ID

        Raises:
            ValueError: If leverage is invalid (must be 1-10)
        """
        if not self.is_live_mode:
            # Paper mode: use parent's implementation (includes validation)
            return await super().submit_order(
                symbol, order_type, quantity, price,
                strategy_name, pump_signal_strength,
                leverage, order_kind, max_slippage_pct
            )

        # TIER 3.1: Validate leverage before live order submission
        if leverage < 1.0 or leverage > 10.0:
            error_msg = f"Leverage must be between 1.0 and 10.0, got {leverage}"
            self.logger.error("order_manager_live.invalid_leverage", {
                "leverage": leverage,
                "symbol": symbol,
                "order_type": order_type.name,
                "strategy_name": strategy_name
            })
            raise ValueError(error_msg)

        # Log warning for high leverage (>5x) in live mode
        if leverage > 5.0:
            self.logger.warning("order_manager_live.high_leverage_warning", {
                "leverage": leverage,
                "symbol": symbol,
                "order_type": order_type.name,
                "liquidation_distance_pct": round(100 / leverage, 1),
                "warning": f"HIGH RISK LIVE ORDER: {leverage}x leverage. Liquidation at {(100/leverage):.1f}% price movement"
            })

        # Live mode: submit to MEXC Futures
        try:
            # Map OrderType to MEXC API parameters
            side, position_side = self._map_order_type_to_mexc(order_type)

            # Set leverage before opening position (if opening order)
            if order_type.is_opening_order() and leverage > 1.0:
                await self.set_leverage(symbol, int(leverage))

            # Submit order to exchange
            response = await self.exchange_adapter.place_futures_order(
                symbol=symbol,
                side=side,
                position_side=position_side,
                order_type=order_kind,
                quantity=quantity,
                price=price if order_kind == "LIMIT" else None
            )

            # Extract order ID from response
            order_id = response.get("order_id") or response.get("orderId") or "unknown"

            # Create order record
            order_record = OrderRecord(
                order_id=str(order_id),
                symbol=symbol.upper(),
                side=order_type,
                quantity=float(quantity),
                price=float(response.get("avg_price") or response.get("price") or price),
                status=OrderStatus.FILLED if response.get("status") == "FILLED" else OrderStatus.PENDING,
                strategy_name=strategy_name,
                pump_signal_strength=pump_signal_strength,
                leverage=leverage,
                order_kind=order_kind,
                max_slippage_pct=max_slippage_pct,
                actual_slippage_pct=0.0  # TODO: Calculate from avg_price vs requested price
            )

            # Store order
            self._orders[order_id] = order_record

            # Update position tracking
            if order_record.status == OrderStatus.FILLED:
                self._update_position(order_record)

            self.logger.info("order_manager.live_order_submitted", {
                "order_id": order_id,
                "symbol": symbol,
                "side": order_type.value,
                "quantity": quantity,
                "price": order_record.price,
                "leverage": leverage
            })

            return str(order_id)

        except Exception as e:
            self.logger.error("order_manager.submit_order_error", {
                "symbol": symbol,
                "order_type": order_type.value,
                "error": str(e)
            })
            raise

    def _map_order_type_to_mexc(self, order_type: OrderType) -> tuple[str, str]:
        """
        Map OrderType to MEXC API parameters.

        Args:
            order_type: Our OrderType enum

        Returns:
            Tuple of (side, position_side) for MEXC API

        MEXC API logic:
        - LONG + BUY = Open long
        - LONG + SELL = Close long
        - SHORT + SELL = Open short
        - SHORT + BUY = Close short (cover)
        """
        if order_type == OrderType.BUY:
            return ("BUY", "LONG")
        elif order_type == OrderType.SELL:
            return ("SELL", "LONG")
        elif order_type == OrderType.SHORT:
            return ("SELL", "SHORT")
        elif order_type == OrderType.COVER:
            return ("BUY", "SHORT")
        else:
            raise ValueError(f"Unknown order type: {order_type}")

    async def close_position(self,
                            symbol: str,
                            current_price: float,
                            strategy_name: str = "close_position",
                            leverage: float = 1.0,
                            order_kind: str = "MARKET",
                            max_slippage_pct: float = 1.0) -> Optional[str]:
        """
        Close position - uses exchange adapter in live mode.

        Args:
            symbol: Trading symbol
            current_price: Current market price
            strategy_name: Reason for closing
            leverage: Leverage
            order_kind: MARKET or LIMIT
            max_slippage_pct: Max slippage

        Returns:
            Order ID or None
        """
        if not self.is_live_mode:
            # Paper mode: use parent's implementation
            return await super().close_position(
                symbol, current_price, strategy_name,
                leverage, order_kind, max_slippage_pct
            )

        # Live mode: close via exchange adapter
        try:
            # Get current position from exchange
            exchange_position = await self.exchange_adapter.get_position(symbol)

            if not exchange_position:
                self.logger.warning("order_manager.no_position_to_close", {
                    "symbol": symbol
                })
                return None

            position_side = exchange_position["position_side"]

            # Close position via exchange
            response = await self.exchange_adapter.close_position(
                symbol=symbol,
                position_side=position_side,
                order_type=order_kind,
                price=current_price if order_kind == "LIMIT" else None
            )

            order_id = response.get("order_id") or response.get("orderId")

            self.logger.info("order_manager.position_closed", {
                "order_id": order_id,
                "symbol": symbol,
                "position_side": position_side,
                "strategy_name": strategy_name
            })

            # Update local tracking
            local_position = self._positions.get(symbol.upper())
            if local_position:
                local_position.quantity = 0.0
                local_position.average_price = 0.0
                local_position.liquidation_price = None

            return str(order_id)

        except Exception as e:
            self.logger.error("order_manager.close_position_error", {
                "symbol": symbol,
                "error": str(e)
            })
            raise

    async def sync_position_from_exchange(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Sync position from exchange (live mode only).

        Useful for:
        - Initial sync on startup
        - Recovery from connection loss
        - Verification after orders

        Args:
            symbol: Trading symbol

        Returns:
            Position info or None
        """
        if not self.is_live_mode:
            # Paper mode: return local position
            return self.get_position(symbol)

        try:
            # Get position from exchange
            exchange_position = await self.exchange_adapter.get_position(symbol)

            if not exchange_position:
                # No position on exchange - clear local
                if symbol.upper() in self._positions:
                    self._positions[symbol.upper()].quantity = 0.0
                return None

            # Update local position to match exchange
            position = self._positions.setdefault(
                symbol.upper(),
                PositionRecord(symbol=symbol.upper())
            )

            # Map exchange position to local format
            position_amount = exchange_position["position_amount"]
            position.quantity = position_amount  # Negative = SHORT
            position.average_price = exchange_position["entry_price"]
            position.leverage = exchange_position["leverage"]
            position.liquidation_price = exchange_position["liquidation_price"]
            position.unrealized_pnl = exchange_position.get("unrealized_pnl", 0.0)

            # Calculate P&L percentage
            if position.average_price > 0:
                position.unrealized_pnl_pct = (
                    position.unrealized_pnl / (abs(position_amount) * position.average_price)
                ) * 100

            self.logger.info("order_manager.position_synced", {
                "symbol": symbol,
                "quantity": position.quantity,
                "entry_price": position.average_price,
                "unrealized_pnl": position.unrealized_pnl
            })

            return self.get_position(symbol)

        except Exception as e:
            self.logger.error("order_manager.sync_position_error", {
                "symbol": symbol,
                "error": str(e)
            })
            return None

    async def get_funding_cost(self, symbol: str, holding_hours: float = 24.0) -> float:
        """
        Calculate funding cost for current position.

        Args:
            symbol: Trading symbol
            holding_hours: Expected holding period

        Returns:
            Expected funding cost (negative = you pay)
        """
        if not self.is_live_mode:
            return 0.0  # No funding in paper mode

        try:
            position = self.get_position(symbol)
            if not position or position["quantity"] == 0:
                return 0.0

            # Get funding cost from adapter
            funding_cost = await self.exchange_adapter.calculate_funding_cost(
                symbol=symbol,
                position_amount=position["quantity"],
                holding_hours=holding_hours
            )

            return funding_cost

        except Exception as e:
            self.logger.warning("order_manager.funding_cost_error", {
                "symbol": symbol,
                "error": str(e)
            })
            return 0.0
