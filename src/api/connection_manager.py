"""
Connection Manager
=================
Manages WebSocket client connections with proper state tracking and cleanup.
Production-ready with memory leak prevention and performance monitoring.
"""

import asyncio
import json
import uuid
from typing import Dict, Set, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from collections import deque
import time
import psutil
import weakref
from websockets.exceptions import ConnectionClosed

try:
    # When imported as part of 'src' package
    from ..core.logger import StructuredLogger
except Exception:
    # Compatibility for tests importing as top-level 'api.connection_manager'
    from src.core.logger import StructuredLogger


@dataclass
class ClientConnection:
    """Client connection state tracking with memory-safe design"""

    client_id: str
    websocket: Any  # WebSocketServerProtocol
    connected_at: datetime
    last_heartbeat: float
    ip_address: str
    user_agent: str

    # Subscription state - using sets for O(1) lookups
    active_subscriptions: Set[str] = field(default_factory=set)
    subscription_filters: Dict[str, Any] = field(default_factory=dict)

    # Performance tracking
    messages_sent: int = 0
    messages_received: int = 0
    bandwidth_used: int = 0
    connection_duration: float = 0.0

    # Rate limiting - using deques for sliding window
    message_timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    subscription_timestamps: deque = field(default_factory=lambda: deque(maxlen=100))

    # Preferences
    preferred_format: str = "json"  # "json" | "binary"
    compression_enabled: bool = False
    batch_updates: bool = True

    # Connection health
    consecutive_errors: int = 0
    last_error_time: Optional[float] = None
    is_healthy: bool = True
    is_fastapi_websocket: bool = False  # Flag to distinguish WebSocket types

    def update_heartbeat(self):
        """Update last heartbeat timestamp"""
        self.last_heartbeat = time.time()

    def record_message_sent(self, size_bytes: int):
        """Record outbound message for rate limiting and stats"""
        now = time.time()
        self.message_timestamps.append(now)
        self.messages_sent += 1
        self.bandwidth_used += size_bytes

    def record_message_received(self):
        """Record inbound message for rate limiting and stats"""
        now = time.time()
        self.message_timestamps.append(now)
        self.messages_received += 1

    def record_subscription_attempt(self):
        """Record subscription attempt for rate limiting"""
        self.subscription_timestamps.append(time.time())

    def get_connection_age_seconds(self) -> float:
        """Get connection age in seconds"""
        return time.time() - self.connected_at.timestamp()

    def get_messages_per_minute(self) -> float:
        """Calculate messages per minute rate"""
        if not self.message_timestamps:
            return 0.0

        # Remove old timestamps (older than 1 minute)
        cutoff = time.time() - 60
        while self.message_timestamps and self.message_timestamps[0] < cutoff:
            self.message_timestamps.popleft()

        return len(self.message_timestamps)

    def get_subscriptions_per_hour(self) -> float:
        """Calculate subscriptions per hour rate"""
        if not self.subscription_timestamps:
            return 0.0

        # Remove old timestamps (older than 1 hour)
        cutoff = time.time() - 3600
        while self.subscription_timestamps and self.subscription_timestamps[0] < cutoff:
            self.subscription_timestamps.popleft()

        return len(self.subscription_timestamps)

    def is_rate_limited(self, max_messages_per_minute: int = 100, max_subscriptions_per_hour: int = 50) -> bool:
        """Check if connection is rate limited"""
        return (self.get_messages_per_minute() >= max_messages_per_minute or
                self.get_subscriptions_per_hour() >= max_subscriptions_per_hour)

    def record_error(self):
        """Record connection error for health monitoring"""
        self.consecutive_errors += 1
        self.last_error_time = time.time()
        if self.consecutive_errors >= 5:  # Threshold for unhealthy
            self.is_healthy = False

    def reset_error_count(self):
        """Reset error count on successful operation"""
        self.consecutive_errors = 0
        self.is_healthy = True


class ConnectionManager:
    """
    Manages all WebSocket client connections with production safeguards.

    Features:
    - Memory-safe connection tracking with weak references
    - Automatic cleanup of dead connections
    - Rate limiting and abuse prevention
    - Performance monitoring and metrics
    - Graceful degradation under load
    """

    def __init__(self,
                 max_connections: int = 1000,
                 heartbeat_timeout_seconds: int = 60,
                 cleanup_interval_seconds: int = 30,
                 max_messages_per_minute: int = 100,
                 max_subscriptions_per_hour: int = 50):
        """
        Initialize ConnectionManager with production settings.

        Args:
            max_connections: Maximum concurrent connections
            heartbeat_timeout_seconds: Connection timeout without heartbeat
            cleanup_interval_seconds: Interval for cleanup operations
            max_messages_per_minute: Rate limit for messages per client
            max_subscriptions_per_hour: Rate limit for subscriptions per client
        """
        self.max_connections = max_connections
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.max_messages_per_minute = max_messages_per_minute
        self.max_subscriptions_per_hour = max_subscriptions_per_hour

        # ✅ CRITICAL FIX: Memory-safe connection storage with atomic operations
        self._connections: Dict[str, ClientConnection] = {}
        self._connection_lock = asyncio.Lock()  # Protects all connection operations

        # Subscription tracking for efficient broadcasting
        self._subscription_clients: Dict[str, Set[str]] = {}
        self._client_subscriptions: Dict[str, Set[str]] = {}

        # Cleanup and monitoring
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_shutting_down = False
        self._last_cleanup_time = time.time()

        # Performance metrics
        self.total_connections_accepted = 0
        self.total_connections_rejected = 0
        self.total_connections_dropped = 0
        self.peak_concurrent_connections = 0

        # Logger will be injected
        self.logger: Optional[StructuredLogger] = None

    def set_logger(self, logger: StructuredLogger):
        """Set logger instance"""
        self.logger = logger

    async def add_connection(self,
                           websocket: Any,
                           metadata: Dict[str, Any],
                           user_id: Optional[str] = None,
                           is_fastapi_websocket: bool = False) -> Optional[str]:
        """
        Add new client connection with validation and rate limiting.

        Args:
            websocket: WebSocket connection object
            metadata: Connection metadata (IP, user agent, etc.)
            user_id: Optional authenticated user ID
            is_fastapi_websocket: Flag indicating if it's a FastAPI WebSocket

        Returns:
            Client ID if connection accepted, None if rejected
        """
        # ✅ CRITICAL FIX: Atomic connection limit check and addition to prevent race conditions
        async with self._connection_lock:
            # Check connection limits atomically
            if len(self._connections) >= self.max_connections:
                self.total_connections_rejected += 1
                if self.logger:
                    self.logger.warning("connection_manager.connection_limit_reached", {
                        "current_connections": len(self._connections),
                        "max_connections": self.max_connections,
                        "rejected_ip": metadata.get("ip_address")
                    })
                return None

            # Generate unique client ID
            client_id = str(uuid.uuid4())

            # Create connection object
            connection = ClientConnection(
                client_id=client_id,
                websocket=websocket,
                connected_at=datetime.now(),
                last_heartbeat=time.time(),
                ip_address=metadata.get("ip_address", "unknown"),
                user_agent=metadata.get("user_agent", "unknown"),
                is_fastapi_websocket=is_fastapi_websocket
            )

            # ✅ CRITICAL FIX: Store connection atomically within the same lock
            self._connections[client_id] = connection
            self.total_connections_accepted += 1

            # Update peak connections
            current_count = len(self._connections)
            if current_count > self.peak_concurrent_connections:
                self.peak_concurrent_connections = current_count

            # Initialize subscription tracking
            self._client_subscriptions[client_id] = set()

            if self.logger:
                self.logger.info("connection_manager.connection_added", {
                    "client_id": client_id,
                    "ip_address": connection.ip_address,
                    "total_connections": current_count,
                    "user_id": user_id
                })

            # Start cleanup task if not running
            if not self._cleanup_task or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())

            return client_id

    async def restore_connection(self,
                                client_id: str,
                                websocket: Any,
                                metadata: Dict[str, Any],
                                is_fastapi_websocket: bool = False) -> bool:
        """
        Restore a previously saved connection for reconnection.

        Args:
            client_id: Existing client ID to restore
            websocket: New WebSocket connection object
            metadata: Updated connection metadata
            is_fastapi_websocket: Flag indicating if it's a FastAPI WebSocket

        Returns:
            True if connection restored successfully, False otherwise
        """
        async with self._connection_lock:
            # Check if client_id already exists (shouldn't for reconnect)
            if client_id in self._connections:
                if self.logger:
                    self.logger.warning("connection_manager.restore_connection_already_exists", {
                        "client_id": client_id
                    })
                return False

            # Check connection limits
            if len(self._connections) >= self.max_connections:
                self.total_connections_rejected += 1
                if self.logger:
                    self.logger.warning("connection_manager.restore_connection_limit_reached", {
                        "client_id": client_id,
                        "current_connections": len(self._connections),
                        "max_connections": self.max_connections
                    })
                return False

            # Create restored connection object
            connection = ClientConnection(
                client_id=client_id,
                websocket=websocket,
                connected_at=datetime.now(),
                last_heartbeat=time.time(),
                ip_address=metadata.get("ip_address", "unknown"),
                user_agent=metadata.get("user_agent", "unknown"),
                is_fastapi_websocket=is_fastapi_websocket
            )

            # Store connection
            self._connections[client_id] = connection
            self.total_connections_accepted += 1

            # Initialize subscription tracking (will be restored by caller)
            self._client_subscriptions[client_id] = set()

            # Update peak connections
            current_count = len(self._connections)
            if current_count > self.peak_concurrent_connections:
                self.peak_concurrent_connections = current_count

            if self.logger:
                self.logger.info("connection_manager.connection_restored", {
                    "client_id": client_id,
                    "ip_address": connection.ip_address,
                    "total_connections": current_count
                })

            return True

    async def remove_connection(self, client_id: str, reason: str = "normal"):
        """
        Remove client connection and perform cleanup.

        Args:
            client_id: Client ID to remove
            reason: Reason for removal (normal, timeout, error, etc.)
        """
        async with self._connection_lock:
            connection = self._connections.get(client_id)
            if not connection:
                return

            # Calculate connection duration
            connection.connection_duration = connection.get_connection_age_seconds()

            # Clean up subscriptions
            await self._cleanup_client_subscriptions(client_id)

            # Remove from main storage
            del self._connections[client_id]

            # Update metrics
            self.total_connections_dropped += 1

            if self.logger:
                self.logger.info("connection_manager.connection_removed", {
                    "client_id": client_id,
                    "reason": reason,
                    "duration_seconds": connection.connection_duration,
                    "messages_sent": connection.messages_sent,
                    "messages_received": connection.messages_received,
                    "bandwidth_used": connection.bandwidth_used,
                    "remaining_connections": len(self._connections)
                })

    async def _cleanup_client_subscriptions(self, client_id: str):
        """Clean up all subscriptions for a client"""
        if client_id not in self._client_subscriptions:
            return

        subscriptions = self._client_subscriptions[client_id].copy()
        for subscription_type in subscriptions:
            await self.unsubscribe_client(client_id, subscription_type)

        del self._client_subscriptions[client_id]

    async def get_connection(self, client_id: str) -> Optional[ClientConnection]:
        """Get client connection by ID"""
        async with self._connection_lock:
            return self._connections.get(client_id)

    async def update_heartbeat(self, client_id: str):
        """Update heartbeat timestamp for client"""
        connection = await self.get_connection(client_id)
        if connection:
            connection.update_heartbeat()

    async def record_message_activity(self, client_id: str, direction: str, size_bytes: int = 0):
        """Record message activity for monitoring"""
        connection = await self.get_connection(client_id)
        if not connection:
            return

        if direction == "sent":
            connection.record_message_sent(size_bytes)
        elif direction == "received":
            connection.record_message_received()

    async def subscribe_client(self,
                              client_id: str,
                              subscription_type: str,
                              filters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Subscribe client to data stream with thread-safe operations.

        Args:
            client_id: Client ID
            subscription_type: Type of data to subscribe to
            filters: Optional filters for the subscription

        Returns:
            True if subscription successful, False otherwise
        """
        connection = await self.get_connection(client_id)
        if not connection:
            return False

        # Check rate limiting
        if connection.is_rate_limited(self.max_messages_per_minute, self.max_subscriptions_per_hour):
            if self.logger:
                self.logger.warning("connection_manager.subscription_rate_limited", {
                    "client_id": client_id,
                    "subscription_type": subscription_type
                })
            return False

        # Record subscription attempt
        connection.record_subscription_attempt()

        # ✅ CRITICAL FIX: Atomic subscription operations to prevent race conditions
        async with self._connection_lock:
            # Double-check connection still exists (within lock)
            if client_id not in self._connections:
                return False

            # Add to client's subscriptions
            if client_id not in self._client_subscriptions:
                self._client_subscriptions[client_id] = set()
            self._client_subscriptions[client_id].add(subscription_type)

            # Add to subscription tracking
            if subscription_type not in self._subscription_clients:
                self._subscription_clients[subscription_type] = set()
            self._subscription_clients[subscription_type].add(client_id)

            # Update connection state
            connection.active_subscriptions.add(subscription_type)
            if filters:
                connection.subscription_filters[subscription_type] = filters

        if self.logger:
            self.logger.info("connection_manager.client_subscribed", {
                "client_id": client_id,
                "subscription_type": subscription_type,
                "total_subscribers": len(self._subscription_clients.get(subscription_type, set())),
                "filters": filters
            })

        return True

    async def unsubscribe_client(self, client_id: str, subscription_type: str) -> bool:
        """Unsubscribe client from data stream with thread-safe operations"""
        connection = await self.get_connection(client_id)
        if not connection:
            return False

        # ✅ CRITICAL FIX: Atomic unsubscription operations to prevent race conditions
        async with self._connection_lock:
            # Double-check connection still exists (within lock)
            if client_id not in self._connections:
                return False

            # Remove from client's subscriptions
            if client_id in self._client_subscriptions:
                self._client_subscriptions[client_id].discard(subscription_type)

            # Remove from subscription tracking
            if subscription_type in self._subscription_clients:
                self._subscription_clients[subscription_type].discard(client_id)
                if not self._subscription_clients[subscription_type]:
                    del self._subscription_clients[subscription_type]

            # Update connection state
            connection.active_subscriptions.discard(subscription_type)
            connection.subscription_filters.pop(subscription_type, None)

        if self.logger:
            self.logger.info("connection_manager.client_unsubscribed", {
                "client_id": client_id,
                "subscription_type": subscription_type,
                "remaining_subscribers": len(self._subscription_clients.get(subscription_type, set()))
            })

        return True

    async def get_subscribers(self, subscription_type: str) -> Set[str]:
        """Get all clients subscribed to specific type"""
        async with self._connection_lock:
            return self._subscription_clients.get(subscription_type, set()).copy()

    async def broadcast_to_subscription(self,
                                      subscription_type: str,
                                      message: Dict[str, Any],
                                      sender_client_id: Optional[str] = None) -> int:
        """
        Broadcast message to all clients subscribed to type.

        Args:
            subscription_type: Subscription type to broadcast to
            message: Message to broadcast
            sender_client_id: Client ID to exclude from broadcast (optional)

        Returns:
            Number of clients message was sent to
        """
        subscribers = await self.get_subscribers(subscription_type)
        if sender_client_id:
            subscribers.discard(sender_client_id)

        if not subscribers:
            return 0

        sent_count = 0
        for client_id in subscribers:
            if await self.send_to_client(client_id, message):
                sent_count += 1

        if self.logger:
            self.logger.debug("connection_manager.broadcast_completed", {
                "subscription_type": subscription_type,
                "total_subscribers": len(subscribers),
                "messages_sent": sent_count,
                "sender_excluded": sender_client_id is not None
            })

        return sent_count

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to specific client.

        Args:
            client_id: Target client ID
            message: Message to send

        Returns:
            True if message sent successfully, False otherwise
        """
        connection = await self.get_connection(client_id)
        if not connection:
            return False

        try:
            # Serialize message
            if connection.preferred_format == "json":
                message_data = json.dumps(message)
            else:
                # Binary format support (future enhancement)
                message_data = json.dumps(message).encode('utf-8')

            # Send message - detect WebSocket type and use appropriate API
            websocket = connection.websocket

            # Use the flag stored in the connection object
            if connection.is_fastapi_websocket:
                # FastAPI WebSocket
                await websocket.send_text(message_data)
            else:
                # websockets library WebSocket
                await websocket.send(message_data)

            # Record activity
            await self.record_message_activity(client_id, "sent", len(message_data))

            return True

        except ConnectionClosed as e:
            # Normal closures (e.g., client disconnected gracefully) are not errors.
            # ConnectionClosedOK inherits from ConnectionClosed and covers code 1000.
            if isinstance(e, ConnectionClosed) and e.code in [1000, 1001]:
                if self.logger:
                    self.logger.debug("connection_manager.send_skipped_normal_closure", {
                        "client_id": client_id,
                        "close_code": e.code,
                        "reason": "Normal WebSocket closure"
                    })
            else:
                if self.logger:
                    self.logger.debug("connection_manager.send_skipped_connection_closed", {
                        "client_id": client_id,
                        "close_code": e.code,
                        "reason": "Connection closed by client"
                    })

            # Remove connection since it's closed (but don't treat as error)
            await self.remove_connection(client_id, "connection_closed_by_client")
            return False

        except Exception as e: # Catches other exceptions like ConnectionClosedError
            # Record actual error and mark connection as unhealthy
            connection.record_error()

            if self.logger:
                self.logger.error("connection_manager.send_failed", {
                    "client_id": client_id,
                    "error": str(e),
                    "consecutive_errors": connection.consecutive_errors
                })

            # Remove unhealthy connections
            if not connection.is_healthy:
                await self.remove_connection(client_id, "unhealthy")

            return False

    async def _cleanup_loop(self):
        """Background cleanup loop for dead connections and maintenance"""
        while not self._is_shutting_down:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)
                await self._perform_cleanup()
            except Exception as e:
                if self.logger:
                    self.logger.error("connection_manager.cleanup_error", {"error": str(e)})

    async def _perform_cleanup(self):
        """Perform cleanup operations"""
        async with self._connection_lock:
            current_time = time.time()
            dead_connections = []

            # Find dead connections
            for client_id, connection in self._connections.items():
                # Check heartbeat timeout
                if current_time - connection.last_heartbeat > self.heartbeat_timeout_seconds:
                    dead_connections.append((client_id, "heartbeat_timeout"))
                    continue

                # Check connection health
                if not connection.is_healthy and connection.consecutive_errors >= 10:
                    dead_connections.append((client_id, "unhealthy"))
                    continue

            # Remove dead connections
            for client_id, reason in dead_connections:
                await self.remove_connection(client_id, reason)

            # ✅ CRITICAL FIX: Cleanup message timestamps to prevent memory leaks (more aggressive)
            for connection in self._connections.values():
                # Clean old message timestamps (older than 2 minutes - reduced from 5)
                cutoff = current_time - 120
                while connection.message_timestamps and connection.message_timestamps[0] < cutoff:
                    connection.message_timestamps.popleft()

                # Clean old subscription timestamps (older than 30 minutes - reduced from 1 hour)
                sub_cutoff = current_time - 1800
                while connection.subscription_timestamps and connection.subscription_timestamps[0] < sub_cutoff:
                    connection.subscription_timestamps.popleft()

            # Update cleanup timestamp
            self._last_cleanup_time = current_time

            if self.logger and dead_connections:
                self.logger.info("connection_manager.cleanup_completed", {
                    "dead_connections_removed": len(dead_connections),
                    "remaining_connections": len(self._connections)
                })

    def get_connection_stats_snapshot(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics"""
        # NOTE: This is a snapshot and is not thread-safe. For thread-safe stats, use an async method with a lock.
        connections_snapshot = list(self._connections.values())
        total_bandwidth = sum(conn.bandwidth_used for conn in connections_snapshot)
        total_messages_sent = sum(conn.messages_sent for conn in connections_snapshot)
        total_messages_received = sum(conn.messages_received for conn in connections_snapshot)

        # Calculate average connection age
        if connections_snapshot:
            avg_age = sum(conn.get_connection_age_seconds() for conn in connections_snapshot) / len(connections_snapshot)
        else:
            avg_age = 0.0

        return {
            "current_connections": len(self._connections),
            "max_connections": self.max_connections,
            "peak_concurrent_connections": self.peak_concurrent_connections,
            "total_connections_accepted": self.total_connections_accepted,
            "total_connections_rejected": self.total_connections_rejected,
            "total_connections_dropped": self.total_connections_dropped,
            "total_bandwidth_used": total_bandwidth,
            "total_messages_sent": total_messages_sent,
            "total_messages_received": total_messages_received,
            "average_connection_age_seconds": avg_age,
            "subscription_types": len(self._subscription_clients),
            "total_active_subscriptions": sum(len(subs) for subs in self._client_subscriptions.values()),
            "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "cleanup_last_run": self._last_cleanup_time
        }

    async def shutdown(self):
        """Graceful shutdown of connection manager"""
        self._is_shutting_down = True

        # Stop cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        async with self._connection_lock:
            connection_ids = list(self._connections.keys())

        for client_id in connection_ids:
            await self.remove_connection(client_id, "shutdown")

        if self.logger:
            self.logger.info("connection_manager.shutdown_completed", {
                "final_connection_count": 0,
                "total_connections_handled": self.total_connections_accepted
            })

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on connection manager"""
        stats = self.get_connection_stats_snapshot()

        # Check if we're within acceptable limits
        healthy = True
        issues = []

        if stats["current_connections"] >= self.max_connections * 0.9:  # 90% capacity
            healthy = False
            issues.append("Near connection capacity limit")

        if stats["total_connections_rejected"] > stats["total_connections_accepted"] * 0.1:  # 10% rejection rate
            healthy = False
            issues.append("High connection rejection rate")

        return {
            "healthy": healthy,
            "component": "ConnectionManager",
            "issues": issues,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }

    async def log_connection_closed(
        self,
        client_id: str,
        close_code: int,
        close_reason: str,
        was_clean: bool,
        initiated_by: str = "unknown"
    ) -> None:
        """
        Log detailed diagnostic information when a WebSocket connection closes.

        BUG-008-1: Enhanced disconnect logging for debugging connection issues.

        Args:
            client_id: Unique identifier for the client connection
            close_code: WebSocket close code (1000=normal, 1006=abnormal, etc.)
            close_reason: Human-readable reason for closure
            was_clean: Whether the connection closed cleanly
            initiated_by: Who initiated the close (client/server/network)

        Close Code Reference:
            1000 - Normal Closure (clean close, no error)
            1001 - Going Away (page close, server shutdown)
            1002 - Protocol Error
            1005 - No Status Received
            1006 - Abnormal Closure (connection lost, no close frame)
            1011 - Internal Error
            1012 - Service Restart
        """
        if not self.logger:
            return

        # Get connection details if still available
        connection = self._connections.get(client_id)

        # Calculate metrics
        duration_seconds = 0.0
        messages_sent = 0
        messages_received = 0
        last_activity_age_seconds = 0.0

        if connection:
            duration_seconds = connection.get_connection_age_seconds()
            messages_sent = connection.messages_sent
            messages_received = connection.messages_received
            last_activity_age_seconds = time.time() - connection.last_heartbeat

        # Build log data with all diagnostic fields
        log_data = {
            "client_id": client_id,
            "close_code": close_code,
            "close_reason": close_reason,
            "was_clean": was_clean,
            "duration_seconds": duration_seconds,
            "messages_sent": messages_sent,
            "messages_received": messages_received,
            "last_activity_age_seconds": last_activity_age_seconds,
            "initiated_by": initiated_by
        }

        # Determine if this is an abnormal close (AC6: log at WARNING level)
        # Normal closes: 1000 (normal), 1001 (going away)
        # Abnormal closes: 1002, 1005, 1006, 1011, 1012, etc.
        is_abnormal = close_code not in [1000, 1001]

        if is_abnormal:
            self.logger.warning("websocket.connection_closed", log_data)
        else:
            self.logger.info("websocket.connection_closed", log_data)
