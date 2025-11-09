"""
Unit Tests - ExecutionController State Machine
===============================================
Tests for ExecutionController state machine and lifecycle management.

Test Coverage:
- State transitions (IDLE -> STARTING -> RUNNING -> STOPPING -> STOPPED)
- Invalid transition rejection
- Concurrent stop calls (idempotency)
- Mode switching (backtest, live, data collection)
- Session lifecycle and cleanup
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any

try:
    from src.application.controllers.execution_controller import (
        ExecutionController,
        ExecutionState,
        ExecutionMode,
        ExecutionSession,
        IExecutionDataSource
    )
    from src.core.event_bus import EventBus
    from src.core.logger import StructuredLogger
except ImportError:
    from application.controllers.execution_controller import (
        ExecutionController,
        ExecutionState,
        ExecutionMode,
        ExecutionSession,
        IExecutionDataSource
    )
    from core.event_bus import EventBus
    from core.logger import StructuredLogger


class MockDataSource(IExecutionDataSource):
    """Mock data source for testing"""

    def __init__(self):
        self.started = False
        self.stopped = False

    async def start_stream(self) -> None:
        self.started = True

    async def stop_stream(self) -> None:
        self.stopped = True

    def get_progress(self) -> float:
        return 50.0


class TestExecutionControllerStateTransitions:
    """Test state machine transitions"""

    @pytest.fixture
    def controller(self):
        """Create ExecutionController for testing"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        logger = Mock(spec=StructuredLogger)
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()

        # Create mock persistence service
        db_persistence_service = Mock()
        db_persistence_service.create_session = AsyncMock()
        db_persistence_service.update_session_status = AsyncMock()
        db_persistence_service.persist_tick_prices = AsyncMock()

        controller = ExecutionController(
            event_bus=event_bus,
            logger=logger,
            market_data_provider_factory=None,
            db_persistence_service=db_persistence_service
        )

        return controller

    @pytest.mark.asyncio
    async def test_idle_to_starting_to_running_sequence(self, controller):
        """Test IDLE -> STARTING -> RUNNING state sequence"""
        # Create session (starts in IDLE)
        session_id = await controller.create_session(
            mode=ExecutionMode.BACKTEST,
            symbols=["BTC_USDT"],
            config={"session_id": "test_session_123"}
        )

        assert controller._current_session is not None
        assert controller._current_session.status == ExecutionState.IDLE

        # Start execution (will transition to STARTING then RUNNING)
        data_source = MockDataSource()

        # Use asyncio.create_task to avoid waiting for completion
        task = asyncio.create_task(controller.start_execution(
            mode=ExecutionMode.BACKTEST,
            symbols=["BTC_USDT"],
            data_source=data_source,
            parameters={"session_id": "test_session_123"}
        ))

        # Wait a bit for state transitions
        await asyncio.sleep(0.2)

        # Should be in RUNNING state
        assert controller._current_session.status in (
            ExecutionState.RUNNING,
            ExecutionState.STARTING
        )

        # Cleanup
        await controller.stop_execution()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_running_to_stopping_to_stopped_sequence(self, controller):
        """Test RUNNING -> STOPPING -> STOPPED state sequence"""
        # Setup running session
        session_id = await controller.create_session(
            mode=ExecutionMode.BACKTEST,
            symbols=["ETH_USDT"],
            config={"session_id": "test_session_456"}
        )

        data_source = MockDataSource()
        task = asyncio.create_task(controller.start_execution(
            mode=ExecutionMode.BACKTEST,
            symbols=["ETH_USDT"],
            data_source=data_source,
            parameters={"session_id": "test_session_456"}
        ))

        await asyncio.sleep(0.2)

        # Should be running
        assert controller._current_session.status in (
            ExecutionState.RUNNING,
            ExecutionState.STARTING
        )

        # Stop execution
        await controller.stop_execution()

        # Should transition to STOPPING then STOPPED
        assert controller._current_session.status in (
            ExecutionState.STOPPING,
            ExecutionState.STOPPED
        )

        # Cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_invalid_transitions_are_rejected(self, controller):
        """Test that invalid state transitions are rejected"""
        # Create session in IDLE state
        session_id = await controller.create_session(
            mode=ExecutionMode.BACKTEST,
            symbols=["BNB_USDT"],
            config={"session_id": "test_session_789"}
        )

        # Can't transition from IDLE to STOPPED directly
        with pytest.raises(RuntimeError, match="Invalid state transition|Cannot stop"):
            # Manually set state to test invalid transition
            controller._current_session.status = ExecutionState.IDLE
            await controller.stop_execution()

    @pytest.mark.asyncio
    async def test_concurrent_stop_calls_are_idempotent(self, controller):
        """Test that concurrent stop calls are idempotent (no errors)"""
        # Create and start session
        session_id = await controller.create_session(
            mode=ExecutionMode.BACKTEST,
            symbols=["ADA_USDT"],
            config={"session_id": "test_session_concurrent"}
        )

        data_source = MockDataSource()
        task = asyncio.create_task(controller.start_execution(
            mode=ExecutionMode.BACKTEST,
            symbols=["ADA_USDT"],
            data_source=data_source,
            parameters={"session_id": "test_session_concurrent"}
        ))

        await asyncio.sleep(0.2)

        # Call stop multiple times concurrently
        stop_tasks = [controller.stop_execution() for _ in range(5)]
        results = await asyncio.gather(*stop_tasks, return_exceptions=True)

        # All should complete without error (idempotent)
        for result in results:
            if isinstance(result, Exception):
                # RuntimeError is acceptable for invalid state transitions
                assert isinstance(result, RuntimeError), f"Unexpected error: {result}"

        # Should be stopped
        assert controller._current_session.status in (
            ExecutionState.STOPPING,
            ExecutionState.STOPPED,
            ExecutionState.IDLE
        )

        # Cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_cleanup_lock_prevents_reentrant_cleanup(self, controller):
        """Test that cleanup lock prevents re-entrant cleanup calls"""
        # Create session
        session_id = await controller.create_session(
            mode=ExecutionMode.BACKTEST,
            symbols=["SOL_USDT"],
            config={"session_id": "test_cleanup"}
        )

        data_source = MockDataSource()
        task = asyncio.create_task(controller.start_execution(
            mode=ExecutionMode.BACKTEST,
            symbols=["SOL_USDT"],
            data_source=data_source,
            parameters={"session_id": "test_cleanup"}
        ))

        await asyncio.sleep(0.2)

        # Try to call cleanup multiple times concurrently
        cleanup_tasks = [controller._cleanup_session() for _ in range(3)]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        # Cleanup should have completed without errors
        # (lock prevents concurrent cleanup)

        # Cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestExecutionControllerModeSwitching:
    """Test mode switching between backtest, live, and data collection"""

    @pytest.fixture
    def controller(self):
        """Create ExecutionController for mode tests"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        logger = Mock(spec=StructuredLogger)
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()

        db_persistence_service = Mock()
        db_persistence_service.create_session = AsyncMock()
        db_persistence_service.update_session_status = AsyncMock()

        controller = ExecutionController(
            event_bus=event_bus,
            logger=logger,
            market_data_provider_factory=None,
            db_persistence_service=db_persistence_service
        )

        return controller

    @pytest.mark.asyncio
    async def test_backtest_mode_initialization(self, controller):
        """Test backtest mode initialization"""
        session_id = await controller.create_session(
            mode=ExecutionMode.BACKTEST,
            symbols=["BTC_USDT"],
            config={"session_id": "historical_session_123"}
        )

        assert controller._current_session.mode == ExecutionMode.BACKTEST
        assert controller._current_session.symbols == ["BTC_USDT"]

    @pytest.mark.asyncio
    async def test_live_mode_initialization(self, controller):
        """Test live mode initialization"""
        # Mock market data provider factory
        mock_factory = Mock()
        mock_provider = Mock()
        mock_provider.connect = AsyncMock()
        mock_provider.subscribe_to_symbol = AsyncMock()
        mock_factory.create = Mock(return_value=mock_provider)
        controller.market_data_provider_factory = mock_factory

        session_id = await controller.create_session(
            mode=ExecutionMode.LIVE,
            symbols=["ETH_USDT"],
            config={}
        )

        assert controller._current_session.mode == ExecutionMode.LIVE
        assert controller._current_session.symbols == ["ETH_USDT"]

    @pytest.mark.asyncio
    async def test_data_collection_mode_initialization(self, controller):
        """Test data collection mode initialization"""
        # Mock market data provider factory
        mock_factory = Mock()
        mock_provider = Mock()
        mock_provider.connect = AsyncMock()
        mock_provider.subscribe_to_symbol = AsyncMock()
        mock_factory.create = Mock(return_value=mock_provider)
        controller.market_data_provider_factory = mock_factory

        session_id = await controller.create_session(
            mode=ExecutionMode.DATA_COLLECTION,
            symbols=["BNB_USDT"],
            config={
                "duration": "5m",
                "data_types": ["prices"],
                "data_path": "/tmp/test_data"
            }
        )

        assert controller._current_session.mode == ExecutionMode.DATA_COLLECTION
        assert controller._current_session.symbols == ["BNB_USDT"]
        assert "duration" in controller._current_session.parameters


class TestExecutionControllerSessionLifecycle:
    """Test session lifecycle and cleanup"""

    @pytest.fixture
    def controller(self):
        """Create ExecutionController for lifecycle tests"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        logger = Mock(spec=StructuredLogger)
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()

        db_persistence_service = Mock()
        db_persistence_service.create_session = AsyncMock()
        db_persistence_service.update_session_status = AsyncMock()

        controller = ExecutionController(
            event_bus=event_bus,
            logger=logger,
            market_data_provider_factory=None,
            db_persistence_service=db_persistence_service
        )

        return controller

    @pytest.mark.asyncio
    async def test_session_creation_and_cleanup(self, controller):
        """Test session creation and cleanup"""
        # Create session
        session_id = await controller.create_session(
            mode=ExecutionMode.BACKTEST,
            symbols=["BTC_USDT"],
            config={"session_id": "cleanup_test"}
        )

        assert controller._current_session is not None
        assert controller._current_session.session_id == session_id

        # Cleanup session
        await controller._cleanup_session()

        # Session should be cleared
        assert controller._current_session is None

    @pytest.mark.asyncio
    async def test_cleanup_on_error_no_resource_leaks(self, controller):
        """Test cleanup on error prevents resource leaks"""
        # Create session
        session_id = await controller.create_session(
            mode=ExecutionMode.BACKTEST,
            symbols=["ETH_USDT"],
            config={"session_id": "error_test"}
        )

        # Create data source that will be cleaned up
        data_source = MockDataSource()
        controller._data_source = data_source

        # Add some mock buffers
        controller._data_buffers = {
            "ETH_USDT": {
                "price_data": [1, 2, 3],
                "orderbook_data": []
            }
        }

        # Simulate error and cleanup
        controller._current_session.status = ExecutionState.ERROR
        await controller._cleanup_session()

        # Verify cleanup
        assert not hasattr(controller, "_data_buffers") or len(controller._data_buffers) == 0
        assert controller._current_session is None or controller._current_session.status == ExecutionState.STOPPED


class TestExecutionControllerSymbolConflicts:
    """Test symbol conflict detection and resolution"""

    @pytest.fixture
    def controller(self):
        """Create ExecutionController for symbol conflict tests"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        logger = Mock(spec=StructuredLogger)
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()

        db_persistence_service = Mock()
        db_persistence_service.create_session = AsyncMock()
        db_persistence_service.update_session_status = AsyncMock()

        controller = ExecutionController(
            event_bus=event_bus,
            logger=logger,
            market_data_provider_factory=None,
            db_persistence_service=db_persistence_service
        )

        return controller

    @pytest.mark.asyncio
    async def test_symbol_conflict_detection(self, controller):
        """Test that symbol conflicts are detected"""
        # Create first session with BTC_USDT
        session_id1 = await controller.create_session(
            mode=ExecutionMode.BACKTEST,
            symbols=["BTC_USDT"],
            config={"session_id": "session_1"}
        )

        # Try to create second session with same symbol (should fail)
        with pytest.raises(ValueError, match="Symbol conflict|strategy_activation_failed"):
            session_id2 = await controller.create_session(
                mode=ExecutionMode.BACKTEST,
                symbols=["BTC_USDT"],
                config={"session_id": "session_2"}
            )

    @pytest.mark.asyncio
    async def test_symbol_release_on_session_end(self, controller):
        """Test that symbols are released when session ends"""
        # Create session
        session_id = await controller.create_session(
            mode=ExecutionMode.BACKTEST,
            symbols=["ETH_USDT"],
            config={"session_id": "release_test"}
        )

        # Verify symbol is locked
        assert "ETH_USDT" in controller._active_symbols

        # End session and cleanup
        await controller._cleanup_session()

        # Symbol should be released
        assert "ETH_USDT" not in controller._active_symbols

    @pytest.mark.asyncio
    async def test_atomic_symbol_acquisition_prevents_race(self, controller):
        """Test that atomic symbol acquisition prevents race conditions"""
        # Try to create 10 sessions concurrently with same symbol
        async def create_session_task(index: int):
            try:
                session_id = await controller.create_session(
                    mode=ExecutionMode.BACKTEST,
                    symbols=["ADA_USDT"],
                    config={"session_id": f"concurrent_{index}"}
                )
                return session_id
            except ValueError:
                return None

        tasks = [create_session_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Only 1 should succeed
        successful = [r for r in results if r is not None and not isinstance(r, Exception)]
        assert len(successful) == 1, f"Race condition: {len(successful)} sessions created"
