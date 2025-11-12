"""
Unit tests for simplified EventBus implementation.

Coverage target: 90%+
"""

import pytest
import asyncio
from src.core.event_bus import EventBus, TOPICS


class TestEventBusBasics:
    """Test basic EventBus functionality."""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """Test basic subscribe and publish flow."""
        bus = EventBus()
        received = []

        async def handler(data):
            received.append(data)

        await bus.subscribe("test_topic", handler)
        await bus.publish("test_topic", {"value": 123})

        # Wait a bit for async delivery
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0]["value"] == 123

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test multiple subscribers receive same event."""
        bus = EventBus()
        received1 = []
        received2 = []
        received3 = []

        async def handler1(data):
            received1.append(data)

        async def handler2(data):
            received2.append(data)

        async def handler3(data):
            received3.append(data)

        await bus.subscribe("test", handler1)
        await bus.subscribe("test", handler2)
        await bus.subscribe("test", handler3)

        await bus.publish("test", {"value": 42})
        await asyncio.sleep(0.1)

        assert len(received1) == 1
        assert len(received2) == 1
        assert len(received3) == 1
        assert received1[0]["value"] == 42
        assert received2[0]["value"] == 42
        assert received3[0]["value"] == 42

    @pytest.mark.asyncio
    async def test_no_subscribers(self):
        """Test publishing to topic with no subscribers."""
        bus = EventBus()

        # Should not raise exception
        await bus.publish("no_subscribers", {"value": 1})

    @pytest.mark.asyncio
    async def test_unsubscribe_cleanup(self):
        """Test unsubscribe removes handler and cleans up empty topics."""
        bus = EventBus()
        received = []

        async def handler(data):
            received.append(data)

        # Subscribe
        await bus.subscribe("test", handler)
        assert "test" in bus._subscribers

        # Unsubscribe
        await bus.unsubscribe("test", handler)

        # Topic should be cleaned up (no subscribers left)
        assert "test" not in bus._subscribers

        # Publishing should not deliver
        await bus.publish("test", {"value": 1})
        await asyncio.sleep(0.1)

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_list_topics(self):
        """Test listing active topics with subscriber counts."""
        bus = EventBus()

        async def handler1(data):
            pass

        async def handler2(data):
            pass

        await bus.subscribe("topic1", handler1)
        await bus.subscribe("topic2", handler1)
        await bus.subscribe("topic2", handler2)

        topics = await bus.list_topics()

        assert len(topics) == 2
        assert "topic1 (1 subscribers)" in topics
        assert "topic2 (2 subscribers)" in topics


class TestEventBusRetry:
    """Test retry logic and error handling."""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry mechanism with exponential backoff."""
        bus = EventBus()
        attempts = []

        async def failing_handler(data):
            attempts.append(1)
            if len(attempts) < 2:  # Fail first attempt, succeed on second
                raise ValueError("Simulated failure")

        await bus.subscribe("test", failing_handler)

        # Should succeed on retry
        await bus.publish("test", {"value": 1})

        # Wait for retry (1s backoff)
        await asyncio.sleep(1.5)

        # Should have made 2 attempts (initial + 1 retry)
        assert len(attempts) == 2

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self):
        """Test that delivery stops after max retries."""
        bus = EventBus()
        attempts = []

        async def always_failing_handler(data):
            attempts.append(1)
            raise ValueError("Always fails")

        await bus.subscribe("test", always_failing_handler)

        # Should try 4 times total (initial + 3 retries)
        await bus.publish("test", {"value": 1})

        # Wait for all retries (1s + 2s + 4s = 7s)
        await asyncio.sleep(8)

        # Should have made exactly 4 attempts
        assert len(attempts) == 4

    @pytest.mark.asyncio
    async def test_subscriber_error_isolation(self):
        """Test that one subscriber's failure doesn't affect others."""
        bus = EventBus()
        received_good1 = []
        received_good2 = []

        async def failing_handler(data):
            raise ValueError("I always fail")

        async def good_handler1(data):
            received_good1.append(data)

        async def good_handler2(data):
            received_good2.append(data)

        # Subscribe in order: good, failing, good
        await bus.subscribe("test", good_handler1)
        await bus.subscribe("test", failing_handler)
        await bus.subscribe("test", good_handler2)

        # Publish event
        await bus.publish("test", {"value": 123})

        # Wait for all deliveries (including retries)
        await asyncio.sleep(8)

        # Both good handlers should have received the event
        assert len(received_good1) == 1
        assert len(received_good2) == 1
        assert received_good1[0]["value"] == 123
        assert received_good2[0]["value"] == 123


class TestEventBusMemoryLeak:
    """Test memory leak prevention."""

    @pytest.mark.asyncio
    async def test_no_memory_leak(self):
        """Test 10k subscribe/unsubscribe cycles don't leak memory."""
        bus = EventBus()

        async def handler(data):
            pass

        # 10,000 subscribe/unsubscribe cycles
        for i in range(10000):
            topic = f"topic_{i % 100}"  # Reuse 100 topics
            await bus.subscribe(topic, handler)
            await bus.unsubscribe(topic, handler)

        # All topics should be cleaned up
        assert len(bus._subscribers) == 0

    @pytest.mark.asyncio
    async def test_topic_cleanup_on_empty(self):
        """Test that topics are removed when last subscriber unsubscribes."""
        bus = EventBus()

        async def handler1(data):
            pass

        async def handler2(data):
            pass

        # Add two subscribers
        await bus.subscribe("test", handler1)
        await bus.subscribe("test", handler2)
        assert "test" in bus._subscribers
        assert len(bus._subscribers["test"]) == 2

        # Remove first subscriber
        await bus.unsubscribe("test", handler1)
        assert "test" in bus._subscribers
        assert len(bus._subscribers["test"]) == 1

        # Remove second subscriber - topic should be cleaned up
        await bus.unsubscribe("test", handler2)
        assert "test" not in bus._subscribers


class TestEventBusConcurrency:
    """Test concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_publish(self):
        """Test 100 events published in parallel."""
        bus = EventBus()
        received = []
        lock = asyncio.Lock()

        async def handler(data):
            async with lock:
                received.append(data)

        await bus.subscribe("test", handler)

        # Publish 100 events concurrently
        tasks = [
            bus.publish("test", {"value": i})
            for i in range(100)
        ]

        await asyncio.gather(*tasks)
        await asyncio.sleep(0.5)

        # All events should be received
        assert len(received) == 100

        # Check all values present
        values = sorted([r["value"] for r in received])
        assert values == list(range(100))

    @pytest.mark.asyncio
    async def test_concurrent_subscribe_publish(self):
        """Test concurrent subscribe and publish operations."""
        bus = EventBus()
        received = []
        lock = asyncio.Lock()

        async def handler(data):
            async with lock:
                received.append(data)

        async def subscribe_task():
            for i in range(10):
                await bus.subscribe("test", handler)
                await asyncio.sleep(0.01)

        async def publish_task():
            for i in range(10):
                await bus.publish("test", {"value": i})
                await asyncio.sleep(0.01)

        # Run subscribe and publish concurrently
        await asyncio.gather(subscribe_task(), publish_task())
        await asyncio.sleep(0.5)

        # Should have received events (exact count depends on timing)
        assert len(received) > 0


class TestEventBusShutdown:
    """Test shutdown behavior."""

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test graceful shutdown clears all subscribers."""
        bus = EventBus()

        async def handler(data):
            pass

        # Add subscribers
        await bus.subscribe("topic1", handler)
        await bus.subscribe("topic2", handler)

        assert len(bus._subscribers) == 2

        # Shutdown
        await bus.shutdown()

        # All subscribers should be cleared
        assert len(bus._subscribers) == 0
        assert bus._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_publish_after_shutdown(self):
        """Test that publish is blocked after shutdown."""
        bus = EventBus()
        received = []

        async def handler(data):
            received.append(data)

        await bus.subscribe("test", handler)

        # Shutdown
        await bus.shutdown()

        # Publish should be blocked
        await bus.publish("test", {"value": 1})
        await asyncio.sleep(0.1)

        # Should not have received anything
        assert len(received) == 0


class TestEventBusValidation:
    """Test input validation."""

    @pytest.mark.asyncio
    async def test_subscribe_invalid_topic(self):
        """Test subscribe with invalid topic."""
        bus = EventBus()

        async def handler(data):
            pass

        with pytest.raises(ValueError, match="Topic must be a non-empty string"):
            await bus.subscribe("", handler)

        with pytest.raises(ValueError, match="Topic must be a non-empty string"):
            await bus.subscribe(None, handler)

    @pytest.mark.asyncio
    async def test_subscribe_invalid_handler(self):
        """Test subscribe with invalid handler."""
        bus = EventBus()

        with pytest.raises(ValueError, match="Handler must be callable"):
            await bus.subscribe("test", "not a callable")

        with pytest.raises(ValueError, match="Handler must be callable"):
            await bus.subscribe("test", None)

    @pytest.mark.asyncio
    async def test_publish_invalid_topic(self):
        """Test publish with invalid topic."""
        bus = EventBus()

        with pytest.raises(ValueError, match="Topic must be a non-empty string"):
            await bus.publish("", {"value": 1})

        with pytest.raises(ValueError, match="Topic must be a non-empty string"):
            await bus.publish(None, {"value": 1})

    @pytest.mark.asyncio
    async def test_publish_invalid_data(self):
        """Test publish with invalid data."""
        bus = EventBus()

        with pytest.raises(ValueError, match="Data must be a dictionary"):
            await bus.publish("test", "not a dict")

        with pytest.raises(ValueError, match="Data must be a dictionary"):
            await bus.publish("test", None)


class TestEventTopics:
    """Test event topics definition."""

    def test_topics_constant_exists(self):
        """Test that TOPICS constant is defined."""
        assert TOPICS is not None
        assert isinstance(TOPICS, dict)

    def test_topics_has_required_events(self):
        """Test that all required event topics are defined."""
        required_topics = [
            "market_data",
            "indicator_updated",
            "signal_generated",
            "order_created",
            "order_filled",
            "position_updated",
            "risk_alert"
        ]

        for topic in required_topics:
            assert topic in TOPICS, f"Missing required topic: {topic}"

    def test_topics_structure(self):
        """Test that each topic has proper structure."""
        for topic_name, topic_info in TOPICS.items():
            assert "description" in topic_info, f"Topic {topic_name} missing description"
            assert "data_structure" in topic_info, f"Topic {topic_name} missing data_structure"
            assert isinstance(topic_info["data_structure"], dict), f"Topic {topic_name} data_structure must be dict"


class TestSyncHandlers:
    """Test synchronous handlers support."""

    @pytest.mark.asyncio
    async def test_sync_handler(self):
        """Test that synchronous handlers are supported."""
        bus = EventBus()
        received = []

        def sync_handler(data):
            """Synchronous handler."""
            received.append(data)

        await bus.subscribe("test", sync_handler)
        await bus.publish("test", {"value": 42})
        await asyncio.sleep(0.2)

        assert len(received) == 1
        assert received[0]["value"] == 42


class TestEventBusHealthCheck:
    """Test health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_basic(self):
        """Test basic health check returns correct structure."""
        bus = EventBus()

        async def handler(data):
            pass

        # Subscribe to some topics
        await bus.subscribe("topic1", handler)
        await bus.subscribe("topic2", handler)
        await bus.subscribe("topic2", handler)  # Second subscriber

        health = await bus.health_check()

        # Check structure
        assert "healthy" in health
        assert "active_subscribers" in health
        assert "total_topics" in health
        assert "total_queue_size" in health
        assert "shutdown_requested" in health
        assert "metrics" in health

        # Check values
        assert health["healthy"] is True
        assert health["active_subscribers"] == 3  # 1 + 2
        assert health["total_topics"] == 2
        assert health["shutdown_requested"] is False

    @pytest.mark.asyncio
    async def test_health_check_after_shutdown(self):
        """Test health check after shutdown."""
        bus = EventBus()

        async def handler(data):
            pass

        await bus.subscribe("test", handler)
        await bus.shutdown()

        health = await bus.health_check()

        assert health["healthy"] is False
        assert health["shutdown_requested"] is True
        assert health["active_subscribers"] == 0  # Cleared on shutdown

    @pytest.mark.asyncio
    async def test_health_check_no_subscribers(self):
        """Test health check with no subscribers."""
        bus = EventBus()

        health = await bus.health_check()

        assert health["healthy"] is True
        assert health["active_subscribers"] == 0
        assert health["total_topics"] == 0
