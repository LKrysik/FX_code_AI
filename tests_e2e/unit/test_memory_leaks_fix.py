"""
Unit tests for P0 Memory Leak Fixes
====================================

Tests for:
- LEAK #1: session_manager._operation_timestamps using deque(maxlen=1000)
- LEAK #2: paper_trading_engine.trade_history using deque(maxlen=10000)
- LEAK #3: strategy_manager unsubscribe in shutdown()
"""

import pytest
import asyncio
from collections import deque
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.infrastructure.config.settings import AppSettings
from src.trading.session_manager import SessionManager
from src.trading.paper_trading_engine import PaperTradingEngine, TradingSignal, TradingSignalType
from src.domain.services.strategy_manager import StrategyManager
from src.domain.services.order_manager import OrderManager
from src.domain.services.risk_manager import RiskManager


@pytest.fixture
def test_settings():
    """Create test settings"""
    return AppSettings()


@pytest.fixture
def test_logger(test_settings):
    """Create test logger"""
    return StructuredLogger("test_memory_leaks", test_settings.logging)


class TestSessionManagerDequeMemoryLeak:
    """Test LEAK #1: session_manager._operation_timestamps bounded by deque"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_operation_timestamps_uses_deque_with_maxlen(self, test_logger):
        """LEAK #1: Verify _operation_timestamps is a deque with maxlen=1000"""
        # Arrange
        event_bus = EventBus()
        market_adapter = MagicMock()
        market_adapter.subscribe_to_symbol = AsyncMock(return_value=True)
        market_adapter.unsubscribe_from_symbol = AsyncMock(return_value=True)

        # Act
        session_manager = SessionManager(
            event_bus=event_bus,
            logger=test_logger,
            market_adapter=market_adapter
        )

        # Assert
        assert isinstance(session_manager._operation_timestamps, deque), \
            "LEAK #1 NOT FIXED: _operation_timestamps should be deque, not list"
        assert session_manager._operation_timestamps.maxlen == 1000, \
            "LEAK #1 NOT FIXED: deque maxlen should be 1000"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_operation_timestamps_bounded_growth(self, test_logger):
        """LEAK #1: Verify _operation_timestamps never exceeds maxlen (1000)"""
        # Arrange
        event_bus = EventBus()
        market_adapter = MagicMock()
        market_adapter.subscribe_to_symbol = AsyncMock(return_value=True)
        market_adapter.unsubscribe_from_symbol = AsyncMock(return_value=True)

        session_manager = SessionManager(
            event_bus=event_bus,
            logger=test_logger,
            market_adapter=market_adapter
        )

        # Act: Simulate 2000 operations (more than maxlen)
        for i in range(2000):
            session_manager._operation_timestamps.append(float(i))

        # Assert: Should only keep last 1000
        assert len(session_manager._operation_timestamps) == 1000, \
            "LEAK #1 NOT FIXED: deque should only keep last 1000 entries"
        assert session_manager._operation_timestamps[0] == 1000.0, \
            "LEAK #1 NOT FIXED: oldest entry should be 1000 (dropped 0-999)"
        assert session_manager._operation_timestamps[-1] == 1999.0, \
            "LEAK #1 NOT FIXED: newest entry should be 1999"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rate_limit_check_no_manual_cleanup_needed(self):
        """LEAK #1: Verify _check_global_rate_limit doesn't need manual cleanup"""
        # Arrange
        event_bus = EventBus()
        logger = StructuredLogger("test")
        market_adapter = MagicMock()
        market_adapter.subscribe_to_symbol = AsyncMock(return_value=True)
        market_adapter.unsubscribe_from_symbol = AsyncMock(return_value=True)

        session_manager = SessionManager(
            event_bus=event_bus,
            logger=logger,
            market_adapter=market_adapter
        )

        # Fill up to 500 entries
        for i in range(500):
            session_manager._operation_timestamps.append(float(i))

        # Act: Check rate limit (should not clean old timestamps)
        initial_len = len(session_manager._operation_timestamps)
        can_proceed = await session_manager._check_global_rate_limit()

        # Assert: Length should stay the same (deque handles eviction)
        assert len(session_manager._operation_timestamps) == initial_len, \
            "LEAK #1: deque should not need manual cleanup in _check_global_rate_limit"


class TestPaperTradingEngineDequeMemoryLeak:
    """Test LEAK #2: paper_trading_engine.trade_history bounded by deque"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_trade_history_uses_deque_with_maxlen(self):
        """LEAK #2: Verify trade_history is a deque with maxlen=10000"""
        # Arrange
        order_manager = MagicMock(spec=OrderManager)
        risk_manager = MagicMock(spec=RiskManager)
        logger = StructuredLogger("test")

        # Act
        engine = PaperTradingEngine(
            order_manager=order_manager,
            risk_manager=risk_manager,
            logger=logger
        )

        # Assert
        assert isinstance(engine.trade_history, deque), \
            "LEAK #2 NOT FIXED: trade_history should be deque, not list"
        assert engine.trade_history.maxlen == 10000, \
            "LEAK #2 NOT FIXED: deque maxlen should be 10000"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_trade_history_bounded_growth(self):
        """LEAK #2: Verify trade_history never exceeds maxlen (10000)"""
        # Arrange
        order_manager = MagicMock(spec=OrderManager)
        risk_manager = MagicMock(spec=RiskManager)
        logger = StructuredLogger("test")

        engine = PaperTradingEngine(
            order_manager=order_manager,
            risk_manager=risk_manager,
            logger=logger
        )

        # Act: Simulate 15000 trades (more than maxlen)
        from src.trading.paper_trading_engine import PaperTrade
        for i in range(15000):
            trade = PaperTrade(
                order_id=f"order_{i}",
                symbol="BTCUSDT",
                action=TradingSignalType.BUY,
                quantity=1.0,
                execution_price=50000.0,
                strategy_name="test",
                timestamp=datetime.now()
            )
            engine.trade_history.append(trade)

        # Assert: Should only keep last 10000
        assert len(engine.trade_history) == 10000, \
            "LEAK #2 NOT FIXED: deque should only keep last 10000 entries"
        assert engine.trade_history[0].order_id == "order_5000", \
            "LEAK #2 NOT FIXED: oldest entry should be order_5000 (dropped 0-4999)"
        assert engine.trade_history[-1].order_id == "order_14999", \
            "LEAK #2 NOT FIXED: newest entry should be order_14999"


class TestStrategyManagerUnsubscribeMemoryLeak:
    """Test LEAK #3: strategy_manager unsubscribe in shutdown()"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_shutdown_unsubscribes_from_event_bus(self):
        """LEAK #3: Verify shutdown() unsubscribes from event bus"""
        # Arrange
        event_bus = EventBus()
        logger = StructuredLogger("test")
        order_manager = MagicMock(spec=OrderManager)
        risk_manager = MagicMock(spec=RiskManager)

        strategy_manager = StrategyManager(
            event_bus=event_bus,
            logger=logger,
            order_manager=order_manager,
            risk_manager=risk_manager
        )

        # Subscribe handlers
        await strategy_manager.start()

        # Verify subscribed
        assert "indicator.updated" in event_bus._subscribers, \
            "LEAK #3: indicator.updated should be subscribed"
        assert "market.price_update" in event_bus._subscribers, \
            "LEAK #3: market.price_update should be subscribed"

        initial_indicator_subscribers = len(event_bus._subscribers.get("indicator.updated", []))
        initial_price_subscribers = len(event_bus._subscribers.get("market.price_update", []))

        # Act: Shutdown
        await strategy_manager.shutdown()

        # Assert: Handlers should be unsubscribed
        final_indicator_subscribers = len(event_bus._subscribers.get("indicator.updated", []))
        final_price_subscribers = len(event_bus._subscribers.get("market.price_update", []))

        assert final_indicator_subscribers == initial_indicator_subscribers - 1, \
            "LEAK #3 NOT FIXED: indicator.updated handler should be unsubscribed"
        assert final_price_subscribers == initial_price_subscribers - 1, \
            "LEAK #3 NOT FIXED: market.price_update handler should be unsubscribed"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_shutdown_handles_unsubscribe_errors_gracefully(self):
        """LEAK #3: Verify shutdown() handles unsubscribe errors gracefully"""
        # Arrange
        event_bus = EventBus()
        logger = StructuredLogger("test")
        order_manager = MagicMock(spec=OrderManager)
        risk_manager = MagicMock(spec=RiskManager)

        strategy_manager = StrategyManager(
            event_bus=event_bus,
            logger=logger,
            order_manager=order_manager,
            risk_manager=risk_manager
        )

        # Subscribe handlers
        await strategy_manager.start()

        # Mock unsubscribe to raise error
        original_unsubscribe = event_bus.unsubscribe
        async def failing_unsubscribe(topic, handler):
            raise RuntimeError("Mock unsubscribe error")

        event_bus.unsubscribe = failing_unsubscribe

        # Act: Shutdown should not raise exception
        try:
            await strategy_manager.shutdown()
            # Assert: Should complete without raising
            assert True, "LEAK #3: shutdown() should handle unsubscribe errors gracefully"
        except Exception as e:
            pytest.fail(f"LEAK #3 NOT FIXED: shutdown() raised exception: {e}")
        finally:
            # Restore original
            event_bus.unsubscribe = original_unsubscribe

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_multiple_shutdown_calls_safe(self):
        """LEAK #3: Verify multiple shutdown() calls are safe (idempotent)"""
        # Arrange
        event_bus = EventBus()
        logger = StructuredLogger("test")
        order_manager = MagicMock(spec=OrderManager)
        risk_manager = MagicMock(spec=RiskManager)

        strategy_manager = StrategyManager(
            event_bus=event_bus,
            logger=logger,
            order_manager=order_manager,
            risk_manager=risk_manager
        )

        # Subscribe handlers
        await strategy_manager.start()

        # Act: Multiple shutdowns
        try:
            await strategy_manager.shutdown()
            await strategy_manager.shutdown()  # Second call should be safe
            await strategy_manager.shutdown()  # Third call should be safe

            # Assert: Should complete without raising
            assert True, "LEAK #3: multiple shutdown() calls should be safe"
        except Exception as e:
            pytest.fail(f"LEAK #3 NOT FIXED: multiple shutdown() calls raised exception: {e}")


class TestMemoryLeaksIntegration:
    """Integration tests to verify all leaks are fixed together"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_all_leaks_fixed_in_production_like_scenario(self):
        """Integration: Verify all 3 leaks are fixed in production-like scenario"""
        # Arrange
        event_bus = EventBus()
        logger = StructuredLogger("test")
        market_adapter = MagicMock()
        market_adapter.subscribe_to_symbol = AsyncMock(return_value=True)
        market_adapter.unsubscribe_from_symbol = AsyncMock(return_value=True)

        order_manager = MagicMock(spec=OrderManager)
        risk_manager = MagicMock(spec=RiskManager)

        # Create all components
        session_manager = SessionManager(
            event_bus=event_bus,
            logger=logger,
            market_adapter=market_adapter
        )

        paper_trading_engine = PaperTradingEngine(
            order_manager=order_manager,
            risk_manager=risk_manager,
            logger=logger
        )

        strategy_manager = StrategyManager(
            event_bus=event_bus,
            logger=logger,
            order_manager=order_manager,
            risk_manager=risk_manager
        )

        # Act: Simulate heavy load
        # 1. Fill session_manager operations
        for i in range(2000):
            session_manager._operation_timestamps.append(float(i))

        # 2. Fill paper_trading_engine trades
        from src.trading.paper_trading_engine import PaperTrade
        for i in range(15000):
            trade = PaperTrade(
                order_id=f"order_{i}",
                symbol="BTCUSDT",
                action=TradingSignalType.BUY,
                quantity=1.0,
                execution_price=50000.0,
                strategy_name="test",
                timestamp=datetime.now()
            )
            paper_trading_engine.trade_history.append(trade)

        # 3. Start and shutdown strategy_manager
        await strategy_manager.start()
        await strategy_manager.shutdown()

        # Assert: All structures should be bounded
        assert len(session_manager._operation_timestamps) == 1000, \
            "LEAK #1: operations should be bounded to 1000"
        assert len(paper_trading_engine.trade_history) == 10000, \
            "LEAK #2: trades should be bounded to 10000"

        # Verify event bus has no dangling subscribers from strategy_manager
        # (strategy_manager should have unsubscribed)
        indicator_subs = len(event_bus._subscribers.get("indicator.updated", []))
        price_subs = len(event_bus._subscribers.get("market.price_update", []))

        assert indicator_subs == 0, \
            "LEAK #3: indicator.updated should have no subscribers after shutdown"
        assert price_subs == 0, \
            "LEAK #3: market.price_update should have no subscribers after shutdown"
