"""
Trade Executor Factory
======================
Handles conditional logic for creating trade executors.
Isolates trading mode selection logic from Container.
"""

from typing import TYPE_CHECKING
from ...domain.interfaces.trading import IOrderExecutor

if TYPE_CHECKING:
    from ...core.event_bus import EventBus
    from ...core.logger import StructuredLogger
    from ...infrastructure.config.settings import AppSettings


class TradeExecutorFactory:
    """Factory for creating trade executors based on settings"""
    
    def __init__(self, settings: 'AppSettings', event_bus: 'EventBus', logger: 'StructuredLogger'):
        self.settings = settings
        self.event_bus = event_bus
        self.logger = logger
    
    def create(self) -> IOrderExecutor:
        """
        Create trade executor based on trading mode.

        Returns:
            Configured trade executor

        Raises:
            NotImplementedError: Real trade executors are not yet implemented
        """
        trading_mode = self.settings.trading.mode.value.lower()

        self.logger.error("trade_executor_factory.not_implemented", {
            "mode": trading_mode,
            "message": "Real trade executors are not yet implemented. Only mock implementations were available and have been removed."
        })

        raise NotImplementedError(
            f"Real trade executor for mode '{trading_mode}' is not implemented. "
            "Mock implementations have been removed from the codebase."
        )
