"""
Integration Test for Container - Multi-Agent Service Integration
=================================================================

Tests the complete dependency injection and service initialization
from all agents (Agent 0-6).

Tests:
1. Container initialization
2. All services created without errors
3. EventBus connections (subscriber count)
4. No circular dependencies
5. Service lifecycle (start/stop)
"""

import pytest
import asyncio
from decimal import Decimal

from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.infrastructure.config.config_loader import get_settings_from_working_directory
from src.infrastructure.container import Container


@pytest.fixture
def event_bus():
    """Create EventBus instance."""
    return EventBus()


@pytest.fixture
def logger():
    """Create StructuredLogger instance."""
    settings = get_settings_from_working_directory()
    return StructuredLogger("TestContainer", settings.logging)


@pytest.fixture
def settings():
    """Load application settings."""
    return get_settings_from_working_directory()


@pytest.fixture
async def container(settings, event_bus, logger):
    """Create Container instance."""
    container = Container(settings, event_bus, logger)
    yield container
    # Cleanup
    await container.shutdown()


@pytest.mark.asyncio
async def test_container_initialization(container):
    """Test that Container initializes successfully."""
    assert container is not None
    assert container.event_bus is not None
    assert container.logger is not None
    assert container.settings is not None


@pytest.mark.asyncio
async def test_create_risk_manager(container):
    """Test Agent 2: RiskManager creation with EventBus + Settings."""
    risk_manager = await container.create_risk_manager(initial_capital=10000.0)

    assert risk_manager is not None
    assert risk_manager.event_bus is container.event_bus
    # ✅ FIX (2025-12-02): RiskManager uses risk_config (not settings) per Architecture Fix 2025-11-30
    # Domain layer should not depend on Infrastructure (AppSettings)
    assert risk_manager.risk_config is container.settings.risk_management.risk_manager
    assert risk_manager.initial_capital == Decimal('10000.0')

    # Test singleton pattern
    risk_manager2 = await container.create_risk_manager()
    assert risk_manager is risk_manager2  # Same instance


@pytest.mark.asyncio
async def test_create_prometheus_metrics(container):
    """Test Agent 5: PrometheusMetrics creation and EventBus subscription."""
    # Get initial subscriber count
    initial_subscriber_count = sum(
        len(subscribers) for subscribers in container.event_bus._subscribers.values()
    )

    # Create PrometheusMetrics
    prometheus_metrics = await container.create_prometheus_metrics()

    assert prometheus_metrics is not None
    assert prometheus_metrics.event_bus is container.event_bus
    assert prometheus_metrics._subscribed is True

    # Verify EventBus subscriptions increased
    final_subscriber_count = sum(
        len(subscribers) for subscribers in container.event_bus._subscribers.values()
    )

    # PrometheusMetrics subscribes to 7 topics (some with duplicate handlers)
    # Expected: order_created, order_filled, position_updated, risk_alert, etc.
    assert final_subscriber_count > initial_subscriber_count
    print(f"EventBus subscribers increased: {initial_subscriber_count} → {final_subscriber_count}")

    # Test singleton pattern
    prometheus_metrics2 = await container.create_prometheus_metrics()
    assert prometheus_metrics is prometheus_metrics2  # Same instance


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires MEXC credentials and QuestDB running")
async def test_create_live_order_manager(container):
    """Test Agent 3: LiveOrderManager creation with full dependencies."""
    # This test requires:
    # - MEXC API credentials (for MEXC adapter)
    # - RiskManager
    # - EventBus

    live_order_manager = await container.create_live_order_manager()

    assert live_order_manager is not None
    assert live_order_manager.event_bus is container.event_bus
    assert live_order_manager.mexc_adapter is not None
    assert live_order_manager.risk_manager is not None

    # Test singleton pattern
    live_order_manager2 = await container.create_live_order_manager()
    assert live_order_manager is live_order_manager2  # Same instance


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires MEXC credentials and QuestDB running")
async def test_create_position_sync_service(container):
    """Test Agent 3: PositionSyncService creation with full dependencies."""
    # This test requires:
    # - MEXC API credentials (for MEXC adapter)
    # - RiskManager
    # - EventBus

    position_sync_service = await container.create_position_sync_service()

    assert position_sync_service is not None
    assert position_sync_service.event_bus is container.event_bus
    assert position_sync_service.mexc_adapter is not None
    assert position_sync_service.risk_manager is not None

    # Test singleton pattern
    position_sync_service2 = await container.create_position_sync_service()
    assert position_sync_service is position_sync_service2  # Same instance


@pytest.mark.asyncio
async def test_eventbus_subscriber_count(container):
    """
    Test EventBus subscriber registration from all services.

    Expected subscribers:
    - PrometheusMetrics: 7+ subscriptions
    - LiveOrderManager: 1 subscription (signal_generated)
    - PositionSyncService: 1 subscription (order_filled)

    Total expected: 9+ subscriptions
    """
    # Create all services (skip ones that require external dependencies)
    prometheus_metrics = await container.create_prometheus_metrics()

    # Count subscribers per topic
    subscriber_counts = {
        topic: len(subscribers)
        for topic, subscribers in container.event_bus._subscribers.items()
    }

    print("EventBus subscriber counts per topic:")
    for topic, count in subscriber_counts.items():
        print(f"  {topic}: {count} subscribers")

    # Verify PrometheusMetrics subscriptions
    assert "order_created" in subscriber_counts
    assert "order_filled" in subscriber_counts
    assert "position_updated" in subscriber_counts
    assert "risk_alert" in subscriber_counts

    # Total subscriber count should be > 0
    total_subscribers = sum(subscriber_counts.values())
    assert total_subscribers > 0
    print(f"Total EventBus subscribers: {total_subscribers}")


@pytest.mark.asyncio
async def test_no_circular_dependencies(container):
    """
    Test that no circular dependencies exist between services.

    Services should create successfully without deadlocks.
    """
    # Create services in dependency order
    risk_manager = await container.create_risk_manager()
    prometheus_metrics = await container.create_prometheus_metrics()

    # If we get here without hanging, no circular dependencies exist
    assert risk_manager is not None
    assert prometheus_metrics is not None


@pytest.mark.asyncio
async def test_service_lifecycle(container):
    """Test service lifecycle (creation, startup, shutdown)."""
    # Create PrometheusMetrics
    prometheus_metrics = await container.create_prometheus_metrics()

    # Verify subscriptions
    assert prometheus_metrics._subscribed is True

    # Test cleanup
    prometheus_metrics.unsubscribe_from_events()
    assert prometheus_metrics._subscribed is False

    # Container shutdown
    await container.shutdown()

    # Verify EventBus is cleared
    assert len(container.event_bus._subscribers) == 0


@pytest.mark.asyncio
async def test_container_health_check(container):
    """Test Container health check."""
    # Create some services
    await container.create_risk_manager()
    await container.create_prometheus_metrics()

    # Run health check
    health_status = await container.health_check()

    assert health_status is not None
    assert "overall_healthy" in health_status
    assert "services" in health_status
    assert "total_services" in health_status

    print(f"Container health status: {health_status}")


@pytest.mark.asyncio
async def test_container_service_status(container):
    """Test Container service status reporting."""
    # Create some services
    await container.create_risk_manager()
    await container.create_prometheus_metrics()

    # Get service status
    status = container.get_service_status()

    assert status is not None
    assert "total_services" in status
    assert "singleton_services" in status
    assert "created_service_types" in status

    print(f"Container service status: {status}")

    # Verify singleton services
    assert status["singleton_services"] >= 2  # RiskManager + PrometheusMetrics


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
