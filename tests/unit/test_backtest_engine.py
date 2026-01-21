"""
Unit Tests for BacktestEngine - Story 1b-2
==========================================
Tests for the backtest execution engine.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from src.trading.backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestProgress,
    BacktestResult,
    BacktestStatus,
    TradeRecord,
    EquityPoint,
    run_backtest
)
from src.trading.backtest_data_provider_questdb import MarketDataSnapshot
from src.domain.services.backtest_order_manager import OrderType, PositionRecord


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_event_bus():
    """Create mock EventBus"""
    event_bus = MagicMock()
    event_bus.publish = AsyncMock()
    event_bus.subscribe = AsyncMock()
    event_bus.unsubscribe = AsyncMock()
    return event_bus


@pytest.fixture
def mock_db_provider():
    """Create mock QuestDB provider"""
    provider = MagicMock()
    provider.execute_query = AsyncMock()
    provider.execute = AsyncMock()
    provider.initialize = AsyncMock()
    provider.close = AsyncMock()
    return provider


@pytest.fixture
def mock_logger():
    """Create mock logger"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def sample_config():
    """Sample backtest configuration"""
    return BacktestConfig(
        session_id="bt_test_001",
        strategy_id="strategy_001",
        symbol="BTCUSDT",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 7, tzinfo=timezone.utc),
        acceleration_factor=10,
        initial_balance=10000.0,
        stop_loss_percent=5.0,
        take_profit_percent=10.0
    )


@pytest.fixture
def sample_candles():
    """Generate sample candles for testing"""
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles = []
    base_price = 50000.0

    for i in range(100):
        # Create some price movement
        price_offset = (i % 20 - 10) * 100  # Oscillate +/- 1000
        volume_surge = 2.0 if i % 10 == 5 else 1.0  # Volume surge every 10 candles

        candle = MarketDataSnapshot(
            symbol="BTCUSDT",
            timestamp=base_time + timedelta(minutes=i),
            open=base_price + price_offset,
            high=base_price + price_offset + 50,
            low=base_price + price_offset - 50,
            close=base_price + price_offset + 25,
            volume=1000.0 * volume_surge
        )
        candles.append(candle)

    return candles


# =============================================================================
# BacktestConfig Tests
# =============================================================================

class TestBacktestConfig:
    """Tests for BacktestConfig dataclass"""

    def test_config_creation(self, sample_config):
        """Test creating a backtest configuration"""
        assert sample_config.session_id == "bt_test_001"
        assert sample_config.strategy_id == "strategy_001"
        assert sample_config.symbol == "BTCUSDT"
        assert sample_config.acceleration_factor == 10
        assert sample_config.initial_balance == 10000.0

    def test_config_defaults(self):
        """Test default values for optional fields"""
        config = BacktestConfig(
            session_id="bt_001",
            strategy_id="strat_001",
            symbol="ETHUSDT",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
        assert config.acceleration_factor == 10
        assert config.initial_balance == 10000.0
        assert config.stop_loss_percent == 5.0
        assert config.take_profit_percent == 10.0
        assert config.timeframe == "1m"


# =============================================================================
# BacktestProgress Tests
# =============================================================================

class TestBacktestProgress:
    """Tests for BacktestProgress dataclass"""

    def test_progress_creation(self):
        """Test creating a progress tracker"""
        progress = BacktestProgress(session_id="bt_001")
        assert progress.session_id == "bt_001"
        assert progress.status == BacktestStatus.PENDING
        assert progress.progress_pct == 0.0
        assert progress.current_pnl == 0.0

    def test_progress_to_dict(self):
        """Test serializing progress to dict"""
        progress = BacktestProgress(
            session_id="bt_001",
            status=BacktestStatus.RUNNING,
            progress_pct=50.5,
            current_pnl=1234.56,
            total_trades=5,
            equity=11234.56
        )

        result = progress.to_dict()

        assert result["session_id"] == "bt_001"
        assert result["status"] == "running"
        assert result["progress_pct"] == 50.5
        assert result["current_pnl"] == 1234.56
        assert result["total_trades"] == 5

    def test_progress_with_timestamps(self):
        """Test progress with timestamps"""
        now = datetime.now(timezone.utc)
        progress = BacktestProgress(
            session_id="bt_001",
            started_at=now,
            current_timestamp=now + timedelta(hours=1)
        )

        result = progress.to_dict()

        assert result["started_at"] is not None
        assert result["current_timestamp"] is not None


# =============================================================================
# BacktestResult Tests
# =============================================================================

class TestBacktestResult:
    """Tests for BacktestResult dataclass"""

    def test_result_creation(self, sample_config):
        """Test creating a backtest result"""
        result = BacktestResult(
            session_id=sample_config.session_id,
            symbol=sample_config.symbol,
            strategy_id=sample_config.strategy_id,
            start_date=sample_config.start_date,
            end_date=sample_config.end_date,
            final_pnl=2500.0,
            total_trades=42,
            winning_trades=25,
            losing_trades=17,
            win_rate=0.595
        )

        assert result.final_pnl == 2500.0
        assert result.total_trades == 42
        assert result.win_rate == 0.595

    def test_result_to_dict(self, sample_config):
        """Test serializing result to dict"""
        result = BacktestResult(
            session_id=sample_config.session_id,
            symbol=sample_config.symbol,
            strategy_id=sample_config.strategy_id,
            start_date=sample_config.start_date,
            end_date=sample_config.end_date,
            final_pnl=1500.0,
            total_trades=20,
            duration_seconds=120.5
        )

        data = result.to_dict()

        assert data["session_id"] == sample_config.session_id
        assert data["final_pnl"] == 1500.0
        assert data["total_trades"] == 20
        assert data["duration_seconds"] == 120.5


# =============================================================================
# BacktestEngine Unit Tests
# =============================================================================

class TestBacktestEngineInit:
    """Tests for BacktestEngine initialization"""

    def test_engine_creation(self, mock_event_bus, mock_db_provider, mock_logger):
        """Test creating a backtest engine"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus,
            logger=mock_logger
        )

        assert engine.session_id == "bt_001"
        assert engine.db_provider == mock_db_provider
        assert engine.event_bus == mock_event_bus
        assert engine.config is None  # Not loaded yet
        assert engine._running is False

    def test_engine_default_broadcast_interval(self, mock_event_bus, mock_db_provider):
        """Test default broadcast interval"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )

        assert engine.broadcast_interval == 1.0

    def test_engine_custom_broadcast_interval(self, mock_event_bus, mock_db_provider):
        """Test custom broadcast interval"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus,
            broadcast_interval=0.5
        )

        assert engine.broadcast_interval == 0.5


class TestBacktestEngineLoadConfig:
    """Tests for loading session configuration"""

    @pytest.mark.asyncio
    async def test_load_session_config_success(self, mock_event_bus, mock_db_provider, mock_logger):
        """Test successfully loading session config"""
        mock_db_provider.execute_query.return_value = [{
            "session_id": "bt_001",
            "strategy_id": "strat_001",
            "symbol": "BTCUSDT",
            "start_date": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2025, 1, 7, tzinfo=timezone.utc),
            "acceleration_factor": 10,
            "initial_balance": 10000.0
        }]

        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus,
            logger=mock_logger
        )

        config = await engine.load_session_config()

        assert config.session_id == "bt_001"
        assert config.strategy_id == "strat_001"
        assert config.symbol == "BTCUSDT"
        mock_db_provider.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_session_config_not_found(self, mock_event_bus, mock_db_provider, mock_logger):
        """Test loading non-existent session config"""
        mock_db_provider.execute_query.return_value = []

        engine = BacktestEngine(
            session_id="bt_nonexistent",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus,
            logger=mock_logger
        )

        with pytest.raises(ValueError, match="Backtest session not found"):
            await engine.load_session_config()


class TestBacktestEngineLoadStrategy:
    """Tests for loading strategy configuration"""

    @pytest.mark.asyncio
    async def test_load_strategy_success(self, mock_event_bus, mock_db_provider, mock_logger):
        """Test successfully loading strategy"""
        mock_db_provider.execute_query.return_value = [{
            "strategy_id": "strat_001",
            "name": "Test Strategy",
            "config": {"signal_detection": {"conditions": []}},
            "enabled": True
        }]

        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus,
            logger=mock_logger
        )

        strategy = await engine.load_strategy("strat_001")

        assert strategy is not None
        assert "signal_detection" in strategy

    @pytest.mark.asyncio
    async def test_load_strategy_fallback_to_default(self, mock_event_bus, mock_db_provider, mock_logger):
        """Test falling back to default strategy when not found"""
        mock_db_provider.execute_query.return_value = []

        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus,
            logger=mock_logger
        )

        strategy = await engine.load_strategy("strat_nonexistent")

        assert strategy is not None
        assert "signal_detection" in strategy
        assert strategy["strategy_id"] == "strat_nonexistent"


class TestBacktestEngineSignalEvaluation:
    """Tests for signal evaluation logic"""

    def test_evaluate_entry_signal_positive_momentum(self, mock_event_bus, mock_db_provider, sample_config):
        """Test entry signal with positive momentum"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )
        engine.config = sample_config

        candle = {
            "open": 50000.0,
            "close": 50100.0,  # Positive momentum
            "high": 50150.0,
            "low": 49950.0,
            "volume": 2000.0  # High volume
        }

        indicators = {
            "avg_volume": 1000.0,  # Volume ratio = 2.0
            "price": 50100.0
        }

        signal = engine._evaluate_entry_signal(candle, indicators)

        assert signal is not None
        assert signal["signal_type"] == "S1"
        assert signal["side"] == "buy"

    def test_evaluate_entry_signal_no_momentum(self, mock_event_bus, mock_db_provider, sample_config):
        """Test no entry signal with negative momentum"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )
        engine.config = sample_config

        candle = {
            "open": 50100.0,
            "close": 50000.0,  # Negative momentum
            "high": 50150.0,
            "low": 49950.0,
            "volume": 500.0  # Low volume
        }

        indicators = {
            "avg_volume": 1000.0,  # Volume ratio = 0.5
            "price": 50000.0
        }

        signal = engine._evaluate_entry_signal(candle, indicators)

        assert signal is None

    def test_evaluate_exit_signal_stop_loss(self, mock_event_bus, mock_db_provider, sample_config):
        """Test exit signal when stop loss triggered"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )
        engine.config = sample_config

        candle = {"close": 45000.0}  # Price dropped

        position = PositionRecord(
            symbol="BTCUSDT",
            quantity=1.0,  # Long position
            average_price=50000.0  # Entry at 50k
        )

        signal = engine._evaluate_exit_signal(candle, position)

        assert signal is not None
        assert signal["signal_type"] == "E1"
        assert signal["side"] == "sell"

    def test_evaluate_exit_signal_take_profit(self, mock_event_bus, mock_db_provider, sample_config):
        """Test exit signal when take profit triggered"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )
        engine.config = sample_config

        candle = {"close": 56000.0}  # Price increased

        position = PositionRecord(
            symbol="BTCUSDT",
            quantity=1.0,  # Long position
            average_price=50000.0  # Entry at 50k, +12% profit
        )

        signal = engine._evaluate_exit_signal(candle, position)

        assert signal is not None
        assert signal["signal_type"] == "ZE1"
        assert signal["side"] == "sell"

    def test_evaluate_exit_signal_no_position(self, mock_event_bus, mock_db_provider, sample_config):
        """Test no exit signal when no position"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )
        engine.config = sample_config

        candle = {"close": 50000.0}

        position = PositionRecord(
            symbol="BTCUSDT",
            quantity=0.0,  # No position
            average_price=0.0
        )

        signal = engine._evaluate_exit_signal(candle, position)

        assert signal is None


class TestBacktestEngineEquityTracking:
    """Tests for equity curve tracking"""

    def test_record_equity_point(self, mock_event_bus, mock_db_provider, sample_config):
        """Test recording equity point"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )
        engine.config = sample_config
        engine.peak_equity = 10000.0
        engine.progress.current_pnl = 500.0

        positions = [{"unrealized_pnl": 200.0}]
        timestamp = datetime.now(timezone.utc)

        engine._record_equity_point(timestamp, positions)

        assert len(engine.equity_curve) == 1
        point = engine.equity_curve[0]
        assert point.timestamp == timestamp
        assert point.equity == 10700.0  # 10000 + 500 + 200
        assert engine.progress.equity == 10700.0

    def test_record_drawdown(self, mock_event_bus, mock_db_provider, sample_config):
        """Test recording drawdown"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )
        engine.config = sample_config
        engine.peak_equity = 12000.0  # Peak was higher
        engine.progress.current_pnl = -500.0

        positions = [{"unrealized_pnl": -200.0}]
        timestamp = datetime.now(timezone.utc)

        engine._record_equity_point(timestamp, positions)

        # Current equity = 10000 - 500 - 200 = 9300
        # Drawdown = (12000 - 9300) / 12000 * 100 = 22.5%
        assert engine.progress.max_drawdown_pct > 0


class TestBacktestEngineBroadcast:
    """Tests for WebSocket broadcast functionality"""

    @pytest.mark.asyncio
    async def test_broadcast_progress(self, mock_event_bus, mock_db_provider):
        """Test broadcasting progress"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus,
            broadcast_interval=0.0  # No throttle for testing
        )

        engine.progress.status = BacktestStatus.RUNNING
        engine.progress.progress_pct = 50.0

        await engine.broadcast_progress(force=True)

        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == "backtest.progress"
        assert call_args[0][1]["type"] == "backtest.progress"

    @pytest.mark.asyncio
    async def test_broadcast_completed(self, mock_event_bus, mock_db_provider, sample_config):
        """Test broadcasting completion"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )

        result = BacktestResult(
            session_id="bt_001",
            symbol="BTCUSDT",
            strategy_id="strat_001",
            start_date=sample_config.start_date,
            end_date=sample_config.end_date,
            final_pnl=2500.0,
            total_trades=10,
            win_rate=0.6,
            duration_seconds=60.0
        )

        await engine.broadcast_completed(result)

        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == "backtest.completed"
        assert call_args[0][1]["data"]["final_pnl"] == 2500.0

    @pytest.mark.asyncio
    async def test_broadcast_failed(self, mock_event_bus, mock_db_provider):
        """Test broadcasting failure"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )

        await engine.broadcast_failed("Test error message")

        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == "backtest.failed"
        assert call_args[0][1]["data"]["error"] == "Test error message"


class TestBacktestEngineStop:
    """Tests for stop functionality"""

    def test_stop_request(self, mock_event_bus, mock_db_provider):
        """Test requesting stop"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )

        assert engine._stop_requested is False

        engine.stop()

        assert engine._stop_requested is True

    def test_is_running_property(self, mock_event_bus, mock_db_provider):
        """Test is_running property"""
        engine = BacktestEngine(
            session_id="bt_001",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus
        )

        assert engine.is_running is False

        engine._running = True
        assert engine.is_running is True


# =============================================================================
# Integration-like Tests (with mocked dependencies)
# =============================================================================

class TestBacktestEngineRun:
    """Tests for the main run() method"""

    @pytest.mark.asyncio
    async def test_run_no_data_error(self, mock_event_bus, mock_db_provider, mock_logger):
        """Test run fails gracefully when no historical data"""
        # Setup mocks
        mock_db_provider.execute_query.side_effect = [
            # load_session_config
            [{
                "session_id": "bt_001",
                "strategy_id": "strat_001",
                "symbol": "BTCUSDT",
                "start_date": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "end_date": datetime(2025, 1, 7, tzinfo=timezone.utc),
                "acceleration_factor": 10,
                "initial_balance": 10000.0
            }],
            # load_strategy
            []  # Strategy not found, will use default
        ]

        with patch('src.trading.backtest_engine.BacktestMarketDataProvider') as MockDataProvider:
            mock_data_provider = MagicMock()
            mock_data_provider.initialize = AsyncMock()
            mock_data_provider.get_price_range = AsyncMock(return_value=[])  # No data
            mock_data_provider.close = AsyncMock()
            MockDataProvider.return_value = mock_data_provider

            with patch('src.trading.backtest_engine.BacktestOrderManager') as MockOrderManager:
                mock_order_manager = MagicMock()
                mock_order_manager.start = AsyncMock()
                mock_order_manager.stop = AsyncMock()
                MockOrderManager.return_value = mock_order_manager

                engine = BacktestEngine(
                    session_id="bt_001",
                    db_provider=mock_db_provider,
                    event_bus=mock_event_bus,
                    logger=mock_logger
                )

                result = await engine.run()

                assert result.status == BacktestStatus.FAILED
                assert "No historical data found" in result.error_message

    @pytest.mark.asyncio
    async def test_run_session_not_found(self, mock_event_bus, mock_db_provider, mock_logger):
        """Test run fails when session not found"""
        mock_db_provider.execute_query.return_value = []

        engine = BacktestEngine(
            session_id="bt_nonexistent",
            db_provider=mock_db_provider,
            event_bus=mock_event_bus,
            logger=mock_logger
        )

        result = await engine.run()

        assert result.status == BacktestStatus.FAILED
        assert "session not found" in result.error_message.lower()


# =============================================================================
# TradeRecord Tests
# =============================================================================

class TestTradeRecord:
    """Tests for TradeRecord dataclass"""

    def test_trade_record_creation(self):
        """Test creating a trade record"""
        trade = TradeRecord(
            trade_id="trade_001",
            session_id="bt_001",
            symbol="BTCUSDT",
            order_type="buy",
            quantity=0.1,
            entry_price=50000.0,
            exit_price=52000.0,
            pnl=200.0,
            entry_time=datetime.now(timezone.utc),
            exit_time=datetime.now(timezone.utc),
            strategy_signal="S1"
        )

        assert trade.trade_id == "trade_001"
        assert trade.pnl == 200.0
        assert trade.strategy_signal == "S1"


# =============================================================================
# EquityPoint Tests
# =============================================================================

class TestEquityPoint:
    """Tests for EquityPoint dataclass"""

    def test_equity_point_creation(self):
        """Test creating an equity point"""
        point = EquityPoint(
            timestamp=datetime.now(timezone.utc),
            equity=11000.0,
            drawdown_pct=5.0,
            open_positions=2
        )

        assert point.equity == 11000.0
        assert point.drawdown_pct == 5.0
        assert point.open_positions == 2


# =============================================================================
# run_backtest convenience function tests
# =============================================================================

class TestRunBacktestFunction:
    """Tests for the run_backtest convenience function"""

    @pytest.mark.asyncio
    async def test_run_backtest_creates_engine(self, mock_event_bus, mock_db_provider):
        """Test that run_backtest creates and runs an engine"""
        mock_db_provider.execute_query.return_value = []

        with patch('src.trading.backtest_engine.BacktestEngine') as MockEngine:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=BacktestResult(
                session_id="bt_001",
                symbol="BTCUSDT",
                strategy_id="strat_001",
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc)
            ))
            MockEngine.return_value = mock_engine

            result = await run_backtest(
                session_id="bt_001",
                db_provider=mock_db_provider,
                event_bus=mock_event_bus
            )

            MockEngine.assert_called_once()
            mock_engine.run.assert_called_once()
            assert result.session_id == "bt_001"
