"""
Unit Tests for MexcPaperAdapter
================================
Tests paper trading adapter functionality, especially get_positions() method.
"""

import pytest
import asyncio
from unittest.mock import MagicMock

from src.infrastructure.adapters.mexc_paper_adapter import MexcPaperAdapter
from src.infrastructure.adapters.mexc_adapter import PositionResponse
from src.core.logger import StructuredLogger


@pytest.fixture
def logger():
    """Create mock logger."""
    return MagicMock(spec=StructuredLogger)


@pytest.fixture
def adapter(logger):
    """Create MexcPaperAdapter instance."""
    return MexcPaperAdapter(logger=logger, initial_balance=10000.0)


# ===== TEST: get_positions() - Empty positions =====

@pytest.mark.asyncio
async def test_get_positions_empty(adapter):
    """Test get_positions returns empty list when no positions."""
    positions = await adapter.get_positions()

    assert isinstance(positions, list)
    assert len(positions) == 0


# ===== TEST: get_positions() - Single LONG position =====

@pytest.mark.asyncio
async def test_get_positions_single_long(adapter):
    """Test get_positions returns single LONG position."""
    # Set leverage first
    await adapter.set_leverage("BTC_USDT", 5)

    # Place LONG order (BUY to open)
    order = await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="BUY",
        position_side="LONG",
        order_type="MARKET",
        quantity=0.01
    )

    # Get positions
    positions = await adapter.get_positions()

    assert len(positions) == 1

    position = positions[0]
    assert isinstance(position, PositionResponse)
    assert position.symbol == "BTC_USDT"
    assert position.side == "LONG"
    assert position.quantity == 0.01
    assert position.entry_price > 0
    assert position.current_price > 0
    assert position.leverage == 5
    assert position.liquidation_price > 0


# ===== TEST: get_positions() - Single SHORT position =====

@pytest.mark.asyncio
async def test_get_positions_single_short(adapter):
    """Test get_positions returns single SHORT position."""
    # Set leverage first
    await adapter.set_leverage("ETH_USDT", 3)

    # Place SHORT order (SELL to open)
    order = await adapter.place_futures_order(
        symbol="ETH_USDT",
        side="SELL",
        position_side="SHORT",
        order_type="MARKET",
        quantity=0.5
    )

    # Get positions
    positions = await adapter.get_positions()

    assert len(positions) == 1

    position = positions[0]
    assert isinstance(position, PositionResponse)
    assert position.symbol == "ETH_USDT"
    assert position.side == "SHORT"
    assert position.quantity == 0.5
    assert position.leverage == 3


# ===== TEST: get_positions() - Multiple positions =====

@pytest.mark.asyncio
async def test_get_positions_multiple(adapter):
    """Test get_positions returns multiple positions (LONG + SHORT)."""
    # Open LONG BTC position
    await adapter.set_leverage("BTC_USDT", 5)
    await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="BUY",
        position_side="LONG",
        order_type="MARKET",
        quantity=0.01
    )

    # Open SHORT ETH position
    await adapter.set_leverage("ETH_USDT", 3)
    await adapter.place_futures_order(
        symbol="ETH_USDT",
        side="SELL",
        position_side="SHORT",
        order_type="MARKET",
        quantity=0.5
    )

    # Open LONG SOL position
    await adapter.set_leverage("SOL_USDT", 2)
    await adapter.place_futures_order(
        symbol="SOL_USDT",
        side="BUY",
        position_side="LONG",
        order_type="MARKET",
        quantity=10.0
    )

    # Get positions
    positions = await adapter.get_positions()

    assert len(positions) == 3

    # Verify all are PositionResponse objects
    for position in positions:
        assert isinstance(position, PositionResponse)

    # Verify symbols
    symbols = {p.symbol for p in positions}
    assert symbols == {"BTC_USDT", "ETH_USDT", "SOL_USDT"}

    # Verify sides
    btc_position = next(p for p in positions if p.symbol == "BTC_USDT")
    assert btc_position.side == "LONG"

    eth_position = next(p for p in positions if p.symbol == "ETH_USDT")
    assert eth_position.side == "SHORT"

    sol_position = next(p for p in positions if p.symbol == "SOL_USDT")
    assert sol_position.side == "LONG"


# ===== TEST: get_positions() - Filters zero quantity =====

@pytest.mark.asyncio
async def test_get_positions_filters_zero_quantity(adapter):
    """Test get_positions excludes closed positions (zero quantity)."""
    # Open position
    await adapter.set_leverage("BTC_USDT", 5)
    await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="BUY",
        position_side="LONG",
        order_type="MARKET",
        quantity=0.01
    )

    # Verify position exists
    positions_before = await adapter.get_positions()
    assert len(positions_before) == 1

    # Close position completely
    await adapter.close_position("BTC_USDT", "LONG")

    # Verify position is filtered out
    positions_after = await adapter.get_positions()
    assert len(positions_after) == 0


# ===== TEST: get_positions() - P&L calculation =====

@pytest.mark.asyncio
async def test_get_positions_calculates_pnl(adapter):
    """Test get_positions calculates unrealized P&L correctly."""
    # Mock market price to ensure predictable P&L
    original_price = adapter._market_prices["BTC_USDT"]
    adapter._market_prices["BTC_USDT"] = 50000.0

    # Open LONG position at 50000
    await adapter.set_leverage("BTC_USDT", 5)
    await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="BUY",
        position_side="LONG",
        order_type="LIMIT",
        quantity=0.01,
        price=50000.0
    )

    # Change market price to 52000 (profit)
    adapter._market_prices["BTC_USDT"] = 52000.0

    # Get positions
    positions = await adapter.get_positions()

    assert len(positions) == 1
    position = positions[0]

    # Expected P&L: 0.01 * (52000 - 50000) = 20 USDT profit
    assert position.unrealized_pnl == pytest.approx(20.0, rel=1e-2)
    assert position.entry_price == 50000.0
    assert position.current_price >= 51000.0  # Account for small variation

    # Restore original price
    adapter._market_prices["BTC_USDT"] = original_price


# ===== TEST: get_positions() - SHORT P&L calculation =====

@pytest.mark.asyncio
async def test_get_positions_calculates_short_pnl(adapter):
    """Test get_positions calculates SHORT unrealized P&L correctly."""
    # Mock market price
    adapter._market_prices["ETH_USDT"] = 3000.0

    # Open SHORT position at 3000
    await adapter.set_leverage("ETH_USDT", 3)
    await adapter.place_futures_order(
        symbol="ETH_USDT",
        side="SELL",
        position_side="SHORT",
        order_type="LIMIT",
        quantity=1.0,
        price=3000.0
    )

    # Change market price to 2900 (profit for SHORT)
    adapter._market_prices["ETH_USDT"] = 2900.0

    # Get positions
    positions = await adapter.get_positions()

    assert len(positions) == 1
    position = positions[0]

    # Expected P&L: 1.0 * (3000 - 2900) = 100 USDT profit
    assert position.unrealized_pnl == pytest.approx(100.0, rel=1e-2)
    assert position.side == "SHORT"


# ===== TEST: get_positions() - Margin calculation =====

@pytest.mark.asyncio
async def test_get_positions_calculates_margin(adapter):
    """Test get_positions calculates margin correctly."""
    # Mock market price
    adapter._market_prices["BTC_USDT"] = 50000.0

    # Open position with 5x leverage
    await adapter.set_leverage("BTC_USDT", 5)
    await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="BUY",
        position_side="LONG",
        order_type="LIMIT",
        quantity=0.1,
        price=50000.0
    )

    # Get positions
    positions = await adapter.get_positions()

    assert len(positions) == 1
    position = positions[0]

    # Expected margin: (0.1 * 50000) / 5 = 1000 USDT
    assert position.margin == pytest.approx(1000.0, rel=1e-2)
    assert position.leverage == 5


# ===== TEST: get_positions() - Margin ratio calculation =====

@pytest.mark.asyncio
async def test_get_positions_calculates_margin_ratio(adapter):
    """Test get_positions calculates margin ratio."""
    # Mock market price
    adapter._market_prices["BTC_USDT"] = 50000.0

    # Open position
    await adapter.set_leverage("BTC_USDT", 5)
    await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="BUY",
        position_side="LONG",
        order_type="LIMIT",
        quantity=0.1,
        price=50000.0
    )

    # Get positions
    positions = await adapter.get_positions()

    assert len(positions) == 1
    position = positions[0]

    # Margin ratio should be > 0 (healthy position)
    assert position.margin_ratio > 0
    # In paper trading with no losses, should be >= 100%
    assert position.margin_ratio >= 90.0


# ===== TEST: get_positions() - Returns PositionResponse type =====

@pytest.mark.asyncio
async def test_get_positions_returns_position_response_type(adapter):
    """Test get_positions returns correct dataclass type."""
    # Open position
    await adapter.set_leverage("BTC_USDT", 5)
    await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="BUY",
        position_side="LONG",
        order_type="MARKET",
        quantity=0.01
    )

    # Get positions
    positions = await adapter.get_positions()

    assert len(positions) == 1
    position = positions[0]

    # Verify type
    assert isinstance(position, PositionResponse)

    # Verify all required fields exist
    assert hasattr(position, 'symbol')
    assert hasattr(position, 'side')
    assert hasattr(position, 'quantity')
    assert hasattr(position, 'entry_price')
    assert hasattr(position, 'current_price')
    assert hasattr(position, 'unrealized_pnl')
    assert hasattr(position, 'margin_ratio')
    assert hasattr(position, 'liquidation_price')
    assert hasattr(position, 'leverage')
    assert hasattr(position, 'margin')


# ===== TEST: get_positions() - Liquidation price included =====

@pytest.mark.asyncio
async def test_get_positions_includes_liquidation_price(adapter):
    """Test get_positions includes liquidation price."""
    # Open position with leverage
    await adapter.set_leverage("BTC_USDT", 10)
    await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="BUY",
        position_side="LONG",
        order_type="MARKET",
        quantity=0.01
    )

    # Get positions
    positions = await adapter.get_positions()

    assert len(positions) == 1
    position = positions[0]

    # Liquidation price should be set (non-zero for leveraged position)
    assert position.liquidation_price > 0
    # For LONG with 10x leverage, liquidation should be ~10% below entry
    assert position.liquidation_price < position.entry_price


# ===== TEST: get_positions() - Both LONG and SHORT for same symbol =====

@pytest.mark.asyncio
async def test_get_positions_long_and_short_same_symbol(adapter):
    """Test get_positions can return both LONG and SHORT for same symbol."""
    # MEXC Futures allows both LONG and SHORT positions simultaneously (hedge mode)

    # Open LONG position
    await adapter.set_leverage("BTC_USDT", 5)
    await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="BUY",
        position_side="LONG",
        order_type="MARKET",
        quantity=0.01
    )

    # Open SHORT position for same symbol
    await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="SELL",
        position_side="SHORT",
        order_type="MARKET",
        quantity=0.02
    )

    # Get positions
    positions = await adapter.get_positions()

    # Should have 2 positions (LONG and SHORT)
    assert len(positions) == 2

    # Verify both sides exist
    sides = {p.side for p in positions}
    assert sides == {"LONG", "SHORT"}

    # Verify same symbol
    symbols = {p.symbol for p in positions}
    assert len(symbols) == 1
    assert "BTC_USDT" in symbols


# ===== TEST: Integration with PositionSyncService =====

@pytest.mark.asyncio
async def test_get_positions_compatibility_with_position_sync_service(adapter):
    """Test get_positions returns data compatible with PositionSyncService."""
    # This test verifies the returned data structure matches what PositionSyncService expects

    # Open multiple positions
    await adapter.set_leverage("BTC_USDT", 5)
    await adapter.place_futures_order(
        symbol="BTC_USDT",
        side="BUY",
        position_side="LONG",
        order_type="MARKET",
        quantity=0.01
    )

    await adapter.set_leverage("ETH_USDT", 3)
    await adapter.place_futures_order(
        symbol="ETH_USDT",
        side="SELL",
        position_side="SHORT",
        order_type="MARKET",
        quantity=0.5
    )

    # Get positions (as PositionSyncService would)
    positions = await adapter.get_positions()

    # Verify type
    assert isinstance(positions, list)

    # Verify all elements are PositionResponse
    for position in positions:
        assert isinstance(position, PositionResponse)

        # Verify required fields for PositionSyncService
        assert isinstance(position.symbol, str)
        assert position.side in ["LONG", "SHORT"]
        assert isinstance(position.quantity, (int, float))
        assert isinstance(position.entry_price, (int, float))
        assert isinstance(position.current_price, (int, float))
        assert isinstance(position.unrealized_pnl, (int, float))
        assert isinstance(position.margin_ratio, (int, float))
        assert isinstance(position.liquidation_price, (int, float))
        assert isinstance(position.leverage, (int, float))
        assert isinstance(position.margin, (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
