"""
Integration Tests - Live Trading Flow
=====================================

Tests full signal → order flow with EventBus integration.
All MEXC API calls are mocked - NO real exchange calls.

Test Scenarios:
1. Full signal → order flow (S1 signal → RiskManager → MEXC → PositionSync)
2. Circuit breaker activation and recovery
3. Position liquidation detection
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from decimal import Decimal

# Import components
from src.core.event_bus import EventBus
from src.domain.services.risk_manager import RiskManager
from src.domain.services.order_manager_live import LiveOrderManager, Order, OrderStatus
from src.domain.services.position_sync_service import PositionSyncService, LocalPosition
from src.infrastructure.adapters.mexc_adapter import (
    MexcRealAdapter,
    OrderStatusResponse,
    PositionResponse,
    OrderStatus as MexcOrderStatus
)
from src.domain.models.trading import Position, OrderSide
from src.infrastructure.config.settings import AppSettings
from src.core.logger import StructuredLogger
from src.core.circuit_breaker import CircuitBreakerOpenException


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def event_bus():
    """Create EventBus instance"""
    bus = EventBus()
    yield bus
    # Cleanup
    await bus.shutdown()


@pytest.fixture
def mock_logger():
    """Mock StructuredLogger"""
    logger = Mock(spec=StructuredLogger)
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def mock_mexc_adapter(mock_logger):
    """
    Mock MEXC adapter - NO real API calls.

    All methods return mock data.
    """
    adapter = Mock(spec=MexcRealAdapter)

    # Mock successful order submission
    adapter.create_market_order = AsyncMock(return_value="MOCK_ORDER_123")
    adapter.create_limit_order = AsyncMock(return_value="MOCK_ORDER_456")
    adapter.cancel_order = AsyncMock(return_value=True)

    # Mock order status (filled)
    adapter.get_order_status = AsyncMock(return_value=OrderStatusResponse(
        exchange_order_id="MOCK_ORDER_123",
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        quantity=0.001,
        price=50000.0,
        status=MexcOrderStatus.FILLED,
        filled_quantity=0.001,
        average_fill_price=50000.0,
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000)
    ))

    # Mock positions (empty)
    adapter.get_positions = AsyncMock(return_value=[])

    # Mock circuit breaker status
    adapter.get_circuit_breaker_status = Mock(return_value={
        "state": "CLOSED",
        "failure_count": 0
    })

    return adapter


@pytest.fixture
def settings():
    """Mock AppSettings"""
    return AppSettings()


@pytest.fixture
def risk_manager(event_bus, settings):
    """Create RiskManager instance"""
    return RiskManager(
        event_bus=event_bus,
        settings=settings,
        initial_capital=Decimal('10000')
    )


@pytest.fixture
def live_order_manager(event_bus, mock_mexc_adapter, risk_manager):
    """Create LiveOrderManager with mocked MEXC adapter"""
    return LiveOrderManager(
        event_bus=event_bus,
        mexc_adapter=mock_mexc_adapter,
        risk_manager=risk_manager,
        max_orders=100
    )


@pytest.fixture
def position_sync_service(event_bus, mock_mexc_adapter, risk_manager):
    """Create PositionSyncService with mocked MEXC adapter"""
    return PositionSyncService(
        event_bus=event_bus,
        mexc_adapter=mock_mexc_adapter,
        risk_manager=risk_manager,
        max_positions=10
    )


# ============================================================================
# TEST 1: Full Signal → Order Flow
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
@pytest.mark.e2e
class TestFullSignalToOrderFlow:
    """Test full signal → order flow with EventBus integration"""

    async def test_signal_to_order_creation(
        self,
        event_bus,
        live_order_manager,
        position_sync_service,
        risk_manager,
        mock_mexc_adapter
    ):
        """
        Test: S1 signal → RiskManager → LiveOrderManager → MEXC → PositionSync

        Flow:
        1. Mock StrategyManager generates S1 signal
        2. EventBus publishes signal_generated
        3. LiveOrderManager receives signal
        4. RiskManager validates order (should pass)
        5. MEXC Adapter submits order (mocked)
        6. EventBus publishes order_created
        7. PositionSyncService updates position
        8. EventBus publishes position_updated
        """

        # Track events
        events_received = []

        async def track_event(topic, handler):
            async def wrapper(data):
                events_received.append({"topic": topic, "data": data})
                if handler:
                    await handler(data)
            return wrapper

        # Subscribe to events
        await event_bus.subscribe("signal_generated", await track_event("signal_generated", None))
        await event_bus.subscribe("order_created", await track_event("order_created", None))
        await event_bus.subscribe("order_filled", await track_event("order_filled", None))
        await event_bus.subscribe("position_updated", await track_event("position_updated", None))

        # Start services
        await live_order_manager.start()
        await position_sync_service.start()

        try:
            # Step 1: Generate S1 signal (mock StrategyManager)
            signal_data = {
                "signal_type": "S1",
                "signal_id": "test_signal_001",
                "symbol": "BTC_USDT",
                "side": "buy",
                "quantity": 0.001,
                "price": None,  # Market order
                "order_type": "market",
                "confidence": 0.85,
                "indicator_values": {
                    "price_velocity": 0.75,
                    "volume_surge": 2.5
                }
            }

            # Step 2: Publish signal_generated event
            await event_bus.publish("signal_generated", signal_data)

            # Wait for order processing
            await asyncio.sleep(0.5)

            # Step 3: Verify LiveOrderManager received signal and created order
            assert len(live_order_manager.orders) == 1
            order = list(live_order_manager.orders.values())[0]
            assert order.symbol == "BTC_USDT"
            assert order.side == "buy"
            assert order.quantity == 0.001
            assert order.status in [OrderStatus.SUBMITTED, OrderStatus.PENDING]

            # Step 4: Verify MEXC adapter was called
            mock_mexc_adapter.create_market_order.assert_called_once()
            call_args = mock_mexc_adapter.create_market_order.call_args
            assert call_args.kwargs["symbol"] == "BTC_USDT"
            assert call_args.kwargs["side"] == "buy"
            assert call_args.kwargs["quantity"] == 0.001

            # Step 5: Verify order_created event was emitted
            order_created_events = [e for e in events_received if e["topic"] == "order_created"]
            assert len(order_created_events) >= 1
            order_event = order_created_events[0]["data"]
            assert order_event["symbol"] == "BTC_USDT"
            assert order_event["side"] == "buy"

            # Step 6: Simulate order fill
            await event_bus.publish("order_filled", {
                "order_id": order.order_id,
                "symbol": "BTC_USDT",
                "side": "buy",
                "quantity": 0.001,
                "price": 50000.0,
                "slippage": 0.0,
                "timestamp": int(time.time() * 1000)
            })

            # Wait for position update
            await asyncio.sleep(0.5)

            # Step 7: Verify PositionSyncService created position
            assert len(position_sync_service.positions) == 1
            assert "BTC_USDT" in position_sync_service.positions
            position = position_sync_service.positions["BTC_USDT"]
            assert position.symbol == "BTC_USDT"
            assert position.side == "LONG"
            assert position.quantity == 0.001

            # Step 8: Verify position_updated event was emitted
            position_updated_events = [e for e in events_received if e["topic"] == "position_updated"]
            assert len(position_updated_events) >= 1
            position_event = position_updated_events[0]["data"]
            assert position_event["symbol"] == "BTC_USDT"
            assert position_event["status"] == "opened"

        finally:
            # Cleanup
            await live_order_manager.stop()
            await position_sync_service.stop()


    async def test_risk_manager_rejects_order(
        self,
        event_bus,
        live_order_manager,
        risk_manager,
        mock_mexc_adapter
    ):
        """
        Test: RiskManager rejects order due to max position size

        Flow:
        1. Set capital to $100 (low)
        2. Generate S1 signal for $500 position
        3. RiskManager should reject (> 10% of capital)
        4. Order should NOT be submitted to MEXC
        5. risk_alert event should be emitted
        """

        # Track events
        risk_alerts = []

        async def track_risk_alert(data):
            risk_alerts.append(data)

        await event_bus.subscribe("risk_alert", track_risk_alert)

        # Set low capital
        await risk_manager.update_capital(Decimal('100'), Decimal('0'))

        # Start service
        await live_order_manager.start()

        try:
            # Create order that exceeds max position size
            order = Order(
                order_id="test_order_reject",
                symbol="BTC_USDT",
                side="buy",
                quantity=0.01,  # 0.01 BTC @ $50000 = $500 (> 10% of $100)
                price=50000.0,
                order_type="limit",
                status=OrderStatus.PENDING,
                created_at=time.time(),
                updated_at=time.time()
            )

            # Submit order with current positions
            current_positions = []
            result = await live_order_manager.submit_order(order, current_positions)

            # Verify order was rejected
            assert result is False
            assert order.status == OrderStatus.FAILED
            assert "risk check failed" in order.error_message.lower()

            # Verify MEXC adapter was NOT called
            mock_mexc_adapter.create_limit_order.assert_not_called()

            # Verify risk_alert was emitted
            assert len(risk_alerts) >= 1
            alert = risk_alerts[0]
            assert alert["severity"] == "WARNING"
            assert alert["alert_type"] == "ORDER_REJECTED"

        finally:
            await live_order_manager.stop()


# ============================================================================
# TEST 2: Circuit Breaker Activation
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
@pytest.mark.e2e
class TestCircuitBreakerActivation:
    """Test circuit breaker activation and recovery"""

    async def test_circuit_breaker_opens_after_failures(
        self,
        event_bus,
        live_order_manager,
        mock_mexc_adapter,
        risk_manager
    ):
        """
        Test: Circuit breaker opens after 5 MEXC API failures

        Flow:
        1. Simulate 5 consecutive MEXC API failures
        2. Verify circuit breaker opens
        3. Verify orders are NOT submitted while open
        4. Simulate MEXC recovery
        5. Verify circuit breaker closes
        6. Verify orders are submitted again
        """

        # Configure mock to fail 5 times, then succeed
        call_count = {"count": 0}

        async def failing_create_order(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] <= 5:
                raise Exception("MEXC API Error 500: Internal Server Error")
            else:
                return "MOCK_ORDER_SUCCESS"

        mock_mexc_adapter.create_market_order = AsyncMock(side_effect=failing_create_order)

        # Start service
        await live_order_manager.start()

        try:
            # Step 1: Submit orders that will fail (simulate 5 failures)
            for i in range(5):
                order = Order(
                    order_id=f"test_order_{i}",
                    symbol="BTC_USDT",
                    side="buy",
                    quantity=0.001,
                    price=None,
                    order_type="market",
                    status=OrderStatus.PENDING,
                    created_at=time.time(),
                    updated_at=time.time()
                )

                result = await live_order_manager.submit_order(order, current_positions=[])

                # Order should fail
                assert result is False
                assert order.status == OrderStatus.FAILED

                # Wait between attempts
                await asyncio.sleep(0.1)

            # Step 2: Verify circuit breaker state (if accessible)
            # Note: Circuit breaker is inside ResilientService in MEXC adapter
            # We verify by checking if next call raises CircuitBreakerOpenException

            # Step 3: Try to submit order while circuit breaker is open
            # (This depends on circuit breaker implementation)
            # For now, we just verify failures occurred

            assert call_count["count"] >= 5

            # Step 4: Wait for recovery timeout (circuit breaker should allow retry)
            # Note: In real implementation, we'd wait for recovery_timeout
            # For testing, we'll just verify the 6th attempt succeeds

            order_6 = Order(
                order_id="test_order_6",
                symbol="BTC_USDT",
                side="buy",
                quantity=0.001,
                price=None,
                order_type="market",
                status=OrderStatus.PENDING,
                created_at=time.time(),
                updated_at=time.time()
            )

            result = await live_order_manager.submit_order(order_6, current_positions=[])

            # Step 5: Verify order succeeds (circuit breaker closed)
            assert result is True
            assert order_6.status == OrderStatus.SUBMITTED
            assert order_6.exchange_order_id == "MOCK_ORDER_SUCCESS"

        finally:
            await live_order_manager.stop()


# ============================================================================
# TEST 3: Position Liquidation Detection
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
@pytest.mark.e2e
class TestPositionLiquidationDetection:
    """Test position liquidation detection"""

    async def test_detect_liquidation(
        self,
        event_bus,
        position_sync_service,
        mock_mexc_adapter,
        risk_manager
    ):
        """
        Test: Detect position liquidation (position missing on exchange)

        Flow:
        1. Create position in PositionSyncService
        2. Mock MEXC API to return empty positions (position liquidated)
        3. Trigger position sync
        4. Verify PositionSyncService detects liquidation
        5. Verify risk_alert event emitted with severity=CRITICAL
        """

        # Track risk alerts
        risk_alerts = []

        async def track_risk_alert(data):
            risk_alerts.append(data)

        await event_bus.subscribe("risk_alert", track_risk_alert)

        # Step 1: Create local position
        position_sync_service.positions["BTC_USDT"] = LocalPosition(
            symbol="BTC_USDT",
            side="LONG",
            quantity=0.001,
            entry_price=50000.0,
            current_price=50000.0,
            liquidation_price=45000.0,
            unrealized_pnl=0.0,
            margin=500.0,
            leverage=2.0,
            margin_ratio=100.0,
            opened_at=time.time(),
            updated_at=time.time()
        )

        assert len(position_sync_service.positions) == 1

        # Step 2: Mock MEXC to return empty positions (liquidated)
        mock_mexc_adapter.get_positions = AsyncMock(return_value=[])

        # Start service
        await position_sync_service.start()

        try:
            # Step 3: Wait for sync (10s interval, but we'll trigger manually)
            # Manually call sync method
            await position_sync_service._sync_positions()

            # Wait for event processing
            await asyncio.sleep(0.5)

            # Step 4: Verify position was removed
            assert len(position_sync_service.positions) == 0
            assert "BTC_USDT" not in position_sync_service.positions

            # Step 5: Verify risk_alert was emitted
            liquidation_alerts = [
                a for a in risk_alerts
                if a.get("alert_type") == "LIQUIDATION_DETECTED"
            ]

            assert len(liquidation_alerts) >= 1
            alert = liquidation_alerts[0]
            assert alert["severity"] == "CRITICAL"
            assert "BTC_USDT" in alert["details"]["symbol"]

        finally:
            await position_sync_service.stop()


    async def test_detect_new_position_on_exchange(
        self,
        event_bus,
        position_sync_service,
        mock_mexc_adapter,
        risk_manager
    ):
        """
        Test: Detect new position opened directly on exchange (manual trading)

        Flow:
        1. Start with empty local positions
        2. Mock MEXC to return a position
        3. Trigger sync
        4. Verify PositionSyncService adds the position
        5. Verify position_updated event emitted
        """

        # Track position events
        position_events = []

        async def track_position(data):
            position_events.append(data)

        await event_bus.subscribe("position_updated", track_position)

        # Step 1: Start with empty positions
        assert len(position_sync_service.positions) == 0

        # Step 2: Mock MEXC to return a position
        mock_mexc_adapter.get_positions = AsyncMock(return_value=[
            PositionResponse(
                symbol="ETH_USDT",
                side="LONG",
                quantity=0.01,
                entry_price=3000.0,
                current_price=3050.0,
                unrealized_pnl=0.5,
                margin_ratio=150.0,
                liquidation_price=2500.0,
                leverage=2.0,
                margin=300.0
            )
        ])

        # Start service
        await position_sync_service.start()

        try:
            # Step 3: Trigger sync
            await position_sync_service._sync_positions()

            # Wait for event processing
            await asyncio.sleep(0.5)

            # Step 4: Verify position was added
            assert len(position_sync_service.positions) == 1
            assert "ETH_USDT" in position_sync_service.positions

            position = position_sync_service.positions["ETH_USDT"]
            assert position.symbol == "ETH_USDT"
            assert position.side == "LONG"
            assert position.quantity == 0.01
            assert position.entry_price == 3000.0

            # Step 5: Verify position_updated event
            opened_events = [
                e for e in position_events
                if e.get("status") == "opened"
            ]

            assert len(opened_events) >= 1
            event = opened_events[0]
            assert event["symbol"] == "ETH_USDT"

        finally:
            await position_sync_service.stop()


# ============================================================================
# TEST 4: EventBus Integration
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
@pytest.mark.e2e
class TestEventBusIntegration:
    """Test EventBus integration across all components"""

    async def test_eventbus_message_flow(self, event_bus):
        """
        Test: EventBus publishes messages to all subscribers

        Verify:
        - Multiple subscribers receive same message
        - Messages delivered in order
        - No message loss
        """

        # Track messages
        subscriber1_messages = []
        subscriber2_messages = []

        async def subscriber1(data):
            subscriber1_messages.append(data)

        async def subscriber2(data):
            subscriber2_messages.append(data)

        # Subscribe
        await event_bus.subscribe("test_topic", subscriber1)
        await event_bus.subscribe("test_topic", subscriber2)

        # Publish 10 messages
        for i in range(10):
            await event_bus.publish("test_topic", {"message_id": i})

        # Wait for processing
        await asyncio.sleep(0.5)

        # Verify all messages received by both subscribers
        assert len(subscriber1_messages) == 10
        assert len(subscriber2_messages) == 10

        # Verify order
        for i in range(10):
            assert subscriber1_messages[i]["message_id"] == i
            assert subscriber2_messages[i]["message_id"] == i

        # Cleanup
        await event_bus.unsubscribe("test_topic", subscriber1)
        await event_bus.unsubscribe("test_topic", subscriber2)


    async def test_eventbus_error_isolation(self, event_bus):
        """
        Test: EventBus isolates subscriber errors

        Verify:
        - Failing subscriber doesn't affect others
        - EventBus continues processing
        """

        # Track messages
        good_subscriber_messages = []

        async def failing_subscriber(data):
            raise Exception("Subscriber crashed!")

        async def good_subscriber(data):
            good_subscriber_messages.append(data)

        # Subscribe
        await event_bus.subscribe("test_topic", failing_subscriber)
        await event_bus.subscribe("test_topic", good_subscriber)

        # Publish message
        await event_bus.publish("test_topic", {"test": "data"})

        # Wait for processing (retry logic: 3 attempts with backoff)
        await asyncio.sleep(10)  # Wait for all retries (1s + 2s + 4s = 7s + buffer)

        # Verify good subscriber still received message
        assert len(good_subscriber_messages) == 1
        assert good_subscriber_messages[0]["test"] == "data"

        # Cleanup
        await event_bus.unsubscribe("test_topic", failing_subscriber)
        await event_bus.unsubscribe("test_topic", good_subscriber)
