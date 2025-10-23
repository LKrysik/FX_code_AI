"""
Factory for PositionManagementService
=====================================
"""

from ...core.event_bus import EventBus
from ...core.logger import StructuredLogger
from ...infrastructure.config.settings import AppSettings
from ...application.services.position_management_service import PositionManagementService

class PositionManagementServiceFactory:
    @staticmethod
    def create(settings: AppSettings, event_bus: EventBus, logger: StructuredLogger) -> PositionManagementService:
        """Create a PositionManagementService instance."""
        return PositionManagementService(
            settings=settings,
            event_bus=event_bus,
            logger=logger
        )
