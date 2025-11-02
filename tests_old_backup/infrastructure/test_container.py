"""Container singleton wiring tests."""

import pytest
import pytest_asyncio

from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.infrastructure.config.settings import AppSettings
from src.infrastructure.container import Container


@pytest_asyncio.fixture()
async def container_under_test(tmp_path):
    """Provide container with isolated settings and ensure cleanup."""
    settings = AppSettings(
        config_dir=str(tmp_path / "config"),
        data_dir=str(tmp_path / "data"),
        logging={
            "file_enabled": False,
            "console_enabled": False,
            "structured_logging": False,
            "log_dir": str(tmp_path / "logs"),
            "level": "INFO",
        },
    )

    event_bus = EventBus()
    logger = StructuredLogger("TestContainer", settings.logging)
    container = Container(settings=settings, event_bus=event_bus, logger=logger)

    try:
        yield container
    finally:
        await event_bus.shutdown()

@pytest.mark.timeout(30)
@pytest.mark.asyncio
async def test_live_market_adapter_singleton(container_under_test):
    container = container_under_test

    first = await container.create_live_market_adapter()
    second = await container.create_live_market_adapter()

    assert first is second
    assert first.session_manager is None


@pytest.mark.asyncio
async def test_session_manager_singleton_sets_adapter(container_under_test):
    container = container_under_test

    session_one = await container.create_session_manager()
    session_two = await container.create_session_manager()

    assert session_one is session_two

    adapter = await container.create_live_market_adapter()
    assert adapter.session_manager is session_one


@pytest.mark.asyncio
async def test_metrics_exporter_singleton_reuses_dependencies(container_under_test):
    container = container_under_test

    exporter_one = await container.create_metrics_exporter()
    exporter_two = await container.create_metrics_exporter()

    assert exporter_one is exporter_two

    adapter = await container.create_live_market_adapter()
    session_manager = await container.create_session_manager()

    assert exporter_one.market_adapter is adapter
    assert exporter_one.session_manager is session_manager
