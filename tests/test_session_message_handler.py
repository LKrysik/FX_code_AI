"""
Unit tests for SessionMessageHandler
=====================================
Tests session start/stop/status handling, validation, and delegation.

Test coverage:
- Session start (validation, auth, permissions, delegation)
- Session stop (validation, delegation)
- Session status (simple query)
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.api.websocket.handlers import SessionMessageHandler
from src.api.websocket.utils import ErrorHandler


class MockConnection:
    """Mock WebSocket connection"""
    def __init__(self, authenticated=False, session_token=None):
        self.authenticated = authenticated
        self.session_token = session_token


class MockUserSession:
    """Mock user session with permissions"""
    def __init__(self, has_permission_result=True):
        self._has_permission = has_permission_result

    def has_permission(self, permission):
        return self._has_permission


class TestSessionHandlerStart:
    """Test session start (handle_session_start)"""

    @pytest.mark.asyncio
    async def test_session_start_without_controller(self):
        """Test session start fails when controller not available"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=None,  # No controller
            error_handler=mock_error_handler
        )

        message = {
            "session_type": "backtest",
            "strategy_config": {"TestStrategy": ["BTC_USDT"]}
        }
        response = await handler.handle_session_start("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_session_start_without_authentication(self):
        """Test session start fails for unauthenticated client"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Unauthenticated connection
        mock_connection = MockConnection(authenticated=False)
        mock_connection_manager.get_connection.return_value = mock_connection

        message = {
            "session_type": "live",
            "strategy_config": {"Strategy": ["BTC_USDT"]}
        }
        response = await handler.handle_session_start("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "authentication_required"

    @pytest.mark.asyncio
    async def test_session_start_invalid_session_type(self):
        """Test session start fails for invalid session type"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection

        # Invalid session type
        message = {
            "session_type": "invalid_type",
            "strategy_config": {"Strategy": ["BTC_USDT"]}
        }
        response = await handler.handle_session_start("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "invalid_parameter"
        assert "session_type" in response["error_message"]

    @pytest.mark.asyncio
    async def test_session_start_missing_strategy_config(self):
        """Test session start fails without strategy_config"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection

        # Missing strategy_config
        message = {"session_type": "backtest"}
        response = await handler.handle_session_start("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "missing_parameters"

    @pytest.mark.asyncio
    async def test_session_start_without_session_starter(self):
        """Test session start fails when session_starter not configured"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler,
            session_starter=None  # No session starter
        )

        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection

        message = {
            "session_type": "backtest",
            "strategy_config": {"Strategy": ["BTC_USDT"]}
        }
        response = await handler.handle_session_start("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "operation_failed"

    @pytest.mark.asyncio
    async def test_session_start_delegates_to_starter(self):
        """Test session start delegates to session_starter callback"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()
        mock_session_starter = AsyncMock()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler,
            session_starter=mock_session_starter
        )

        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection

        # Setup session starter success
        mock_session_starter.return_value = {
            "type": "response",
            "status": "session_started",
            "session_id": "session_abc123"
        }

        message = {
            "session_type": "backtest",
            "strategy_config": {"Strategy": ["BTC_USDT"]}
        }
        response = await handler.handle_session_start("client_start", message)

        # Verify delegation
        mock_session_starter.assert_called_once_with("client_start", message)

        # Verify response
        assert response["status"] == "session_started"
        assert response["session_id"] == "session_abc123"

    @pytest.mark.asyncio
    async def test_session_start_handles_starter_exception(self):
        """Test session start handles exception from session_starter"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()
        mock_session_starter = AsyncMock()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler,
            session_starter=mock_session_starter
        )

        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection

        # Session starter raises exception
        mock_session_starter.side_effect = ValueError("Strategy activation failed")

        message = {
            "session_type": "live",
            "strategy_config": {"Strategy": ["BTC_USDT"]}
        }
        response = await handler.handle_session_start("client", message)

        # Verify error handling
        assert response["type"] == "error"
        assert response["error_code"] == "operation_failed"
        assert "Strategy activation failed" in response["error_message"]


class TestSessionHandlerStop:
    """Test session stop (handle_session_stop)"""

    @pytest.mark.asyncio
    async def test_session_stop_without_controller(self):
        """Test session stop fails when controller not available"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=None,
            error_handler=mock_error_handler
        )

        message = {"session_id": "session_123"}
        response = await handler.handle_session_stop("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_session_stop_without_session_stopper(self):
        """Test session stop fails when session_stopper not configured"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler,
            session_stopper=None  # No stopper
        )

        message = {"session_id": "session_123"}
        response = await handler.handle_session_stop("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "operation_failed"

    @pytest.mark.asyncio
    async def test_session_stop_delegates_to_stopper(self):
        """Test session stop delegates to session_stopper callback"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()
        mock_session_stopper = AsyncMock()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler,
            session_stopper=mock_session_stopper
        )

        # Setup session stopper success
        mock_session_stopper.return_value = {
            "type": "response",
            "status": "session_stopped",
            "session_id": "session_456"
        }

        message = {"session_id": "session_456"}
        response = await handler.handle_session_stop("client_stop", message)

        # Verify delegation
        mock_session_stopper.assert_called_once_with("client_stop", message)

        # Verify response
        assert response["status"] == "session_stopped"
        assert response["session_id"] == "session_456"

    @pytest.mark.asyncio
    async def test_session_stop_handles_stopper_exception(self):
        """Test session stop handles exception from session_stopper"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()
        mock_session_stopper = AsyncMock()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler,
            session_stopper=mock_session_stopper
        )

        # Session stopper raises exception
        mock_session_stopper.side_effect = Exception("Stop failed")

        message = {"session_id": "session_fail"}
        response = await handler.handle_session_stop("client", message)

        # Verify error handling
        assert response["type"] == "error"
        assert response["error_code"] == "operation_failed"
        assert "Stop failed" in response["error_message"]


class TestSessionHandlerStatus:
    """Test session status (handle_session_status)"""

    @pytest.mark.asyncio
    async def test_session_status_without_controller(self):
        """Test session status fails when controller not available"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=None,
            error_handler=mock_error_handler
        )

        message = {"session_id": "session_123"}
        response = await handler.handle_session_status("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_session_status_with_active_session(self):
        """Test session status returns active session data"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup controller with active session
        mock_controller.get_execution_status.return_value = {
            "session_id": "session_789",
            "status": "running",
            "symbols": ["BTC_USDT"]
        }

        message = {}
        response = await handler.handle_session_status("client", message)

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "session_status"
        assert response["session_data"]["session_id"] == "session_789"
        assert response["session_data"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_session_status_no_active_session(self):
        """Test session status when no active session"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup controller with no active session
        mock_controller.get_execution_status.return_value = None

        message = {}
        response = await handler.handle_session_status("client", message)

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "no_active_session"

    @pytest.mark.asyncio
    async def test_session_status_handles_exception(self):
        """Test session status handles controller exception"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Controller raises exception
        mock_controller.get_execution_status.side_effect = Exception("Status error")

        message = {}
        response = await handler.handle_session_status("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "status_retrieval_failed"
        assert "Status error" in response["error_message"]


class TestSessionHandlerEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_session_start_valid_session_types(self):
        """Test session start accepts all valid session types"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()
        mock_session_starter = AsyncMock()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler,
            session_starter=mock_session_starter
        )

        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection

        mock_session_starter.return_value = {"type": "response", "status": "session_started"}

        # Test all valid session types
        for session_type in ["backtest", "live", "paper"]:
            message = {
                "session_type": session_type,
                "strategy_config": {"Strategy": ["BTC_USDT"]}
            }
            response = await handler.handle_session_start("client", message)

            # Should delegate successfully
            assert mock_session_starter.called

    @pytest.mark.asyncio
    async def test_session_stop_with_missing_session_id(self):
        """Test session stop works even without session_id in message"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()
        mock_session_stopper = AsyncMock()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler,
            session_stopper=mock_session_stopper
        )

        mock_session_stopper.return_value = {"type": "response", "status": "session_stopped"}

        # No session_id in message
        message = {}
        response = await handler.handle_session_stop("client", message)

        # Should still delegate
        assert mock_session_stopper.called


class TestSessionHandlerIntegration:
    """Integration-style tests"""

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self):
        """Test complete session lifecycle: start, status, stop"""
        mock_connection_manager = AsyncMock()
        mock_auth_handler = AsyncMock()
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()
        mock_session_starter = AsyncMock()
        mock_session_stopper = AsyncMock()

        handler = SessionMessageHandler(
            connection_manager=mock_connection_manager,
            auth_handler=mock_auth_handler,
            controller=mock_controller,
            error_handler=mock_error_handler,
            session_starter=mock_session_starter,
            session_stopper=mock_session_stopper
        )

        mock_connection = MockConnection(authenticated=True)
        mock_connection_manager.get_connection.return_value = mock_connection

        # 1. Start session
        mock_session_starter.return_value = {
            "type": "response",
            "status": "session_started",
            "session_id": "integration_session"
        }

        start_msg = {
            "session_type": "backtest",
            "strategy_config": {"TestStrategy": ["BTC_USDT"]}
        }
        start_response = await handler.handle_session_start("client", start_msg)
        assert start_response["status"] == "session_started"

        # 2. Query status
        mock_controller.get_execution_status.return_value = {
            "session_id": "integration_session",
            "status": "running"
        }

        status_response = await handler.handle_session_status("client", {})
        assert status_response["status"] == "session_status"

        # 3. Stop session
        mock_session_stopper.return_value = {
            "type": "response",
            "status": "session_stopped"
        }

        stop_msg = {"session_id": "integration_session"}
        stop_response = await handler.handle_session_stop("client", stop_msg)
        assert stop_response["status"] == "session_stopped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
