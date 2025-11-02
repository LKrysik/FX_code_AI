"""
Tests for State Persistence Manager - Redis-based temporal state persistence.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from src.core.state_persistence_manager import StatePersistenceManager


class TestStatePersistenceManager:
    """Test suite for StatePersistenceManager."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None
        mock_redis.delete.return_value = 1
        mock_redis.keys.return_value = []
        return mock_redis

    @pytest.fixture
    def state_manager(self, mock_redis, monkeypatch):
        """StatePersistenceManager instance with mocked Redis."""
        monkeypatch.setattr('src.core.state_persistence_manager.REDIS_AVAILABLE', True)
        manager = StatePersistenceManager()
        manager.redis = mock_redis
        return manager

    def test_initialization_default_url(self):
        """Test initialization with default Redis URL."""
        manager = StatePersistenceManager()
        assert manager.redis_url == "redis://localhost:6379/0"
        assert manager.redis is None
        assert not manager._connected

    def test_initialization_custom_url(self):
        """Test initialization with custom Redis URL."""
        custom_url = "redis://localhost:6380/1"
        manager = StatePersistenceManager(redis_url=custom_url)
        assert manager.redis_url == custom_url

    def test_initialization_with_settings(self):
        """Test initialization with settings object."""
        mock_settings = Mock()
        mock_settings.redis.url = "redis://test:6379/0"
        manager = StatePersistenceManager(settings=mock_settings)
        assert manager.redis_url == "redis://test:6379/0"

    @pytest.mark.asyncio
    async def test_connect_success(self, state_manager, mock_redis):
        """Test successful Redis connection."""
        mock_redis.ping.return_value = True

        result = await state_manager.connect()

        assert state_manager._connected
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, state_manager, mock_redis):
        """Test Redis connection failure."""
        mock_redis.ping.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            await state_manager.connect()

        assert not state_manager._connected

    @pytest.mark.asyncio
    async def test_disconnect(self, state_manager, mock_redis):
        """Test Redis disconnection."""
        state_manager._connected = True

        await state_manager.disconnect()

        assert not state_manager._connected
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_temporal_state_success(self, state_manager, mock_redis):
        """Test successful temporal state persistence."""
        strategy_name = "test_strategy"
        symbol = "BTCUSDT"
        condition_id = "duration_1"
        state_data = {
            "type": "duration",
            "duration_seconds": 30,
            "state": {
                "active": True,
                "start_time": 1640995200.0,
                "elapsed": 15.5
            }
        }

        mock_redis.set.return_value = True

        result = await state_manager.persist_temporal_state(
            strategy_name, symbol, condition_id, state_data
        )

        assert result is True
        expected_key = f"strategy:{strategy_name}:temporal:{symbol}:{condition_id}"
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == expected_key

        # Verify the stored data contains metadata
        stored_data = json.loads(call_args[0][1])
        assert stored_data["type"] == "duration"
        assert stored_data["strategy_name"] == strategy_name
        assert stored_data["symbol"] == symbol
        assert stored_data["condition_id"] == condition_id
        assert "last_update" in stored_data

    @pytest.mark.asyncio
    async def test_persist_temporal_state_failure(self, state_manager, mock_redis):
        """Test temporal state persistence failure."""
        mock_redis.set.return_value = False

        result = await state_manager.persist_temporal_state(
            "test_strategy", "BTCUSDT", "duration_1", {"type": "duration"}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_persist_temporal_state_connection_error(self, state_manager, mock_redis):
        """Test temporal state persistence with connection error."""
        mock_redis.set.side_effect = Exception("Connection lost")

        result = await state_manager.persist_temporal_state(
            "test_strategy", "BTCUSDT", "duration_1", {"type": "duration"}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_recover_temporal_state_success(self, state_manager, mock_redis):
        """Test successful temporal state recovery."""
        strategy_name = "test_strategy"
        symbol = "BTCUSDT"
        condition_id = "duration_1"

        state_data = {
            "type": "duration",
            "duration_seconds": 30,
            "state": {"active": True, "start_time": 1640995200.0},
            "last_update": "2023-01-01T12:00:00Z"
        }

        mock_redis.get.return_value = json.dumps(state_data)

        result = await state_manager.recover_temporal_state(
            strategy_name, symbol, condition_id
        )

        assert result == state_data
        expected_key = f"strategy:{strategy_name}:temporal:{symbol}:{condition_id}"
        mock_redis.get.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_recover_temporal_state_not_found(self, state_manager, mock_redis):
        """Test temporal state recovery when state doesn't exist."""
        mock_redis.get.return_value = None

        result = await state_manager.recover_temporal_state(
            "test_strategy", "BTCUSDT", "duration_1"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_recover_temporal_states_multiple(self, state_manager, mock_redis):
        """Test recovering multiple temporal states for a strategy."""
        strategy_name = "test_strategy"

        # Mock Redis keys and data
        keys = [
            b"strategy:test_strategy:temporal:BTCUSDT:duration_1",
            b"strategy:test_strategy:temporal:ETHUSDT:sequence_1"
        ]
        state_data_1 = {"type": "duration", "state": {"active": True}}
        state_data_2 = {"type": "sequence", "state": {"sequence": [1, 2, 3]}}

        mock_redis.keys.return_value = keys
        mock_redis.get.side_effect = [
            json.dumps(state_data_1),
            json.dumps(state_data_2)
        ]

        result = await state_manager.recover_temporal_states(strategy_name)

        assert len(result) == 2
        assert "strategy:test_strategy:temporal:BTCUSDT:duration_1" in result
        assert "strategy:test_strategy:temporal:ETHUSDT:sequence_1" in result
        assert result["strategy:test_strategy:temporal:BTCUSDT:duration_1"] == state_data_1
        assert result["strategy:test_strategy:temporal:ETHUSDT:sequence_1"] == state_data_2

    @pytest.mark.asyncio
    async def test_recover_temporal_states_empty(self, state_manager, mock_redis):
        """Test recovering temporal states when none exist."""
        mock_redis.keys.return_value = []

        result = await state_manager.recover_temporal_states("test_strategy")

        assert result == {}

    @pytest.mark.asyncio
    async def test_delete_temporal_state_success(self, state_manager, mock_redis):
        """Test successful temporal state deletion."""
        mock_redis.delete.return_value = 1

        result = await state_manager.delete_temporal_state(
            "test_strategy", "BTCUSDT", "duration_1"
        )

        assert result is True
        expected_key = "strategy:test_strategy:temporal:BTCUSDT:duration_1"
        mock_redis.delete.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_delete_temporal_state_not_found(self, state_manager, mock_redis):
        """Test temporal state deletion when state doesn't exist."""
        mock_redis.delete.return_value = 0

        result = await state_manager.delete_temporal_state(
            "test_strategy", "BTCUSDT", "duration_1"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_states(self, state_manager, mock_redis):
        """Test cleanup of expired temporal states."""
        # Mock keys and data with some expired states
        keys = [
            b"strategy:test_strategy:temporal:BTCUSDT:duration_1",
            b"strategy:test_strategy:temporal:ETHUSDT:sequence_1"
        ]

        current_time = datetime.now(timezone.utc)
        expired_time = current_time - timedelta(hours=25)  # 25 hours ago

        state_data_1 = {
            "type": "duration",
            "last_update": expired_time.isoformat()
        }
        state_data_2 = {
            "type": "sequence",
            "last_update": current_time.isoformat()  # Not expired
        }

        mock_redis.keys.return_value = keys
        mock_redis.get.side_effect = [
            json.dumps(state_data_1),
            json.dumps(state_data_2)
        ]
        mock_redis.delete.return_value = 1

        result = await state_manager.cleanup_expired_states(max_age_hours=24)

        assert result == 1  # One state should be cleaned up
        assert mock_redis.delete.call_count == 1

    @pytest.mark.asyncio
    async def test_get_state_stats(self, state_manager, mock_redis):
        """Test getting state statistics."""
        keys = [
            b"strategy:strategy1:temporal:BTCUSDT:duration_1",
            b"strategy:strategy1:temporal:ETHUSDT:sequence_1",
            b"strategy:strategy2:temporal:BTCUSDT:duration_2"
        ]

        mock_redis.keys.return_value = keys

        result = await state_manager.get_state_stats()

        assert result["total_states"] == 3
        assert "strategy1" in result["strategies"]
        assert "strategy2" in result["strategies"]
        assert "BTCUSDT" in result["symbols"]
        assert "ETHUSDT" in result["symbols"]

    @pytest.mark.asyncio
    async def test_get_state_stats_filtered(self, state_manager, mock_redis):
        """Test getting state statistics for specific strategy."""
        keys = [
            b"strategy:strategy1:temporal:BTCUSDT:duration_1",
            b"strategy:strategy1:temporal:ETHUSDT:sequence_1"
        ]

        mock_redis.keys.return_value = keys

        result = await state_manager.get_state_stats("strategy1")

        assert result["total_states"] == 2
        assert result["strategies"] == ["strategy1"]
        assert "BTCUSDT" in result["symbols"]
        assert "ETHUSDT" in result["symbols"]

    @pytest.mark.asyncio
    async def test_operations_without_connection(self, state_manager, mock_redis):
        """Test that operations handle disconnected state gracefully."""
        state_manager._connected = False

        # These should attempt to connect and then perform operations
        with patch.object(state_manager, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            mock_redis.set.return_value = True

            result = await state_manager.persist_temporal_state(
                "test", "BTCUSDT", "duration_1", {"type": "duration"}
            )

            mock_connect.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_json_serialization_errors(self, state_manager, mock_redis):
        """Test handling of JSON serialization errors."""
        # Test with non-serializable data
        class NonSerializable:
            pass

        state_data = {"non_serializable": NonSerializable()}

        result = await state_manager.persist_temporal_state(
            "test", "BTCUSDT", "duration_1", state_data
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_corrupted_data_recovery(self, state_manager, mock_redis):
        """Test recovery from corrupted Redis data."""
        mock_redis.get.return_value = "invalid json"

        result = await state_manager.recover_temporal_state(
            "test", "BTCUSDT", "duration_1"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_bulk_recovery_with_corruption(self, state_manager, mock_redis):
        """Test bulk recovery when some data is corrupted."""
        keys = [
            b"strategy:test_strategy:temporal:BTCUSDT:duration_1",
            b"strategy:test_strategy:temporal:ETHUSDT:sequence_1"
        ]

        valid_state = {"type": "duration", "state": {"active": True}}

        mock_redis.keys.return_value = keys
        mock_redis.get.side_effect = [
            json.dumps(valid_state),  # Valid data
            "corrupted json data"     # Corrupted data
        ]

        result = await state_manager.recover_temporal_states("test_strategy")

        # Should only contain the valid state
        assert len(result) == 1
        assert "strategy:test_strategy:temporal:BTCUSDT:duration_1" in result
        assert result["strategy:test_strategy:temporal:BTCUSDT:duration_1"] == valid_state


class TestStatePersistenceManagerIntegration:
    """Integration tests for StatePersistenceManager (requires Redis)."""

    @pytest.fixture
    def redis_url(self):
        """Redis URL for integration tests."""
        return "redis://localhost:6379/0"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_persistence_workflow(self, redis_url):
        """Test complete persistence workflow with real Redis."""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available")

        try:
            manager = StatePersistenceManager(redis_url)
            await manager.connect()

            # Test data
            strategy_name = "integration_test_strategy"
            symbol = "BTCUSDT"
            condition_id = "duration_test_1"
            state_data = {
                "type": "duration",
                "duration_seconds": 60,
                "state": {
                    "active": True,
                    "start_time": 1640995200.0,
                    "elapsed": 30.0
                }
            }

            # Persist state
            persist_result = await manager.persist_temporal_state(
                strategy_name, symbol, condition_id, state_data
            )
            assert persist_result is True

            # Recover state
            recovered_state = await manager.recover_temporal_state(
                strategy_name, symbol, condition_id
            )
            assert recovered_state is not None
            assert recovered_state["type"] == "duration"
            assert recovered_state["state"]["active"] is True

            # Recover all states for strategy
            all_states = await manager.recover_temporal_states(strategy_name)
            assert len(all_states) >= 1
            assert any(condition_id in key for key in all_states.keys())

            # Delete state
            delete_result = await manager.delete_temporal_state(
                strategy_name, symbol, condition_id
            )
            assert delete_result is True

            # Verify deletion
            recovered_after_delete = await manager.recover_temporal_state(
                strategy_name, symbol, condition_id
            )
            assert recovered_after_delete is None

            await manager.disconnect()

        except redis.ConnectionError:
            pytest.skip("Redis not available for integration tests")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_state_stats_with_real_redis(self, redis_url):
        """Test state statistics with real Redis."""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available")

        try:
            manager = StatePersistenceManager(redis_url)
            await manager.connect()

            # Create some test data
            test_states = [
                ("strategy1", "BTCUSDT", "duration_1", {"type": "duration"}),
                ("strategy1", "ETHUSDT", "sequence_1", {"type": "sequence"}),
                ("strategy2", "BTCUSDT", "duration_2", {"type": "duration"})
            ]

            for strategy, symbol, condition_id, state in test_states:
                await manager.persist_temporal_state(strategy, symbol, condition_id, state)

            # Get stats
            stats = await manager.get_state_stats()
            assert stats["total_states"] >= 3
            assert "strategy1" in stats["strategies"]
            assert "strategy2" in stats["strategies"]
            assert "BTCUSDT" in stats["symbols"]
            assert "ETHUSDT" in stats["symbols"]

            # Get filtered stats
            strategy1_stats = await manager.get_state_stats("strategy1")
            assert strategy1_stats["total_states"] >= 2
            assert strategy1_stats["strategies"] == ["strategy1"]

            # Cleanup
            for strategy, symbol, condition_id, _ in test_states:
                await manager.delete_temporal_state(strategy, symbol, condition_id)

            await manager.disconnect()

        except redis.ConnectionError:
            pytest.skip("Redis not available for integration tests")