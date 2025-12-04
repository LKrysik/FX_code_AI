"""
Performance Tracker
===================

Real-time performance tracking and analytics for paper trading.
Calculates P&L, risk metrics, and performance statistics.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import statistics

from ..core.logger import StructuredLogger


class PerformanceMetric(Enum):
    """Performance metrics that can be calculated."""
    TOTAL_RETURN = "total_return"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    AVERAGE_WIN = "average_win"
    AVERAGE_LOSS = "average_loss"
    CALMAR_RATIO = "calmar_ratio"


@dataclass
class TradeRecord:
    """Record of a completed trade."""
    order_id: str
    symbol: str
    action: str
    entry_price: float
    quantity: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    commission: float = 0.0
    strategy_name: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0

    @property
    def is_closed(self) -> bool:
        """Check if trade is closed."""
        return self.exit_price is not None

    @property
    def duration(self) -> Optional[float]:
        """Trade duration in hours."""
        if not self.is_closed:
            return None
        return (self.exit_time - self.entry_time).total_seconds() / 3600


@dataclass
class PositionSnapshot:
    """Snapshot of a position at a point in time."""
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    unrealized_pnl: float
    timestamp: datetime


class PerformanceTracker:
    """
    Real-time performance tracking and analytics for paper trading.

    Tracks trades, positions, and calculates comprehensive performance metrics
    including risk-adjusted returns, drawdown analysis, and trade statistics.
    """

    def __init__(self, logger: StructuredLogger, initial_balance: float = 10000.0):
        self.logger = logger
        self.initial_balance = initial_balance
        self.current_balance = initial_balance

        # Trade tracking
        self.trades: List[TradeRecord] = []
        self.open_trades: Dict[str, TradeRecord] = {}

        # Position snapshots for P&L calculation
        self.position_snapshots: List[PositionSnapshot] = []

        # Daily P&L tracking
        self.daily_pnl: Dict[str, float] = {}  # date -> pnl

        # Performance cache
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_validity_seconds = 30  # Cache metrics for 30 seconds

        self.logger.info("performance_tracker.initialized", {
            "initial_balance": initial_balance
        })

    async def record_trade_entry(self,
                               order_id: str,
                               symbol: str,
                               action: str,
                               quantity: float,
                               price: float,
                               strategy_name: str = "",
                               commission: float = 0.0) -> None:
        """Record a trade entry (opening position)."""
        trade = TradeRecord(
            order_id=order_id,
            symbol=symbol,
            action=action,
            entry_price=price,
            quantity=quantity,
            entry_time=datetime.now(),
            strategy_name=strategy_name,
            commission=commission
        )

        self.open_trades[order_id] = trade
        self.trades.append(trade)

        # Update balance (reduce by commission)
        self.current_balance -= commission

        self.logger.debug("performance_tracker.trade_entry_recorded", {
            "order_id": order_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "strategy": strategy_name
        })

    async def record_trade_exit(self,
                              order_id: str,
                              exit_price: float,
                              commission: float = 0.0) -> None:
        """Record a trade exit (closing position)."""
        if order_id not in self.open_trades:
            self.logger.warning("performance_tracker.trade_exit_not_found", {
                "order_id": order_id
            })
            return

        trade = self.open_trades[order_id]
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.commission += commission

        # Calculate P&L
        if trade.action.upper() == "BUY":
            # For long positions: (exit - entry) * quantity
            trade.pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            # For short positions: (entry - exit) * quantity
            trade.pnl = (trade.entry_price - exit_price) * trade.quantity

        trade.pnl_pct = (trade.pnl / (trade.entry_price * trade.quantity)) * 100

        # Update balance
        self.current_balance += trade.pnl - commission

        # Remove from open trades
        del self.open_trades[order_id]

        # Update daily P&L
        date_key = trade.exit_time.strftime("%Y-%m-%d")
        self.daily_pnl[date_key] = self.daily_pnl.get(date_key, 0.0) + trade.pnl

        # Invalidate cache
        self._invalidate_cache()

        self.logger.info("performance_tracker.trade_exit_recorded", {
            "order_id": order_id,
            "symbol": trade.symbol,
            "pnl": trade.pnl,
            "pnl_pct": trade.pnl_pct,
            "exit_price": exit_price
        })

    async def update_position_snapshot(self,
                                     symbol: str,
                                     quantity: float,
                                     average_price: float,
                                     current_price: float) -> None:
        """Update position snapshot for unrealized P&L calculation."""
        unrealized_pnl = 0.0
        if quantity > 0:
            unrealized_pnl = (current_price - average_price) * quantity

        snapshot = PositionSnapshot(
            symbol=symbol,
            quantity=quantity,
            average_price=average_price,
            current_price=current_price,
            unrealized_pnl=unrealized_pnl,
            timestamp=datetime.now()
        )

        self.position_snapshots.append(snapshot)

        # Keep only last 100 snapshots per symbol for memory efficiency
        symbol_snapshots = [s for s in self.position_snapshots if s.symbol == symbol]
        if len(symbol_snapshots) > 100:
            # Remove oldest snapshots for this symbol
            oldest_to_remove = symbol_snapshots[:-100]
            for old_snapshot in oldest_to_remove:
                self.position_snapshots.remove(old_snapshot)

    async def calculate_realtime_metrics(self) -> Dict[str, float]:
        """Calculate current performance metrics."""
        # Check cache validity
        now = datetime.now()
        if (self._cache_timestamp and
            (now - self._cache_timestamp).total_seconds() < self._cache_validity_seconds and
            self._metrics_cache):
            return self._metrics_cache.copy()

        metrics = {}

        # Basic metrics
        closed_trades = [t for t in self.trades if t.is_closed]
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl < 0]

        metrics['total_trades'] = len(closed_trades)
        metrics['winning_trades'] = len(winning_trades)
        metrics['losing_trades'] = len(losing_trades)
        metrics['win_rate'] = len(winning_trades) / max(len(closed_trades), 1)

        # P&L metrics
        total_pnl = sum(t.pnl for t in closed_trades)
        metrics['total_pnl'] = total_pnl
        metrics['total_return_pct'] = (total_pnl / self.initial_balance) * 100

        # Average win/loss
        if winning_trades:
            metrics['average_win'] = statistics.mean(t.pnl for t in winning_trades)
            metrics['largest_win'] = max(t.pnl for t in winning_trades)
        else:
            metrics['average_win'] = 0.0
            metrics['largest_win'] = 0.0

        if losing_trades:
            metrics['average_loss'] = statistics.mean(t.pnl for t in losing_trades)
            metrics['largest_loss'] = min(t.pnl for t in losing_trades)
        else:
            metrics['average_loss'] = 0.0
            metrics['largest_loss'] = 0.0

        # Profit factor
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        metrics['profit_factor'] = total_wins / max(total_losses, 0.001)

        # Risk metrics
        metrics['max_drawdown'] = self._calculate_max_drawdown()
        metrics['current_drawdown'] = self._calculate_current_drawdown()

        # Sharpe and Sortino ratios (simplified)
        if len(closed_trades) > 1:
            daily_returns = list(self.daily_pnl.values())
            if daily_returns:
                avg_daily_return = statistics.mean(daily_returns)
                daily_volatility = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0.0

                # Annualized Sharpe ratio (assuming 252 trading days)
                if daily_volatility > 0:
                    metrics['sharpe_ratio'] = (avg_daily_return / daily_volatility) * (252 ** 0.5)
                else:
                    metrics['sharpe_ratio'] = 0.0

                # Sortino ratio (downside deviation)
                negative_returns = [r for r in daily_returns if r < 0]
                if negative_returns:
                    downside_deviation = statistics.stdev(negative_returns)
                    metrics['sortino_ratio'] = (avg_daily_return / downside_deviation) * (252 ** 0.5) if downside_deviation > 0 else 0.0
                else:
                    metrics['sortino_ratio'] = float('inf') if avg_daily_return >= 0 else 0.0
            else:
                metrics['sharpe_ratio'] = 0.0
                metrics['sortino_ratio'] = 0.0
        else:
            metrics['sharpe_ratio'] = 0.0
            metrics['sortino_ratio'] = 0.0

        # Calmar ratio
        if metrics['max_drawdown'] > 0:
            annual_return = metrics['total_return_pct']  # Simplified
            metrics['calmar_ratio'] = annual_return / abs(metrics['max_drawdown'])
        else:
            metrics['calmar_ratio'] = 0.0

        # Current unrealized P&L
        unrealized_pnl = 0.0
        if self.position_snapshots:
            # Use latest snapshot for each symbol
            latest_snapshots = {}
            for snapshot in self.position_snapshots:
                latest_snapshots[snapshot.symbol] = snapshot

            unrealized_pnl = sum(s.unrealized_pnl for s in latest_snapshots.values())

        metrics['unrealized_pnl'] = unrealized_pnl
        metrics['total_equity'] = self.current_balance + unrealized_pnl

        # Update cache
        self._metrics_cache = metrics.copy()
        self._cache_timestamp = now

        return metrics

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from peak to trough."""
        if not self.daily_pnl:
            return 0.0

        cumulative_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0

        for pnl in self.daily_pnl.values():
            cumulative_pnl += pnl
            peak = max(peak, cumulative_pnl)
            drawdown = peak - cumulative_pnl
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown from peak."""
        if not self.daily_pnl:
            return 0.0

        cumulative_pnl = sum(self.daily_pnl.values())
        peak = max(0.0, max(self.daily_pnl.values())) if self.daily_pnl else 0.0

        return max(0.0, peak - cumulative_pnl)

    def _invalidate_cache(self) -> None:
        """Invalidate the metrics cache."""
        self._cache_timestamp = None
        self._metrics_cache.clear()

    async def get_trade_history(self,
                              symbol: Optional[str] = None,
                              strategy: Optional[str] = None,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history with optional filtering."""
        trades = self.trades

        if symbol:
            trades = [t for t in trades if t.symbol == symbol]

        if strategy:
            trades = [t for t in trades if t.strategy_name == strategy]

        # Sort by entry time, most recent first
        trades = sorted(trades, key=lambda t: t.entry_time, reverse=True)

        # Convert to dict format
        result = []
        for trade in trades[:limit]:
            result.append({
                'order_id': trade.order_id,
                'symbol': trade.symbol,
                'action': trade.action,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'quantity': trade.quantity,
                'entry_time': trade.entry_time.isoformat(),
                'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                'commission': trade.commission,
                'strategy_name': trade.strategy_name,
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_pct,
                'is_closed': trade.is_closed,
                'duration_hours': trade.duration
            })

        return result

    async def reset(self) -> None:
        """Reset all performance tracking data."""
        self.trades.clear()
        self.open_trades.clear()
        self.position_snapshots.clear()
        self.daily_pnl.clear()
        self.current_balance = self.initial_balance
        self._invalidate_cache()

        self.logger.info("performance_tracker.reset", {
            "initial_balance": self.initial_balance
        })