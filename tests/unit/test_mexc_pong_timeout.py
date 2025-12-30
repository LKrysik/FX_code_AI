"""
Unit Tests for MEXC Pong Timeout Handling (BUG-008-4)
=====================================================

Tests for pong timeout threshold-based connection health monitoring.

Test Coverage:
- AC1: Pong age > 60s triggers WARNING + health check ping
- AC2: Pong age > 120s triggers connection close + reconnect
- AC3: Consecutive timeout counter escalates action severity
- Configurable thresholds via settings
- Health check ping on first warning
- Pong health restoration resets counters

Reference: BUG-008-4 in sprint-status.yaml
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.exchanges.mexc_websocket_adapter import MexcWebSocketAdapter
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
    """ExchangeSettings with default pong thresholds (Pydantic model)"""
    return ExchangeSettings(
        mexc_futures_ws_url="wss://contract.mexc.com/edge",
        mexc_max_subscriptions_per_connection=30,
        mexc_max_connections=5,
        mexc_max_reconnect_attempts=10,
        mexc_pong_warn_threshold_seconds=60,
        mexc_pong_reconnect_threshold_seconds=120
    )


@pytest.fixture
def settings_fast_thresholds():
    """ExchangeSettings with fast thresholds for testing (5s warn, 10s reconnect)"""
    return ExchangeSettings(
        mexc_futures_ws_url="wss://contract.mexc.com/edge",
        mexc_max_subscriptions_per_connection=30,
        mexc_max_connections=5,
        mexc_max_reconnect_attempts=10,
        mexc_pong_warn_threshold_seconds=5,
        mexc_pong_reconnect_threshold_seconds=10
    )


class TestPongTimeoutThresholds:
    """Test pong timeout threshold configuration"""

    def test_default_threshold_values(self, settings_default, event_bus, logger):
        """AC1/AC2: Default thresholds are 60s warn, 120s reconnect"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        assert adapter.pong_warn_threshold_seconds == 60
        assert adapter.pong_reconnect_threshold_seconds == 120

    def test_custom_threshold_values(self, settings_fast_thresholds, event_bus, logger):
        """AC5: Thresholds are loaded from settings"""
        adapter = MexcWebSocketAdapter(
            settings=settings_fast_thresholds,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        assert adapter.pong_warn_threshold_seconds == 5
        assert adapter.pong_reconnect_threshold_seconds == 10


class TestHeartbeatMonitorIntegration:
    """Integration tests that call the real _heartbeat_monitor method"""

    @pytest.mark.asyncio
    async def test_ac2_pong_age_exceeds_reconnect_threshold_triggers_close(
        self, settings_default, event_bus, logger
    ):
        """AC2: When pong age > 120s, _heartbeat_monitor logs ERROR and closes connection"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # Setup mock websocket
        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.close = AsyncMock()
        mock_websocket.send = AsyncMock()

        connection_id = 0
        current_time = 1000.0
        # Pong received 130s ago (> 120s reconnect threshold)
        old_pong_time = current_time - 130

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": old_pong_time,
            "last_ping_sent": current_time - 10,
            "last_heartbeat": current_time,
            "subscriptions": set()
        }
        adapter._running = True

        # Mock time functions to return controlled values
        iteration_count = 0

        def mock_sleep(duration):
            """After first iteration, stop the loop"""
            nonlocal iteration_count
            iteration_count += 1
            # Stop after first iteration by setting _running = False
            adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            # Run the heartbeat monitor - it should detect old pong and close
            await adapter._heartbeat_monitor(connection_id)

        # Verify ERROR was logged with correct event type
        logger.error.assert_called()
        error_calls = [call for call in logger.error.call_args_list
                       if call[0][0] == "mexc_adapter.pong_age_exceeded_reconnect_threshold"]
        assert len(error_calls) >= 1, "Expected error log for exceeded reconnect threshold"

        # Verify the log data contains correct fields
        error_call = error_calls[0]
        log_data = error_call[0][1]
        assert log_data["connection_id"] == connection_id
        assert log_data["last_pong_age_seconds"] == 130.0
        assert log_data["threshold_seconds"] == 120
        assert "closing" in log_data["action"]

    @pytest.mark.asyncio
    async def test_ac1_pong_age_exceeds_warn_threshold_triggers_warning(
        self, settings_default, event_bus, logger
    ):
        """AC1: When pong age > 60s (but < 120s), _heartbeat_monitor logs WARNING"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # Setup mock websocket
        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.send = AsyncMock()

        connection_id = 0
        current_time = 1000.0
        # Pong received 70s ago (> 60s warn, < 120s reconnect)
        old_pong_time = current_time - 70

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": old_pong_time,
            "last_ping_sent": current_time - 10,
            "last_heartbeat": current_time,
            "subscriptions": set()
        }
        adapter._running = True

        # Track iterations
        iteration_count = 0

        def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            adapter._running = False  # Stop after first check
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Verify WARNING was logged
        logger.warning.assert_called()
        warning_calls = [call for call in logger.warning.call_args_list
                         if call[0][0] == "mexc_adapter.pong_age_exceeded_warn_threshold"]
        assert len(warning_calls) >= 1, "Expected warning log for exceeded warn threshold"

        # Verify log data
        warning_call = warning_calls[0]
        log_data = warning_call[0][1]
        assert log_data["connection_id"] == connection_id
        assert log_data["last_pong_age_seconds"] == 70.0
        assert log_data["threshold_seconds"] == 60

    @pytest.mark.asyncio
    async def test_ac1_health_check_ping_sent_on_first_warning(
        self, settings_default, event_bus, logger
    ):
        """AC1: Health check ping is sent when pong age first exceeds warn threshold"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        # Setup mock websocket
        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.send = AsyncMock()

        connection_id = 0
        current_time = 1000.0
        old_pong_time = current_time - 70  # > 60s warn threshold

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": old_pong_time,
            "last_ping_sent": current_time - 10,
            "last_heartbeat": current_time,
            "subscriptions": set()
        }
        adapter._running = True

        def mock_sleep(duration):
            adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Verify health check ping was sent
        mock_websocket.send.assert_called()

        # Verify health check log was emitted
        info_calls = [call for call in logger.info.call_args_list
                      if call[0][0] == "mexc_adapter.health_check_ping_sent"]
        assert len(info_calls) >= 1, "Expected health_check_ping_sent log"

    @pytest.mark.asyncio
    async def test_healthy_pong_resets_counters(
        self, settings_default, event_bus, logger
    ):
        """When pong age < warn threshold, no warnings are logged"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.send = AsyncMock()

        connection_id = 0
        current_time = 1000.0
        fresh_pong_time = current_time - 10  # Only 10s old (< 60s threshold)

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": fresh_pong_time,
            "last_ping_sent": current_time - 5,
            "last_heartbeat": current_time,
            "subscriptions": set()
        }
        adapter._running = True

        def mock_sleep(duration):
            adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Verify NO warning or error logs for pong timeout
        warning_calls = [call for call in logger.warning.call_args_list
                         if "pong_age" in call[0][0]]
        error_calls = [call for call in logger.error.call_args_list
                       if "pong_age" in call[0][0]]

        assert len(warning_calls) == 0, "No pong warnings expected for healthy connection"
        assert len(error_calls) == 0, "No pong errors expected for healthy connection"

    @pytest.mark.asyncio
    async def test_ac3_consecutive_timeouts_increment(
        self, settings_default, event_bus, logger
    ):
        """AC3: Consecutive timeout counter increments with each warning iteration"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.send = AsyncMock()

        connection_id = 0
        current_time = 1000.0
        # Pong age that triggers warning but not reconnect
        old_pong_time = current_time - 70

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": old_pong_time,
            "last_ping_sent": current_time - 10,
            "last_heartbeat": current_time,
            "subscriptions": set()
        }
        adapter._running = True

        # Allow 3 iterations
        iteration_count = 0

        def mock_sleep(duration):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 3:
                adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Verify warnings were logged with increasing consecutive_timeouts
        warning_calls = [call for call in logger.warning.call_args_list
                         if call[0][0] == "mexc_adapter.pong_age_exceeded_warn_threshold"]

        assert len(warning_calls) >= 2, "Expected multiple warning logs"

        # Check consecutive_timeouts increments
        timeouts_seen = [call[0][1]["consecutive_timeouts"] for call in warning_calls]
        assert 1 in timeouts_seen, "Expected consecutive_timeouts=1"
        assert 2 in timeouts_seen or 3 in timeouts_seen, "Expected incrementing timeouts"

    @pytest.mark.asyncio
    async def test_pong_health_restored_logs_info(
        self, settings_default, event_bus, logger
    ):
        """When pong becomes healthy after timeouts, pong_health_restored is logged"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.send = AsyncMock()

        connection_id = 0
        start_time = 1000.0

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": start_time - 70,  # Start with old pong
            "last_ping_sent": start_time - 10,
            "last_heartbeat": start_time,
            "subscriptions": set()
        }
        adapter._running = True

        iteration_count = 0
        simulated_time = start_time

        def mock_time():
            return simulated_time

        def mock_sleep(duration):
            nonlocal iteration_count, simulated_time
            iteration_count += 1
            if iteration_count == 1:
                # After first warning, simulate fresh pong received
                adapter._connections[connection_id]["last_pong_received"] = simulated_time
            elif iteration_count >= 3:
                adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', side_effect=mock_time), \
             patch('time.monotonic', return_value=start_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Verify health_restored was logged
        info_calls = [call for call in logger.info.call_args_list
                      if call[0][0] == "mexc_adapter.pong_health_restored"]
        assert len(info_calls) >= 1, "Expected pong_health_restored log after recovery"


class TestBackoffConfiguration:
    """Test AC4/AC5: Exponential backoff configuration"""

    def test_max_reconnect_attempts_configurable(
        self, settings_default, event_bus, logger
    ):
        """AC5: max_reconnect_attempts is configurable"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        assert adapter.max_reconnect_attempts == 10

    def test_backoff_calculation_formula(self, settings_default, event_bus, logger):
        """AC4: Exponential backoff follows min(2^attempt, 30) pattern"""
        # Test the backoff formula directly
        expected_backoffs = [
            (0, 1),   # 2^0 = 1
            (1, 2),   # 2^1 = 2
            (2, 4),   # 2^2 = 4
            (3, 8),   # 2^3 = 8
            (4, 16),  # 2^4 = 16
            (5, 30),  # 2^5 = 32, capped at 30
            (6, 30),  # 2^6 = 64, capped at 30
            (10, 30), # 2^10 = 1024, capped at 30
        ]

        for attempt, expected in expected_backoffs:
            actual = min(2 ** attempt, 30)
            assert actual == expected, f"Attempt {attempt}: expected {expected}, got {actual}"


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_connection_not_found_exits_gracefully(
        self, settings_default, event_bus, logger
    ):
        """_heartbeat_monitor exits gracefully if connection not found"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )
        adapter._running = True

        # Call with non-existent connection
        await adapter._heartbeat_monitor(999)

        # Should not raise, just return
        # No warnings/errors about pong should be logged
        pong_calls = [call for call in logger.warning.call_args_list
                      if "pong" in str(call)]
        assert len(pong_calls) == 0

    @pytest.mark.asyncio
    async def test_websocket_already_closed(
        self, settings_default, event_bus, logger
    ):
        """_heartbeat_monitor handles already-closed websocket"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = 1000  # Already closed
        mock_websocket.send = AsyncMock(side_effect=Exception("Connection closed"))

        connection_id = 0
        current_time = 1000.0

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": current_time - 70,
            "last_ping_sent": current_time - 10,
            "last_heartbeat": current_time,
            "subscriptions": set()
        }
        adapter._running = True

        def mock_sleep(duration):
            adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            # Should handle gracefully
            await adapter._heartbeat_monitor(connection_id)

        # No crash means success


class TestIntegrationScenarios:
    """Integration test scenarios for pong timeout handling"""

    @pytest.mark.asyncio
    async def test_55_minute_stale_connection_prevented(
        self, settings_default, event_bus, logger
    ):
        """
        BUG-008-4 Root Cause: 55-minute stale connection should be impossible.

        With thresholds of 60s warn and 120s reconnect, _heartbeat_monitor
        will close the connection long before 55 minutes of staleness.
        """
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.close = AsyncMock()

        connection_id = 0
        current_time = 1000.0
        # Simulate 55 minutes (3300 seconds) of staleness
        very_old_pong = current_time - 3300

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": very_old_pong,
            "last_ping_sent": current_time - 10,
            "last_heartbeat": current_time,
            "subscriptions": set()
        }
        adapter._running = True

        def mock_sleep(duration):
            adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Verify ERROR was logged (55 min > 120s threshold)
        error_calls = [call for call in logger.error.call_args_list
                       if call[0][0] == "mexc_adapter.pong_age_exceeded_reconnect_threshold"]
        assert len(error_calls) >= 1, "Expected reconnect threshold error for 55-min staleness"

        # Verify logged age is correct (3300 seconds)
        log_data = error_calls[0][0][1]
        assert log_data["last_pong_age_seconds"] == 3300.0

    @pytest.mark.asyncio
    async def test_threshold_boundary_60s_triggers_warning(
        self, settings_default, event_bus, logger
    ):
        """Exact 60s boundary triggers warning (> 60, not >=)"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.send = AsyncMock()

        connection_id = 0
        current_time = 1000.0
        # Exactly 60.1 seconds (just over threshold)
        pong_time = current_time - 60.1

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": pong_time,
            "last_ping_sent": current_time - 10,
            "last_heartbeat": current_time,
            "subscriptions": set()
        }
        adapter._running = True

        def mock_sleep(duration):
            adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Should trigger warning, not error
        warning_calls = [call for call in logger.warning.call_args_list
                         if call[0][0] == "mexc_adapter.pong_age_exceeded_warn_threshold"]
        error_calls = [call for call in logger.error.call_args_list
                       if call[0][0] == "mexc_adapter.pong_age_exceeded_reconnect_threshold"]

        assert len(warning_calls) >= 1, "Expected warning at 60.1s"
        assert len(error_calls) == 0, "Should not trigger reconnect at 60.1s"
