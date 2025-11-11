"""
Broadcast Provider
==================
Centralized WebSocket broadcast logic with performance monitoring and error handling.
Production-ready with consistent message formatting and client management.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Set, Callable, Awaitable
from datetime import datetime
from collections import deque

from ..core.logger import StructuredLogger
from ..infrastructure.exchanges.rate_limiter import TokenBucketRateLimiter


class WebSocketServerInterface:
    """Interface for WebSocket server communication"""

    async def broadcast_to_subscribers(self, subscription_type: str, data: dict, exclude_client: str = None) -> int:
        """Broadcast message to subscribers"""
        ...


class BroadcastProvider:
    """
    Centralized broadcast provider for WebSocket messages.

    Features:
    - Consistent message formatting and validation
    - Performance monitoring and latency tracking
    - Error handling and recovery
    - Client management and statistics
    - Rate limiting and backpressure handling
    - Memory-efficient message queuing
    """

    def __init__(self,
                 websocket_server: WebSocketServerInterface,
                 logger: StructuredLogger,
                 event_bus: Any,
                 max_queue_size: int = 20000,  # Increased for trading (was 10000)
                 max_batch_size: int = 50,
                 latency_threshold_ms: int = 50,  # Reduced for trading (was 100)
                 progress_throttle_interval: float = 0.1):  # Faster updates (was 0.5)
        """
        Initialize BroadcastProvider.

        Args:
            websocket_server: WebSocket server interface for broadcasting
            event_bus: EventBus instance for publishing events
            logger: Optional logger instance
            max_queue_size: Maximum size of broadcast queue
            max_batch_size: Maximum batch size for batched broadcasts
            latency_threshold_ms: Threshold for latency warnings
        """
        self.websocket_server = websocket_server
        if event_bus is None:
            raise ValueError("BroadcastProvider requires an EventBus instance.")
        self.event_bus = event_bus
        self.logger = logger

        # Configuration
        self.max_queue_size = max_queue_size
        self.max_batch_size = max_batch_size
        self.latency_threshold_ms = latency_threshold_ms

        # Thread safety
        self._queue_lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()

        # Rate limiter for backpressure control - TRADING OPTIMIZED
        self._output_rate_limiter = TokenBucketRateLimiter(
            max_tokens=2000,  # Increased burst capacity for trading (was 1000)
            refill_rate=1000.0,  # Higher sustained rate for trading (was 500)
            name="BroadcastOutput"
        )

        # Message queue for async processing
        self.broadcast_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)

        # Performance tracking
        self._total_messages_sent = 0
        self._total_clients_reached = 0
        self._total_errors = 0
        self._latency_measurements: deque[float] = deque(maxlen=1000)
        self._processing_times: deque[float] = deque(maxlen=1000)

        # Progress throttling
        self._progress_throttle_interval = progress_throttle_interval
        self._last_progress_emit: Dict[str, float] = {}
        self._last_progress_percentage: Dict[str, float] = {}

        # Message type statistics
        self._message_type_stats: Dict[str, int] = {}
        self._stream_type_stats: Dict[str, int] = {}

        # Control flags
        self.is_running = False
        self._shutdown_event = asyncio.Event()

        # ✅ MEMORY LEAK FIX: Background task tracking to prevent fire-and-forget leaks
        # Tasks are tracked and properly cancelled during shutdown (following StrategyManager pattern)
        self._background_tasks: set = set()

        # Background processing task
        self._processing_task: Optional[asyncio.Task] = None

    async def get_total_messages_sent(self) -> int:
        async with self._stats_lock:
            return self._total_messages_sent

    async def get_total_clients_reached(self) -> int:
        async with self._stats_lock:
            return self._total_clients_reached

    async def get_total_errors(self) -> int:
        async with self._stats_lock:
            return self._total_errors

    async def start(self):
        """Start the broadcast provider"""
        if self.is_running:
            return

        self.is_running = True
        self._processing_task = asyncio.create_task(self._process_broadcast_queue())
        # ✅ MEMORY LEAK FIX: Track task and auto-cleanup when done
        self._background_tasks.add(self._processing_task)
        self._processing_task.add_done_callback(self._background_tasks.discard)

        self.logger.info("broadcast_provider.started", {
            "max_queue_size": self.max_queue_size,
            "max_batch_size": self.max_batch_size
        })

    async def stop(self):
        """Stop the broadcast provider gracefully"""
        if not self.is_running:
            return

        self.is_running = False
        self._shutdown_event.set()

        # Drain remaining messages to prevent loss
        await self.broadcast_queue.join()

        # ✅ MEMORY LEAK FIX: Cancel all background tasks (prevents dangling task warnings)
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete or be cancelled
        if self._background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._background_tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("broadcast_provider.shutdown_timeout", {
                    "remaining_tasks": len([t for t in self._background_tasks if not t.done()])
                })

        # Clear the task set
        self._background_tasks.clear()

        self.logger.info("broadcast_provider.stopped")

    async def broadcast_message(self,
                               stream_type: str,
                               message_type: str,
                               data: Dict[str, Any],
                               exclude_client: str = None) -> bool:
        """
        Broadcast a message to subscribers.

        Args:
            stream_type: Type of data stream (e.g., 'market_data', 'execution_status')
            message_type: Type of message (e.g., 'data', 'batch_update')
            data: Message data payload
            exclude_client: Optional client ID to exclude from broadcast

        Returns:
            True if message was queued successfully, False otherwise
        """
        start_time = time.perf_counter()

        try:
            # Validate message structure
            if not self._validate_message(stream_type, message_type, data):
                return False

            # Create standardized message
            message = self._create_standard_message(stream_type, message_type, data)

            # ✅ PERF FIX: Add to queue with timeout - fail fast instead of indefinite blocking
            # This prevents EventBridge handlers from blocking when broadcast queue is full
            try:
                await asyncio.wait_for(
                    self.broadcast_queue.put({
                        "message": message,
                        "stream_type": stream_type,
                        "exclude_client": exclude_client,
                        "queue_time": start_time
                    }),
                    timeout=0.01  # 10ms max - fail fast for real-time trading
                )
            except asyncio.TimeoutError:
                # Broadcast queue overloaded - drop event (best effort delivery)
                async with self._stats_lock:
                    self._total_errors += 1

                if self.logger:
                    self.logger.warning("broadcast_provider.queue_full_event_dropped", {
                        "stream_type": stream_type,
                        "message_type": message_type,
                        "queue_size": self.broadcast_queue.qsize(),
                        "max_queue_size": self.max_queue_size
                    })
                return False

            # Track message type statistics
            async with self._stats_lock:
                self._message_type_stats[message_type] = self._message_type_stats.get(message_type, 0) + 1
                self._stream_type_stats[stream_type] = self._stream_type_stats.get(stream_type, 0) + 1

            return True

        except Exception as e:
            async with self._stats_lock:
                self._total_errors += 1

            if self.logger:
                self.logger.error("broadcast_provider.message_queue_error", {
                    "stream_type": stream_type,
                    "message_type": message_type,
                    "error": str(e)
                })
            return False

    async def broadcast_execution_progress(self,
                                          session_id: str,
                                          progress_data: Dict[str, Any],
                                          exclude_client: str = None) -> bool:
        """
        Broadcast execution progress update.

        Args:
            session_id: Execution session ID
            progress_data: Progress data from ExecutionProgress.to_dict()
            exclude_client: Optional client ID to exclude

        Returns:
            True if broadcast was successful
        """
        now = time.monotonic()
        progress_section = progress_data.get("progress")
        percentage = None
        if isinstance(progress_section, dict):
            try:
                percentage = float(progress_section.get("percentage"))
            except (TypeError, ValueError):
                percentage = None

        status_value = progress_data.get("status")
        is_terminal = status_value in {"completed", "failed", "stopped", "cancelled"}

        last_emit = self._last_progress_emit.get(session_id)
        last_percentage = self._last_progress_percentage.get(session_id)

        if not is_terminal and last_emit is not None:
            if now - last_emit < self._progress_throttle_interval:
                if percentage is None or last_percentage is None or abs(percentage - last_percentage) < 0.1:
                    if self.logger:
                        self.logger.debug("broadcast_provider.progress_throttled", {
                            "session_id": session_id,
                            "queue_latency_ms": 0,
                            "throttle_interval": self._progress_throttle_interval
                        })
                    self._last_progress_emit[session_id] = now
                    if percentage is not None:
                        self._last_progress_percentage[session_id] = percentage
                    return True

        self._last_progress_emit[session_id] = now
        if percentage is not None:
            self._last_progress_percentage[session_id] = percentage
        elif session_id in self._last_progress_percentage:
            del self._last_progress_percentage[session_id]

        # Ensure required fields are present
        if "session_id" not in progress_data:
            progress_data["session_id"] = session_id
            if self.logger:
                self.logger.warning("broadcast_provider.session_id_missing_in_progress_data", {
                    "session_id": session_id
                })

        # Create WebSocket message format for EventBridge
        websocket_message = {
            "type": "data",
            "stream": "execution_status",
            "data": progress_data
        }

        try:
            if self.event_bus:
                await self.event_bus.publish(
                    "execution.progress_websocket_update",
                    websocket_message,
                    publisher_id=f"broadcast:{session_id}"
                )
            else:
                if self.logger:
                    self.logger.debug("broadcast_provider.execution_progress_published", {
                        "session_id": session_id,
                        "progress_percentage": progress_data.get('progress', {}).get('percentage', 0),
                        "records_collected": progress_data.get('records_collected', 0)
                    })
            if is_terminal:
                self._last_progress_emit.pop(session_id, None)
                self._last_progress_percentage.pop(session_id, None)
            return True

        except Exception as e:
            if self.logger:
                self.logger.error("broadcast_provider.execution_progress_publish_error", {
                    "session_id": session_id,
                    "error": str(e)
                })
            return False

    async def broadcast_execution_result(self,
                                       session_id: str,
                                       result_data: Dict[str, Any],
                                       exclude_client: str = None) -> bool:
        """
        Broadcast execution result.

        Args:
            session_id: Execution session ID
            result_data: Result data from ExecutionResult.to_dict()
            exclude_client: Optional client ID to exclude

        Returns:
            True if broadcast was successful
        """
        # Create WebSocket message format for EventBridge
        websocket_message = {
            "type": "execution_result",
            "stream": "execution_result",
            "data": result_data
        }

        # Publish to EventBus for EventBridge to handle
        try:
            if self.event_bus:
                await self.event_bus.publish("execution.result_websocket_update", websocket_message)
            else:
                self.logger.error("broadcast_provider.no_eventbus_instance_available_for_execution_result", {
                    "session_id": session_id
                })
                return False

            if self.logger:
                self.logger.debug("broadcast_provider.execution_result_published", {
                    "session_id": session_id,
                    "status": result_data.get('status', 'unknown')
                })

            return True

        except Exception as e:
            self.logger.error("broadcast_provider.execution_result_publish_error", {
                "session_id": session_id,
                "error": str(e)
            })
            return False

    async def broadcast_market_data(self,
                                  market_data: Dict[str, Any],
                                  exclude_client: str = None) -> bool:
        """
        Broadcast market data update.

        Args:
            market_data: Market data payload
            exclude_client: Optional client ID to exclude

        Returns:
            True if broadcast was successful
        """
        return await self.broadcast_message(
            stream_type="market_data",
            message_type="data",
            data=market_data,
            exclude_client=exclude_client
        )

    async def broadcast_indicator_data(self,
                                     indicator_data: Dict[str, Any],
                                     exclude_client: str = None) -> bool:
        """
        Broadcast indicator data update.

        Args:
            indicator_data: Indicator data payload
            exclude_client: Optional client ID to exclude

        Returns:
            True if broadcast was successful
        """
        return await self.broadcast_message(
            stream_type="indicators",
            message_type="data",
            data=indicator_data,
            exclude_client=exclude_client
        )

    async def broadcast_health_update(self,
                                    health_data: Dict[str, Any],
                                    exclude_client: str = None) -> bool:
        """
        Broadcast health status update.

        Args:
            health_data: Health monitoring data
            exclude_client: Optional client ID to exclude

        Returns:
            True if broadcast was successful
        """
        return await self.broadcast_message(
            stream_type="health_check",
            message_type="health_update",
            data=health_data,
            exclude_client=exclude_client
        )

    async def broadcast_batch_update(self,
                                   stream_type: str,
                                   batch_data: Dict[str, Any],
                                   exclude_client: str = None) -> bool:
        """
        Broadcast batched update.

        Args:
            stream_type: Type of data stream
            batch_data: Batched data payload
            exclude_client: Optional client ID to exclude

        Returns:
            True if broadcast was successful
        """
        return await self.broadcast_message(
            stream_type=stream_type,
            message_type="batch_update",
            data=batch_data,
            exclude_client=exclude_client
        )

    def _validate_message(self, stream_type: str, message_type: str, data: Dict[str, Any]) -> bool:
        """Validate message structure"""
        if not stream_type or not message_type:
            return False

        if not isinstance(data, dict):
            return False

        # Stream-specific validation
        if stream_type == "execution_status":
            return "session_id" in data
        elif stream_type == "execution_result":
            return "session_id" in data and "status" in data
        elif stream_type == "market_data":
            return "symbol" in data or "symbols" in data
        elif stream_type == "indicators":
            return "indicators" in data or any(k in data for k in ["name", "value", "symbol"])
        elif stream_type == "health_check":
            return "status" in data

        return True

    def _create_standard_message(self, stream_type: str, message_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized WebSocket message"""
        return {
            "type": message_type,
            "stream": stream_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

    async def _process_broadcast_queue(self):
        """Process messages from broadcast queue"""
        while not self._shutdown_event.is_set():
            try:
                # Get next message from queue
                queue_item = await self.broadcast_queue.get()

                message = queue_item["message"]
                stream_type = queue_item["stream_type"]
                exclude_client = queue_item["exclude_client"]
                queue_time = queue_item["queue_time"]

                # Measure queue latency
                queue_latency = (time.perf_counter() - queue_time) * 1000
                if queue_latency > self.latency_threshold_ms:
                    # Check if this is a trading-critical message
                    is_trading_critical = (message.get("type") == "data" and 
                                         stream_type in ["trading_signals", "order_updates", "position_updates"])
                    
                    if is_trading_critical:
                        self.logger.error("broadcast_provider.trading_critical_latency", {
                            "stream_type": stream_type,
                            "queue_latency_ms": queue_latency,
                            "threshold_ms": self.latency_threshold_ms,
                            "warning": "TRADING LATENCY EXCEEDED"
                        })
                    else:
                        self.logger.warning("broadcast_provider.high_queue_latency", {
                            "stream_type": stream_type,
                            "queue_latency_ms": queue_latency,
                            "threshold_ms": self.latency_threshold_ms
                        })

                # ✅ PERF FIX: Bypass rate limiting for high-frequency streams
                # Market data and indicators generate 1000+ msgs/sec - rate limiting causes backpressure
                # Rate limiting only for low-frequency streams to prevent abuse
                is_high_frequency = stream_type in ["market_data", "indicators", "trading_signals", "order_updates", "position_updates"]
                if not is_high_frequency:
                    await self._output_rate_limiter.acquire_wait(tokens=1, timeout=0.05)  # Shorter timeout

                # Broadcast message
                broadcast_start = time.perf_counter()
                clients_reached = await self.websocket_server.broadcast_to_subscribers(
                    stream_type, message, exclude_client
                )

                # Measure broadcast latency
                broadcast_latency = (time.perf_counter() - broadcast_start) * 1000
                self._latency_measurements.append(broadcast_latency)

                if broadcast_latency > self.latency_threshold_ms:
                    self.logger.warning("broadcast_provider.high_broadcast_latency", {
                        "stream_type": stream_type,
                        "broadcast_latency_ms": broadcast_latency,
                        "clients_reached": clients_reached
                    })

                # Update statistics
                async with self._stats_lock:
                    self._total_messages_sent += 1
                    self._total_clients_reached += clients_reached

                # Log successful broadcast
                self.logger.debug("broadcast_provider.message_sent", {
                    "stream_type": stream_type,
                    "message_type": message["type"],
                    "clients_reached": clients_reached,
                    "queue_latency_ms": queue_latency,
                    "broadcast_latency_ms": broadcast_latency
                })

                self.broadcast_queue.task_done()

            except Exception as e:
                async with self._stats_lock:
                    self._total_errors += 1

                self.logger.error("broadcast_provider.queue_processing_error", {
                    "error": str(e)
                })

    async def get_stats(self) -> Dict[str, Any]:
        """Get broadcast provider statistics"""
        async with self._stats_lock:
            avg_latency = (sum(self._latency_measurements) / len(self._latency_measurements)
                          if self._latency_measurements else 0)
            max_latency = max(self._latency_measurements) if self._latency_measurements else 0

            total_messages_sent = await self.get_total_messages_sent()
            total_clients_reached = await self.get_total_clients_reached()
            total_errors = await self.get_total_errors()

            return {
                "is_running": self.is_running,
                "total_messages_sent": total_messages_sent,
                "total_clients_reached": total_clients_reached,
                "total_errors": total_errors,
                "queue_size": self.broadcast_queue.qsize(),
                "avg_latency_ms": avg_latency,
                "max_latency_ms": max_latency,
                "latency_measurements_count": len(self._latency_measurements),
                "message_type_stats": dict(self._message_type_stats),
                "stream_type_stats": dict(self._stream_type_stats)
            }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        stats = await self.get_stats()

        # Check if provider is healthy
        healthy = (
            self.is_running and
            stats["total_errors"] < 100 and  # Less than 100 errors
            stats["queue_size"] < self.max_queue_size * 0.9  # Queue not over 90% full
        )

        return {
            "healthy": healthy,
            "component": "BroadcastProvider",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }