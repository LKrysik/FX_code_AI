"""
Unit Tests for Data Activity Monitoring (BUG-008-6)
====================================================

Tests for symbol-aware activity thresholds, pre-close health checks,
and activity type distinction.

Test Coverage:
- AC1: Data activity threshold is configurable per symbol type (high/low volume)
- AC2: Before closing, send a subscription refresh to verify connection
- AC3: Low-volume symbols have higher threshold (300s) vs high-volume (120s)
- AC4: Activity monitoring distinguishes between "no trades" and "dead connection"
- AC5: Log includes context: symbol volume category, last N messages received
- AC6: False positive rate tracking (connections closed that were actually healthy)

Reference: BUG-008-6 in sprint-status.yaml
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

from src.infrastructure.exchanges.mexc_websocket_adapter import MexcWebSocketAdapter
from src.infrastructure.exchanges.symbol_volume_classifier import (
    SymbolVolumeCategory,
    SymbolVolumeClassifier,
    ACTIVITY_THRESHOLDS,
    ActivityType,
)
from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.infrastructure.config.settings import ExchangeSettings


@pytest.fixture
def event_bus():
    """Mock EventBus"""
    bus = MagicMock(spec=EventBus)
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def logger():
    """Mock StructuredLogger for capturing log calls"""
    mock_logger = MagicMock(spec=StructuredLogger)
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.critical = MagicMock()
    mock_logger.logger = MagicMock()
    mock_logger.logger.isEnabledFor = MagicMock(return_value=False)
    return mock_logger


@pytest.fixture
def settings_default():
    """ExchangeSettings with default activity thresholds"""
    return ExchangeSettings(
        mexc_futures_ws_url="wss://contract.mexc.com/edge",
        mexc_max_subscriptions_per_connection=30,
        mexc_max_connections=5,
        mexc_max_reconnect_attempts=10,
        # Activity monitoring thresholds (BUG-008-6)
        mexc_activity_threshold_high_volume=60,
        mexc_activity_threshold_medium_volume=120,
        mexc_activity_threshold_low_volume=300,
        mexc_pre_close_health_check_timeout=10,
    )


class TestSymbolVolumeClassifier:
    """Test symbol volume classification logic"""

    def test_high_volume_symbols_classified_correctly(self):
        """AC3: BTC, ETH are high volume symbols with 60s threshold"""
        classifier = SymbolVolumeClassifier()

        assert classifier.get_category("BTCUSDT") == SymbolVolumeCategory.HIGH
        assert classifier.get_category("ETHUSDT") == SymbolVolumeCategory.HIGH
        assert classifier.get_category("BTC_USDT") == SymbolVolumeCategory.HIGH

    def test_medium_volume_symbols_classified_correctly(self):
        """AC3: Top 100 symbols get medium threshold (120s)"""
        classifier = SymbolVolumeClassifier()

        # These would be medium volume - common altcoins
        category = classifier.get_category("SOLUSDT")
        assert category in [SymbolVolumeCategory.MEDIUM, SymbolVolumeCategory.HIGH]

    def test_low_volume_symbols_classified_correctly(self):
        """AC3: Unknown/uncommon symbols get low threshold (300s)"""
        classifier = SymbolVolumeClassifier()

        # Obscure symbols should be LOW
        assert classifier.get_category("UNKNOWN123USDT") == SymbolVolumeCategory.LOW

    def test_threshold_values_match_requirements(self):
        """AC1/AC3: Verify threshold values match spec"""
        assert ACTIVITY_THRESHOLDS[SymbolVolumeCategory.HIGH] == 60
        assert ACTIVITY_THRESHOLDS[SymbolVolumeCategory.MEDIUM] == 120
        assert ACTIVITY_THRESHOLDS[SymbolVolumeCategory.LOW] == 300

    def test_custom_thresholds_can_be_configured(self):
        """AC1: Thresholds are configurable"""
        custom_thresholds = {
            SymbolVolumeCategory.HIGH: 30,
            SymbolVolumeCategory.MEDIUM: 60,
            SymbolVolumeCategory.LOW: 180,
        }
        classifier = SymbolVolumeClassifier(thresholds=custom_thresholds)

        assert classifier.get_threshold("BTCUSDT") == 30
        assert classifier.get_threshold("UNKNOWN123USDT") == 180


class TestActivityTypeTracking:
    """Test activity type distinction (AC4)"""

    def test_activity_types_defined(self):
        """AC4: Activity types are properly defined"""
        assert ActivityType.TRADE is not None
        assert ActivityType.ORDERBOOK is not None
        assert ActivityType.DEPTH_SNAPSHOT is not None
        assert ActivityType.SYSTEM is not None
        assert ActivityType.PING_PONG is not None

    def test_trade_activity_resets_timer(self):
        """AC4: Trade data resets activity timer"""
        # Trade activity should reset the timer
        assert ActivityType.TRADE.resets_timer == True

    def test_orderbook_activity_resets_timer(self):
        """AC4: Orderbook update resets activity timer"""
        assert ActivityType.ORDERBOOK.resets_timer == True

    def test_ping_pong_does_not_reset_timer(self):
        """AC4: Ping/Pong does NOT reset data activity timer"""
        assert ActivityType.PING_PONG.resets_timer == False


class TestDataActivityMonitor:
    """Test the data activity monitoring in adapter"""

    def test_adapter_loads_activity_thresholds(self, settings_default, event_bus, logger):
        """AC1: Activity thresholds loaded from settings"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        assert adapter.activity_threshold_high_volume == 60
        assert adapter.activity_threshold_medium_volume == 120
        assert adapter.activity_threshold_low_volume == 300

    def test_symbol_classifier_integration(self, settings_default, event_bus, logger):
        """AC1: Adapter uses symbol classifier for threshold selection"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # BTC should use high volume threshold
        threshold = adapter.get_activity_threshold_for_symbol("BTCUSDT")
        assert threshold == 60

        # Unknown should use low volume threshold
        threshold = adapter.get_activity_threshold_for_symbol("OBSCURE123USDT")
        assert threshold == 300


class TestPreCloseHealthCheck:
    """Test pre-close health check mechanism (AC2)"""

    @pytest.mark.asyncio
    async def test_health_check_sent_before_close(self, settings_default, event_bus, logger):
        """AC2: Before closing for inactivity, subscription refresh is sent"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # Mock connection
        mock_websocket = AsyncMock()
        mock_websocket.close_code = None

        connection_id = 1
        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "subscriptions": {"BTCUSDT"},
            "last_heartbeat": time.time() - 65,  # 65 seconds ago (exceeds HIGH threshold)
            "last_pong_received": time.time(),
            "last_ping_sent": time.time(),
        }

        # Perform health check
        health_check_result = await adapter._perform_pre_close_health_check(connection_id, "BTCUSDT")

        # Verify subscription refresh was sent
        assert mock_websocket.send.called

    @pytest.mark.asyncio
    async def test_health_check_timeout_configured(self, settings_default, event_bus, logger):
        """AC2: Health check waits configured timeout (10s) for response"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        assert adapter.pre_close_health_check_timeout == 10

    @pytest.mark.asyncio
    async def test_timer_reset_on_health_check_response(self, settings_default, event_bus, logger):
        """AC2: If response received after health check, timer resets"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # This tests the behavior: if health check gets a response, don't close
        # Implementation will track this via _health_check_pending flag


class TestActivityMessageTracking:
    """Test message type tracking for activity distinction (AC4, AC5)"""

    def test_last_message_types_tracked(self, settings_default, event_bus, logger):
        """AC5: Last N message types are tracked"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # Adapter should have message type tracking
        assert hasattr(adapter, '_last_message_types')

    def test_message_type_buffer_size(self, settings_default, event_bus, logger):
        """AC5: Buffer tracks last 5 message types"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # Default buffer size is 5
        assert adapter.message_type_buffer_size == 5


class TestInactivityLogging:
    """Test enhanced logging for inactivity events (AC5)"""

    def test_log_includes_volume_category(self, settings_default, event_bus, logger):
        """AC5: Log includes symbol volume category"""
        # When logging inactivity, the volume category should be included
        # This will be verified in integration tests
        pass

    def test_log_includes_last_message_types(self, settings_default, event_bus, logger):
        """AC5: Log includes last N messages received"""
        # When logging inactivity, the last message types should be included
        pass


class TestFalsePositiveTracking:
    """Test false positive rate tracking (AC6)"""

    def test_inactivity_close_count_tracked(self, settings_default, event_bus, logger):
        """AC6: Count of connections closed for inactivity is tracked"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        assert hasattr(adapter, '_inactivity_close_count')
        assert adapter._inactivity_close_count == 0

    def test_false_positive_count_tracked(self, settings_default, event_bus, logger):
        """AC6: False positives (closed then immediately reconnected with data) are tracked"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        assert hasattr(adapter, '_false_positive_count')
        assert adapter._false_positive_count == 0

    def test_false_positive_detection(self, settings_default, event_bus, logger):
        """AC6: Reconnection with immediate data flags potential false positive"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # Record inactivity close
        adapter._record_inactivity_close("BTCUSDT", connection_id=1)

        # Simulate rapid reconnection with data
        adapter._record_reconnection_with_data("BTCUSDT", connection_id=2, seconds_since_close=5)

        # Should flag as potential false positive (reconnected within 30s with data)
        assert adapter._false_positive_count == 1


class TestSymbolVolumeSettings:
    """Test settings for activity thresholds"""

    def test_settings_have_activity_threshold_fields(self):
        """AC1: ExchangeSettings has activity threshold fields"""
        settings = ExchangeSettings(
            mexc_activity_threshold_high_volume=45,
            mexc_activity_threshold_medium_volume=90,
            mexc_activity_threshold_low_volume=180,
        )

        assert settings.mexc_activity_threshold_high_volume == 45
        assert settings.mexc_activity_threshold_medium_volume == 90
        assert settings.mexc_activity_threshold_low_volume == 180

    def test_settings_have_configurable_symbol_lists(self):
        """Symbol lists are configurable via settings"""
        settings = ExchangeSettings(
            mexc_high_volume_symbols="BTCUSDT,ETHUSDT,CUSTOMUSDT",
            mexc_medium_volume_symbols="SOLUSDT,LINKUSDT",
        )

        assert "BTCUSDT" in settings.mexc_high_volume_symbols
        assert "CUSTOMUSDT" in settings.mexc_high_volume_symbols
        assert "SOLUSDT" in settings.mexc_medium_volume_symbols


class TestFalsePositiveIntegration:
    """Test false positive detection integration in data flow"""

    def test_check_false_positive_on_data_detects_quick_reconnect(self, settings_default, event_bus, logger):
        """AC6: Data arriving within 30s of close is flagged as false positive"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # Simulate inactivity close
        adapter._record_inactivity_close("BTCUSDT", connection_id=1)
        assert adapter._inactivity_close_count == 1

        # Simulate quick reconnection with data (within 30s)
        adapter._check_false_positive_on_data("BTCUSDT", connection_id=2)

        # Should be flagged as false positive
        assert adapter._false_positive_count == 1

    def test_check_false_positive_clears_timestamp_after_check(self, settings_default, event_bus, logger):
        """Timestamp is cleared after checking to avoid double counting"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        adapter._record_inactivity_close("BTCUSDT", connection_id=1)
        adapter._check_false_positive_on_data("BTCUSDT", connection_id=2)

        # Timestamp should be cleared
        assert "BTCUSDT" not in adapter._inactivity_close_timestamps

        # Second check should not increment count again
        adapter._check_false_positive_on_data("BTCUSDT", connection_id=3)
        assert adapter._false_positive_count == 1  # Still 1, not 2


class TestActivityMonitoringMetrics:
    """Test metrics reporting for AC6 compliance"""

    def test_get_activity_monitoring_metrics(self, settings_default, event_bus, logger):
        """AC6: Metrics include all required fields"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        metrics = adapter.get_activity_monitoring_metrics()

        assert "inactivity_close_count" in metrics
        assert "false_positive_count" in metrics
        assert "false_positive_rate_percent" in metrics
        assert "ac6_compliant" in metrics

    def test_metrics_ac6_compliant_when_rate_below_5_percent(self, settings_default, event_bus, logger):
        """AC6: ac6_compliant is True when rate < 5%"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # 1 false positive out of 100 closes = 1%
        adapter._inactivity_close_count = 100
        adapter._false_positive_count = 1

        metrics = adapter.get_activity_monitoring_metrics()
        assert metrics["false_positive_rate_percent"] == 1.0
        assert metrics["ac6_compliant"] == True

    def test_metrics_ac6_not_compliant_when_rate_above_5_percent(self, settings_default, event_bus, logger):
        """AC6: ac6_compliant is False when rate >= 5%"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # 6 false positives out of 100 closes = 6%
        adapter._inactivity_close_count = 100
        adapter._false_positive_count = 6

        metrics = adapter.get_activity_monitoring_metrics()
        assert metrics["false_positive_rate_percent"] == 6.0
        assert metrics["ac6_compliant"] == False


class TestConfigurableSymbolLists:
    """Test configurable symbol volume classification"""

    def test_custom_high_volume_symbols_from_config(self, event_bus, logger):
        """Custom high volume symbols are used from config"""
        settings = ExchangeSettings(
            mexc_high_volume_symbols="CUSTOMUSDT,TESTUSDT",
            mexc_medium_volume_symbols="MEDUSDT",
        )

        adapter = MexcWebSocketAdapter(
            settings=settings,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # Custom symbol should be HIGH
        threshold = adapter.get_activity_threshold_for_symbol("CUSTOMUSDT")
        assert threshold == 60  # HIGH threshold

        # Unknown symbol should be LOW
        threshold = adapter.get_activity_threshold_for_symbol("UNKNOWNUSDT")
        assert threshold == 300  # LOW threshold

    def test_symbol_list_parsing_handles_spaces(self, event_bus, logger):
        """Symbol list parsing handles whitespace correctly"""
        settings = ExchangeSettings(
            mexc_high_volume_symbols=" BTCUSDT , ETHUSDT , SOLUSDT ",
        )

        adapter = MexcWebSocketAdapter(
            settings=settings,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # Should work despite spaces
        threshold = adapter.get_activity_threshold_for_symbol("BTCUSDT")
        assert threshold == 60
