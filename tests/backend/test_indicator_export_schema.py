from pathlib import Path
from typing import Any, Dict, Callable

from src.domain.services.indicator_persistence_service import IndicatorPersistenceService
from src.domain.types.indicator_types import IndicatorValue


class DummyEventBus:
    def __init__(self) -> None:
        self._subscriptions = []

    def subscribe(self, event_name: str, handler: Callable, priority: Any = None) -> None:
        self._subscriptions.append((event_name, handler, priority))

    async def publish(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class DummyLogger:
    def __init__(self) -> None:
        self.messages = []

    def info(self, message: str, payload: Dict[str, Any] = None) -> None:
        self.messages.append((message, payload))

    def debug(self, message: str, payload: Dict[str, Any] = None) -> None:
        self.messages.append((message, payload))

    def warning(self, message: str, payload: Dict[str, Any] = None) -> None:
        self.messages.append((message, payload))

    def error(self, message: str, payload: Dict[str, Any] = None) -> None:
        self.messages.append((message, payload))


def test_indicator_persistence_writes_two_column_csv(tmp_path: Path):
    event_bus = DummyEventBus()
    logger = DummyLogger()
    service = IndicatorPersistenceService(event_bus, logger, base_data_dir=str(tmp_path))

    values = [
        IndicatorValue(timestamp=1_700_000_000.0, symbol="BTCUSDT", indicator_id="id", value=100.123456),
        IndicatorValue(timestamp=1_700_000_001.5, symbol="BTCUSDT", indicator_id="id", value=101.654321),
    ]

    service.save_batch_values("session", "BTCUSDT", "twpa", values, "general")

    csv_file = tmp_path / "session" / "BTCUSDT" / "indicators" / "general_twpa.csv"
    assert csv_file.exists()

    content = csv_file.read_text().strip().splitlines()
    assert content[0] == "timestamp,value"
    assert content[1].count(",") == 1
    assert content[2].count(",") == 1
    # values formatted with six decimal places
    assert content[1].split(",")[1] == "100.123456"
    assert content[2].split(",")[1] == "101.654321"
