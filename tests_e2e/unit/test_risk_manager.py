"""
Unit Tests for RiskManager
===========================
Tests all 6 risk checks, event emission, configuration loading, and thread safety.

Coverage target: 85%+
Test count: 20+ tests
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.domain.services.risk_manager import RiskManager, RiskCheckResult, RiskAlertSeverity, RiskAlertType
from src.domain.models.trading import Position, Order, OrderSide, OrderType, OrderStatus, PositionStatus
from src.core.event_bus import EventBus
from src.infrastructure.config.settings import AppSettings


# === Fixtures ===

@pytest.fixture
def event_bus():
    """Create EventBus instance."""
    return EventBus()


@pytest.fixture
def settings():
    """Create test settings with known values."""
    settings = AppSettings()
    # Ensure risk manager settings are set to known test values
    settings.risk_management.risk_manager.max_position_size_percent = Decimal('10.0')
    settings.risk_management.risk_manager.max_concurrent_positions = 3
    settings.risk_management.risk_manager.max_symbol_concentration_percent = Decimal('30.0')
    settings.risk_management.risk_manager.daily_loss_limit_percent = Decimal('5.0')
    settings.risk_management.risk_manager.max_drawdown_percent = Decimal('15.0')
    settings.risk_management.risk_manager.max_margin_utilization_percent = Decimal('80.0')
    return settings


@pytest.fixture
def risk_manager(event_bus, settings):
    """Create RiskManager instance with 10,000 USDT capital."""
    return RiskManager(
        event_bus=event_bus,
        settings=settings,
        initial_capital=Decimal('10000')
    )


@pytest.fixture
def sample_position():
    """Create sample open position."""
    return Position(
        position_id="pos_1",
        symbol="BTC_USDT",
        exchange="MEXC",
        side=OrderSide.BUY,
        size=Decimal('0.1'),
        entry_price=Decimal('50000'),
        leverage=Decimal('1'),
        status=PositionStatus.OPEN
    )


@pytest.fixture
def sample_order():
    """Create sample order."""
    return Order(
        order_id="order_1",
        symbol="BTC_USDT",
        exchange="MEXC",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal('0.1'),
        price=Decimal('50000'),
        status=OrderStatus.PENDING
    )


# === Test Check 1: Max Position Size ===

@pytest.mark.asyncio
async def test_check1_position_size_within_limit(risk_manager):
    """Test that position within 10% limit is approved."""
    # 10% of 10,000 = 1,000 USDT max
    # Position: 0.01 BTC * 50,000 = 500 USDT (50% of limit)
    result = await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.01'),
        price=Decimal('50000'),
        current_positions=[]
    )

    assert result.can_proceed is True
    assert "max_position_size" not in result.failed_checks
    assert result.risk_score < 10  # Low risk


@pytest.mark.asyncio
async def test_check1_position_size_exceeds_limit(risk_manager):
    """Test that position exceeding 10% limit is rejected."""
    # 10% of 10,000 = 1,000 USDT max
    # Position: 0.03 BTC * 50,000 = 1,500 USDT (exceeds limit)
    result = await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.03'),
        price=Decimal('50000'),
        current_positions=[]
    )

    assert result.can_proceed is False
    assert "max_position_size" in result.failed_checks
    assert "exceeds max" in result.reason.lower()


# === Test Check 2: Max Concurrent Positions ===

@pytest.mark.asyncio
async def test_check2_positions_within_limit(risk_manager):
    """Test that 2 open positions (< 3) is approved."""
    positions = [
        Position(
            position_id=f"pos_{i}",
            symbol=f"BTC_USDT",
            exchange="MEXC",
            side=OrderSide.BUY,
            size=Decimal('0.01'),
            entry_price=Decimal('50000'),
            leverage=Decimal('1'),
            status=PositionStatus.OPEN
        )
        for i in range(2)
    ]

    result = await risk_manager.can_open_position(
        symbol="ETH_USDT",
        side="buy",
        quantity=Decimal('0.1'),
        price=Decimal('3000'),
        current_positions=positions
    )

    assert result.can_proceed is True
    assert "max_concurrent_positions" not in result.failed_checks


@pytest.mark.asyncio
async def test_check2_positions_at_limit(risk_manager):
    """Test that 3rd position (at limit) is rejected."""
    positions = [
        Position(
            position_id=f"pos_{i}",
            symbol=f"SYMBOL_{i}",
            exchange="MEXC",
            side=OrderSide.BUY,
            size=Decimal('0.01'),
            entry_price=Decimal('1000'),
            leverage=Decimal('1'),
            status=PositionStatus.OPEN
        )
        for i in range(3)
    ]

    result = await risk_manager.can_open_position(
        symbol="NEW_USDT",
        side="buy",
        quantity=Decimal('0.1'),
        price=Decimal('100'),
        current_positions=positions
    )

    assert result.can_proceed is False
    assert "max_concurrent_positions" in result.failed_checks


@pytest.mark.asyncio
async def test_check2_closed_positions_not_counted(risk_manager):
    """Test that closed positions don't count toward limit."""
    positions = [
        Position(
            position_id=f"pos_{i}",
            symbol=f"SYMBOL_{i}",
            exchange="MEXC",
            side=OrderSide.BUY,
            size=Decimal('0.01'),
            entry_price=Decimal('1000'),
            leverage=Decimal('1'),
            status=PositionStatus.CLOSED if i == 2 else PositionStatus.OPEN
        )
        for i in range(3)
    ]

    result = await risk_manager.can_open_position(
        symbol="NEW_USDT",
        side="buy",
        quantity=Decimal('0.01'),
        price=Decimal('1000'),
        current_positions=positions
    )

    # 2 open + 1 closed = 2 open (below limit of 3)
    assert result.can_proceed is True


# === Test Check 3: Position Concentration ===

@pytest.mark.asyncio
async def test_check3_concentration_within_limit(risk_manager):
    """Test that 20% concentration in one symbol is approved."""
    # 30% of 10,000 = 3,000 USDT max per symbol
    # Existing: 0.01 BTC * 50,000 = 500 USDT
    # New: 0.03 BTC * 50,000 = 1,500 USDT
    # Total: 2,000 USDT (67% of limit)
    existing_position = Position(
        position_id="pos_1",
        symbol="BTC_USDT",
        exchange="MEXC",
        side=OrderSide.BUY,
        size=Decimal('0.01'),
        entry_price=Decimal('50000'),
        leverage=Decimal('1'),
        status=PositionStatus.OPEN
    )

    result = await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.03'),
        price=Decimal('50000'),
        current_positions=[existing_position]
    )

    # Should fail because total position size exceeds 10% limit (check 1)
    # but concentration is OK
    assert "symbol_concentration" not in result.failed_checks


@pytest.mark.asyncio
async def test_check3_concentration_exceeds_limit(risk_manager):
    """Test that 35% concentration in one symbol is rejected."""
    # 30% of 10,000 = 3,000 USDT max per symbol
    # Existing: 0.04 BTC * 50,000 = 2,000 USDT
    # New: 0.03 BTC * 50,000 = 1,500 USDT
    # Total: 3,500 USDT (exceeds 3,000 limit)
    existing_position = Position(
        position_id="pos_1",
        symbol="BTC_USDT",
        exchange="MEXC",
        side=OrderSide.BUY,
        size=Decimal('0.04'),
        entry_price=Decimal('50000'),
        leverage=Decimal('1'),
        status=PositionStatus.OPEN
    )

    result = await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.03'),
        price=Decimal('50000'),
        current_positions=[existing_position]
    )

    # Will fail multiple checks
    assert result.can_proceed is False
    assert "symbol_concentration" in result.failed_checks


# === Test Check 4: Daily Loss Limit ===

@pytest.mark.asyncio
async def test_check4_daily_loss_within_limit(risk_manager):
    """Test that 3% daily loss is approved."""
    # 5% of 10,000 = 500 USDT max daily loss
    # Set daily loss to 300 USDT (60% of limit)
    await risk_manager.update_capital(
        new_capital=Decimal('9700'),
        pnl_change=Decimal('-300')
    )

    result = await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.01'),
        price=Decimal('50000'),
        current_positions=[]
    )

    assert result.can_proceed is True
    assert "daily_loss_limit" not in result.failed_checks


@pytest.mark.asyncio
async def test_check4_daily_loss_exceeds_limit(risk_manager):
    """Test that 6% daily loss is rejected."""
    # 5% of 10,000 = 500 USDT max daily loss
    # Set daily loss to 600 USDT (exceeds limit)
    await risk_manager.update_capital(
        new_capital=Decimal('9400'),
        pnl_change=Decimal('-600')
    )

    result = await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.01'),
        price=Decimal('50000'),
        current_positions=[]
    )

    assert result.can_proceed is False
    assert "daily_loss_limit" in result.failed_checks


# === Test Check 5: Max Drawdown ===

@pytest.mark.asyncio
async def test_check5_drawdown_within_limit(risk_manager):
    """Test that 10% drawdown is approved."""
    # 15% of 10,000 = 1,500 USDT max drawdown
    # Peak: 10,000, Current: 9,000 = 10% drawdown
    await risk_manager.update_capital(Decimal('9000'))

    result = await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.01'),
        price=Decimal('50000'),
        current_positions=[]
    )

    assert result.can_proceed is True
    assert "max_drawdown" not in result.failed_checks


@pytest.mark.asyncio
async def test_check5_drawdown_exceeds_limit(risk_manager):
    """Test that 16% drawdown is rejected."""
    # 15% of 10,000 = 1,500 USDT max drawdown
    # Peak: 10,000, Current: 8,400 = 16% drawdown
    await risk_manager.update_capital(Decimal('8400'))

    result = await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.01'),
        price=Decimal('50000'),
        current_positions=[]
    )

    assert result.can_proceed is False
    assert "max_drawdown" in result.failed_checks


# === Test Check 6: Margin Utilization ===

@pytest.mark.asyncio
async def test_check6_margin_within_limit(risk_manager):
    """Test that 70% margin utilization is approved."""
    result = await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.01'),
        price=Decimal('50000'),
        current_positions=[],
        current_margin_ratio=Decimal('70.0'),
        available_margin=Decimal('3000')
    )

    assert result.can_proceed is True
    assert "margin_utilization" not in result.failed_checks


@pytest.mark.asyncio
async def test_check6_margin_exceeds_limit(risk_manager):
    """Test that 85% margin utilization is rejected."""
    result = await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.01'),
        price=Decimal('50000'),
        current_positions=[],
        current_margin_ratio=Decimal('85.0'),
        available_margin=Decimal('1000')
    )

    assert result.can_proceed is False
    assert "margin_utilization" in result.failed_checks


# === Test EventBus Integration ===

@pytest.mark.asyncio
async def test_risk_alert_emitted_on_rejection(event_bus, settings):
    """Test that risk_alert event is emitted when order is rejected."""
    # Track emitted events
    events_received = []

    async def capture_event(data: Dict[str, Any]):
        events_received.append(data)

    await event_bus.subscribe("risk_alert", capture_event)

    risk_manager = RiskManager(event_bus, settings, Decimal('10000'))

    # Trigger rejection (position size exceeds limit)
    await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.5'),  # 25,000 USDT (exceeds 10%)
        price=Decimal('50000'),
        current_positions=[]
    )

    # Give event bus time to process
    await asyncio.sleep(0.1)

    # Check event was emitted
    assert len(events_received) == 1
    event = events_received[0]
    assert event["type"] == "risk_alert"
    assert event["severity"] == RiskAlertSeverity.WARNING.value
    assert event["alert_type"] == RiskAlertType.ORDER_REJECTED.value
    assert "BTC_USDT" in event["message"]


# === Test validate_order() Method ===

@pytest.mark.asyncio
async def test_validate_order_with_limit_order(risk_manager, sample_order):
    """Test validate_order() with limit order (has price)."""
    result = await risk_manager.validate_order(sample_order, current_positions=[])

    assert result.can_proceed is True


@pytest.mark.asyncio
async def test_validate_order_with_market_order(risk_manager):
    """Test validate_order() with market order (no price)."""
    market_order = Order(
        order_id="order_1",
        symbol="BTC_USDT",
        exchange="MEXC",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal('0.1'),
        price=None  # Market order has no price
    )

    result = await risk_manager.validate_order(market_order, current_positions=[])

    # Should approve (can't validate without price)
    assert result.can_proceed is True


# === Test Capital Tracking ===

@pytest.mark.asyncio
async def test_equity_peak_tracking(risk_manager):
    """Test that equity peak is tracked correctly."""
    assert risk_manager.equity_peak == Decimal('10000')

    # Increase capital
    await risk_manager.update_capital(Decimal('11000'))
    assert risk_manager.equity_peak == Decimal('11000')

    # Decrease capital (peak should stay at 11000)
    await risk_manager.update_capital(Decimal('10500'))
    assert risk_manager.equity_peak == Decimal('11000')


@pytest.mark.asyncio
async def test_daily_pnl_reset(risk_manager):
    """Test that daily P&L resets at midnight."""
    # Set daily P&L
    await risk_manager.update_capital(Decimal('9500'), pnl_change=Decimal('-500'))
    assert risk_manager.daily_pnl == Decimal('-500')

    # Manually trigger reset by changing date
    risk_manager.daily_reset_date = datetime.utcnow().date() - timedelta(days=1)

    # Trigger check (will reset)
    await risk_manager.can_open_position(
        symbol="BTC_USDT",
        side="buy",
        quantity=Decimal('0.01'),
        price=Decimal('50000'),
        current_positions=[]
    )

    # Daily P&L should be reset to 0
    assert risk_manager.daily_pnl == Decimal('0')


# === Test Margin Ratio Alerts ===

@pytest.mark.asyncio
async def test_margin_ratio_critical_alert(event_bus, settings):
    """Test that CRITICAL alert is emitted when margin ratio < 15%."""
    events_received = []

    async def capture_event(data: Dict[str, Any]):
        events_received.append(data)

    await event_bus.subscribe("risk_alert", capture_event)

    risk_manager = RiskManager(event_bus, settings, Decimal('10000'))

    # Trigger critical margin ratio
    await risk_manager.check_margin_ratio(Decimal('12.0'))

    await asyncio.sleep(0.1)

    assert len(events_received) == 1
    event = events_received[0]
    assert event["severity"] == RiskAlertSeverity.CRITICAL.value
    assert event["alert_type"] == RiskAlertType.MARGIN_RATIO_LOW.value


@pytest.mark.asyncio
async def test_margin_ratio_warning_alert(event_bus, settings):
    """Test that WARNING alert is emitted when margin ratio < 25%."""
    events_received = []

    async def capture_event(data: Dict[str, Any]):
        events_received.append(data)

    await event_bus.subscribe("risk_alert", capture_event)

    risk_manager = RiskManager(event_bus, settings, Decimal('10000'))

    # Trigger warning margin ratio
    await risk_manager.check_margin_ratio(Decimal('20.0'))

    await asyncio.sleep(0.1)

    assert len(events_received) == 1
    event = events_received[0]
    assert event["severity"] == RiskAlertSeverity.WARNING.value


# === Test Configuration ===

def test_configuration_loading(risk_manager, settings):
    """Test that configuration is loaded correctly from settings."""
    assert risk_manager.risk_config.max_position_size_percent == Decimal('10.0')
    assert risk_manager.risk_config.max_concurrent_positions == 3
    assert risk_manager.risk_config.max_symbol_concentration_percent == Decimal('30.0')
    assert risk_manager.risk_config.daily_loss_limit_percent == Decimal('5.0')
    assert risk_manager.risk_config.max_drawdown_percent == Decimal('15.0')
    assert risk_manager.risk_config.max_margin_utilization_percent == Decimal('80.0')


# === Test Thread Safety ===

@pytest.mark.asyncio
async def test_concurrent_risk_checks(risk_manager):
    """Test that concurrent risk checks don't cause race conditions."""
    # Create 10 concurrent check requests
    tasks = [
        risk_manager.can_open_position(
            symbol=f"SYMBOL_{i}",
            side="buy",
            quantity=Decimal('0.01'),
            price=Decimal('1000'),
            current_positions=[]
        )
        for i in range(10)
    ]

    # Run all concurrently
    results = await asyncio.gather(*tasks)

    # All should succeed (small positions)
    assert all(r.can_proceed for r in results)


# === Test get_risk_summary() ===

def test_get_risk_summary(risk_manager):
    """Test that risk summary returns correct data."""
    summary = risk_manager.get_risk_summary()

    assert summary["current_capital"] == 10000.0
    assert summary["initial_capital"] == 10000.0
    assert summary["equity_peak"] == 10000.0
    assert summary["drawdown_percent"] == 0.0
    assert summary["daily_pnl"] == 0.0
    assert "limits" in summary
    assert summary["limits"]["max_position_size_percent"] == 10.0
    assert summary["limits"]["max_concurrent_positions"] == 3


# === Test Multiple Failed Checks ===

@pytest.mark.asyncio
async def test_multiple_failed_checks(risk_manager):
    """Test that multiple checks can fail simultaneously."""
    # Create 3 open positions (at limit)
    positions = [
        Position(
            position_id=f"pos_{i}",
            symbol=f"SYMBOL_{i}",
            exchange="MEXC",
            side=OrderSide.BUY,
            size=Decimal('0.01'),
            entry_price=Decimal('1000'),
            leverage=Decimal('1'),
            status=PositionStatus.OPEN
        )
        for i in range(3)
    ]

    # Try to open oversized position with max positions already
    result = await risk_manager.can_open_position(
        symbol="NEW_USDT",
        side="buy",
        quantity=Decimal('0.5'),  # Oversized (25,000 USDT)
        price=Decimal('50000'),
        current_positions=positions
    )

    assert result.can_proceed is False
    assert "max_position_size" in result.failed_checks
    assert "max_concurrent_positions" in result.failed_checks
    assert len(result.failed_checks) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
