"""
Paper MEXC Futures Adapter - Simulated Futures Trading
=======================================================
Complete paper trading implementation that mirrors MexcFuturesAdapter interface.
Simulates futures trading with leverage, SHORT positions, slippage, and funding rates.

Usage:
    async with MexcPaperAdapter(logger, initial_balance=10000.0) as adapter:
        # Set leverage (stored in memory)
        await adapter.set_leverage("BTC_USDT", 3)

        # Open SHORT position with simulated execution
        order = await adapter.place_futures_order(
            symbol="BTC_USDT",
            side="SELL",
            position_side="SHORT",
            order_type="MARKET",
            quantity=0.001
        )

        # Get position with unrealized P&L
        position = await adapter.get_position("BTC_USDT")

        # Calculate funding cost
        cost = await adapter.calculate_funding_cost("BTC_USDT", -0.001, 24)
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Literal, List
from ...core.logger import StructuredLogger


class MexcPaperAdapter:
    """
    Paper trading adapter that simulates MEXC Futures API.

    Features:
    - Full futures API interface (matches MexcFuturesAdapter)
    - Leverage support (1-200x)
    - SHORT and LONG position simulation
    - Realistic slippage (0.01-0.1%)
    - Simulated funding rates (typical range: -0.1% to +0.1%)
    - Liquidation price calculation
    - Position tracking with unrealized P&L
    """

    def __init__(self,
                 logger: StructuredLogger,
                 initial_balance: float = 10000.0,
                 initial_balances: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize paper adapter.

        Args:
            logger: Structured logger
            initial_balance: Starting USDT balance
            initial_balances: Legacy parameter for backward compatibility
        """
        self._logger = logger

        # Wallet balances
        if initial_balances:
            self._assets = dict(initial_balances)
        else:
            self._assets = {
                "USDT": {"free": str(initial_balance), "locked": "0.0"},
                "BTC": {"free": "0.0", "locked": "0.0"},
            }

        # Position tracking
        self._positions: Dict[str, Dict[str, Any]] = {}

        # Leverage settings per symbol
        self._leverage_settings: Dict[str, int] = {}

        # Order history
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._order_sequence = 0

        # Simulated market prices (would use real prices in production)
        self._market_prices: Dict[str, float] = {
            "BTC_USDT": 50000.0,
            "ETH_USDT": 3000.0,
            "SOL_USDT": 100.0
        }

        # Simulated funding rates (updated every 8 hours in real futures)
        self._funding_rates: Dict[str, float] = {
            "BTC_USDT": 0.0001,  # 0.01%
            "ETH_USDT": 0.00005,  # 0.005%
            "SOL_USDT": 0.00015   # 0.015%
        }

        self._logger.info("mexc_paper_adapter.initialized", {
            "initial_balance": initial_balance,
            "mode": "paper_trading"
        })

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass

    def get_balances(self) -> Dict[str, Any]:
        """Return current balances (legacy method)."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "assets": self._assets,
            "source": "paper_wallet",
        }
        self._logger.debug("mexc_paper_adapter.get_balances", snapshot)
        return snapshot

    async def set_leverage(self,
                          symbol: str,
                          leverage: int,
                          margin_type: Literal["ISOLATED", "CROSS"] = "ISOLATED") -> Dict[str, Any]:
        """
        Set leverage for symbol (stored in memory).

        Args:
            symbol: Trading symbol
            leverage: Leverage multiplier (1-200)
            margin_type: ISOLATED or CROSS (simulated)

        Returns:
            Success response
        """
        if leverage < 1 or leverage > 200:
            raise ValueError(f"Leverage must be between 1 and 200, got {leverage}")

        symbol_upper = symbol.upper()
        self._leverage_settings[symbol_upper] = leverage

        self._logger.info("mexc_paper_adapter.set_leverage", {
            "symbol": symbol,
            "leverage": leverage,
            "margin_type": margin_type
        })

        return {
            "success": True,
            "symbol": symbol,
            "leverage": leverage,
            "margin_type": margin_type,
            "source": "paper_trading"
        }

    async def get_leverage(self, symbol: str) -> int:
        """
        Get current leverage setting for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Leverage (1 if not set)
        """
        return self._leverage_settings.get(symbol.upper(), 1)

    def _simulate_market_price(self, symbol: str) -> float:
        """
        Get simulated market price for symbol.

        In real implementation, this would fetch live prices.
        For paper trading, we use stored values with small random variation.
        """
        base_price = self._market_prices.get(symbol.upper(), 50000.0)

        # Add small random variation (±0.1%)
        variation = random.uniform(-0.001, 0.001)
        return base_price * (1 + variation)

    def _simulate_slippage(self, price: float, side: str, order_type: str) -> float:
        """
        Simulate slippage for order execution.

        Args:
            price: Base price
            side: BUY or SELL
            order_type: MARKET or LIMIT

        Returns:
            Execution price with slippage
        """
        if order_type == "LIMIT":
            return price  # No slippage on limit orders

        # MARKET orders: 0.01-0.1% slippage
        slippage_pct = random.uniform(0.0001, 0.001)

        if side == "BUY":
            # Buy at higher price (worse fill)
            return price * (1 + slippage_pct)
        else:
            # Sell at lower price (worse fill)
            return price * (1 - slippage_pct)

    def _calculate_liquidation_price(self,
                                     entry_price: float,
                                     leverage: int,
                                     position_side: str) -> float:
        """
        Calculate liquidation price for position.

        Args:
            entry_price: Entry price
            leverage: Leverage multiplier
            position_side: LONG or SHORT

        Returns:
            Liquidation price
        """
        if leverage <= 1:
            return 0.0 if position_side == "LONG" else float('inf')

        if position_side == "LONG":
            # LONG: liquidation = entry × (1 - 1/leverage)
            return entry_price * (1 - 1 / leverage)
        else:
            # SHORT: liquidation = entry × (1 + 1/leverage)
            return entry_price * (1 + 1 / leverage)

    async def place_futures_order(self,
                                  symbol: str,
                                  side: Literal["BUY", "SELL"],
                                  position_side: Literal["LONG", "SHORT"],
                                  order_type: Literal["MARKET", "LIMIT"],
                                  quantity: float,
                                  price: Optional[float] = None,
                                  time_in_force: str = "GTC",
                                  reduce_only: bool = False) -> Dict[str, Any]:
        """
        Place simulated futures order.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            position_side: LONG or SHORT
            order_type: MARKET or LIMIT
            quantity: Order quantity
            price: Limit price (optional for MARKET)
            time_in_force: GTC, IOC, FOK
            reduce_only: Only reduce position

        Returns:
            Order result
        """
        symbol_upper = symbol.upper()
        order_id = self._generate_order_id()

        # Get market price
        market_price = self._simulate_market_price(symbol)
        execution_price = price if order_type == "LIMIT" else market_price

        # Apply slippage
        execution_price = self._simulate_slippage(execution_price, side, order_type)

        # Get leverage
        leverage = self._leverage_settings.get(symbol_upper, 1)

        # Calculate liquidation price
        liquidation_price = self._calculate_liquidation_price(
            execution_price, leverage, position_side
        )

        # Update position
        self._update_position(
            symbol_upper, side, position_side, quantity,
            execution_price, leverage, liquidation_price, reduce_only
        )

        # Record order
        order_result = {
            "order_id": order_id,
            "status": "FILLED",  # Paper orders fill immediately
            "symbol": symbol_upper,
            "side": side,
            "position_side": position_side,
            "type": order_type,
            "quantity": quantity,
            "price": execution_price,
            "avg_price": execution_price,
            "leverage": leverage,
            "liquidation_price": liquidation_price,
            "source": "paper_trading",
            "timestamp": datetime.utcnow().isoformat()
        }

        self._orders[order_id] = order_result

        self._logger.info("mexc_paper_adapter.order_filled", order_result)

        return order_result

    def _update_position(self,
                        symbol: str,
                        side: str,
                        position_side: str,
                        quantity: float,
                        price: float,
                        leverage: int,
                        liquidation_price: float,
                        reduce_only: bool) -> None:
        """Update position based on order execution."""
        position_key = f"{symbol}_{position_side}"

        if position_key not in self._positions:
            self._positions[position_key] = {
                "symbol": symbol,
                "position_side": position_side,
                "position_amount": 0.0,
                "entry_price": 0.0,
                "leverage": leverage,
                "liquidation_price": liquidation_price,
                "unrealized_pnl": 0.0,
                "margin_type": "ISOLATED"
            }

        position = self._positions[position_key]

        # Determine if opening or closing
        is_opening = (side == "BUY" and position_side == "LONG") or \
                     (side == "SELL" and position_side == "SHORT")

        if is_opening:
            # Opening position
            old_amount = position["position_amount"]
            old_price = position["entry_price"]

            new_amount = old_amount + quantity
            if old_amount == 0:
                position["entry_price"] = price
            else:
                # Average price
                position["entry_price"] = (
                    (old_amount * old_price) + (quantity * price)
                ) / new_amount

            position["position_amount"] = new_amount
            position["leverage"] = leverage
            position["liquidation_price"] = liquidation_price

        else:
            # Closing position
            position["position_amount"] = max(0, position["position_amount"] - quantity)

            if position["position_amount"] == 0:
                # Position fully closed
                position["entry_price"] = 0.0
                position["liquidation_price"] = 0.0
                position["unrealized_pnl"] = 0.0

    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current position for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position info or None
        """
        symbol_upper = symbol.upper()

        # Check both LONG and SHORT positions
        for pos_side in ["LONG", "SHORT"]:
            position_key = f"{symbol_upper}_{pos_side}"
            position = self._positions.get(position_key)

            if position and position["position_amount"] > 0:
                # Calculate unrealized P&L
                current_price = self._simulate_market_price(symbol)
                entry_price = position["entry_price"]
                amount = position["position_amount"]

                if pos_side == "LONG":
                    unrealized_pnl = amount * (current_price - entry_price)
                else:  # SHORT
                    unrealized_pnl = amount * (entry_price - current_price)

                position["unrealized_pnl"] = unrealized_pnl
                position["source"] = "paper_trading"

                return position

        return None  # No active position

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions (paper trading simulation).

        ✅ FUTURES ONLY - Returns position dictionaries (NOT PositionResponse objects)

        This matches the interface change made in Phase 4 where MexcFuturesAdapter
        and PositionSyncService were updated to use Dict instead of PositionResponse.

        Returns:
            List of position dictionaries for positions with non-zero quantity

        Note:
            Paper trading doesn't have network errors, so no exceptions are raised.

        Architecture Decision (Phase 5):
            Removed import of PositionResponse from deprecated mexc_adapter.py (MexcSpotAdapter)
            which had RuntimeError in class definition. Using Dict for consistency with
            MexcFuturesAdapter.get_positions().
        """
        positions = []

        for position_key, position in self._positions.items():
            # Only include positions with non-zero quantity
            if position["position_amount"] <= 0:
                continue

            symbol = position["symbol"]
            current_price = self._simulate_market_price(symbol)
            entry_price = position["entry_price"]
            amount = position["position_amount"]
            position_side = position["position_side"]

            # Calculate unrealized P&L
            if position_side == "LONG":
                unrealized_pnl = amount * (current_price - entry_price)
            else:  # SHORT
                unrealized_pnl = amount * (entry_price - current_price)

            # Calculate margin (for isolated margin: notional / leverage)
            leverage = position.get("leverage", 1)
            margin = (amount * current_price) / leverage if leverage > 0 else 0

            # Calculate margin ratio (simulated as 100% + (pnl / margin) * 100)
            # In paper trading, we assume healthy margin ratios
            margin_ratio = 100.0 + (unrealized_pnl / margin * 100) if margin > 0 else 100.0

            # Return dictionary instead of PositionResponse object
            position_dict = {
                "symbol": symbol,
                "side": position_side,
                "quantity": amount,
                "entry_price": entry_price,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "margin_ratio": margin_ratio,
                "liquidation_price": position.get("liquidation_price", 0.0),
                "leverage": leverage,
                "margin": margin
            }

            positions.append(position_dict)

        self._logger.debug("mexc_paper_adapter.get_positions", {
            "count": len(positions),
            "source": "paper_trading"
        })

        return positions

    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Get simulated funding rate.

        Args:
            symbol: Trading symbol

        Returns:
            Funding rate info
        """
        symbol_upper = symbol.upper()
        funding_rate = self._funding_rates.get(symbol_upper, 0.0001)

        # Simulate next funding time (every 8 hours)
        now = datetime.utcnow()
        hours_until_funding = 8 - (now.hour % 8)
        next_funding = now + timedelta(hours=hours_until_funding)

        return {
            "symbol": symbol_upper,
            "funding_rate": funding_rate,
            "funding_time": now.isoformat(),
            "next_funding_time": next_funding.isoformat(),
            "mark_price": self._simulate_market_price(symbol),
            "source": "paper_trading"
        }

    async def calculate_funding_cost(self,
                                     symbol: str,
                                     position_amount: float,
                                     holding_hours: float) -> float:
        """
        Calculate expected funding cost.

        Args:
            symbol: Trading symbol
            position_amount: Position size (positive=LONG, negative=SHORT)
            holding_hours: Expected holding period

        Returns:
            Funding cost (negative=you pay, positive=you earn)
        """
        funding_info = await self.get_funding_rate(symbol)
        funding_rate = funding_info["funding_rate"]
        mark_price = funding_info["mark_price"]

        # Funding applied every 8 hours
        funding_intervals = holding_hours / 8

        # Notional value
        notional_value = abs(position_amount) * mark_price

        # Calculate total funding
        total_funding = position_amount * mark_price * funding_rate * funding_intervals

        return -total_funding  # Negative = cost

    async def create_market_order(self, symbol: str, side: str, quantity: float) -> str:
        """
        Create market order (compatibility wrapper for MexcFuturesAdapter interface).

        Compatibility method - wraps place_futures_order() to match Spot adapter interface.
        Automatically determines position_side based on side parameter.

        Args:
            symbol: Trading symbol (e.g., "BTC_USDT")
            side: "BUY" or "SELL"
            quantity: Order quantity

        Returns:
            Paper order ID (string)

        Note:
            This is a compatibility wrapper. For new code, use place_futures_order() directly
            with explicit position_side parameter for better control over LONG/SHORT positions.
        """
        # Determine position_side: BUY -> LONG, SELL -> SHORT
        position_side = "LONG" if side.upper() == "BUY" else "SHORT"

        self._logger.info("mexc_paper_adapter.create_market_order_wrapper", {
            "symbol": symbol,
            "side": side,
            "position_side": position_side,
            "quantity": quantity,
            "note": "Compatibility wrapper - use place_futures_order() for explicit control"
        })

        response = await self.place_futures_order(
            symbol=symbol,
            side=side.upper(),
            position_side=position_side,
            order_type="MARKET",
            quantity=quantity
        )

        # Extract order ID from response
        order_id = response.get("order_id", "")

        return order_id

    async def close_position(self,
                            symbol: str,
                            position_side: Literal["LONG", "SHORT"],
                            order_type: Literal["MARKET", "LIMIT"] = "MARKET",
                            price: Optional[float] = None) -> Dict[str, Any]:
        """
        Close entire position.

        Args:
            symbol: Trading symbol
            position_side: LONG or SHORT
            order_type: MARKET or LIMIT
            price: Limit price

        Returns:
            Order result
        """
        position = await self.get_position(symbol)

        if not position or position["position_side"] != position_side:
            raise ValueError(f"No {position_side} position found for {symbol}")

        quantity = position["position_amount"]

        # Determine side (opposite of position)
        side = "BUY" if position_side == "SHORT" else "SELL"

        return await self.place_futures_order(
            symbol=symbol,
            side=side,
            position_side=position_side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            reduce_only=True
        )

    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        self._order_sequence += 1
        return f"paper_{self._order_sequence:08d}_{uuid.uuid4().hex[:8]}"
