"""
Unit tests for ProtocolMessageHandler
======================================
Tests command execution, heartbeat handling, and protocol handshake.

Test coverage:
- Command execution (success, failures, auth checks)
- Heartbeat ping/pong
- Protocol handshake (success, validation failures, security)
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.api.websocket.handlers import ProtocolMessageHandler


class MockConnection:
    """Mock WebSocket connection"""
    def __init__(self, authenticated=False):
        self.authenticated = authenticated
        self.__dict__ = {"authenticated": authenticated}


class TestProtocolHandlerCommand:
    """Test command execution (handle_command)"""

    @pytest.mark.asyncio
    async def test_successful_command_execution(self):
        """Test successful command execution"""
        mock_connection_manager = AsyncMock()
        mock_controller = Mock()
        mock_command_executor = AsyncMock()
        mock_logger = Mock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager,
            controller=mock_controller,
            command_executor=mock_command_executor,
            logger=mock_logger
        )

        # Setup mocks
        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection
        mock_command_executor.return_value = {"result": "backtest_started"}

        # Handle command
        message = {
            "action": "start_backtest",
            "params": {"symbols": ["BTC_USDT"], "acceleration": 10.0}
        }
        response = await handler.handle_command("client_123", message)

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "success"
        assert response["command"] == "start_backtest"
        assert response["data"] == {"result": "backtest_started"}

    @pytest.mark.asyncio
    async def test_command_without_controller(self):
        """Test command fails when controller not available"""
        mock_connection_manager = AsyncMock()
        mock_logger = Mock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager,
            controller=None,  # No controller
            logger=mock_logger
        )

        message = {"action": "start_backtest", "params": {}}
        response = await handler.handle_command("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "service_unavailable"
        assert "Trading controller not available" in response["error_message"]

    @pytest.mark.asyncio
    async def test_command_without_authentication(self):
        """Test command fails for unauthenticated client"""
        mock_connection_manager = AsyncMock()
        mock_controller = Mock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager,
            controller=mock_controller
        )

        # Unauthenticated connection
        mock_connection = MockConnection(authenticated=False)
        mock_connection_manager.get_connection.return_value = mock_connection

        message = {"action": "start_live_trading", "params": {}}
        response = await handler.handle_command("client_unauth", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "authentication_required"

    @pytest.mark.asyncio
    async def test_command_without_executor(self):
        """Test command fails when command_executor not configured"""
        mock_connection_manager = AsyncMock()
        mock_controller = Mock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager,
            controller=mock_controller,
            command_executor=None  # No executor
        )

        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection

        message = {"action": "stop_session", "params": {}}
        response = await handler.handle_command("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "command_executor_unavailable"

    @pytest.mark.asyncio
    async def test_command_execution_exception(self):
        """Test command execution handles exceptions"""
        mock_connection_manager = AsyncMock()
        mock_controller = Mock()
        mock_command_executor = AsyncMock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager,
            controller=mock_controller,
            command_executor=mock_command_executor
        )

        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection

        # Executor raises exception
        mock_command_executor.side_effect = ValueError("Invalid parameters")

        message = {"action": "bad_command", "params": {}}
        response = await handler.handle_command("client", message)

        # Verify error response
        assert response["type"] == "error"
        assert response["error_code"] == "command_failed"
        assert "Invalid parameters" in response["error_message"]


class TestProtocolHandlerHeartbeat:
    """Test heartbeat handling (handle_heartbeat)"""

    @pytest.mark.asyncio
    async def test_heartbeat_updates_connection(self):
        """Test heartbeat updates connection manager"""
        mock_connection_manager = AsyncMock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager
        )

        message = {}
        response = await handler.handle_heartbeat("client_ping", message)

        # Verify heartbeat was updated
        mock_connection_manager.update_heartbeat.assert_called_once_with("client_ping")

    @pytest.mark.asyncio
    async def test_heartbeat_returns_pong(self):
        """Test heartbeat returns pong response"""
        mock_connection_manager = AsyncMock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager
        )

        message = {}
        response = await handler.handle_heartbeat("client", message)

        # Verify pong response
        assert response["type"] == "status"
        assert response["status"] == "pong"
        assert "timestamp" in response


class TestProtocolHandlerHandshake:
    """Test protocol handshake (handle_handshake)"""

    @pytest.mark.asyncio
    async def test_successful_handshake(self):
        """Test successful handshake with valid message"""
        mock_connection_manager = AsyncMock()
        mock_logger = Mock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager,
            logger=mock_logger
        )

        # Setup connection
        mock_connection = MockConnection()
        mock_connection_manager.get_connection.return_value = mock_connection

        # Valid handshake message
        message = {
            "version": "1.0",
            "client_id": "web_client_123",
            "capabilities": ["market_data", "signals"]
        }
        response = await handler.handle_handshake("client_123", message)

        # Verify acceptance
        assert response["type"] == "handshake_ack"
        assert response["status"] == "accepted"
        assert response["server_version"] == "1.0"
        assert "server_capabilities" in response
        assert "session_id" in response

    @pytest.mark.asyncio
    async def test_handshake_updates_connection_metadata(self):
        """Test handshake updates connection with protocol info"""
        mock_connection_manager = AsyncMock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager
        )

        mock_connection = MockConnection()
        mock_connection_manager.get_connection.return_value = mock_connection

        message = {
            "version": "1.0",
            "client_id": "test_client",
            "capabilities": ["market_data"]
        }
        await handler.handle_handshake("client", message)

        # Verify connection metadata updated
        assert mock_connection.__dict__["handshake_completed"] is True
        assert mock_connection.__dict__["protocol_version"] == "1.0"
        assert mock_connection.__dict__["client_capabilities"] == ["market_data"]

    @pytest.mark.asyncio
    async def test_handshake_missing_required_field(self):
        """Test handshake rejection for missing required field"""
        mock_connection_manager = AsyncMock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager
        )

        # Missing 'capabilities' field
        message = {
            "version": "1.0",
            "client_id": "client"
        }
        response = await handler.handle_handshake("client", message)

        # Verify rejection
        assert response["status"] == "rejected"
        assert "Missing required field: capabilities" in response["reason"]

    @pytest.mark.asyncio
    async def test_handshake_unsupported_version(self):
        """Test handshake rejection for unsupported protocol version"""
        mock_connection_manager = AsyncMock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager
        )

        # Unsupported version
        message = {
            "version": "2.0",  # Not supported
            "client_id": "client",
            "capabilities": []
        }
        response = await handler.handle_handshake("client", message)

        # Verify rejection
        assert response["status"] == "rejected"
        assert "Unsupported protocol version: 2.0" in response["reason"]
        assert "Expected: 1.0" in response["reason"]

    @pytest.mark.asyncio
    async def test_handshake_invalid_capabilities(self):
        """Test handshake rejection for unsupported capabilities"""
        mock_connection_manager = AsyncMock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager
        )

        # Invalid capabilities
        message = {
            "version": "1.0",
            "client_id": "client",
            "capabilities": ["market_data", "invalid_cap", "another_invalid"]
        }
        response = await handler.handle_handshake("client", message)

        # Verify rejection
        assert response["status"] == "rejected"
        assert "Unsupported capabilities" in response["reason"]
        assert "supported_capabilities" in response

    @pytest.mark.asyncio
    async def test_handshake_logs_success(self):
        """Test handshake logs successful completion"""
        mock_connection_manager = AsyncMock()
        mock_logger = Mock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager,
            logger=mock_logger
        )

        mock_connection = MockConnection()
        mock_connection_manager.get_connection.return_value = mock_connection

        message = {
            "version": "1.0",
            "client_id": "log_test",
            "capabilities": ["market_data"]
        }
        await handler.handle_handshake("client", message)

        # Verify logging
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0]
        assert "websocket_protocol.handshake_successful" in call_args[0]

    @pytest.mark.asyncio
    async def test_handshake_handles_exception(self):
        """Test handshake handles unexpected exceptions"""
        mock_connection_manager = AsyncMock()
        mock_logger = Mock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager,
            logger=mock_logger
        )

        # get_connection raises exception
        mock_connection_manager.get_connection.side_effect = Exception("Connection error")

        message = {
            "version": "1.0",
            "client_id": "client",
            "capabilities": []
        }
        response = await handler.handle_handshake("client", message)

        # Should return rejected status
        assert response["status"] == "rejected"
        assert "Handshake processing error" in response["reason"]

        # Should log error
        mock_logger.error.assert_called_once()


class TestProtocolHandlerEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_command_with_missing_action(self):
        """Test command with missing action field"""
        mock_connection_manager = AsyncMock()
        mock_controller = Mock()
        mock_command_executor = AsyncMock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager,
            controller=mock_controller,
            command_executor=mock_command_executor
        )

        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection

        # Missing action (defaults to empty string)
        message = {"params": {}}
        await handler.handle_command("client", message)

        # Executor should be called with empty command
        mock_command_executor.assert_called_once_with("", {})

    @pytest.mark.asyncio
    async def test_handshake_without_connection(self):
        """Test handshake when connection not found"""
        mock_connection_manager = AsyncMock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager
        )

        # Connection not found
        mock_connection_manager.get_connection.return_value = None

        message = {
            "version": "1.0",
            "client_id": "no_conn",
            "capabilities": []
        }
        response = await handler.handle_handshake("client", message)

        # Should still succeed (connection may not exist yet)
        assert response["status"] == "accepted"


class TestProtocolHandlerIntegration:
    """Integration-style tests"""

    @pytest.mark.asyncio
    async def test_full_protocol_flow(self):
        """Test complete protocol flow: handshake, heartbeat, command"""
        mock_connection_manager = AsyncMock()
        mock_controller = Mock()
        mock_command_executor = AsyncMock()
        mock_logger = Mock()

        handler = ProtocolMessageHandler(
            connection_manager=mock_connection_manager,
            controller=mock_controller,
            command_executor=mock_command_executor,
            logger=mock_logger
        )

        # 1. Handshake
        mock_connection = MockConnection()
        mock_connection_manager.get_connection.return_value = mock_connection

        handshake_msg = {
            "version": "1.0",
            "client_id": "integration_client",
            "capabilities": ["market_data", "commands"]
        }
        hs_response = await handler.handle_handshake("client", handshake_msg)
        assert hs_response["status"] == "accepted"

        # 2. Heartbeat
        hb_response = await handler.handle_heartbeat("client", {})
        assert hb_response["status"] == "pong"

        # 3. Command (after handshake sets authenticated)
        mock_connection.authenticated = True
        mock_command_executor.return_value = {"status": "running"}

        cmd_msg = {"action": "start_session", "params": {}}
        cmd_response = await handler.handle_command("client", cmd_msg)
        assert cmd_response["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
