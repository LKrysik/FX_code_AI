"""
Unit tests for ConnectionLifecycle
===================================
Tests connection lifecycle orchestration: accept, message handling, disconnect.

Test coverage:
- Client IP extraction
- User agent extraction
- Connection metadata building
- Message processing orchestration
- Rate limiting enforcement
- JSON parsing
- Message routing
- Response sending
- Connection cleanup
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from src.api.websocket.lifecycle import ConnectionLifecycle


class MockWebSocket:
    """Mock WebSocket connection"""
    def __init__(self, remote_address=("192.168.1.100", 12345)):
        self.remote_address = remote_address
        self.request_headers = {"User-Agent": "Mozilla/5.0"}


class MockConnection:
    """Mock connection object"""
    def __init__(self):
        self.__dict__ = {}
        self.ip_address = "192.168.1.100"
        self.metadata = {"ip_address": "192.168.1.100"}


class TestConnectionLifecycleExtraction:
    """Test metadata extraction methods"""

    def test_extract_client_ip_websockets_library(self):
        """Test IP extraction from websockets library"""
        mock_connection_manager = Mock()
        mock_session_store = Mock()
        mock_message_router = Mock()
        mock_rate_limiter = Mock()
        mock_subscription_manager = Mock()

        lifecycle = ConnectionLifecycle(
            connection_manager=mock_connection_manager,
            session_store=mock_session_store,
            message_router=mock_message_router,
            rate_limiter=mock_rate_limiter,
            subscription_manager=mock_subscription_manager
        )

        mock_ws = MockWebSocket(remote_address=("10.0.0.1", 54321))
        ip = lifecycle._extract_client_ip(mock_ws)

        assert ip == "10.0.0.1"

    def test_extract_client_ip_fallback(self):
        """Test IP extraction fallback"""
        lifecycle = ConnectionLifecycle(None, None, None, None, None)

        # WebSocket with no IP info
        mock_ws = Mock(spec=[])
        ip = lifecycle._extract_client_ip(mock_ws)

        assert ip == "127.0.0.1"

    def test_extract_user_agent_success(self):
        """Test User-Agent extraction"""
        lifecycle = ConnectionLifecycle(None, None, None, None, None)

        mock_ws = MockWebSocket()
        user_agent = lifecycle._extract_user_agent(mock_ws)

        assert user_agent == "Mozilla/5.0"

    def test_extract_user_agent_fallback(self):
        """Test User-Agent extraction fallback"""
        lifecycle = ConnectionLifecycle(None, None, None, None, None)

        mock_ws = Mock(spec=[])
        user_agent = lifecycle._extract_user_agent(mock_ws)

        assert user_agent == "unknown"

    def test_build_connection_metadata(self):
        """Test connection metadata building"""
        lifecycle = ConnectionLifecycle(None, None, None, None, None)

        mock_ws = MockWebSocket()
        metadata = lifecycle._build_connection_metadata(mock_ws, "192.168.1.100")

        assert metadata["ip_address"] == "192.168.1.100"
        assert metadata["user_agent"] == "Mozilla/5.0"
        assert "path" in metadata


class TestConnectionLifecycleMessageProcessing:
    """Test message processing orchestration"""

    @pytest.mark.asyncio
    async def test_process_message_rate_limit_exceeded(self):
        """Test message processing when rate limit exceeded"""
        mock_connection_manager = AsyncMock()
        mock_session_store = Mock()
        mock_message_router = AsyncMock()
        mock_rate_limiter = Mock()
        mock_subscription_manager = Mock()

        lifecycle = ConnectionLifecycle(
            connection_manager=mock_connection_manager,
            session_store=mock_session_store,
            message_router=mock_message_router,
            rate_limiter=mock_rate_limiter,
            subscription_manager=mock_subscription_manager
        )

        # Setup rate limit exceeded
        mock_rate_limiter.check_message_limit.return_value = False

        # Should send error and not process message
        await lifecycle._process_message("client_123", "192.168.1.100", '{"test": "data"}')

        # Verify rate limiter was checked
        mock_rate_limiter.check_message_limit.assert_called_once_with("192.168.1.100")

        # Verify message was NOT routed
        mock_message_router.route_message.assert_not_called()

        # Verify connection manager send was called with rate limit error
        mock_connection_manager.send_to_client.assert_called_once()
        call_args = mock_connection_manager.send_to_client.call_args[0]
        assert call_args[0] == "client_123"

    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self):
        """Test message processing with invalid JSON"""
        mock_connection_manager = AsyncMock()
        mock_session_store = Mock()
        mock_message_router = AsyncMock()
        mock_rate_limiter = Mock()
        mock_subscription_manager = Mock()

        lifecycle = ConnectionLifecycle(
            connection_manager=mock_connection_manager,
            session_store=mock_session_store,
            message_router=mock_message_router,
            rate_limiter=mock_rate_limiter,
            subscription_manager=mock_subscription_manager
        )

        # Setup rate limit passed
        mock_rate_limiter.check_message_limit.return_value = True

        # Invalid JSON
        await lifecycle._process_message("client_123", "192.168.1.100", "invalid json {")

        # Verify message was NOT routed
        mock_message_router.route_message.assert_not_called()

        # Verify error was sent
        mock_connection_manager.send_to_client.assert_called()

    @pytest.mark.asyncio
    @patch('src.api.websocket.lifecycle.connection_lifecycle.sanitizer')
    async def test_process_message_success(self, mock_sanitizer):
        """Test successful message processing"""
        mock_connection_manager = AsyncMock()
        mock_session_store = Mock()
        mock_message_router = AsyncMock()
        mock_rate_limiter = Mock()
        mock_subscription_manager = Mock()

        lifecycle = ConnectionLifecycle(
            connection_manager=mock_connection_manager,
            session_store=mock_session_store,
            message_router=mock_message_router,
            rate_limiter=mock_rate_limiter,
            subscription_manager=mock_subscription_manager
        )

        # Setup mocks
        mock_rate_limiter.check_message_limit.return_value = True
        mock_sanitizer.sanitize_websocket_message.return_value = {"type": "test", "data": "value"}
        mock_message_router.route_message.return_value = {"type": "response", "status": "ok"}
        mock_connection_manager.get_connection.return_value = MockConnection()

        # Process valid message
        await lifecycle._process_message("client_123", "192.168.1.100", '{"type": "test", "data": "value"}')

        # Verify message was routed
        mock_message_router.route_message.assert_called_once()

        # Verify response was sent
        mock_connection_manager.send_to_client.assert_called()

        # Verify activity was recorded
        mock_connection_manager.record_message_activity.assert_called()

    @pytest.mark.asyncio
    async def test_send_to_client_success(self):
        """Test sending message to client"""
        mock_connection_manager = AsyncMock()
        mock_session_store = Mock()
        mock_message_router = AsyncMock()
        mock_rate_limiter = Mock()
        mock_subscription_manager = Mock()

        lifecycle = ConnectionLifecycle(
            connection_manager=mock_connection_manager,
            session_store=mock_session_store,
            message_router=mock_message_router,
            rate_limiter=mock_rate_limiter,
            subscription_manager=mock_subscription_manager
        )

        # Setup mocks
        mock_connection = MockConnection()
        mock_connection.last_request_id = "req_123"
        mock_connection_manager.get_connection.return_value = mock_connection
        mock_connection_manager.send_to_client.return_value = True

        # Send message
        message = {"type": "response", "data": "test"}
        with patch('src.api.websocket.lifecycle.connection_lifecycle.ensure_envelope') as mock_envelope:
            mock_envelope.return_value = {"type": "response", "data": "test", "id": "req_123"}

            success = await lifecycle._send_to_client("client_123", message)

            # Verify success
            assert success is True

            # Verify envelope enrichment was called
            mock_envelope.assert_called_once()

            # Verify connection manager send was called
            mock_connection_manager.send_to_client.assert_called_once()

            # Verify activity was recorded
            mock_connection_manager.record_message_activity.assert_called()


class TestConnectionLifecycleCleanup:
    """Test connection cleanup"""

    @pytest.mark.asyncio
    async def test_cleanup_connection_saves_session(self):
        """Test cleanup saves session state"""
        mock_connection_manager = AsyncMock()
        mock_session_store = Mock()
        mock_message_router = AsyncMock()
        mock_rate_limiter = Mock()
        mock_subscription_manager = Mock()

        lifecycle = ConnectionLifecycle(
            connection_manager=mock_connection_manager,
            session_store=mock_session_store,
            message_router=mock_message_router,
            rate_limiter=mock_rate_limiter,
            subscription_manager=mock_subscription_manager
        )

        # Setup connection with data
        mock_connection = MockConnection()
        mock_connection.authenticated = True
        mock_connection.user_id = "user_456"
        mock_connection.permissions = ["read", "write"]
        mock_connection_manager.get_connection.return_value = mock_connection
        mock_subscription_manager.get_client_subscriptions.return_value = {"market_data": {}}

        metadata = {
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0"
        }

        # Cleanup
        await lifecycle._cleanup_connection("client_cleanup", metadata)

        # Verify session was saved
        mock_session_store.save_session.assert_called_once()
        call_args = mock_session_store.save_session.call_args[0]
        assert call_args[0] == "client_cleanup"
        session_data = call_args[1]
        assert session_data["authenticated"] is True
        assert session_data["user_id"] == "user_456"
        assert "market_data" in session_data["subscriptions"]

        # Verify connection was removed
        mock_connection_manager.remove_connection.assert_called_once_with(
            "client_cleanup", "disconnected"
        )

    @pytest.mark.asyncio
    async def test_cleanup_connection_handles_error(self):
        """Test cleanup handles errors gracefully"""
        mock_connection_manager = AsyncMock()
        mock_session_store = Mock()
        mock_message_router = AsyncMock()
        mock_rate_limiter = Mock()
        mock_subscription_manager = Mock()

        lifecycle = ConnectionLifecycle(
            connection_manager=mock_connection_manager,
            session_store=mock_session_store,
            message_router=mock_message_router,
            rate_limiter=mock_rate_limiter,
            subscription_manager=mock_subscription_manager
        )

        # Setup error
        mock_connection_manager.get_connection.side_effect = Exception("Connection error")

        metadata = {"ip_address": "192.168.1.100"}

        # Should not raise exception
        await lifecycle._cleanup_connection("client_error", metadata)

        # Verify connection was still removed
        mock_connection_manager.remove_connection.assert_called_once()


class TestConnectionLifecycleGetClientIP:
    """Test getting client IP by ID"""

    @pytest.mark.asyncio
    async def test_get_client_ip_by_id_success(self):
        """Test getting client IP by ID"""
        mock_connection_manager = AsyncMock()
        mock_session_store = Mock()
        mock_message_router = AsyncMock()
        mock_rate_limiter = Mock()
        mock_subscription_manager = Mock()

        lifecycle = ConnectionLifecycle(
            connection_manager=mock_connection_manager,
            session_store=mock_session_store,
            message_router=mock_message_router,
            rate_limiter=mock_rate_limiter,
            subscription_manager=mock_subscription_manager
        )

        # Setup connection with IP
        mock_connection = MockConnection()
        mock_connection.ip_address = "10.0.0.5"
        mock_connection_manager.get_connection.return_value = mock_connection

        ip = await lifecycle._get_client_ip_by_id("client_ip_test")

        assert ip == "10.0.0.5"

    @pytest.mark.asyncio
    async def test_get_client_ip_by_id_fallback(self):
        """Test getting client IP by ID fallback"""
        mock_connection_manager = AsyncMock()
        lifecycle = ConnectionLifecycle(
            mock_connection_manager, None, None, None, None
        )

        # Connection not found
        mock_connection_manager.get_connection.return_value = None

        ip = await lifecycle._get_client_ip_by_id("client_not_found")

        assert ip == "unknown"


class TestConnectionLifecycleStatistics:
    """Test statistics tracking"""

    def test_get_stats_initial_state(self):
        """Test get_stats returns initial state"""
        lifecycle = ConnectionLifecycle(None, None, None, None, None)

        stats = lifecycle.get_stats()

        assert stats["total_connections_handled"] == 0
        assert stats["total_messages_processed"] == 0

    @pytest.mark.asyncio
    @patch('src.api.websocket.lifecycle.connection_lifecycle.sanitizer')
    async def test_message_processing_updates_stats(self, mock_sanitizer):
        """Test message processing updates statistics"""
        mock_connection_manager = AsyncMock()
        mock_session_store = Mock()
        mock_message_router = AsyncMock()
        mock_rate_limiter = Mock()
        mock_subscription_manager = Mock()

        lifecycle = ConnectionLifecycle(
            connection_manager=mock_connection_manager,
            session_store=mock_session_store,
            message_router=mock_message_router,
            rate_limiter=mock_rate_limiter,
            subscription_manager=mock_subscription_manager
        )

        # Setup mocks
        mock_rate_limiter.check_message_limit.return_value = True
        mock_sanitizer.sanitize_websocket_message.return_value = {"type": "test"}
        mock_message_router.route_message.return_value = {"type": "response"}
        mock_connection_manager.get_connection.return_value = MockConnection()

        # Process message
        await lifecycle._process_message("client", "192.168.1.1", '{"type": "test"}')

        # Verify stats updated
        stats = lifecycle.get_stats()
        assert stats["total_messages_processed"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
