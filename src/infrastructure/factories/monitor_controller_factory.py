"""
MonitorController Factory - Handles optional dependency creation logic
====================================================================
Factory handles conditional logic for MonitorController creation,
keeping Container free of business decisions.
"""

from typing import Optional
from ...core.event_bus import EventBus
from ...core.logger import StructuredLogger
from ...infrastructure.config.settings import AppSettings


class MonitorControllerFactory:
    """
    Factory for creating MonitorController instances.
    Handles optional dependency logic that was previously in Container.
    """
    
    def __init__(self, settings: AppSettings, event_bus: EventBus, logger: StructuredLogger):
        """
        Initialize factory with dependencies.
        
        Args:
            settings: Application settings
            event_bus: Central communication hub
            logger: Structured logger instance
        """
        self.settings = settings
        self.event_bus = event_bus
        self.logger = logger
    
    def create(self) -> Optional['MonitorController']:
        """
        Create MonitorController instance if available.
        Handles import logic that was previously in Container.
        
        Returns:
            MonitorController instance or None if not available
        """
        try:
            from ...trading.monitor_controller import MonitorController
            
            # Convert AppSettings to dict for MonitorController compatibility
            config_dict = self.settings.model_dump() if hasattr(self.settings, 'model_dump') else (
                self.settings.dict() if hasattr(self.settings, 'dict') else dict(self.settings)
            )
            
            return MonitorController(config_dict, self.logger, self.event_bus)
        except ImportError:
            # MonitorController is optional dependency
            self.logger.debug("monitor_controller.not_available", {
                "reason": "ImportError - MonitorController module not found"
            })
            return None