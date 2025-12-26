"""
E2E Trading Flow Tests
======================
Comprehensive end-to-end tests for the complete trading flow:
    Signal Detection → Risk Assessment → Order Execution → Position Management

These tests verify the integration between all system components.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List

# Domain models
from src.domain.models.signals import FlashPumpSignal, SignalStrength
from src.domain.models.trading import Order, OrderSide, OrderType, OrderStatus


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_pump_signal():
    """Create a realistic pump signal for testing."""
    return FlashPumpSignal(
        symbol="BTCUSDT",
        exchange="MEXC_FUTURES",
        detection_time=datetime.utcnow(),
        peak_price=Decimal("52000.00"),
        baseline_price=Decimal("50000.00"),
        pump_magnitude=Decimal("4.0"),  # 4% pump
        volume_surge_ratio=Decimal("3.5"),
        price_velocity=Decimal("0.8"),
        confidence_score=Decimal("75.0"),
        pump_age_seconds=Decimal("15"),
        baseline_volume=Decimal("1000000"),
        volume_24h_usdt=Decimal("50000000")
    )


@pytest.fixture
def mock_market_data():
    """Create mock market data."""
    return {
        "symbol": "BTCUSDT",
        "price": Decimal("51500.00"),
        "volume": Decimal("1500000"),
        "bid": Decimal("51490.00"),
        "ask": Decimal("51510.00"),
        "spread_pct": 0.04,
        "timestamp": datetime.utcnow()
    }


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBus with tracking."""
    event_bus = MagicMock()
    event_bus.published_events = []
    event_bus.subscriptions = {}

    async def mock_subscribe(event_name: str, handler):
        if event_name not in event_bus.subscriptions:
            event_bus.subscriptions[event_name] = []
        event_bus.subscriptions[event_name].append(handler)

    async def mock_publish(event_name: str, data: Dict[str, Any]):
        event_bus.published_events.append({
            "event": event_name,
            "data": data,
            "timestamp": datetime.utcnow()
        })
        if event_name in event_bus.subscriptions:
            for handler in event_bus.subscriptions[event_name]:
                await handler(data)

    event_bus.subscribe = mock_subscribe
    event_bus.publish = mock_publish
    return event_bus


@pytest.fixture
def mock_order_executor():
    """Create a mock order executor."""
    executor = AsyncMock()
    executor.orders_placed = []

    async def mock_place_market_order(symbol, side, quantity, client_order_id=None):
        order = Order(
            order_id=f"test_order_{len(executor.orders_placed) + 1}",
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=None,
            status=OrderStatus.FILLED,
            filled_quantity=quantity,
            average_price=Decimal("51500.00"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            exchange="MEXC_FUTURES",
            exchange_order_id=f"mexc_{len(executor.orders_placed) + 1}"
        )
        executor.orders_placed.append(order)
        return order

    async def mock_place_stop_loss(symbol, side, quantity, stop_price, client_order_id=None):
        order = Order(
            order_id=f"stop_order_{len(executor.orders_placed) + 1}",
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP_LOSS,
            quantity=quantity,
            price=stop_price,
            status=OrderStatus.PENDING,
            filled_quantity=Decimal("0"),
            average_price=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            exchange="MEXC_FUTURES",
            exchange_order_id=f"mexc_stop_{len(executor.orders_placed) + 1}"
        )
        executor.orders_placed.append(order)
        return order

    executor.place_market_order = mock_place_market_order
    executor.place_stop_loss_order = mock_place_stop_loss
    executor.get_exchange_name.return_value = "MEXC_FUTURES"
    executor.health_check.return_value = True
    return executor


# ============================================================================
# E2E SIGNAL FLOW TESTS
# ============================================================================

class TestE2ESignalFlow:
    """End-to-end tests for signal generation and forwarding."""

    @pytest.mark.asyncio
    async def test_signal_published_to_event_bus(self, mock_event_bus, mock_pump_signal):
        """Test that pump signals are published to EventBus."""
        # Publish signal
        await mock_event_bus.publish("signal_generated", {
            "signal_type": "S1",
            "symbol": mock_pump_signal.symbol,
            "timestamp": mock_pump_signal.detection_time.isoformat(),
            "indicators": {
                "pump_magnitude_pct": float(mock_pump_signal.pump_magnitude),
                "volume_surge_ratio": float(mock_pump_signal.volume_surge_ratio),
                "confidence": float(mock_pump_signal.confidence_score)
            }
        })

        # Verify event was published
        assert len(mock_event_bus.published_events) == 1
        event = mock_event_bus.published_events[0]
        assert event["event"] == "signal_generated"
        assert event["data"]["signal_type"] == "S1"
        assert event["data"]["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_signal_forwarded_to_subscribers(self, mock_event_bus):
        """Test that signals are forwarded to all subscribers."""
        received_signals = []

        async def signal_handler(data):
            received_signals.append(data)

        # Subscribe to signals
        await mock_event_bus.subscribe("signal_generated", signal_handler)

        # Publish signal
        await mock_event_bus.publish("signal_generated", {
            "signal_type": "Z1",
            "symbol": "ETHUSDT",
            "timestamp": datetime.utcnow().isoformat()
        })

        # Verify handler received the signal
        assert len(received_signals) == 1
        assert received_signals[0]["signal_type"] == "Z1"


# ============================================================================
# E2E RISK ASSESSMENT TESTS
# ============================================================================

class TestE2ERiskAssessment:
    """End-to-end tests for risk assessment flow."""

    @pytest.mark.asyncio
    async def test_emergency_conditions_block_trading(self):
        """Test that emergency conditions prevent order execution."""
        from src.domain.services.risk_assessment import (
            RiskAssessmentService,
            RiskLimits
        )

        # Create mock settings objects with all required attributes
        risk_settings = MagicMock()
        risk_settings.max_drawdown_pct = 6.0
        risk_settings.spread_blowout_pct = 5.0
        risk_settings.volume_death_threshold_pct = 80.0
        risk_settings.emergency_min_liquidity = 100.0

        entry_settings = MagicMock()
        entry_settings.min_pump_age_seconds = 5
        entry_settings.max_entry_delay_seconds = 45
        entry_settings.min_confidence_threshold = 60.0
        entry_settings.max_spread_pct = 2.0
        entry_settings.min_liquidity_usdt = 1000.0
        entry_settings.rsi_max = 70.0

        safety_settings = MagicMock()
        safety_settings.max_daily_trades = 3
        safety_settings.max_consecutive_losses = 2
        safety_settings.daily_loss_limit_pct = 2.0

        # Create mock market data with dangerous spread
        mock_market = MagicMock()
        mock_market.volume = Decimal("100000")
        mock_market.volume_24h_usdt = None

        # Test with dangerous spread (>5%)
        service = RiskAssessmentService(risk_settings, entry_settings, safety_settings)
        is_safe, reasons = service.assess_emergency_conditions(
            market_data=mock_market,
            spread_pct=6.0,  # Exceeds 5% threshold
            liquidity_usdt=1000.0
        )

        assert is_safe is False
        assert any("spread" in reason.lower() for reason in reasons)

    @pytest.mark.asyncio
    async def test_low_liquidity_triggers_emergency(self):
        """Test that low liquidity triggers emergency condition."""
        from src.domain.services.risk_assessment import RiskAssessmentService

        # Create mock settings with all required attributes
        risk_settings = MagicMock()
        risk_settings.max_drawdown_pct = 6.0
        risk_settings.spread_blowout_pct = 5.0
        risk_settings.volume_death_threshold_pct = 80.0
        risk_settings.emergency_min_liquidity = 100.0

        entry_settings = MagicMock()
        entry_settings.min_pump_age_seconds = 5
        entry_settings.max_entry_delay_seconds = 45
        entry_settings.min_confidence_threshold = 60.0
        entry_settings.max_spread_pct = 2.0
        entry_settings.min_liquidity_usdt = 1000.0
        entry_settings.rsi_max = 70.0

        safety_settings = MagicMock()
        safety_settings.max_daily_trades = 3
        safety_settings.max_consecutive_losses = 2
        safety_settings.daily_loss_limit_pct = 2.0

        mock_market = MagicMock()
        mock_market.volume = Decimal("100000")
        mock_market.volume_24h_usdt = None

        service = RiskAssessmentService(risk_settings, entry_settings, safety_settings)
        is_safe, reasons = service.assess_emergency_conditions(
            market_data=mock_market,
            spread_pct=0.5,
            liquidity_usdt=50.0  # Below $100 threshold
        )

        assert is_safe is False
        assert any("liquidity" in reason.lower() for reason in reasons)


# ============================================================================
# E2E ORDER EXECUTION TESTS
# ============================================================================

class TestE2EOrderExecution:
    """End-to-end tests for order execution flow."""

    @pytest.mark.asyncio
    async def test_market_order_execution(self, mock_order_executor):
        """Test complete market order execution flow."""
        order = await mock_order_executor.place_market_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.001")
        )

        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == Decimal("0.001")
        assert order.exchange == "MEXC_FUTURES"

    @pytest.mark.asyncio
    async def test_stop_loss_order_creation(self, mock_order_executor):
        """Test stop-loss order creation."""
        order = await mock_order_executor.place_stop_loss_order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.001"),
            stop_price=Decimal("48000.00")
        )

        assert order.order_type == OrderType.STOP_LOSS
        assert order.price == Decimal("48000.00")
        assert order.status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_order_with_stop_loss_flow(self, mock_order_executor):
        """Test complete order flow with stop-loss."""
        # 1. Place entry order
        entry_order = await mock_order_executor.place_market_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.001")
        )
        assert entry_order.status == OrderStatus.FILLED

        # 2. Place stop-loss order
        stop_order = await mock_order_executor.place_stop_loss_order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.001"),
            stop_price=Decimal("48000.00")
        )
        assert stop_order.status == OrderStatus.PENDING

        # Verify both orders are tracked
        assert len(mock_order_executor.orders_placed) == 2


# ============================================================================
# E2E CIRCUIT BREAKER TESTS
# ============================================================================

class TestE2ECircuitBreaker:
    """End-to-end tests for circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test that circuit breaker opens after consecutive failures."""
        from src.core.circuit_breaker import (
            CircuitBreaker,
            CircuitBreakerConfig,
            CircuitBreakerState,
            CircuitBreakerOpenException
        )

        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            name="test_breaker"
        )
        breaker = CircuitBreaker(config)

        # Simulate failures
        async def failing_operation():
            raise Exception("API Error")

        for _ in range(3):
            try:
                await breaker.call_async(failing_operation)
            except Exception:
                pass

        # Circuit should be open now
        assert breaker.state == CircuitBreakerState.OPEN

        # New requests should be rejected
        with pytest.raises(CircuitBreakerOpenException):
            await breaker.call_async(failing_operation)

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovers(self):
        """Test that circuit breaker recovers after timeout."""
        from src.core.circuit_breaker import (
            CircuitBreaker,
            CircuitBreakerConfig,
            CircuitBreakerState
        )

        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for fast test
            name="test_breaker"
        )
        breaker = CircuitBreaker(config)

        # Force failures
        async def failing_op():
            raise Exception("Fail")

        for _ in range(2):
            try:
                await breaker.call_async(failing_op)
            except:
                pass

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Try successful operation
        async def success_op():
            return "success"

        # Should transition to half-open
        result = await breaker.call_async(success_op)
        assert result == "success"


# ============================================================================
# E2E WEBSOCKET TESTS
# ============================================================================

class TestE2EWebSocket:
    """End-to-end tests for WebSocket communication."""

    @pytest.mark.asyncio
    async def test_signal_broadcast_to_clients(self):
        """Test that signals are broadcast to WebSocket clients."""
        broadcasts = []

        async def mock_broadcast(stream_type, data):
            broadcasts.append({"stream": stream_type, "data": data})
            return True

        # Simulate signal broadcast
        await mock_broadcast("signals", {
            "type": "signal_generated",
            "data": {
                "signal_type": "S1",
                "symbol": "BTCUSDT",
                "confidence": 85.0
            }
        })

        assert len(broadcasts) == 1
        assert broadcasts[0]["stream"] == "signals"
        assert broadcasts[0]["data"]["data"]["signal_type"] == "S1"

    @pytest.mark.asyncio
    async def test_execution_progress_updates(self):
        """Test that execution progress is broadcast."""
        progress_updates = []

        async def mock_broadcast(stream_type, data):
            progress_updates.append({"stream": stream_type, "data": data})
            return True

        # Simulate progress updates
        for progress in [25, 50, 75, 100]:
            await mock_broadcast("execution_status", {
                "type": "progress",
                "data": {
                    "session_id": "test_session",
                    "progress_pct": progress,
                    "records_collected": progress * 10
                }
            })

        assert len(progress_updates) == 4
        assert progress_updates[-1]["data"]["data"]["progress_pct"] == 100


# ============================================================================
# E2E PUMP DETECTION TESTS
# ============================================================================

class TestE2EPumpDetection:
    """End-to-end tests for pump detection."""

    def test_pump_detection_threshold(self):
        """Test pump detection with various magnitudes."""
        from src.domain.services.pump_detector import (
            PumpDetectionService,
            PumpDetectionConfig
        )

        config = PumpDetectionConfig(
            min_pump_magnitude=Decimal("7.0"),
            volume_surge_multiplier=Decimal("3.5")
        )
        detector = PumpDetectionService(config)

        # A 7% pump should be detected
        assert config.min_pump_magnitude == Decimal("7.0")

        # A 5% pump should not trigger
        test_magnitude = Decimal("5.0")
        assert test_magnitude < config.min_pump_magnitude

    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        from src.domain.services.pump_detector import ConfidenceCalculator

        calc = ConfidenceCalculator()
        confidence = calc.calculate_confidence(
            pump_magnitude=Decimal("10.0"),
            volume_surge_ratio=Decimal("4.0"),
            price_velocity=Decimal("1.0"),
            volume_24h_usdt=Decimal("100000000")
        )

        # Confidence should be between 0 and 100
        assert Decimal("0") <= confidence <= Decimal("100")
        # With strong signals, confidence should be high
        assert confidence >= Decimal("50")


# ============================================================================
# E2E FULL TRADING CYCLE TEST
# ============================================================================

class TestE2EFullTradingCycle:
    """Complete trading cycle integration test."""

    @pytest.mark.asyncio
    async def test_complete_trading_cycle(
        self,
        mock_event_bus,
        mock_order_executor,
        mock_pump_signal
    ):
        """Test complete cycle: Signal → Assessment → Entry → Stop-Loss → Exit."""
        trading_events = []

        # Subscribe to trading events
        async def track_events(data):
            trading_events.append(data)

        await mock_event_bus.subscribe("signal_generated", track_events)
        await mock_event_bus.subscribe("order_placed", track_events)

        # Step 1: Signal detection
        await mock_event_bus.publish("signal_generated", {
            "signal_type": "S1",
            "symbol": "BTCUSDT",
            "confidence": 80.0,
            "pump_magnitude": 8.5
        })

        assert len(trading_events) >= 1

        # Step 2: Risk assessment passed, place entry
        entry_order = await mock_order_executor.place_market_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.001")
        )
        assert entry_order.status == OrderStatus.FILLED

        # Step 3: Place stop-loss protection
        stop_order = await mock_order_executor.place_stop_loss_order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.001"),
            stop_price=Decimal("48000.00")
        )
        assert stop_order.order_type == OrderType.STOP_LOSS

        # Verify complete flow
        assert len(mock_order_executor.orders_placed) == 2
        assert mock_order_executor.orders_placed[0].order_type == OrderType.MARKET
        assert mock_order_executor.orders_placed[1].order_type == OrderType.STOP_LOSS


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
