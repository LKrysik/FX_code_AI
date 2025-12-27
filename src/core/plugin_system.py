"""
Plugin System - Basic Interface for Future Extensibility
=======================================================
Simple plugin interface for future phases. Not used in MVP.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from src.core.logger import get_logger

logger = get_logger(__name__)


class PluginInterface(ABC):
    """Base interface for all plugins"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize plugin with configuration"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown plugin"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get plugin status"""
        pass


class PluginManager:
    """Basic plugin manager for future use"""

    def __init__(self):
        self._plugins: Dict[str, PluginInterface] = {}
        self._enabled_plugins: set = set()

    async def load_plugin(self, plugin: PluginInterface, config: Optional[Dict[str, Any]] = None) -> bool:
        """Load a plugin (placeholder for future implementation)"""
        try:
            plugin_name = plugin.name
            if plugin_name in self._plugins:
                logger.warning(f"Plugin {plugin_name} already loaded")
                return False

            # Initialize plugin
            init_config = config or {}
            if await plugin.initialize(init_config):
                self._plugins[plugin_name] = plugin
                logger.info(f"Plugin {plugin_name} loaded successfully")
                return True
            else:
                logger.error(f"Failed to initialize plugin {plugin_name}")
                return False

        except Exception as e:
            logger.error(f"Error loading plugin {plugin.name}: {e}")
            return False

    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin (placeholder for future implementation)"""
        if plugin_name not in self._plugins:
            logger.warning(f"Plugin {plugin_name} not found")
            return False

        try:
            plugin = self._plugins[plugin_name]
            await plugin.shutdown()
            del self._plugins[plugin_name]
            self._enabled_plugins.discard(plugin_name)
            logger.info(f"Plugin {plugin_name} unloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False

    def get_plugin_status(self) -> Dict[str, Any]:
        """Get status of all plugins"""
        status = {
            "total_plugins": len(self._plugins),
            "enabled_plugins": list(self._enabled_plugins),
            "plugin_details": {}
        }

        for name, plugin in self._plugins.items():
            try:
                status["plugin_details"][name] = plugin.get_status()
            except Exception as e:
                status["plugin_details"][name] = {"error": str(e)}

        return status


# Global plugin manager instance (for future use)
plugin_manager = PluginManager()