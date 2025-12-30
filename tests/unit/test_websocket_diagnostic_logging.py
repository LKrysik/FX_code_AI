"""
BUG-008-1 Unit Tests: WebSocket Disconnect Diagnostic Logging
==============================================================
Story: BUG-008-1 - WebSocket Disconnect Diagnostic Logging
Tests: Verify detailed diagnostic logs when WebSocket connections close

Acceptance Criteria:
- AC1: Backend logs include disconnect reason code (1000=normal, 1001=going away, 1006=abnormal, etc.)
- AC2: Backend logs include connection duration before disconnect
- AC3: Backend logs include last activity timestamp and message counts
- AC4: Backend logs include client_id for correlation with frontend logs
- AC5: Frontend logs include disconnect reason when connection closes
- AC6: Disconnect events are logged at WARNING level if abnormal

Test Pattern: RED-GREEN-REFACTOR
- These tests should FAIL on current code and PASS after implementation
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, Dict, Any


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_logger():
    """Create a mock structured logger to capture log calls."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def mock_connection():
    """Create a mock ClientConnection with test data."""
    connection = MagicMock()
    connection.client_id = "test-client-123"
    connection.connected_at = datetime.now(timezone.utc)
    connection.last_heartbeat = time.time()
    connection.messages_sent = 42
    connection.messages_received = 15
    connection.ip_address = "192.168.1.100"
    connection.user_agent = "Mozilla/5.0"
    connection.get_connection_age_seconds = MagicMock(return_value=300.5)  # 5 minutes
    return connection


# ============================================================================
# BACKEND TESTS - AC1: Disconnect reason code logging
# ============================================================================

class TestBackendDisconnectReasonCode:
    """Tests for AC1: Backend logs include disconnect reason code."""

    def test_logs_normal_close_code_1000(self, mock_logger, mock_connection):
        """
        AC1: Verify normal closure (code 1000) is logged.
        Expected: Log includes close_code=1000
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)

        # Simulate disconnect with code 1000
        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Normal closure",
            was_clean=True
        ))

        # Verify log was called with close_code
        mock_logger.info.assert_called()
        log_call_args = mock_logger.info.call_args
        assert log_call_args is not None
        log_data = log_call_args[0][1] if len(log_call_args[0]) > 1 else log_call_args[1]
        assert log_data.get("close_code") == 1000

    def test_logs_abnormal_close_code_1006(self, mock_logger, mock_connection):
        """
        AC1: Verify abnormal closure (code 1006) is logged at WARNING level.
        Expected: Log includes close_code=1006, logged as WARNING
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)

        # Simulate abnormal disconnect
        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1006,
            close_reason="Abnormal closure",
            was_clean=False
        ))

        # Verify WARNING level for abnormal close
        mock_logger.warning.assert_called()
        log_call_args = mock_logger.warning.call_args
        assert log_call_args is not None
        log_data = log_call_args[0][1] if len(log_call_args[0]) > 1 else log_call_args[1]
        assert log_data.get("close_code") == 1006

    def test_logs_going_away_code_1001(self, mock_logger, mock_connection):
        """
        AC1: Verify 'going away' closure (code 1001) is logged.
        Expected: Log includes close_code=1001
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1001,
            close_reason="Going away",
            was_clean=True
        ))

        # 1001 is a clean close, should be INFO level
        mock_logger.info.assert_called()


# ============================================================================
# BACKEND TESTS - AC2: Connection duration logging
# ============================================================================

class TestBackendConnectionDuration:
    """Tests for AC2: Backend logs include connection duration before disconnect."""

    def test_logs_connection_duration_seconds(self, mock_logger, mock_connection):
        """
        AC2: Verify connection duration is logged in seconds.
        Expected: Log includes duration_seconds field with accurate value
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Normal closure",
            was_clean=True
        ))

        # Verify duration is logged
        log_call_args = mock_logger.info.call_args
        log_data = log_call_args[0][1] if len(log_call_args[0]) > 1 else log_call_args[1]
        assert "duration_seconds" in log_data
        assert isinstance(log_data["duration_seconds"], (int, float))
        assert log_data["duration_seconds"] >= 0

    def test_duration_calculated_from_connected_at(self, mock_logger, mock_connection):
        """
        AC2: Verify duration is calculated from connection start time.
        Expected: Duration reflects time since connected_at
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)

        # Set up connection with known duration
        mock_connection.get_connection_age_seconds.return_value = 120.5  # 2 minutes
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Normal closure",
            was_clean=True
        ))

        log_call_args = mock_logger.info.call_args
        log_data = log_call_args[0][1] if len(log_call_args[0]) > 1 else log_call_args[1]
        assert log_data.get("duration_seconds") == pytest.approx(120.5, rel=0.1)


# ============================================================================
# BACKEND TESTS - AC3: Message counts and last activity logging
# ============================================================================

class TestBackendMessageCounts:
    """Tests for AC3: Backend logs include last activity timestamp and message counts."""

    def test_logs_messages_sent_count(self, mock_logger, mock_connection):
        """
        AC3: Verify messages_sent count is logged.
        Expected: Log includes accurate messages_sent count
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Normal closure",
            was_clean=True
        ))

        log_call_args = mock_logger.info.call_args
        log_data = log_call_args[0][1] if len(log_call_args[0]) > 1 else log_call_args[1]
        assert log_data.get("messages_sent") == 42

    def test_logs_messages_received_count(self, mock_logger, mock_connection):
        """
        AC3: Verify messages_received count is logged.
        Expected: Log includes accurate messages_received count
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Normal closure",
            was_clean=True
        ))

        log_call_args = mock_logger.info.call_args
        log_data = log_call_args[0][1] if len(log_call_args[0]) > 1 else log_call_args[1]
        assert log_data.get("messages_received") == 15

    def test_logs_last_activity_age(self, mock_logger, mock_connection):
        """
        AC3: Verify last activity age is logged.
        Expected: Log includes last_activity_age_seconds
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        mock_connection.last_heartbeat = time.time() - 30  # 30 seconds ago
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Normal closure",
            was_clean=True
        ))

        log_call_args = mock_logger.info.call_args
        log_data = log_call_args[0][1] if len(log_call_args[0]) > 1 else log_call_args[1]
        assert "last_activity_age_seconds" in log_data
        assert log_data["last_activity_age_seconds"] >= 30


# ============================================================================
# BACKEND TESTS - AC4: Client ID correlation logging
# ============================================================================

class TestBackendClientIdCorrelation:
    """Tests for AC4: Backend logs include client_id for correlation."""

    def test_logs_client_id(self, mock_logger, mock_connection):
        """
        AC4: Verify client_id is logged for correlation.
        Expected: Log includes client_id field
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Normal closure",
            was_clean=True
        ))

        log_call_args = mock_logger.info.call_args
        log_data = log_call_args[0][1] if len(log_call_args[0]) > 1 else log_call_args[1]
        assert log_data.get("client_id") == "test-client-123"

    def test_logs_initiated_by_field(self, mock_logger, mock_connection):
        """
        AC4: Verify initiated_by field helps identify disconnect source.
        Expected: Log includes initiated_by (client/server/network)
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        manager._connections = {"test-client-123": mock_connection}

        # Client-initiated close (code 1000)
        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Client closed",
            was_clean=True,
            initiated_by="client"
        ))

        log_call_args = mock_logger.info.call_args
        log_data = log_call_args[0][1] if len(log_call_args[0]) > 1 else log_call_args[1]
        assert log_data.get("initiated_by") == "client"


# ============================================================================
# BACKEND TESTS - AC6: WARNING level for abnormal closes
# ============================================================================

class TestBackendLogLevels:
    """Tests for AC6: Disconnect events logged at WARNING if abnormal."""

    def test_normal_close_uses_info_level(self, mock_logger, mock_connection):
        """
        AC6: Normal closure (1000) should use INFO level.
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Normal closure",
            was_clean=True
        ))

        # INFO should be called, not WARNING
        mock_logger.info.assert_called()
        # Verify WARNING was NOT called for normal close
        warning_calls = [c for c in mock_logger.warning.call_args_list
                         if "connection_closed" in str(c)]
        assert len(warning_calls) == 0

    def test_abnormal_close_uses_warning_level(self, mock_logger, mock_connection):
        """
        AC6: Abnormal closure (1006) should use WARNING level.
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1006,
            close_reason="Abnormal closure",
            was_clean=False
        ))

        # WARNING should be called for abnormal close
        mock_logger.warning.assert_called()

    @pytest.mark.parametrize("close_code,expected_level", [
        (1000, "info"),      # Normal closure
        (1001, "info"),      # Going away
        (1002, "warning"),   # Protocol error
        (1005, "warning"),   # No status received
        (1006, "warning"),   # Abnormal closure
        (1011, "warning"),   # Internal error
        (1012, "warning"),   # Service restart
    ])
    def test_close_codes_use_appropriate_log_level(
        self, mock_logger, mock_connection, close_code, expected_level
    ):
        """
        AC6: Verify each close code uses appropriate log level.
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=close_code,
            close_reason="Test reason",
            was_clean=(close_code in [1000, 1001])
        ))

        if expected_level == "info":
            mock_logger.info.assert_called()
        else:
            mock_logger.warning.assert_called()


# ============================================================================
# INTEGRATION TEST - Full disconnect logging flow
# ============================================================================

class TestDisconnectLoggingIntegration:
    """Integration tests for complete disconnect logging flow."""

    def test_complete_disconnect_log_contains_all_fields(
        self, mock_logger, mock_connection
    ):
        """
        Integration: Verify complete disconnect log has all required fields.
        Required fields: client_id, close_code, close_reason, was_clean,
                        duration_seconds, messages_sent, messages_received,
                        last_activity_age_seconds, initiated_by
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Normal closure",
            was_clean=True,
            initiated_by="client"
        ))

        # Get the logged data
        log_call_args = mock_logger.info.call_args
        log_data = log_call_args[0][1] if len(log_call_args[0]) > 1 else log_call_args[1]

        # Verify all required fields
        required_fields = [
            "client_id",
            "close_code",
            "close_reason",
            "was_clean",
            "duration_seconds",
            "messages_sent",
            "messages_received",
            "last_activity_age_seconds",
            "initiated_by"
        ]

        for field in required_fields:
            assert field in log_data, f"Missing required field: {field}"

    def test_log_event_name_is_connection_closed(self, mock_logger, mock_connection):
        """
        Verify the log event name is 'connection_manager.connection_closed'.
        DNA Inheritance: follows project convention of 'connection_manager.*' prefix.
        """
        from src.api.connection_manager import ConnectionManager

        manager = ConnectionManager()
        manager.set_logger(mock_logger)
        manager._connections = {"test-client-123": mock_connection}

        asyncio.run(manager.log_connection_closed(
            client_id="test-client-123",
            close_code=1000,
            close_reason="Normal closure",
            was_clean=True
        ))

        # Verify event name follows connection_manager.* convention
        log_call_args = mock_logger.info.call_args
        event_name = log_call_args[0][0]
        assert event_name == "connection_manager.connection_closed"
