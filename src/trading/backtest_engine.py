"""
Backtest Engine - Story 1b-2
============================
Executes backtests by processing historical data through a strategy.

Flow:
1. Load session config from database
2. Initialize data provider with date range
3. Load and initialize strategy
4. Process historical data candle-by-candle
5. Generate signals and execute orders
6. Track P&L and update progress
7. Store results and mark complete
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

from src.core.logger import StructuredLogger, get_logger
from src.core.event_bus import EventBus
from src.data_feed.questdb_provider import QuestDBProvider
from src.trading.backtest_data_provider_questdb import BacktestMarketDataProvider
from src.domain.services.backtest_order_manager import (
    BacktestOrderManager,
    OrderType,
    PositionRecord
)

logger = get_logger(__name__)


class BacktestStatus(Enum):
    """Backtest session status"""
    PENDING = "pending"
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class BacktestConfig:
    """Configuration for a backtest session"""
    session_id: str
    strategy_id: str
    symbol: str
    start_date: datetime
    end_date: datetime
    acceleration_factor: int = 10
    initial_balance: float = 10000.0
    stop_loss_percent: float = 5.0
    take_profit_percent: float = 10.0
    timeframe: str = "1m"  # Candle timeframe for processing


@dataclass
class BacktestProgress:
    """Progress tracking for backtest execution"""
    session_id: str
    status: BacktestStatus = BacktestStatus.PENDING
    progress_pct: float = 0.0
    current_timestamp: Optional[datetime] = None
    current_pnl: float = 0.0
    total_trades: int = 0
    open_positions: int = 0
    equity: float = 0.0
    max_drawdown_pct: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "progress_pct": round(self.progress_pct, 2),
            "current_timestamp": self.current_timestamp.isoformat() if self.current_timestamp else None,
            "current_pnl": round(self.current_pnl, 2),
            "total_trades": self.total_trades,
            "open_positions": self.open_positions,
            "equity": round(self.equity, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        }


@dataclass
class TradeRecord:
    """Record of a completed trade"""
    trade_id: str
    session_id: str
    symbol: str
    order_type: str
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    pnl: float = 0.0
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    strategy_signal: str = ""


@dataclass
class EquityPoint:
    """Point on the equity curve"""
    timestamp: datetime
    equity: float
    drawdown_pct: float = 0.0
    open_positions: int = 0


@dataclass
class BacktestResult:
    """Final results of a backtest"""
    session_id: str
    symbol: str
    strategy_id: str
    start_date: datetime
    end_date: datetime

    # Performance metrics
    final_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0

    # Equity data
    initial_balance: float = 10000.0
    final_balance: float = 10000.0
    equity_curve: List[EquityPoint] = field(default_factory=list)

    # Trade list
    trades: List[TradeRecord] = field(default_factory=list)

    # Execution stats
    duration_seconds: float = 0.0
    candles_processed: int = 0
    signals_generated: int = 0

    # Status
    status: BacktestStatus = BacktestStatus.COMPLETED
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "symbol": self.symbol,
            "strategy_id": self.strategy_id,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "final_pnl": round(self.final_pnl, 2),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 4),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "initial_balance": self.initial_balance,
            "final_balance": round(self.final_balance, 2),
            "duration_seconds": round(self.duration_seconds, 2),
            "candles_processed": self.candles_processed,
            "signals_generated": self.signals_generated,
            "status": self.status.value,
            "error_message": self.error_message
        }


class BacktestEngine:
    """
    Executes backtests by processing historical data through a strategy.

    Features:
    - Process historical market data candle-by-candle
    - Evaluate strategy conditions and generate signals
    - Execute trades via BacktestOrderManager
    - Track P&L, equity curve, and drawdown
    - Store results to database
    - Broadcast progress via WebSocket
    - Support acceleration factor for speed control
    """

    def __init__(
        self,
        session_id: str,
        db_provider: QuestDBProvider,
        event_bus: EventBus,
        logger: Optional[StructuredLogger] = None,
        broadcast_interval: float = 1.0
    ):
        """
        Initialize backtest engine.

        Args:
            session_id: Unique backtest session ID
            db_provider: QuestDB provider for data access
            event_bus: EventBus for signal/event communication
            logger: Optional structured logger
            broadcast_interval: Seconds between progress broadcasts
        """
        self.session_id = session_id
        self.db_provider = db_provider
        self.event_bus = event_bus
        self.logger = logger or get_logger(__name__)
        self.broadcast_interval = broadcast_interval

        # Components initialized during run()
        self.data_provider: Optional[BacktestMarketDataProvider] = None
        self.order_manager: Optional[BacktestOrderManager] = None

        # Configuration loaded from database
        self.config: Optional[BacktestConfig] = None

        # Strategy loaded from database
        self.strategy_config: Optional[Dict[str, Any]] = None

        # Progress tracking
        self.progress = BacktestProgress(session_id=session_id)

        # Trade tracking
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[EquityPoint] = []
        self.peak_equity: float = 0.0

        # Signal tracking
        self._signals_generated = 0
        self._last_broadcast_time = 0.0

        # Control flags
        self._running = False
        self._stop_requested = False

        self.logger.info("backtest_engine.initialized", {
            "session_id": session_id,
            "broadcast_interval": broadcast_interval
        })

    async def load_session_config(self) -> BacktestConfig:
        """
        Load backtest session configuration from database.

        Returns:
            BacktestConfig with session parameters

        Raises:
            ValueError: If session not found
        """
        query = """
            SELECT session_id, strategy_id, symbol, start_date, end_date,
                   acceleration_factor, initial_balance, status
            FROM backtest_sessions
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """

        result = await self.db_provider.execute_query(query, [self.session_id])

        if not result:
            raise ValueError(f"Backtest session not found: {self.session_id}")

        row = result[0]

        config = BacktestConfig(
            session_id=row["session_id"],
            strategy_id=row["strategy_id"],
            symbol=row["symbol"],
            start_date=row["start_date"] if isinstance(row["start_date"], datetime) else datetime.fromisoformat(str(row["start_date"])),
            end_date=row["end_date"] if isinstance(row["end_date"], datetime) else datetime.fromisoformat(str(row["end_date"])),
            acceleration_factor=row.get("acceleration_factor", 10),
            initial_balance=row.get("initial_balance", 10000.0)
        )

        self.logger.info("backtest_engine.config_loaded", {
            "session_id": config.session_id,
            "strategy_id": config.strategy_id,
            "symbol": config.symbol,
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat()
        })

        return config

    async def load_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """
        Load strategy configuration from database.

        Args:
            strategy_id: Strategy ID to load

        Returns:
            Strategy configuration dict

        Raises:
            ValueError: If strategy not found
        """
        query = """
            SELECT strategy_id, name, config, enabled
            FROM strategies
            WHERE strategy_id = $1
            ORDER BY timestamp DESC
            LIMIT 1
        """

        result = await self.db_provider.execute_query(query, [strategy_id])

        if not result:
            # Try loading from default/template strategies
            self.logger.warning("backtest_engine.strategy_not_found_trying_default", {
                "strategy_id": strategy_id
            })
            return self._get_default_strategy(strategy_id)

        row = result[0]
        config = row.get("config", {})

        # Parse config if it's a string
        if isinstance(config, str):
            import json
            config = json.loads(config)

        self.logger.info("backtest_engine.strategy_loaded", {
            "strategy_id": strategy_id,
            "name": row.get("name", strategy_id)
        })

        return config

    def _get_default_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """
        Get a default/test strategy configuration.

        Used when strategy is not found in database.
        """
        return {
            "strategy_id": strategy_id,
            "name": f"Default Strategy ({strategy_id})",
            "signal_detection": {
                "conditions": [
                    {"type": "price_momentum", "operator": "gte", "value": 0.5}
                ]
            },
            "entry_conditions": {
                "conditions": []
            },
            "exit_conditions": {
                "conditions": [
                    {"type": "take_profit_pct", "operator": "gte", "value": 2.0},
                    {"type": "stop_loss_pct", "operator": "gte", "value": 1.0}
                ]
            }
        }

    async def update_session_status(
        self,
        status: BacktestStatus,
        progress_pct: float = 0.0,
        current_timestamp: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update session status in database.

        Args:
            status: New session status
            progress_pct: Progress percentage (0-100)
            current_timestamp: Current timestamp being processed
            error_message: Error message if failed
        """
        # Build update query
        update_parts = ["status = $2", "progress_pct = $3"]
        params = [self.session_id, status.value, progress_pct]
        param_idx = 4

        if current_timestamp:
            update_parts.append(f"current_timestamp = ${param_idx}")
            params.append(current_timestamp)
            param_idx += 1

        if status == BacktestStatus.COMPLETED:
            update_parts.append(f"completed_at = ${param_idx}")
            params.append(datetime.now(timezone.utc))
            param_idx += 1

            # Add final metrics
            update_parts.append(f"final_pnl = ${param_idx}")
            params.append(self.progress.current_pnl)
            param_idx += 1

            update_parts.append(f"total_trades = ${param_idx}")
            params.append(self.progress.total_trades)
            param_idx += 1

            win_rate = 0.0
            if self.trades:
                winning = sum(1 for t in self.trades if t.pnl > 0)
                win_rate = winning / len(self.trades) if self.trades else 0.0
            update_parts.append(f"win_rate = ${param_idx}")
            params.append(win_rate)
            param_idx += 1

        if error_message:
            update_parts.append(f"error_message = ${param_idx}")
            params.append(error_message)
            param_idx += 1

        query = f"""
            UPDATE backtest_sessions
            SET {', '.join(update_parts)}
            WHERE session_id = $1
        """

        try:
            await self.db_provider.execute(query, *params)
        except Exception as e:
            # Log but don't fail - session status is not critical
            self.logger.warning("backtest_engine.status_update_failed", {
                "session_id": self.session_id,
                "status": status.value,
                "error": str(e)
            })

    async def broadcast_progress(self, force: bool = False) -> None:
        """
        Broadcast progress update via EventBus.

        Args:
            force: If True, broadcast immediately regardless of interval
        """
        now = time.time()

        # Throttle broadcasts unless forced
        if not force and (now - self._last_broadcast_time) < self.broadcast_interval:
            return

        self._last_broadcast_time = now

        # Build WebSocket message
        message = {
            "type": "backtest.progress",
            "data": self.progress.to_dict()
        }

        # Publish to EventBus
        await self.event_bus.publish("backtest.progress", message)

        self.logger.debug("backtest_engine.progress_broadcast", {
            "session_id": self.session_id,
            "progress_pct": self.progress.progress_pct,
            "current_pnl": self.progress.current_pnl
        })

    async def broadcast_completed(self, result: BacktestResult) -> None:
        """
        Broadcast backtest completion event.

        Args:
            result: Final backtest result
        """
        message = {
            "type": "backtest.completed",
            "data": {
                "session_id": self.session_id,
                "final_pnl": result.final_pnl,
                "total_trades": result.total_trades,
                "win_rate": result.win_rate,
                "duration_seconds": result.duration_seconds
            }
        }

        await self.event_bus.publish("backtest.completed", message)

        self.logger.info("backtest_engine.completed_broadcast", {
            "session_id": self.session_id,
            "final_pnl": result.final_pnl
        })

    async def broadcast_failed(self, error: str) -> None:
        """
        Broadcast backtest failure event.

        Args:
            error: Error message
        """
        message = {
            "type": "backtest.failed",
            "data": {
                "session_id": self.session_id,
                "error": error
            }
        }

        await self.event_bus.publish("backtest.failed", message)

        self.logger.error("backtest_engine.failed_broadcast", {
            "session_id": self.session_id,
            "error": error
        })

    def _evaluate_entry_signal(
        self,
        candle_data: Dict[str, Any],
        indicator_values: Dict[str, float]
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate strategy conditions for entry signal.

        Simple implementation - checks if price momentum is positive.
        In production, this would use the full StrategyManager.

        Args:
            candle_data: Current candle OHLCV data
            indicator_values: Current indicator values

        Returns:
            Signal dict if conditions met, None otherwise
        """
        # Simple momentum-based entry logic for demo
        # Calculate simple price momentum from candle
        price_change_pct = 0.0
        if candle_data.get("open", 0) > 0:
            price_change_pct = ((candle_data.get("close", 0) - candle_data.get("open", 0))
                               / candle_data.get("open", 0)) * 100

        # Volume surge check
        volume = candle_data.get("volume", 0)
        avg_volume = indicator_values.get("avg_volume", volume)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0

        # Entry condition: positive momentum + volume surge
        # BUG-DV-003 FIX: Use UPPERCASE for consistency with MEXC API
        if price_change_pct > 0.1 and volume_ratio > 1.5:
            return {
                "signal_type": "S1",
                "side": "BUY",
                "price": candle_data.get("close", 0),
                "quantity": self.config.initial_balance * 0.02 / candle_data.get("close", 1),  # 2% of balance
                "reason": f"Price momentum {price_change_pct:.2f}%, Volume ratio {volume_ratio:.2f}"
            }

        return None

    def _evaluate_exit_signal(
        self,
        candle_data: Dict[str, Any],
        position: PositionRecord
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate exit conditions for open position.

        Args:
            candle_data: Current candle OHLCV data
            position: Current open position

        Returns:
            Exit signal dict if conditions met, None otherwise
        """
        if position.quantity == 0:
            return None

        current_price = candle_data.get("close", 0)

        # Update unrealized P&L
        position.update_unrealized_pnl(current_price)

        # Check stop loss
        # BUG-DV-003 FIX: Use UPPERCASE for consistency with MEXC API
        if position.unrealized_pnl_pct <= -self.config.stop_loss_percent:
            return {
                "signal_type": "E1",
                "side": "SELL" if position.quantity > 0 else "COVER",
                "price": current_price,
                "quantity": abs(position.quantity),
                "reason": f"Stop loss triggered at {position.unrealized_pnl_pct:.2f}%"
            }

        # Check take profit
        # BUG-DV-003 FIX: Use UPPERCASE for consistency with MEXC API
        if position.unrealized_pnl_pct >= self.config.take_profit_percent:
            return {
                "signal_type": "ZE1",
                "side": "SELL" if position.quantity > 0 else "COVER",
                "price": current_price,
                "quantity": abs(position.quantity),
                "reason": f"Take profit triggered at {position.unrealized_pnl_pct:.2f}%"
            }

        return None

    async def _process_signal(
        self,
        signal: Dict[str, Any],
        timestamp: datetime
    ) -> Optional[str]:
        """
        Process a trading signal through BacktestOrderManager.

        Args:
            signal: Signal dict with type, side, price, quantity
            timestamp: Signal timestamp

        Returns:
            Order ID if executed, None if failed
        """
        try:
            # BUG-DV-003 FIX: Normalize to UPPERCASE for consistency with MEXC API
            side = signal.get("side", "BUY").upper()

            if side == "BUY":
                order_type = OrderType.BUY
            elif side == "SELL":
                order_type = OrderType.SELL
            elif side == "SHORT":
                order_type = OrderType.SHORT
            elif side == "COVER":
                order_type = OrderType.COVER
            else:
                self.logger.warning("backtest_engine.invalid_signal_side", {"side": side})
                return None

            order_id = await self.order_manager.submit_order(
                symbol=self.config.symbol,
                order_type=order_type,
                quantity=signal.get("quantity", 0),
                price=signal.get("price", 0),
                strategy_name=self.config.strategy_id
            )

            self._signals_generated += 1

            self.logger.info("backtest_engine.signal_executed", {
                "session_id": self.session_id,
                "order_id": order_id,
                "signal_type": signal.get("signal_type"),
                "side": side,
                "price": signal.get("price")
            })

            return order_id

        except Exception as e:
            self.logger.error("backtest_engine.signal_execution_failed", {
                "session_id": self.session_id,
                "signal": signal,
                "error": str(e)
            })
            return None

    def _record_equity_point(self, timestamp: datetime, positions: List[Dict]) -> None:
        """
        Record a point on the equity curve.

        Args:
            timestamp: Current timestamp
            positions: Current positions list
        """
        # Calculate current equity
        total_unrealized_pnl = sum(p.get("unrealized_pnl", 0) for p in positions)
        realized_pnl = self.progress.current_pnl
        current_equity = self.config.initial_balance + realized_pnl + total_unrealized_pnl

        # Update peak equity and drawdown
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        drawdown_pct = 0.0
        if self.peak_equity > 0:
            drawdown_pct = ((self.peak_equity - current_equity) / self.peak_equity) * 100

        if drawdown_pct > self.progress.max_drawdown_pct:
            self.progress.max_drawdown_pct = drawdown_pct

        # Store equity point
        point = EquityPoint(
            timestamp=timestamp,
            equity=current_equity,
            drawdown_pct=drawdown_pct,
            open_positions=len([p for p in positions if p.get("quantity", 0) != 0])
        )
        self.equity_curve.append(point)

        # Update progress
        self.progress.equity = current_equity
        self.progress.open_positions = point.open_positions

    async def _store_trade(self, trade: TradeRecord) -> None:
        """
        Store completed trade to database.

        Args:
            trade: Trade record to store
        """
        try:
            query = """
                INSERT INTO backtest_trades (
                    trade_id, session_id, symbol, order_type, quantity,
                    entry_price, exit_price, pnl, entry_time, exit_time,
                    strategy_signal, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """

            await self.db_provider.execute(
                query,
                trade.trade_id,
                trade.session_id,
                trade.symbol,
                trade.order_type,
                trade.quantity,
                trade.entry_price,
                trade.exit_price,
                trade.pnl,
                trade.entry_time,
                trade.exit_time,
                trade.strategy_signal,
                datetime.now(timezone.utc)
            )
        except Exception as e:
            # Log but don't fail - trade storage is not critical for execution
            self.logger.warning("backtest_engine.trade_storage_failed", {
                "trade_id": trade.trade_id,
                "error": str(e)
            })

    async def _store_equity_curve(self) -> None:
        """Store equity curve points to database."""
        if not self.equity_curve:
            return

        try:
            # Sample equity curve to reduce storage (every 10th point)
            sampled = self.equity_curve[::10]
            if self.equity_curve[-1] not in sampled:
                sampled.append(self.equity_curve[-1])

            for point in sampled:
                query = """
                    INSERT INTO backtest_equity_curve (
                        session_id, timestamp, equity, drawdown_pct, open_positions
                    ) VALUES ($1, $2, $3, $4, $5)
                """

                await self.db_provider.execute(
                    query,
                    self.session_id,
                    point.timestamp,
                    point.equity,
                    point.drawdown_pct,
                    point.open_positions
                )
        except Exception as e:
            self.logger.warning("backtest_engine.equity_curve_storage_failed", {
                "session_id": self.session_id,
                "error": str(e)
            })

    async def run(self) -> BacktestResult:
        """
        Execute the backtest and return results.

        Main execution loop:
        1. Load configuration
        2. Initialize components
        3. Process historical data
        4. Generate signals and execute trades
        5. Track P&L and equity
        6. Store results

        Returns:
            BacktestResult with all metrics and trade data
        """
        start_time = time.time()
        self._running = True
        self._stop_requested = False

        try:
            # 1. Load session configuration
            self.config = await self.load_session_config()

            # 2. Update status to running
            self.progress.status = BacktestStatus.RUNNING
            self.progress.started_at = datetime.now(timezone.utc)
            self.peak_equity = self.config.initial_balance
            self.progress.equity = self.config.initial_balance

            await self.update_session_status(
                BacktestStatus.RUNNING,
                progress_pct=0.0
            )

            # 3. Initialize data provider
            self.data_provider = BacktestMarketDataProvider(self.db_provider)
            await self.data_provider.initialize()

            # 4. Initialize order manager
            self.order_manager = BacktestOrderManager(
                logger=self.logger,
                event_bus=self.event_bus,
                slippage_pct=0.0  # No slippage for backtests
            )
            await self.order_manager.start()

            # 5. Load strategy
            self.strategy_config = await self.load_strategy(self.config.strategy_id)

            # 6. Get historical data
            candles = await self.data_provider.get_price_range(
                symbol=self.config.symbol,
                start_time=self.config.start_date,
                end_time=self.config.end_date,
                timeframe=self.config.timeframe
            )

            if not candles:
                raise ValueError(f"No historical data found for {self.config.symbol} "
                               f"from {self.config.start_date} to {self.config.end_date}")

            self.logger.info("backtest_engine.data_loaded", {
                "session_id": self.session_id,
                "candle_count": len(candles),
                "first_candle": candles[0].timestamp.isoformat(),
                "last_candle": candles[-1].timestamp.isoformat()
            })

            # 7. Process candles
            total_candles = len(candles)
            candles_processed = 0

            # Running average volume for indicator
            volume_sum = 0.0
            volume_count = 0

            for candle in candles:
                if self._stop_requested:
                    self.logger.info("backtest_engine.stop_requested", {
                        "session_id": self.session_id,
                        "candles_processed": candles_processed
                    })
                    break

                # Convert candle to dict
                candle_data = {
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume
                }

                # Update running average volume
                volume_sum += candle.volume
                volume_count += 1
                avg_volume = volume_sum / volume_count if volume_count > 0 else candle.volume

                indicator_values = {
                    "avg_volume": avg_volume,
                    "price": candle.close
                }

                # Update current price in data provider
                self.data_provider.update_current_price(candle.symbol, candle.close)

                # Get current positions
                positions = await self.order_manager.get_all_positions()

                # Check for exit signals on open positions
                for position_dict in positions:
                    if position_dict.get("quantity", 0) != 0:
                        position = PositionRecord(
                            symbol=position_dict["symbol"],
                            quantity=position_dict["quantity"],
                            average_price=position_dict["average_price"],
                            leverage=position_dict.get("leverage", 1.0)
                        )

                        exit_signal = self._evaluate_exit_signal(candle_data, position)
                        if exit_signal:
                            order_id = await self._process_signal(exit_signal, candle.timestamp)
                            if order_id:
                                # Record trade
                                trade = TradeRecord(
                                    trade_id=f"trade_{uuid4().hex[:8]}",
                                    session_id=self.session_id,
                                    symbol=candle.symbol,
                                    order_type=exit_signal["side"],
                                    quantity=exit_signal["quantity"],
                                    entry_price=position.average_price,
                                    exit_price=exit_signal["price"],
                                    pnl=position.unrealized_pnl,
                                    entry_time=None,  # Would need to track from entry
                                    exit_time=candle.timestamp,
                                    strategy_signal=exit_signal.get("signal_type", "")
                                )
                                self.trades.append(trade)
                                await self._store_trade(trade)

                                self.progress.current_pnl += trade.pnl
                                self.progress.total_trades += 1

                # Refresh positions after exits
                positions = await self.order_manager.get_all_positions()

                # Check for entry signals if no open position
                open_positions = [p for p in positions if p.get("quantity", 0) != 0]
                if not open_positions:
                    entry_signal = self._evaluate_entry_signal(candle_data, indicator_values)
                    if entry_signal:
                        await self._process_signal(entry_signal, candle.timestamp)

                # Record equity point
                self._record_equity_point(candle.timestamp, await self.order_manager.get_all_positions())

                # Update progress
                candles_processed += 1
                self.progress.progress_pct = (candles_processed / total_candles) * 100
                self.progress.current_timestamp = candle.timestamp

                # Broadcast progress periodically
                await self.broadcast_progress()

                # Apply acceleration factor (optional sleep)
                if self.config.acceleration_factor < 100:
                    # Real-time simulation would sleep here
                    # For backtests, we typically run at max speed
                    pass

            # 8. Close any remaining positions at end
            # BUG-DV-003 FIX: Use UPPERCASE for consistency with MEXC API
            final_positions = await self.order_manager.get_all_positions()
            for position_dict in final_positions:
                if position_dict.get("quantity", 0) != 0:
                    close_signal = {
                        "signal_type": "CLOSE",
                        "side": "SELL" if position_dict["quantity"] > 0 else "COVER",
                        "price": candles[-1].close if candles else 0,
                        "quantity": abs(position_dict["quantity"]),
                        "reason": "End of backtest period"
                    }
                    await self._process_signal(close_signal, candles[-1].timestamp if candles else datetime.now(timezone.utc))

            # 9. Calculate final metrics
            duration_seconds = time.time() - start_time

            winning_trades = sum(1 for t in self.trades if t.pnl > 0)
            losing_trades = sum(1 for t in self.trades if t.pnl < 0)
            win_rate = winning_trades / len(self.trades) if self.trades else 0.0

            result = BacktestResult(
                session_id=self.session_id,
                symbol=self.config.symbol,
                strategy_id=self.config.strategy_id,
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                final_pnl=self.progress.current_pnl,
                total_trades=len(self.trades),
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                max_drawdown_pct=self.progress.max_drawdown_pct,
                initial_balance=self.config.initial_balance,
                final_balance=self.config.initial_balance + self.progress.current_pnl,
                equity_curve=self.equity_curve,
                trades=self.trades,
                duration_seconds=duration_seconds,
                candles_processed=candles_processed,
                signals_generated=self._signals_generated,
                status=BacktestStatus.COMPLETED if not self._stop_requested else BacktestStatus.STOPPED
            )

            # 10. Update final status
            self.progress.status = result.status
            self.progress.completed_at = datetime.now(timezone.utc)

            await self.update_session_status(
                result.status,
                progress_pct=100.0
            )

            # 11. Store equity curve
            await self._store_equity_curve()

            # 12. Broadcast completion
            await self.broadcast_progress(force=True)
            await self.broadcast_completed(result)

            self.logger.info("backtest_engine.completed", {
                "session_id": self.session_id,
                "duration_seconds": duration_seconds,
                "candles_processed": candles_processed,
                "total_trades": len(self.trades),
                "final_pnl": self.progress.current_pnl
            })

            return result

        except Exception as e:
            # Handle errors gracefully
            error_message = f"{type(e).__name__}: {str(e)}"

            self.logger.error("backtest_engine.failed", {
                "session_id": self.session_id,
                "error": error_message
            })

            self.progress.status = BacktestStatus.FAILED
            self.progress.error_message = error_message

            await self.update_session_status(
                BacktestStatus.FAILED,
                error_message=error_message
            )

            await self.broadcast_failed(error_message)

            return BacktestResult(
                session_id=self.session_id,
                symbol=self.config.symbol if self.config else "",
                strategy_id=self.config.strategy_id if self.config else "",
                start_date=self.config.start_date if self.config else datetime.now(timezone.utc),
                end_date=self.config.end_date if self.config else datetime.now(timezone.utc),
                status=BacktestStatus.FAILED,
                error_message=error_message,
                duration_seconds=time.time() - start_time
            )

        finally:
            self._running = False

            # Cleanup
            if self.order_manager:
                await self.order_manager.stop()
            if self.data_provider:
                await self.data_provider.close()

    def stop(self) -> None:
        """
        Request graceful stop of backtest execution.
        """
        self._stop_requested = True
        self.logger.info("backtest_engine.stop_requested", {
            "session_id": self.session_id
        })

    @property
    def is_running(self) -> bool:
        """Check if backtest is currently running."""
        return self._running


async def run_backtest(
    session_id: str,
    db_provider: QuestDBProvider,
    event_bus: EventBus
) -> BacktestResult:
    """
    Convenience function to run a backtest.

    Args:
        session_id: Backtest session ID
        db_provider: QuestDB provider
        event_bus: EventBus for communication

    Returns:
        BacktestResult with metrics and trade data
    """
    engine = BacktestEngine(
        session_id=session_id,
        db_provider=db_provider,
        event_bus=event_bus
    )

    return await engine.run()
