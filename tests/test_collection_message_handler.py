"""
Unit tests for CollectionMessageHandler
========================================
Tests data collection start/stop/status and results handling.

Test coverage:
- Collection start (validation, delegation)
- Collection stop
- Collection status (with delegation)
- Results request (complex delegation)
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.api.websocket.handlers import CollectionMessageHandler
from src.api.websocket.utils import ErrorHandler


class TestCollectionHandlerStart:
    """Test collection start (handle_collection_start)"""

    @pytest.mark.asyncio
    async def test_collection_start_without_controller(self):
        """Test collection start fails when controller not available"""
        mock_error_handler = ErrorHandler()
        mock_logger = Mock()

        handler = CollectionMessageHandler(
            controller=None,  # No controller
            error_handler=mock_error_handler,
            logger=mock_logger
        )

        message = {"symbols": ["BTC_USDT"], "duration": "1h"}
        response = await handler.handle_collection_start("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_collection_start_success(self):
        """Test successful collection start"""
        mock_controller = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Setup controller to return collection ID
        mock_controller.start_data_collection.return_value = "collection_abc123"

        message = {
            "symbols": ["BTC_USDT", "ETH_USDT"],
            "duration": "2h"
        }
        response = await handler.handle_collection_start("client_start", message)

        # Verify controller was called correctly
        mock_controller.start_data_collection.assert_called_once_with(
            symbols=["BTC_USDT", "ETH_USDT"],
            duration="2h"
        )

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "collection_started"
        assert response["collection_id"] == "collection_abc123"
        assert response["symbols"] == ["BTC_USDT", "ETH_USDT"]
        assert response["duration"] == "2h"

    @pytest.mark.asyncio
    async def test_collection_start_default_duration(self):
        """Test collection start uses default duration"""
        mock_controller = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        mock_controller.start_data_collection.return_value = "collection_123"

        # No duration specified
        message = {"symbols": ["BTC_USDT"]}
        response = await handler.handle_collection_start("client", message)

        # Verify default duration "1h" was used
        mock_controller.start_data_collection.assert_called_once()
        call_kwargs = mock_controller.start_data_collection.call_args[1]
        assert call_kwargs["duration"] == "1h"

    @pytest.mark.asyncio
    async def test_collection_start_empty_symbols(self):
        """Test collection start with empty symbols list"""
        mock_controller = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        mock_controller.start_data_collection.return_value = "collection_empty"

        # Empty symbols
        message = {"symbols": [], "duration": "30m"}
        response = await handler.handle_collection_start("client", message)

        # Should still process (controller will handle validation)
        assert response["status"] == "collection_started"
        assert response["symbols"] == []

    @pytest.mark.asyncio
    async def test_collection_start_controller_exception(self):
        """Test collection start handles controller exception"""
        mock_controller = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Controller raises exception
        mock_controller.start_data_collection.side_effect = ValueError("Invalid duration format")

        message = {"symbols": ["BTC_USDT"], "duration": "invalid"}
        response = await handler.handle_collection_start("client", message)

        # Verify error handling
        assert response["type"] == "error"
        assert response["error_code"] == "collection_start_failed"
        assert "Invalid duration format" in response["error_message"]


class TestCollectionHandlerStop:
    """Test collection stop (handle_collection_stop)"""

    @pytest.mark.asyncio
    async def test_collection_stop_without_controller(self):
        """Test collection stop fails when controller not available"""
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=None,
            error_handler=mock_error_handler
        )

        message = {"collection_id": "collection_123"}
        response = await handler.handle_collection_stop("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_collection_stop_success(self):
        """Test successful collection stop"""
        mock_controller = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        message = {"collection_id": "collection_456"}
        response = await handler.handle_collection_stop("client_stop", message)

        # Verify controller was called
        mock_controller.stop_execution.assert_called_once()

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "stopped"
        assert response["collection_id"] == "collection_456"

    @pytest.mark.asyncio
    async def test_collection_stop_controller_exception(self):
        """Test collection stop handles controller exception"""
        mock_controller = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # Controller raises exception
        mock_controller.stop_execution.side_effect = Exception("Stop failed")

        message = {"collection_id": "collection_fail"}
        response = await handler.handle_collection_stop("client", message)

        # Verify error handling
        assert response["type"] == "error"
        assert response["error_code"] == "collection_stop_failed"
        assert "Stop failed" in response["error_message"]


class TestCollectionHandlerStatus:
    """Test collection status (handle_collection_status)"""

    @pytest.mark.asyncio
    async def test_collection_status_with_status_provider(self):
        """Test collection status delegates to status_provider"""
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()
        mock_status_provider = AsyncMock()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler,
            status_provider=mock_status_provider
        )

        # Setup status provider
        mock_status_provider.return_value = {
            "type": "response",
            "status": "collection_status",
            "collection_data": {"collection_id": "col_123"}
        }

        message = {"collection_id": "col_123"}
        response = await handler.handle_collection_status("client_status", message)

        # Verify delegation
        mock_status_provider.assert_called_once_with("client_status", message)

        # Verify response
        assert response["status"] == "collection_status"

    @pytest.mark.asyncio
    async def test_collection_status_without_provider_active_collection(self):
        """Test collection status fallback with active collection"""
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler,
            status_provider=None  # No provider
        )

        # Setup controller with active collection
        mock_controller.get_execution_status.return_value = {
            "collection_id": "col_789",
            "status": "running",
            "symbols": ["BTC_USDT"]
        }

        message = {}
        response = await handler.handle_collection_status("client", message)

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "collection_status"
        assert response["collection_data"]["collection_id"] == "col_789"

    @pytest.mark.asyncio
    async def test_collection_status_without_provider_no_collection(self):
        """Test collection status fallback with no active collection"""
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler,
            status_provider=None
        )

        # Setup controller with no active collection
        mock_controller.get_execution_status.return_value = None

        message = {}
        response = await handler.handle_collection_status("client", message)

        # Verify response
        assert response["type"] == "response"
        assert response["status"] == "no_active_collection"

    @pytest.mark.asyncio
    async def test_collection_status_without_controller(self):
        """Test collection status fails when controller not available"""
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=None,
            error_handler=mock_error_handler,
            status_provider=None
        )

        message = {}
        response = await handler.handle_collection_status("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "service_unavailable"


class TestCollectionHandlerResults:
    """Test results request (handle_results_request)"""

    @pytest.mark.asyncio
    async def test_results_request_without_controller(self):
        """Test results request fails when controller not available"""
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=None,
            error_handler=mock_error_handler
        )

        message = {"request_type": "session_results"}
        response = await handler.handle_results_request("client", message)

        # Verify error
        assert response["type"] == "error"
        assert response["error_code"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_results_request_with_results_provider(self):
        """Test results request delegates to results_provider"""
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()
        mock_results_provider = AsyncMock()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler,
            results_provider=mock_results_provider
        )

        # Setup results provider
        mock_results_provider.return_value = {
            "type": "response",
            "status": "results",
            "data": {"total_trades": 100}
        }

        message = {
            "request_type": "session_results",
            "session_id": "session_abc"
        }
        response = await handler.handle_results_request("client_results", message)

        # Verify delegation
        mock_results_provider.assert_called_once_with("client_results", message)

        # Verify response
        assert response["status"] == "results"
        assert response["data"]["total_trades"] == 100

    @pytest.mark.asyncio
    async def test_results_request_provider_exception(self):
        """Test results request handles provider exception"""
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()
        mock_results_provider = AsyncMock()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler,
            results_provider=mock_results_provider
        )

        # Results provider raises exception
        mock_results_provider.side_effect = Exception("Results calculation failed")

        message = {"request_type": "strategy_results"}
        response = await handler.handle_results_request("client", message)

        # Verify error handling
        assert response["type"] == "error"
        assert response["error_code"] == "operation_failed"
        assert "Results calculation failed" in response["error_message"]

    @pytest.mark.asyncio
    async def test_results_request_without_provider_fallback(self):
        """Test results request fallback without results_provider"""
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler,
            results_provider=None  # No provider
        )

        # Setup controller execution status
        mock_controller.get_execution_status.return_value = {
            "session_id": "session_fallback",
            "status": "completed"
        }

        message = {"request_type": "session_results"}
        response = await handler.handle_results_request("client", message)

        # Verify fallback response
        assert response["type"] == "response"
        assert response["status"] == "results"
        assert response["data"]["session_id"] == "session_fallback"

    @pytest.mark.asyncio
    async def test_results_request_fallback_controller_exception(self):
        """Test results request fallback handles controller exception"""
        mock_controller = Mock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler,
            results_provider=None
        )

        # Controller raises exception
        mock_controller.get_execution_status.side_effect = Exception("Status error")

        message = {}
        response = await handler.handle_results_request("client", message)

        # Verify error handling
        assert response["type"] == "error"
        assert response["error_code"] == "results_retrieval_failed"


class TestCollectionHandlerEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_collection_start_missing_symbols(self):
        """Test collection start with missing symbols field"""
        mock_controller = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        mock_controller.start_data_collection.return_value = "collection_no_symbols"

        # No symbols field (defaults to empty list)
        message = {"duration": "1h"}
        response = await handler.handle_collection_start("client", message)

        # Should use empty list
        mock_controller.start_data_collection.assert_called_once()
        call_kwargs = mock_controller.start_data_collection.call_args[1]
        assert call_kwargs["symbols"] == []

    @pytest.mark.asyncio
    async def test_collection_stop_missing_collection_id(self):
        """Test collection stop works without collection_id"""
        mock_controller = AsyncMock()
        mock_error_handler = ErrorHandler()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler
        )

        # No collection_id in message
        message = {}
        response = await handler.handle_collection_stop("client", message)

        # Should still stop
        assert response["status"] == "stopped"
        assert response["collection_id"] is None


class TestCollectionHandlerIntegration:
    """Integration-style tests"""

    @pytest.mark.asyncio
    async def test_full_collection_lifecycle(self):
        """Test complete collection lifecycle: start, status, results, stop"""
        mock_controller = AsyncMock()
        mock_error_handler = ErrorHandler()
        mock_status_provider = AsyncMock()
        mock_results_provider = AsyncMock()

        handler = CollectionMessageHandler(
            controller=mock_controller,
            error_handler=mock_error_handler,
            status_provider=mock_status_provider,
            results_provider=mock_results_provider
        )

        # 1. Start collection
        mock_controller.start_data_collection.return_value = "integration_col"

        start_msg = {"symbols": ["BTC_USDT"], "duration": "1h"}
        start_response = await handler.handle_collection_start("client", start_msg)
        assert start_response["status"] == "collection_started"

        # 2. Query status
        mock_status_provider.return_value = {
            "type": "response",
            "status": "collection_status"
        }

        status_response = await handler.handle_collection_status("client", {})
        assert status_response["status"] == "collection_status"

        # 3. Get results
        mock_results_provider.return_value = {
            "type": "response",
            "status": "results",
            "data": {"records": 1000}
        }

        results_msg = {"request_type": "session_results"}
        results_response = await handler.handle_results_request("client", results_msg)
        assert results_response["status"] == "results"

        # 4. Stop collection
        stop_msg = {"collection_id": "integration_col"}
        stop_response = await handler.handle_collection_stop("client", stop_msg)
        assert stop_response["status"] == "stopped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
