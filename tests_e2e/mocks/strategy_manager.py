"""Mock for StrategyManager."""

from unittest.mock import AsyncMock, MagicMock


def create_mock_strategy_manager():
    """
    Create mock StrategyManager for tests.

    Returns mock with realistic return values.
    """
    from src.domain.services.strategy_manager import StrategyManager

    mock = MagicMock(spec=StrategyManager)

    # Mock async methods
    mock.initialize_strategies = AsyncMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.activate_strategy = AsyncMock()
    mock.deactivate_strategy = AsyncMock()
    mock.get_active_strategies = AsyncMock(return_value=[])
    mock.evaluate_strategies = AsyncMock()

    return mock
