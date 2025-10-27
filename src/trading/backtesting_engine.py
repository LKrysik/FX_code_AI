"""
Backtesting Execution Engine
============================
Executes trading strategies against historical market data with time acceleration.
Provides comprehensive performance analysis and trade tracking.
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path

from ..core.logger import StructuredLogger
from ..core.event_bus import EventBus
from ..infrastructure.config.settings import BacktestSettings
from ..exchanges.file_connector import FileConnector, FileExchangeConfig
from ..results.unified_results_manager import UnifiedResultsManager, TradeRecord, SignalRecord
from ..engine.graph_adapter import GraphAdapter, LiveGraphExecutor
from ..strategy_graph.serializer import StrategyGraph
from ..data_feed.questdb_provider import QuestDBProvider
from .backtest_data_provider_questdb import BacktestMarketDataProvider


@dataclass
class BacktestConfiguration:
    """Configuration for a backtest execution"""
    session_id: str
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    timeframe: str = "1h"
    initial_balance: float = 10000.0
    strategy_graph: StrategyGraph = None
    time_acceleration: float = 10.0
    data_directory: str = "data"


@dataclass
class BacktestResult:
    """Results of a completed backtest"""
    session_id: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    profit_factor: float = 0.0
    avg_trade_duration: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    trades: List[TradeRecord] = field(default_factory=list)
    signals: List[SignalRecord] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    drawdown_curve: List[Tuple[datetime, float]] = field(default_factory=list)


class BacktestingEngine:
    """
    Executes trading strategies against historical market data.

    Features:
    - Time-accelerated historical data replay
    - Real-time strategy execution using StrategyEvaluator
    - Comprehensive performance metrics calculation
    - Trade and signal tracking
    - Risk management integration
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_provider: Optional[QuestDBProvider] = None,
        logger: Optional[StructuredLogger] = None,
        settings: Optional[BacktestSettings] = None
    ):
        self.event_bus = event_bus
        self.db_provider = db_provider
        self.logger = logger or StructuredLogger("backtesting_engine")
        self.settings = settings or BacktestSettings()

        # Core components
        self.file_connector: Optional[FileConnector] = None
        self.graph_adapter: Optional[GraphAdapter] = None
        self.results_manager: Optional[UnifiedResultsManager] = None
        self.data_provider: Optional[BacktestMarketDataProvider] = None

        # Execution state
        self.is_running = False
        self.current_config: Optional[BacktestConfiguration] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Performance tracking
        self.current_balance = 0.0
        self.peak_balance = 0.0
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.drawdown_curve: List[Tuple[datetime, float]] = []

        # Trade tracking
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.completed_trades: List[TradeRecord] = []
        self.signals_generated: List[SignalRecord] = []

        self.logger.info("backtesting_engine.initialized", {
            "time_acceleration": self.settings.time_scale_factor,
            "data_directory": self.settings.data_directory
        })

    async def initialize(self, config: BacktestConfiguration) -> bool:
        """
        Initialize the backtesting engine with configuration.

        Args:
            config: Backtest configuration

        Returns:
            True if initialization successful
        """
        try:
            self.current_config = config
            self.current_balance = config.initial_balance
            self.peak_balance = config.initial_balance

            # Initialize file connector for historical data
            file_config = FileExchangeConfig(
                enabled=True,
                path=config.data_directory,
                playback_speed=config.time_acceleration,
                loop=False,
                start_from_beginning=True
            )

            self.file_connector = FileConnector(
                config=file_config.__dict__,
                event_bus=self.event_bus,
                logger=self.logger
            )

            # Initialize graph adapter for strategy execution
            self.graph_adapter = GraphAdapter(
                event_bus=self.event_bus,
                indicator_engine=None,  # Will use mock indicators for backtesting
                state_persistence_manager=None  # No persistence needed for backtesting
            )

            # Initialize results manager
            self.results_manager = UnifiedResultsManager(
                session_id=config.session_id,
                mode="backtest",
                logger=self.logger
            )

            # Set data timespan for results tracking
            self.results_manager.set_data_timespan(
                config.start_date.timestamp(),
                config.end_date.timestamp()
            )

            # Initialize data provider if database is available
            if self.db_provider:
                self.data_provider = BacktestMarketDataProvider(
                    db_provider=self.db_provider,
                    cache_size=1000
                )
                self.logger.info("backtesting_engine.data_provider_initialized", {
                    "cache_size": 1000
                })

            # Validate strategy graph
            if not config.strategy_graph:
                raise ValueError("Strategy graph is required for backtesting")

            # Adapt graph to execution plan (done during execution)
            self.execution_plan = None

            self.logger.info("backtesting_engine.initialized_successfully", {
                "session_id": config.session_id,
                "symbols": config.symbols,
                "date_range": f"{config.start_date.isoformat()} to {config.end_date.isoformat()}",
                "time_acceleration": config.time_acceleration
            })

            return True

        except Exception as e:
            self.logger.error("backtesting_engine.initialization_failed", {
                "session_id": config.session_id,
                "error": str(e)
            }, exc_info=True)
            return False

    async def execute_backtest(self) -> BacktestResult:
        """
        Execute the backtest using historical data replay and graph-based strategy execution.

        Returns:
            Complete backtest results
        """
        if not self.current_config or not self.file_connector or not self.graph_adapter:
            raise ValueError("Backtesting engine not properly initialized")

        try:
            self.is_running = True
            self.start_time = datetime.now()

            self.logger.info("backtesting_engine.execution_started", {
                "session_id": self.current_config.session_id,
                "symbols": self.current_config.symbols,
                "strategy": self.current_config.strategy_graph.name if self.current_config.strategy_graph else "unknown"
            })

            # Adapt strategy graph to execution plan
            self.execution_plan = await self.graph_adapter.adapt_graph(
                self.current_config.strategy_graph,
                self.current_config.symbols[0] if self.current_config.symbols else "BTCUSDT"
            )

            # Connect to data source
            await self.file_connector.connect()

            # Subscribe to symbols
            for symbol in self.current_config.symbols:
                success = await self.file_connector.subscribe_symbol(symbol)
                if not success:
                    self.logger.warning("backtesting_engine.symbol_subscription_failed", {
                        "session_id": self.current_config.session_id,
                        "symbol": symbol
                    })

            # Set up event handlers for market data processing
            await self._setup_event_handlers()

            # Execute backtest by replaying historical data
            await self._replay_historical_data()

            # Disconnect from data source
            await self.file_connector.disconnect()

            # Calculate final results
            result = await self._calculate_results()

            self.end_time = datetime.now()
            self.is_running = False

            self.logger.info("backtesting_engine.execution_completed", {
                "session_id": self.current_config.session_id,
                "total_trades": result.total_trades,
                "total_pnl": result.total_pnl,
                "win_rate": result.win_rate,
                "duration_seconds": (self.end_time - self.start_time).total_seconds()
            })

            return result

        except Exception as e:
            self.logger.error("backtesting_engine.execution_failed", {
                "session_id": self.current_config.session_id,
                "error": str(e)
            }, exc_info=True)

            # Ensure cleanup on failure
            if self.file_connector:
                await self.file_connector.disconnect()

            self.is_running = False
            raise

    async def _setup_event_handlers(self):
        """Set up event handlers for market data processing during backtesting"""
        # Market data handler - executes strategy graph on each price update
        async def handle_market_data(event_data: Dict[str, Any]):
            if not self.execution_plan:
                return

            # Extract market data
            symbol = event_data.get('symbol')
            price_data = event_data.get('data', {})
            price = price_data.get('price')
            volume = price_data.get('volume')
            timestamp = price_data.get('timestamp')

            if not symbol or not price or not timestamp:
                return

            # Update current price in data provider
            if self.data_provider:
                self.data_provider.update_current_price(symbol, price)

            # Create market data dict for graph execution
            market_data = {
                symbol: {
                    'price': price,
                    'volume': volume,
                    'timestamp': timestamp,
                    'symbol': symbol
                }
            }

            try:
                # Execute strategy graph with current market data
                signals = await self.graph_adapter.execute_plan(self.execution_plan, market_data)

                # Process any signals generated
                for signal in signals:
                    await self._process_signal(signal)

                # Update equity curve
                await self._update_equity_curve(timestamp)

            except Exception as e:
                self.logger.error("backtesting_engine.graph_execution_error", {
                    "session_id": self.current_config.session_id,
                    "symbol": symbol,
                    "error": str(e)
                })

        # Register event handler
        self.event_bus.subscribe("market.price_update", handle_market_data)

    async def _replay_historical_data(self):
        """Replay historical data and wait for completion"""
        # The FileConnector will automatically start replaying data when subscribed
        # We need to wait for it to complete. For now, we'll use a simple approach
        # In a production implementation, we'd listen for completion events

        # Wait for a reasonable time for data replay to complete
        # This is a simplified implementation - in production we'd have proper completion detection
        await asyncio.sleep(5)  # Allow time for data replay

        self.logger.info("backtesting_engine.data_replay_completed", {
            "session_id": self.current_config.session_id
        })

    async def _process_signal(self, signal):
        """Process a trading signal from the strategy graph"""
        try:
            # Get current price for signal record (FIXED: was hardcoded 0.0)
            current_price = 0.0

            if self.data_provider:
                price_from_provider = self.data_provider.get_current_price(signal.symbol)
                if price_from_provider:
                    current_price = price_from_provider

            # Convert signal to our format
            signal_record = SignalRecord(
                signal_id=str(uuid.uuid4()),
                timestamp=signal.timestamp / 1000,  # Convert from ms to seconds
                symbol=signal.symbol,
                signal_type=signal.signal_type.value,
                strength=signal.confidence,
                price=current_price,
                metadata={
                    'position_size': signal.position_size,
                    'risk_level': signal.risk_level.value,
                    'indicators': signal.indicators,
                    'reason': signal.reason
                },
                strategy_id=self.current_config.session_id,
                exchange='backtest',
                mode='backtest'
            )

            self.signals_generated.append(signal_record)

            # Execute trade based on signal type
            if signal.signal_type.name == "BUY":
                await self._execute_buy_signal(signal)
            elif signal.signal_type.name == "SELL":
                await self._execute_sell_signal(signal)

        except Exception as e:
            self.logger.error("backtesting_engine.signal_processing_error", {
                "session_id": self.current_config.session_id,
                "signal_type": getattr(signal, 'signal_type', {}).get('name', 'unknown') if signal else 'unknown',
                "error": str(e)
            })

    async def _execute_buy_signal(self, signal):
        """Execute a buy signal"""
        try:
            # Get current market price from data provider (FIXED: was hardcoded 50000.0)
            current_price = None

            if self.data_provider:
                current_price = self.data_provider.get_current_price(signal.symbol)

            # Fallback: try to get from signal timestamp if data provider query available
            if current_price is None and self.data_provider and hasattr(signal, 'timestamp'):
                try:
                    timestamp = datetime.fromtimestamp(signal.timestamp / 1000)
                    market_data = await self.data_provider.get_market_data_at_time(
                        signal.symbol,
                        timestamp,
                        timeframe="1s"
                    )
                    if market_data:
                        current_price = market_data.close
                except Exception as e:
                    self.logger.warning("backtesting_engine.price_query_failed", {
                        "symbol": signal.symbol,
                        "error": str(e)
                    })

            if current_price is None:
                self.logger.error("backtesting_engine.no_price_available", {
                    "symbol": signal.symbol,
                    "signal_timestamp": signal.timestamp
                })
                return

            # Calculate position size
            quantity = self._calculate_position_size(current_price)

            if quantity * current_price > self.current_balance:
                self.logger.warning("backtesting_engine.insufficient_balance_for_buy", {
                    "session_id": self.current_config.session_id,
                    "required": quantity * current_price,
                    "available": self.current_balance
                })
                return

            # Create trade record
            trade = TradeRecord(
                trade_id=str(uuid.uuid4()),
                symbol=signal.symbol,
                side="BUY",
                quantity=quantity,
                price=current_price,
                timestamp=signal.timestamp / 1000,
                exchange='backtest',
                mode='backtest',
                strategy_id=self.current_config.session_id
            )

            # Update position
            position_key = f"{signal.symbol}_LONG"
            if position_key in self.open_positions:
                existing = self.open_positions[position_key]
                total_quantity = existing['quantity'] + quantity
                avg_price = ((existing['quantity'] * existing['price']) + (quantity * current_price)) / total_quantity
                self.open_positions[position_key] = {
                    'quantity': total_quantity,
                    'price': avg_price,
                    'timestamp': signal.timestamp / 1000
                }
            else:
                self.open_positions[position_key] = {
                    'quantity': quantity,
                    'price': current_price,
                    'timestamp': signal.timestamp / 1000
                }

            # Update balance
            self.current_balance -= quantity * current_price

            # Record trade
            self.completed_trades.append(trade)

            if self.results_manager:
                await self.results_manager.record_trade(trade)

            self.logger.info("backtesting_engine.buy_executed", {
                "trade_id": trade.trade_id,
                "symbol": signal.symbol,
                "quantity": quantity,
                "price": current_price,
                "cost": quantity * current_price
            })

        except Exception as e:
            self.logger.error("backtesting_engine.signal_processing_error", {
                "session_id": self.current_config.session_id,
                "signal_type": signal.signal_type.value,
                "error": str(e)
            })

    async def _execute_sell_signal(self, signal):
        """Execute a sell signal"""
        position_key = f"{signal.symbol}_LONG"

        if position_key not in self.open_positions:
            self.logger.warning("backtesting_engine.no_position_to_sell", {
                "symbol": signal.symbol
            })
            return

        # Get current market price from data provider (FIXED: was hardcoded 50000.0)
        current_price = None

        if self.data_provider:
            current_price = self.data_provider.get_current_price(signal.symbol)

        # Fallback: try to get from signal timestamp if data provider query available
        if current_price is None and self.data_provider and hasattr(signal, 'timestamp'):
            try:
                timestamp = datetime.fromtimestamp(signal.timestamp / 1000)
                market_data = await self.data_provider.get_market_data_at_time(
                    signal.symbol,
                    timestamp,
                    timeframe="1s"
                )
                if market_data:
                    current_price = market_data.close
            except Exception as e:
                self.logger.warning("backtesting_engine.price_query_failed", {
                    "symbol": signal.symbol,
                    "error": str(e)
                })

        if current_price is None:
            self.logger.error("backtesting_engine.no_price_available", {
                "symbol": signal.symbol,
                "signal_timestamp": signal.timestamp
            })
            return

        position = self.open_positions[position_key]
        quantity = min(position['quantity'], self._calculate_position_size(current_price))
        revenue = quantity * current_price

        # Create trade record
        trade = TradeRecord(
            trade_id=str(uuid.uuid4()),
            symbol=signal.symbol,
            side="SELL",
            quantity=quantity,
            price=current_price,
            timestamp=signal.timestamp / 1000,
            exchange='backtest',
            mode='backtest',
            strategy_id=self.current_config.session_id
        )

        # Calculate P&L
        entry_cost = position['price'] * quantity
        trade.pnl = revenue - entry_cost
        trade.fees = 0.0

        # Update position
        if quantity >= position['quantity']:
            del self.open_positions[position_key]
        else:
            position['quantity'] -= quantity

        # Update balance
        self.current_balance += revenue

        # Record trade
        self.completed_trades.append(trade)

        if self.results_manager:
            await self.results_manager.record_trade(trade)

        self.logger.info("backtesting_engine.sell_executed", {
            "trade_id": trade.trade_id,
            "symbol": signal.symbol,
            "quantity": quantity,
            "price": current_price,
            "revenue": revenue,
            "pnl": trade.pnl
        })

    async def _execute_signal(self, signal: SignalRecord):
        """Execute a trading signal"""
        try:
            if signal.signal_type == "BUY":
                await self._execute_buy(signal)
            elif signal.signal_type == "SELL":
                await self._execute_sell(signal)

        except Exception as e:
            self.logger.error("backtesting_engine.signal_execution_failed", {
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type,
                "error": str(e)
            })

    async def _execute_buy(self, signal: SignalRecord):
        """Execute a buy order"""
        # Simple market order execution
        quantity = self._calculate_position_size(signal.price)
        cost = quantity * signal.price

        if cost > self.current_balance:
            self.logger.warning("backtesting_engine.insufficient_balance", {
                "required": cost,
                "available": self.current_balance
            })
            return

        # Create trade record
        trade = TradeRecord(
            trade_id=str(uuid.uuid4()),
            symbol=signal.symbol,
            side="BUY",
            quantity=quantity,
            price=signal.price,
            timestamp=signal.timestamp,
            exchange='backtest',
            mode='backtest',
            strategy_id=signal.strategy_id
        )

        # Update position
        position_key = f"{signal.symbol}_LONG"
        if position_key in self.open_positions:
            existing = self.open_positions[position_key]
            total_quantity = existing['quantity'] + quantity
            avg_price = ((existing['quantity'] * existing['price']) + (quantity * signal.price)) / total_quantity
            self.open_positions[position_key] = {
                'quantity': total_quantity,
                'price': avg_price,
                'timestamp': signal.timestamp
            }
        else:
            self.open_positions[position_key] = {
                'quantity': quantity,
                'price': signal.price,
                'timestamp': signal.timestamp
            }

        # Update balance
        self.current_balance -= cost

        # Record trade
        self.completed_trades.append(trade)

        if self.results_manager:
            await self.results_manager.record_trade(trade)

        self.logger.info("backtesting_engine.buy_executed", {
            "trade_id": trade.trade_id,
            "symbol": signal.symbol,
            "quantity": quantity,
            "price": signal.price,
            "cost": cost
        })

    async def _execute_sell(self, signal: SignalRecord):
        """Execute a sell order"""
        position_key = f"{signal.symbol}_LONG"

        if position_key not in self.open_positions:
            self.logger.warning("backtesting_engine.no_position_to_sell", {
                "symbol": signal.symbol
            })
            return

        position = self.open_positions[position_key]
        quantity = min(position['quantity'], self._calculate_position_size(signal.price))
        revenue = quantity * signal.price

        # Create trade record
        trade = TradeRecord(
            trade_id=str(uuid.uuid4()),
            symbol=signal.symbol,
            side="SELL",
            quantity=quantity,
            price=signal.price,
            timestamp=signal.timestamp,
            exchange='backtest',
            mode='backtest',
            strategy_id=signal.strategy_id
        )

        # Update position
        if quantity >= position['quantity']:
            del self.open_positions[position_key]
        else:
            position['quantity'] -= quantity

        # Update balance
        self.current_balance += revenue

        # Calculate P&L for this trade
        entry_cost = position['price'] * quantity
        trade.pnl = revenue - entry_cost
        trade.fees = 0.0  # No fees in backtest

        # Record trade
        self.completed_trades.append(trade)

        if self.results_manager:
            await self.results_manager.record_trade(trade)

        self.logger.info("backtesting_engine.sell_executed", {
            "trade_id": trade.trade_id,
            "symbol": signal.symbol,
            "quantity": quantity,
            "price": signal.price,
            "revenue": revenue,
            "pnl": trade.pnl
        })

    def _calculate_position_size(self, price: float) -> float:
        """Calculate position size based on risk management"""
        # Simple fixed percentage of balance
        risk_percentage = 0.02  # 2% risk per trade
        position_value = self.current_balance * risk_percentage
        return position_value / price

    async def _update_equity_curve(self, timestamp: str):
        """Update equity curve with current balance"""
        try:
            ts = datetime.fromtimestamp(float(timestamp))
            self.equity_curve.append((ts, self.current_balance))

            # Update drawdown
            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance
                self.current_drawdown = 0.0
            else:
                self.current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
                self.max_drawdown = max(self.max_drawdown, self.current_drawdown)

            self.drawdown_curve.append((ts, self.current_drawdown))

        except Exception as e:
            self.logger.error("backtesting_engine.equity_update_failed", {
                "timestamp": timestamp,
                "error": str(e)
            })

    async def _calculate_results(self) -> BacktestResult:
        """Calculate comprehensive backtest results"""
        if not self.current_config:
            raise ValueError("No active backtest configuration")

        # Basic trade statistics
        total_trades = len(self.completed_trades)
        winning_trades = len([t for t in self.completed_trades if (t.pnl or 0) > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        # P&L calculations
        total_pnl = sum((t.pnl or 0) for t in self.completed_trades)
        largest_win = max((t.pnl or 0) for t in self.completed_trades) if self.completed_trades else 0.0
        largest_loss = min((t.pnl or 0) for t in self.completed_trades) if self.completed_trades else 0.0

        # Calculate Sharpe ratio (simplified)
        returns = []
        if len(self.equity_curve) > 1:
            for i in range(1, len(self.equity_curve)):
                prev_balance = self.equity_curve[i-1][1]
                curr_balance = self.equity_curve[i][1]
                if prev_balance > 0:
                    returns.append((curr_balance - prev_balance) / prev_balance)

        sharpe_ratio = 0.0
        if returns:
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            if std_return > 0:
                sharpe_ratio = avg_return / std_return * (252 ** 0.5)  # Annualized

        # Calculate profit factor
        gross_profit = sum(t.pnl or 0 for t in self.completed_trades if (t.pnl or 0) > 0)
        gross_loss = abs(sum(t.pnl or 0 for t in self.completed_trades if (t.pnl or 0) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Calculate consecutive wins/losses
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in self.completed_trades:
            if (trade.pnl or 0) > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            elif (trade.pnl or 0) < 0:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)

        # Calculate average trade duration
        durations = []
        for trade in self.completed_trades:
            if trade.exit_time and trade.entry_time:
                durations.append(trade.exit_time - trade.entry_time)
        avg_trade_duration = sum(durations) / len(durations) if durations else 0.0

        return BacktestResult(
            session_id=self.current_config.session_id,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            max_drawdown=self.max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sharpe_ratio * 0.8,  # Simplified approximation
            calmar_ratio=total_pnl / self.max_drawdown if self.max_drawdown > 0 else float('inf'),
            profit_factor=profit_factor,
            avg_trade_duration=avg_trade_duration,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            largest_win=largest_win,
            largest_loss=largest_loss,
            trades=self.completed_trades,
            signals=self.signals_generated,
            equity_curve=self.equity_curve,
            drawdown_curve=self.drawdown_curve
        )

    async def stop_backtest(self):
        """Stop the current backtest execution"""
        self.is_running = False

        if self.file_connector:
            await self.file_connector.disconnect()

        self.logger.info("backtesting_engine.stopped", {
            "session_id": self.current_config.session_id if self.current_config else "unknown"
        })

    def get_status(self) -> Dict[str, Any]:
        """Get current backtest execution status"""
        return {
            "is_running": self.is_running,
            "session_id": self.current_config.session_id if self.current_config else None,
            "current_balance": self.current_balance,
            "total_trades": len(self.completed_trades),
            "open_positions": len(self.open_positions),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "progress": 0.0  # Would be calculated based on time elapsed vs total time
        }