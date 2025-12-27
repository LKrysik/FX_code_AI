"""
Event Bus - Simplified Implementation
======================================
Central asynchronous event bus for pub/sub communication.

Delivery Guarantee: AT_LEAST_ONCE (with retry on failure)
Memory Safe: NO defaultdict, explicit cleanup
Error Isolation: Subscriber crashes don't affect others
"""

import asyncio
from typing import Callable, Any, Dict, List, Optional

from src.core.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# W2 Enhancement: Metrics and Alerting Data Classes
# ============================================================================

from dataclasses import dataclass, field
from time import time


@dataclass
class EventBusMetrics:
    """
    Comprehensive metrics for EventBus monitoring.

    Tracks publish/delivery statistics and latency for health monitoring.
    Thread-safe through atomic operations on primitive counters.
    """
    # Counters
    total_published: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    total_retries: int = 0

    # Per-topic counters (topic -> count)
    published_by_topic: Dict[str, int] = field(default_factory=dict)
    failed_by_topic: Dict[str, int] = field(default_factory=dict)

    # Latency tracking (in milliseconds)
    total_latency_ms: float = 0.0
    latency_samples: int = 0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')

    # Time tracking
    last_publish_time: float = 0.0
    last_failure_time: float = 0.0
    started_at: float = field(default_factory=time)

    def record_publish(self, topic: str) -> None:
        """Record a publish event."""
        self.total_published += 1
        self.published_by_topic[topic] = self.published_by_topic.get(topic, 0) + 1
        self.last_publish_time = time()

    def record_delivery(self, latency_ms: float) -> None:
        """Record successful delivery with latency."""
        self.total_delivered += 1
        self.total_latency_ms += latency_ms
        self.latency_samples += 1
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)

    def record_failure(self, topic: str) -> None:
        """Record a delivery failure."""
        self.total_failed += 1
        self.failed_by_topic[topic] = self.failed_by_topic.get(topic, 0) + 1
        self.last_failure_time = time()

    def record_retry(self) -> None:
        """Record a retry attempt."""
        self.total_retries += 1

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.latency_samples == 0:
            return 0.0
        return self.total_latency_ms / self.latency_samples

    @property
    def success_rate(self) -> float:
        """Calculate delivery success rate (0.0 - 1.0)."""
        total = self.total_delivered + self.total_failed
        if total == 0:
            return 1.0
        return self.total_delivered / total

    @property
    def uptime_seconds(self) -> float:
        """Calculate uptime in seconds."""
        return time() - self.started_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for health check."""
        return {
            "total_published": self.total_published,
            "total_delivered": self.total_delivered,
            "total_failed": self.total_failed,
            "total_retries": self.total_retries,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2) if self.min_latency_ms != float('inf') else 0.0,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "last_publish_time": self.last_publish_time,
            "last_failure_time": self.last_failure_time,
            "topics_with_failures": list(self.failed_by_topic.keys())
        }

    def to_prometheus_format(self) -> str:
        """
        P66 FIX: Convert metrics to Prometheus exposition format.

        Returns metrics in standard Prometheus text format for future
        integration with Prometheus/Grafana monitoring stack.

        Returns:
            String in Prometheus exposition format
        """
        lines = [
            "# HELP eventbus_messages_published_total Total messages published",
            "# TYPE eventbus_messages_published_total counter",
            f"eventbus_messages_published_total {self.total_published}",
            "",
            "# HELP eventbus_messages_delivered_total Total messages delivered successfully",
            "# TYPE eventbus_messages_delivered_total counter",
            f"eventbus_messages_delivered_total {self.total_delivered}",
            "",
            "# HELP eventbus_messages_failed_total Total messages that failed delivery",
            "# TYPE eventbus_messages_failed_total counter",
            f"eventbus_messages_failed_total {self.total_failed}",
            "",
            "# HELP eventbus_retries_total Total retry attempts",
            "# TYPE eventbus_retries_total counter",
            f"eventbus_retries_total {self.total_retries}",
            "",
            "# HELP eventbus_success_rate Delivery success rate (0.0-1.0)",
            "# TYPE eventbus_success_rate gauge",
            f"eventbus_success_rate {self.success_rate:.4f}",
            "",
            "# HELP eventbus_latency_avg_ms Average delivery latency in milliseconds",
            "# TYPE eventbus_latency_avg_ms gauge",
            f"eventbus_latency_avg_ms {self.avg_latency_ms:.2f}",
            "",
            "# HELP eventbus_latency_max_ms Maximum delivery latency in milliseconds",
            "# TYPE eventbus_latency_max_ms gauge",
            f"eventbus_latency_max_ms {self.max_latency_ms:.2f}",
            "",
            "# HELP eventbus_uptime_seconds EventBus uptime in seconds",
            "# TYPE eventbus_uptime_seconds gauge",
            f"eventbus_uptime_seconds {self.uptime_seconds:.1f}",
        ]

        # Add per-topic metrics
        for topic, count in self.published_by_topic.items():
            lines.append(f'eventbus_messages_published_by_topic{{topic="{topic}"}} {count}')

        for topic, count in self.failed_by_topic.items():
            lines.append(f'eventbus_messages_failed_by_topic{{topic="{topic}"}} {count}')

        return "\n".join(lines)


@dataclass
class AlertThresholds:
    """
    Configurable thresholds for EventBus health alerting.

    When metrics exceed these thresholds, alerts are triggered.
    """
    # Success rate threshold (below this triggers CRITICAL)
    min_success_rate: float = 0.95

    # Latency thresholds (ms)
    max_avg_latency_ms: float = 100.0
    max_single_latency_ms: float = 500.0

    # Failure thresholds
    max_consecutive_failures: int = 5
    max_failures_per_minute: int = 10

    # Queue thresholds (for future queue-based implementation)
    max_queue_size: int = 1000

    # Inactivity threshold (seconds without publish)
    max_inactivity_seconds: float = 300.0  # 5 minutes


@dataclass
class HealthAlert:
    """
    Health alert emitted when thresholds are breached.
    """
    severity: str  # CRITICAL, WARNING, INFO
    alert_type: str  # success_rate, latency, failure_count, inactivity
    message: str
    current_value: Any
    threshold_value: Any
    timestamp: float = field(default_factory=time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "severity": self.severity,
            "alert_type": self.alert_type,
            "message": self.message,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp
        }


# Event Topics - DO NOT CHANGE without coordination
TOPICS = {
    "market_data": {
        "description": "New tick price/volume from exchange",
        "data_structure": {
            "symbol": "str",
            "timestamp": "int (epoch ms)",
            "price": "float",
            "volume": "float",
            "quote_volume": "float"
        }
    },
    "indicator_updated": {
        "description": "Indicator calculation completed",
        "data_structure": {
            "indicator_id": "str",
            "symbol": "str",
            "value": "float",
            "confidence": "float",
            "metadata": "dict"
        }
    },
    "signal_generated": {
        "description": "Strategy generated trading signal (S1, Z1, ZE1, E1)",
        "data_structure": {
            "signal_type": "str (S1/Z1/ZE1/E1)",
            "symbol": "str",
            "side": "str (BUY/SELL)",
            "quantity": "float",
            "confidence": "float",
            "indicator_values": "dict"
        }
    },
    "order_created": {
        "description": "New order submitted to exchange",
        "data_structure": {
            "order_id": "str",
            "symbol": "str",
            "side": "str",
            "quantity": "float",
            "price": "float (optional)",
            "status": "str",
            "exchange_order_id": "str (optional)",
            "timestamp": "int (epoch ms)"
        }
    },
    "order_filled": {
        "description": "Order executed by exchange",
        "data_structure": {
            "order_id": "str",
            "exchange_order_id": "str",
            "filled_price": "float",
            "filled_quantity": "float",
            "slippage": "float",
            "timestamp": "int (epoch ms)"
        }
    },
    "position_updated": {
        "description": "Position changed (new, closed, liquidated)",
        "data_structure": {
            "position_id": "str",
            "symbol": "str",
            "current_price": "float",
            "entry_price": "float",
            "quantity": "float",
            "unrealized_pnl": "float",
            "margin_ratio": "float",
            "liquidation_price": "float",
            "timestamp": "int (epoch ms)"
        }
    },
    "risk_alert": {
        "description": "Risk threshold breached (margin < 15%)",
        "data_structure": {
            "severity": "str (CRITICAL/WARNING/INFO)",
            "alert_type": "str",
            "message": "str",
            "details": "dict",
            "timestamp": "int (epoch ms)"
        }
    }
}


class EventBus:
    """
    Simplified EventBus with AT_LEAST_ONCE delivery guarantee.

    Features:
    - Subscribe/publish/unsubscribe pattern
    - Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s)
    - Error isolation: subscriber crash doesn't affect others
    - Memory safe: NO defaultdict, explicit cleanup
    - All async (asyncio)
    - W2 Enhancement: Comprehensive health monitoring and alerting
    """

    def __init__(self):
        """Initialize EventBus with memory-safe structures."""
        # CRITICAL: Use explicit Dict, NOT defaultdict (memory leak prevention)
        self._subscribers: Dict[str, List[Callable]] = {}
        self._shutdown_requested = False
        # Lock to protect concurrent access to _subscribers dict
        self._lock = asyncio.Lock()

        # W2 Enhancement: Metrics tracking
        self._metrics = EventBusMetrics()
        self._alert_thresholds = AlertThresholds()
        self._alert_callbacks: List[Callable] = []

        # P61 FIX: Prevent alert→publish infinite loop
        self._in_alert_emission = False

        # P58 FIX: Rate limit alert checking (max once per second)
        self._last_alert_check_time: float = 0.0
        self._alert_check_interval: float = 1.0  # seconds

        logger.info("EventBus initialized (simplified, AT_LEAST_ONCE delivery, W2 monitoring)")

    async def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        """
        Subscribe to topic with async handler.

        Args:
            topic: Event topic to subscribe to
            handler: Async callable that receives event data

        Raises:
            ValueError: If topic or handler is invalid
        """
        if not topic or not isinstance(topic, str):
            raise ValueError("Topic must be a non-empty string")
        if not callable(handler):
            raise ValueError("Handler must be callable")

        # Protect concurrent access to _subscribers dict
        async with self._lock:
            # Explicit dict creation (NO defaultdict)
            if topic not in self._subscribers:
                self._subscribers[topic] = []

            self._subscribers[topic].append(handler)
            subscriber_count = len(self._subscribers[topic])

        logger.info(f"Subscribed to '{topic}' (total subscribers: {subscriber_count})")

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """
        Publish event to all subscribers with AT_LEAST_ONCE guarantee.

        Retry Policy: 3 attempts with exponential backoff (1s, 2s, 4s)
        Error Handling: Log error but continue to other subscribers

        Args:
            topic: Event topic
            data: Event data (must be dict)

        Raises:
            ValueError: If topic or data is invalid
        """
        if not topic or not isinstance(topic, str):
            raise ValueError("Topic must be a non-empty string")
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        if self._shutdown_requested:
            logger.warning(f"Publish blocked - EventBus shutting down (topic: {topic})")
            return

        # Protect concurrent access to _subscribers dict
        # Make a copy of subscribers while holding lock, then release before delivery
        async with self._lock:
            if topic not in self._subscribers:
                logger.debug(f"No subscribers for topic '{topic}'")
                return

            # Create snapshot of subscribers to avoid holding lock during delivery
            subscribers = list(self._subscribers[topic])

        logger.debug(f"Publishing to '{topic}' ({len(subscribers)} subscribers)")

        # W2: Track publish metrics
        self._metrics.record_publish(topic)

        # Deliver to each subscriber with retry and error isolation
        for subscriber in subscribers:
            await self._deliver_with_retry(topic, subscriber, data)

        # W2: Check thresholds and trigger alerts if needed
        await self._check_and_alert()

    async def _deliver_with_retry(
        self,
        topic: str,
        subscriber: Callable,
        data: Dict[str, Any]
    ) -> None:
        """
        Deliver event to subscriber with retry logic.

        Retry Strategy:
        - Attempt 1: Immediate
        - Attempt 2: After 1s backoff
        - Attempt 3: After 2s backoff
        - Attempt 4: After 4s backoff (total 3 retries)

        Args:
            topic: Event topic
            subscriber: Subscriber handler
            data: Event data
        """
        max_retries = 3
        retries = 0

        while retries <= max_retries:
            # W2: Track delivery start time for latency
            start_time = time()

            try:
                # Call subscriber handler
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(data)
                else:
                    # Sync handler - run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, subscriber, data)

                # W2: Record successful delivery with latency
                latency_ms = (time() - start_time) * 1000
                self._metrics.record_delivery(latency_ms)

                # Success - exit retry loop
                return

            except Exception as e:
                retries += 1

                # W2: Record retry attempt
                if retries <= max_retries:
                    self._metrics.record_retry()

                if retries > max_retries:
                    # W2: Record failure after all retries exhausted
                    self._metrics.record_failure(topic)

                    # All retries exhausted - log and move on (error isolation)
                    logger.error(
                        f"Failed to deliver to subscriber after {max_retries} attempts: "
                        f"topic={topic}, error={str(e)}"
                    )
                    return
                else:
                    # Calculate backoff: 2^(retries-1) = 1s, 2s, 4s
                    backoff = 2 ** (retries - 1)
                    logger.warning(
                        f"Delivery failed, retrying in {backoff}s... "
                        f"(attempt {retries}/{max_retries}, topic={topic})"
                    )
                    await asyncio.sleep(backoff)

    async def unsubscribe(self, topic: str, handler: Callable) -> None:
        """
        Unsubscribe handler from topic with cleanup.

        Args:
            topic: Event topic
            handler: Handler to remove
        """
        # Protect concurrent access to _subscribers dict
        async with self._lock:
            if topic in self._subscribers and handler in self._subscribers[topic]:
                self._subscribers[topic].remove(handler)
                remaining = len(self._subscribers[topic])

                logger.info(f"Unsubscribed from '{topic}' (remaining: {remaining})")

                # Cleanup empty topics (memory leak prevention)
                if remaining == 0:
                    del self._subscribers[topic]
                    logger.debug(f"Topic '{topic}' removed (no subscribers)")

    async def list_topics(self) -> List[str]:
        """
        List all active topics with subscriber counts.

        Returns:
            List of strings like "topic_name (N subscribers)"
        """
        # Protect concurrent access to _subscribers dict
        async with self._lock:
            return [
                f"{topic} ({len(subscribers)} subscribers)"
                for topic, subscribers in self._subscribers.items()
            ]

    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check for monitoring (W2 Enhanced).

        Returns EventBus state with full metrics tracking.
        Includes success rates, latency, and failure information.

        Returns:
            Dict with health status, metrics, and alerts
        """
        async with self._lock:
            active_subscribers = sum(
                len(subscribers) for subscribers in self._subscribers.values()
            )
            total_topics = len(self._subscribers)

        # P60 FIX: Detect "warming up" state before first publish
        has_data = self._metrics.total_published > 0

        # W2: Determine health based on metrics thresholds
        # P60: When no data yet, we're in unknown state (not unhealthy, but uncertain)
        if has_data:
            is_healthy = (
                not self._shutdown_requested and
                self._metrics.success_rate >= self._alert_thresholds.min_success_rate and
                self._metrics.avg_latency_ms <= self._alert_thresholds.max_avg_latency_ms
            )
        else:
            # No data yet - healthy if not shutting down, but flag as warming up
            is_healthy = not self._shutdown_requested

        # W2: Check for inactivity
        time_since_publish = time() - self._metrics.last_publish_time if self._metrics.last_publish_time > 0 else 0
        is_inactive = time_since_publish > self._alert_thresholds.max_inactivity_seconds if self._metrics.last_publish_time > 0 else False

        return {
            "healthy": is_healthy,
            "warming_up": not has_data,  # P60 FIX: Explicit warming up indicator
            "active_subscribers": active_subscribers,
            "total_topics": total_topics,
            "total_queue_size": 0,  # Simplified EventBus has no queues
            "shutdown_requested": self._shutdown_requested,
            "is_inactive": is_inactive,
            "time_since_last_publish": round(time_since_publish, 1),
            # W2: Full metrics
            "metrics": self._metrics.to_dict(),
            # W2: Thresholds for reference
            "thresholds": {
                "min_success_rate": self._alert_thresholds.min_success_rate,
                "max_avg_latency_ms": self._alert_thresholds.max_avg_latency_ms,
                "max_inactivity_seconds": self._alert_thresholds.max_inactivity_seconds
            },
            # Legacy field for backward compatibility
            "legacy_metrics": {
                "total_processed": self._metrics.total_delivered
            }
        }

    async def shutdown(self) -> None:
        """
        Cleanup all subscriptions and shutdown EventBus.

        This is explicit cleanup to prevent memory leaks.
        """
        logger.info("EventBus shutdown initiated")
        self._shutdown_requested = True

        # Protect concurrent access to _subscribers dict during shutdown
        async with self._lock:
            # Clear all subscribers (explicit cleanup)
            topic_count = len(self._subscribers)
            subscriber_count = sum(len(subs) for subs in self._subscribers.values())

            self._subscribers.clear()

        logger.info(
            f"EventBus shutdown completed: "
            f"cleared {subscriber_count} subscribers from {topic_count} topics"
        )

    # =========================================================================
    # W2 Enhancement: Alerting and Threshold Configuration
    # =========================================================================

    def register_alert_callback(self, callback: Callable[[HealthAlert], None]) -> None:
        """
        Register a callback for health alerts.

        Args:
            callback: Async or sync callable that receives HealthAlert
        """
        self._alert_callbacks.append(callback)
        logger.info(f"Alert callback registered (total: {len(self._alert_callbacks)})")

    def unregister_alert_callback(self, callback: Callable) -> None:
        """
        Unregister an alert callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
            logger.info(f"Alert callback unregistered (remaining: {len(self._alert_callbacks)})")

    def configure_thresholds(
        self,
        min_success_rate: Optional[float] = None,
        max_avg_latency_ms: Optional[float] = None,
        max_single_latency_ms: Optional[float] = None,
        max_inactivity_seconds: Optional[float] = None
    ) -> None:
        """
        Configure alert thresholds.

        Args:
            min_success_rate: Minimum acceptable success rate (0.0-1.0)
            max_avg_latency_ms: Maximum average latency in ms
            max_single_latency_ms: Maximum single delivery latency in ms
            max_inactivity_seconds: Maximum seconds without publish activity
        """
        if min_success_rate is not None:
            self._alert_thresholds.min_success_rate = min_success_rate
        if max_avg_latency_ms is not None:
            self._alert_thresholds.max_avg_latency_ms = max_avg_latency_ms
        if max_single_latency_ms is not None:
            self._alert_thresholds.max_single_latency_ms = max_single_latency_ms
        if max_inactivity_seconds is not None:
            self._alert_thresholds.max_inactivity_seconds = max_inactivity_seconds

        logger.info(
            f"Alert thresholds updated: min_success_rate={self._alert_thresholds.min_success_rate}, "
            f"max_avg_latency_ms={self._alert_thresholds.max_avg_latency_ms}"
        )

    async def _check_and_alert(self) -> None:
        """
        Check metrics against thresholds and emit alerts if needed.

        Called after each publish to detect threshold breaches.
        Rate limited to avoid performance impact (P58 FIX).
        """
        # P58 FIX: Rate limit alert checking
        current_time = time()
        if current_time - self._last_alert_check_time < self._alert_check_interval:
            return  # Skip check, too soon since last check
        self._last_alert_check_time = current_time

        # P61 FIX: Skip if already emitting alerts (prevent recursion)
        if self._in_alert_emission:
            return

        alerts = []

        # Check success rate
        if self._metrics.success_rate < self._alert_thresholds.min_success_rate:
            alerts.append(HealthAlert(
                severity="CRITICAL",
                alert_type="success_rate",
                message=f"Delivery success rate below threshold: {self._metrics.success_rate:.2%}",
                current_value=self._metrics.success_rate,
                threshold_value=self._alert_thresholds.min_success_rate
            ))

        # Check average latency
        if self._metrics.avg_latency_ms > self._alert_thresholds.max_avg_latency_ms:
            alerts.append(HealthAlert(
                severity="WARNING",
                alert_type="avg_latency",
                message=f"Average latency exceeds threshold: {self._metrics.avg_latency_ms:.1f}ms",
                current_value=self._metrics.avg_latency_ms,
                threshold_value=self._alert_thresholds.max_avg_latency_ms
            ))

        # Check max single latency
        if self._metrics.max_latency_ms > self._alert_thresholds.max_single_latency_ms:
            alerts.append(HealthAlert(
                severity="WARNING",
                alert_type="max_latency",
                message=f"Single delivery latency spike: {self._metrics.max_latency_ms:.1f}ms",
                current_value=self._metrics.max_latency_ms,
                threshold_value=self._alert_thresholds.max_single_latency_ms
            ))

        # Emit alerts to callbacks
        for alert in alerts:
            await self._emit_alert(alert)

    async def _emit_alert(self, alert: HealthAlert) -> None:
        """
        Emit alert to all registered callbacks.

        P61 FIX: Uses _in_alert_emission flag to prevent infinite recursion
        if a callback publishes back to EventBus.

        Args:
            alert: HealthAlert to emit
        """
        # P61 FIX: Set recursion guard before emitting
        self._in_alert_emission = True
        try:
            logger.warning(f"EventBus Alert: [{alert.severity}] {alert.message}")

            for callback in self._alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(alert)
                    else:
                        callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {str(e)}")
        finally:
            # P61 FIX: Always clear recursion guard
            self._in_alert_emission = False

    def get_metrics(self) -> EventBusMetrics:
        """
        Get current metrics snapshot.

        Returns:
            Current EventBusMetrics instance
        """
        return self._metrics

    def reset_metrics(self) -> None:
        """
        Reset all metrics counters.

        Useful for testing or periodic reset.
        """
        self._metrics = EventBusMetrics()
        logger.info("EventBus metrics reset")
