from collections import deque
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.calculators.indicator_calculator import IndicatorCalculator
from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine, StreamingIndicator
from src.domain.types.indicator_types import MarketDataPoint


def _build_market_points():
    base_ts = 1_700_000_000.0
    prices = [100.0, 101.0, 102.0, 104.0]
    return [
        MarketDataPoint(timestamp=base_ts + idx * 10, price=price, volume=1.0, symbol="BTCUSDT")
        for idx, price in enumerate(prices)
    ]


def test_offline_vs_streaming_twpa_consistency():
    """
    Test that offline and streaming TWPA calculations produce identical results.

    This verifies that both engines use the same algorithm (TWPAAlgorithm).
    """
    market_points = _build_market_points()
    context = {"t1": 60.0, "t2": 0.0}

    # Calculate using offline engine (via IndicatorCalculator)
    offline_value = IndicatorCalculator.calculate_indicator_unified(
        "TWPA",
        market_points,
        market_points[-1].timestamp,
        context,
    )

    # Calculate using streaming engine
    event_bus = AsyncMock()
    logger = MagicMock()
    engine = StreamingIndicatorEngine(event_bus, logger)

    indicator = StreamingIndicator(
        symbol="BTCUSDT",
        indicator="TWPA",
        timeframe="1m",
        current_value=0.0,
        timestamp=market_points[-1].timestamp,
        series=deque(maxlen=100),
        metadata={"type": "TWPA", **context},
    )

    price_key = f"{indicator.symbol}_{indicator.timeframe}"
    engine._price_data[price_key] = deque(
        [
            {"timestamp": point.timestamp, "price": point.price}
            for point in market_points
        ],
        maxlen=engine._max_series_length,
    )

    # Use the new _calculate_twpa() which uses algorithm registry
    streaming_value = engine._calculate_twpa(indicator, context)

    assert streaming_value is not None, "Streaming TWPA should return a value"
    assert offline_value is not None, "Offline TWPA should return a value"
    assert streaming_value == pytest.approx(offline_value, rel=1e-9), \
        f"Offline ({offline_value}) and streaming ({streaming_value}) should match"


def test_twpa_with_pre_window_transaction():
    """
    CRITICAL TEST: Verify both engines correctly handle pre-window transaction.

    This test ensures that the fix for including pre-window transactions
    works in both offline and streaming engines.
    """
    # Create data where first point is BEFORE the window
    base_ts = 1_700_000_000.0
    market_points = [
        MarketDataPoint(timestamp=base_ts, price=1.0, volume=1.0, symbol="BTCUSDT"),      # Before window
        MarketDataPoint(timestamp=base_ts + 15, price=2.0, volume=1.0, symbol="BTCUSDT"), # In window
        MarketDataPoint(timestamp=base_ts + 25, price=3.0, volume=1.0, symbol="BTCUSDT"), # In window
    ]

    # Window: last 20 seconds
    context = {"t1": 20.0, "t2": 0.0}
    current_timestamp = base_ts + 25

    # Calculate using offline engine
    offline_value = IndicatorCalculator.calculate_indicator_unified(
        "TWPA",
        market_points,
        current_timestamp,
        context,
    )

    # Calculate using streaming engine
    event_bus = AsyncMock()
    logger = MagicMock()
    engine = StreamingIndicatorEngine(event_bus, logger)

    indicator = StreamingIndicator(
        symbol="BTCUSDT",
        indicator="TWPA",
        timeframe="1m",
        current_value=0.0,
        timestamp=current_timestamp,
        series=deque(maxlen=100),
        metadata={"type": "TWPA", **context},
    )

    price_key = f"{indicator.symbol}_{indicator.timeframe}"
    engine._price_data[price_key] = deque(
        [
            {"timestamp": point.timestamp, "price": point.price}
            for point in market_points
        ],
        maxlen=engine._max_series_length,
    )

    streaming_value = engine._calculate_twpa(indicator, context)

    # Manual expected calculation:
    # Window: [base_ts+5, base_ts+25]
    # - base_ts (before window, price 1.0) valid from base_ts+5 to base_ts+15 = 10s
    # - base_ts+15 (in window, price 2.0) valid from base_ts+15 to base_ts+25 = 10s
    # TWPA = (1.0*10 + 2.0*10) / 20 = 1.5
    expected = 1.5

    assert offline_value is not None
    assert streaming_value is not None
    assert offline_value == pytest.approx(expected, rel=1e-9), \
        f"Offline should be {expected}, got {offline_value}"
    assert streaming_value == pytest.approx(expected, rel=1e-9), \
        f"Streaming should be {expected}, got {streaming_value}"
    assert streaming_value == pytest.approx(offline_value, rel=1e-9), \
        f"Offline and streaming must match"


def test_indicator_calculator_deterministic_results():
    """Test that TWPA calculation is deterministic (same input = same output)."""
    market_points = _build_market_points()
    context = {"t1": 120.0, "t2": 0.0}
    timestamp = market_points[-1].timestamp

    first = IndicatorCalculator.calculate_indicator_unified("TWPA", market_points, timestamp, context)
    second = IndicatorCalculator.calculate_indicator_unified("TWPA", market_points, timestamp, context)

    assert first == pytest.approx(second, rel=1e-12)
