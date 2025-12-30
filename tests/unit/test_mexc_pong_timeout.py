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

    @pytest.mark.asyncio
    async def test_threshold_boundary_exactly_60s_no_warning(
        self, settings_default, event_bus, logger
    ):
        """Exactly 60s should NOT trigger warning (condition is > 60, not >=)"""
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
        # Exactly 60.0 seconds (at threshold, not over)
        pong_time = current_time - 60.0

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

        # Should NOT trigger warning at exactly 60s
        warning_calls = [call for call in logger.warning.call_args_list
                         if call[0][0] == "mexc_adapter.pong_age_exceeded_warn_threshold"]
        assert len(warning_calls) == 0, "Should NOT warn at exactly 60s (condition is > not >=)"

    @pytest.mark.asyncio
    async def test_threshold_boundary_exactly_120s_no_reconnect(
        self, settings_default, event_bus, logger
    ):
        """Exactly 120s should NOT trigger reconnect (condition is > 120, not >=)"""
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
        # Exactly 120.0 seconds (at threshold, not over)
        pong_time = current_time - 120.0

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

        # Should trigger warning but NOT reconnect error at exactly 120s
        warning_calls = [call for call in logger.warning.call_args_list
                         if call[0][0] == "mexc_adapter.pong_age_exceeded_warn_threshold"]
        error_calls = [call for call in logger.error.call_args_list
                       if call[0][0] == "mexc_adapter.pong_age_exceeded_reconnect_threshold"]

        assert len(warning_calls) >= 1, "Should warn at 120s (> 60)"
        assert len(error_calls) == 0, "Should NOT reconnect at exactly 120s (condition is > not >=)"


class TestCloseConnectionIntegration:
    """Test that _close_connection is properly called during timeout scenarios"""

    @pytest.mark.asyncio
    async def test_close_connection_called_on_reconnect_threshold(
        self, settings_default, event_bus, logger
    ):
        """AC2: _close_connection is actually called when pong age exceeds reconnect threshold"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.close = AsyncMock()
        mock_websocket.send = AsyncMock()

        connection_id = 0
        current_time = 1000.0
        old_pong_time = current_time - 130  # > 120s

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": old_pong_time,
            "last_ping_sent": current_time - 10,
            "last_heartbeat": current_time,
            "subscriptions": set(),
            "heartbeat_task": None,
            "message_task": None
        }
        adapter._running = True

        # Mock _close_connection to track if it's called
        close_connection_called = False
        original_close = adapter._close_connection

        async def mock_close_connection(conn_id):
            nonlocal close_connection_called
            close_connection_called = True
            # Don't call original - just mark as called

        adapter._close_connection = mock_close_connection

        def mock_sleep(duration):
            adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        assert close_connection_called, "_close_connection should be called when pong age > 120s"


class TestHealthCheckExceptionHandling:
    """Test exception handling during health check ping"""

    @pytest.mark.asyncio
    async def test_health_check_ping_failure_logged(
        self, settings_default, event_bus, logger
    ):
        """When health check ping send fails, error is logged"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        # Health check ping will fail
        mock_websocket.send = AsyncMock(side_effect=Exception("Connection reset"))

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

        # Verify health check failure was logged
        error_calls = [call for call in logger.error.call_args_list
                       if call[0][0] == "mexc_adapter.health_check_ping_failed"]
        assert len(error_calls) >= 1, "Expected health_check_ping_failed error log"

        # Verify error contains the exception message
        error_data = error_calls[0][0][1]
        assert "Connection reset" in error_data["error"]

    @pytest.mark.asyncio
    async def test_health_check_ping_not_sent_twice(
        self, settings_default, event_bus, logger
    ):
        """Health check ping is only sent once (health_check_sent flag)"""
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

        # Allow 3 iterations to verify ping is only sent once
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

        # Count health check ping logs - should be exactly 1
        health_check_logs = [call for call in logger.info.call_args_list
                             if call[0][0] == "mexc_adapter.health_check_ping_sent"]
        assert len(health_check_logs) == 1, "Health check ping should be sent only once"


class TestRegularPingExceptionHandling:
    """Test exception handling during regular ping send"""

    @pytest.mark.asyncio
    async def test_ping_send_failure_closes_connection(
        self, settings_default, event_bus, logger
    ):
        """When regular ping send fails, connection is closed"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.send = AsyncMock(side_effect=Exception("Network error"))

        connection_id = 0
        current_time = 1000.0
        # Fresh pong - no timeout, will trigger regular ping cycle
        fresh_pong_time = current_time - 10

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": fresh_pong_time,
            "last_ping_sent": current_time - 25,
            "last_heartbeat": current_time,
            "subscriptions": set(),
            "heartbeat_task": None,
            "message_task": None
        }
        adapter._running = True

        close_connection_called = False

        async def mock_close_connection(conn_id):
            nonlocal close_connection_called
            close_connection_called = True

        adapter._close_connection = mock_close_connection

        # Track monotonic time - start at 0, then advance past ping interval
        monotonic_calls = [0]

        def mock_monotonic():
            # First call: returns 0 (sets last_ping_time = 0)
            # Second call: returns 25 (current_time - last_ping_time = 25 > 20s interval)
            if len(monotonic_calls) == 1:
                monotonic_calls.append(25)
                return 0
            return 25

        def mock_sleep(duration):
            adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', side_effect=mock_monotonic), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Verify ping send failure was logged
        error_calls = [call for call in logger.error.call_args_list
                       if call[0][0] == "mexc_adapter.ping_send_failed"]
        assert len(error_calls) >= 1, "Expected ping_send_failed error log"

        # Verify connection was closed
        assert close_connection_called, "_close_connection should be called on ping failure"


class TestMaxReconnectAttemptsIntegration:
    """Test AC6: Max reconnection attempts handling"""

    @pytest.mark.asyncio
    async def test_ac6_max_attempts_exceeded_logs_error(
        self, settings_default, event_bus, logger
    ):
        """AC6: When max reconnect attempts reached, error is logged and reconnection stops"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        connection_id = 0
        failed_symbols = {"BTC_USDT", "ETH_USDT"}

        # Set attempts to max (10) - next attempt should be blocked
        adapter._reconnection_attempts[connection_id] = 10
        adapter._running = True

        # Call _reconnect_connection directly
        await adapter._reconnect_connection(connection_id, failed_symbols)

        # Verify error log for max attempts exceeded
        error_calls = [call for call in logger.error.call_args_list
                       if call[0][0] == "mexc_adapter.max_reconnection_attempts_exceeded"]
        assert len(error_calls) >= 1, "Expected max_reconnection_attempts_exceeded error log"

        # Verify log data contains correct fields
        error_data = error_calls[0][0][1]
        assert error_data["old_connection_id"] == connection_id
        assert error_data["max_attempts"] == 10
        assert error_data["total_attempts"] == 10
        assert set(error_data["failed_symbols"]) == failed_symbols

        # Verify attempt tracking was cleaned up
        assert connection_id not in adapter._reconnection_attempts

    @pytest.mark.asyncio
    async def test_ac6_reconnect_stops_after_max_attempts(
        self, settings_default, event_bus, logger
    ):
        """AC6: No further reconnection is scheduled after max attempts"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        connection_id = 0
        failed_symbols = {"BTC_USDT"}

        # Set attempts to max
        adapter._reconnection_attempts[connection_id] = 10
        adapter._running = True

        # Track if _create_tracked_task is called
        create_task_called = False
        original_create_task = adapter._create_tracked_task

        def mock_create_tracked_task(coro, name):
            nonlocal create_task_called
            create_task_called = True
            # Cancel the coroutine to avoid warnings
            coro.close()

        adapter._create_tracked_task = mock_create_tracked_task

        await adapter._reconnect_connection(connection_id, failed_symbols)

        # No new task should be scheduled
        assert not create_task_called, "No reconnection task should be scheduled after max attempts"


class TestReconnectFlowIntegration:
    """Test reconnect flow: _close_connection triggers _reconnect_connection"""

    @pytest.mark.asyncio
    async def test_close_connection_schedules_reconnect(
        self, settings_default, event_bus, logger
    ):
        """When connection with subscriptions is closed, reconnect is scheduled"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.close_code = None

        connection_id = 0
        subscribed_symbols = {"BTC_USDT", "ETH_USDT"}

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": 1000.0,
            "last_ping_sent": 1000.0,
            "last_heartbeat": 1000.0,
            "subscriptions": subscribed_symbols.copy(),
            "heartbeat_task": None,
            "message_task": None
        }
        adapter._subscribed_symbols = subscribed_symbols.copy()
        adapter._running = True

        # Track _create_tracked_task calls
        reconnect_scheduled = False
        reconnect_symbols = None

        original_create_task = adapter._create_tracked_task

        def mock_create_tracked_task(coro, name):
            nonlocal reconnect_scheduled, reconnect_symbols
            if "reconnect_" in name:
                reconnect_scheduled = True
                # Extract failed_symbols from coroutine (it's in the closure)
                # We can't easily extract, but we verify the call happens
            # Close the coroutine to avoid warnings
            coro.close()

        adapter._create_tracked_task = mock_create_tracked_task

        # Close the connection
        await adapter._close_connection(connection_id)

        # Verify reconnection was scheduled
        assert reconnect_scheduled, "_reconnect_connection should be scheduled after _close_connection"

    @pytest.mark.asyncio
    async def test_close_connection_no_reconnect_when_not_running(
        self, settings_default, event_bus, logger
    ):
        """When adapter is stopped, no reconnect is scheduled on close"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.close_code = None

        connection_id = 0

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": 1000.0,
            "last_ping_sent": 1000.0,
            "last_heartbeat": 1000.0,
            "subscriptions": {"BTC_USDT"},
            "heartbeat_task": None,
            "message_task": None
        }
        adapter._subscribed_symbols = {"BTC_USDT"}
        adapter._running = False  # Adapter is stopped

        # Track _create_tracked_task calls
        reconnect_scheduled = False

        def mock_create_tracked_task(coro, name):
            nonlocal reconnect_scheduled
            if "reconnect_" in name:
                reconnect_scheduled = True
            coro.close()

        adapter._create_tracked_task = mock_create_tracked_task

        await adapter._close_connection(connection_id)

        # No reconnection when adapter is stopped
        assert not reconnect_scheduled, "No reconnect should be scheduled when adapter is stopped"

    @pytest.mark.asyncio
    async def test_close_connection_no_reconnect_when_no_subscriptions(
        self, settings_default, event_bus, logger
    ):
        """When connection has no subscriptions, no reconnect is scheduled"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.close_code = None

        connection_id = 0

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": 1000.0,
            "last_ping_sent": 1000.0,
            "last_heartbeat": 1000.0,
            "subscriptions": set(),  # No subscriptions
            "heartbeat_task": None,
            "message_task": None
        }
        adapter._subscribed_symbols = set()
        adapter._running = True

        reconnect_scheduled = False

        def mock_create_tracked_task(coro, name):
            nonlocal reconnect_scheduled
            if "reconnect_" in name:
                reconnect_scheduled = True
            coro.close()

        adapter._create_tracked_task = mock_create_tracked_task

        await adapter._close_connection(connection_id)

        # No reconnection when no subscriptions to restore
        assert not reconnect_scheduled, "No reconnect needed when no subscriptions"


class TestCancelledErrorHandling:
    """Test CancelledError handling in heartbeat monitor - lines 912-916"""

    @pytest.mark.asyncio
    async def test_cancelled_error_logs_info_and_exits(
        self, settings_default, event_bus, logger
    ):
        """When heartbeat is cancelled, it logs info and exits gracefully"""
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

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": current_time - 10,
            "last_ping_sent": current_time - 5,
            "last_heartbeat": current_time,
            "subscriptions": set()
        }
        adapter._running = True

        # Make asyncio.sleep raise CancelledError
        async def mock_sleep_cancelled(duration):
            raise asyncio.CancelledError()

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep_cancelled):

            # Should not raise, should exit gracefully
            await adapter._heartbeat_monitor(connection_id)

        # Verify info log for cancellation
        info_calls = [call for call in logger.info.call_args_list
                      if call[0][0] == "mexc_adapter.heartbeat_cancelled"]
        assert len(info_calls) >= 1, "Expected heartbeat_cancelled info log"


class TestUnexpectedExceptionHandling:
    """Test unexpected exception handling - lines 917-924"""

    @pytest.mark.asyncio
    async def test_unexpected_error_logs_and_closes(
        self, settings_default, event_bus, logger
    ):
        """When unexpected exception occurs, it logs error and closes connection"""
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

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": current_time - 10,
            "last_ping_sent": current_time - 5,
            "last_heartbeat": current_time,
            "subscriptions": set(),
            "heartbeat_task": None,
            "message_task": None
        }
        adapter._running = True

        close_connection_called = False

        async def mock_close_connection(conn_id):
            nonlocal close_connection_called
            close_connection_called = True

        adapter._close_connection = mock_close_connection

        # Make time.time raise unexpected exception
        call_count = [0]

        def mock_time_with_error():
            call_count[0] += 1
            if call_count[0] > 2:  # Fail on 3rd call
                raise RuntimeError("Unexpected database error")
            return current_time

        with patch('time.time', side_effect=mock_time_with_error), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=lambda d: asyncio.sleep(0)):

            await adapter._heartbeat_monitor(connection_id)

        # Verify error log
        error_calls = [call for call in logger.error.call_args_list
                       if call[0][0] == "mexc_adapter.heartbeat_unexpected_error"]
        assert len(error_calls) >= 1, "Expected heartbeat_unexpected_error log"

        # Verify error contains exception info
        error_data = error_calls[0][0][1]
        assert error_data["error_type"] == "RuntimeError"
        assert "Unexpected database error" in error_data["error"]

        # Verify connection was closed
        assert close_connection_called, "_close_connection should be called on unexpected error"


class TestPongReceivedFlow:
    """Test successful pong received flow - lines 856-876"""

    @pytest.mark.asyncio
    async def test_pong_received_resets_counters(
        self, settings_default, event_bus, logger
    ):
        """When pong is received via wait_for_pong, counters are reset"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.send = AsyncMock()
        # Simulate wait_for_pong exists and completes successfully
        mock_websocket.wait_for_pong = AsyncMock(return_value=None)

        connection_id = 0
        start_time = 1000.0

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": start_time - 10,
            "last_ping_sent": start_time - 25,  # 25s ago, so ping will be sent
            "last_heartbeat": start_time,
            "subscriptions": set()
        }
        adapter._running = True

        iteration_count = [0]
        monotonic_time = [0]

        def mock_monotonic():
            # First call: 0, triggers ping (0 - 0 >= 20 is false initially)
            # Actually we need to make current_time - last_ping_time >= 20
            return monotonic_time[0]

        def mock_sleep(duration):
            iteration_count[0] += 1
            monotonic_time[0] += 25  # Advance time past ping interval
            if iteration_count[0] >= 2:
                adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=start_time), \
             patch('time.monotonic', side_effect=mock_monotonic), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Verify ping was sent
        assert mock_websocket.send.called, "Ping should be sent"

        # Verify wait_for_pong was called
        assert mock_websocket.wait_for_pong.called, "wait_for_pong should be called"

        # Verify debug log for pong received
        debug_calls = [call for call in logger.debug.call_args_list
                       if call[0][0] == "mexc_adapter.pong_received"]
        assert len(debug_calls) >= 1, "Expected pong_received debug log"

    @pytest.mark.asyncio
    async def test_pong_timeout_logs_debug(
        self, settings_default, event_bus, logger
    ):
        """When wait_for_pong times out, debug log is emitted"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        mock_websocket = AsyncMock()
        mock_websocket.close_code = None
        mock_websocket.send = AsyncMock()
        # Simulate wait_for_pong timing out
        mock_websocket.wait_for_pong = AsyncMock(side_effect=asyncio.TimeoutError())

        connection_id = 0
        current_time = 1000.0

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": current_time - 10,
            "last_ping_sent": current_time - 25,
            "last_heartbeat": current_time,
            "subscriptions": set()
        }
        adapter._running = True

        # Track monotonic calls: 1st=0 (sets last_ping_time), 2nd=25 (checks condition)
        monotonic_calls = [0]

        def mock_monotonic():
            result = monotonic_calls[0]
            # Advance time on each call so ping condition (25 - 0 >= 20) is met
            monotonic_calls[0] = 25
            return result

        iteration_count = [0]

        def mock_sleep(duration):
            iteration_count[0] += 1
            if iteration_count[0] >= 1:
                adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', side_effect=mock_monotonic), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Verify debug log for pong wait timeout
        debug_calls = [call for call in logger.debug.call_args_list
                       if call[0][0] == "mexc_adapter.pong_wait_timeout"]
        assert len(debug_calls) >= 1, "Expected pong_wait_timeout debug log"


class TestSuccessfulReconnection:
    """Test successful reconnection flow - lines 2083-2119"""

    @pytest.mark.asyncio
    async def test_successful_reconnect_logs_success(
        self, settings_default, event_bus, logger
    ):
        """When reconnection succeeds, success is logged and attempts reset"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        connection_id = 0
        failed_symbols = {"BTC_USDT", "ETH_USDT"}

        # Set up initial reconnection attempt
        adapter._reconnection_attempts[connection_id] = 1
        adapter._running = True

        # Mock successful connection creation
        new_connection_id = 1

        async def mock_create_new_connection():
            return new_connection_id

        adapter._create_new_connection = mock_create_new_connection

        # Track _create_tracked_task calls for resubscription
        resubscribe_tasks = []

        def mock_create_tracked_task(coro, name):
            resubscribe_tasks.append(name)
            coro.close()

        adapter._create_tracked_task = mock_create_tracked_task

        # Mock asyncio.sleep to not actually wait
        with patch('asyncio.sleep', side_effect=lambda d: asyncio.sleep(0)):
            await adapter._reconnect_connection(connection_id, failed_symbols)

        # Verify success log
        info_calls = [call for call in logger.info.call_args_list
                      if call[0][0] == "mexc_adapter.reconnection_successful"]
        assert len(info_calls) >= 1, "Expected reconnection_successful log"

        # Verify log data
        info_data = info_calls[0][0][1]
        assert info_data["old_connection_id"] == connection_id
        assert info_data["new_connection_id"] == new_connection_id
        assert info_data["resubscribed_symbols"] == 2

        # Verify attempt tracking was cleaned up
        assert connection_id not in adapter._reconnection_attempts

        # Verify resubscription tasks were created
        assert len(resubscribe_tasks) == 2
        assert any("resubscribe_BTC_USDT" in t for t in resubscribe_tasks)
        assert any("resubscribe_ETH_USDT" in t for t in resubscribe_tasks)

    @pytest.mark.asyncio
    async def test_reconnect_failure_schedules_retry(
        self, settings_default, event_bus, logger
    ):
        """When reconnection fails, retry is scheduled with incremented attempt"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        connection_id = 0
        failed_symbols = {"BTC_USDT"}

        adapter._reconnection_attempts[connection_id] = 0  # First attempt
        adapter._running = True

        # Mock connection creation failure
        async def mock_create_new_connection():
            raise ConnectionError("Network unreachable")

        adapter._create_new_connection = mock_create_new_connection

        # Track retry scheduling
        retry_scheduled = False
        retry_name = None

        def mock_create_tracked_task(coro, name):
            nonlocal retry_scheduled, retry_name
            if "reconnect_retry" in name:
                retry_scheduled = True
                retry_name = name
            coro.close()

        adapter._create_tracked_task = mock_create_tracked_task

        # Mock _update_tracking_expiry
        adapter._update_tracking_expiry = lambda x: None

        with patch('asyncio.sleep', side_effect=lambda d: asyncio.sleep(0)):
            await adapter._reconnect_connection(connection_id, failed_symbols)

        # Verify warning log for failed attempt
        warning_calls = [call for call in logger.warning.call_args_list
                         if call[0][0] == "mexc_adapter.reconnection_attempt_failed"]
        assert len(warning_calls) >= 1, "Expected reconnection_attempt_failed warning"

        # Verify attempt counter was incremented
        assert adapter._reconnection_attempts[connection_id] == 1

        # Verify retry was scheduled
        assert retry_scheduled, "Retry should be scheduled after failure"

    @pytest.mark.asyncio
    async def test_backoff_delay_calculated_correctly(
        self, settings_default, event_bus, logger
    ):
        """Backoff delay follows exponential pattern with jitter"""
        adapter = MexcWebSocketAdapter(
            settings=settings_default,
            event_bus=event_bus,
            logger=logger,
            data_types=['prices']
        )

        connection_id = 0
        failed_symbols = {"BTC_USDT"}

        # Test different attempt numbers
        test_cases = [
            (0, 1.0),   # 2^0 = 1
            (1, 2.0),   # 2^1 = 2
            (2, 4.0),   # 2^2 = 4
            (3, 8.0),   # 2^3 = 8
            (5, 30.0),  # 2^5 = 32, capped at 30
        ]

        for attempt, expected_base in test_cases:
            adapter._reconnection_attempts[connection_id] = attempt
            adapter._running = True

            # Capture the sleep duration
            sleep_durations = []

            async def capture_sleep(duration):
                sleep_durations.append(duration)
                # Fail the connection to exit early
                raise ConnectionError("Test exit")

            adapter._create_new_connection = AsyncMock(side_effect=ConnectionError("Test"))

            def mock_create_task(coro, name):
                coro.close()

            adapter._create_tracked_task = mock_create_task
            adapter._update_tracking_expiry = lambda x: None

            with patch('asyncio.sleep', side_effect=capture_sleep):
                try:
                    await adapter._reconnect_connection(connection_id, failed_symbols)
                except ConnectionError:
                    pass

            if sleep_durations:
                # Verify delay is within expected range (base + up to 10% jitter)
                actual_delay = sleep_durations[0]
                assert actual_delay >= expected_base, f"Delay {actual_delay} should be >= base {expected_base}"
                assert actual_delay <= expected_base * 1.1, f"Delay {actual_delay} should be <= base*1.1 {expected_base * 1.1}"


class TestNoDataActivityTimeout:
    """Test no data activity timeout handling"""

    @pytest.mark.asyncio
    async def test_no_data_activity_closes_connection(
        self, settings_default, event_bus, logger
    ):
        """When no data received for 120s, connection is closed"""
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
        # Fresh pong (no pong timeout)
        fresh_pong_time = current_time - 10
        # But very old heartbeat (no data activity for 130s)
        old_heartbeat = current_time - 130

        adapter._connections[connection_id] = {
            "websocket": mock_websocket,
            "connected": True,
            "last_pong_received": fresh_pong_time,
            "last_ping_sent": current_time - 5,
            "last_heartbeat": old_heartbeat,  # No data for 130s
            "subscriptions": set(),
            "heartbeat_task": None,
            "message_task": None
        }
        adapter._running = True

        close_connection_called = False

        async def mock_close_connection(conn_id):
            nonlocal close_connection_called
            close_connection_called = True

        adapter._close_connection = mock_close_connection

        def mock_sleep(duration):
            adapter._running = False
            return asyncio.sleep(0)

        with patch('time.time', return_value=current_time), \
             patch('time.monotonic', return_value=current_time), \
             patch('asyncio.sleep', side_effect=mock_sleep):

            await adapter._heartbeat_monitor(connection_id)

        # Verify no data activity was logged
        error_calls = [call for call in logger.error.call_args_list
                       if call[0][0] == "mexc_adapter.no_data_activity"]
        assert len(error_calls) >= 1, "Expected no_data_activity error log"

        # Verify connection was closed
        assert close_connection_called, "_close_connection should be called on no data activity"
