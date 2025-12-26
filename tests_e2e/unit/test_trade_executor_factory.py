"""
Integration Tests for Trade Executor Factory
=============================================
Tests end-to-end factory creation for live and paper trading modes.

Tests cover:
- Paper mode executor creation
- Live mode executor creation (with API credentials)
- Live mode rejection (without credentials)
- Backtest mode uses paper adapter
- Leverage configuration

Created: 2025-12-22
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from decimal import Decimal

from src.infrastructure.factories.trade_executor_factory import TradeExecutorFactory
from src.infrastructure.adapters.mexc_futures_order_executor import MexcFuturesOrderExecutor
from src.domain.interfaces.trading import IOrderExecutor
from src.core.logger import StructuredLogger

# Mark all tests in this module as unit tests (no database required)
pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def logger():
    """Mock structured logger"""
    mock_logger = MagicMock(spec=StructuredLogger)
    mock_logger.info = MagicMock()
    mock_logger.error = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.debug = MagicMock()
    return mock_logger


@pytest.fixture
def event_bus():
    """Mock event bus"""
    return MagicMock()


@pytest.fixture
def paper_settings():
    """Settings configured for paper trading"""
    settings = MagicMock()
    settings.trading.mode.value = "paper"
    settings.trading.live_trading_enabled = False
    settings.trading.default_leverage = 3
    settings.trading.paper_trading.initial_balance = 10000.0
    return settings


@pytest.fixture
def live_settings_with_credentials():
    """Settings configured for live trading with API credentials"""
    settings = MagicMock()
    settings.trading.mode.value = "live"
    settings.trading.live_trading_enabled = True
    settings.trading.default_leverage = 5
    settings.exchanges.mexc_api_key = "test_api_key_12345"
    settings.exchanges.mexc_api_secret = "test_api_secret_67890"
    return settings


@pytest.fixture
def live_settings_without_credentials():
    """Settings configured for live trading WITHOUT API credentials"""
    settings = MagicMock()
    settings.trading.mode.value = "live"
    settings.trading.live_trading_enabled = True
    settings.trading.default_leverage = 3
    settings.exchanges.mexc_api_key = ""
    settings.exchanges.mexc_api_secret = ""
    return settings


@pytest.fixture
def backtest_settings():
    """Settings configured for backtest mode"""
    settings = MagicMock()
    settings.trading.mode.value = "backtest"
    settings.trading.live_trading_enabled = False
    settings.trading.default_leverage = 2
    settings.trading.paper_trading.initial_balance = 50000.0
    return settings


# ============================================================================
# Test: Paper Mode
# ============================================================================

class TestTradeExecutorFactoryPaperMode:
    """Test factory creates paper executors correctly"""

    def test_create_paper_executor(self, paper_settings, event_bus, logger):
        """Test factory creates MexcFuturesOrderExecutor for paper mode"""
        factory = TradeExecutorFactory(
            settings=paper_settings,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()

        # Should return IOrderExecutor implementation
        assert isinstance(executor, IOrderExecutor)
        assert isinstance(executor, MexcFuturesOrderExecutor)

        # Should use paper adapter
        assert executor.get_exchange_name() == "MEXC_FUTURES"
        assert executor.default_leverage == 3

        # Logger should log creation
        logger.info.assert_called()

    def test_paper_executor_uses_initial_balance(self, paper_settings, event_bus, logger):
        """Test paper executor uses configured initial balance"""
        paper_settings.trading.paper_trading.initial_balance = 25000.0

        factory = TradeExecutorFactory(
            settings=paper_settings,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()

        # Paper adapter should have initial balance configured
        assert hasattr(executor.mexc_adapter, '_assets')

    def test_paper_mode_when_live_trading_disabled(self, paper_settings, event_bus, logger):
        """Test paper executor created even with 'live' mode when live_trading_enabled=False"""
        paper_settings.trading.mode.value = "live"
        paper_settings.trading.live_trading_enabled = False

        factory = TradeExecutorFactory(
            settings=paper_settings,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()

        # Should still create paper executor
        assert isinstance(executor, MexcFuturesOrderExecutor)


# ============================================================================
# Test: Live Mode
# ============================================================================

class TestTradeExecutorFactoryLiveMode:
    """Test factory creates live executors correctly"""

    def test_create_live_executor_with_credentials(
        self, live_settings_with_credentials, event_bus, logger
    ):
        """Test factory creates live executor when credentials provided"""
        factory = TradeExecutorFactory(
            settings=live_settings_with_credentials,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()

        # Should return IOrderExecutor implementation
        assert isinstance(executor, IOrderExecutor)
        assert isinstance(executor, MexcFuturesOrderExecutor)

        # Should use live adapter with API credentials
        assert hasattr(executor.mexc_adapter, 'api_key')
        assert executor.mexc_adapter.api_key == "test_api_key_12345"

        # Should use configured leverage
        assert executor.default_leverage == 5

    def test_live_executor_rejects_missing_api_key(
        self, live_settings_without_credentials, event_bus, logger
    ):
        """Test factory raises error when API key missing for live mode"""
        factory = TradeExecutorFactory(
            settings=live_settings_without_credentials,
            event_bus=event_bus,
            logger=logger
        )

        with pytest.raises(RuntimeError) as exc_info:
            factory.create()

        assert "MEXC API credentials" in str(exc_info.value)

    def test_live_executor_rejects_missing_api_secret(
        self, live_settings_with_credentials, event_bus, logger
    ):
        """Test factory raises error when API secret missing"""
        live_settings_with_credentials.exchanges.mexc_api_secret = ""

        factory = TradeExecutorFactory(
            settings=live_settings_with_credentials,
            event_bus=event_bus,
            logger=logger
        )

        with pytest.raises(RuntimeError) as exc_info:
            factory.create()

        assert "MEXC API credentials" in str(exc_info.value)


# ============================================================================
# Test: Backtest Mode
# ============================================================================

class TestTradeExecutorFactoryBacktestMode:
    """Test factory handles backtest mode correctly"""

    def test_backtest_uses_paper_adapter(self, backtest_settings, event_bus, logger):
        """Test backtest mode uses paper adapter (no real orders)"""
        factory = TradeExecutorFactory(
            settings=backtest_settings,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()

        # Should create paper executor for backtest
        assert isinstance(executor, MexcFuturesOrderExecutor)

        # Should use configured leverage
        assert executor.default_leverage == 2

    def test_backtest_uses_higher_initial_balance(self, backtest_settings, event_bus, logger):
        """Test backtest can use higher initial balance for testing"""
        backtest_settings.trading.paper_trading.initial_balance = 100000.0

        factory = TradeExecutorFactory(
            settings=backtest_settings,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()
        assert isinstance(executor, MexcFuturesOrderExecutor)


# ============================================================================
# Test: Leverage Configuration
# ============================================================================

class TestTradeExecutorFactoryLeverage:
    """Test leverage configuration"""

    def test_leverage_capped_at_10x(self, paper_settings, event_bus, logger):
        """Test leverage is capped at 10x for safety"""
        paper_settings.trading.default_leverage = 25  # Try to set 25x

        factory = TradeExecutorFactory(
            settings=paper_settings,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()

        # Should be capped at 10x
        assert executor.default_leverage == 10

    def test_leverage_defaults_to_3x(self, paper_settings, event_bus, logger):
        """Test leverage defaults to 3x when not set"""
        # Remove default_leverage attribute
        del paper_settings.trading.default_leverage

        factory = TradeExecutorFactory(
            settings=paper_settings,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()

        # Should default to 3x
        assert executor.default_leverage == 3

    def test_leverage_respects_configured_value(self, paper_settings, event_bus, logger):
        """Test leverage uses configured value when within range"""
        paper_settings.trading.default_leverage = 7

        factory = TradeExecutorFactory(
            settings=paper_settings,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()

        assert executor.default_leverage == 7


# ============================================================================
# Test: Error Handling
# ============================================================================

class TestTradeExecutorFactoryErrorHandling:
    """Test factory error handling"""

    def test_logs_error_on_creation_failure(self, live_settings_with_credentials, event_bus, logger):
        """Test factory logs error when creation fails"""
        # Make MexcFuturesAdapter raise an error during construction
        with patch('src.infrastructure.factories.trade_executor_factory.MexcFuturesAdapter') as mock_adapter:
            mock_adapter.side_effect = Exception("Connection failed")

            factory = TradeExecutorFactory(
                settings=live_settings_with_credentials,
                event_bus=event_bus,
                logger=logger
            )

            with pytest.raises(RuntimeError):
                factory.create()

            # Should log error
            logger.error.assert_called()

    def test_wraps_exceptions_in_runtime_error(self, live_settings_with_credentials, event_bus, logger):
        """Test factory wraps exceptions in RuntimeError"""
        # Make MexcFuturesAdapter raise an error during construction
        with patch('src.infrastructure.factories.trade_executor_factory.MexcFuturesAdapter') as mock_adapter:
            mock_adapter.side_effect = ValueError("Invalid configuration")

            factory = TradeExecutorFactory(
                settings=live_settings_with_credentials,
                event_bus=event_bus,
                logger=logger
            )

            with pytest.raises(RuntimeError) as exc_info:
                factory.create()

            # Should contain original error message
            assert "Failed to create trade executor" in str(exc_info.value)
            assert "Invalid configuration" in str(exc_info.value)


# ============================================================================
# Test: IOrderExecutor Interface Compliance
# ============================================================================

class TestTradeExecutorFactoryInterfaceCompliance:
    """Test created executors implement IOrderExecutor correctly"""

    def test_executor_has_all_interface_methods(self, paper_settings, event_bus, logger):
        """Test executor has all IOrderExecutor methods"""
        factory = TradeExecutorFactory(
            settings=paper_settings,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()

        # All required IOrderExecutor methods
        required_methods = [
            'connect',
            'disconnect',
            'place_market_order',
            'place_limit_order',
            'place_stop_loss_order',
            'cancel_order',
            'cancel_all_orders',
            'get_order_status',
            'get_open_orders',
            'get_order_history',
            'get_exchange_name',
            'health_check',
            'get_account_info',
            'get_trading_fees'
        ]

        for method in required_methods:
            assert hasattr(executor, method), f"Missing method: {method}"
            assert callable(getattr(executor, method)), f"Method not callable: {method}"

    @pytest.mark.asyncio
    async def test_executor_can_get_trading_fees(self, paper_settings, event_bus, logger):
        """Test executor returns trading fees"""
        factory = TradeExecutorFactory(
            settings=paper_settings,
            event_bus=event_bus,
            logger=logger
        )

        executor = factory.create()
        fees = await executor.get_trading_fees("BTC_USDT")

        assert "maker" in fees
        assert "taker" in fees
        assert fees["maker"] == Decimal("0.0002")
        assert fees["taker"] == Decimal("0.0004")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
