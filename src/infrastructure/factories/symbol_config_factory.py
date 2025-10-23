"""
Symbol Configuration Factory
===========================
Factory for creating SymbolConfigurationManager instances.
Following Clean Architecture - no conditional logic in Container.
"""

from ..config.settings import AppSettings
from ..config.symbol_config import SymbolConfigurationManager
from ...core.logger import StructuredLogger


class SymbolConfigurationFactory:
    """
    Factory for creating SymbolConfigurationManager instances.
    Encapsulates creation logic and keeps Container free of business decisions.
    """
    
    def create(self, settings: AppSettings, logger: StructuredLogger) -> SymbolConfigurationManager:
        """
        Create a SymbolConfigurationManager instance.
        
        Args:
            settings: Application settings
            logger: Structured logger instance
            
        Returns:
            Configured SymbolConfigurationManager
        """
        return SymbolConfigurationManager(
            config_dir=settings.config_dir,
            default_settings=settings,
            logger=logger
        )
