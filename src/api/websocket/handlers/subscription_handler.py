"""
SubscriptionMessageHandler - WebSocket Subscription Management
==============================================================
Handles subscription and unsubscription to data streams.

Responsibilities:
- Subscribe clients to streams (market_data, indicators, signals, etc.)
- Unsubscribe clients from streams
- Validate authentication before subscriptions
- Trigger initial data seeding for new subscriptions
- Track subscription confirmations

Extracted from WebSocketAPIServer (lines 1253-1323)
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable


class SubscriptionMessageHandler:
    """
    Handles WebSocket subscription and unsubscription messages.

    Subscription flow:
    1. Client sends SUBSCRIBE message with stream type
    2. Handler checks authentication
    3. SubscriptionManager registers subscription
    4. Handler confirms subscription
    5. Optional: Seed initial data to client

    Dependencies:
    - subscription_manager: For subscription tracking
    - connection_manager: For authentication checks
    - controller: For session context (optional)
    - stream_seeder: For initial data seeding (optional)
    """

    def __init__(self,
                 subscription_manager,
                 connection_manager,
                 controller = None,
                 stream_seeder: Optional[Callable[[str, str, Dict[str, Any]], Awaitable[None]]] = None,
                 logger = None):
        """
        Initialize subscription handler.

        Args:
            subscription_manager: SubscriptionManager for tracking subscriptions
            connection_manager: ConnectionManager for authentication
            controller: Optional trading controller for session context
            stream_seeder: Optional async callable(client_id, stream, params) for data seeding
            logger: Optional logger for diagnostics
        """
        self.subscription_manager = subscription_manager
        self.connection_manager = connection_manager
        self.controller = controller
        self.stream_seeder = stream_seeder
        self.logger = logger

    async def handle_subscribe(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle subscription message.

        Message format:
        {
            "type": "subscribe",
            "stream": "market_data",
            "params": {"symbols": ["BTC_USDT"]}
        }

        Success response:
        {
            "type": "response",
            "status": "subscribed",
            "stream": "market_data",
            "params": {"symbols": ["BTC_USDT"]},
            "session_id": "session_123",  // if available
            "timestamp": "2025-11-03T11:00:00"
        }

        Error response:
        {
            "type": "error",
            "error_code": "authentication_required",
            "error_message": "Authentication required for subscriptions",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Subscription message with stream and params

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:1253-1302 (handle_subscribe nested function)
        """
        subscription_type = message.get("stream", "")
        params = message.get("params", {})

        # Check authentication requirement
        connection = await self.connection_manager.get_connection(client_id)
        if not getattr(connection, 'authenticated', False):
            return {
                "type": "error",
                "error_code": "authentication_required",
                "error_message": "Authentication required for subscriptions",
                "timestamp": datetime.now().isoformat()
            }

        # Register subscription
        success = await self.subscription_manager.subscribe_client(
            client_id, subscription_type, params
        )

        if success:
            # Get session context if available
            current_session_id = None
            try:
                if self.controller:
                    current = self.controller.get_execution_status()
                    if isinstance(current, dict) and current.get("session_id"):
                        current_session_id = current.get("session_id")
            except Exception:
                # Controller may not be initialized
                pass

            # Build success response
            response = {
                "type": "response",
                "status": "subscribed",
                "stream": subscription_type,
                "params": params,
                "session_id": current_session_id,
                "timestamp": datetime.now().isoformat()
            }

            # Confirm subscription after response is constructed
            try:
                self.subscription_manager.confirm_subscription(client_id, subscription_type)
            except Exception:
                # Confirmation failure is non-critical
                pass

            # Seed initial data asynchronously (non-blocking)
            if self.stream_seeder:
                try:
                    asyncio.create_task(
                        self.stream_seeder(client_id, subscription_type, params)
                    )
                except Exception:
                    # Seeding failure is non-critical
                    pass

            return response
        else:
            return {
                "type": "error",
                "error_code": "subscription_failed",
                "error_message": "Failed to create subscription",
                "timestamp": datetime.now().isoformat()
            }

    async def handle_unsubscribe(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle unsubscription message.

        Message format:
        {
            "type": "unsubscribe",
            "stream": "market_data"
        }

        Success response:
        {
            "type": "response",
            "status": "unsubscribed",
            "stream": "market_data",
            "timestamp": "2025-11-03T11:00:00"
        }

        Error response:
        {
            "type": "error",
            "error_code": "unsubscription_failed",
            "error_message": "Failed to remove subscription",
            "timestamp": "2025-11-03T11:00:00"
        }

        Args:
            client_id: Unique client identifier
            message: Unsubscription message with stream

        Returns:
            Response dict (success or error)

        Original location: websocket_server.py:1305-1323 (handle_unsubscribe nested function)
        """
        subscription_type = message.get("stream", "")

        # Remove subscription
        success = await self.subscription_manager.unsubscribe_client(
            client_id, subscription_type
        )

        if success:
            return {
                "type": "response",
                "status": "unsubscribed",
                "stream": subscription_type,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "type": "error",
                "error_code": "unsubscription_failed",
                "error_message": "Failed to remove subscription",
                "timestamp": datetime.now().isoformat()
            }
