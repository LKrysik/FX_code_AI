"""
CollectionMessageHandler - Data Collection Management
=====================================================
Handles data collection operations: start, stop, status, and results queries.

Responsibilities:
- Start data collection sessions
- Stop data collection
- Query collection status
- Retrieve collection results

Extracted from WebSocketAPIServer (lines 2337-2610+)
"""

from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable
from src.api.websocket.utils import ErrorHandler


class CollectionMessageHandler:
    """
    Handles data collection management messages.

    Collection lifecycle:
    1. Client sends COLLECTION_START → starts data collection for symbols
    2. Data collection runs
    3. Client sends COLLECTION_STOP → stops collection
    4. Client queries COLLECTION_STATUS or RESULTS_REQUEST → gets results

    Dependencies:
    - controller: For collection operations
    - error_handler: For standardized error responses
    - status_provider: Async callable for status queries (optional delegation)
    - results_provider: Async callable for results queries (complex logic delegation)
    """

    def __init__(self,
                 controller,
                 error_handler: ErrorHandler,
                 status_provider: Optional[Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
                 results_provider: Optional[Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
                 logger = None):
        """
        Initialize collection handler.

        Args:
            controller: Trading controller for collection operations
            error_handler: ErrorHandler for standardized errors
            status_provider: Async callable(client_id, message) for status queries
            results_provider: Async callable(client_id, message) for results queries
            logger: Optional logger for diagnostics
        """
        self.controller = controller
        self.error_handler = error_handler
        self.status_provider = status_provider
        self.results_provider = results_provider
        self.logger = logger

    async def handle_collection_start(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle data collection start request.

        Message format:
        {
            "type": "collection_start",
            "symbols": ["BTC_USDT", "ETH_USDT"],
            "duration": "1h"  // optional, default "1h"
        }

        Success response:
        {
            "type": "response",
            "status": "collection_started",
            "collection_id": "collection_abc123",
            "symbols": ["BTC_USDT", "ETH_USDT"],
            "duration": "1h",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Collection start message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:2337-2377 (_handle_collection_start)
        """
        # Validate controller availability
        if not self.controller:
            if self.logger:
                self.logger.error("websocket_collection.collection_start_failed", {
                    "client_id": client_id,
                    "reason": "Trading controller not initialized",
                    "message": message
                })
            return self.error_handler.service_unavailable(
                "Trading controller",
                session_id=message.get("collection_id")
            )

        # Extract parameters
        symbols = message.get("symbols", [])
        duration = message.get("duration", "1h")

        try:
            # Start data collection via controller
            command_id = await self.controller.start_data_collection(
                symbols=symbols,
                duration=duration
            )

            return {
                "type": "response",
                "status": "collection_started",
                "collection_id": command_id,
                "symbols": symbols,
                "duration": duration,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "type": "error",
                "error_code": "collection_start_failed",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def handle_collection_stop(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle data collection stop request.

        Message format:
        {
            "type": "collection_stop",
            "collection_id": "collection_abc123"
        }

        Success response:
        {
            "type": "response",
            "status": "stopped",
            "collection_id": "collection_abc123",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Collection stop message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:2379-2406 (_handle_collection_stop)
        """
        # Validate controller availability
        if not self.controller:
            return self.error_handler.service_unavailable(
                "Trading controller",
                session_id=message.get("collection_id")
            )

        collection_id = message.get("collection_id")

        try:
            # Stop execution via controller
            await self.controller.stop_execution()

            return {
                "type": "response",
                "status": "stopped",
                "collection_id": collection_id,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "type": "error",
                "error_code": "collection_stop_failed",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def handle_collection_status(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle data collection status query.

        Message format:
        {
            "type": "collection_status",
            "collection_id": "collection_abc123"
        }

        Args:
            client_id: Unique client identifier
            message: Collection status message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:2408-2411 (_handle_collection_status)

        Note: Delegates to status_provider (typically same as session status).
        """
        # Delegate to status provider if available
        if self.status_provider:
            return await self.status_provider(client_id, message)

        # Fallback: simple status from controller
        if not self.controller:
            return self.error_handler.service_unavailable(
                "Trading controller",
                session_id=message.get("collection_id")
            )

        try:
            status = self.controller.get_execution_status()

            if status:
                return {
                    "type": "response",
                    "status": "collection_status",
                    "collection_data": status,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "type": "response",
                    "status": "no_active_collection",
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            return {
                "type": "error",
                "error_code": "status_retrieval_failed",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def handle_results_request(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle results request (session results, strategy results, etc.).

        Message format:
        {
            "type": "results_request",
            "request_type": "session_results",  // or "strategy_results", etc.
            "session_id": "session_abc123",
            "symbol": "BTC_USDT",  // optional
            "strategy": "MovingAverageCross"  // optional
        }

        Args:
            client_id: Unique client identifier
            message: Results request message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:2413-2610+ (_handle_results_request, ~197 lines)

        Note: Complex results normalization logic is delegated to results_provider callback.
        This includes symbol counting, aggregate calculations, and per-strategy results.
        """
        # Validate controller availability
        if not self.controller:
            return self.error_handler.service_unavailable(
                "Trading controller",
                session_id=message.get("session_id")
            )

        # Delegate to results provider if available (complex logic)
        if self.results_provider:
            try:
                return await self.results_provider(client_id, message)
            except Exception as e:
                return self.error_handler.operation_failed(
                    "results_request",
                    e,
                    session_id=message.get("session_id")
                )

        # Fallback: simple status response
        try:
            execution_status = self.controller.get_execution_status()

            return {
                "type": "response",
                "status": "results",
                "data": execution_status or {},
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "type": "error",
                "error_code": "results_retrieval_failed",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
