"""
AuthMessageHandler - WebSocket Authentication Handler
=====================================================
Handles authentication-related WebSocket messages.

Responsibilities:
- Token-based authentication via AuthHandler
- Connection metadata updates (authenticated status, user_id, permissions)
- Authentication failure logging

Extracted from WebSocketAPIServer (lines 1211-1250)
"""

from datetime import datetime
from typing import Dict, Any, Optional
from src.api.websocket.utils import ClientUtils


class AuthMessageHandler:
    """
    Handles WebSocket authentication messages.

    Authentication flow:
    1. Client sends AUTH message with JWT token
    2. Handler validates token via AuthHandler
    3. On success: Update connection with user_id, permissions
    4. On failure: Return error response with code

    Dependencies:
    - auth_handler: For token validation
    - connection_manager: For connection metadata updates
    - logger: For authentication failure logging
    """

    def __init__(self,
                 auth_handler,
                 connection_manager,
                 logger = None):
        """
        Initialize authentication handler.

        Args:
            auth_handler: AuthHandler instance for token validation
            connection_manager: ConnectionManager for metadata updates
            logger: Optional logger for diagnostics
        """
        self.auth_handler = auth_handler
        self.connection_manager = connection_manager
        self.logger = logger

    async def handle_auth(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle authentication message.

        Message format:
        {
            "type": "auth",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }

        Success response:
        {
            "type": "response",
            "status": "authenticated",
            "user_id": "user_123",
            "permissions": ["read", "write"],
            "session_expires": "2025-11-03T12:00:00",
            "timestamp": "2025-11-03T11:00:00"
        }

        Error response:
        {
            "type": "error",
            "error_code": "invalid_token",
            "error_message": "Token is expired",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Authentication message with token

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:1211-1250 (handle_auth nested function)
        """
        token = message.get("token", "")

        # Get client IP for audit logging
        client_ip = await ClientUtils.get_client_ip_by_id(
            client_id,
            self.connection_manager,
            self.logger
        )

        # Validate token via AuthHandler
        auth_result = await self.auth_handler.authenticate_token(
            token, client_ip, "websocket_client"
        )

        if auth_result.success and auth_result.user_session:
            # Authentication successful - update connection metadata
            connection = await self.connection_manager.get_connection(client_id)
            if connection:
                # Add session info to connection (extend dataclass)
                connection.__dict__.update({
                    "authenticated": True,
                    "user_id": auth_result.user_session.user_id,
                    "permissions": auth_result.user_session.permissions
                })

            return {
                "type": "response",
                "status": "authenticated",
                "user_id": auth_result.user_session.user_id,
                "permissions": auth_result.user_session.permissions,
                "session_expires": auth_result.user_session.expires_at.isoformat(),
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Authentication failed - log and return error
            if self.logger:
                self.logger.warning("websocket_auth.auth_failed", {
                    "client_id": client_id,
                    "client_ip": client_ip,
                    "error_code": auth_result.error_code,
                    "error_message": auth_result.error_message
                })

            return {
                "type": "error",
                "error_code": auth_result.error_code or "auth_failed",
                "error_message": auth_result.error_message or "Authentication failed",
                "timestamp": datetime.now().isoformat()
            }
