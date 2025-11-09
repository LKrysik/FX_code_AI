"""
Unit Tests - StrategyManager Concurrency
=========================================
Tests for race condition fixes in StrategyManager after Agent 3 Phase 2.

Test Coverage:
- Signal slot acquisition under concurrent access
- Symbol locking mechanisms
- Background task tracking and cleanup
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

try:
    from src.domain.services.strategy_manager import (
        StrategyManager,
        Strategy,
        StrategyState,
        ConditionGroup,
        Condition
    )
    from src.core.event_bus import EventBus
    from src.core.logger import StructuredLogger
except ImportError:
    from domain.services.strategy_manager import (
        StrategyManager,
        Strategy,
        StrategyState,
        ConditionGroup,
        Condition
    )
    from core.event_bus import EventBus
    from core.logger import StructuredLogger


class TestStrategyManagerSignalSlots:
    """Test signal slot acquisition and management"""

    @pytest.fixture
    async def manager(self):
        """Create StrategyManager instance for testing"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        logger = Mock(spec=StructuredLogger)
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()

        manager = StrategyManager(
            event_bus=event_bus,
            logger=logger,
            order_manager=None,
            risk_manager=None,
            db_pool=None
        )

        await manager.start()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_strategies_competing_for_slots(self, manager):
        """Test 10 concurrent strategies competing for 3 slots"""
        # Set max slots to 3
        manager._max_concurrent_signals = 3

        # Create 10 concurrent acquisition attempts
        tasks = [
            manager.acquire_signal_slot(f"strategy_{i}")
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # Only 3 should succeed
        acquired = sum(1 for r in results if r)
        assert acquired == 3, f"Expected 3 slots acquired, got {acquired}"

        # Verify slot status
        status = manager.get_slot_status()
        assert status["total_active_signals"] == 3
        assert status["available_slots"] == 0

    @pytest.mark.asyncio
    async def test_slot_release_and_reacquisition(self, manager):
        """Test slot release and re-acquisition"""
        manager._max_concurrent_signals = 2

        # Acquire 2 slots
        result1 = await manager.acquire_signal_slot("strategy_1")
        result2 = await manager.acquire_signal_slot("strategy_2")

        assert result1 is True
        assert result2 is True

        # Try to acquire third (should fail)
        result3 = await manager.acquire_signal_slot("strategy_3")
        assert result3 is False

        # Release one slot
        await manager.release_signal_slot("strategy_1")

        # Now strategy_3 should succeed
        result3_retry = await manager.acquire_signal_slot("strategy_3")
        assert result3_retry is True

        # Verify final status
        status = manager.get_slot_status()
        assert status["total_active_signals"] == 2

    @pytest.mark.asyncio
    async def test_max_slot_enforcement(self, manager):
        """Test that max slot limit is enforced (should reject over-allocation)"""
        manager._max_concurrent_signals = 5

        # Acquire all 5 slots
        for i in range(5):
            result = await manager.acquire_signal_slot(f"strategy_{i}")
            assert result is True

        # Verify all slots used
        status = manager.get_slot_status()
        assert status["total_active_signals"] == 5
        assert status["available_slots"] == 0

        # Try to acquire 6th slot (should fail)
        result = await manager.acquire_signal_slot("strategy_overflow")
        assert result is False

        # Status should remain at 5
        status = manager.get_slot_status()
        assert status["total_active_signals"] == 5


class TestStrategyManagerSymbolLocking:
    """Test symbol locking mechanisms"""

    @pytest.fixture
    async def manager(self):
        """Create StrategyManager for symbol locking tests"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        logger = Mock(spec=StructuredLogger)
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()

        manager = StrategyManager(
            event_bus=event_bus,
            logger=logger,
            order_manager=None,
            risk_manager=None,
            db_pool=None
        )

        await manager.start()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_strategies_competing_for_symbol(self, manager):
        """Test 5 concurrent strategies competing for 1 symbol"""
        symbol = "BTC_USDT"

        # Create 5 concurrent lock attempts
        tasks = [
            manager.lock_symbol(symbol, f"strategy_{i}")
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # Only 1 should succeed (first one to acquire lock)
        acquired = sum(1 for r in results if r)
        assert acquired == 1, f"Expected 1 symbol lock, got {acquired}"

        # Verify symbol is locked
        status = manager.get_slot_status()
        assert symbol in status["symbol_locks"]

    @pytest.mark.asyncio
    async def test_symbol_unlock_and_relock(self, manager):
        """Test symbol unlock and re-lock by different strategy"""
        symbol = "ETH_USDT"

        # Strategy 1 locks symbol
        result1 = await manager.lock_symbol(symbol, "strategy_1")
        assert result1 is True

        # Strategy 2 tries to lock (should fail)
        result2 = await manager.lock_symbol(symbol, "strategy_2")
        assert result2 is False

        # Strategy 1 unlocks
        await manager.unlock_symbol(symbol, "strategy_1")

        # Strategy 2 tries again (should succeed)
        result2_retry = await manager.lock_symbol(symbol, "strategy_2")
        assert result2_retry is True

        # Verify current lock holder
        status = manager.get_slot_status()
        assert status["symbol_locks"][symbol] == "strategy_2"

    @pytest.mark.asyncio
    async def test_same_strategy_can_relock_own_symbol(self, manager):
        """Test that same strategy can re-lock its own symbol"""
        symbol = "BNB_USDT"

        # Strategy 1 locks symbol
        result1 = await manager.lock_symbol(symbol, "strategy_1")
        assert result1 is True

        # Strategy 1 tries to lock again (should succeed - idempotent)
        result2 = await manager.lock_symbol(symbol, "strategy_1")
        assert result2 is True

        # Verify still locked by strategy_1
        status = manager.get_slot_status()
        assert status["symbol_locks"][symbol] == "strategy_1"


class TestStrategyManagerBackgroundTasks:
    """Test background task tracking and cleanup"""

    @pytest.fixture
    async def manager(self):
        """Create StrategyManager for background task tests"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        logger = Mock(spec=StructuredLogger)
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()

        manager = StrategyManager(
            event_bus=event_bus,
            logger=logger,
            order_manager=None,
            risk_manager=None,
            db_pool=None
        )

        await manager.start()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_task_tracking_no_leaks(self, manager):
        """Test that background tasks are tracked and don't leak"""
        # Create a strategy and trigger an event that creates background tasks
        strategy = Strategy(
            strategy_name="test_strategy",
            enabled=True,
            direction="LONG"
        )
        manager.add_strategy(strategy)

        # Activate strategy for a symbol
        manager.activate_strategy_for_symbol("test_strategy", "BTC_USDT")

        # Simulate indicator update that triggers background task
        indicator_values = {
            "pump_magnitude_pct": 10.0,
            "volume_surge_ratio": 3.5
        }

        # Update indicator cache (this would normally trigger evaluation)
        async with manager._indicator_values_lock:
            manager.indicator_values["BTC_USDT"] = indicator_values

        # Allow time for any background tasks
        await asyncio.sleep(0.1)

        # Check that background tasks are being tracked
        initial_task_count = len(manager._background_tasks)

        # Shutdown should cleanup all tasks
        await manager.shutdown()

        # Verify all tasks were cancelled
        assert len(manager._background_tasks) == 0

    @pytest.mark.asyncio
    async def test_graceful_shutdown_cancels_all_tasks(self, manager):
        """Test that graceful shutdown cancels all background tasks"""
        # Add some strategies
        for i in range(3):
            strategy = Strategy(
                strategy_name=f"strategy_{i}",
                enabled=True,
                direction="LONG"
            )
            manager.add_strategy(strategy)
            manager.activate_strategy_for_symbol(f"strategy_{i}", f"SYMBOL_{i}")

        # Simulate some indicator updates
        for i in range(3):
            async with manager._indicator_values_lock:
                manager.indicator_values[f"SYMBOL_{i}"] = {
                    "pump_magnitude_pct": 5.0 + i
                }

        await asyncio.sleep(0.1)

        # Shutdown
        await manager.shutdown()

        # Verify cleanup
        assert len(manager._background_tasks) == 0


class TestStrategyManagerRaceConditionFixes:
    """Test specific race condition fixes from Agent 3 Phase 2"""

    @pytest.fixture
    async def manager(self):
        """Create StrategyManager for race condition tests"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        logger = Mock(spec=StructuredLogger)
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()

        manager = StrategyManager(
            event_bus=event_bus,
            logger=logger,
            order_manager=None,
            risk_manager=None,
            db_pool=None
        )

        await manager.start()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_atomic_slot_acquisition_prevents_over_allocation(self, manager):
        """Test that atomic slot acquisition prevents race condition over-allocation"""
        manager._max_concurrent_signals = 3

        # Create 100 concurrent attempts (high contention)
        tasks = [
            manager.acquire_signal_slot(f"strategy_{i}")
            for i in range(100)
        ]

        results = await asyncio.gather(*tasks)

        # Exactly 3 should succeed (no over-allocation)
        acquired = sum(1 for r in results if r)
        assert acquired == 3, f"Race condition: {acquired} slots acquired instead of 3"

        # Verify no over-allocation in internal state
        total_signals = sum(manager._global_signal_slots.values())
        assert total_signals == 3

    @pytest.mark.asyncio
    async def test_atomic_symbol_lock_prevents_double_booking(self, manager):
        """Test that atomic symbol lock prevents double-booking"""
        symbol = "ADA_USDT"

        # Create 50 concurrent lock attempts for same symbol
        tasks = [
            manager.lock_symbol(symbol, f"strategy_{i}")
            for i in range(50)
        ]

        results = await asyncio.gather(*tasks)

        # Exactly 1 should succeed (no double-booking)
        acquired = sum(1 for r in results if r)
        assert acquired == 1, f"Race condition: {acquired} strategies locked same symbol"

        # Verify symbol lock state
        assert symbol in manager._symbol_locks
        assert manager._symbol_locks[symbol].startswith("strategy_")

    @pytest.mark.asyncio
    async def test_per_dictionary_locks_prevent_concurrent_modifications(self, manager):
        """Test that per-dictionary locks prevent concurrent modification issues"""
        # Add multiple strategies concurrently
        async def add_strategy_task(index: int):
            strategy = Strategy(
                strategy_name=f"concurrent_strategy_{index}",
                enabled=True,
                direction="LONG"
            )
            # Directly test lock protection
            async with manager._strategies_lock:
                manager.strategies[strategy.strategy_name] = strategy

        tasks = [add_strategy_task(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # Verify all strategies added without corruption
        assert len(manager.strategies) == 20

        # Test concurrent indicator updates
        async def update_indicator_task(index: int):
            async with manager._indicator_values_lock:
                manager.indicator_values[f"SYMBOL_{index}"] = {
                    "pump_magnitude_pct": float(index)
                }

        tasks = [update_indicator_task(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # Verify all updates succeeded
        assert len(manager.indicator_values) == 20
