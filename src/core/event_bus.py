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
    """

    def __init__(self):
        """Initialize EventBus with memory-safe structures."""
        # CRITICAL: Use explicit Dict, NOT defaultdict (memory leak prevention)
        self._subscribers: Dict[str, List[Callable]] = {}
        self._shutdown_requested = False
        # Lock to protect concurrent access to _subscribers dict
        self._lock = asyncio.Lock()

        logger.info("EventBus initialized (simplified, AT_LEAST_ONCE delivery)")

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

        # Deliver to each subscriber with retry and error isolation
        for subscriber in subscribers:
            await self._deliver_with_retry(topic, subscriber, data)

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
            try:
                # Call subscriber handler
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(data)
                else:
                    # Sync handler - run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, subscriber, data)

                # Success - exit retry loop
                return

            except Exception as e:
                retries += 1

                if retries > max_retries:
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
        Minimal health check for monitoring.

        Returns basic EventBus state without complex metrics.
        Simplified version - does not track queues or processing rates.

        Returns:
            Dict with health status and subscriber count
        """
        async with self._lock:
            active_subscribers = sum(
                len(subscribers) for subscribers in self._subscribers.values()
            )
            total_topics = len(self._subscribers)

        return {
            "healthy": not self._shutdown_requested,
            "active_subscribers": active_subscribers,
            "total_topics": total_topics,
            "total_queue_size": 0,  # Simplified EventBus has no queues
            "shutdown_requested": self._shutdown_requested,
            # Legacy fields for backward compatibility (execution_monitor expects these)
            "metrics": {
                "total_processed": 0  # Not tracked in simplified version
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
