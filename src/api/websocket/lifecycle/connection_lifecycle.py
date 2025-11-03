"""
ConnectionLifecycle - WebSocket Connection Management
=====================================================
Orchestrates WebSocket connection lifecycle: accept, message handling, disconnect.

Responsibilities:
- Accept new connections with metadata
- Handle reconnection with session restoration
- Send welcome messages
- Process incoming messages (rate limiting, parsing, routing)
- Send responses to clients
- Cleanup on disconnect with session preservation

This is an orchestrator that coordinates:
- ConnectionManager (connection tracking)
- SessionStore (session persistence for reconnect)
- MessageRouter (message routing to handlers)
- RateLimiter (rate limiting)
- Sanitizer (input validation)

Extracted from WebSocketAPIServer (lines 682-1070+)
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

# Try to import WebSocketDisconnect from FastAPI/Starlette
try:
    from starlette.websockets import WebSocketDisconnect
except ImportError:
    # Define a placeholder if not available
    class WebSocketDisconnect(Exception):
        """Placeholder for WebSocketDisconnect when starlette not available"""
        pass


class ConnectionLifecycle:
    """
    Orchestrates WebSocket connection lifecycle.

    Lifecycle stages:
    1. Accept connection → metadata extraction → reconnect detection
    2. Restore session or create new → welcome message
    3. Message loop → rate limit → parse → sanitize → route → respond
    4. Disconnect → save session → cleanup

    Dependencies:
    - connection_manager: Connection tracking and management
    - session_store: Session persistence for reconnection
    - message_router: Routes messages to appropriate handlers
    - rate_limiter: Rate limiting enforcement
    - json_executor: Thread pool for async JSON parsing
    - logger: Diagnostics logging
    """

    def __init__(self,
                 connection_manager,
                 session_store,
                 message_router,
                 rate_limiter,
                 subscription_manager,
                 json_executor = None,
                 logger = None):
        """
        Initialize connection lifecycle orchestrator.

        Args:
            connection_manager: ConnectionManager for connection tracking
            session_store: SessionStore for session persistence
            message_router: MessageRouter for message routing
            rate_limiter: RateLimiter for rate limiting
            subscription_manager: SubscriptionManager for subscription tracking
            json_executor: ThreadPoolExecutor for async JSON parsing (optional)
            logger: Optional logger for diagnostics
        """
        self.connection_manager = connection_manager
        self.session_store = session_store
        self.message_router = message_router
        self.rate_limiter = rate_limiter
        self.subscription_manager = subscription_manager
        self.json_executor = json_executor
        self.logger = logger

        # Statistics
        self.total_connections_handled = 0
        self.total_messages_processed = 0

    def _extract_client_ip(self, websocket: Any) -> str:
        """
        Extract client IP from WebSocket connection.

        Handles both websockets library and FastAPI WebSocket.

        Args:
            websocket: WebSocket connection object

        Returns:
            Client IP address string

        Original location: websocket_server.py:2861-2899 (_get_client_ip)
        Note: Uses ClientUtils internally in actual implementation
        """
        try:
            # websockets library
            if hasattr(websocket, 'remote_address') and websocket.remote_address:
                if isinstance(websocket.remote_address, tuple):
                    return websocket.remote_address[0]

            # FastAPI WebSocket
            if hasattr(websocket, 'client') and websocket.client:
                if hasattr(websocket.client, 'host'):
                    return websocket.client.host

            # Connection attribute
            if hasattr(websocket, 'connection'):
                conn = websocket.connection
                if hasattr(conn, 'remote_address') and conn.remote_address:
                    if isinstance(conn.remote_address, tuple):
                        return conn.remote_address[0]

        except Exception:
            pass

        return "127.0.0.1"  # Fallback

    def _extract_user_agent(self, websocket: Any) -> str:
        """
        Safely extract User-Agent from WebSocket connection.

        Args:
            websocket: WebSocket connection object

        Returns:
            User-Agent string or "unknown"

        Original location: websocket_server.py:716-733
        """
        try:
            if hasattr(websocket, 'request_headers'):
                return websocket.request_headers.get("User-Agent", "unknown")
        except Exception:
            pass

        return "unknown"

    def _build_connection_metadata(self, websocket: Any, client_ip: str) -> Dict[str, str]:
        """
        Build connection metadata.

        Args:
            websocket: WebSocket connection object
            client_ip: Client IP address

        Returns:
            Metadata dict with ip_address, user_agent, path

        Original location: websocket_server.py:735-739
        """
        return {
            "ip_address": client_ip,
            "user_agent": self._extract_user_agent(websocket),
            "path": ""  # Path not available in websockets library
        }

    async def handle_client_connection(self, websocket: Any, is_fastapi_websocket: bool = False):
        """
        Handle new WebSocket client connection with reconnect support.

        Connection flow:
        1. Extract client IP and metadata
        2. Check for reconnection (future enhancement)
        3. Add connection to manager or restore
        4. Generate reconnect token
        5. Send welcome message
        6. Handle client messages
        7. On disconnect: save session, cleanup

        Args:
            websocket: WebSocket connection object
            is_fastapi_websocket: True if FastAPI WebSocket, False for websockets library

        Original location: websocket_server.py:682-867 (_handle_client_connection)

        Note: Reconnect logic currently basic - can be enhanced with token validation
        """
        client_id = None
        client_ip = self._extract_client_ip(websocket)
        metadata = self._build_connection_metadata(websocket, client_ip)

        if self.logger:
            self.logger.info("websocket_lifecycle.new_connection", {"client_ip": client_ip})

        try:
            # Add new connection (reconnect logic can be added here)
            client_id = await self.connection_manager.add_connection(
                websocket,
                metadata,
                is_fastapi_websocket=is_fastapi_websocket
            )

            if not client_id:
                # Connection rejected (limit reached)
                if is_fastapi_websocket:
                    await websocket.close(1013, "Server at capacity")
                else:
                    await websocket.close(1013, "Server at capacity")
                return

            self.total_connections_handled += 1

            # Generate reconnect token
            reconnect_token = self.session_store.generate_reconnect_token(client_id)

            if self.logger:
                self.logger.info("websocket_lifecycle.client_connected", {
                    "client_id": client_id,
                    "ip_address": client_ip,
                    "user_agent": metadata["user_agent"]
                })

            # Send welcome message
            welcome_message = {
                "type": "status",
                "status": "connected",
                "client_id": client_id,
                "reconnect_token": reconnect_token,
                "server_time": datetime.now().isoformat(),
                "features": ["reconnect", "heartbeat", "subscriptions"],
                "reconnected": False,  # Future enhancement
                "timestamp": datetime.now().isoformat()
            }
            await self._send_to_client(client_id, welcome_message)

            # Handle client messages
            await self._handle_client_messages(client_id, websocket, is_fastapi_websocket)

        except Exception as e:
            if self.logger:
                self.logger.error("websocket_lifecycle.unexpected_error", {
                    "client_id": client_id,
                    "ip_address": client_ip,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
        finally:
            # Cleanup connection with session preservation
            if client_id:
                await self._cleanup_connection(client_id, metadata)

    async def _handle_client_messages(self, client_id: str, websocket, is_fastapi_websocket: bool = False):
        """
        Handle messages from connected client.

        Message loop supports both FastAPI WebSocket and websockets library.

        Args:
            client_id: Unique client identifier
            websocket: WebSocket connection object
            is_fastapi_websocket: True if FastAPI WebSocket

        Original location: websocket_server.py:868-886 (_handle_client_messages)
        """
        client_ip = await self._get_client_ip_by_id(client_id)

        if is_fastapi_websocket:
            # FastAPI WebSocket handling
            try:
                while True:
                    message = await websocket.receive_text()
                    await self._process_message(client_id, client_ip, message)
            except WebSocketDisconnect:
                if self.logger:
                    self.logger.info("websocket_lifecycle.client_disconnected", {
                        "client_id": client_id,
                        "client_ip": client_ip
                    })
        else:
            # websockets library handling
            async for message in websocket:
                await self._process_message(client_id, client_ip, message)

    async def _process_message(self, client_id: str, client_ip: str, message: str):
        """
        Process a single WebSocket message.

        Processing steps:
        1. Rate limit check
        2. Async JSON parsing (prevent event loop blocking)
        3. Input sanitization (security)
        4. Route message to appropriate handler
        5. Send response
        6. Record activity

        Args:
            client_id: Unique client identifier
            client_ip: Client IP address
            message: Raw message string

        Original location: websocket_server.py:888-1023 (_process_message)
        """
        try:
            # Rate limit check
            if not self.rate_limiter.check_message_limit(client_ip):
                if self.logger:
                    self.logger.warning("websocket_lifecycle.rate_limited", {
                        "client_id": client_id,
                        "client_ip": client_ip
                    })
                error_response = {
                    "type": "error",
                    "error_code": "rate_limit_exceeded",
                    "error_message": "Message rate limit exceeded. Please slow down your requests.",
                    "timestamp": datetime.now().isoformat()
                }
                await self._send_to_client(client_id, error_response)
                return

            # Async JSON parsing
            try:
                if self.json_executor:
                    parsed = await asyncio.get_event_loop().run_in_executor(
                        self.json_executor, json.loads, message
                    )
                else:
                    parsed = json.loads(message)

                # Input sanitization
                from src.infrastructure.security import sanitizer
                try:
                    parsed = sanitizer.sanitize_websocket_message(parsed)
                except ValueError as e:
                    if self.logger:
                        self.logger.warning("websocket_lifecycle.sanitization_failed", {
                            "client_id": client_id,
                            "error": str(e)
                        })
                    error_response = {
                        "type": "error",
                        "error_code": "invalid_input",
                        "error_message": f"Input validation failed: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
                    await self._send_to_client(client_id, error_response)
                    return

                # Store request ID for response enrichment
                req_id = parsed.get("id") if isinstance(parsed, dict) else None
                if req_id:
                    connection = await self.connection_manager.get_connection(client_id)
                    if connection:
                        setattr(connection, 'last_request_id', req_id)
                        setattr(connection, 'in_flight_response', True)

            except json.JSONDecodeError as e:
                if self.logger:
                    self.logger.warning("websocket_lifecycle.json_parse_error", {
                        "client_id": client_id,
                        "error": str(e)
                    })
                error_response = {
                    "type": "error",
                    "error_code": "invalid_json",
                    "error_message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }
                await self._send_to_client(client_id, error_response)
                return

            # Route message to appropriate handler
            response = await self.message_router.route_message(client_id, parsed)

            if response:
                await self._send_to_client(client_id, response)

            # Clear in-flight flag
            try:
                connection = await self.connection_manager.get_connection(client_id)
                if connection and hasattr(connection, 'in_flight_response'):
                    setattr(connection, 'in_flight_response', False)
            except Exception:
                pass

            # Record message activity
            await self.connection_manager.record_message_activity(client_id, "received", len(message))

            self.total_messages_processed += 1

        except Exception as e:
            # Send error response if possible
            try:
                error_response = {
                    "type": "error",
                    "error_code": "message_processing_error",
                    "error_message": f"Failed to process message: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
                await self._send_to_client(client_id, error_response)
            except Exception:
                pass

            if self.logger:
                self.logger.error("websocket_lifecycle.message_processing_error", {
                    "client_id": client_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

    async def _send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to specific client with envelope enrichment.

        Args:
            client_id: Unique client identifier
            message: Message dict to send

        Returns:
            True if sent successfully, False otherwise

        Original location: websocket_server.py:1025-1070 (_send_to_client)
        """
        try:
            # Extract request ID from connection for response enrichment
            request_id = None
            try:
                connection = await self.connection_manager.get_connection(client_id)
                if connection and hasattr(connection, 'last_request_id'):
                    request_id = getattr(connection, 'last_request_id')
            except Exception:
                pass

            # Enrich message with envelope
            from src.api.protocol import ensure_envelope
            enriched = ensure_envelope(message, request_id=request_id)

            # Send via connection manager
            success = await self.connection_manager.send_to_client(client_id, enriched)

            if success:
                # Record message size for bandwidth tracking
                message_size = len(json.dumps(enriched).encode('utf-8'))
                await self.connection_manager.record_message_activity(client_id, "sent", message_size)

            return success

        except Exception as e:
            if self.logger:
                self.logger.error("websocket_lifecycle.send_error", {
                    "client_id": client_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
            return False

    async def _cleanup_connection(self, client_id: str, metadata: Dict[str, str]):
        """
        Cleanup connection on disconnect with session preservation.

        Preserves session state for potential reconnection.

        Args:
            client_id: Unique client identifier
            metadata: Connection metadata

        Original location: websocket_server.py:841-867 (finally block)
        """
        try:
            # Save session state before cleanup
            connection = await self.connection_manager.get_connection(client_id)
            if connection:
                session_data = {
                    "client_ip": metadata.get("ip_address", "unknown"),
                    "user_agent": metadata.get("user_agent", "unknown"),
                    "authenticated": getattr(connection, 'authenticated', False),
                    "user_id": getattr(connection, 'user_id', None),
                    "permissions": getattr(connection, 'permissions', []),
                    "subscriptions": list(self.subscription_manager.get_client_subscriptions(client_id).keys()),
                    "last_seen": datetime.now().isoformat()
                }
                self.session_store.save_session(client_id, session_data)

        except Exception as e:
            if self.logger:
                self.logger.debug("websocket_lifecycle.session_save_error", {
                    "client_id": client_id,
                    "error": str(e)
                })

        # Remove connection but preserve session data
        await self.connection_manager.remove_connection(client_id, "disconnected")

    async def _get_client_ip_by_id(self, client_id: str) -> str:
        """
        Get client IP by client ID.

        Args:
            client_id: Unique client identifier

        Returns:
            Client IP address or "unknown"

        Original location: websocket_server.py:2901-2904 (_get_client_ip_by_id)
        """
        try:
            connection = await self.connection_manager.get_connection(client_id)
            if connection and hasattr(connection, 'ip_address'):
                return connection.ip_address
            if connection and hasattr(connection, 'metadata'):
                return connection.metadata.get("ip_address", "unknown")
        except Exception:
            pass

        return "unknown"

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection lifecycle statistics.

        Returns:
            Statistics dict with connection and message counts
        """
        return {
            "total_connections_handled": self.total_connections_handled,
            "total_messages_processed": self.total_messages_processed
        }
