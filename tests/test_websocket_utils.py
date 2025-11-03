"""
Unit Tests for WebSocket Utilities
===================================
Tests for ErrorHandler and ClientUtils extracted from websocket_server.py

Coverage target: >90%
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.api.websocket.utils import ErrorHandler, ClientUtils


# ============================================================================
# ErrorHandler Tests
# ============================================================================

class TestErrorHandler:
    """Test ErrorHandler utility class"""

    def test_service_unavailable(self):
        """Test service unavailable error generation"""
        handler = ErrorHandler()

        result = handler.service_unavailable("controller", "session_123")

        assert result["type"] == "error"
        assert result["error_code"] == "service_unavailable"
        assert "controller" in result["error_message"]
        assert result["session_id"] == "session_123"
        assert "timestamp" in result
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(result["timestamp"])

    def test_service_unavailable_no_session(self):
        """Test service unavailable without session ID"""
        handler = ErrorHandler()

        result = handler.service_unavailable("strategy_manager")

        assert result["type"] == "error"
        assert result["error_code"] == "service_unavailable"
        assert "strategy_manager" in result["error_message"]
        assert result["session_id"] is None

    def test_missing_parameters(self):
        """Test missing parameters error"""
        handler = ErrorHandler()

        result = handler.missing_parameters(["username", "password"])

        assert result["type"] == "error"
        assert result["error_code"] == "missing_parameters"
        assert "username" in result["error_message"]
        assert "password" in result["error_message"]
        assert "timestamp" in result

    def test_missing_parameters_single(self):
        """Test missing single parameter"""
        handler = ErrorHandler()

        result = handler.missing_parameters(["session_type"])

        assert "session_type" in result["error_message"]
        assert "Required parameters" in result["error_message"]

    def test_invalid_parameter(self):
        """Test invalid parameter error"""
        handler = ErrorHandler()

        result = handler.invalid_parameter(
            "session_type",
            "INVALID",
            "backtest, live, or paper"
        )

        assert result["type"] == "error"
        assert result["error_code"] == "invalid_parameter"
        assert "session_type" in result["error_message"]
        assert "INVALID" in result["error_message"]
        assert "backtest" in result["error_message"]

    def test_invalid_parameter_no_expected(self):
        """Test invalid parameter without expected value"""
        handler = ErrorHandler()

        result = handler.invalid_parameter("symbol", "INVALID$")

        assert "Invalid symbol" in result["error_message"]
        assert "INVALID$" in result["error_message"]

    def test_operation_failed(self):
        """Test operation failed error"""
        handler = ErrorHandler()
        error = ValueError("Invalid configuration")

        result = handler.operation_failed("session_start", error, "sess_123")

        assert result["type"] == "error"
        assert result["error_code"] == "session_start_failed"
        assert "Invalid configuration" in result["error_message"]
        assert result["session_id"] == "sess_123"

    def test_authentication_required(self):
        """Test authentication required error"""
        handler = ErrorHandler()

        result = handler.authentication_required("for session commands")

        assert result["type"] == "error"
        assert result["error_code"] == "authentication_required"
        assert "Authentication required" in result["error_message"]
        assert "session commands" in result["error_message"]

    def test_insufficient_permissions(self):
        """Test insufficient permissions error"""
        handler = ErrorHandler()

        result = handler.insufficient_permissions("EXECUTE_LIVE_TRADING")

        assert result["type"] == "error"
        assert result["error_code"] == "insufficient_permissions"
        assert "EXECUTE_LIVE_TRADING" in result["error_message"]
        assert "permission required" in result["error_message"]

    def test_message_processing_error(self):
        """Test message processing error"""
        handler = ErrorHandler()
        error = Exception("JSON parsing failed")

        result = handler.message_processing_error(error, "client_123")

        assert result["type"] == "error"
        assert result["error_code"] == "message_processing_error"
        assert "Failed to process message" in result["error_message"]
        assert "JSON parsing failed" in result["error_message"]

    def test_validation_error(self):
        """Test validation error"""
        handler = ErrorHandler()
        errors = ["Field 'name' is required", "Field 'age' must be positive"]

        result = handler.validation_error(
            "Validation failed",
            errors=errors,
            session_id="sess_123"
        )

        assert result["type"] == "error"
        assert result["error_code"] == "validation_error"
        assert "Validation failed" in result["error_message"]
        assert result["errors"] == errors
        assert result["session_id"] == "sess_123"

    def test_get_session_id_safe_success(self):
        """Test get_session_id_safe with valid controller"""
        handler = ErrorHandler()
        mock_controller = Mock()
        mock_controller.get_execution_status.return_value = {
            "session_id": "test_session_123",
            "status": "running"
        }

        session_id = handler.get_session_id_safe(mock_controller)

        assert session_id == "test_session_123"
        mock_controller.get_execution_status.assert_called_once()

    def test_get_session_id_safe_no_controller(self):
        """Test get_session_id_safe with None controller"""
        handler = ErrorHandler()

        session_id = handler.get_session_id_safe(None)

        assert session_id is None

    def test_get_session_id_safe_exception(self):
        """Test get_session_id_safe when controller raises exception"""
        handler = ErrorHandler()
        mock_controller = Mock()
        mock_controller.get_execution_status.side_effect = Exception("Controller error")

        session_id = handler.get_session_id_safe(mock_controller)

        assert session_id is None

    def test_get_session_id_safe_invalid_status(self):
        """Test get_session_id_safe with non-dict status"""
        handler = ErrorHandler()
        mock_controller = Mock()
        mock_controller.get_execution_status.return_value = "not_a_dict"

        session_id = handler.get_session_id_safe(mock_controller)

        assert session_id is None

    def test_error_handler_with_logger(self):
        """Test ErrorHandler with logger"""
        mock_logger = Mock()
        handler = ErrorHandler(logger=mock_logger)

        handler.service_unavailable("controller")

        # Verify logger was called
        mock_logger.warning.assert_called_once()


# ============================================================================
# ClientUtils Tests
# ============================================================================

class TestClientUtils:
    """Test ClientUtils utility class"""

    def test_get_client_ip_remote_address_tuple(self):
        """Test IP extraction from remote_address tuple"""
        mock_ws = Mock()
        mock_ws.remote_address = ("192.168.1.1", 8080)

        ip = ClientUtils.get_client_ip(mock_ws)

        assert ip == "192.168.1.1"

    def test_get_client_ip_fastapi_client(self):
        """Test IP extraction from FastAPI WebSocket"""
        mock_ws = Mock()
        del mock_ws.remote_address  # No remote_address
        mock_ws.client = Mock()
        mock_ws.client.host = "10.0.0.1"

        ip = ClientUtils.get_client_ip(mock_ws)

        assert ip == "10.0.0.1"

    def test_get_client_ip_connection(self):
        """Test IP extraction from connection attribute"""
        mock_ws = Mock(spec=[])  # Empty spec - no remote_address
        mock_ws.connection = Mock()
        mock_ws.connection.remote_address = ("172.16.0.1", 9000)

        ip = ClientUtils.get_client_ip(mock_ws)

        assert ip == "172.16.0.1"

    def test_get_client_ip_fallback(self):
        """Test IP extraction fallback to 127.0.0.1"""
        mock_ws = Mock(spec=[])  # No attributes

        ip = ClientUtils.get_client_ip(mock_ws)

        assert ip == "127.0.0.1"

    def test_get_client_ip_with_logger(self):
        """Test IP extraction with logger"""
        mock_ws = Mock(spec=[])
        mock_logger = Mock()

        ip = ClientUtils.get_client_ip(mock_ws, logger=mock_logger)

        assert ip == "127.0.0.1"
        # Verify logger was called for fallback
        mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_get_client_ip_by_id_success(self):
        """Test get_client_ip_by_id with valid connection"""
        mock_conn_mgr = Mock()
        mock_connection = Mock()
        mock_connection.ip_address = "10.0.0.1"
        mock_conn_mgr.get_connection = AsyncMock(return_value=mock_connection)

        ip = await ClientUtils.get_client_ip_by_id("client1", mock_conn_mgr)

        assert ip == "10.0.0.1"
        mock_conn_mgr.get_connection.assert_called_once_with("client1")

    @pytest.mark.asyncio
    async def test_get_client_ip_by_id_metadata(self):
        """Test get_client_ip_by_id with metadata dict"""
        mock_conn_mgr = Mock()
        mock_connection = Mock(spec=[])  # No ip_address attribute
        mock_connection.metadata = {"ip_address": "192.168.1.5"}
        mock_conn_mgr.get_connection = AsyncMock(return_value=mock_connection)

        ip = await ClientUtils.get_client_ip_by_id("client2", mock_conn_mgr)

        assert ip == "192.168.1.5"

    @pytest.mark.asyncio
    async def test_get_client_ip_by_id_no_connection(self):
        """Test get_client_ip_by_id when connection not found"""
        mock_conn_mgr = Mock()
        mock_conn_mgr.get_connection = AsyncMock(return_value=None)

        ip = await ClientUtils.get_client_ip_by_id("client_unknown", mock_conn_mgr)

        assert ip == "unknown"

    @pytest.mark.asyncio
    async def test_get_client_ip_by_id_exception(self):
        """Test get_client_ip_by_id when exception occurs"""
        mock_conn_mgr = Mock()
        mock_conn_mgr.get_connection = AsyncMock(side_effect=Exception("Connection error"))

        ip = await ClientUtils.get_client_ip_by_id("client1", mock_conn_mgr)

        assert ip == "unknown"

    def test_build_connection_metadata(self):
        """Test building connection metadata"""
        mock_ws = Mock()
        mock_ws.request_headers = {"User-Agent": "Mozilla/5.0"}
        mock_ws.path = "/ws"

        metadata = ClientUtils.build_connection_metadata(mock_ws, "192.168.1.1")

        assert metadata["ip_address"] == "192.168.1.1"
        assert metadata["user_agent"] == "Mozilla/5.0"
        assert metadata["path"] == "/ws"

    def test_build_connection_metadata_no_headers(self):
        """Test building metadata when headers not available"""
        mock_ws = Mock(spec=[])  # No attributes

        metadata = ClientUtils.build_connection_metadata(mock_ws, "10.0.0.1")

        assert metadata["ip_address"] == "10.0.0.1"
        assert metadata["user_agent"] == "unknown"
        assert metadata["path"] == ""

    def test_build_connection_metadata_fastapi_scope(self):
        """Test building metadata from FastAPI scope"""
        mock_ws = Mock(spec=['scope'])
        mock_ws.scope = {"path": "/api/ws"}

        metadata = ClientUtils.build_connection_metadata(mock_ws, "172.16.0.1")

        assert metadata["path"] == "/api/ws"

    def test_extract_reconnect_token(self):
        """Test extracting reconnect token from headers"""
        mock_ws = Mock()
        mock_ws.request_headers = {"X-Reconnect-Token": "client123:abc..."}

        token = ClientUtils.extract_reconnect_token(mock_ws)

        assert token == "client123:abc..."

    def test_extract_reconnect_token_none(self):
        """Test extracting reconnect token when not present"""
        mock_ws = Mock()
        mock_ws.request_headers = {}

        token = ClientUtils.extract_reconnect_token(mock_ws)

        assert token is None

    def test_extract_reconnect_token_fastapi(self):
        """Test extracting reconnect token from FastAPI headers"""
        mock_ws = Mock(spec=['headers'])
        mock_ws.headers = {"X-Reconnect-Token": "client456:xyz..."}

        token = ClientUtils.extract_reconnect_token(mock_ws)

        assert token == "client456:xyz..."

    def test_extract_reconnect_token_exception(self):
        """Test extracting reconnect token when exception occurs"""
        mock_ws = Mock()
        mock_ws.request_headers.get.side_effect = Exception("Header error")

        token = ClientUtils.extract_reconnect_token(mock_ws)

        assert token is None


# ============================================================================
# Integration Tests
# ============================================================================

class TestUtilitiesIntegration:
    """Integration tests for ErrorHandler and ClientUtils together"""

    def test_error_with_client_info(self):
        """Test using ErrorHandler with ClientUtils extracted IP"""
        # Extract IP
        mock_ws = Mock()
        mock_ws.remote_address = ("192.168.1.100", 8080)
        client_ip = ClientUtils.get_client_ip(mock_ws)

        # Build metadata
        metadata = ClientUtils.build_connection_metadata(mock_ws, client_ip)

        # Create error with session ID
        handler = ErrorHandler()
        error = handler.service_unavailable("controller", "session_test")

        # Verify both utilities work together
        assert client_ip == "192.168.1.100"
        assert metadata["ip_address"] == client_ip
        assert error["error_code"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_error_with_connection_lookup(self):
        """Test ErrorHandler with ClientUtils connection lookup"""
        # Setup mock connection manager
        mock_conn_mgr = Mock()
        mock_connection = Mock()
        mock_connection.ip_address = "10.0.0.50"
        mock_conn_mgr.get_connection = AsyncMock(return_value=mock_connection)

        # Get IP by ID
        client_ip = await ClientUtils.get_client_ip_by_id("client_test", mock_conn_mgr)

        # Generate error
        handler = ErrorHandler()
        error = handler.operation_failed("connection_lookup", Exception("Test error"))

        # Verify
        assert client_ip == "10.0.0.50"
        assert "connection_lookup_failed" in error["error_code"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.api.websocket.utils", "--cov-report=term-missing"])
