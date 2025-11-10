"""
Unit Tests for EventBusMarketDataProvider
==========================================
Tests for EventBus-backed market data provider with focus on:
- Health check functionality (prevent infinite recursion)
- Memory management and resource cleanup
- Queue operations and symbol subscription
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.infrastructure.exchanges.eventbus_market_data_provider import EventBusMarketDataProvider
from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.domain.models.market_data import MarketData


@pytest.fixture
def event_bus():
    """Create a real EventBus instance for testing"""
    return EventBus()


@pytest.fixture
def logger():
    """Create a mock logger"""
    logger = MagicMock(spec=StructuredLogger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def provider(event_bus, logger):
    """Create EventBusMarketDataProvider instance"""
    return EventBusMarketDataProvider(event_bus, logger, exchange_name="test_exchange")


class TestHealthCheck:
    """Test health check functionality - critical to prevent infinite recursion"""

    @pytest.mark.asyncio
    async def test_health_check_no_infinite_recursion(self, provider):
        """
        CRITICAL: Verify health_check does not call itself recursively.
        This test would hang/timeout if infinite recursion exists.
        """
        # Set timeout to detect infinite recursion
        try:
            result = await asyncio.wait_for(provider.health_check(), timeout=2.0)
            assert isinstance(result, bool), "health_check should return bool"
        except asyncio.TimeoutError:
            pytest.fail("health_check() caused infinite recursion - test timed out")

    @pytest.mark.asyncio
    async def test_health_check_disconnected_state(self, provider):
        """Test health check returns False when disconnected"""
        # Provider is disconnected by default
        result = await provider.health_check()
        assert result is False, "health_check should return False when disconnected"

    @pytest.mark.asyncio
    async def test_health_check_connected_state(self, provider):
        """Test health check returns True when connected"""
        await provider.connect()
        result = await provider.health_check()
        assert result is True, "health_check should return True when connected"
        await provider.disconnect()

    @pytest.mark.asyncio
    async def test_get_detailed_health_status_structure(self, provider):
        """Test detailed health status returns correct structure"""
        status = await provider.get_detailed_health_status()

        # Verify structure
        assert "healthy" in status
        assert "connected" in status
        assert "exchange" in status
        assert "memory_stats" in status
        assert "alerts" in status

        # Verify types
        assert isinstance(status["healthy"], bool)
        assert isinstance(status["connected"], bool)
        assert isinstance(status["exchange"], str)
        assert isinstance(status["memory_stats"], dict)
        assert isinstance(status["alerts"], list)

    @pytest.mark.asyncio
    async def test_health_check_with_subscribed_symbols(self, provider):
        """Test health check with active symbol subscriptions"""
        await provider.connect()
        await provider.subscribe_to_symbol("BTC_USDT")
        await provider.subscribe_to_symbol("ETH_USDT")

        result = await provider.health_check()
        assert result is True

        status = await provider.get_detailed_health_status()
        assert status["memory_stats"]["queues_count"] == 2
        assert status["memory_stats"]["allowed_symbols_count"] == 2

        await provider.disconnect()


class TestConnectionManagement:
    """Test connection lifecycle"""

    @pytest.mark.asyncio
    async def test_connect_sets_connected_flag(self, provider):
        """Test connect sets internal state"""
        assert provider._connected is False
        await provider.connect()
        assert provider._connected is True
        await provider.disconnect()

    @pytest.mark.asyncio
    async def test_connect_idempotent(self, provider):
        """Test multiple connects don't cause issues"""
        await provider.connect()
        await provider.connect()  # Should not raise
        assert provider._connected is True
        await provider.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_clears_resources(self, provider, logger):
        """Test disconnect cleans up all resources"""
        await provider.connect()
        await provider.subscribe_to_symbol("BTC_USDT")
        await provider.subscribe_to_symbol("ETH_USDT")

        # Verify resources exist
        assert len(provider._queues) == 2
        assert len(provider._allowed_symbols) == 2

        # Disconnect
        await provider.disconnect()

        # Verify cleanup
        assert provider._connected is False
        assert len(provider._queues) == 0
        assert len(provider._allowed_symbols) == 0

        # Verify logging
        logger.info.assert_called()
        calls = [call for call in logger.info.call_args_list
                if "market_data_provider.disconnected" in str(call)]
        assert len(calls) > 0


class TestSymbolSubscription:
    """Test symbol subscription and resource management"""

    @pytest.mark.asyncio
    async def test_subscribe_creates_queue(self, provider):
        """Test subscribe creates queue and adds to allowed symbols"""
        await provider.subscribe_to_symbol("BTC_USDT")

        assert "BTC_USDT" in provider._queues
        assert "BTC_USDT" in provider._allowed_symbols
        assert isinstance(provider._queues["BTC_USDT"], asyncio.Queue)

    @pytest.mark.asyncio
    async def test_subscribe_multiple_symbols(self, provider):
        """Test subscribing to multiple symbols"""
        symbols = ["BTC_USDT", "ETH_USDT", "XRP_USDT"]

        for symbol in symbols:
            await provider.subscribe_to_symbol(symbol)

        assert len(provider._queues) == 3
        assert len(provider._allowed_symbols) == 3

    @pytest.mark.asyncio
    async def test_subscribe_idempotent(self, provider):
        """Test multiple subscribes to same symbol don't duplicate"""
        await provider.subscribe_to_symbol("BTC_USDT")
        await provider.subscribe_to_symbol("BTC_USDT")

        assert len(provider._queues) == 1
        assert len(provider._allowed_symbols) == 1

    @pytest.mark.asyncio
    async def test_subscribe_enforces_max_symbols_limit(self, provider):
        """Test subscription respects MAX_SYMBOLS limit"""
        provider.MAX_SYMBOLS = 3

        await provider.subscribe_to_symbol("BTC_USDT")
        await provider.subscribe_to_symbol("ETH_USDT")
        await provider.subscribe_to_symbol("XRP_USDT")

        # Fourth subscription should fail
        with pytest.raises(ValueError, match="Too many symbols subscribed"):
            await provider.subscribe_to_symbol("LTC_USDT")

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_queue(self, provider):
        """Test unsubscribe removes queue and symbol"""
        await provider.subscribe_to_symbol("BTC_USDT")
        assert "BTC_USDT" in provider._queues

        await provider.unsubscribe_from_symbol("BTC_USDT")
        assert "BTC_USDT" not in provider._queues
        assert "BTC_USDT" not in provider._allowed_symbols

    @pytest.mark.asyncio
    async def test_unsubscribe_drains_queue(self, provider, logger):
        """Test unsubscribe drains queue before removal"""
        await provider.connect()
        await provider.subscribe_to_symbol("BTC_USDT")

        # Add some events to queue
        queue = provider._queues["BTC_USDT"]
        await queue.put({"symbol": "BTC_USDT", "price": 50000})
        await queue.put({"symbol": "BTC_USDT", "price": 50100})

        # Unsubscribe should drain
        await provider.unsubscribe_from_symbol("BTC_USDT")

        # Verify logging includes drained count
        logger.info.assert_called()
        calls = [call for call in logger.info.call_args_list
                if "market_data_provider.symbol_unsubscribed" in str(call)]
        assert len(calls) > 0

        await provider.disconnect()

    @pytest.mark.asyncio
    async def test_unsubscribe_unknown_symbol_logs_warning(self, provider, logger):
        """Test unsubscribe of non-existent symbol logs warning"""
        await provider.unsubscribe_from_symbol("UNKNOWN_SYMBOL")

        logger.warning.assert_called()
        calls = [call for call in logger.warning.call_args_list
                if "market_data_provider.unsubscribe_unknown_symbol" in str(call)]
        assert len(calls) > 0


class TestMemoryManagement:
    """Test memory safety and resource management"""

    @pytest.mark.asyncio
    async def test_get_memory_stats(self, provider):
        """Test memory statistics reporting"""
        await provider.subscribe_to_symbol("BTC_USDT")
        await provider.subscribe_to_symbol("ETH_USDT")

        stats = provider.get_memory_stats()

        assert "queues_count" in stats
        assert "allowed_symbols_count" in stats
        assert "total_queue_sizes" in stats
        assert "max_queue_size" in stats

        assert stats["queues_count"] == 2
        assert stats["allowed_symbols_count"] == 2

    @pytest.mark.asyncio
    async def test_cleanup_resources_removes_inactive(self, provider):
        """Test cleanup removes inactive queues"""
        await provider.subscribe_to_symbol("BTC_USDT")

        # Remove from allowed symbols to make it eligible for cleanup
        provider._allowed_symbols.discard("BTC_USDT")

        # Mark as old
        provider._last_activity["BTC_USDT"] = 0

        # Trigger cleanup
        await provider._cleanup_resources()

        # Should be removed
        assert "BTC_USDT" not in provider._queues

    @pytest.mark.asyncio
    async def test_cleanup_resources_keeps_active(self, provider):
        """Test cleanup keeps active queues"""
        await provider.subscribe_to_symbol("BTC_USDT")

        # Mark as recently active
        import time
        provider._last_activity["BTC_USDT"] = time.time()

        # Trigger cleanup
        await provider._cleanup_resources()

        # Should still exist
        assert "BTC_USDT" in provider._queues

    @pytest.mark.asyncio
    async def test_queue_has_max_size(self, provider):
        """Test queues respect MAX_QUEUE_SIZE"""
        await provider.subscribe_to_symbol("BTC_USDT")
        queue = provider._queues["BTC_USDT"]

        assert queue.maxsize == provider.MAX_QUEUE_SIZE


class TestEventProcessing:
    """Test event processing and queue operations"""

    @pytest.mark.asyncio
    async def test_on_price_update_enqueues_for_subscribed_symbol(self, provider):
        """Test price update events are enqueued for subscribed symbols"""
        await provider.connect()
        await provider.subscribe_to_symbol("BTC_USDT")

        # Simulate price update event
        event = {
            "symbol": "BTC_USDT",
            "price": 50000.0,
            "volume": 100.0,
            "timestamp": 1234567890
        }

        await provider._on_price_update(event)

        # Verify event was enqueued
        queue = provider._queues["BTC_USDT"]
        assert queue.qsize() == 1

        await provider.disconnect()

    @pytest.mark.asyncio
    async def test_on_price_update_ignores_unsubscribed_symbol(self, provider):
        """Test price updates for unsubscribed symbols are ignored"""
        await provider.connect()
        await provider.subscribe_to_symbol("BTC_USDT")

        # Try to send update for different symbol
        event = {
            "symbol": "ETH_USDT",  # Not subscribed
            "price": 3000.0,
            "volume": 50.0,
            "timestamp": 1234567890
        }

        await provider._on_price_update(event)

        # Should not create queue for ETH_USDT
        assert "ETH_USDT" not in provider._queues

        await provider.disconnect()

    @pytest.mark.asyncio
    async def test_on_price_update_handles_missing_symbol(self, provider, logger):
        """Test handling of events without symbol"""
        await provider.connect()

        # Event without symbol
        event = {
            "price": 50000.0,
            "volume": 100.0
        }

        await provider._on_price_update(event)

        # Should not crash, just return early
        # No errors should be logged
        logger.error.assert_not_called()

        await provider.disconnect()


class TestExchangeInfo:
    """Test exchange information methods"""

    def test_get_exchange_name(self, provider):
        """Test get_exchange_name returns configured name"""
        assert provider.get_exchange_name() == "test_exchange"

    @pytest.mark.asyncio
    async def test_is_symbol_active_always_true(self, provider):
        """Test is_symbol_active returns True (simplified implementation)"""
        result = await provider.is_symbol_active("BTC_USDT")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_symbol_info_returns_none(self, provider):
        """Test get_symbol_info returns None (not implemented)"""
        result = await provider.get_symbol_info("BTC_USDT")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_24h_volume_returns_none(self, provider):
        """Test get_24h_volume returns None (not tracked)"""
        result = await provider.get_24h_volume("BTC_USDT")
        assert result is None


class TestResourceLimits:
    """Test resource limits and safety mechanisms"""

    @pytest.mark.asyncio
    async def test_max_symbols_enforcement(self, provider):
        """Test MAX_SYMBOLS limit is enforced"""
        provider.MAX_SYMBOLS = 2

        await provider.subscribe_to_symbol("BTC_USDT")
        await provider.subscribe_to_symbol("ETH_USDT")

        with pytest.raises(ValueError):
            await provider.subscribe_to_symbol("XRP_USDT")

    @pytest.mark.asyncio
    async def test_queue_timeout_prevents_blocking(self, provider, logger):
        """Test queue.put timeout prevents blocking on full queue"""
        await provider.connect()
        await provider.subscribe_to_symbol("BTC_USDT")

        # Fill queue to capacity
        provider.MAX_QUEUE_SIZE = 5
        queue = asyncio.Queue(maxsize=5)
        provider._queues["BTC_USDT"] = queue

        for i in range(5):
            await queue.put({"price": i})

        # Try to add more - should timeout and log warning
        event = {"symbol": "BTC_USDT", "price": 99999}
        await provider._on_price_update(event)

        # Verify warning was logged
        logger.warning.assert_called()

        await provider.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
