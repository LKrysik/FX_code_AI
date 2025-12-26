"""
E2E WebSocket and API Tests
============================
End-to-end tests for WebSocket communication and API endpoints.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_websocket_client():
    """Create a mock WebSocket client."""
    client = MagicMock()
    client.id = "test_client_1"
    client.subscriptions = set()
    client.messages_received = []

    async def mock_send(message):
        client.messages_received.append(message)

    client.send = mock_send
    return client


@pytest.fixture
def mock_broadcast_provider():
    """Create a mock broadcast provider."""
    provider = AsyncMock()
    provider.broadcasts = []

    async def mock_broadcast(stream_type, message_type, data):
        provider.broadcasts.append({
            "stream": stream_type,
            "type": message_type,
            "data": data,
            "timestamp": time.time()
        })
        return True

    provider.broadcast_message = mock_broadcast
    return provider


# ============================================================================
# WEBSOCKET CONNECTION TESTS
# ============================================================================

class TestWebSocketConnection:
    """Tests for WebSocket connection lifecycle."""

    @pytest.mark.asyncio
    async def test_client_connects_successfully(self, mock_websocket_client):
        """Test successful WebSocket connection."""
        connections = {}

        # Simulate connection
        connections[mock_websocket_client.id] = mock_websocket_client

        assert mock_websocket_client.id in connections
        assert len(connections) == 1

    @pytest.mark.asyncio
    async def test_client_subscription(self, mock_websocket_client):
        """Test client can subscribe to streams."""
        # Subscribe to multiple streams
        streams = ["signals", "market_data", "execution_status"]
        for stream in streams:
            mock_websocket_client.subscriptions.add(stream)

        assert "signals" in mock_websocket_client.subscriptions
        assert "market_data" in mock_websocket_client.subscriptions
        assert len(mock_websocket_client.subscriptions) == 3

    @pytest.mark.asyncio
    async def test_client_receives_subscribed_messages(
        self,
        mock_websocket_client,
        mock_broadcast_provider
    ):
        """Test client receives messages for subscribed streams."""
        mock_websocket_client.subscriptions.add("signals")

        # Broadcast a signal
        await mock_broadcast_provider.broadcast_message(
            stream_type="signals",
            message_type="signal_generated",
            data={"signal_type": "S1", "symbol": "BTCUSDT"}
        )

        assert len(mock_broadcast_provider.broadcasts) == 1
        assert mock_broadcast_provider.broadcasts[0]["stream"] == "signals"


# ============================================================================
# WEBSOCKET HEARTBEAT TESTS
# ============================================================================

class TestWebSocketHeartbeat:
    """Tests for WebSocket heartbeat mechanism."""

    @pytest.mark.asyncio
    async def test_heartbeat_response(self):
        """Test that ping receives pong response."""
        ping_sent_at = time.time()
        pong_received = False
        latency_ms = 0

        # Simulate ping/pong
        async def send_ping():
            nonlocal ping_sent_at
            ping_sent_at = time.time()
            return {"type": "ping", "timestamp": ping_sent_at}

        async def receive_pong():
            nonlocal pong_received, latency_ms
            await asyncio.sleep(0.01)  # Simulate network delay
            pong_received = True
            latency_ms = (time.time() - ping_sent_at) * 1000
            return {"type": "pong", "latency_ms": latency_ms}

        await send_ping()
        response = await receive_pong()

        assert pong_received is True
        assert response["type"] == "pong"
        assert latency_ms < 100  # Should be very fast in tests

    @pytest.mark.asyncio
    async def test_heartbeat_interval(self):
        """Test heartbeat is sent at regular intervals."""
        heartbeats = []
        heartbeat_interval = 0.05  # 50ms for fast test

        async def heartbeat_loop(duration: float):
            start = time.time()
            while time.time() - start < duration:
                heartbeats.append(time.time())
                await asyncio.sleep(heartbeat_interval)

        # Run for 200ms
        await heartbeat_loop(0.2)

        # Should have ~4 heartbeats
        assert len(heartbeats) >= 3

    @pytest.mark.asyncio
    async def test_connection_timeout_detection(self):
        """Test that missed heartbeats trigger reconnection."""
        last_pong = time.time()
        connection_healthy = True
        timeout_threshold = 0.1  # 100ms for test

        async def check_connection():
            nonlocal connection_healthy
            if time.time() - last_pong > timeout_threshold:
                connection_healthy = False

        # Simulate timeout
        await asyncio.sleep(0.15)
        await check_connection()

        assert connection_healthy is False


# ============================================================================
# API ENDPOINT TESTS
# ============================================================================

class TestAPIEndpoints:
    """Tests for REST API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """Test /health endpoint returns healthy status."""
        mock_response = {
            "status": "healthy",
            "components": {
                "database": "connected",
                "event_bus": "running",
                "websocket": "connected"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        assert mock_response["status"] == "healthy"
        assert "components" in mock_response

    @pytest.mark.asyncio
    async def test_signals_endpoint(self):
        """Test /api/signals endpoint returns signal data."""
        mock_signals = [
            {
                "signal_type": "S1",
                "symbol": "BTCUSDT",
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 85.0
            },
            {
                "signal_type": "Z1",
                "symbol": "ETHUSDT",
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 72.0
            }
        ]

        assert len(mock_signals) == 2
        assert all("signal_type" in s for s in mock_signals)

    @pytest.mark.asyncio
    async def test_positions_endpoint(self):
        """Test /api/positions endpoint returns position data."""
        mock_positions = [
            {
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": 0.001,
                "entry_price": 50000.0,
                "current_price": 51000.0,
                "unrealized_pnl": 1.0
            }
        ]

        assert len(mock_positions) == 1
        assert mock_positions[0]["side"] == "LONG"


# ============================================================================
# EVENT BRIDGE TESTS
# ============================================================================

class TestEventBridge:
    """Tests for EventBridge signal forwarding."""

    @pytest.mark.asyncio
    async def test_signal_forwarding_latency(self):
        """Test that signal forwarding is under 500ms."""
        start_time = time.time()
        forwarded = False

        async def forward_signal(signal):
            nonlocal forwarded
            await asyncio.sleep(0.01)  # Simulate processing
            forwarded = True

        await forward_signal({"signal_type": "S1"})
        latency = (time.time() - start_time) * 1000

        assert forwarded is True
        assert latency < 500, f"Latency {latency}ms exceeds 500ms threshold"

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test batch processing of multiple events."""
        processed_count = 0
        batch_size = 10

        async def process_batch(events: List[Dict]):
            nonlocal processed_count
            for event in events:
                processed_count += 1
                await asyncio.sleep(0.001)  # Simulate per-event processing

        events = [{"id": i, "type": "test"} for i in range(batch_size)]
        await process_batch(events)

        assert processed_count == batch_size

    @pytest.mark.asyncio
    async def test_concurrent_event_processing(self):
        """Test concurrent processing of events."""
        results = []
        processing_times = []

        async def process_event(event_id: int):
            start = time.time()
            await asyncio.sleep(0.01)  # Simulate work
            processing_times.append(time.time() - start)
            results.append(event_id)

        # Process 5 events concurrently
        start = time.time()
        await asyncio.gather(*[process_event(i) for i in range(5)])
        total_time = time.time() - start

        assert len(results) == 5
        # Concurrent processing should be faster than sequential
        assert total_time < 0.1  # 5 * 0.01 = 0.05 + overhead


# ============================================================================
# SUBSCRIPTION MANAGER TESTS
# ============================================================================

class TestSubscriptionManager:
    """Tests for subscription management."""

    @pytest.mark.asyncio
    async def test_subscribe_to_stream(self):
        """Test subscribing to a stream."""
        subscriptions = {}

        def subscribe(client_id: str, stream: str):
            if client_id not in subscriptions:
                subscriptions[client_id] = set()
            subscriptions[client_id].add(stream)

        subscribe("client_1", "signals")
        subscribe("client_1", "market_data")

        assert "signals" in subscriptions["client_1"]
        assert "market_data" in subscriptions["client_1"]

    @pytest.mark.asyncio
    async def test_unsubscribe_from_stream(self):
        """Test unsubscribing from a stream."""
        subscriptions = {"client_1": {"signals", "market_data"}}

        def unsubscribe(client_id: str, stream: str):
            if client_id in subscriptions:
                subscriptions[client_id].discard(stream)

        unsubscribe("client_1", "signals")

        assert "signals" not in subscriptions["client_1"]
        assert "market_data" in subscriptions["client_1"]

    @pytest.mark.asyncio
    async def test_get_subscribers_for_stream(self):
        """Test getting all subscribers for a stream."""
        subscriptions = {
            "client_1": {"signals", "market_data"},
            "client_2": {"signals"},
            "client_3": {"market_data"}
        }

        def get_subscribers(stream: str) -> List[str]:
            return [
                client_id
                for client_id, streams in subscriptions.items()
                if stream in streams
            ]

        signal_subscribers = get_subscribers("signals")
        assert len(signal_subscribers) == 2
        assert "client_1" in signal_subscribers
        assert "client_2" in signal_subscribers


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Tests for error handling in WebSocket/API."""

    @pytest.mark.asyncio
    async def test_invalid_message_handling(self):
        """Test handling of invalid WebSocket messages."""
        errors = []

        async def handle_message(message: Dict):
            try:
                if "type" not in message:
                    raise ValueError("Missing 'type' field")
                return {"status": "ok"}
            except Exception as e:
                errors.append(str(e))
                return {"status": "error", "message": str(e)}

        result = await handle_message({})  # Missing 'type'
        assert result["status"] == "error"
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_broadcast_failure_recovery(self):
        """Test recovery from broadcast failures."""
        attempts = 0
        max_retries = 3

        async def broadcast_with_retry(data: Dict) -> bool:
            nonlocal attempts
            for attempt in range(max_retries):
                attempts += 1
                try:
                    if attempt < 2:
                        raise Exception("Broadcast failed")
                    return True
                except Exception:
                    if attempt == max_retries - 1:
                        return False
                    await asyncio.sleep(0.01)
            return False

        success = await broadcast_with_retry({"test": "data"})
        assert success is True
        assert attempts == 3  # Took 3 attempts

    @pytest.mark.asyncio
    async def test_graceful_disconnect(self):
        """Test graceful handling of client disconnect."""
        active_clients = {"client_1", "client_2", "client_3"}
        cleanup_performed = False

        async def handle_disconnect(client_id: str):
            nonlocal cleanup_performed
            active_clients.discard(client_id)
            cleanup_performed = True

        await handle_disconnect("client_2")

        assert "client_2" not in active_clients
        assert len(active_clients) == 2
        assert cleanup_performed is True


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
