"""
Tests for DashboardCacheService - BUG-004-4 Fix

Tests that _get_session_symbols() retrieves symbols from session configuration
(data_collection_sessions table) instead of tick_prices table.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.domain.services.dashboard_cache_service import DashboardCacheService


class TestGetSessionSymbols:
    """Tests for _get_session_symbols method - BUG-004-4 fix."""

    @pytest.fixture
    def mock_questdb(self):
        """Create mock QuestDB provider."""
        mock = MagicMock()
        mock.pg_pool = MagicMock()
        return mock

    @pytest.fixture
    def service(self, mock_questdb):
        """Create DashboardCacheService with mocked QuestDB."""
        return DashboardCacheService(mock_questdb, update_interval=1.0)

    @pytest.mark.asyncio
    async def test_get_session_symbols_from_session_config(self, service, mock_questdb):
        """
        BUG-004-4 AC1: Symbols should be retrieved from data_collection_sessions,
        not from tick_prices table.
        """
        # Arrange: Mock database response with JSON array format
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'symbols': '["BTC_USDT","ETH_USDT","SOL_USDT"]'
        })
        mock_questdb.pg_pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None)
        ))

        # Act
        symbols = await service._get_session_symbols("test_session_123")

        # Assert
        assert symbols == ["BTC_USDT", "ETH_USDT", "SOL_USDT"]

        # Verify query was to data_collection_sessions, not tick_prices
        call_args = mock_conn.fetchrow.call_args
        query = call_args[0][0]
        assert "data_collection_sessions" in query
        assert "tick_prices" not in query

    @pytest.mark.asyncio
    async def test_get_session_symbols_comma_separated_format(self, service, mock_questdb):
        """Test handling of comma-separated symbols format."""
        # Arrange
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'symbols': 'BTC_USDT,ETH_USDT,SOL_USDT'
        })
        mock_questdb.pg_pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None)
        ))

        # Act
        symbols = await service._get_session_symbols("test_session")

        # Assert
        assert symbols == ["BTC_USDT", "ETH_USDT", "SOL_USDT"]

    @pytest.mark.asyncio
    async def test_get_session_symbols_list_format(self, service, mock_questdb):
        """Test handling when database returns native list."""
        # Arrange
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'symbols': ["BTC_USDT", "ETH_USDT"]
        })
        mock_questdb.pg_pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None)
        ))

        # Act
        symbols = await service._get_session_symbols("test_session")

        # Assert
        assert symbols == ["BTC_USDT", "ETH_USDT"]

    @pytest.mark.asyncio
    async def test_get_session_symbols_session_not_found(self, service, mock_questdb):
        """Test when session doesn't exist - should return empty list."""
        # Arrange
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_questdb.pg_pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None)
        ))

        # Act
        symbols = await service._get_session_symbols("nonexistent_session")

        # Assert
        assert symbols == []

    @pytest.mark.asyncio
    async def test_get_session_symbols_empty_symbols(self, service, mock_questdb):
        """Test when session has no symbols configured."""
        # Arrange
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'symbols': ''
        })
        mock_questdb.pg_pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None)
        ))

        # Act
        symbols = await service._get_session_symbols("empty_session")

        # Assert
        assert symbols == []

    @pytest.mark.asyncio
    async def test_get_session_symbols_limits_to_20(self, service, mock_questdb):
        """Test that symbols are limited to 20."""
        # Arrange: Create 25 symbols
        many_symbols = [f"SYM{i}_USDT" for i in range(25)]
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'symbols': ','.join(many_symbols)
        })
        mock_questdb.pg_pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None)
        ))

        # Act
        symbols = await service._get_session_symbols("many_symbols_session")

        # Assert
        assert len(symbols) == 20
        assert symbols[0] == "SYM0_USDT"
        assert symbols[19] == "SYM19_USDT"

    @pytest.mark.asyncio
    async def test_get_session_symbols_handles_exception(self, service, mock_questdb):
        """Test graceful handling of database exceptions."""
        # Arrange
        mock_questdb.pg_pool.acquire = MagicMock(side_effect=Exception("DB connection failed"))

        # Act
        symbols = await service._get_session_symbols("error_session")

        # Assert - should return empty list, not raise
        assert symbols == []

    @pytest.mark.asyncio
    async def test_get_session_symbols_filters_deleted_sessions(self, service, mock_questdb):
        """Test that deleted sessions are filtered out."""
        # Arrange
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)  # Simulates is_deleted = false filter
        mock_questdb.pg_pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None)
        ))

        # Act
        await service._get_session_symbols("deleted_session")

        # Assert: Query should include is_deleted = false
        call_args = mock_conn.fetchrow.call_args
        query = call_args[0][0]
        assert "is_deleted = false" in query
