"""
WebSocket Heartbeat Service
============================
Proactive heartbeat mechanism for WebSocket connection health monitoring.

Features:
- Server-initiated ping messages at configurable intervals
- Connection timeout detection and cleanup
- RTT (Round-Trip Time) tracking for latency monitoring
- Automatic reconnection signaling for unhealthy connections
"""

import asyncio
import time
from typing import Dict, Any, Optional, Set, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class HeartbeatMetrics:
    """Metrics for a single connection's heartbeat status."""
    client_id: str
    last_ping_sent: float = 0.0
    last_pong_received: float = 0.0
    ping_count: int = 0
    pong_count: int = 0
    missed_pongs: int = 0
    rtt_ms: float = 0.0
    rtt_history: list = field(default_factory=list)
    is_healthy: bool = True

    @property
    def avg_rtt_ms(self) -> float:
        """Calculate average RTT from history."""
        if not self.rtt_history:
            return 0.0
        return sum(self.rtt_history) / len(self.rtt_history)

    @property
    def pending_pong(self) -> bool:
        """Check if we're waiting for a pong response."""
        return self.last_ping_sent > self.last_pong_received

    def record_ping_sent(self):
        """Record that a ping was sent."""
        self.last_ping_sent = time.time()
        self.ping_count += 1

    def record_pong_received(self):
        """Record pong received and calculate RTT."""
        now = time.time()
        self.last_pong_received = now
        self.pong_count += 1
        self.missed_pongs = 0
        self.is_healthy = True

        # Calculate RTT
        if self.last_ping_sent > 0:
            self.rtt_ms = (now - self.last_ping_sent) * 1000
            # Keep last 10 RTT values for averaging
            self.rtt_history.append(self.rtt_ms)
            if len(self.rtt_history) > 10:
                self.rtt_history.pop(0)

    def record_missed_pong(self):
        """Record that expected pong was not received."""
        self.missed_pongs += 1
        if self.missed_pongs >= 3:
            self.is_healthy = False


class HeartbeatService:
    """
    Manages WebSocket connection heartbeats.

    Responsibilities:
    - Send periodic ping messages to all connected clients
    - Track pong responses and detect timeouts
    - Report connection health to ConnectionManager
    - Provide RTT/latency metrics for monitoring

    Configuration:
    - ping_interval_seconds: How often to send pings (default: 30s)
    - pong_timeout_seconds: How long to wait for pong (default: 10s)
    - max_missed_pongs: Disconnect after this many missed pongs (default: 3)
    """

    def __init__(
        self,
        ping_interval_seconds: float = 30.0,
        pong_timeout_seconds: float = 10.0,
        max_missed_pongs: int = 3,
        logger=None
    ):
        """
        Initialize HeartbeatService.

        Args:
            ping_interval_seconds: Interval between pings
            pong_timeout_seconds: Timeout waiting for pong
            max_missed_pongs: Max missed pongs before marking unhealthy
            logger: Optional structured logger
        """
        self.ping_interval = ping_interval_seconds
        self.pong_timeout = pong_timeout_seconds
        self.max_missed_pongs = max_missed_pongs
        self.logger = logger

        # Heartbeat tracking per client
        self._metrics: Dict[str, HeartbeatMetrics] = {}

        # Callbacks
        self._send_message_callback: Optional[Callable[[str, Dict], Awaitable[bool]]] = None
        self._on_unhealthy_callback: Optional[Callable[[str], Awaitable[None]]] = None
        self._on_timeout_callback: Optional[Callable[[str], Awaitable[None]]] = None

        # Background task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._is_running = False

        # Connected clients set (managed by ConnectionManager)
        self._active_clients: Set[str] = set()

    def set_callbacks(
        self,
        send_message: Callable[[str, Dict], Awaitable[bool]],
        on_unhealthy: Optional[Callable[[str], Awaitable[None]]] = None,
        on_timeout: Optional[Callable[[str], Awaitable[None]]] = None
    ):
        """
        Set callback functions for heartbeat events.

        Args:
            send_message: Async function(client_id, message) -> bool to send messages
            on_unhealthy: Async function(client_id) called when connection becomes unhealthy
            on_timeout: Async function(client_id) called when connection times out
        """
        self._send_message_callback = send_message
        self._on_unhealthy_callback = on_unhealthy
        self._on_timeout_callback = on_timeout

    def register_client(self, client_id: str):
        """Register a new client for heartbeat monitoring."""
        self._active_clients.add(client_id)
        self._metrics[client_id] = HeartbeatMetrics(client_id=client_id)
        if self.logger:
            self.logger.debug("heartbeat_service.client_registered", {
                "client_id": client_id
            })

    def unregister_client(self, client_id: str):
        """Unregister a client from heartbeat monitoring."""
        self._active_clients.discard(client_id)
        self._metrics.pop(client_id, None)
        if self.logger:
            self.logger.debug("heartbeat_service.client_unregistered", {
                "client_id": client_id
            })

    async def record_pong(self, client_id: str):
        """
        Record pong response from client.

        Called by message handlers when pong is received.

        Args:
            client_id: Client that sent the pong
        """
        if client_id in self._metrics:
            metrics = self._metrics[client_id]
            metrics.record_pong_received()

            if self.logger:
                self.logger.debug("heartbeat_service.pong_received", {
                    "client_id": client_id,
                    "rtt_ms": metrics.rtt_ms,
                    "avg_rtt_ms": metrics.avg_rtt_ms
                })

    async def start(self):
        """Start the heartbeat service background task."""
        if self._is_running:
            return

        self._is_running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        if self.logger:
            self.logger.info("heartbeat_service.started", {
                "ping_interval_seconds": self.ping_interval,
                "pong_timeout_seconds": self.pong_timeout,
                "max_missed_pongs": self.max_missed_pongs
            })

    async def stop(self):
        """Stop the heartbeat service."""
        self._is_running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.logger:
            self.logger.info("heartbeat_service.stopped")

    async def _heartbeat_loop(self):
        """Main heartbeat loop - runs in background."""
        while self._is_running:
            try:
                await self._send_pings()
                await asyncio.sleep(self.ping_interval)
                await self._check_timeouts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger:
                    self.logger.error("heartbeat_service.loop_error", {
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                await asyncio.sleep(1)  # Brief pause on error

    async def _send_pings(self):
        """Send ping messages to all active clients."""
        if not self._send_message_callback:
            return

        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat(),
            "server_time": time.time()
        }

        for client_id in list(self._active_clients):
            try:
                metrics = self._metrics.get(client_id)
                if metrics:
                    metrics.record_ping_sent()

                success = await self._send_message_callback(client_id, ping_message)

                if not success and self.logger:
                    self.logger.warning("heartbeat_service.ping_send_failed", {
                        "client_id": client_id
                    })

            except Exception as e:
                if self.logger:
                    self.logger.error("heartbeat_service.ping_error", {
                        "client_id": client_id,
                        "error": str(e)
                    })

    async def _check_timeouts(self):
        """Check for clients that haven't responded to pings."""
        now = time.time()
        unhealthy_clients = []
        timeout_clients = []

        for client_id in list(self._active_clients):
            metrics = self._metrics.get(client_id)
            if not metrics:
                continue

            # Check if we're waiting for a pong that's overdue
            if metrics.pending_pong:
                time_since_ping = now - metrics.last_ping_sent

                if time_since_ping > self.pong_timeout:
                    metrics.record_missed_pong()

                    if self.logger:
                        self.logger.warning("heartbeat_service.pong_timeout", {
                            "client_id": client_id,
                            "missed_pongs": metrics.missed_pongs,
                            "time_since_ping_seconds": time_since_ping
                        })

                    if not metrics.is_healthy:
                        unhealthy_clients.append(client_id)

                    if metrics.missed_pongs >= self.max_missed_pongs:
                        timeout_clients.append(client_id)

        # Handle unhealthy connections
        for client_id in unhealthy_clients:
            if self._on_unhealthy_callback:
                try:
                    await self._on_unhealthy_callback(client_id)
                except Exception as e:
                    if self.logger:
                        self.logger.error("heartbeat_service.unhealthy_callback_error", {
                            "client_id": client_id,
                            "error": str(e)
                        })

        # Handle timed out connections
        for client_id in timeout_clients:
            if self._on_timeout_callback:
                try:
                    await self._on_timeout_callback(client_id)
                except Exception as e:
                    if self.logger:
                        self.logger.error("heartbeat_service.timeout_callback_error", {
                            "client_id": client_id,
                            "error": str(e)
                        })

    def get_metrics(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get heartbeat metrics for a specific client.

        Args:
            client_id: Client to get metrics for

        Returns:
            Dict with heartbeat metrics or None if client not found
        """
        metrics = self._metrics.get(client_id)
        if not metrics:
            return None

        return {
            "client_id": metrics.client_id,
            "is_healthy": metrics.is_healthy,
            "ping_count": metrics.ping_count,
            "pong_count": metrics.pong_count,
            "missed_pongs": metrics.missed_pongs,
            "last_rtt_ms": metrics.rtt_ms,
            "avg_rtt_ms": metrics.avg_rtt_ms,
            "pending_pong": metrics.pending_pong,
            "last_ping_sent": metrics.last_ping_sent,
            "last_pong_received": metrics.last_pong_received
        }

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get heartbeat metrics for all clients."""
        return {
            client_id: self.get_metrics(client_id)
            for client_id in self._active_clients
            if self.get_metrics(client_id) is not None
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of heartbeat service status."""
        all_metrics = list(self._metrics.values())
        healthy_count = sum(1 for m in all_metrics if m.is_healthy)
        unhealthy_count = len(all_metrics) - healthy_count

        avg_rtt = 0.0
        if all_metrics:
            rtts = [m.avg_rtt_ms for m in all_metrics if m.avg_rtt_ms > 0]
            if rtts:
                avg_rtt = sum(rtts) / len(rtts)

        return {
            "is_running": self._is_running,
            "active_clients": len(self._active_clients),
            "healthy_clients": healthy_count,
            "unhealthy_clients": unhealthy_count,
            "average_rtt_ms": avg_rtt,
            "ping_interval_seconds": self.ping_interval,
            "pong_timeout_seconds": self.pong_timeout
        }
