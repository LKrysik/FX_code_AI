"""
Client Utilities
================
Helper functions for extracting client information from WebSocket connections.

Why this exists:
- Consolidates IP extraction logic used in 10+ places
- Provides defensive programming for various WebSocket implementations
- Single place to handle different WebSocket library interfaces
- Easier testing with mocked WebSocket objects

Extracted from websocket_server.py lines 2861-2904
"""

from typing import Dict, Any, Optional


class ClientUtils:
    """
    Utility functions for client information extraction.

    Handles:
    - IP address extraction from WebSocket connections
    - Connection metadata building
    - Defensive handling of different WebSocket implementations

    All methods are static - no state needed.
    """

    @staticmethod
    def get_client_ip(websocket, logger=None) -> str:
        """
        Extract client IP address from WebSocket connection.

        Handles multiple WebSocket implementations:
        - websockets library (remote_address tuple)
        - FastAPI WebSocket (client.host)
        - Other implementations with connection.remote_address

        EXTRACTED FROM websocket_server.py lines 2861-2899

        Args:
            websocket: WebSocket connection object
            logger: Optional logger for debugging

        Returns:
            Client IP address string, or "127.0.0.1" as fallback

        Example:
            >>> from unittest.mock import Mock
            >>> mock_ws = Mock()
            >>> mock_ws.remote_address = ("192.168.1.1", 8080)
            >>> ClientUtils.get_client_ip(mock_ws)
            '192.168.1.1'
        """
        try:
            # For websockets library, try to get remote address
            if hasattr(websocket, 'remote_address') and websocket.remote_address:
                # remote_address is typically a tuple (host, port)
                if isinstance(websocket.remote_address, tuple):
                    return websocket.remote_address[0]
                return str(websocket.remote_address)

            # For FastAPI WebSocket, try client.host
            if hasattr(websocket, 'client') and websocket.client:
                if hasattr(websocket.client, 'host'):
                    return websocket.client.host

            # Try to get from connection if available
            if hasattr(websocket, 'connection'):
                conn = websocket.connection
                if hasattr(conn, 'remote_address') and conn.remote_address:
                    if isinstance(conn.remote_address, tuple):
                        return conn.remote_address[0]
                    return str(conn.remote_address)

        except (AttributeError, TypeError) as e:
            # Expected errors when WebSocket object doesn't have expected attributes
            if logger:
                logger.debug("client_utils.ip_extraction_attribute_error", {
                    "error": str(e),
                    "websocket_type": type(websocket).__name__
                })
        except Exception as e:
            # Unexpected error during IP extraction
            if logger:
                logger.warning("client_utils.ip_extraction_unexpected_error", {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "websocket_type": type(websocket).__name__
                })

        # Default fallback - log this as it might indicate configuration issues
        default_ip = "127.0.0.1"
        if logger:
            logger.debug("client_utils.using_default_ip", {
                "default_ip": default_ip,
                "reason": "Could not extract IP from WebSocket connection"
            })
        return default_ip

    @staticmethod
    async def get_client_ip_by_id(
        client_id: str,
        connection_manager,
        logger=None
    ) -> str:
        """
        Get client IP address by client ID.

        Looks up connection in connection manager and extracts IP.

        EXTRACTED FROM websocket_server.py lines 2901-2904

        Args:
            client_id: The client ID to look up
            connection_manager: ConnectionManager instance
            logger: Optional logger

        Returns:
            Client IP address string, or "unknown" if not found

        Example:
            >>> from unittest.mock import Mock, AsyncMock
            >>> mock_mgr = Mock()
            >>> mock_conn = Mock(ip_address="10.0.0.1")
            >>> mock_mgr.get_connection = AsyncMock(return_value=mock_conn)
            >>> import asyncio
            >>> ip = asyncio.run(ClientUtils.get_client_ip_by_id("client1", mock_mgr))
            >>> print(ip)
            '10.0.0.1'
        """
        try:
            connection = await connection_manager.get_connection(client_id)
            if connection:
                # Try different ways to get IP
                if hasattr(connection, 'ip_address'):
                    return connection.ip_address
                if hasattr(connection, 'metadata') and isinstance(connection.metadata, dict):
                    return connection.metadata.get("ip_address", "unknown")
            return "unknown"
        except Exception as e:
            if logger:
                logger.debug("client_utils.get_ip_by_id_error", {
                    "client_id": client_id,
                    "error": str(e)
                })
            return "unknown"

    @staticmethod
    def build_connection_metadata(
        websocket,
        client_ip: str,
        logger=None
    ) -> Dict[str, str]:
        """
        Build connection metadata dictionary.

        Extracts user agent and other metadata from WebSocket connection.

        REFACTORED FROM websocket_server.py lines 735-739

        Args:
            websocket: WebSocket connection object
            client_ip: Already extracted client IP
            logger: Optional logger

        Returns:
            Metadata dictionary with ip_address, user_agent, path

        Example:
            >>> mock_ws = Mock()
            >>> mock_ws.request_headers = {"User-Agent": "Mozilla/5.0"}
            >>> meta = ClientUtils.build_connection_metadata(mock_ws, "192.168.1.1")
            >>> meta["ip_address"]
            '192.168.1.1'
            >>> meta["user_agent"]
            'Mozilla/5.0'
        """
        user_agent = "unknown"
        path = ""

        try:
            # Try to get user agent from request headers
            if hasattr(websocket, 'request_headers'):
                headers = websocket.request_headers
                if isinstance(headers, dict):
                    user_agent = headers.get("User-Agent", "unknown")
                elif hasattr(headers, 'get'):
                    user_agent = headers.get("User-Agent", "unknown")

            # Try to get path
            if hasattr(websocket, 'path'):
                path = websocket.path or ""
            elif hasattr(websocket, 'scope') and isinstance(websocket.scope, dict):
                path = websocket.scope.get('path', "")

        except (AttributeError, TypeError) as e:
            # Expected errors when WebSocket object doesn't have expected attributes
            if logger:
                logger.debug("client_utils.metadata_extraction_error", {
                    "error": str(e),
                    "websocket_type": type(websocket).__name__
                })
        except Exception as e:
            # Unexpected error during metadata extraction
            if logger:
                logger.warning("client_utils.metadata_extraction_unexpected_error", {
                    "error": str(e),
                    "error_type": type(e).__name__
                })

        return {
            "ip_address": client_ip,
            "user_agent": user_agent,
            "path": path
        }

    @staticmethod
    def extract_reconnect_token(websocket, logger=None) -> Optional[str]:
        """
        Extract reconnect token from WebSocket headers.

        Used for client reconnection support.

        Args:
            websocket: WebSocket connection object
            logger: Optional logger

        Returns:
            Reconnect token string or None

        Example:
            >>> mock_ws = Mock()
            >>> mock_ws.request_headers = {"X-Reconnect-Token": "client123:abc..."}
            >>> ClientUtils.extract_reconnect_token(mock_ws)
            'client123:abc...'
        """
        try:
            if hasattr(websocket, 'request_headers'):
                headers = websocket.request_headers
                if isinstance(headers, dict):
                    return headers.get("X-Reconnect-Token")
                elif hasattr(headers, 'get'):
                    return headers.get("X-Reconnect-Token")

            # Try FastAPI style
            if hasattr(websocket, 'headers'):
                return websocket.headers.get("X-Reconnect-Token")

        except Exception as e:
            if logger:
                logger.debug("client_utils.token_extraction_error", {
                    "error": str(e)
                })

        return None
