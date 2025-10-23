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
    market_points = _build_market_points()
    context = {"t1": 60.0, "t2": 0.0}

    offline_value = IndicatorCalculator.calculate_indicator_unified(
        "TWPA",
        market_points,
        market_points[-1].timestamp,
        context,
    )

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

    streaming_value = engine._calculate_windowed_price_aggregates(indicator, "TWPA", context)

    assert streaming_value is not None
    assert offline_value is not None
    assert streaming_value == pytest.approx(offline_value, rel=1e-9)


def test_indicator_calculator_deterministic_results():
    market_points = _build_market_points()
    context = {"t1": 120.0, "t2": 0.0}
    timestamp = market_points[-1].timestamp

    first = IndicatorCalculator.calculate_indicator_unified("TWPA", market_points, timestamp, context)
    second = IndicatorCalculator.calculate_indicator_unified("TWPA", market_points, timestamp, context)

    assert first == pytest.approx(second, rel=1e-12)
