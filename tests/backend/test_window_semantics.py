import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine, StreamingIndicator


@pytest.fixture
def streaming_engine():
    event_bus = AsyncMock()
    logger = MagicMock()
    engine = StreamingIndicatorEngine(event_bus, logger)
    return engine


def test_validate_time_window_semantics_auto_correct(streaming_engine):
    corrected_t1, corrected_t2 = streaming_engine._validate_time_window_semantics(30, 120, "TWPA")
    assert corrected_t1 == 120
    assert corrected_t2 == 30


def test_price_series_normalizes_millisecond_timestamps(streaming_engine):
    symbol = "BTCUSDT"
    timeframe = "1m"
    indicator = StreamingIndicator(
        symbol=symbol,
        indicator="TWPA",
        timeframe=timeframe,
        current_value=0.0,
        timestamp=time.time(),
        series=deque(maxlen=10),
        metadata={"type": "TWPA", "t1": 60, "t2": 0},
    )

    price_key = f"{symbol}_{timeframe}"
    streaming_engine._price_data[price_key] = deque(
        [
            {"timestamp": 1_700_000_000_000, "price": 100.0},
            {"timestamp": 1_700_000_060_000, "price": 101.0},
        ],
        maxlen=streaming_engine._max_series_length,
    )

    window, start_ts, end_ts = streaming_engine._get_price_series_for_window(indicator, 120, 0)

    assert len(window) == 2
    # Values should be normalized to seconds instead of milliseconds
    assert all(ts < 10**12 for ts, _ in window)
    assert pytest.approx(window[1][0] - window[0][0], rel=1e-6) == 60
    assert start_ts < end_ts
