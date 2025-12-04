"""
Paper Trading Engine
====================

Real-time paper trading execution engine that processes strategy signals into virtual trades.
Implements realistic order execution with slippage, position management, and performance tracking.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..core.logger import StructuredLogger
from ..domain.services.order_manager import OrderManager, OrderType
from ..domain.services.risk_manager import RiskManager


class TradingSignalType(Enum):
    """Trading signal types for paper trading."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"


@dataclass
class TradingSignal:
    """Trading signal from strategy execution."""
    symbol: str
    action: TradingSignalType
    quantity: float
    strategy_name: str
    confidence: float = 0.0
    price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PaperTrade:
    """Record of a paper trade execution."""
    order_id: str
    symbol: str
    action: TradingSignalType
    quantity: float
    execution_price: float
    strategy_name: str
    timestamp: datetime
    slippage: float = 0.0
    commission: float = 0.0


class PaperTradingEngine:
    """
    Real-time paper trading execution engine.

    Processes trading signals from strategies and executes virtual orders with realistic
    market conditions including slippage, latency, and position management.
    """

    def __init__(self,
                 order_manager: OrderManager,
                 risk_manager: RiskManager,
                 logger: StructuredLogger,
                 slippage_model: Optional[Callable] = None,
                 commission_rate: float = 0.001):  # 0.1% commission

        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.logger = logger
        self.commission_rate = commission_rate

        # Slippage model - defaults to simple percentage-based
        self.slippage_model = slippage_model or self._default_slippage_model

        # Active positions tracking
        self.active_positions: Dict[str, Dict[str, Any]] = {}

        # Trade history
        self.trade_history: List[PaperTrade] = []

        # Performance tracking
        self.performance_metrics: Dict[str, Any] = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'total_commission': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0
        }

        self.logger.info("paper_trading_engine.initialized", {
            "commission_rate": commission_rate,
            "has_slippage_model": slippage_model is not None
        })

    async def process_signal(self, signal: TradingSignal) -> Optional[str]:
        """
        Process a trading signal and execute order if risk checks pass.

        Args:
            signal: Trading signal from strategy

        Returns:
            Order ID if executed, None if rejected
        """
        try:
            # Validate signal
            if not await self._validate_signal(signal):
                self.logger.debug("paper_trading_engine.signal_rejected", {
                    "symbol": signal.symbol,
                    "action": signal.action.value,
                    "reason": "validation_failed"
                })
                return None

            # Calculate position size with risk management
            position_size = await self._calculate_position_size(signal)
            if position_size <= 0:
                self.logger.debug("paper_trading_engine.signal_rejected", {
                    "symbol": signal.symbol,
                    "action": signal.action.value,
                    "reason": "position_size_zero"
                })
                return None

            # Apply slippage to get execution price
            execution_price = self._calculate_execution_price(signal, position_size)

            # Execute the order
            order_id = await self._execute_order(signal, position_size, execution_price)

            if order_id:
                # Record the trade for performance tracking
                await self._record_trade(order_id, signal, position_size, execution_price)

                self.logger.info("paper_trading_engine.signal_executed", {
                    "order_id": order_id,
                    "symbol": signal.symbol,
                    "action": signal.action.value,
                    "quantity": position_size,
                    "execution_price": execution_price,
                    "strategy": signal.strategy_name
                })

            return order_id

        except Exception as e:
            self.logger.error("paper_trading_engine.signal_processing_error", {
                "symbol": signal.symbol,
                "action": signal.action.value,
                "error": str(e)
            })
            return None

    async def _validate_signal(self, signal: TradingSignal) -> bool:
        """Validate trading signal against risk rules."""
        # Check if action is valid
        if signal.action not in [TradingSignalType.BUY, TradingSignalType.SELL, TradingSignalType.EMERGENCY_EXIT]:
            return False

        # Check position limits for emergency exit
        if signal.action == TradingSignalType.EMERGENCY_EXIT:
            position = await self.order_manager.get_position(signal.symbol)
            return position is not None and position.get('quantity', 0) > 0

        # For BUY signals, check if we already have a position
        if signal.action == TradingSignalType.BUY:
            position = await self.order_manager.get_position(signal.symbol)
            if position and position.get('quantity', 0) > 0:
                # Already have position, could implement averaging logic here
                return False

        return True

    async def _calculate_position_size(self, signal: TradingSignal) -> float:
        """Calculate position size using risk management rules."""
        # Use risk manager to determine position size
        # For now, use a simple approach based on signal confidence
        base_position_size = 100.0  # Base position in USD

        if signal.confidence > 0:
            # Scale position size with confidence (0.1 to 1.0 multiplier)
            confidence_multiplier = 0.1 + (signal.confidence * 0.9)
            position_size = base_position_size * confidence_multiplier
        else:
            position_size = base_position_size

        # Apply risk management limits
        max_position_size = 1000.0  # Max position in USD
        position_size = min(position_size, max_position_size)

        return position_size

    def _calculate_execution_price(self, signal: TradingSignal, position_size: float) -> float:
        """Calculate execution price with slippage."""
        # Use provided price or estimate current market price
        base_price = signal.price or 50000.0  # Default BTC price

        # Apply slippage model
        slippage_pct = self.slippage_model(position_size, signal.action)

        if signal.action == TradingSignalType.BUY:
            # Pay slightly more for buys (slippage)
            execution_price = base_price * (1 + slippage_pct)
        else:
            # Receive slightly less for sells (slippage)
            execution_price = base_price * (1 - slippage_pct)

        return execution_price

    def _default_slippage_model(self, position_size: float, action: TradingSignalType) -> float:
        """Default slippage model based on position size."""
        # Larger positions have more slippage
        base_slippage = 0.001  # 0.1% base slippage
        size_multiplier = min(position_size / 100.0, 5.0)  # Max 5x multiplier

        return base_slippage * size_multiplier

    async def _execute_order(self,
                           signal: TradingSignal,
                           position_size: float,
                           execution_price: float) -> Optional[str]:
        """Execute the order through the order manager."""
        try:
            # Convert signal action to order type
            if signal.action == TradingSignalType.BUY:
                order_type = OrderType.BUY
                quantity = position_size / execution_price  # Convert USD to crypto amount
            elif signal.action in [TradingSignalType.SELL, TradingSignalType.EMERGENCY_EXIT]:
                order_type = OrderType.SELL
                # Get current position quantity
                position = await self.order_manager.get_position(signal.symbol)
                if not position:
                    return None
                quantity = position['quantity']
            else:
                return None

            # Submit the order
            order_id = await self.order_manager.submit_order(
                symbol=signal.symbol,
                order_type=order_type,
                quantity=quantity,
                price=execution_price,
                strategy_name=signal.strategy_name
            )

            return order_id

        except Exception as e:
            self.logger.error("paper_trading_engine.order_execution_error", {
                "symbol": signal.symbol,
                "action": signal.action.value,
                "error": str(e)
            })
            return None

    async def _record_trade(self,
                          order_id: str,
                          signal: TradingSignal,
                          quantity: float,
                          execution_price: float) -> None:
        """Record trade for performance tracking."""
        # Calculate slippage and commission
        base_price = signal.price or execution_price
        slippage = abs(execution_price - base_price) / base_price
        commission = quantity * execution_price * self.commission_rate

        # Create trade record
        trade = PaperTrade(
            order_id=order_id,
            symbol=signal.symbol,
            action=signal.action,
            quantity=quantity,
            execution_price=execution_price,
            strategy_name=signal.strategy_name,
            timestamp=signal.timestamp,
            slippage=slippage,
            commission=commission
        )

        self.trade_history.append(trade)

        # Update performance metrics
        self.performance_metrics['total_trades'] += 1
        self.performance_metrics['total_commission'] += commission

        # Update telemetry with total trades
        self._update_trade_metrics(trade)

        self.logger.debug("paper_trading_engine.trade_recorded", {
            "order_id": order_id,
            "symbol": signal.symbol,
            "pnl_impact": 0.0,  # Would calculate based on position changes
            "commission": commission
        })

    def _update_trade_metrics(self, trade: PaperTrade) -> None:
        """Update telemetry with trade metrics"""
        try:
            from src.core.telemetry import telemetry

            # Increment total trades counter
            telemetry.increment_counter('business.total_trades', 1)

            # Update total PnL gauge (if we have realized pnl)
            if hasattr(trade, 'realized_pnl') and trade.realized_pnl is not None:
                total_pnl = self.performance_metrics.get('total_pnl', 0.0)
                telemetry.set_gauge('business.total_pnl', float(total_pnl))

                # Track winning/losing trades
                if trade.realized_pnl > 0:
                    telemetry.increment_counter('business.winning_trades', 1)
                elif trade.realized_pnl < 0:
                    telemetry.increment_counter('business.losing_trades', 1)
        except Exception as e:
            self.logger.warning("paper_trading_engine.telemetry_update_failed", {
                "error": str(e)
            })

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary."""
        # Calculate current P&L from positions
        current_pnl = 0.0
        positions = await self.order_manager.get_all_positions()

        for position in positions:
            # Simplified P&L calculation - would need current market prices
            # For now, just return basic metrics
            pass

        return {
            **self.performance_metrics,
            'active_positions': len(positions),
            'current_pnl': current_pnl,
            'total_trades': len(self.trade_history),
            'last_update': datetime.now().isoformat()
        }

    async def emergency_exit_all(self) -> List[str]:
        """Emergency exit all positions."""
        positions = await self.order_manager.get_all_positions()
        exited_symbols = []

        for position in positions:
            if position['quantity'] > 0:
                # Create emergency exit signal
                signal = TradingSignal(
                    symbol=position['symbol'],
                    action=TradingSignalType.EMERGENCY_EXIT,
                    quantity=position['quantity'],
                    strategy_name="emergency_exit"
                )

                # Process the exit signal
                order_id = await self.process_signal(signal)
                if order_id:
                    exited_symbols.append(position['symbol'])

        self.logger.warning("paper_trading_engine.emergency_exit_all", {
            "exited_symbols": exited_symbols,
            "total_positions": len(positions)
        })

        return exited_symbols