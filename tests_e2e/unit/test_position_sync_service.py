"""
Unit Tests for PositionSyncService
===================================
Tests position synchronization, liquidation detection, and EventBus integration.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

# Import the components we're testing
from src.domain.services.position_sync_service import PositionSyncService, LocalPosition
from src.infrastructure.adapters.mexc_adapter import PositionResponse
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
    adapter.get_positions = AsyncMock(return_value=[])
    return adapter


@pytest.fixture
def risk_manager():
    """Create mock RiskManager."""
    manager = AsyncMock()
    manager.check_margin_ratio = AsyncMock()
    return manager


@pytest.fixture
def position_sync(event_bus, mexc_adapter, risk_manager):
    """Create PositionSyncService instance."""
    return PositionSyncService(
        event_bus=event_bus,
        mexc_adapter=mexc_adapter,
        risk_manager=risk_manager,
        max_positions=100
    )


# ===== TEST: Initialization =====

def test_initialization(position_sync):
    """Test PositionSyncService initializes correctly."""
    assert position_sync.max_positions == 100
    assert len(position_sync.positions) == 0
    assert position_sync._running == False


# ===== TEST: Order Fill Handling =====

@pytest.mark.asyncio
async def test_on_order_filled_new_position(position_sync):
    """Test creating new position from order fill."""
    order_fill_data = {
        "symbol": "BTC_USDT",
        "side": "buy",
        "quantity": 0.01,
        "price": 50000.0
    }

    await position_sync._on_order_filled(order_fill_data)

    # Should have created new position
    assert "BTC_USDT" in position_sync.positions
    position = position_sync.positions["BTC_USDT"]
    
    assert position.symbol == "BTC_USDT"
    assert position.side == "LONG"
    assert position.quantity == 0.01
    assert position.entry_price == 50000.0


@pytest.mark.asyncio
async def test_on_order_filled_add_to_long(position_sync):
    """Test adding to existing long position."""
    # Create initial position
    position_sync.positions["BTC_USDT"] = LocalPosition(
        symbol="BTC_USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        current_price=50000.0,
        liquidation_price=0.0,
        unrealized_pnl=0.0,
        margin=0.0,
        leverage=1.0,
        margin_ratio=100.0,
        opened_at=time.time(),
        updated_at=time.time()
    )

    # Add to position
    order_fill_data = {
        "symbol": "BTC_USDT",
        "side": "buy",
        "quantity": 0.01,
        "price": 51000.0
    }

    await position_sync._on_order_filled(order_fill_data)

    position = position_sync.positions["BTC_USDT"]
    
    # Should have averaged entry price
    assert position.quantity == 0.02
    assert position.entry_price == 50500.0  # (50000*0.01 + 51000*0.01) / 0.02


@pytest.mark.asyncio
async def test_on_order_filled_close_long(position_sync):
    """Test closing long position via sell."""
    # Create initial position
    position_sync.positions["BTC_USDT"] = LocalPosition(
        symbol="BTC_USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        current_price=50000.0,
        liquidation_price=0.0,
        unrealized_pnl=0.0,
        margin=0.0,
        leverage=1.0,
        margin_ratio=100.0,
        opened_at=time.time(),
        updated_at=time.time()
    )

    # Close position
    order_fill_data = {
        "symbol": "BTC_USDT",
        "side": "sell",
        "quantity": 0.01,
        "price": 51000.0
    }

    await position_sync._on_order_filled(order_fill_data)

    # Position should be removed
    assert "BTC_USDT" not in position_sync.positions


@pytest.mark.asyncio
async def test_on_order_filled_max_positions(position_sync):
    """Test max positions limit."""
    # Set low limit
    position_sync.max_positions = 1
    
    # Create first position
    position_sync.positions["BTC_USDT"] = LocalPosition(
        symbol="BTC_USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        current_price=50000.0,
        liquidation_price=0.0,
        unrealized_pnl=0.0,
        margin=0.0,
        leverage=1.0,
        margin_ratio=100.0,
        opened_at=time.time(),
        updated_at=time.time()
    )

    # Try to create second position
    order_fill_data = {
        "symbol": "ETH_USDT",
        "side": "buy",
        "quantity": 1.0,
        "price": 3000.0
    }

    await position_sync._on_order_filled(order_fill_data)

    # Should not have created new position
    assert "ETH_USDT" not in position_sync.positions
    assert len(position_sync.positions) == 1


# ===== TEST: Position Sync =====

@pytest.mark.asyncio
async def test_sync_positions_detect_liquidation(position_sync, mexc_adapter):
    """Test detecting liquidation when position missing on exchange."""
    # Create local position
    position_sync.positions["BTC_USDT"] = LocalPosition(
        symbol="BTC_USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        current_price=50000.0,
        liquidation_price=45000.0,
        unrealized_pnl=0.0,
        margin=500.0,
        leverage=10.0,
        margin_ratio=150.0,
        opened_at=time.time(),
        updated_at=time.time()
    )

    # Mock MEXC returns empty positions (liquidation)
    mexc_adapter.get_positions.return_value = []

    # Start sync service
    await position_sync.start()
    
    # Wait for one sync cycle
    await asyncio.sleep(0.5)
    
    # Stop service
    await position_sync.stop()

    # Position should be removed (liquidated)
    assert "BTC_USDT" not in position_sync.positions


@pytest.mark.asyncio
async def test_sync_positions_update_existing(position_sync, mexc_adapter):
    """Test updating existing position from exchange."""
    # Create local position
    position_sync.positions["BTC_USDT"] = LocalPosition(
        symbol="BTC_USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        current_price=50000.0,
        liquidation_price=45000.0,
        unrealized_pnl=0.0,
        margin=500.0,
        leverage=10.0,
        margin_ratio=150.0,
        opened_at=time.time(),
        updated_at=time.time()
    )

    # Mock MEXC returns updated position
    exchange_position = PositionResponse(
        symbol="BTC_USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        current_price=52000.0,  # Price increased
        unrealized_pnl=200.0,   # Profit
        margin_ratio=160.0,     # Margin ratio improved
        liquidation_price=45000.0,
        leverage=10.0,
        margin=500.0
    )
    mexc_adapter.get_positions.return_value = [exchange_position]

    # Manually trigger sync (instead of waiting for background task)
    await position_sync.start()
    await asyncio.sleep(0.5)
    await position_sync.stop()

    # Position should be updated
    position = position_sync.positions["BTC_USDT"]
    assert position.current_price == 52000.0
    assert position.unrealized_pnl == 200.0
    assert position.margin_ratio == 160.0


@pytest.mark.asyncio
async def test_sync_positions_detect_new_position(position_sync, mexc_adapter):
    """Test detecting new position opened externally on exchange."""
    # Mock MEXC returns new position not in local tracking
    exchange_position = PositionResponse(
        symbol="ETH_USDT",
        side="LONG",
        quantity=1.0,
        entry_price=3000.0,
        current_price=3000.0,
        unrealized_pnl=0.0,
        margin_ratio=150.0,
        liquidation_price=2700.0,
        leverage=5.0,
        margin=600.0
    )
    mexc_adapter.get_positions.return_value = [exchange_position]

    await position_sync.start()
    await asyncio.sleep(0.5)
    await position_sync.stop()

    # Should have added new position
    assert "ETH_USDT" in position_sync.positions
    position = position_sync.positions["ETH_USDT"]
    assert position.side == "LONG"
    assert position.quantity == 1.0


@pytest.mark.asyncio
async def test_sync_positions_circuit_breaker_open(position_sync, mexc_adapter):
    """Test graceful handling when circuit breaker is open."""
    # Mock circuit breaker open
    mexc_adapter.get_positions.side_effect = CircuitBreakerOpenException("Circuit open")

    # Create local position
    position_sync.positions["BTC_USDT"] = LocalPosition(
        symbol="BTC_USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        current_price=50000.0,
        liquidation_price=45000.0,
        unrealized_pnl=0.0,
        margin=500.0,
        leverage=10.0,
        margin_ratio=150.0,
        opened_at=time.time(),
        updated_at=time.time()
    )

    await position_sync.start()
    await asyncio.sleep(0.5)
    await position_sync.stop()

    # Position should still exist (not removed due to circuit breaker)
    assert "BTC_USDT" in position_sync.positions


# ===== TEST: Getters =====

def test_get_position(position_sync):
    """Test get_position method."""
    position = LocalPosition(
        symbol="BTC_USDT",
        side="LONG",
        quantity=0.01,
        entry_price=50000.0,
        current_price=50000.0,
        liquidation_price=45000.0,
        unrealized_pnl=0.0,
        margin=500.0,
        leverage=10.0,
        margin_ratio=150.0,
        opened_at=time.time(),
        updated_at=time.time()
    )
    position_sync.positions["BTC_USDT"] = position

    retrieved = position_sync.get_position("BTC_USDT")
    assert retrieved is not None
    assert retrieved.symbol == "BTC_USDT"

    # Test unknown position
    assert position_sync.get_position("UNKNOWN") is None


def test_get_all_positions(position_sync):
    """Test get_all_positions method."""
    # Add multiple positions
    for i, symbol in enumerate(["BTC_USDT", "ETH_USDT", "XRP_USDT"]):
        position = LocalPosition(
            symbol=symbol,
            side="LONG",
            quantity=0.01,
            entry_price=50000.0,
            current_price=50000.0,
            liquidation_price=45000.0,
            unrealized_pnl=0.0,
            margin=500.0,
            leverage=10.0,
            margin_ratio=150.0,
            opened_at=time.time(),
            updated_at=time.time()
        )
        position_sync.positions[symbol] = position

    all_positions = position_sync.get_all_positions()
    assert len(all_positions) == 3


def test_get_metrics(position_sync):
    """Test get_metrics method."""
    # Add positions with different sides and P&L
    positions_data = [
        ("BTC_USDT", "LONG", 100.0, 150.0),
        ("ETH_USDT", "SHORT", -50.0, 120.0),
        ("XRP_USDT", "LONG", 200.0, 80.0),
    ]

    for symbol, side, unrealized_pnl, margin_ratio in positions_data:
        position = LocalPosition(
            symbol=symbol,
            side=side,
            quantity=0.01,
            entry_price=50000.0,
            current_price=50000.0,
            liquidation_price=45000.0,
            unrealized_pnl=unrealized_pnl,
            margin=500.0,
            leverage=10.0,
            margin_ratio=margin_ratio,
            opened_at=time.time(),
            updated_at=time.time()
        )
        position_sync.positions[symbol] = position

    metrics = position_sync.get_metrics()
    
    assert metrics["total_positions"] == 3
    assert metrics["long_positions"] == 2
    assert metrics["short_positions"] == 1
    assert metrics["total_unrealized_pnl"] == 250.0  # 100 - 50 + 200
    assert metrics["avg_margin_ratio"] == 116.67  # (150 + 120 + 80) / 3
    assert metrics["min_margin_ratio"] == 80.0


# ===== TEST: Lifecycle =====

@pytest.mark.asyncio
async def test_start_stop(position_sync):
    """Test start and stop methods."""
    assert not position_sync._running

    await position_sync.start()
    assert position_sync._running
    assert position_sync._sync_task is not None

    await position_sync.stop()
    assert not position_sync._running
    assert len(position_sync.positions) == 0  # Cleaned up


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
