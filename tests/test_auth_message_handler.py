"""
Unit tests for AuthMessageHandler
==================================
Tests authentication message handling, token validation, and connection updates.

Test coverage:
- Successful authentication with valid token
- Failed authentication with invalid/expired token
- Connection metadata updates
- Error handling and logging
- Edge cases (missing token, no connection, etc.)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
from src.api.websocket.handlers import AuthMessageHandler


class MockAuthResult:
    """Mock authentication result"""
    def __init__(self, success, user_session=None, error_code=None, error_message=None):
        self.success = success
        self.user_session = user_session
        self.error_code = error_code
        self.error_message = error_message


class MockUserSession:
    """Mock user session"""
    def __init__(self, user_id, permissions, expires_at):
        self.user_id = user_id
        self.permissions = permissions
        self.expires_at = expires_at


class MockConnection:
    """Mock WebSocket connection"""
    def __init__(self):
        self.__dict__ = {}


class TestAuthMessageHandlerSuccess:
    """Test successful authentication scenarios"""

    @pytest.mark.asyncio
    async def test_successful_auth_with_valid_token(self):
        """Test successful authentication with valid JWT token"""
        # Setup mocks
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()
        mock_logger = Mock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager,
            logger=mock_logger
        )

        # Setup successful auth result
        expires_at = datetime.now() + timedelta(hours=1)
        user_session = MockUserSession(
            user_id="user_123",
            permissions=["read", "write", "admin"],
            expires_at=expires_at
        )
        auth_result = MockAuthResult(
            success=True,
            user_session=user_session
        )

        mock_auth_handler.authenticate_token.return_value = auth_result

        # Setup connection
        mock_connection = MockConnection()
        mock_connection_manager.get_connection.return_value = mock_connection

        # Handle auth message
        message = {"token": "valid_jwt_token"}
        response = await handler.handle_auth("client_123", message)

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "authenticated"
        assert response["user_id"] == "user_123"
        assert response["permissions"] == ["read", "write", "admin"]
        assert "session_expires" in response
        assert "timestamp" in response

    @pytest.mark.asyncio
    async def test_successful_auth_updates_connection_metadata(self):
        """Test that successful auth updates connection with user info"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager
        )

        # Setup auth result
        user_session = MockUserSession(
            user_id="user_456",
            permissions=["read"],
            expires_at=datetime.now() + timedelta(hours=1)
        )
        auth_result = MockAuthResult(success=True, user_session=user_session)
        mock_auth_handler.authenticate_token.return_value = auth_result

        # Setup connection
        mock_connection = MockConnection()
        mock_connection_manager.get_connection.return_value = mock_connection

        # Handle auth
        message = {"token": "valid_token"}
        await handler.handle_auth("client_456", message)

        # Verify connection was updated
        assert mock_connection.__dict__["authenticated"] is True
        assert mock_connection.__dict__["user_id"] == "user_456"
        assert mock_connection.__dict__["permissions"] == ["read"]

    @pytest.mark.asyncio
    async def test_auth_calls_auth_handler_with_correct_params(self):
        """Test that auth handler is called with token, IP, and client type"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager
        )

        # Setup auth result
        user_session = MockUserSession(
            user_id="user_789",
            permissions=["read"],
            expires_at=datetime.now() + timedelta(hours=1)
        )
        auth_result = MockAuthResult(success=True, user_session=user_session)
        mock_auth_handler.authenticate_token.return_value = auth_result
        mock_connection_manager.get_connection.return_value = MockConnection()

        # Handle auth
        message = {"token": "test_token_123"}
        await handler.handle_auth("client_789", message)

        # Verify authenticate_token was called with correct params
        mock_auth_handler.authenticate_token.assert_called_once()
        call_args = mock_auth_handler.authenticate_token.call_args[0]
        assert call_args[0] == "test_token_123"  # token
        assert call_args[2] == "websocket_client"  # client_type


class TestAuthMessageHandlerFailure:
    """Test failed authentication scenarios"""

    @pytest.mark.asyncio
    async def test_failed_auth_with_invalid_token(self):
        """Test failed authentication with invalid token"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()
        mock_logger = Mock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager,
            logger=mock_logger
        )

        # Setup failed auth result
        auth_result = MockAuthResult(
            success=False,
            error_code="invalid_token",
            error_message="Token signature is invalid"
        )
        mock_auth_handler.authenticate_token.return_value = auth_result

        # Handle auth
        message = {"token": "invalid_token"}
        response = await handler.handle_auth("client_fail", message)

        # Verify error response
        assert response["type"] == "error"
        assert response["error_code"] == "invalid_token"
        assert response["error_message"] == "Token signature is invalid"
        assert "timestamp" in response

    @pytest.mark.asyncio
    async def test_failed_auth_with_expired_token(self):
        """Test failed authentication with expired token"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager
        )

        # Setup expired token result
        auth_result = MockAuthResult(
            success=False,
            error_code="token_expired",
            error_message="Token has expired"
        )
        mock_auth_handler.authenticate_token.return_value = auth_result

        # Handle auth
        message = {"token": "expired_token"}
        response = await handler.handle_auth("client_expired", message)

        # Verify error response
        assert response["type"] == "error"
        assert response["error_code"] == "token_expired"
        assert response["error_message"] == "Token has expired"

    @pytest.mark.asyncio
    async def test_failed_auth_logs_warning(self):
        """Test that failed auth logs warning with details"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()
        mock_logger = Mock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager,
            logger=mock_logger
        )

        # Setup failed auth
        auth_result = MockAuthResult(
            success=False,
            error_code="auth_failed",
            error_message="Invalid credentials"
        )
        mock_auth_handler.authenticate_token.return_value = auth_result

        # Handle auth
        message = {"token": "bad_token"}
        await handler.handle_auth("client_bad", message)

        # Verify logging
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "websocket_auth.auth_failed"
        assert call_args[0][1]["client_id"] == "client_bad"
        assert call_args[0][1]["error_code"] == "auth_failed"

    @pytest.mark.asyncio
    async def test_failed_auth_does_not_update_connection(self):
        """Test that failed auth does not update connection metadata"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager
        )

        # Setup failed auth
        auth_result = MockAuthResult(
            success=False,
            error_code="invalid_token",
            error_message="Bad token"
        )
        mock_auth_handler.authenticate_token.return_value = auth_result

        mock_connection = MockConnection()
        mock_connection_manager.get_connection.return_value = mock_connection

        # Handle auth
        message = {"token": "bad_token"}
        await handler.handle_auth("client_fail", message)

        # Verify connection was NOT updated
        assert "authenticated" not in mock_connection.__dict__
        assert "user_id" not in mock_connection.__dict__

    @pytest.mark.asyncio
    async def test_failed_auth_with_no_error_details(self):
        """Test failed auth when auth_result has no error details"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager
        )

        # Setup failed auth with no error details
        auth_result = MockAuthResult(success=False)
        mock_auth_handler.authenticate_token.return_value = auth_result

        # Handle auth
        message = {"token": "token"}
        response = await handler.handle_auth("client", message)

        # Verify default error response
        assert response["type"] == "error"
        assert response["error_code"] == "auth_failed"
        assert response["error_message"] == "Authentication failed"


class TestAuthMessageHandlerEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_auth_with_missing_token(self):
        """Test auth message with missing token field"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager
        )

        # Setup failed auth (empty token treated as invalid)
        auth_result = MockAuthResult(
            success=False,
            error_code="missing_token",
            error_message="Token is required"
        )
        mock_auth_handler.authenticate_token.return_value = auth_result

        # Handle auth with no token
        message = {}
        response = await handler.handle_auth("client", message)

        # Verify error response
        assert response["type"] == "error"

        # Verify empty string was passed to auth handler
        mock_auth_handler.authenticate_token.assert_called_once()
        assert mock_auth_handler.authenticate_token.call_args[0][0] == ""

    @pytest.mark.asyncio
    async def test_auth_when_connection_not_found(self):
        """Test auth when connection is not found in connection manager"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager
        )

        # Setup successful auth
        user_session = MockUserSession(
            user_id="user_no_conn",
            permissions=["read"],
            expires_at=datetime.now() + timedelta(hours=1)
        )
        auth_result = MockAuthResult(success=True, user_session=user_session)
        mock_auth_handler.authenticate_token.return_value = auth_result

        # Connection not found
        mock_connection_manager.get_connection.return_value = None

        # Handle auth - should still succeed (connection may not exist yet)
        message = {"token": "valid_token"}
        response = await handler.handle_auth("client_no_conn", message)

        # Verify success response (even though connection wasn't updated)
        assert response["type"] == "response"
        assert response["status"] == "authenticated"

    @pytest.mark.asyncio
    async def test_auth_without_logger(self):
        """Test that handler works without logger"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()

        # Create handler without logger
        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager,
            logger=None
        )

        # Setup failed auth
        auth_result = MockAuthResult(
            success=False,
            error_code="bad_token"
        )
        mock_auth_handler.authenticate_token.return_value = auth_result

        # Should not raise exception
        message = {"token": "token"}
        response = await handler.handle_auth("client", message)

        assert response["type"] == "error"

    @pytest.mark.asyncio
    async def test_auth_success_without_user_session(self):
        """Test auth when success=True but user_session is None (edge case)"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager
        )

        # Success but no session (should be treated as failure)
        auth_result = MockAuthResult(success=True, user_session=None)
        mock_auth_handler.authenticate_token.return_value = auth_result

        message = {"token": "weird_token"}
        response = await handler.handle_auth("client", message)

        # Should return error (no user_session to extract data from)
        assert response["type"] == "error"


class TestAuthMessageHandlerIntegration:
    """Integration-style tests"""

    @pytest.mark.asyncio
    async def test_full_auth_flow_success(self):
        """Test complete successful authentication flow"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()
        mock_logger = Mock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager,
            logger=mock_logger
        )

        # Setup
        expires_at = datetime.now() + timedelta(hours=1)
        user_session = MockUserSession(
            user_id="integration_user",
            permissions=["read", "write"],
            expires_at=expires_at
        )
        auth_result = MockAuthResult(success=True, user_session=user_session)
        mock_auth_handler.authenticate_token.return_value = auth_result

        mock_connection = MockConnection()
        mock_connection_manager.get_connection.return_value = mock_connection

        # Execute
        message = {"token": "integration_token_123"}
        response = await handler.handle_auth("integration_client", message)

        # Verify all aspects
        assert response["type"] == "response"
        assert response["status"] == "authenticated"
        assert response["user_id"] == "integration_user"
        assert mock_connection.__dict__["authenticated"] is True
        assert mock_connection.__dict__["user_id"] == "integration_user"

        # Verify no error logging
        mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_auth_flow_failure(self):
        """Test complete failed authentication flow"""
        mock_auth_handler = AsyncMock()
        mock_connection_manager = AsyncMock()
        mock_logger = Mock()

        handler = AuthMessageHandler(
            auth_handler=mock_auth_handler,
            connection_manager=mock_connection_manager,
            logger=mock_logger
        )

        # Setup failure
        auth_result = MockAuthResult(
            success=False,
            error_code="invalid_token",
            error_message="Token is malformed"
        )
        mock_auth_handler.authenticate_token.return_value = auth_result

        # Execute
        message = {"token": "bad_token"}
        response = await handler.handle_auth("bad_client", message)

        # Verify all aspects
        assert response["type"] == "error"
        assert response["error_code"] == "invalid_token"
        mock_logger.warning.assert_called_once()

        # Verify connection was queried but not updated
        mock_connection_manager.get_connection.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
