"""
Tests for StateMachineBroadcaster
=================================
Verifies real-time state machine event broadcasting via WebSocket.

Part of BUG-007 fix: ADR-002 Backend Must Broadcast State Machine Events
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.api.websocket.broadcasters.state_machine_broadcaster import StateMachineBroadcaster
from src.core.event_bus import EventBus


@pytest.fixture
def mock_subscription_manager():
    """Create mock SubscriptionManager"""
    manager = MagicMock()
    manager.get_subscribers = MagicMock(return_value=["client_1", "client_2"])
    return manager


@pytest.fixture
def mock_connection_manager():
    """Create mock ConnectionManager"""
    manager = MagicMock()
    manager.send_to_client = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_event_bus():
    """Create mock EventBus"""
    bus = MagicMock(spec=EventBus)
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    return bus


@pytest.fixture
def mock_logger():
    """Create mock logger"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def broadcaster(mock_subscription_manager, mock_connection_manager, mock_logger):
    """Create StateMachineBroadcaster instance without event_bus"""
    return StateMachineBroadcaster(
        subscription_manager=mock_subscription_manager,
        connection_manager=mock_connection_manager,
        logger=mock_logger
    )


@pytest.fixture
def broadcaster_with_event_bus(mock_subscription_manager, mock_connection_manager, mock_event_bus, mock_logger):
    """Create StateMachineBroadcaster instance with event_bus"""
    return StateMachineBroadcaster(
        subscription_manager=mock_subscription_manager,
        connection_manager=mock_connection_manager,
        event_bus=mock_event_bus,
        logger=mock_logger
    )


class TestStateMachineBroadcasterInitialization:
    """Test broadcaster initialization and lifecycle"""

    def test_initialization_without_event_bus(self, broadcaster):
        """Verify broadcaster initializes correctly without event_bus"""
        assert broadcaster.subscription_manager is not None
        assert broadcaster.connection_manager is not None
        assert broadcaster.event_bus is None
        assert broadcaster._is_running is False
        assert broadcaster.total_broadcasts == 0

    def test_initialization_with_event_bus(self, broadcaster_with_event_bus, mock_event_bus):
        """Verify broadcaster initializes correctly with event_bus"""
        assert broadcaster_with_event_bus.event_bus is mock_event_bus
        assert broadcaster_with_event_bus._is_running is False

    @pytest.mark.asyncio
    async def test_start_subscribes_to_events(self, broadcaster_with_event_bus, mock_event_bus):
        """Verify broadcaster subscribes to session events on start"""
        await broadcaster_with_event_bus.start()

        assert mock_event_bus.subscribe.call_count == 2
        subscribed_topics = [call[0][0] for call in mock_event_bus.subscribe.call_args_list]
        assert "session.started" in subscribed_topics
        assert "session.stopped" in subscribed_topics
        assert broadcaster_with_event_bus._is_running is True

    @pytest.mark.asyncio
    async def test_start_without_event_bus_logs_warning(self, broadcaster, mock_logger):
        """Verify broadcaster logs warning when started without event_bus"""
        await broadcaster.start()

        mock_logger.warning.assert_called()
        assert broadcaster._is_running is False

    @pytest.mark.asyncio
    async def test_stop_unsubscribes_from_events(self, broadcaster_with_event_bus, mock_event_bus):
        """Verify broadcaster unsubscribes from events on stop"""
        await broadcaster_with_event_bus.start()
        await broadcaster_with_event_bus.stop()

        assert mock_event_bus.unsubscribe.call_count == 2
        assert broadcaster_with_event_bus._is_running is False

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self, broadcaster_with_event_bus, mock_event_bus):
        """Verify calling start twice doesn't double-subscribe"""
        await broadcaster_with_event_bus.start()
        await broadcaster_with_event_bus.start()  # Second call

        # Should only subscribe once
        assert mock_event_bus.subscribe.call_count == 2  # 2 topics, not 4


class TestBroadcastMethods:
    """Test broadcast methods"""

    @pytest.mark.asyncio
    async def test_broadcast_state_change(self, broadcaster, mock_connection_manager):
        """Verify state_change broadcast sends to all subscribers"""
        sent_count = await broadcaster.broadcast_state_change(
            session_id="session_123",
            data={"state": "ACTIVE", "previous_state": "IDLE"}
        )

        assert sent_count == 2
        assert mock_connection_manager.send_to_client.call_count == 2

        # Verify message structure
        call_args = mock_connection_manager.send_to_client.call_args_list[0]
        message = call_args[0][1]
        assert message["type"] == "state_change"
        assert message["stream"] == "state_machines"
        assert message["session_id"] == "session_123"
        assert message["data"]["state"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_broadcast_instance_added(self, broadcaster, mock_connection_manager):
        """Verify instance_added broadcast sends correct data"""
        instance_data = {
            "instance_id": "inst_1",
            "strategy_name": "MACD_Strategy"
        }

        sent_count = await broadcaster.broadcast_instance_added(
            session_id="session_123",
            instance_data=instance_data
        )

        assert sent_count == 2
        call_args = mock_connection_manager.send_to_client.call_args_list[0]
        message = call_args[0][1]
        assert message["type"] == "instance_added"
        assert message["data"]["instance_id"] == "inst_1"

    @pytest.mark.asyncio
    async def test_broadcast_instance_removed(self, broadcaster, mock_connection_manager):
        """Verify instance_removed broadcast sends correct data"""
        sent_count = await broadcaster.broadcast_instance_removed(
            session_id="session_123",
            instance_id="inst_1"
        )

        assert sent_count == 2
        call_args = mock_connection_manager.send_to_client.call_args_list[0]
        message = call_args[0][1]
        assert message["type"] == "instance_removed"
        assert message["data"]["instance_id"] == "inst_1"

    @pytest.mark.asyncio
    async def test_broadcast_full_update_to_specific_client(self, broadcaster, mock_connection_manager):
        """Verify full_update sends to specific client only"""
        instances = [
            {"instance_id": "inst_1", "state": "ACTIVE"},
            {"instance_id": "inst_2", "state": "IDLE"}
        ]

        success = await broadcaster.broadcast_full_update(
            client_id="client_1",
            session_id="session_123",
            instances=instances
        )

        assert success is True
        assert mock_connection_manager.send_to_client.call_count == 1

        call_args = mock_connection_manager.send_to_client.call_args
        assert call_args[0][0] == "client_1"  # Target client
        message = call_args[0][1]
        assert message["type"] == "full_update"
        assert len(message["data"]["instances"]) == 2

    @pytest.mark.asyncio
    async def test_broadcast_no_subscribers(self, broadcaster, mock_subscription_manager, mock_connection_manager):
        """Verify broadcast handles no subscribers gracefully"""
        mock_subscription_manager.get_subscribers.return_value = []

        sent_count = await broadcaster.broadcast_state_change(
            session_id="session_123",
            data={"state": "ACTIVE"}
        )

        assert sent_count == 0
        assert mock_connection_manager.send_to_client.call_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_handles_send_failure(self, broadcaster, mock_connection_manager):
        """Verify broadcast handles send failures gracefully"""
        mock_connection_manager.send_to_client = AsyncMock(
            side_effect=[True, False]  # First succeeds, second fails
        )

        sent_count = await broadcaster.broadcast_state_change(
            session_id="session_123",
            data={"state": "ACTIVE"}
        )

        assert sent_count == 1  # Only one succeeded
        assert broadcaster.total_failures == 1


class TestEventHandlers:
    """Test event bus handlers"""

    @pytest.mark.asyncio
    async def test_on_session_started_broadcasts(self, broadcaster_with_event_bus, mock_connection_manager):
        """Verify session.started event triggers instance_added broadcast"""
        await broadcaster_with_event_bus.start()

        # Simulate session.started event
        session_data = {
            "session_id": "session_123",
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "mode": "paper",
            "state": "ACTIVE",
            "client_id": "client_1"
        }
        await broadcaster_with_event_bus._on_session_started(session_data)

        assert mock_connection_manager.send_to_client.call_count == 2
        call_args = mock_connection_manager.send_to_client.call_args_list[0]
        message = call_args[0][1]
        assert message["type"] == "instance_added"
        assert message["data"]["session_id"] == "session_123"
        assert message["data"]["symbols"] == ["BTCUSDT", "ETHUSDT"]

    @pytest.mark.asyncio
    async def test_on_session_stopped_broadcasts(self, broadcaster_with_event_bus, mock_connection_manager):
        """Verify session.stopped event triggers instance_removed broadcast"""
        await broadcaster_with_event_bus.start()

        session_data = {"session_id": "session_123"}
        await broadcaster_with_event_bus._on_session_stopped(session_data)

        assert mock_connection_manager.send_to_client.call_count == 2
        call_args = mock_connection_manager.send_to_client.call_args_list[0]
        message = call_args[0][1]
        assert message["type"] == "instance_removed"

    @pytest.mark.asyncio
    async def test_on_session_started_missing_id(self, broadcaster_with_event_bus, mock_connection_manager, mock_logger):
        """Verify handler handles missing session_id gracefully"""
        await broadcaster_with_event_bus.start()

        await broadcaster_with_event_bus._on_session_started({})  # No session_id

        mock_logger.warning.assert_called()
        assert mock_connection_manager.send_to_client.call_count == 0


class TestMetrics:
    """Test metrics tracking"""

    @pytest.mark.asyncio
    async def test_stats_tracking(self, broadcaster, mock_connection_manager):
        """Verify stats are tracked correctly"""
        await broadcaster.broadcast_state_change("s1", {"state": "A"})
        await broadcaster.broadcast_instance_added("s1", {"id": "1"})

        stats = broadcaster.get_stats()

        assert stats["total_broadcasts"] == 2
        assert stats["total_messages_sent"] == 4  # 2 clients * 2 broadcasts
        assert stats["success_rate"] == 1.0
        assert stats["is_running"] is False

    @pytest.mark.asyncio
    async def test_failure_tracking(self, broadcaster, mock_connection_manager):
        """Verify failures are tracked"""
        mock_connection_manager.send_to_client = AsyncMock(return_value=False)

        await broadcaster.broadcast_state_change("s1", {"state": "A"})

        stats = broadcaster.get_stats()
        assert stats["total_failures"] == 2
        assert stats["total_messages_sent"] == 0
        assert stats["success_rate"] == 0.0
