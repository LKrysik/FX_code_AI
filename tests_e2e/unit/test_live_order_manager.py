"""
Unit Tests for LiveOrderManager
================================
Tests order lifecycle, retry logic, circuit breaker integration, and EventBus events.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

# Import the components we're testing
from src.domain.services.order_manager_live import LiveOrderManager, Order, OrderStatus
from src.core.event_bus import EventBus
from src.core.circuit_breaker import CircuitBreakerOpenException


@pytest.fixture
def event_bus():
    """Create EventBus instance."""
    return EventBus()


@pytest.fixture
def mexc_adapter():
    """Create mock MEXC adapter."""
    adapter = AsyncMock()
    adapter.create_market_order = AsyncMock(return_value="MEXC_12345")
    adapter.create_limit_order = AsyncMock(return_value="MEXC_67890")
    adapter.cancel_order = AsyncMock(return_value=True)
    adapter.get_order_status = AsyncMock()
    return adapter


@pytest.fixture
def risk_manager():
    """Create mock RiskManager."""
    manager = AsyncMock()
    
    # Default: approve all orders
    result = MagicMock()
    result.can_proceed = True
    result.reason = None
    result.risk_score = 10.0
    
    manager.can_open_position = AsyncMock(return_value=result)
    return manager


@pytest.fixture
def order_manager(event_bus, mexc_adapter, risk_manager):
    """Create LiveOrderManager instance."""
    return LiveOrderManager(
        event_bus=event_bus,
        mexc_adapter=mexc_adapter,
        risk_manager=risk_manager,
        max_orders=1000
    )


# ===== TEST: Initialization =====

def test_initialization(order_manager):
    """Test LiveOrderManager initializes correctly."""
    assert order_manager.max_orders == 1000
    assert len(order_manager.orders) == 0
    assert order_manager._running == False


# ===== TEST: Order Submission =====

@pytest.mark.asyncio
async def test_submit_order_success_market(order_manager, mexc_adapter):
    """Test successful market order submission."""
    order = Order(
        order_id="order_1",
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01,
        price=None,  # Market order
        order_type="market",
        status=OrderStatus.PENDING,
        created_at=time.time(),
        updated_at=time.time()
    )

    success = await order_manager.submit_order(order)

    assert success
    assert order.status == OrderStatus.SUBMITTED
    assert order.exchange_order_id == "MEXC_12345"
    assert "order_1" in order_manager.orders

    # Verify MEXC adapter was called
    mexc_adapter.create_market_order.assert_called_once_with(
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01
    )


@pytest.mark.asyncio
async def test_submit_order_success_limit(order_manager, mexc_adapter):
    """Test successful limit order submission."""
    order = Order(
        order_id="order_2",
        symbol="ETH_USDT",
        side="sell",
        quantity=0.5,
        price=2000.0,
        order_type="limit",
        status=OrderStatus.PENDING,
        created_at=time.time(),
        updated_at=time.time()
    )

    success = await order_manager.submit_order(order)

    assert success
    assert order.status == OrderStatus.SUBMITTED
    assert order.exchange_order_id == "MEXC_67890"

    # Verify MEXC adapter was called with price
    mexc_adapter.create_limit_order.assert_called_once_with(
        symbol="ETH_USDT",
        side="sell",
        quantity=0.5,
        price=2000.0
    )


@pytest.mark.asyncio
async def test_submit_order_queue_full(order_manager):
    """Test order rejection when queue is full."""
    # Fill queue to max
    order_manager.max_orders = 2
    for i in range(2):
        order_manager.orders[f"order_{i}"] = Order(
            order_id=f"order_{i}",
            symbol="BTC_USDT",
            side="buy",
            quantity=0.01,
            price=None,
            order_type="market",
            status=OrderStatus.SUBMITTED,
            created_at=time.time(),
            updated_at=time.time()
        )

    # Try to submit one more
    new_order = Order(
        order_id="order_new",
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01,
        price=None,
        order_type="market",
        status=OrderStatus.PENDING,
        created_at=time.time(),
        updated_at=time.time()
    )

    success = await order_manager.submit_order(new_order)

    assert not success
    assert new_order.status == OrderStatus.FAILED
    assert "queue full" in new_order.error_message.lower()


@pytest.mark.asyncio
async def test_submit_order_circuit_breaker_open(order_manager, mexc_adapter):
    """Test order submission blocked by circuit breaker."""
    # Mock circuit breaker open
    mexc_adapter.create_market_order.side_effect = CircuitBreakerOpenException("Circuit open")

    order = Order(
        order_id="order_3",
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01,
        price=None,
        order_type="market",
        status=OrderStatus.PENDING,
        created_at=time.time(),
        updated_at=time.time()
    )

    success = await order_manager.submit_order(order)

    assert not success
    assert order.status == OrderStatus.FAILED
    assert "circuit" in order.error_message.lower()


@pytest.mark.asyncio
async def test_submit_order_retry_logic(order_manager, mexc_adapter):
    """Test retry logic with transient failures."""
    # First 2 attempts fail, 3rd succeeds
    mexc_adapter.create_market_order.side_effect = [
        Exception("Network error"),
        Exception("Timeout"),
        "MEXC_RETRY_SUCCESS"
    ]

    order = Order(
        order_id="order_4",
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01,
        price=None,
        order_type="market",
        status=OrderStatus.PENDING,
        created_at=time.time(),
        updated_at=time.time()
    )

    success = await order_manager.submit_order(order)

    assert success
    assert order.status == OrderStatus.SUBMITTED
    assert order.exchange_order_id == "MEXC_RETRY_SUCCESS"
    
    # Should have called 3 times
    assert mexc_adapter.create_market_order.call_count == 3


@pytest.mark.asyncio
async def test_submit_order_all_retries_fail(order_manager, mexc_adapter):
    """Test order fails after all retries exhausted."""
    # All 3 attempts fail
    mexc_adapter.create_market_order.side_effect = [
        Exception("Error 1"),
        Exception("Error 2"),
        Exception("Error 3")
    ]

    order = Order(
        order_id="order_5",
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01,
        price=None,
        order_type="market",
        status=OrderStatus.PENDING,
        created_at=time.time(),
        updated_at=time.time()
    )

    success = await order_manager.submit_order(order)

    assert not success
    assert order.status == OrderStatus.FAILED
    assert "after 3 attempts" in order.error_message.lower()


@pytest.mark.asyncio
async def test_submit_order_risk_manager_rejects(order_manager, risk_manager):
    """Test order rejected by RiskManager."""
    # Mock risk manager rejection
    result = MagicMock()
    result.can_proceed = False
    result.reason = "Daily loss limit exceeded"
    result.risk_score = 50.0
    risk_manager.can_open_position.return_value = result

    order = Order(
        order_id="order_6",
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01,
        price=50000.0,
        order_type="market",
        status=OrderStatus.PENDING,
        created_at=time.time(),
        updated_at=time.time()
    )

    # Provide current_positions to trigger risk validation
    success = await order_manager.submit_order(order, current_positions=[])

    assert not success
    assert order.status == OrderStatus.FAILED
    assert "risk check failed" in order.error_message.lower()


# ===== TEST: Order Cancellation =====

@pytest.mark.asyncio
async def test_cancel_order_success(order_manager, mexc_adapter):
    """Test successful order cancellation."""
    # Add order to tracking
    order = Order(
        order_id="order_7",
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01,
        price=50000.0,
        order_type="limit",
        status=OrderStatus.SUBMITTED,
        created_at=time.time(),
        updated_at=time.time(),
        exchange_order_id="MEXC_CANCEL_ME"
    )
    order_manager.orders[order.order_id] = order

    success = await order_manager.cancel_order(order.order_id)

    assert success
    assert order.status == OrderStatus.CANCELLED

    # Verify MEXC adapter was called
    mexc_adapter.cancel_order.assert_called_once_with(
        "BTC_USDT",
        "MEXC_CANCEL_ME"
    )


@pytest.mark.asyncio
async def test_cancel_order_unknown(order_manager):
    """Test cancelling unknown order."""
    success = await order_manager.cancel_order("unknown_order")

    assert not success


@pytest.mark.asyncio
async def test_cancel_order_wrong_status(order_manager):
    """Test cancelling order in wrong status."""
    # Add filled order
    order = Order(
        order_id="order_8",
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01,
        price=None,
        order_type="market",
        status=OrderStatus.FILLED,  # Already filled
        created_at=time.time(),
        updated_at=time.time()
    )
    order_manager.orders[order.order_id] = order

    success = await order_manager.cancel_order(order.order_id)

    assert not success
    assert order.status == OrderStatus.FILLED  # Status unchanged


# ===== TEST: Signal Handling =====

@pytest.mark.asyncio
async def test_on_signal_generated_s1(order_manager, mexc_adapter):
    """Test S1 signal creates order."""
    signal_data = {
        "signal_id": "signal_s1",
        "signal_type": "S1",
        "symbol": "BTC_USDT",
        "side": "buy",
        "quantity": 0.01,
        "price": None,
        "order_type": "market"
    }

    await order_manager._on_signal_generated(signal_data)

    # Should have created and submitted order
    assert "signal_s1" in order_manager.orders
    order = order_manager.orders["signal_s1"]
    assert order.status == OrderStatus.SUBMITTED
    assert order.symbol == "BTC_USDT"


@pytest.mark.asyncio
async def test_on_signal_generated_z1_ignored(order_manager, mexc_adapter):
    """Test Z1 signal is ignored (no order creation)."""
    signal_data = {
        "signal_type": "Z1",
        "symbol": "BTC_USDT",
        "side": "buy",
        "quantity": 0.01
    }

    await order_manager._on_signal_generated(signal_data)

    # Should not create any orders
    assert len(order_manager.orders) == 0


# ===== TEST: Getters =====

def test_get_order(order_manager):
    """Test get_order method."""
    order = Order(
        order_id="order_9",
        symbol="BTC_USDT",
        side="buy",
        quantity=0.01,
        price=None,
        order_type="market",
        status=OrderStatus.SUBMITTED,
        created_at=time.time(),
        updated_at=time.time()
    )
    order_manager.orders[order.order_id] = order

    retrieved = order_manager.get_order("order_9")
    assert retrieved is not None
    assert retrieved.order_id == "order_9"

    # Test unknown order
    assert order_manager.get_order("unknown") is None


def test_get_all_orders(order_manager):
    """Test get_all_orders method."""
    # Add multiple orders
    for i in range(3):
        order = Order(
            order_id=f"order_{i}",
            symbol="BTC_USDT" if i % 2 == 0 else "ETH_USDT",
            side="buy",
            quantity=0.01,
            price=None,
            order_type="market",
            status=OrderStatus.SUBMITTED,
            created_at=time.time(),
            updated_at=time.time()
        )
        order_manager.orders[order.order_id] = order

    # Get all orders
    all_orders = order_manager.get_all_orders()
    assert len(all_orders) == 3

    # Get filtered orders
    btc_orders = order_manager.get_all_orders(symbol="BTC_USDT")
    assert len(btc_orders) == 2


def test_get_metrics(order_manager):
    """Test get_metrics method."""
    # Add orders in different statuses
    statuses = [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.FAILED]
    for i, status in enumerate(statuses):
        order = Order(
            order_id=f"order_{i}",
            symbol="BTC_USDT",
            side="buy",
            quantity=0.01,
            price=None,
            order_type="market",
            status=status,
            created_at=time.time(),
            updated_at=time.time()
        )
        order_manager.orders[order.order_id] = order

    metrics = order_manager.get_metrics()
    
    assert metrics["total_orders"] == 5
    assert metrics["pending"] == 1
    assert metrics["submitted"] == 1
    assert metrics["filled"] == 1
    assert metrics["cancelled"] == 1
    assert metrics["failed"] == 1


# ===== TEST: Lifecycle =====

@pytest.mark.asyncio
async def test_start_stop(order_manager):
    """Test start and stop methods."""
    assert not order_manager._running

    await order_manager.start()
    assert order_manager._running
    assert order_manager._status_poll_task is not None
    assert order_manager._cleanup_task is not None

    await order_manager.stop()
    assert not order_manager._running
    assert len(order_manager.orders) == 0  # Cleaned up


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
