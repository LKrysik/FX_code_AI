import asyncio
from collections import deque
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.services import streaming_indicator_engine as sie
from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine, StreamingIndicator


class FakeTime:
    def __init__(self, start: float = 0.0):
        self.current = start

    def time(self) -> float:
        return self.current

    def advance(self, delta: float) -> None:
        self.current += delta


@pytest.mark.asyncio
async def test_scheduler_timestamp_drift_below_threshold(monkeypatch):
    fake_time = FakeTime(start=1_700_000_000.0)
    monkeypatch.setattr(sie, "time", fake_time)

    event_bus = AsyncMock()
    logger = MagicMock()
    engine = StreamingIndicatorEngine(event_bus, logger)

    symbol = "BTCUSDT"
    timeframe = "1m"
    indicator = StreamingIndicator(
        symbol=symbol,
        indicator="TWPA",
        timeframe=timeframe,
        current_value=0.0,
        timestamp=fake_time.time(),
        series=deque(maxlen=120),
        metadata={"type": "TWPA", "t1": 60.0, "t2": 0.0},
    )

    indicator_key = "BTCUSDT_TWPA"
    engine._indicators[indicator_key] = indicator
    engine._register_time_driven_indicator(indicator_key, indicator)

    price_key = f"{symbol}_{timeframe}"
    engine._price_data[price_key] = deque(
        [
            {"timestamp": fake_time.time() - 5.0, "price": 99.0},
            {"timestamp": fake_time.time() - 2.0, "price": 100.0},
        ],
        maxlen=engine._max_series_length,
    )

    timestamps = []
    for step in range(5):
        engine._price_data[price_key].append(
            {"timestamp": fake_time.time(), "price": 100.0 + step}
        )
        await engine._recalculate_time_driven_indicator(indicator_key)
        timestamps.append(indicator.series[-1].timestamp)
        fake_time.advance(1.0)

    deltas = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    assert all(delta == pytest.approx(1.0, abs=0.1) for delta in deltas)
