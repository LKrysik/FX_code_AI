"""
SessionMessageHandler - Trading Session Management
==================================================
Handles trading session lifecycle: start, stop, and status queries.

Responsibilities:
- Session start requests (backtest, live, paper trading)
- Session stop requests with strategy deactivation
- Session status queries
- Authentication and permission validation

Complex business logic (strategy activation, conflict resolution, lock management)
is delegated to callbacks provided by the server.

Extracted from WebSocketAPIServer (lines 1885-2334)
"""

from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable
from src.api.websocket.utils import ErrorHandler


class SessionMessageHandler:
    """
    Handles trading session management messages.

    Session lifecycle:
    1. Client sends SESSION_START → validates auth/permissions → delegates to session_starter
    2. Trading occurs
    3. Client sends SESSION_STOP → delegates to session_stopper
    4. Client queries SESSION_STATUS → delegates to controller

    Dependencies:
    - connection_manager: For authentication checks
    - auth_handler: For permission validation
    - controller: For session operations
    - error_handler: For standardized error responses
    - session_starter: Async callable for starting sessions (complex logic)
    - session_stopper: Async callable for stopping sessions (complex logic)
    """

    def __init__(self,
                 connection_manager,
                 auth_handler,
                 controller,
                 error_handler: ErrorHandler,
                 session_starter: Optional[Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
                 session_stopper: Optional[Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
                 logger = None):
        """
        Initialize session handler.

        Args:
            connection_manager: ConnectionManager for authentication
            auth_handler: AuthHandler for permission checks
            controller: Trading controller for session operations
            error_handler: ErrorHandler for standardized errors
            session_starter: Async callable(client_id, message) for session start logic
            session_stopper: Async callable(client_id, message) for session stop logic
            logger: Optional logger for diagnostics
        """
        self.connection_manager = connection_manager
        self.auth_handler = auth_handler
        self.controller = controller
        self.error_handler = error_handler
        self.session_starter = session_starter
        self.session_stopper = session_stopper
        self.logger = logger

    async def handle_session_start(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle session start request.

        Message format:
        {
            "type": "session_start",
            "session_type": "backtest",  // or "live", "paper"
            "strategy_config": {
                "MovingAverageCross": ["BTC_USDT", "ETH_USDT"],
                "RSIStrategy": ["BTC_USDT"]
            },
            "config": {...additional config...},
            "idempotent": false
        }

        Success response:
        {
            "type": "response",
            "status": "session_started",
            "session_id": "session_abc123",
            "session_type": "backtest",
            "strategy_config": {...},
            "symbols": ["BTC_USDT", "ETH_USDT"],
            "activation_results": {
                "success": true,
                "activated": [...]
            },
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Session start message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:1885-2146 (_handle_session_start)

        Note: Complex business logic (strategy activation, conflict resolution,
        lock management) is delegated to session_starter callback.
        """
        # Validate controller availability
        if not self.controller:
            return self.error_handler.service_unavailable(
                "Trading controller",
                session_id=message.get("session_id")
            )

        # Validate authentication
        connection = await self.connection_manager.get_connection(client_id)
        if not getattr(connection, 'authenticated', False):
            return {
                "type": "error",
                "error_code": "authentication_required",
                "error_message": "Authentication required for session commands",
                "timestamp": datetime.now().isoformat()
            }

        # Validate permissions for live trading
        session_token = getattr(connection, 'session_token', None)
        if session_token:
            try:
                from src.domain.models.permission import Permission
                user_session = await self.auth_handler.validate_session(session_token)
                if user_session and not user_session.has_permission(Permission.EXECUTE_LIVE_TRADING):
                    return self.error_handler.insufficient_permissions(
                        "EXECUTE_LIVE_TRADING",
                        session_id=message.get("session_id")
                    )
            except Exception:
                # Permission check failed non-critically
                pass

        # Validate session type
        session_type = message.get("session_type")
        if session_type not in ("backtest", "live", "paper"):
            return self.error_handler.invalid_parameter(
                "session_type",
                f"Must be one of: backtest, live, paper. Got: {session_type}",
                session_id=message.get("session_id")
            )

        # Validate strategy configuration
        strategy_config = message.get("strategy_config", {})
        if not strategy_config:
            return self.error_handler.missing_parameters(
                ["strategy_config"],
                session_id=message.get("session_id")
            )

        # Delegate complex session start logic to callback
        if not self.session_starter:
            return self.error_handler.operation_failed(
                "session_start",
                Exception("Session starter not configured"),
                session_id=message.get("session_id")
            )

        try:
            result = await self.session_starter(client_id, message)
            return result
        except Exception as e:
            return self.error_handler.operation_failed(
                "session_start",
                e,
                session_id=message.get("session_id")
            )

    async def handle_session_stop(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle session stop request.

        Message format:
        {
            "type": "session_stop",
            "session_id": "session_abc123"
        }

        Success response:
        {
            "type": "response",
            "status": "session_stopped",
            "session_id": "session_abc123",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Session stop message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:2231-2293 (_handle_session_stop)

        Note: Complex logic (strategy deactivation, lock management) is
        delegated to session_stopper callback.
        """
        # Validate controller availability
        if not self.controller:
            return self.error_handler.service_unavailable(
                "Trading controller",
                session_id=message.get("session_id")
            )

        # Delegate complex session stop logic to callback
        if not self.session_stopper:
            return self.error_handler.operation_failed(
                "session_stop",
                Exception("Session stopper not configured"),
                session_id=message.get("session_id")
            )

        try:
            result = await self.session_stopper(client_id, message)
            return result
        except Exception as e:
            return self.error_handler.operation_failed(
                "session_stop",
                e,
                session_id=message.get("session_id")
            )

    async def handle_session_status(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle session status query.

        Message format:
        {
            "type": "session_status",
            "session_id": "session_abc123"  // optional
        }

        Success response:
        {
            "type": "response",
            "status": "session_status",
            "session_data": {
                "session_id": "session_abc123",
                "status": "running",
                "symbols": ["BTC_USDT"],
                ...controller status fields...
            },
            "timestamp": "2025-11-03T11:00:00"
        }

        No active session response:
        {
            "type": "response",
            "status": "no_active_session",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Session status message

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:2295-2334 (_handle_session_status)
        """
        # Validate controller availability
        if not self.controller:
            return self.error_handler.service_unavailable(
                "Trading controller",
                session_id=message.get("session_id")
            )

        try:
            # Get execution status from controller
            status = self.controller.get_execution_status()

            if status:
                return {
                    "type": "response",
                    "status": "session_status",
                    "session_data": status,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "type": "response",
                    "status": "no_active_session",
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            return {
                "type": "error",
                "error_code": "status_retrieval_failed",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
