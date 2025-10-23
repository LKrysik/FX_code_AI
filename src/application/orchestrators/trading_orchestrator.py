"""
Trading Orchestrator
====================
Minimal orchestrator wiring market data, use-case, and executor.
Designed to be created by the DI Container.
"""

import asyncio
from typing import Optional, List

from ...core.event_bus import EventBus
from ...core.logger import StructuredLogger
from ...domain.interfaces.market_data import IMarketDataProvider
from ...domain.interfaces.trading import IOrderExecutor as ITradeExecutor  # alias for clarity
from ...domain.interfaces.notifications import INotificationService
from ...application.use_cases.detect_pump_signals import DetectPumpSignalsUseCase
from ...application.services.position_management_service import PositionManagementService


class TradingOrchestrator:
    def __init__(
        self,
        market_data_provider: IMarketDataProvider,
        trade_executor: ITradeExecutor,
        pump_detection_use_case: DetectPumpSignalsUseCase,
        position_management_service: PositionManagementService,
        notification_service: Optional[INotificationService],
        event_bus: EventBus,
        logger: StructuredLogger,
        symbols: Optional[List[str]] = None,
    ):
        self.market_data = market_data_provider
        self.executor = trade_executor
        self.use_case = pump_detection_use_case
        self.position_manager = position_management_service
        self.notifications = notification_service
        self.event_bus = event_bus
        self.logger = logger
        self.symbols = symbols or []
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        await self.market_data.connect()
        for sym in self.symbols:
            await self.market_data.subscribe_to_symbol(sym)
            task = asyncio.create_task(self._consume_symbol(sym))
            self._tasks.append(task)
        self.logger.info("trading_orchestrator.started", {"symbols": self.symbols})

    async def stop(self) -> None:
        self.logger.info("trading_orchestrator.stopping", {"task_count": len(self._tasks)})
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete with timeout
        if self._tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("trading_orchestrator.stop_timeout", {"timeout_seconds": 2.0})
        
        # Disconnect market data
        try:
            await self.market_data.disconnect()
        except Exception as e:
            self.logger.error("trading_orchestrator.disconnect_error", {"error": str(e)})
            
        self.logger.info("trading_orchestrator.stopped", {})

    async def _wait_for_completion(self) -> None:
        """Wait for all orchestrator tasks to complete naturally"""
        if self._tasks:
            try:
                await asyncio.gather(*self._tasks, return_exceptions=True)
                self.logger.info("trading_orchestrator.completed_naturally")
            except Exception as e:
                self.logger.error("trading_orchestrator.completion_error", {"error": str(e)})

    async def _consume_symbol(self, symbol: str) -> None:
        try:
            async for md in self.market_data.get_market_data_stream(symbol):
                # Market data is now consumed via EventBus
                # The pump detection use case subscribes to 'market.price_update' events
                # No direct call needed here - event-driven architecture
                pass
        except asyncio.CancelledError:
            return

