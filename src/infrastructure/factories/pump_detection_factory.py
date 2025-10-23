"""
Factory for PumpDetectionService
================================
"""

from ...domain.services.pump_detector import PumpDetectionService
from ...infrastructure.config.settings import AppSettings
from ...core.logger import StructuredLogger

class PumpDetectionServiceFactory:
    @staticmethod
    def create(settings: AppSettings, logger: StructuredLogger = None) -> PumpDetectionService:
        """Create pump detection service from Settings."""
        return PumpDetectionService(settings.flash_pump_detection, logger)
