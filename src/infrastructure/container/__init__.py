"""
Container Modules - Domain-Specific Dependency Injection
=========================================================

Refactored container architecture breaking the monolithic container.py
into focused, maintainable modules.

Architecture:
- base.py: Base module class with shared utilities
- trading_module.py: Order, Position, Risk, Session management
- data_module.py: Market data, Indicators, QuestDB providers
- api_module.py: WebSocket, Broadcasting, API endpoints
- container_main.py: Main Container class (renamed from container.py)

Usage:
    from src.infrastructure.container import Container
    container = Container(settings, event_bus, logger)
    order_manager = await container.create_order_manager()
"""

from .base import ContainerModule
from .trading_module import TradingModule
from .data_module import DataModule
from .api_module import ApiModule

# Re-export Container from container_main.py for backward compatibility
from ..container_main import Container

__all__ = [
    'Container',
    'ContainerModule',
    'TradingModule',
    'DataModule',
    'ApiModule',
]
