"""
Domain Interfaces - Ports for External Dependencies
==================================================
Abstract interfaces that define how domain layer communicates with infrastructure.
"""

from .market_data import IMarketDataProvider, IOrderBookProvider
from .trading import IOrderExecutor, IPositionRepository, ITradeRepository
from .notifications import INotificationService
from .storage import IDataStorage, IConfigStorage

__all__ = [
    # Market data interfaces
    'IMarketDataProvider', 'IOrderBookProvider',
    # Trading interfaces
    'IOrderExecutor', 'IPositionRepository', 'ITradeRepository',
    # Notification interfaces
    'INotificationService',
    # Storage interfaces
    'IDataStorage', 'IConfigStorage'
]