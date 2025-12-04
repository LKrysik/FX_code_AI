"""
Unit tests for max_drawdown calculation.

Tests:
- Happy path: Normal equity curve with drawdown
- Edge case: Empty data
- Edge case: Single data point
- Edge case: No drawdown (only gains)
- Edge case: Multiple peaks and troughs
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.domain.services.dashboard_cache_service import DashboardCacheService


class TestMaxDrawdownCalculation:
    """Test suite for max_drawdown calculation from equity curve."""

    @pytest.fixture
    def mock_questdb(self):
        """Mock QuestDB provider."""
        questdb = MagicMock()
        questdb.pg_pool = MagicMock()
        return questdb

    @pytest.fixture
    def cache_service(self, mock_questdb):
        """Create DashboardCacheService instance."""
        return DashboardCacheService(mock_questdb, update_interval=1.0)

    @pytest.mark.asyncio
    async def test_max_drawdown_normal_case(self, cache_service, mock_questdb):
        """Test max_drawdown calculation with normal equity curve."""
        # Arrange: Equity curve with 10% drawdown
        session_id = "test_session_001"
        equity_data = [
            {"current_balance": 10000.0, "timestamp": datetime.now()},
            {"current_balance": 11000.0, "timestamp": datetime.now() + timedelta(minutes=1)},  # Peak
            {"current_balance": 10500.0, "timestamp": datetime.now() + timedelta(minutes=2)},  # 4.5% DD
            {"current_balance": 9900.0, "timestamp": datetime.now() + timedelta(minutes=3)},   # 10% DD from peak
            {"current_balance": 10200.0, "timestamp": datetime.now() + timedelta(minutes=4)},  # Recovery
        ]

        # Mock database response
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=equity_data)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_questdb.pg_pool.acquire = MagicMock(return_value=mock_context)

        # Act
        result = await cache_service._calculate_max_drawdown(session_id)

        # Assert
        assert result == pytest.approx(10.0, rel=0.01), f"Expected ~10% drawdown, got {result}%"

    @pytest.mark.asyncio
    async def test_max_drawdown_empty_data(self, cache_service, mock_questdb):
        """Test max_drawdown with empty equity curve."""
        # Arrange
        session_id = "test_session_002"

        # Mock database response - empty
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_questdb.pg_pool.acquire = MagicMock(return_value=mock_context)

        # Act
        result = await cache_service._calculate_max_drawdown(session_id)

        # Assert
        assert result == 0.0, "Empty data should return 0% drawdown"

    @pytest.mark.asyncio
    async def test_max_drawdown_single_point(self, cache_service, mock_questdb):
        """Test max_drawdown with single data point."""
        # Arrange
        session_id = "test_session_003"
        equity_data = [
            {"current_balance": 10000.0, "timestamp": datetime.now()},
        ]

        # Mock database response
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=equity_data)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_questdb.pg_pool.acquire = MagicMock(return_value=mock_context)

        # Act
        result = await cache_service._calculate_max_drawdown(session_id)

        # Assert
        assert result == 0.0, "Single data point should return 0% drawdown"

    @pytest.mark.asyncio
    async def test_max_drawdown_no_drawdown(self, cache_service, mock_questdb):
        """Test max_drawdown with only gains (no drawdown)."""
        # Arrange
        session_id = "test_session_004"
        equity_data = [
            {"current_balance": 10000.0, "timestamp": datetime.now()},
            {"current_balance": 10500.0, "timestamp": datetime.now() + timedelta(minutes=1)},
            {"current_balance": 11000.0, "timestamp": datetime.now() + timedelta(minutes=2)},
            {"current_balance": 11500.0, "timestamp": datetime.now() + timedelta(minutes=3)},
        ]

        # Mock database response
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=equity_data)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_questdb.pg_pool.acquire = MagicMock(return_value=mock_context)

        # Act
        result = await cache_service._calculate_max_drawdown(session_id)

        # Assert
        assert result == 0.0, "No drawdown should return 0%"

    @pytest.mark.asyncio
    async def test_max_drawdown_multiple_peaks(self, cache_service, mock_questdb):
        """Test max_drawdown with multiple peaks - should return max of all drawdowns."""
        # Arrange
        session_id = "test_session_005"
        equity_data = [
            {"current_balance": 10000.0, "timestamp": datetime.now()},
            {"current_balance": 11000.0, "timestamp": datetime.now() + timedelta(minutes=1)},  # Peak 1
            {"current_balance": 10500.0, "timestamp": datetime.now() + timedelta(minutes=2)},  # 4.5% DD
            {"current_balance": 12000.0, "timestamp": datetime.now() + timedelta(minutes=3)},  # Peak 2 (higher)
            {"current_balance": 10200.0, "timestamp": datetime.now() + timedelta(minutes=4)},  # 15% DD from Peak 2
            {"current_balance": 11000.0, "timestamp": datetime.now() + timedelta(minutes=5)},  # Recovery
        ]

        # Mock database response
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=equity_data)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_questdb.pg_pool.acquire = MagicMock(return_value=mock_context)

        # Act
        result = await cache_service._calculate_max_drawdown(session_id)

        # Assert
        assert result == pytest.approx(15.0, rel=0.01), f"Expected ~15% max drawdown, got {result}%"

    @pytest.mark.asyncio
    async def test_max_drawdown_null_balance(self, cache_service, mock_questdb):
        """Test max_drawdown with null balance values."""
        # Arrange
        session_id = "test_session_006"
        equity_data = [
            {"current_balance": 10000.0, "timestamp": datetime.now()},
            {"current_balance": None, "timestamp": datetime.now() + timedelta(minutes=1)},
            {"current_balance": 9500.0, "timestamp": datetime.now() + timedelta(minutes=2)},
        ]

        # Mock database response
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=equity_data)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_questdb.pg_pool.acquire = MagicMock(return_value=mock_context)

        # Act
        result = await cache_service._calculate_max_drawdown(session_id)

        # Assert
        # Should handle None gracefully and still calculate drawdown
        assert result >= 0.0, "Should handle None values gracefully"

    @pytest.mark.asyncio
    async def test_max_drawdown_severe_loss(self, cache_service, mock_questdb):
        """Test max_drawdown with severe loss (50% drawdown)."""
        # Arrange
        session_id = "test_session_007"
        equity_data = [
            {"current_balance": 10000.0, "timestamp": datetime.now()},
            {"current_balance": 12000.0, "timestamp": datetime.now() + timedelta(minutes=1)},  # Peak
            {"current_balance": 6000.0, "timestamp": datetime.now() + timedelta(minutes=2)},   # 50% DD
        ]

        # Mock database response
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=equity_data)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_questdb.pg_pool.acquire = MagicMock(return_value=mock_context)

        # Act
        result = await cache_service._calculate_max_drawdown(session_id)

        # Assert
        assert result == pytest.approx(50.0, rel=0.01), f"Expected ~50% drawdown, got {result}%"

    @pytest.mark.asyncio
    async def test_max_drawdown_database_error(self, cache_service, mock_questdb):
        """Test max_drawdown handles database errors gracefully."""
        # Arrange
        session_id = "test_session_008"

        # Mock database error
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("Database connection failed"))

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_questdb.pg_pool.acquire = MagicMock(return_value=mock_context)

        # Act
        result = await cache_service._calculate_max_drawdown(session_id)

        # Assert
        assert result == 0.0, "Should return 0% on database error (graceful handling)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
