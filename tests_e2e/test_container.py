"""
TestContainer - Lightweight Container for unit testing.

This Container returns mocks instead of real services, allowing tests
to run without QuestDB or other heavy dependencies.

Usage:
    @pytest.fixture
    def test_container(mock_questdb_provider, test_settings):
        container = TestContainer(test_settings, event_bus, logger)
        container._singleton_services["questdb_provider"] = mock_questdb_provider
        return container

For integration tests, use the production Container with real QuestDB.
"""

from unittest.mock import AsyncMock, MagicMock
from src.infrastructure.container import Container


class TestContainer(Container):
    """
    Lightweight Container for testing.

    Overrides expensive factory methods to return mocks.
    Inherits from production Container to maintain interface compatibility.

    WARNING: This is TEST-ONLY. Do NOT use in production code.
    """

    async def create_questdb_provider(self):
        """
        Mock QuestDBProvider - no database connection.

        If mock was injected via _singleton_services, return it.
        Otherwise create a new mock.
        """
        # Check if mock was injected (from conftest.py fixture)
        existing = self._singleton_services.get("questdb_provider")
        if existing:
            return existing

        # Create new mock
        from src.data_feed.questdb_provider import QuestDBProvider

        mock = MagicMock(spec=QuestDBProvider)
        mock.initialize = AsyncMock()
        mock.close = AsyncMock()
        mock.is_healthy = AsyncMock(return_value=True)
        mock.execute_query = AsyncMock(return_value=[])
        mock.fetch_tick_prices = AsyncMock(return_value=[])
        mock.pg_pool = MagicMock()

        return mock

    async def create_streaming_indicator_engine(self):
        """
        Mock StreamingIndicatorEngine - no database loading.

        Returns mock that responds to all expected method calls.
        """
        from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine

        mock = MagicMock(spec=StreamingIndicatorEngine)

        # Mock async methods
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.create_variant = AsyncMock(return_value="mock_variant_id")
        mock.delete_variant = AsyncMock()
        mock.get_variant = AsyncMock(return_value=None)
        mock.get_all_variants = AsyncMock(return_value=[])
        mock.get_indicators = AsyncMock(return_value={})
        mock.process_market_data = AsyncMock()

        # Mock attributes
        mock._variants = {}
        mock._indicator_cache = {}

        return mock

    async def create_strategy_manager(self):
        """
        Mock StrategyManager - no database, no real strategies.

        Returns mock that responds to all expected method calls.
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
        mock.get_strategy = AsyncMock(return_value=None)
        mock.evaluate_strategies = AsyncMock()

        # Mock attributes
        mock._strategies = {}
        mock._active_strategies = set()

        return mock

    async def create_order_manager(self):
        """Mock OrderManager - no real orders."""
        mock = MagicMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.create_order = AsyncMock(return_value="mock_order_id")
        mock.cancel_order = AsyncMock()
        mock.get_order = AsyncMock(return_value=None)
        mock.get_all_orders = AsyncMock(return_value=[])
        return mock

    async def create_risk_manager(self):
        """Mock RiskManager - no real risk checks."""
        mock = MagicMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.assess_order_risk = AsyncMock(return_value={"approved": True})
        mock.get_risk_summary = AsyncMock(return_value={})
        return mock

    async def create_position_manager(self):
        """Mock PositionManager - no real positions."""
        mock = MagicMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.get_position = AsyncMock(return_value=None)
        mock.get_all_positions = AsyncMock(return_value=[])
        mock.update_position = AsyncMock()
        return mock

    async def create_live_market_adapter(self):
        """Mock LiveMarketAdapter - no exchange connection."""
        mock = MagicMock()
        mock.connect = AsyncMock()
        mock.disconnect = AsyncMock()
        mock.is_connected = AsyncMock(return_value=False)
        mock.get_market_data = AsyncMock(return_value={})
        return mock

    async def create_session_manager(self):
        """Mock SessionManager - no database."""
        mock = MagicMock()
        mock.create_session = AsyncMock(return_value="mock_session_id")
        mock.get_session = AsyncMock(return_value=None)
        mock.list_sessions = AsyncMock(return_value=[])
        mock.delete_session = AsyncMock()
        return mock

    async def create_metrics_exporter(self):
        """Mock MetricsExporter - no metrics collection."""
        mock = MagicMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.record_metric = AsyncMock()
        return mock

    # NOTE: Add more mock factories as needed for tests
    # Example:
    # async def create_<service_name>(self):
    #     mock = MagicMock()
    #     mock.start = AsyncMock()
    #     return mock
