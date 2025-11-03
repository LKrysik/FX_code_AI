"""
ProtocolMessageHandler - WebSocket Protocol Operations
======================================================
Handles protocol-level operations: commands, heartbeats, and handshakes.

Responsibilities:
- Command execution (start_backtest, start_live_trading, etc.)
- Heartbeat/ping-pong for connection keepalive
- Protocol handshake for capability negotiation

Extracted from WebSocketAPIServer (lines 1326-1381, 1781-1883)
"""

from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable, List


class ProtocolMessageHandler:
    """
    Handles protocol-level WebSocket messages.

    Protocol operations:
    - COMMAND: Execute trading commands
    - HEARTBEAT: Update connection heartbeat (ping/pong)
    - HANDSHAKE: Validate protocol version and capabilities

    Dependencies:
    - connection_manager: For authentication and heartbeat updates
    - controller: For command execution context (optional)
    - command_executor: Async callable for executing commands (optional)
    - logger: For diagnostics and security logging
    """

    # Supported protocol version and capabilities
    PROTOCOL_VERSION = "1.0"
    SUPPORTED_CAPABILITIES = ['market_data', 'signals', 'commands', 'indicators']

    def __init__(self,
                 connection_manager,
                 controller = None,
                 command_executor: Optional[Callable[[str, Dict[str, Any]], Awaitable[Any]]] = None,
                 logger = None):
        """
        Initialize protocol handler.

        Args:
            connection_manager: ConnectionManager for heartbeat and metadata
            controller: Optional trading controller for service checks
            command_executor: Optional async callable(command, params) for command execution
            logger: Optional logger for diagnostics
        """
        self.connection_manager = connection_manager
        self.controller = controller
        self.command_executor = command_executor
        self.logger = logger

    async def handle_command(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle command execution message.

        Message format:
        {
            "type": "command",
            "action": "start_backtest",
            "params": {"symbols": ["BTC_USDT"], "acceleration": 10.0}
        }

        Success response:
        {
            "type": "response",
            "status": "success",
            "command": "start_backtest",
            "data": {...command result...},
            "timestamp": "2025-11-03T11:00:00"
        }

        Error response:
        {
            "type": "error",
            "error_code": "command_failed",
            "error_message": "Command execution error",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Command message with action and params

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:1326-1369 (handle_command nested function)
        """
        # Check controller availability
        if not self.controller:
            if self.logger:
                self.logger.error("websocket_protocol.command_failed", {
                    "client_id": client_id,
                    "reason": "Trading controller not initialized",
                    "message": message
                })
            return {
                "type": "error",
                "error_code": "service_unavailable",
                "error_message": "Trading controller not available",
                "timestamp": datetime.now().isoformat()
            }

        # Check authentication
        connection = await self.connection_manager.get_connection(client_id)
        if not getattr(connection, 'authenticated', False):
            return {
                "type": "error",
                "error_code": "authentication_required",
                "error_message": "Authentication required for commands",
                "timestamp": datetime.now().isoformat()
            }

        command = message.get("action", "")
        params = message.get("params", {})

        # Execute command via command_executor
        if not self.command_executor:
            return {
                "type": "error",
                "error_code": "command_executor_unavailable",
                "error_message": "Command executor not configured",
                "timestamp": datetime.now().isoformat()
            }

        try:
            result = await self.command_executor(command, params)
            return {
                "type": "response",
                "status": "success",
                "command": command,
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "type": "error",
                "error_code": "command_failed",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def handle_heartbeat(self, client_id: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle heartbeat (ping) message.

        Message format:
        {
            "type": "heartbeat"
        }

        Response:
        {
            "type": "status",
            "status": "pong",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Heartbeat message

        Returns:
            Pong response

        Original location: websocket_server.py:1372-1381 (handle_heartbeat nested function)
        """
        # Update heartbeat timestamp
        await self.connection_manager.update_heartbeat(client_id)

        # Send pong response
        return {
            "type": "status",
            "status": "pong",
            "timestamp": datetime.now().isoformat()
        }

    async def handle_handshake(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle WebSocket handshake - CRITICAL SECURITY FEATURE.

        Validates protocol version and client capabilities before allowing operations.

        Message format:
        {
            "type": "handshake",
            "version": "1.0",
            "client_id": "web_client_123",
            "capabilities": ["market_data", "signals"]
        }

        Success response:
        {
            "type": "handshake_ack",
            "status": "accepted",
            "server_version": "1.0",
            "server_capabilities": ["market_data", "signals", "commands", "indicators"],
            "session_id": "session_client_123_1234567890",
            "timestamp": "2025-11-03T11:00:00"
        }

        Rejection response:
        {
            "type": "handshake_ack",
            "status": "rejected",
            "reason": "Unsupported protocol version: 2.0. Expected: 1.0",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Handshake message with version and capabilities

        Returns:
            Handshake acknowledgment (accepted or rejected)

        Original location: websocket_server.py:1781-1883 (_handle_handshake method)

        Security features:
        - Prevents unauthorized connections
        - Validates protocol version compatibility
        - Establishes secure communication channel
        - Enables capability negotiation
        """
        try:
            # Validate required fields
            required_fields = ['version', 'client_id', 'capabilities']
            for field in required_fields:
                if field not in message:
                    return {
                        "type": "handshake_ack",
                        "status": "rejected",
                        "reason": f"Missing required field: {field}",
                        "timestamp": datetime.now().isoformat()
                    }

            client_version = message.get('version')
            client_capabilities = message.get('capabilities', [])
            client_id_from_msg = message.get('client_id')

            # Validate protocol version
            if client_version != self.PROTOCOL_VERSION:
                return {
                    "type": "handshake_ack",
                    "status": "rejected",
                    "reason": f"Unsupported protocol version: {client_version}. Expected: {self.PROTOCOL_VERSION}",
                    "timestamp": datetime.now().isoformat()
                }

            # Validate capabilities
            invalid_capabilities = [
                cap for cap in client_capabilities
                if cap not in self.SUPPORTED_CAPABILITIES
            ]

            if invalid_capabilities:
                return {
                    "type": "handshake_ack",
                    "status": "rejected",
                    "reason": f"Unsupported capabilities: {invalid_capabilities}",
                    "supported_capabilities": self.SUPPORTED_CAPABILITIES,
                    "timestamp": datetime.now().isoformat()
                }

            # Update connection metadata with handshake info
            connection = await self.connection_manager.get_connection(client_id)
            if connection:
                connection.__dict__.update({
                    'handshake_completed': True,
                    'protocol_version': client_version,
                    'client_capabilities': client_capabilities,
                    'client_id': client_id_from_msg,
                    'handshake_timestamp': datetime.now().isoformat()
                })

            # Log successful handshake
            if self.logger:
                self.logger.info("websocket_protocol.handshake_successful", {
                    "client_id": client_id,
                    "client_version": client_version,
                    "capabilities": client_capabilities,
                    "handshake_timestamp": datetime.now().isoformat()
                })

            # Return successful acknowledgment
            return {
                "type": "handshake_ack",
                "status": "accepted",
                "server_version": self.PROTOCOL_VERSION,
                "server_capabilities": self.SUPPORTED_CAPABILITIES,
                "session_id": f"session_{client_id}_{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            if self.logger:
                self.logger.error("websocket_protocol.handshake_error", {
                    "client_id": client_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

            return {
                "type": "handshake_ack",
                "status": "rejected",
                "reason": f"Handshake processing error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
