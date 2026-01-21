"""
Domain Interfaces - Ports for External Dependencies
==================================================
Abstract interfaces that define how domain layer communicates with infrastructure.
"""

from .market_data import (
    IMarketDataProvider,
    IOrderBookProvider,
    IHistoricalDataProvider,
    IMarketDataCache,
    IMarketDataValidator,
    IMarketDataAggregator
)
from .trading import (
    IOrderExecutor,
    IPositionRepository,
    ITradeRepository,
    IPortfolioManager,
    IRiskManager,
    ISignalProcessor,
    ITradingStrategy
)
from .notifications import (
    INotificationService,
    INotificationFormatter,
    INotificationFilter,
    INotificationHistory,
    INotificationAggregator,
    IAlertManager,
    NotificationLevel,
    NotificationType
)
from .storage import (
    IDataStorage,
    IConfigStorage,
    ITimeSeriesStorage,
    ILogStorage,
    ICacheStorage,
    IBackupStorage,
    IStorageManager
)
from .execution import IExecutionProcessor, IEventBridge
from .indicator_engine import IIndicatorEngine, EngineMode
from .coordination import (
    ITradingCoordinator,
    ISubscriptionCoordinator,
    ISessionStateProvider,
    SubscriptionDecision
)

__all__ = [
    # Market data interfaces
    'IMarketDataProvider',
    'IOrderBookProvider',
    'IHistoricalDataProvider',
    'IMarketDataCache',
    'IMarketDataValidator',
    'IMarketDataAggregator',
    # Trading interfaces
    'IOrderExecutor',
    'IPositionRepository',
    'ITradeRepository',
    'IPortfolioManager',
    'IRiskManager',
    'ISignalProcessor',
    'ITradingStrategy',
    # Notification interfaces
    'INotificationService',
    'INotificationFormatter',
    'INotificationFilter',
    'INotificationHistory',
    'INotificationAggregator',
    'IAlertManager',
    'NotificationLevel',
    'NotificationType',
    # Storage interfaces
    'IDataStorage',
    'IConfigStorage',
    'ITimeSeriesStorage',
    'ILogStorage',
    'ICacheStorage',
    'IBackupStorage',
    'IStorageManager',
    # Execution interfaces
    'IExecutionProcessor',
    'IEventBridge',
    # Indicator engine interfaces
    'IIndicatorEngine',
    'EngineMode',
    # Coordination interfaces
    'ITradingCoordinator',
    'ISubscriptionCoordinator',
    'ISessionStateProvider',
    'SubscriptionDecision'
]