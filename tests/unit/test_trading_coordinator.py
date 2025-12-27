"""
Tests for TradingCoordinator - Mediator Pattern Implementation
==============================================================
Verifies the circular dependency elimination and proper coordination.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.trading.trading_coordinator import TradingCoordinator, SubscriptionState
from src.domain.interfaces.coordination import SubscriptionDecision
from src.core.event_bus import EventBus


@pytest.fixture
def mock_event_bus():
    """Create mock EventBus for testing"""
    bus = MagicMock(spec=EventBus)
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    bus.publish = AsyncMock()
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
async def coordinator(mock_event_bus, mock_logger):
    """Create TradingCoordinator instance for testing"""
    coord = TradingCoordinator(
        event_bus=mock_event_bus,
        logger=mock_logger,
        rate_limit_per_minute=10,
        default_decision_timeout=1.0
    )
    await coord.start()
    yield coord
    await coord.stop()


class TestTradingCoordinatorInitialization:
    """Test coordinator initialization and lifecycle"""

    @pytest.mark.asyncio
    async def test_start_subscribes_to_event_bus(self, mock_event_bus, mock_logger):
        """Verify coordinator subscribes to required EventBus topics on start"""
        coordinator = TradingCoordinator(
            event_bus=mock_event_bus,
            logger=mock_logger
        )

        await coordinator.start()

        # Verify subscriptions
        assert mock_event_bus.subscribe.call_count >= 4
        subscribed_topics = [call[0][0] for call in mock_event_bus.subscribe.call_args_list]
        assert "session.registered" in subscribed_topics
        assert "session.started" in subscribed_topics
        assert "session.stopped" in subscribed_topics
        assert "subscription.check_response" in subscribed_topics

        await coordinator.stop()

    @pytest.mark.asyncio
    async def test_stop_unsubscribes_from_event_bus(self, mock_event_bus, mock_logger):
        """Verify coordinator unsubscribes from EventBus topics on stop"""
        coordinator = TradingCoordinator(
            event_bus=mock_event_bus,
            logger=mock_logger
        )

        await coordinator.start()
        await coordinator.stop()

        # Verify unsubscriptions
        assert mock_event_bus.unsubscribe.call_count >= 4

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self, coordinator):
        """Verify health check returns proper status"""
        health = await coordinator.health_check()

        assert health["healthy"] is True
        assert "session_manager_registered" in health
        assert "active_sessions" in health
        assert "pending_requests" in health


class TestSubscriptionCoordination:
    """Test subscription request handling"""

    @pytest.mark.asyncio
    async def test_request_subscription_without_session_manager_allows(self, coordinator):
        """When no session manager registered, allow subscription (graceful degradation)"""
        decision = await coordinator.request_subscription("BTCUSDT")

        assert decision == SubscriptionDecision.ALLOWED

    @pytest.mark.asyncio
    async def test_rate_limiting_blocks_excessive_requests(self, mock_event_bus, mock_logger):
        """Verify rate limiting blocks excessive subscription requests"""
        coordinator = TradingCoordinator(
            event_bus=mock_event_bus,
            logger=mock_logger,
            rate_limit_per_minute=3  # Very low limit for testing
        )
        await coordinator.start()

        # Make requests up to limit
        for i in range(3):
            decision = await coordinator.request_subscription(f"SYMBOL{i}")
            assert decision == SubscriptionDecision.ALLOWED

        # Next request should be rate limited
        decision = await coordinator.request_subscription("SYMBOL_BLOCKED")
        assert decision == SubscriptionDecision.DENIED_RATE_LIMIT

        await coordinator.stop()

    @pytest.mark.asyncio
    async def test_notify_subscription_success_tracks_state(self, coordinator):
        """Verify subscription success is tracked"""
        await coordinator.notify_subscription_success("BTCUSDT")

        symbols = await coordinator.get_active_symbols()
        assert "BTCUSDT" in symbols

    @pytest.mark.asyncio
    async def test_notify_subscription_failure_tracks_count(self, coordinator):
        """Verify subscription failure count is tracked"""
        await coordinator.notify_subscription_failure("BTCUSDT", "Connection failed")
        await coordinator.notify_subscription_failure("BTCUSDT", "Timeout")

        # Subscription state should track failures
        state = coordinator._subscriptions.get("BTCUSDT")
        assert state is not None
        assert state.failure_count == 2


class TestEventBusHandlers:
    """Test EventBus event handlers"""

    @pytest.mark.asyncio
    async def test_session_registered_handler(self, coordinator):
        """Verify session manager registration is tracked"""
        await coordinator._on_session_manager_registered({
            "component": "session_manager"
        })

        assert coordinator._session_manager_registered is True

    @pytest.mark.asyncio
    async def test_session_started_handler(self, coordinator):
        """Verify session start is tracked"""
        await coordinator._on_session_started({
            "session_id": "test_session_1",
            "symbols": ["BTCUSDT"]
        })

        is_active = await coordinator.is_session_active("test_session_1")
        assert is_active is True

    @pytest.mark.asyncio
    async def test_session_stopped_handler(self, coordinator):
        """Verify session stop removes tracking"""
        # First start a session
        await coordinator._on_session_started({
            "session_id": "test_session_1",
            "symbols": ["BTCUSDT"]
        })

        # Then stop it
        await coordinator._on_session_stopped({
            "session_id": "test_session_1"
        })

        is_active = await coordinator.is_session_active("test_session_1")
        assert is_active is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_handler(self, coordinator):
        """Verify circuit breaker state updates are tracked"""
        await coordinator._on_circuit_breaker_changed({
            "symbol": "BTCUSDT",
            "state": "open",
            "failure_count": 5
        })

        cb_state = await coordinator.get_circuit_breaker_state("BTCUSDT")
        assert cb_state["state"] == "open"


class TestCircularDependencyElimination:
    """
    Tests specifically verifying the circular dependency is eliminated.
    These are the critical tests for the K2 fix.
    """

    @pytest.mark.asyncio
    async def test_no_direct_session_manager_reference(self, coordinator):
        """Verify coordinator doesn't hold direct SessionManager reference"""
        # Coordinator should only communicate via EventBus
        assert not hasattr(coordinator, 'session_manager')
        assert not hasattr(coordinator, '_session_manager')

    @pytest.mark.asyncio
    async def test_subscription_check_via_event_bus(self, mock_event_bus, mock_logger):
        """Verify subscription checks happen via EventBus, not direct calls"""
        coordinator = TradingCoordinator(
            event_bus=mock_event_bus,
            logger=mock_logger,
            default_decision_timeout=0.1  # Short timeout for test
        )
        await coordinator.start()

        # Simulate session manager registration
        coordinator._session_manager_registered = True

        # Request subscription - should publish to EventBus
        await coordinator.request_subscription("BTCUSDT")

        # Verify EventBus was used
        publish_calls = [call for call in mock_event_bus.publish.call_args_list
                        if call[0][0] == "subscription.check_request"]
        assert len(publish_calls) >= 1

        await coordinator.stop()

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_session_manager(self, coordinator):
        """
        Verify system works even if SessionManager is not registered.
        This is the key fix for the NULL WINDOW bug.
        """
        # Coordinator starts without session manager registered
        assert coordinator._session_manager_registered is False

        # Subscription should still be allowed (graceful degradation)
        decision = await coordinator.request_subscription("BTCUSDT")
        assert decision == SubscriptionDecision.ALLOWED


class TestIntegrationScenarios:
    """Integration-style tests for real-world scenarios"""

    @pytest.mark.asyncio
    async def test_full_subscription_flow_with_coordinator(self, mock_event_bus, mock_logger):
        """
        Test complete subscription flow:
        1. Coordinator starts
        2. Session manager registers
        3. Subscription requested
        4. Response received
        5. Success tracked
        """
        coordinator = TradingCoordinator(
            event_bus=mock_event_bus,
            logger=mock_logger,
            default_decision_timeout=1.0
        )
        await coordinator.start()

        # Step 1: Session manager registers
        await coordinator._on_session_manager_registered({"component": "session_manager"})
        assert coordinator._session_manager_registered is True

        # Step 2: Simulate subscription check response coming back
        async def simulate_response():
            await asyncio.sleep(0.1)
            # Find the pending request and respond
            for request_id in list(coordinator._pending_requests.keys()):
                await coordinator._on_subscription_check_response({
                    "request_id": request_id,
                    "allowed": True,
                    "reason": ""
                })

        # Start response simulation
        asyncio.create_task(simulate_response())

        # Step 3: Request subscription
        decision = await coordinator.request_subscription("BTCUSDT")
        assert decision == SubscriptionDecision.ALLOWED

        # Step 4: Notify success
        await coordinator.notify_subscription_success("BTCUSDT")

        # Step 5: Verify tracking
        symbols = await coordinator.get_active_symbols()
        assert "BTCUSDT" in symbols

        await coordinator.stop()
