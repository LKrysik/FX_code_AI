"""
State Machine Broadcaster
=========================
Broadcasts state machine events to subscribed WebSocket clients.

Supports:
- state_change: Strategy state transitions
- instance_added: New strategy instance started
- instance_removed: Strategy instance stopped
- full_update: Initial state on subscription

Part of BUG-007 fix: ADR-002 Backend Must Broadcast State Machine Events
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ...subscription_manager import SubscriptionManager
    from ...connection_manager import ConnectionManager
    from ....core.event_bus import EventBus

try:
    from ....core.logger import StructuredLogger, get_logger
except ImportError:
    from src.core.logger import StructuredLogger, get_logger


class StateMachineBroadcaster:
    """
    Broadcasts state machine events to clients subscribed to 'state_machines' stream.

    Usage:
        broadcaster = StateMachineBroadcaster(subscription_manager, connection_manager)
        await broadcaster.broadcast_state_change(session_id, {"state": "ACTIVE", ...})
    """

    STREAM_TYPE = "state_machines"

    def __init__(
        self,
        subscription_manager: "SubscriptionManager",
        connection_manager: "ConnectionManager",
        event_bus: Optional["EventBus"] = None,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize StateMachineBroadcaster.

        Args:
            subscription_manager: Manages client subscriptions
            connection_manager: Manages WebSocket connections and message sending
            event_bus: Optional EventBus for subscribing to session events
            logger: Optional structured logger instance
        """
        self.subscription_manager = subscription_manager
        self.connection_manager = connection_manager
        self.event_bus = event_bus
        self.logger = logger or get_logger(__name__)

        # Metrics
        self.total_broadcasts = 0
        self.total_messages_sent = 0
        self.total_failures = 0

        # Event subscription tracking
        self._is_running = False

    async def broadcast_state_change(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> int:
        """
        Broadcast state change event when strategy state transitions.

        Args:
            session_id: Trading session ID
            data: State change data (e.g., {"state": "ACTIVE", "previous_state": "IDLE"})

        Returns:
            Number of clients message was sent to
        """
        message = self._create_message("state_change", session_id, data)
        return await self._broadcast(message)

    async def broadcast_instance_added(
        self,
        session_id: str,
        instance_data: Dict[str, Any]
    ) -> int:
        """
        Broadcast when a new strategy instance is started.

        Args:
            session_id: Trading session ID
            instance_data: Instance info (e.g., {"instance_id": "...", "strategy_name": "..."})

        Returns:
            Number of clients message was sent to
        """
        message = self._create_message("instance_added", session_id, instance_data)
        return await self._broadcast(message)

    async def broadcast_instance_removed(
        self,
        session_id: str,
        instance_id: str
    ) -> int:
        """
        Broadcast when a strategy instance is stopped.

        Args:
            session_id: Trading session ID
            instance_id: ID of the removed instance

        Returns:
            Number of clients message was sent to
        """
        data = {"instance_id": instance_id}
        message = self._create_message("instance_removed", session_id, data)
        return await self._broadcast(message)

    async def broadcast_full_update(
        self,
        client_id: str,
        session_id: str,
        instances: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send full state update to a specific client (on subscription).

        Args:
            client_id: Target client ID
            session_id: Trading session ID
            instances: List of all active instances

        Returns:
            True if sent successfully, False otherwise
        """
        data = {
            "instances": instances or [],
            "session_id": session_id
        }
        message = self._create_message("full_update", session_id, data)

        success = await self.connection_manager.send_to_client(client_id, message)

        if success:
            self.total_messages_sent += 1
            self.logger.info("state_machine_broadcaster.full_update_sent", {
                "client_id": client_id,
                "session_id": session_id,
                "instance_count": len(instances) if instances else 0
            })
        else:
            self.total_failures += 1
            self.logger.warning("state_machine_broadcaster.full_update_failed", {
                "client_id": client_id,
                "session_id": session_id
            })

        return success

    def _create_message(
        self,
        message_type: str,
        session_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a properly formatted broadcast message.

        Args:
            message_type: Type of message (state_change, instance_added, etc.)
            session_id: Trading session ID
            data: Message payload

        Returns:
            Formatted message dictionary
        """
        return {
            "type": message_type,
            "stream": self.STREAM_TYPE,
            "session_id": session_id,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

    async def _broadcast(self, message: Dict[str, Any]) -> int:
        """
        Broadcast message to all subscribed clients.

        Args:
            message: Message to broadcast

        Returns:
            Number of clients message was sent to
        """
        self.total_broadcasts += 1

        # Get all clients subscribed to state_machines stream
        subscribers = self.subscription_manager.get_subscribers(self.STREAM_TYPE)

        if not subscribers:
            self.logger.debug("state_machine_broadcaster.no_subscribers", {
                "message_type": message.get("type"),
                "session_id": message.get("session_id")
            })
            return 0

        sent_count = 0
        failed_count = 0

        for client_id in subscribers:
            try:
                success = await self.connection_manager.send_to_client(client_id, message)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                self.logger.error("state_machine_broadcaster.send_error", {
                    "client_id": client_id,
                    "error": str(e)
                })

        self.total_messages_sent += sent_count
        self.total_failures += failed_count

        self.logger.info("state_machine_broadcaster.broadcast_complete", {
            "message_type": message.get("type"),
            "session_id": message.get("session_id"),
            "subscribers": len(subscribers),
            "sent": sent_count,
            "failed": failed_count
        })

        return sent_count

    def get_stats(self) -> Dict[str, Any]:
        """Get broadcaster statistics."""
        return {
            "total_broadcasts": self.total_broadcasts,
            "total_messages_sent": self.total_messages_sent,
            "total_failures": self.total_failures,
            "success_rate": (
                self.total_messages_sent / max(self.total_messages_sent + self.total_failures, 1)
            ),
            "is_running": self._is_running
        }

    # =========================================================================
    # Event Bus Integration (AC: 2, 3, 4)
    # =========================================================================

    async def start(self) -> None:
        """
        Start the broadcaster by subscribing to session events.

        Subscribes to:
        - session.started: Broadcasts instance_added
        - session.stopped: Broadcasts instance_removed
        """
        if self._is_running:
            self.logger.warning("state_machine_broadcaster.already_running")
            return

        if not self.event_bus:
            self.logger.warning("state_machine_broadcaster.no_event_bus", {
                "message": "Event bus not provided, broadcaster will only work with manual calls"
            })
            return

        # Subscribe to session events
        await self.event_bus.subscribe("session.started", self._on_session_started)
        await self.event_bus.subscribe("session.stopped", self._on_session_stopped)

        self._is_running = True
        self.logger.info("state_machine_broadcaster.started", {
            "subscribed_topics": ["session.started", "session.stopped"]
        })

    async def stop(self) -> None:
        """
        Stop the broadcaster by unsubscribing from events.
        """
        if not self._is_running:
            return

        if self.event_bus:
            await self.event_bus.unsubscribe("session.started", self._on_session_started)
            await self.event_bus.unsubscribe("session.stopped", self._on_session_stopped)

        self._is_running = False
        self.logger.info("state_machine_broadcaster.stopped", {
            "stats": self.get_stats()
        })

    async def _on_session_started(self, data: Dict[str, Any]) -> None:
        """
        Handle session.started event from EventBus.

        Broadcasts instance_added to all state_machines subscribers.

        Args:
            data: Session data from event (contains session_id, symbols, mode, etc.)
        """
        session_id = data.get("session_id")
        if not session_id:
            self.logger.warning("state_machine_broadcaster.session_started_missing_id", {
                "data_keys": list(data.keys())
            })
            return

        instance_data = {
            "instance_id": session_id,
            "session_id": session_id,
            "symbols": data.get("symbols", []),
            "mode": data.get("mode", "unknown"),
            "state": data.get("state", "ACTIVE"),
            "start_time": data.get("start_time"),
            "client_id": data.get("client_id")
        }

        sent_count = await self.broadcast_instance_added(session_id, instance_data)
        self.logger.info("state_machine_broadcaster.session_started_broadcast", {
            "session_id": session_id,
            "sent_to_clients": sent_count
        })

    async def _on_session_stopped(self, data: Dict[str, Any]) -> None:
        """
        Handle session.stopped event from EventBus.

        Broadcasts instance_removed to all state_machines subscribers.

        Args:
            data: Session data from event (contains session_id)
        """
        session_id = data.get("session_id")
        if not session_id:
            self.logger.warning("state_machine_broadcaster.session_stopped_missing_id", {
                "data_keys": list(data.keys())
            })
            return

        sent_count = await self.broadcast_instance_removed(session_id, session_id)
        self.logger.info("state_machine_broadcaster.session_stopped_broadcast", {
            "session_id": session_id,
            "sent_to_clients": sent_count
        })
